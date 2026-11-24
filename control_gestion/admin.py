from django.contrib import admin

from .models import Actividad, Compromiso, EventoAgenda, ItemFuncionario, Medicion, Meta, Notificacion


class ItemFuncionarioInline(admin.TabularInline):
    model = ItemFuncionario
    extra = 0
    autocomplete_fields = ("meta",)


class ActividadInline(admin.TabularInline):
    model = Actividad
    extra = 0
    fields = ("codigo", "fecha_actividad", "meta", "servicio", "punto_validado")
    readonly_fields = fields
    can_delete = False
    def has_add_permission(self, request, obj=None):return False
    autocomplete_fields = ("meta",)
    show_change_link = True


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre", "descripcion")


@admin.register(ItemFuncionario)
class ItemFuncionarioAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "meta", "ponderador", "meta_trimestre", "avance_actual", "porcentaje_avance")
    search_fields = ("funcionario__nombre", "funcionario__codigo", "meta__nombre")
    list_filter = ("funcionario__delegacion", "funcionario")
    autocomplete_fields = ("funcionario", "meta")


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    readonly_fields = ('abrir_evidencia','punto_validado','estado_revision','version_revision')
    def get_readonly_fields(self,request,obj=None):
        if obj and obj.estado_revision!='HISTORICA':
            return tuple(f.name for f in self.model._meta.fields if f.editable)+self.readonly_fields
        return self.readonly_fields
    def has_delete_permission(self,request,obj=None):
        return bool(obj and obj.estado_revision=='HISTORICA' and super().has_delete_permission(request,obj))
    def save_model(self,request,obj,form,change):
        if not change:obj.creado_por=request.user
        super().save_model(request,obj,form,change)

    @admin.display(description='Ver evidencia adjunta')
    def abrir_evidencia(self,obj):
        from django.urls import reverse
        from django.utils.html import format_html
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir imagen o PDF</a>',reverse('admin_actividad_evidencia',args=[obj.codigo])) if obj.evidencia_archivo else 'Sin archivo adjunto'

    list_display = ("codigo", "fecha_actividad", "funcionario", "delegacion", "meta", "servicio", "punto_validado")
    search_fields = ("codigo", "servicio", "contacto", "codigo_verificador", "funcionario__nombre")
    list_filter = ("punto_validado", "delegacion", "funcionario")
    autocomplete_fields = ("funcionario", "delegacion", "meta")
    date_hierarchy = "fecha_actividad"


@admin.register(Compromiso)
class CompromisoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descripcion", "vecino", "funcionario", "delegacion", "fecha_compromiso", "estado")
    search_fields = ("codigo", "descripcion", "vecino__nombre", "funcionario__nombre")
    list_filter = ("estado", "delegacion", "funcionario")
    autocomplete_fields = ("vecino", "funcionario", "delegacion")
    date_hierarchy = "fecha_compromiso"


@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "fecha", "hora", "titulo", "tipo", "delegacion", "responsable", "lugar")
    search_fields = ("codigo", "titulo", "lugar", "responsable__nombre")
    list_filter = ("tipo", "delegacion")
    autocomplete_fields = ("delegacion", "responsable")
    date_hierarchy = "fecha"


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = ("periodo", "delegacion_piloto", "fecha_inicio", "fecha_termino", "dias_totales",
                    "meta_cumplimiento_tubo")
    search_fields = ("periodo", "descripcion")
    list_filter = ("delegacion_piloto",)
    autocomplete_fields = ("delegacion_piloto",)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "fecha", "titulo", "tipo", "enlace")
    search_fields = ("codigo", "titulo", "mensaje")
    list_filter = ("tipo",)
    date_hierarchy = "fecha"

from control_gestion.models import Ausencia, OrganizacionComunitaria
admin.site.register(Ausencia)
admin.site.register(OrganizacionComunitaria)
