from django.db import migrations

def crear_grupos(apps,schema_editor):
    from cuentas.perfiles import preparar_perfiles
    preparar_perfiles(apps,schema_editor)

class Migration(migrations.Migration):
    dependencies=[('cuentas','0006_alter_rol_options_rol_grupo'),('auth','0012_alter_user_first_name_max_length'),('control_gestion','0003_codigos_existentes')]
    operations=[migrations.RunPython(crear_grupos,migrations.RunPython.noop)]
