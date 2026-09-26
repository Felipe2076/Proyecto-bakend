from django.urls import path

from cuentas.mantenedores import MANTENEDORES

urlpatterns = []
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
