"""Secuencia migrate → importar_json sobre una base vacía y sobre una con filas viejas."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

RAIZ = Path(settings.BASE_DIR)
B7 = RAIZ / "sql" / "verificacion" / "B7__rut_simulacion.sql"


def _entorno(ruta):
    entorno = os.environ.copy()
    entorno.update(
        {
            "SIGED_DB": "sqlite",
            "SIGED_SQLITE_PATH": str(ruta),
            "SECRET_KEY": "clave-de-prueba",
            "DEBUG": "False",
            "SIGED_DEMO_PASSWORD": "clave-de-prueba",
            "SIGED_CODE_HMAC_KEY": "clave-de-prueba",
        }
    )
    return entorno


def _manage(entorno, *args):
    resultado = subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=RAIZ,
        env=entorno,
        check=False,
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        cola = ((resultado.stdout or "") + "\n" + (resultado.stderr or ""))[-8000:]
        raise AssertionError(cola)
    return resultado


SEMILLA = r"""
from django.db import connection
from cuentas.models import Cargo, Delegacion, Rol
from cuentas.vocabulario import DELEGACIONES_OFICIALES
for nombre in DELEGACIONES_OFICIALES:
    Delegacion.objects.get_or_create(nombre=nombre, defaults={"comuna": "La Serena"})
for nombre in ("Administrador del sistema", "Delegada Territorial", "Gestor Social", "Apoyo Administrativo"):
    Cargo.objects.get_or_create(nombre=nombre)
for codigo, nombre in (
    ("administrador", "Administrador"),
    ("jefatura", "Jefatura"),
    ("funcionario", "Funcionario"),
    ("ventanilla", "Ventanilla"),
):
    Rol.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
cargo = Cargo.objects.get(nombre="Gestor Social")
centro = Delegacion.objects.get(nombre="Delegación Centro")
rol = Rol.objects.get(codigo="administrador")
with connection.cursor() as cursor:
    for codigo in ("FUN-001", "FUN-011", "FUN-DEMO-ADMIN"):
        cursor.execute(
            "INSERT INTO cuentas_funcionario (codigo, nombre, cargo_id, delegacion_id, estado, es_simulacion) "
            "VALUES (%s, %s, %s, %s, 'activo', 0)",
            [codigo, "Persona " + codigo, cargo.id, centro.id],
        )
    cursor.execute("SELECT id FROM cuentas_funcionario WHERE codigo=%s", ["FUN-DEMO-ADMIN"])
    fun_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO cuentas_usuario (codigo, username, nombre, correo, estado, creado, rol_id, cargo_id, "
        "delegacion_id, funcionario_id) VALUES (%s,%s,%s,%s,'activo','2026-01-01 00:00:00',%s,%s,%s,%s)",
        ["USR-DEMO", "demo.admin", "Demo", "fun-011@siged.test", rol.id, cargo.id, centro.id, fun_id],
    )
    cursor.execute(
        "INSERT INTO requerimientos_vecino (nombre, rut, direccion, telefono, correo, territorio, estado, es_simulacion, delegacion_id) "
        "VALUES (%s,%s,'','','','','activo',0,%s)",
        ["Vecino legado", "11111111-1", centro.id],
    )
print("semilla-ok")
"""

VERIFICACION = r"""
import os
from django.conf import settings
from core.validaciones import cuerpo_en_rango_ficticio
from cuentas.models import Funcionario, Rol, Usuario
from cuentas.vocabulario import DELEGACIONES_OFICIALES
from requerimientos.models import Vecino

def fuera(rut):
    return not rut or not cuerpo_en_rango_ficticio(rut)

fun = Funcionario.objects.get(codigo="FUN-011")
assert fun.rut == "33100011-6", fun.rut
assert Funcionario.objects.filter(rut="33100011-6").count() == 1
if os.environ.get("COMPROBAR_DEMO") == "1":
    demo = Funcionario.objects.get(codigo="FUN-DEMO-ADMIN")
    assert demo.rut != "33100011-6", demo.rut
    assert not fuera(demo.rut), demo.rut
    assert not Vecino.objects.filter(rut="11111111-1").exists()
