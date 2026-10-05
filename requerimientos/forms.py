"""ModelForms de los mantenedores de atención ciudadana."""

import re

from django import forms

from cuentas.forms import FormularioBootstrap, NombreMinimoMixin
from requerimientos.models import Atencion, SubAtencion, TipoAtencion, TipoGestion, Vecino


class TipoGestionForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = TipoGestion
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class TipoAtencionForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = TipoAtencion
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class SubAtencionForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = SubAtencion
        fields = ["nombre", "tipo_atencion", "descripcion"]
        labels = {
            "nombre": "Nombre",
            "tipo_atencion": "Tipo de atención",
            "descripcion": "Descripción",
        }
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo_atencion")
        nombre = cleaned.get("nombre")
        if tipo and nombre:
            qs = SubAtencion.objects.filter(tipo_atencion=tipo, nombre__iexact=nombre)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("nombre", "Ya existe esa sub atención para el tipo elegido.")
        return cleaned


class VecinoForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = Vecino
        fields = [
            "nombre",
            "rut",
            "direccion",
            "telefono",
            "correo",
            "territorio",
            "delegacion",
            "tipo_gestion",
            "estado",
        ]
        labels = {
            "nombre": "Nombre",
            "rut": "RUT",
            "direccion": "Dirección",
            "telefono": "Teléfono",
            "correo": "Correo",
            "territorio": "Territorio",
            "delegacion": "Delegación",
            "tipo_gestion": "Tipo de gestión",
            "estado": "Estado",
        }

    def clean_nombre(self):
        from core.validaciones import MENSAJE_NOMBRE

        nombre = super().clean_nombre()
        if "(" in nombre or ")" in nombre:
            raise forms.ValidationError(MENSAJE_NOMBRE)
        return nombre.replace("(ficticio)", "").strip()

    def clean_rut(self):
        from core.validaciones import MENSAJE_RUT, normalizar_rut, validar_rut

        rut = (self.cleaned_data.get("rut") or "").strip()
        if not rut:
            return None
        if not validar_rut(rut):
            raise forms.ValidationError(MENSAJE_RUT)
        return normalizar_rut(rut)

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()
        if telefono and len(re.sub(r"\D", "", telefono)) < 8:
            raise forms.ValidationError("Ingrese un teléfono de al menos 8 dígitos.")
        return telefono


class AtencionForm(FormularioBootstrap):
    fecha = forms.DateTimeField(
        label="Fecha",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"],
    )

    class Meta:
        model = Atencion
        fields = [
            "vecino",
            "tipo_atencion",
            "sub_atencion",
            "delegacion",
            "usuario",
            "fecha",
            "estado",
            "observacion",
        ]
        labels = {
            "vecino": "Vecino",
            "tipo_atencion": "Tipo de atención",
            "sub_atencion": "Sub atención",
            "delegacion": "Delegación",
            "usuario": "Registrada por",
            "estado": "Estado",
            "observacion": "Observación",
        }
        widgets = {"observacion": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            return
        from django.utils import timezone

        momento = self.instance.fecha if self.instance.pk and self.instance.fecha else timezone.now()
        valor = timezone.localtime(momento).strftime("%Y-%m-%dT%H:%M")
        self.initial["fecha"] = valor
        self.fields["fecha"].widget.attrs["value"] = valor
