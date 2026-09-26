"""ModelForm del mantenedor de metas."""

from django import forms

from control_gestion.models import Meta
from cuentas.forms import FormularioBootstrap, NombreMinimoMixin


class MetaForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = Meta
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}
