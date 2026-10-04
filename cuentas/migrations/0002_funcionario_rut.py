"""Columnas aditivas del RUT del trabajador (equivalente a V017).

``rut``, nombres y apellidos quedan anulables hasta que la migración 0003
confirme que cada fila tiene identidad de simulación.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="funcionario",
            name="rut",
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name="RUT"),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="nombres",
            field=models.CharField(blank=True, max_length=60, null=True),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="apellido_paterno",
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name="apellido paterno"),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="apellido_materno",
            field=models.CharField(blank=True, max_length=60, null=True, verbose_name="apellido materno"),
        ),
        migrations.AddField(
            model_name="funcionario",
            name="es_simulacion",
            field=models.BooleanField(default=False, verbose_name="dato de simulación"),
        ),
        migrations.AddIndex(
            model_name="funcionario",
            index=models.Index(
                fields=["delegacion", "apellido_paterno", "nombres"],
                name="idx_fun_deleg_apellido",
            ),
        ),
    ]
