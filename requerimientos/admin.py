from django.contrib import admin

from .models import AreaSoporte, Atencion, CanalIngreso, Requerimiento, SubAtencion, TipoAtencion, TipoGestion, Vecino


class SubAtencionInline(admin.TabularInline):
    model = SubAtencion
    extra = 0


class RequerimientoInline(admin.TabularInline):
    model = Requerimiento
    extra = 0
    fields = ("codigo", "fecha_ingreso", "tipo_gestion", "estado")
    show_change_link = True


class AtencionInline(admin.TabularInline):
    model = Atencion
    extra = 0
    fields = ("fecha", "tipo_atencion", "sub_atencion", "estado")
    show_change_link = True


@admin.register(TipoGestion)
class TipoGestionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre", "descripcion")


@admin.register(Vecino)
class VecinoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_visible", "rut", "direccion", "telefono", "territorio", "tipo_gestion", "estado")
    search_fields = ("nombre", "rut", "direccion", "telefono", "correo")
    list_filter = ("estado", "tipo_gestion", "territorio", "delegacion")
    autocomplete_fields = ("tipo_gestion", "delegacion")
    inlines = [RequerimientoInline, AtencionInline]

    @admin.display(description="nombre")
    def nombre_visible(self, obj):
        return obj.nombre_mostrado


@admin.register(TipoAtencion)
class TipoAtencionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre", "descripcion")
    inlines = [SubAtencionInline]


@admin.register(SubAtencion)
class SubAtencionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo_atencion")
    search_fields = ("nombre", "tipo_atencion__nombre")
    list_filter = ("tipo_atencion",)
    autocomplete_fields = ("tipo_atencion",)


@admin.register(CanalIngreso)
class CanalIngresoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)


@admin.register(AreaSoporte)
class AreaSoporteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "encargado", "tiempo_promedio_dias", "total_casos_mes",
                    "porcentaje_cumplimiento", "satisfaccion_promedio")
    search_fields = ("codigo", "nombre", "encargado__nombre", "encargado_nombre")
    autocomplete_fields = ("encargado",)
    inlines = [RequerimientoInline]


@admin.register(Requerimiento)
class RequerimientoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "vecino", "delegacion", "tipo_gestion", "area", "canal_ingreso",
                    "fecha_ingreso", "estado", "evaluacion_satisfaccion")
    search_fields = ("codigo", "descripcion", "vecino__nombre", "vecino__rut", "asignado_a")
    list_filter = ("estado", "delegacion", "tipo_gestion", "area", "canal_ingreso")
    autocomplete_fields = ("vecino", "delegacion", "canal_ingreso", "tipo_gestion", "area", "funcionario")
    date_hierarchy = "fecha_ingreso"
    list_select_related = ("vecino", "delegacion", "tipo_gestion", "area", "canal_ingreso")


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "vecino", "tipo_atencion", "sub_atencion", "delegacion", "usuario", "estado")
    search_fields = ("vecino__nombre", "vecino__rut", "observacion", "sub_atencion__nombre")
    # Sin date_hierarchy: en MySQL sin tablas de zona horaria falla con DateTimeField.
    list_filter = ("estado", "tipo_atencion", "delegacion", "fecha")
    autocomplete_fields = ("vecino", "tipo_atencion", "sub_atencion", "delegacion", "usuario")
    list_select_related = ("vecino", "tipo_atencion", "sub_atencion", "delegacion", "usuario")
