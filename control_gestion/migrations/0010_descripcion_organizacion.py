from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('control_gestion', '0009_revision_y_api_movil')]

    operations = [
        migrations.AddField(
            model_name='organizacioncomunitaria',
            name='descripcion',
            field=models.TextField('actividades y descripción', blank=True, null=True, max_length=4000),
        ),
    ]
