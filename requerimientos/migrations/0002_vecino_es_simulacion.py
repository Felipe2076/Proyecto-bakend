"""Marca de simulación en el vecino y ejemplo de RUT ficticio (parte de V017)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requerimientos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vecino",
            name="es_simulacion",
            field=models.BooleanField(default=False, verbose_name="dato de simulación"),
        ),
        migrations.AlterField(
            model_name="vecino",
            name="rut",
            field=models.CharField(
                blank=True,
                help_text="Normalizado o con puntos. Ejemplo: 33.500.001-3. Vacío si no se registró.",
                max_length=12,
                null=True,
                unique=True,
                verbose_name="RUT",
            ),
        ),
    ]
