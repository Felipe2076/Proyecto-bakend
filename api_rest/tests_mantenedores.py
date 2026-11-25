
"""Pruebas de la API v2 para organizaciones y vecinos."""

from typing import Any, cast

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Delegacion

from control_gestion.models import OrganizacionComunitaria

from requerimientos.models import (
    Vecino,
    Requerimiento,
    TipoGestion,
    CanalIngreso,
    AreaSoporte,
)


CLAVE = "Prueba123!"
RUT_ADMIN = "33100120-1"
RUT_USUARIO = "33100122-8"

URL_ORGANIZACIONES = "/api/v2/organizaciones/"
URL_VECINOS = "/api/v2/vecinos/"

CAMPOS_PRIVADOS_ORGANIZACION = (
    "telefono",
    "correo",
    "presidente_rut",
    "tesorero_rut",
    "secretario_rut",
    "clave_origen",
    "eliminado_en",
)

CAMPOS_PRIVADOS_VECINO = (
    "rut",
    "telefono",
    "correo",
)


class MantenedoresTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.delegacion, _ = Delegacion.objects.get_or_create(
            nombre="Delegacion Centro (prueba mantenedores)"
        )

        cls.admin = crear_cuenta(
            codigo="USR-MAN1",
            rut=RUT_ADMIN,
            password=CLAVE,
            rol_codigo="superusuario",
            correo="admin.mantenedor@example.test",
            nombre="Administrador Prueba (ficticio)",
            delegacion=cls.delegacion,
        )

        cls.usuario = crear_cuenta(
            codigo="USR-MAN2",
            rut=RUT_USUARIO,
            password=CLAVE,
            rol_codigo="funcionario",
            correo="usuario.mantenedor@example.test",
            nombre="Usuario Prueba (ficticio)",
            delegacion=cls.delegacion,
        )

        cls.organizacion = OrganizacionComunitaria.objects.create(
            nombre="Organizacion Ficticia",
            tipo="JJVV",
            telefono="000000000",
            correo="organizacion@example.test",
            presidente_nombre="Presidente Prueba",
            presidente_rut="33100001-9",
            tesorero_nombre="Tesorero Prueba",
            tesorero_rut="33100002-7",
            secretario_nombre="Secretario Prueba",
            secretario_rut="33100003-5",
            territorio="Centro",
            delegacion=cls.delegacion,
        )

        cls.vecino = Vecino.objects.create(
            nombre="Vecino Ficticio",
            rut="33100001-9",
            telefono="000000000",
            correo="vecino@example.test",
            territorio="Centro",
            delegacion=cls.delegacion,
            es_simulacion=True,
        )

    def setUp(self):
        cache.clear()

        # Evita los falsos positivos de tipado de Pylance
        # sobre las respuestas de APIClient.
        self.api = cast(Any, APIClient())

    def autenticar(self, rut):

        self.api.credentials()

        respuesta = self.api.post(
            "/api/v2/token/",
            {
                "rut": rut,
                "password": CLAVE,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        self.api.credentials(
            HTTP_AUTHORIZATION=(
                "Bearer " + respuesta.json()["access"]
            )
        )

    def obtener_lista(self, respuesta):

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        datos = respuesta.json()

        if isinstance(datos, dict):
            return datos["results"]

        return datos

    # 1. ACCESO SIN TOKEN

    def test_sin_token_401(self):

        for url in (URL_ORGANIZACIONES, URL_VECINOS):

            with self.subTest(url=url):

                respuesta = self.api.get(url)

                self.assertEqual(
                    respuesta.status_code,
                    401,
                )

    # 2. PRIVACIDAD DE ORGANIZACIONES

    def test_usuario_no_ve_datos_privados_organizacion(self):

        self.autenticar(RUT_USUARIO)

        url = (
            f"{URL_ORGANIZACIONES}"
            f"{self.organizacion.pk}/"
        )

        respuesta = self.api.get(url)

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        datos = respuesta.json()

        self.assertEqual(
            datos["nombre"],
            self.organizacion.nombre,
        )

        for campo in CAMPOS_PRIVADOS_ORGANIZACION:
            self.assertNotIn(campo, datos)

        listado = self.obtener_lista(
            self.api.get(URL_ORGANIZACIONES)
        )

        self.assertTrue(listado)

        for organizacion in listado:
            for campo in CAMPOS_PRIVADOS_ORGANIZACION:
                self.assertNotIn(campo, organizacion)

    # 3. PRIVACIDAD DE VECINOS

    def test_usuario_no_ve_datos_privados_vecino(self):

        self.autenticar(RUT_USUARIO)

        url = f"{URL_VECINOS}{self.vecino.pk}/"

        respuesta = self.api.get(url)

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        datos = respuesta.json()

        self.assertEqual(
            datos["nombre"],
            self.vecino.nombre,
        )

        for campo in CAMPOS_PRIVADOS_VECINO:
            self.assertNotIn(campo, datos)

        listado = self.obtener_lista(
            self.api.get(URL_VECINOS)
        )

        self.assertTrue(listado)

        for vecino in listado:
            for campo in CAMPOS_PRIVADOS_VECINO:
                self.assertNotIn(campo, vecino)

    # 4. USUARIO NORMAL NO PUEDE MODIFICAR

    def test_usuario_no_puede_escribir_403(self):

        self.autenticar(RUT_USUARIO)

        casos = (
            (
                URL_ORGANIZACIONES,
                self.organizacion.pk,
            ),
            (
                URL_VECINOS,
                self.vecino.pk,
            ),
        )

        for url, identificador in casos:

            detalle = f"{url}{identificador}/"

            with self.subTest(url=url):

                respuesta = self.api.post(
                    url,
                    {"nombre": "Registro no autorizado"},
                    format="json",
                )

                self.assertEqual(respuesta.status_code, 403)

                respuesta = self.api.put(
                    detalle,
                    {"nombre": "Cambio no autorizado"},
                    format="json",
                )

                self.assertEqual(respuesta.status_code, 403)

                respuesta = self.api.delete(detalle)

                self.assertEqual(respuesta.status_code, 403)

        self.organizacion.refresh_from_db(from_queryset=None)
        self.vecino.refresh_from_db(from_queryset=None)

        self.assertEqual(
            self.organizacion.nombre,
            "Organizacion Ficticia",
        )

        self.assertIsNone(
            self.organizacion.eliminado_en
        )

        self.assertEqual(
            self.vecino.nombre,
            "Vecino Ficticio",
        )

    # 5. ADMINISTRADOR VE LOS CAMPOS AUTORIZADOS

    def test_admin_ve_datos_completos(self):

        self.autenticar(RUT_ADMIN)

        respuesta = self.api.get(
            f"{URL_ORGANIZACIONES}{self.organizacion.pk}/"
        )

        self.assertEqual(respuesta.status_code, 200)

        datos = respuesta.json()

        for campo in (
            "telefono",
            "correo",
            "presidente_rut",
            "tesorero_rut",
            "secretario_rut",
        ):
            self.assertIn(campo, datos)

        self.assertNotIn("clave_origen", datos)
        self.assertNotIn("eliminado_en", datos)

        respuesta = self.api.get(
            f"{URL_VECINOS}{self.vecino.pk}/"
        )

        self.assertEqual(respuesta.status_code, 200)

        for campo in CAMPOS_PRIVADOS_VECINO:
            self.assertIn(campo, respuesta.json())

    # 6. ADMINISTRADOR CRUD ORGANIZACIONES

    def test_admin_crea_edita_y_da_de_baja_organizacion(self):

        self.autenticar(RUT_ADMIN)

        datos = {
            "nombre": "Nueva Organizacion Ficticia",
            "tipo": "JJVV",
            "territorio": "Centro",
            "correo": "nueva.organizacion@example.test",
            "presidente_rut": "33.100.001-9",
            "socios_activos": 15,
            "delegacion": self.delegacion.pk,
        }

        respuesta = self.api.post(
            URL_ORGANIZACIONES,
            datos,
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.content,
        )

        identificador = respuesta.json()["id"]

        self.assertEqual(
            respuesta.json()["presidente_rut"],
            "33100001-9",
        )

        url = f"{URL_ORGANIZACIONES}{identificador}/"

        datos["nombre"] = "Organizacion Modificada"

        respuesta = self.api.put(
            url,
            datos,
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        organizacion = OrganizacionComunitaria.objects.get(
            pk=identificador
        )

        self.assertEqual(
            organizacion.nombre,
            "Organizacion Modificada",
        )

        respuesta = self.api.delete(url)

        self.assertEqual(
            respuesta.status_code,
            204,
            respuesta.content,
        )

        # Comprueba que la organizacion sigue en la BD.
        # Se utiliza el administrador base mediante _meta.

        organizacion = OrganizacionComunitaria._meta.base_manager.get(
            pk=identificador
        )

        self.assertIsNotNone(
            organizacion.eliminado_en
        )

        # Comprueba que ya no aparece en la API.

        self.assertEqual(
            self.api.get(url).status_code,
            404,
        )

        listado = self.obtener_lista(
            self.api.get(URL_ORGANIZACIONES)
        )

        identificadores = [
            registro["id"] for registro in listado
        ]

        self.assertNotIn(
            identificador,
            identificadores,
        )

    # 7. ADMINISTRADOR CRUD VECINOS

    def test_admin_crea_edita_y_elimina_vecino(self):

        self.autenticar(RUT_ADMIN)

        datos = {
            "nombre": "Nuevo Vecino Ficticio",
            "rut": "33.100.002-7",
            "telefono": "000000000",
            "correo": "nuevo.vecino@example.test",
            "delegacion": self.delegacion.pk,
            "es_simulacion": True,
        }

        respuesta = self.api.post(
            URL_VECINOS,
            datos,
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.content,
        )

        identificador = respuesta.json()["id"]

        self.assertEqual(
            respuesta.json()["rut"],
            "33100002-7",
        )

        url = f"{URL_VECINOS}{identificador}/"

        datos["nombre"] = "Vecino Modificado"

        respuesta = self.api.put(
            url,
            datos,
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.content,
        )

        vecino = Vecino.objects.get(
            pk=identificador
        )

        self.assertEqual(
            vecino.nombre,
            "Vecino Modificado",
        )

        respuesta = self.api.delete(url)

        self.assertEqual(
            respuesta.status_code,
            204,
            respuesta.content,
        )

        self.assertFalse(
            Vecino.objects.filter(
                pk=identificador
            ).exists()
        )

    # 8. VECINO CON TICKET PROTEGIDO

    def test_eliminar_vecino_con_ticket_devuelve_409(self):

        self.autenticar(RUT_ADMIN)

        tipo = TipoGestion.objects.create(
            nombre="Gestion de Prueba"
        )

        canal = CanalIngreso.objects.create(
            nombre="Canal de Prueba"
        )

        area = AreaSoporte.objects.create(
            codigo="AREA-API-MAN",
            nombre="Area de Prueba",
        )

        Requerimiento.objects.create(
            codigo="TK-API-MAN",
            vecino=self.vecino,
            delegacion=self.delegacion,
            canal_ingreso=canal,
            tipo_gestion=tipo,
            area=area,
            descripcion="Ticket ficticio de prueba",
        )

        respuesta = self.api.delete(
            f"{URL_VECINOS}{self.vecino.pk}/"
        )

        self.assertEqual(
            respuesta.status_code,
            409,
            respuesta.content,
        )

        self.assertTrue(
            Vecino.objects.filter(
                pk=self.vecino.pk
            ).exists()
        )

    # 9. VALIDACION DE RUT INVALIDO EN VECINOS

    def test_vecino_rut_invalido_400(self):

        self.autenticar(RUT_ADMIN)

        respuesta = self.api.post(
            URL_VECINOS,
            {
                "nombre": "Vecino Prueba",
                "rut": "33100001-0",
                "es_simulacion": True,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.content,
        )

    # 10. VALIDACION DE RUT EN ORGANIZACIONES

    def test_organizacion_rut_invalido_400(self):

        self.autenticar(RUT_ADMIN)

        for campo in (
            "presidente_rut",
            "tesorero_rut",
            "secretario_rut",
        ):

            with self.subTest(campo=campo):

                respuesta = self.api.post(
                    URL_ORGANIZACIONES,
                    {
                        "nombre": "Organizacion Prueba",
                        campo: "33100001-0",
                    },
                    format="json",
                )

                self.assertEqual(
                    respuesta.status_code,
                    400,
                    respuesta.content,
                )

    # 11. VALIDACION DE RUT DUPLICADO

    def test_vecino_rut_duplicado_400(self):

        self.autenticar(RUT_ADMIN)

        respuesta = self.api.post(
            URL_VECINOS,
            {
                "nombre": "Vecino Duplicado",
                "rut": "33.100.001-9",
                "es_simulacion": True,
            },
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.content,
        )
