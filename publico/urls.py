from django.urls import path
from django.views.generic import RedirectView

from publico import views

# Rutas públicas: deben coincidir con RUTAS_PUBLICAS (config/middleware.py).
urlpatterns = [
    path("", views.portada_view, name="inicio"),
    path("municipio/", views.municipio_view, name="publico_municipio"),
    path("servicios/", views.servicios_view, name="publico_servicios"),
    path("tramites/", views.tramites_view, name="publico_tramites"),
    path("delegaciones/", views.delegaciones_view, name="publico_delegaciones"),
    path("noticias/", views.noticias_view, name="publico_noticias"),
    path("transparencia/", views.transparencia_view, name="publico_transparencia"),
    path("contacto/", views.contacto_view, name="publico_contacto"),
    # La antigua página de créditos se eliminó: redirección permanente a la portada.
    path("creditos/", RedirectView.as_view(url="/", permanent=True)),
]
