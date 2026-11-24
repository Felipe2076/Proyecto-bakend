from django.contrib import admin
from django.urls import include, path

from control_gestion.evidencias import ver_evidencia
from core.seguridad import salud

urlpatterns = [
    path("salud/", salud, name="salud"),
    path("api/v1/", include("control_gestion.urls_movil")),
    path("admin/actividad-evidencia/<str:codigo>/", ver_evidencia, name="admin_actividad_evidencia"),
    path("admin/", admin.site.urls),
    # Entrada al login. Con sesión, "/" muestra el tablero; se conservan las secciones públicas.
    path("", include("publico.urls")),
    path("mantenedores/", include("cuentas.urls_mantenedores")),
    path("", include("cuentas.urls")),
    path("", include("requerimientos.urls")),
    path("control/", include("control_gestion.urls")),
]
