from django.urls import path
from . import views, views_extra

urlpatterns = [
    path("", views.dashboard_cuellos_botella_view, name="dashboard"),
    path("dashboard/", views.dashboard_cuellos_botella_view),
    path("kanban/", views.kanban_view, name="kanban"),
    path("areas/", views.areas_soporte_view, name="areas_soporte"),
    path("semaforo-sgr/", views.semaforo_sgr_view, name="semaforo_sgr"),
    path("tubo-trabajo/", views.tubo_trabajo_view, name="tubo_trabajo"),
    path("funcionarios/", views.funcionarios_view, name="funcionarios"),
    path(
        "funcionarios/<str:id_funcionario>/",
        views.detalle_funcionario_view,
        name="detalle_funcionario",
    ),
    path("resumen/", views.resumen_delegacion_view, name="resumen_delegacion"),
    path("agenda/", views_extra.agenda_view, name="agenda"),
    path("actividades/", views_extra.actividades_diarias_view, name="actividades_diarias"),
    path("compromisos/nuevo/", views_extra.compromiso_form_view, name="compromiso_nuevo"),
    path(
        "compromisos/<str:id_compromiso>/editar/",
        views_extra.compromiso_form_view,
        name="compromiso_editar",
    ),
    path(
        "compromisos/<str:id_compromiso>/eliminar/",
        views_extra.compromiso_eliminar_view,
        name="compromiso_eliminar",
    ),
    path("notificaciones/", views_extra.notificaciones_view, name="notificaciones"),
]
