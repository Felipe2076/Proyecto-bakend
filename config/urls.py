from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("requerimientos.urls")),
    path("control/", include("control_gestion.urls")),
]
