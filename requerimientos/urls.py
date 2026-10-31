from django.urls import path
from . import views, listado

urlpatterns = [
    path("lista/exportar/", listado.exportar, name="exportar_tickets_excel"),
    path("", views.inicio_view, name="inicio"),
    path("lista/", listado.lista, name="lista_requerimientos"),
    path("requerimientos/", listado.lista),
    path("requerimientos/nuevo/", views.nuevo_requerimiento_view, name="nuevo_requerimiento"),
    path(
        "requerimientos/<str:ticket_id>/",
        views.detalle_requerimiento_view,
        name="detalle_requerimiento",
    ),
    path("encuestas/", views.encuestas_view, name="encuestas"),
]
