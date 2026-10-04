from django.contrib import admin

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


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
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


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_visible", "username", "correo", "rol", "delegacion", "estado")
    search_fields = ("nombre", "username", "correo", "codigo", "funcionario__rut", "funcionario__nombre")
    list_filter = ("estado", "rol", "delegacion")
    autocomplete_fields = ("rol", "cargo", "delegacion", "funcionario", "user")
    readonly_fields = ("creado",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("funcionario")

    @admin.display(description="nombre")
    def nombre_visible(self, obj):
        return obj.nombre_mostrado


@admin.register(ParametroSistema)
class ParametroSistemaAdmin(admin.ModelAdmin):
    list_display = ("nombre_sistema", "comuna", "region", "sla_verde_max_dias", "sla_amarillo_max_dias",
                    "meta_tubo_porcentaje", "encuesta_habilitada")
    search_fields = ("nombre_sistema", "comuna")
