from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("recuperar/", views.recuperar_contrasena_view, name="recuperar_contrasena"),
    path("recuperar/codigo/", views.validar_codigo_view, name="validar_codigo"),
    path("recuperar/nueva/", views.nueva_contrasena_view, name="nueva_contrasena"),
    path("administracion/usuarios/", views.administracion_usuarios_view, name="admin_usuarios"),
    path("administracion/cargos/", views.administracion_cargos_view, name="admin_cargos"),
    path("administracion/parametros/", views.administracion_parametros_view, name="admin_parametros"),
]
