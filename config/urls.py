from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Sitio público (portada y secciones espejo de laserena.cl). Con sesión, "/" muestra el tablero.
    path("", include("publico.urls")),
    path("", include("cuentas.urls")),
    path("", include("requerimientos.urls")),
    path("control/", include("control_gestion.urls")),
]
