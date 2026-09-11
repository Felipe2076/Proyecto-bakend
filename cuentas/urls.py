from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("administracion/usuarios/", views.administracion_usuarios_view, name="admin_usuarios"),
    path("administracion/cargos/", views.administracion_cargos_view, name="admin_cargos"),
    path("administracion/parametros/", views.administracion_parametros_view, name="admin_parametros"),
]
