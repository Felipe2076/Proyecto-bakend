from django.db import migrations

def asignar(apps,schema_editor):
    Rol=apps.get_model('cuentas','Rol');Permission=apps.get_model('auth','Permission');ContentType=apps.get_model('contenttypes','ContentType')
    for model in ('ausencia','organizacioncomunitaria','medicion'):
        ct,_=ContentType.objects.get_or_create(app_label='control_gestion',model=model)
        for accion in ('view','add','change','delete'):
            permiso,_=Permission.objects.get_or_create(content_type=ct,codename=accion+'_'+model,defaults={'name':accion+' '+model})
            for rol in Rol.objects.exclude(grupo__isnull=True):
                permitido=rol.codigo=='administrador' or (rol.codigo=='jefatura' and ((model=='ausencia' and accion in ('view','add','change')) or (model in ('organizacioncomunitaria','medicion') and accion=='view'))) or (rol.codigo=='funcionario' and model=='organizacioncomunitaria' and accion=='view')
                if permitido:rol.grupo.permissions.add(permiso)

class Migration(migrations.Migration):
    dependencies=[('control_gestion','0007_gestion_trimestral_organizaciones'),('cuentas','0007_grupos_municipales')]
    operations=[migrations.RunPython(asignar,migrations.RunPython.noop)]
