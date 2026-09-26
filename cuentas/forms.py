"""Formularios de cuentas: mantenedores y nueva contraseña."""

import re

from django import forms
from django.contrib.auth import get_user_model

from cuentas.models import Delegacion, Rol, Usuario
from cuentas.servicios import errores_clave, siguiente_codigo


def aplicar_bootstrap(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            extra = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            extra = "form-select"
        else:
            extra = "form-control"
        previa = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{previa} {extra}".strip()
        field.error_messages["required"] = "Este campo es obligatorio."
        if getattr(field, "empty_label", None) is not None:
            field.empty_label = "Seleccione..." if field.required else "Sin asignar"
        if field.required and not isinstance(widget, forms.CheckboxInput):
            widget.attrs["required"] = "required"
        else:
            widget.attrs.pop("required", None)


class FormularioBootstrap(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_bootstrap(self)


class NombreMinimoMixin:
    minimo_nombre = 3

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if len(nombre) < self.minimo_nombre:
            raise forms.ValidationError(f"Ingrese al menos {self.minimo_nombre} caracteres.")
        return nombre


class RolForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = Rol
        fields = ["codigo", "nombre", "descripcion"]
        labels = {"codigo": "Código", "nombre": "Nombre", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class DelegacionForm(NombreMinimoMixin, FormularioBootstrap):
    class Meta:
        model = Delegacion
        fields = ["nombre", "direccion", "comuna"]
        labels = {"nombre": "Nombre", "direccion": "Dirección", "comuna": "Comuna"}


class UsuarioForm(FormularioBootstrap):
    password = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Usuario
        fields = ["username", "nombre", "correo", "rol", "cargo", "delegacion", "funcionario", "estado"]
        labels = {
            "username": "Usuario",
            "nombre": "Nombre",
            "correo": "Correo",
            "rol": "Rol",
            "cargo": "Cargo",
            "delegacion": "Delegación",
            "funcionario": "Funcionario",
            "estado": "Estado",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        if self.instance.pk is None:
            self.fields["password"].required = True
            self.fields["password"].widget.attrs["required"] = "required"
            self.fields["password"].help_text = (
                "Mínimo 8 caracteres, con mayúscula, minúscula, número y un símbolo."
            )
        else:
            self.fields["password"].help_text = "Déjela en blanco para mantener la contraseña actual."

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,20}", username):
            raise forms.ValidationError(
                "Use de 3 a 20 caracteres: letras minúsculas, números, punto o guion."
            )
        return username

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if len(nombre) < 5:
            raise forms.ValidationError("Ingrese el nombre completo (mínimo 5 caracteres).")
        return nombre

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        if not password:
            if self.instance.pk is None:
                raise forms.ValidationError("Ingrese una contraseña.")
            return ""
        errores = errores_clave(password)
        if errores:
            raise forms.ValidationError(errores)
        return password

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if not usuario.codigo:
            usuario.codigo = siguiente_codigo(Usuario, "codigo", "USR-", 3)
        if commit:
            usuario.save()
            self.save_m2m()
            self._sincronizar_auth(usuario)
        return usuario

    def _sincronizar_auth(self, usuario):
        User = get_user_model()
        password = self.cleaned_data.get("password") or ""
        user = usuario.user or User.objects.filter(username=usuario.username).first()
        if user is None:
            user = User(username=usuario.username, email=usuario.correo)
        user.username = usuario.username
        user.email = usuario.correo
        user.is_active = usuario.activo
        partes = (usuario.nombre or "").split(" ", 1)
        user.first_name = partes[0][:150]
        user.last_name = (partes[1] if len(partes) > 1 else "")[:150]
        if password:
            user.set_password(password)
        elif not user.password:
            user.set_unusable_password()
        user.save()
        if usuario.user_id != user.pk:
            usuario.user = user
            usuario.save(update_fields=["user"])


class NuevaContrasenaForm(forms.Form):
    password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "id": "id_password"}),
    )
    confirmacion = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "id": "id_confirmacion"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_bootstrap(self)

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password") or ""
        confirmacion = cleaned.get("confirmacion") or ""
        if password:
            for mensaje in errores_clave(password):
                self.add_error("password", mensaje)
        if password and confirmacion and password != confirmacion:
            self.add_error("confirmacion", "Las contraseñas no coinciden.")
        return cleaned
