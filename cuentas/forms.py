"""Formularios de cuentas: mantenedores y nueva contraseña."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.db import transaction
from django.forms.boundfield import BoundField

from core.validaciones import MENSAJE_RUT, normalizar_rut, validar_rut
from cuentas.models import Delegacion, Rol, Usuario
from cuentas.servicios import errores_clave, siguiente_codigo


class CampoSiged(BoundField):
    """Calcula ``required`` e ``is-invalid`` al dibujar, no al construir el formulario.

    Antes ``required`` quedaba fijo en el widget y, si una vista volvía opcional un
    campo después, el navegador igual bloqueaba el envío. Además los errores del
    servidor no marcaban el campo en rojo.
    """

    def build_widget_attrs(self, attrs, widget=None):
        attrs = super().build_widget_attrs(attrs, widget)
        if self.form.is_bound and self.errors:
            clases = attrs.get("class", (widget or self.field.widget).attrs.get("class", ""))
            if "is-invalid" not in clases:
                attrs["class"] = f"{clases} is-invalid".strip()
            attrs["aria-describedby"] = f"{self.auto_id}_error"
        return attrs


def aplicar_bootstrap(form):
    form.bound_field_class = CampoSiged
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            extra = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            extra = "form-select"
        else:
            extra = "form-control"
        previa = widget.attrs.get("class", "")
        if extra not in previa.split():
            widget.attrs["class"] = f"{previa} {extra}".strip()
        field.error_messages["required"] = "Este campo es obligatorio."
        if getattr(field, "empty_label", None) is not None:
            field.empty_label = "Seleccione..." if field.required else "Sin asignar"
        # ``required`` lo pone Django al dibujar según field.required vigente.
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
        # Usuario, nombre y delegación salen de la ficha del funcionario al guardar:
        # se muestran solo como referencia para que nadie crea que los cambió.
        for campo in ("username", "nombre", "delegacion"):
            self.fields[campo].required = False
            self.fields[campo].disabled = True
        self.fields["username"].help_text = "Es el RUT del funcionario elegido."
        self.fields["nombre"].help_text = "Se toma de la ficha del funcionario."
        self.fields["delegacion"].help_text = "Se toma de la ficha del funcionario."
        self.fields["funcionario"].required = True
        self.fields["funcionario"].help_text = "Persona con RUT. El acceso usa ese RUT."
        self.fields.pop("password", None)

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean(self):
        cleaned = super().clean()
        funcionario = cleaned.get("funcionario")
        if funcionario is None:
            return cleaned
        rut = normalizar_rut(funcionario.rut or "")
        if not validar_rut(rut):
            self.add_error("funcionario", MENSAJE_RUT)
            return cleaned
        duplicado = Usuario.objects.filter(username=rut).exclude(pk=self.instance.pk).exists()
        if duplicado:
            self.add_error("funcionario", "Ese RUT ya tiene otra cuenta.")
            return cleaned
        # Una cuenta de acceso (auth.User) con ese RUT que no es la de este usuario
        # no se reutiliza: podría ser de administración y heredaría su clave y permisos.
        User = get_user_model()
        ajena = User.objects.filter(username=rut)
        if self.instance.user_id:
            ajena = ajena.exclude(pk=self.instance.user_id)
        if ajena.exists():
            self.add_error("funcionario", "Ese RUT ya pertenece a otra cuenta de acceso. Revise con soporte.")
            return cleaned
        correo = (cleaned.get("correo") or "").strip()
        if correo and Usuario.objects.filter(correo__iexact=correo).exclude(pk=self.instance.pk).exists():
            self.add_error("correo", "Ese correo ya está registrado en otra cuenta.")
        cleaned["username"] = rut
        return cleaned

    def save(self, commit=True):
        usuario = super().save(commit=False)
        funcionario = usuario.funcionario
        if funcionario is not None and funcionario.rut:
            usuario.username = normalizar_rut(funcionario.rut)
            usuario.nombre = funcionario.nombre
            if funcionario.delegacion_id:
                usuario.delegacion = funcionario.delegacion
        if not usuario.codigo:
            usuario.codigo = siguiente_codigo(Usuario, "codigo", "USR-", 3)
        if commit:
            with transaction.atomic():
                usuario.save()
                self.save_m2m()
                self._sincronizar_auth(usuario)
        return usuario

    def _sincronizar_auth(self, usuario):
        User = get_user_model()
        password = self.cleaned_data.get("password") or ""
        # Solo la cuenta propia; clean() ya rechazó un auth.User ajeno con ese RUT.
        user = usuario.user
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


class RestablecerEnlaceForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_bootstrap(self)

    def clean_new_password1(self):
        password=self.cleaned_data.get('new_password1','')
        errores=errores_clave(password)
        if errores:
            raise forms.ValidationError(errores)
        return password
