from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio_view, name="inicio"),
    path("lista/", views.lista_requerimientos_view, name="lista_requerimientos"),
    path("requerimientos/", views.lista_requerimientos_view),
    path("requerimientos/nuevo/", views.nuevo_requerimiento_view, name="nuevo_requerimiento"),
    path(
        "requerimientos/<str:ticket_id>/",
        views.detalle_requerimiento_view,
        name="detalle_requerimiento",
    ),
    path("encuestas/", views.encuestas_view, name="encuestas"),
]
