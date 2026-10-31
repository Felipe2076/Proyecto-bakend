from django.db import migrations
import re

def completar(apps,schema_editor):
    using=schema_editor.connection.alias
    Secuencia=apps.get_model('cuentas','SecuenciaCodigo')
    modelos=[('cuentas','Usuario','USR-'),('requerimientos','Requerimiento','TK-'),
        ('requerimientos','AreaSoporte','AREA-'),('cuentas','Cargo','CARGO-'),('cuentas','Funcionario','FUN-'),
        ('control_gestion','Meta','META-'),('control_gestion','ItemFuncionario','ITEM-'),
        ('control_gestion','Medicion','MED-'),('control_gestion','Actividad','ACT-'),
        ('control_gestion','Compromiso','TUB-'),('control_gestion','EventoAgenda','AG-'),
        ('control_gestion','Notificacion','NTF-')]
    for app,name,prefijo in modelos:
        Model=apps.get_model(app,name)
        patron=re.compile(rf'^{re.escape(prefijo)}(\d+)$')
        seq,_=Secuencia.objects.using(using).get_or_create(clave=f'{Model._meta.label_lower}.codigo.{prefijo}')
        maximo=seq.ultimo
        pendientes=[]
        for pk,codigo in Model.objects.using(using).order_by('pk').values_list('pk','codigo'):
            if not codigo:
                pendientes.append(pk)
            match=patron.fullmatch(str(codigo or ''))
            if match: maximo=max(maximo,int(match.group(1)))
        for pk in pendientes:
            maximo+=1
            Model.objects.using(using).filter(pk=pk).update(codigo=f'{prefijo}{maximo:03d}')
        seq.ultimo=maximo
        seq.save(using=using,update_fields=['ultimo'])

class Migration(migrations.Migration):
    dependencies=[('cuentas','0005_secuenciacodigo'),('control_gestion','0002_itemfuncionario_codigo_medicion_codigo_meta_codigo')]
    operations=[migrations.RunPython(completar,migrations.RunPython.noop)]
