from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Entrada al login. Con sesión, "/" muestra el tablero; se conservan las secciones públicas.
    path("", include("publico.urls")),
    path("mantenedores/", include("cuentas.urls_mantenedores")),
    path("", include("cuentas.urls")),
    path("", include("requerimientos.urls")),
    path("control/", include("control_gestion.urls")),
]