mal_fun = [f.codigo for f in Funcionario.objects.all() if fuera(f.rut) or not f.es_simulacion]
mal_vec = [v.pk for v in Vecino.objects.all() if fuera(v.rut) or not v.es_simulacion]
mal_usr = [
    u.codigo for u in Usuario.objects.all()
    if fuera(u.username) or not (u.correo or "").endswith("@siged.test")
]
assert mal_fun == [], mal_fun
assert mal_vec == [], mal_vec
assert mal_usr == [], mal_usr
assert Usuario.objects.filter(correo="fun-011@siged.test").count() == 1
for rol in Rol.objects.all():
    for nombre in DELEGACIONES_OFICIALES:
        assert Usuario.objects.filter(rol=rol, funcionario__delegacion__nombre=nombre).exists(), (rol.codigo, nombre)
import importlib
from django.apps import apps
from django.db import connection
mod = importlib.import_module("cuentas.migrations.0003_rut_obligatorio")
with connection.constraint_checks_disabled():
    with connection.schema_editor() as editor:
        mod._restricciones(apps, editor)
        mod._restricciones(apps, editor)
print("verificacion-ok", Funcionario.objects.count(), Usuario.objects.count(), Vecino.objects.count())
"""


class ConsultasB7Tests(SimpleTestCase):
    def test_el_archivo_cubre_las_tres_tablas_sin_datos_reales(self):
        texto = B7.read_text(encoding="utf-8")
        self.assertIn("cuentas_funcionario", texto)
        self.assertIn("cuentas_usuario", texto)
        self.assertIn("requerimientos_vecino", texto)
        self.assertIn("NOT BETWEEN 33000000 AND 33999999", texto)
        self.assertNotIn("12345678", texto)
        self.assertNotIn("@laserena", texto)


class SecuenciaDatosPreviosTests(SimpleTestCase):
    def test_base_con_filas_viejas_y_repetir_importar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "legacy.sqlite3"
            entorno = _entorno(ruta)
            _manage(entorno, "migrate", "cuentas", "0002", "--skip-checks")
            _manage(entorno, "migrate", "requerimientos", "0002", "--skip-checks")
            _manage(entorno, "migrate", "control_gestion", "--skip-checks")
            _manage(entorno, "shell", "-c", SEMILLA)
            _manage(entorno, "migrate", "--skip-checks")
            _manage(entorno, "importar_json", "--skip-checks")
            entorno["COMPROBAR_DEMO"] = "1"
            primera = _manage(entorno, "shell", "-c", VERIFICACION)
            self.assertIn("verificacion-ok", primera.stdout)
            conteos = primera.stdout.strip().splitlines()[-1]
            _manage(entorno, "importar_json", "--skip-checks")
            segunda = _manage(entorno, "shell", "-c", VERIFICACION)
            self.assertIn("verificacion-ok", segunda.stdout)
            self.assertEqual(segunda.stdout.strip().splitlines()[-1], conteos)

    def test_base_vacia_loaddata_e_importar_dos_veces(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "vacia.sqlite3"
            entorno = _entorno(ruta)
            _manage(entorno, "migrate", "--skip-checks")
            _manage(entorno, "loaddata", "01_catalogos", "02_datos_sistema", "--skip-checks")
            _manage(entorno, "importar_json", "--skip-checks")
            primera = _manage(entorno, "shell", "-c", VERIFICACION)
            self.assertIn("verificacion-ok", primera.stdout)
            conteos = primera.stdout.strip().splitlines()[-1]
            _manage(entorno, "importar_json", "--skip-checks")
            segunda = _manage(entorno, "shell", "-c", VERIFICACION)
            self.assertIn("verificacion-ok", segunda.stdout)
            self.assertEqual(segunda.stdout.strip().splitlines()[-1], conteos)
