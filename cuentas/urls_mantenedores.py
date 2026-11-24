from django.urls import path

from cuentas.mantenedores import MANTENEDORES

from control_gestion.territorios import buscar_organizaciones, opciones_territorios

urlpatterns = [
    path('organizaciones/territorios/', opciones_territorios, name='territorios_delegacion'),
    path('organizaciones/buscar/', buscar_organizaciones, name='buscar_organizaciones'),
]
for mantenedor in MANTENEDORES:
    urlpatterns += [
        path(f"{mantenedor.ruta}/", mantenedor.vista_lista, name=mantenedor.nombre),
        path(f"{mantenedor.ruta}/nuevo/", mantenedor.vista_crear, name=f"{mantenedor.nombre}_crear"),
        path(
            f"{mantenedor.ruta}/<int:pk>/editar/",
            mantenedor.vista_editar,
            name=f"{mantenedor.nombre}_editar",
        ),
        path(
            f"{mantenedor.ruta}/<int:pk>/eliminar/",
            mantenedor.vista_eliminar,
            name=f"{mantenedor.nombre}_eliminar",
        ),
    ]
