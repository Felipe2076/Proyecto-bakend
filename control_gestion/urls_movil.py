from django.urls import path
from control_gestion import api_movil as a
from control_gestion import api_sincronizacion as s
from control_gestion import api_cuenta as c

urlpatterns=[
    path('sesion/',a.login),path('sesion/cerrar/',a.logout),path('sesion/renovar/',a.renovar),path('panel/',a.panel),
    path('sesiones/',s.sesiones),path('sesiones/<int:pk>/',s.cerrar_sesion),
    path('perfil/',s.perfil),path('perfil/foto/',s.foto_propia),path('usuarios/',s.usuarios),
    path('usuarios/<str:codigo>/foto/',s.foto_usuario),path('catalogos/',s.catalogos),
    path('organizaciones/',s.organizaciones),path('organizaciones/<str:codigo>/',s.organizacion),
    path('sync/',s.sincronizar),
    path('recuperar/',c.recuperar),path('recuperar/verificar/',c.verificar),path('recuperar/nueva/',c.nueva_clave),
    path('mi-trabajo/',c.mi_trabajo),path('compromisos/<str:codigo>/evidencias/',c.subir_evidencia),
    path('evidencias/<int:pk>/',c.ver_evidencia_compromiso),
    path('actividades/',a.actividades),path('actividades/<str:codigo>/',a.detalle_actividad),
    path('actividades/<str:codigo>/evidencia/',a.evidencia),path('actividades/<str:codigo>/revision/',a.revision),
    path('compromisos/',a.compromisos),path('compromisos/<str:codigo>/estado/',a.cambiar_compromiso),
    path('excel/',a.excel),
]
