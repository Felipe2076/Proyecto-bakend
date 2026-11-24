"""Permisos para que jefaturas y funcionarios usen las atenciones en el Tubo y la agenda de organizaciones.

Se ejecuta DENTRO del contenedor de la aplicación (el script se pasa con «shell -c», no por entrada estándar):

    docker compose exec -T app python manage.py shell -c "$(cat permisos_atenciones_agenda.py)"                       (solo revisa)
    docker compose exec -T -e MODO=aplicar app python manage.py shell -c "$(cat permisos_atenciones_agenda.py)"       (agrega)
    docker compose exec -T -e MODO=quitar -e QUITAR_SOLO='rol:app.permiso,...' app python manage.py shell -c "..."    (deshace)

Solo AGREGA permisos puntuales a los grupos «SIGED: jefatura» y «SIGED: funcionario». No toca usuarios, claves,
roles, el administrador ni los permisos de MySQL. Las actividades quedan acotadas a la delegación de cada persona
por el propio sistema (ámbito por delegación). «aplicar» imprime la línea QUITAR_SOLO con lo que realmente agregó;
«quitar» retira únicamente eso (así nunca retira permisos que el grupo ya tenía antes).
"""
import os

from django.contrib.auth.models import Permission
from django.db import transaction

from cuentas.models import Rol

MODO = os.environ.get('MODO', 'revisar')
QUITAR_SOLO = {x.strip() for x in os.environ.get('QUITAR_SOLO', '').split(',') if x.strip()}
PLAN = {
    # Ver y mover atenciones en el Tubo; registrar y modificar actividades de organizaciones (no eliminar).
    'jefatura': ['requerimientos.view_atencion', 'requerimientos.change_atencion',
                 'control_gestion.view_eventoagenda', 'control_gestion.add_eventoagenda',
                 'control_gestion.change_eventoagenda'],
    'funcionario': ['requerimientos.view_atencion', 'requerimientos.change_atencion',
                    'control_gestion.view_eventoagenda', 'control_gestion.add_eventoagenda',
                    'control_gestion.change_eventoagenda'],
}
assert MODO in ('revisar', 'aplicar', 'quitar'), f'MODO desconocido: {MODO}'
assert MODO != 'quitar' or QUITAR_SOLO, 'Para quitar indique QUITAR_SOLO (lo imprime «aplicar»).'

print(f'MODO = {MODO}')
print('Roles y grupos existentes:', [(r.codigo, r.grupo.name if r.grupo_id else None) for r in Rol.objects.select_related('grupo')])
agregados = []
with transaction.atomic():
    for codigo, nombres in PLAN.items():
        rol = Rol.objects.select_related('grupo').filter(codigo=codigo).first()
        if rol is None or rol.grupo is None:
            print(f'\n[{codigo}] no existe el rol o no tiene grupo: se omite')
            continue
        grupo = rol.grupo
        print(f'\n[{codigo}] grupo «{grupo.name}»: {grupo.permissions.count()} permisos hoy')
        for nombre in nombres:
            app, cod = nombre.split('.')
            permiso = Permission.objects.get(content_type__app_label=app, codename=cod)
            tiene = grupo.permissions.filter(pk=permiso.pk).exists()
            if MODO == 'revisar':
                print(f'   {"ya lo tiene " if tiene else "AGREGARÍA   "} {nombre}')
            elif MODO == 'aplicar':
                if not tiene:
                    grupo.permissions.add(permiso)
                    agregados.append(f'{codigo}:{nombre}')
                print(f'   {"ya lo tenía " if tiene else "AGREGADO    "} {nombre}')
            else:
                if tiene and f'{codigo}:{nombre}' in QUITAR_SOLO:
                    grupo.permissions.remove(permiso)
                    print(f'   RETIRADO     {nombre}')
                else:
                    print(f'   se deja      {nombre}')
        print(f'   -> {grupo.permissions.count()} permisos ahora')
if MODO == 'aplicar':
    print('\nPara deshacer exactamente esto:  QUITAR_SOLO=' + repr(','.join(agregados)))
print('\nSolo revisión: no se cambió nada.' if MODO == 'revisar' else '\nListo.')
