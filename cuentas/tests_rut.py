"""RUT, ingreso por rol y datos de simulación de la prioridad 1."""

import json
import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.test import Client, SimpleTestCase, TestCase

from core.validaciones import (
    cuerpo_en_rango_ficticio,
    dv_rut,
    enmascarar_rut,
    formatear_rut,
    normalizar_rut,
    validar_nombre,
    validar_rut,
)
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Delegacion
from cuentas.recuperacion import hash_codigo
from cuentas.simulacion import con_marca

RAIZ = Path(settings.BASE_DIR)
ROLES = ("administrador", "jefatura", "funcionario", "ventanilla")
DELEGACIONES = (
    "Delegación Centro",
    "Delegación Rural",
    "Delegación La Antena",
    "Delegación La Pampa",
    "Delegación Av. del Mar",
    "Delegación Las Compañías",
)


class ValidacionRutTests(SimpleTestCase):
    def test_digito_verificador_de_los_ejemplos_del_plan(self):
        self.assertEqual(dv_rut("33100001"), "9")
        self.assertEqual(dv_rut("33100002"), "7")
        self.assertEqual(dv_rut("33100003"), "5")
        self.assertEqual(dv_rut("33100006"), "K")
        self.assertEqual(dv_rut("33500001"), "3")
        self.assertEqual(dv_rut("33500002"), "1")

    def test_acepta_con_puntos_y_guarda_normalizado(self):
        self.assertTrue(validar_rut("33.100.001-9"))
        self.assertTrue(validar_rut("33100006-k"))
        self.assertEqual(normalizar_rut("33.100.006-k"), "33100006-K")
        self.assertEqual(formatear_rut("33100001-9"), "33.100.001-9")
        self.assertEqual(enmascarar_rut("33100001-9"), "33.1XX.XXX-9")

    def test_rechaza_dv_incorrecto_y_formato(self):
        self.assertFalse(validar_rut("33.100.001-0"))
        self.assertFalse(validar_rut("12345678-9"))
        self.assertFalse(validar_rut("33100001"))
        self.assertFalse(validar_rut(""))

    def test_javascript_usa_el_mismo_modulo_11(self):
        script = RAIZ / "static" / "js" / "modulos" / "validaciones.js"
        nodo = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                (
                    f"import * as v from '{script.as_posix()}';"
                    "const casos = ['33.100.001-9','33100006-k','33.100.001-0',''];"
                    "const salida = casos.map((rut) => v.validarRut(rut));"
                    "if (v.dvRut('33100006') !== 'K') process.exit(2);"
                    "if (JSON.stringify(salida) !== JSON.stringify([true,true,false,false])) process.exit(3);"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(nodo.returncode, 0, nodo.stderr or nodo.stdout)


class PanelPorRolTests(TestCase):
    """Cada rol entra con su RUT y ve el panel que ya existía para ese rol."""

    def setUp(self):
        self.rural = Delegacion.objects.create(nombre="Delegación Rural")
        self.centro = Delegacion.objects.create(nombre="Delegación Centro")
        self.cuentas = {
            "administrador": crear_cuenta(
                codigo="USR-A",
                rut="33100901-6",
                password="ClaveRol1!",
                rol_codigo="administrador",
                correo="rol-admin@siged.test",
                nombre="Admin Rural",
                delegacion=self.rural,
            ),
            "jefatura": crear_cuenta(
                codigo="USR-J",
                rut="33100902-4",
                password="ClaveRol1!",
                rol_codigo="jefatura",
                correo="rol-jefatura@siged.test",
                nombre="Jefatura Rural",
                delegacion=self.rural,
            ),
            "funcionario": crear_cuenta(
                codigo="USR-F",
                rut="33100003-5",
                password="ClaveRol1!",
                rol_codigo="funcionario",
                correo="rol-funcionario@siged.test",
                nombre="Funcionario Rural",
                delegacion=self.rural,
            ),
            "ventanilla": crear_cuenta(
                codigo="USR-V",
                rut="33100006-K",
                password="ClaveRol1!",
                rol_codigo="ventanilla",
                correo="rol-ventanilla@siged.test",
                nombre="Ventanilla Rural",
                delegacion=self.rural,
            ),
        }

    def _entrar(self, rut):
        cliente = Client()
        respuesta = cliente.post("/login/", {"rut": rut, "password": "ClaveRol1!"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/")
        return cliente

    def test_administrador_ve_la_vista_global(self):
        cliente = self._entrar("33100901-6")
        panel = cliente.get("/")
        self.assertContains(panel, "Vista global")
        self.assertNotContains(panel, "Mi delegación")
        self.assertEqual(cliente.session["usuario"]["rol"], "administrador")

    def test_jefatura_ve_su_delegacion(self):
        cliente = self._entrar("33.100.902-4")
        panel = cliente.get("/")
        self.assertContains(panel, "Mi delegación ·")
        self.assertContains(panel, "Delegación Rural")
        self.assertNotContains(panel, "Vista global")

    def test_funcionario_y_ventanilla_ven_el_panel_personal(self):
        for rut in ("33100003-5", "33100006-K"):
            cliente = self._entrar(rut)
            panel = cliente.get("/")
            self.assertContains(panel, "Mi panel")
            self.assertContains(panel, "33.1XX.XXX-")
            self.assertNotContains(panel, "Vista global")
            self.assertNotContains(panel, "Mi delegación ·")

    def test_otra_delegacion_por_url_se_niega_salvo_al_administrador(self):
        jefatura = self._entrar("33100902-4")
        negada = jefatura.get("/lista/", {"delegacion": "Delegación Centro"})
        self.assertEqual(negada.status_code, 302)
        self.assertEqual(negada["Location"], "/")
        admin = self._entrar("33100901-6")
        permitida = admin.get("/lista/", {"delegacion": "Delegación Centro"})
        self.assertEqual(permitida.status_code, 200)


class DatosSimulacionTests(SimpleTestCase):
    def test_usuarios_json_sin_clave_en_claro_y_con_cobertura(self):
        usuarios = json.loads((RAIZ / "data" / "usuarios.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(usuarios), 24)
        cobertura = {(item["rol"], item["delegacion"]) for item in usuarios}
        for delegacion in DELEGACIONES:
            for rol in ROLES:
                self.assertIn((rol, delegacion), cobertura)
        for item in usuarios:
            self.assertNotIn("password", item)
            self.assertNotIn("clave", item)
            self.assertNotIn("(ficticio)", item["nombre"])
            self.assertNotIn("(", item["nombre"])
            self.assertTrue(validar_nombre(item["nombre"]))
            self.assertTrue(item["email"].endswith("@siged.test"))
            self.assertTrue(validar_rut(item["rut"]))
            self.assertTrue(cuerpo_en_rango_ficticio(item["rut"]))
            cuerpo = int(normalizar_rut(item["rut"]).split("-")[0])
            self.assertTrue(33_100_001 <= cuerpo <= 33_100_999)
            self.assertEqual(item["username"], item["rut"])

    def test_fixture_y_d003_no_guardan_la_clave_en_claro(self):
        fixture = json.loads((RAIZ / "fixtures" / "02_datos_sistema.json").read_text(encoding="utf-8"))
        d003 = (RAIZ / "sql" / "datos" / "D003__datos_simulacion.sql").read_text(encoding="utf-8")
        self.assertNotIn("pbkdf2_", d003)
        self.assertNotIn("admin123", d003)
        self.assertNotIn("(ficticio)", d003)
        vecinos = [fila for fila in fixture if fila["model"] == "requerimientos.vecino"]
        funcionarios = [fila for fila in fixture if fila["model"] == "cuentas.funcionario"]
        auth = [fila for fila in fixture if fila["model"] == "auth.user"]
        self.assertGreaterEqual(len(vecinos), 60)
        self.assertGreaterEqual(len(funcionarios), 24)
        self.assertGreaterEqual(len(auth), 24)
        for fila in vecinos:
            campos = fila["fields"]
            self.assertTrue(campos["es_simulacion"])
            self.assertNotIn("(ficticio)", campos["nombre"])
            self.assertNotIn("(", campos["nombre"])
            self.assertTrue(campos["correo"].endswith("@siged.test"))
            self.assertTrue(campos["telefono"].startswith("+5690000"))
            self.assertTrue(validar_rut(campos["rut"]))
            cuerpo = int(normalizar_rut(campos["rut"]).split("-")[0])
            self.assertTrue(33_500_001 <= cuerpo <= 33_509_999)
        for fila in funcionarios:
            campos = fila["fields"]
            self.assertTrue(validar_rut(campos["rut"]))
            self.assertNotIn("(ficticio)", campos["nombre"])
            self.assertNotIn("(", campos["nombre"])
            self.assertTrue(campos["es_simulacion"])
            self.assertTrue(validar_nombre(campos["nombres"]))
            self.assertTrue(validar_nombre(campos["apellido_paterno"]))
            cuerpo = int(normalizar_rut(campos["rut"]).split("-")[0])
            self.assertTrue(33_100_001 <= cuerpo <= 33_100_999)
        for fila in auth:
            clave = fila["fields"]["password"]
            self.assertEqual(clave, "!")

    def test_v019_conserva_el_esquema_acordado(self):
        texto = (RAIZ / "sql" / "migraciones" / "V019__codigo_un_uso.sql").read_text(encoding="utf-8")
        create = texto[texto.index("CREATE TABLE") :].strip()
        esperado = """
CREATE TABLE codigo_un_uso (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  proposito VARCHAR(20) NOT NULL,
  usuario_id BIGINT NULL,
  cuenta_vecino_id BIGINT UNSIGNED NULL,
  codigo_hash CHAR(64) NOT NULL,
  canal VARCHAR(10) NOT NULL DEFAULT 'CORREO',
  destino_mascara VARCHAR(80) NULL,
  expira_en DATETIME NOT NULL,
  intentos TINYINT UNSIGNED NOT NULL DEFAULT 0,
  usado_en DATETIME NULL,
  anulado_en DATETIME NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ip_origen VARCHAR(45) NULL,
  INDEX idx_codigo_dueno (usuario_id, proposito, creado_en),
  INDEX idx_codigo_vecino (cuenta_vecino_id, proposito, creado_en),
  INDEX idx_codigo_expira (expira_en),
  CONSTRAINT fk_codigo_usuario FOREIGN KEY (usuario_id) REFERENCES cuentas_usuario(id) ON DELETE CASCADE,
  CONSTRAINT ck_codigo_intentos CHECK (intentos <= 5),
  CONSTRAINT ck_codigo_proposito CHECK (proposito IN ('RECUPERAR_CLAVE','MFA_EMAIL','LOGIN_VECINO','VERIFICAR_CORREO')),
  CONSTRAINT ck_codigo_canal CHECK (canal IN ('CORREO','SMS'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
""".strip()
        self.assertEqual(create, esperado)
        rollback = (RAIZ / "sql" / "rollback" / "R019__codigo_un_uso.sql").read_text(encoding="utf-8")
        self.assertIn("DROP TABLE codigo_un_uso;", rollback)
        self.assertNotIn("V023", texto)

    def test_hmac_usa_siged_code_hmac_key_o_secret_key(self):
        anterior = os.environ.pop("SIGED_CODE_HMAC_KEY", None)
        try:
            con_secret = hash_codigo("123456")
            os.environ["SIGED_CODE_HMAC_KEY"] = "hmac-de-prueba"
            con_entorno = hash_codigo("123456")
        finally:
            if anterior is None:
                os.environ.pop("SIGED_CODE_HMAC_KEY", None)
            else:
                os.environ["SIGED_CODE_HMAC_KEY"] = anterior
        self.assertEqual(len(con_secret), 64)
        self.assertEqual(len(con_entorno), 64)
        self.assertNotEqual(con_secret, con_entorno)
        self.assertNotEqual(con_entorno, "123456")

    def test_la_marca_se_muestra_y_el_patron_rechaza_parentesis(self):
        self.assertFalse(validar_nombre("Ana (ficticio)"))
        self.assertTrue(validar_nombre("Ana Soto"))
        self.assertEqual(con_marca("Ana Soto", True), "Ana Soto (ficticio)")
        self.assertEqual(con_marca("Ana Soto", False), "Ana Soto")
