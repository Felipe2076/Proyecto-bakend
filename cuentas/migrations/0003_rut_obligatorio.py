"""RUT y funcionario obligatorios (equivalente a V018), después de simular identidades.

El CHECK de formato ``REGEXP_LIKE`` vive en ``sql/migraciones/V018`` porque ese
predicado es de MySQL 8. La aplicación valida el dígito verificador en Python
y en JavaScript en todos los motores, incluida la suite con SQLite.
"""

import django.db.models.deletion
from django.db import migrations, models

from cuentas.simulacion_bd import aplicar

_TABLA = "cuentas_funcionario"
_UNICO = "uq_funcionario_rut"
_CHECK = "ck_funcionario_rut"
_CHECK_SQL = (
    "ALTER TABLE cuentas_funcionario "
    "ADD CONSTRAINT ck_funcionario_rut "
    "CHECK (REGEXP_LIKE(rut, '^[0-9]{7,8}-[0-9K]$', 'c'))"
)


def _existe(cursor, vendor, nombre):
    if vendor == "mysql":
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND CONSTRAINT_NAME = %s
            UNION
            SELECT 1
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
            LIMIT 1
            """,
            [_TABLA, nombre, _TABLA, nombre],
        )
        return cursor.fetchone() is not None
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE tbl_name = %s AND name = %s LIMIT 1",
        [_TABLA, nombre],
    )
    return cursor.fetchone() is not None


def _restricciones(apps, schema_editor):
    """Único en todos los motores y CHECK solo en MySQL.

    ``atomic=False``: en MySQL el DDL no puede ir dentro de la transacción
    con la que Django envuelve cada ``RunPython``. Si el paso anterior ya
    quedó aplicado (MySQL no revierte DDL), volver a migrar no vuelve a
    crear la restricción.
    """
    connection = schema_editor.connection
    Funcionario = apps.get_model("cuentas", "Funcionario")
    with connection.cursor() as cursor:
        hay_unico = _existe(cursor, connection.vendor, _UNICO)
        hay_check = connection.vendor == "mysql" and _existe(cursor, connection.vendor, _CHECK)
    if not hay_unico:
        schema_editor.add_constraint(
            Funcionario,
            models.UniqueConstraint(fields=("rut",), name=_UNICO),
        )
    if hay_check is False and connection.vendor == "mysql":
        schema_editor.execute(_CHECK_SQL)


def _quitar_restricciones(apps, schema_editor):
    connection = schema_editor.connection
    Funcionario = apps.get_model("cuentas", "Funcionario")
    with connection.cursor() as cursor:
        hay_check = connection.vendor == "mysql" and _existe(cursor, connection.vendor, _CHECK)
        hay_unico = _existe(cursor, connection.vendor, _UNICO)
    if hay_check:
        schema_editor.execute("ALTER TABLE cuentas_funcionario DROP CHECK ck_funcionario_rut")
    if hay_unico:
        schema_editor.remove_constraint(
            Funcionario,
            models.UniqueConstraint(fields=("rut",), name=_UNICO),
        )


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
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name="funcionario",
                    constraint=models.UniqueConstraint(fields=("rut",), name="uq_funcionario_rut"),
                ),
            ],
            database_operations=[
                migrations.RunPython(_restricciones, _quitar_restricciones, atomic=False),
            ],
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
    ]
