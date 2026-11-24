from django.db import migrations, models


class Migration(migrations.Migration):
    """Solo agrega columnas que aceptan NULL (compatible con el despliegue aditivo)."""

    dependencies = [
        ('requerimientos', '0003_fecha_resolucion'),
    ]

    operations = [
        migrations.AddField(
            model_name='vecino',
            name='es_extranjero',
            field=models.BooleanField(blank=True, null=True, verbose_name='¿es extranjero/a?'),
        ),
        migrations.AddField(
            model_name='vecino',
            name='nacionalidad',
            field=models.CharField(blank=True, help_text='Solo si es extranjero/a. Ej.: Venezuela, Perú, Haití.', max_length=60, null=True, verbose_name='país de origen'),
        ),
    ]
