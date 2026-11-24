from django.db import migrations


def preparar_catalogo(apps, schema_editor):
    alias = schema_editor.connection.alias
    Organizacion = apps.get_model('control_gestion', 'OrganizacionComunitaria')
    Territorio = apps.get_model('control_gestion', 'TerritorioDelegacion')
    pares = Organizacion.objects.using(alias).filter(delegacion__isnull=False).exclude(territorio='').values_list(
        'delegacion_id', 'territorio',
    ).order_by().distinct()
    for delegacion, nombre in pares.iterator():
        nombre = nombre.strip()
        if nombre:
            Territorio.objects.using(alias).get_or_create(delegacion_id=delegacion, nombre=nombre)

    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Rol = apps.get_model('cuentas', 'Rol')
    ct, _ = ContentType.objects.using(alias).get_or_create(app_label='control_gestion', model='territoriodelegacion')
    permisos = []
    for accion in ('view', 'add', 'change', 'delete'):
        permiso, _ = Permission.objects.using(alias).get_or_create(
            content_type=ct, codename=f'{accion}_territoriodelegacion',
            defaults={'name': f'Can {accion} territorio de delegación'},
        )
        permisos.append(permiso)
    rol = Rol.objects.using(alias).filter(codigo='administrador', grupo__isnull=False).first()
    if rol:
        rol.grupo.permissions.add(*permisos)


class Migration(migrations.Migration):
    dependencies = [('control_gestion', '0011_directiva_y_territorios')]
    operations = [migrations.RunPython(preparar_catalogo, migrations.RunPython.noop)]
