import re

from django import forms
from django.contrib import admin
from django.db import transaction

from core.validaciones import motivo_rut_invalido, rut_canonico

from .models import Cargo, Delegacion, Funcionario, ParametroSistema, Rol, Usuario

admin.site.site_header = "SIGED La Serena - Administración"
admin.site.site_title = "SIGED"
admin.site.index_title = "Mantenedores del sistema municipal"


class UsuarioInline(admin.TabularInline):
    model = Usuario
    extra = 0
    fields = ("username", "nombre", "correo", "estado")
    show_change_link = True


class FuncionarioInline(admin.TabularInline):
    model = Funcionario
    extra = 0
    fields = ("codigo", "rut", "nombre", "cargo", "estado")
    show_change_link = True


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "codigo", "descripcion")
    search_fields = ("nombre", "codigo", "descripcion")
    prepopulated_fields = {"codigo": ("nombre",)}
    inlines = [UsuarioInline]


@admin.register(Delegacion)
class DelegacionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "direccion", "comuna")
    search_fields = ("nombre", "direccion", "comuna")
    list_filter = ("comuna",)
    inlines = [FuncionarioInline]


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "modulo_principal", "descripcion")
    search_fields = ("codigo", "nombre", "descripcion")
    list_filter = ("modulo_principal",)


class FuncionarioAdminForm(forms.ModelForm):
    """El campo del modelo admite 10 caracteres; aquí se acepta el RUT con puntos y se guarda normalizado."""

    rut = forms.CharField(label="RUT", max_length=14, help_text="Con o sin puntos y guion. Se guarda como 33100001-9.")

    class Meta:
        model = Funcionario
        fields = "__all__"

    def clean_rut(self):
        valor = self.cleaned_data["rut"]
        canonico = rut_canonico(valor)
        if canonico is None:
            raise forms.ValidationError(motivo_rut_invalido(valor))
        otro = Funcionario.objects.filter(rut=canonico).exclude(pk=self.instance.pk).first()
        if otro is not None:
            raise forms.ValidationError(f"Ese RUT ya pertenece a la ficha {otro.codigo}.")
        return canonico


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    form = FuncionarioAdminForm
    list_display = ("codigo", "rut", "nombre_visible", "cargo", "delegacion", "es_simulacion", "fecha_ultimo_ingreso", "estado")
    search_fields = ("codigo", "rut", "nombre", "nombres", "apellido_paterno", "cargo__nombre", "delegacion__nombre")
    list_filter = ("estado", "delegacion", "cargo")
    autocomplete_fields = ("cargo", "delegacion")
    date_hierarchy = "fecha_ultimo_ingreso"

    @admin.display(description="nombre")
    def nombre_visible(self, obj):
        return obj.nombre_mostrado

    def get_inlines(self, request, obj):
        # Import diferido para evitar dependencia circular entre apps.
        from control_gestion.admin import ActividadInline, ItemFuncionarioInline
        return [ItemFuncionarioInline, ActividadInline]


class UsuarioAdminForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = "__all__"

    def clean_username(self):
        valor = (self.cleaned_data.get("username") or "").strip()
        canonico = rut_canonico(valor)
        if canonico:
            return canonico
        # Nombres de usuario que no son un RUT (cuentas antiguas) se conservan; un RUT mal escrito, no.
        if re.fullmatch(r"[\d.\s-]+[\dkK]", valor):
            raise forms.ValidationError(motivo_rut_invalido(valor))
        return valor


def _borrar_cuentas_de_acceso(usuarios):
    """Quita la cuenta de acceso de cada perfil borrado para no dejar un RUT bloqueado.

    Nunca elimina cuentas de personal técnico (staff o superusuario).
    """
    from django.contrib.auth import get_user_model

    ids = [u.user_id for u in usuarios if u.user_id]
    if ids:
        get_user_model().objects.filter(pk__in=ids, is_staff=False, is_superuser=False).delete()


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    form = UsuarioAdminForm
    list_display = ("id", "nombre_visible", "username", "correo", "rol", "delegacion", "estado")
    search_fields = ("nombre", "username", "correo", "codigo", "funcionario__rut", "funcionario__nombre")
    list_filter = ("estado", "rol", "delegacion")
    autocomplete_fields = ("rol", "cargo", "delegacion", "funcionario", "user")
    readonly_fields = ("creado",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("funcionario")

    def delete_model(self, request, obj):
        with transaction.atomic():
            perfiles = [obj]
            super().delete_model(request, obj)
            _borrar_cuentas_de_acceso(perfiles)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            perfiles = list(queryset)
            super().delete_queryset(request, queryset)
            _borrar_cuentas_de_acceso(perfiles)

    @admin.display(description="nombre")
    def nombre_visible(self, obj):
        return obj.nombre_mostrado


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ("nombre_sistema", "comuna", "region", "sla_verde_max_dias", "sla_amarillo_max_dias",
                    "meta_tubo_porcentaje", "encuesta_habilitada")
    search_fields = ("nombre_sistema", "comuna")
