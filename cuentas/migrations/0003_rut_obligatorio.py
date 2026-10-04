"""RUT y funcionario obligatorios (equivalente a V018), después de simular identidades.

El CHECK de formato ``REGEXP_LIKE`` vive en ``sql/migraciones/V018`` porque ese
predicado es de MySQL 8. La aplicación valida el dígito verificador en Python
y en JavaScript en todos los motores, incluida la suite con SQLite.
"""

import django.db.models.deletion
from django.db import migrations, models

from cuentas.simulacion_bd import aplicar


def _check_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(
        "ALTER TABLE cuentas_funcionario "
        "ADD CONSTRAINT ck_funcionario_rut "
        "CHECK (REGEXP_LIKE(rut, '^[0-9]{7,8}-[0-9K]$', 'c'))"
    )


def _drop_check_mysql(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute("ALTER TABLE cuentas_funcionario DROP CHECK ck_funcionario_rut")


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_funcionario_rut"),
        ("requerimientos", "0002_vecino_es_simulacion"),
    ]

    operations = [
        migrations.RunPython(aplicar, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="funcionario",
            name="rut",
            field=models.CharField(
                help_text="Normalizado, sin puntos. Ejemplo visible: 33.100.001-9.",
                max_length=10,
                verbose_name="RUT",
            ),
        ),
        migrations.AlterField(
            model_name="funcionario",
            name="nombres",
            field=models.CharField(max_length=60),
        ),
        migrations.AlterField(
            model_name="funcionario",
            name="apellido_paterno",
            field=models.CharField(max_length=60, verbose_name="apellido paterno"),
        ),
        migrations.AddConstraint(
            model_name="funcionario",
            constraint=models.UniqueConstraint(fields=("rut",), name="uq_funcionario_rut"),
        ),
        migrations.AlterField(
            model_name="usuario",
            name="funcionario",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="usuario",
                to="cuentas.funcionario",
            ),
        ),
        migrations.RunPython(_check_mysql, _drop_check_mysql),
    ]
