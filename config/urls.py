from django.contrib import admin
from django.urls import include, path

from config.views_publicas import creditos_view, portada_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # Portada pública: anónimo ve la landing; con sesión se muestra el tablero (inicio_view).
    path("", portada_view, name="inicio"),
    path("creditos/", creditos_view, name="creditos"),
    path("", include("cuentas.urls")),
    path("", include("requerimientos.urls")),
    path("control/", include("control_gestion.urls")),
]
