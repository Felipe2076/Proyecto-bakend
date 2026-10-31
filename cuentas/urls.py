from django.urls import path

from . import views, grupos
from control_gestion import reportes

urlpatterns = [
    path('administracion/grupos/',grupos.grupos_view,name='admin_grupos'),
    path('administracion/grupos/<int:rol_id>/',grupos.grupos_view,name='admin_grupo'),
    path("administracion/usuarios/excel/", reportes.exportar_usuarios, name="exportar_usuarios_excel"),
    path("activar/", views.activar_cuenta_view, name="activar_cuenta"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("recuperar/", views.recuperar_contrasena_view, name="recuperar_contrasena"),
    path('recuperar/enlace/<uidb64>/<token>/', views.RestablecerEnlaceView.as_view(), name='recuperar_enlace'),
    path("recuperar/codigo/", views.validar_codigo_view, name="validar_codigo"),
    path("recuperar/nueva/", views.nueva_contrasena_view, name="nueva_contrasena"),
    path("administracion/usuarios/", views.administracion_usuarios_view, name="admin_usuarios"),
    path("administracion/cargos/", views.administracion_cargos_view, name="admin_cargos"),
    path("administracion/parametros/", views.administracion_parametros_view, name="admin_parametros"),
]
