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
