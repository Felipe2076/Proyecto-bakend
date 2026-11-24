"""Rol «Superusuario» (ve todas las delegaciones) y administradores acotados a su delegación.

Se ejecuta DENTRO del contenedor de la aplicación, DESPUÉS de desplegar el código nuevo, con «shell -c»:

    docker compose exec -T app python manage.py shell -c "$(cat superusuario.py)"                                  (solo revisa)
    docker compose exec -T -e MODO=aplicar -e CUENTA=<RUT o código USR-xxx> app python manage.py shell -c "..."    (aplica)
    docker compose exec -T -e MODO=quitar -e CUENTA=<la misma> -e ROL_ANTERIOR=<rol> -e RESTAURAR='...' app python manage.py shell -c "..."

«aplicar»: crea el rol y el grupo «SIGED: superusuario» (todos los permisos), asigna la CUENTA a ese rol y le quita al
grupo «SIGED: administrador» los permisos de crear, modificar y eliminar sobre la configuración global (delegaciones,
roles, metas, catálogos, períodos, cargos); la consulta se conserva. No toca claves, MySQL ni otras cuentas.
Imprime la línea para deshacerlo. La cuenta debe cerrar sesión y volver a entrar para que el cambio de rol rija.
"""
import os

from django.contrib.auth.models import Permission
from django.db import transaction

from core.validaciones import rut_canonico
from cuentas.models import Rol, Usuario
from cuentas.perfiles import MODELOS_GLOBALES, asegurar_grupo, permisos_iniciales, sincronizar_usuario

MODO = os.environ.get('MODO', 'revisar')
CUENTA = os.environ.get('CUENTA', '').strip()
ROL_ANTERIOR = os.environ.get('ROL_ANTERIOR', '').strip()
RESTAURAR = {x.strip() for x in os.environ.get('RESTAURAR', '').split(',') if x.strip()}
assert MODO in ('revisar', 'aplicar', 'quitar'), f'MODO desconocido: {MODO}'
assert MODO == 'revisar' or CUENTA, 'Indique CUENTA (RUT o código de usuario).'
assert MODO != 'quitar' or ROL_ANTERIOR, 'Para quitar indique ROL_ANTERIOR (lo imprime «aplicar»).'


def buscar_cuenta(texto):
    rut = rut_canonico(texto)
    qs = Usuario.objects.select_related('rol', 'delegacion')
    return qs.filter(codigo=texto).first() or (qs.filter(username=rut).first() if rut else None)


print(f'MODO = {MODO}')
admin_rol = Rol.objects.filter(codigo='administrador').select_related('grupo').first()
super_rol = Rol.objects.filter(codigo='superusuario').first()
print('Rol «superusuario»:', 'ya existe' if super_rol else 'NO existe (se crearía)')

print('\nCuentas con rol administrador hoy:')
for u in Usuario.objects.filter(rol__codigo='administrador').select_related('delegacion').order_by('codigo'):
    print(f'   {u.codigo:8} {u.nombre[:34]:34} {u.delegacion.nombre if u.delegacion_id else "SIN DELEGACIÓN (quedaría sin ver nada)"}')

globales = list(Permission.objects.filter(
    content_type__model__in=MODELOS_GLOBALES, content_type__app_label__in=('cuentas', 'requerimientos', 'control_gestion'),
    codename__regex=r'^(add|change|delete)_').select_related('content_type'))
con_permiso = [p for p in globales if admin_rol and admin_rol.grupo and admin_rol.grupo.permissions.filter(pk=p.pk).exists()]
print(f'\nPermisos globales de escritura que hoy tiene el grupo administrador: {len(con_permiso)}')

objetivo = buscar_cuenta(CUENTA) if CUENTA else None
if CUENTA:
    print('Cuenta indicada:', f'{objetivo.codigo} · {objetivo.nombre} · rol {objetivo.rol.codigo} · '
          f'{objetivo.delegacion.nombre if objetivo.delegacion_id else "sin delegación"}' if objetivo else 'NO ENCONTRADA')

if MODO == 'aplicar':
    assert objetivo is not None, 'No encontré la cuenta indicada.'
    with transaction.atomic():
        rol, _ = Rol.objects.get_or_create(codigo='superusuario', defaults={
            'nombre': 'Superusuario', 'descripcion': 'Ve y administra todas las delegaciones'})
        grupo = asegurar_grupo(rol)
        grupo.permissions.set(permisos_iniciales('superusuario'))
        quitados = []
        if admin_rol and admin_rol.grupo:
            for p in con_permiso:
                admin_rol.grupo.permissions.remove(p)
                quitados.append(f'{p.content_type.app_label}.{p.codename}')
        anterior = objetivo.rol.codigo
        objetivo.rol = rol
        objetivo.save(update_fields=['rol'])
        sincronizar_usuario(objetivo)
    print(f'\nHecho: {objetivo.codigo} ahora es superusuario ({grupo.permissions.count()} permisos). Quitados al administrador: {len(quitados)}.')
    print('Para deshacer:  ROL_ANTERIOR=' + anterior + '  RESTAURAR=' + repr(','.join(quitados)))
elif MODO == 'quitar':
    assert objetivo is not None, 'No encontré la cuenta indicada.'
    with transaction.atomic():
        anterior = Rol.objects.get(codigo=ROL_ANTERIOR)
        objetivo.rol = anterior
        objetivo.save(update_fields=['rol'])
        sincronizar_usuario(objetivo)
        if admin_rol and admin_rol.grupo:
            for nombre in RESTAURAR:
                app, cod = nombre.split('.')
                admin_rol.grupo.permissions.add(Permission.objects.get(content_type__app_label=app, codename=cod))
    print(f'\nDeshecho: {objetivo.codigo} vuelve a {ROL_ANTERIOR}; permisos restaurados: {len(RESTAURAR)}. (El rol superusuario queda sin uso.)')
else:
    print('\nSolo revisión: no se cambió nada.')
