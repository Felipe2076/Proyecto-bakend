"""API v2: token JWT, refresh, endpoints protegidos, Swagger y formato de errores."""
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Delegacion

CLAVE = 'Prueba123!'


class ApiV2Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        centro, _ = Delegacion.objects.get_or_create(nombre='Delegación Centro (prueba API)')
        cls.admin = crear_cuenta(codigo='USR-API1', rut='33100120-1', password=CLAVE, rol_codigo='superusuario',
                                 correo='admin.api@example.test', nombre='Ana Prueba (ficticio)', delegacion=centro)
        cls.func = crear_cuenta(codigo='USR-API2', rut='33100122-8', password=CLAVE, rol_codigo='funcionario',
                                correo='func.api@example.test', nombre='Beto Prueba (ficticio)', delegacion=centro)

    def setUp(self):
        cache.clear()  # el límite de intentos usa la caché
        self.api = APIClient()

    def token(self, rut):
        r = self.api.post('/api/v2/token/', {'rut': rut, 'password': CLAVE}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_sin_token_401_json(self):
        r = self.api.get('/api/v2/yo/')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()['error'], 'Unauthorized')

    def test_clave_mala_401_sin_revelar_cuenta(self):
        r = self.api.post('/api/v2/token/', {'rut': '33100120-1', 'password': 'mala'}, format='json')
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()['detalle'], 'RUT o clave incorrectos.')

    def test_datos_faltantes_400(self):
        self.assertEqual(self.api.post('/api/v2/token/', {}, format='json').status_code, 400)

    def test_access_da_acceso_y_distingue_perfil(self):
        for rut, perfil in (('33.100.120-1', 'administrador'), ('33100122-8', 'usuario')):
            self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token(rut)['access'])
            r = self.api.get('/api/v2/yo/')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['perfil_api'], perfil)

    def test_refresh_entrega_nuevo_access(self):
        par = self.token('33100122-8')
        r = self.api.post('/api/v2/token/refresh/', {'refresh': par['refresh']}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.json())

    def test_token_falso_401(self):
        self.api.credentials(HTTP_AUTHORIZATION='Bearer no.es.un.token')
        self.assertEqual(self.api.get('/api/v2/yo/').status_code, 401)

    def test_swagger_y_esquema_publicos(self):
        self.assertEqual(self.api.get('/api/v2/docs/').status_code, 200)
        r = self.api.get('/api/v2/esquema/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'bearerFormat', r.content)

    def test_web_sigue_pidiendo_login(self):
        r = self.client.get('/control/kanban/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])
