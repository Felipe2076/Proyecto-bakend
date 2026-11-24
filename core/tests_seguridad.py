"""Refuerzo defensivo con datos ficticios: sesión, cookies, cuotas, cargas, ámbito, evidencias y logs."""
import logging
from io import BytesIO
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from PIL import Image

from control_gestion import tests_kanban
from control_gestion.models import Actividad, IntentosMovil, Meta
from core.seguridad import FiltroDatosPersonales, enmascarar, ip_cliente
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.perfiles import sincronizar_usuario

CLAVE = 'Prueba123!'


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SeguridadTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.ventanilla = crear_cuenta(codigo='USR-V', rut='33100043-4', password=CLAVE, rol_codigo='ventanilla',
                                      correo='ventanilla@siged.test', nombre='Vera Prueba', delegacion=cls.centro)
        cls.rural_fun = crear_cuenta(codigo='USR-R', rut='33100065-5', password=CLAVE, rol_codigo='funcionario',
                                     correo='rural@siged.test', nombre='Rita Prueba', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.ventanilla, cls.rural_fun):
            sincronizar_usuario(perfil)

    # --- Sesión y cookies -------------------------------------------------------------------
    def test_sesion_en_base_y_cookies_endurecidas(self):
        self.assertEqual(settings.SESSION_ENGINE, 'django.contrib.sessions.backends.db')
        self.assertTrue(settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE)
        respuesta = self.client.post('/login/', {'rut': self.admin.user.username, 'password': CLAVE})
        self.assertEqual(respuesta.status_code, 302)
        cookie = respuesta.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie['httponly'] and cookie['secure'])
        self.assertEqual(cookie['samesite'], 'Lax')
        # La cookie es un identificador opaco: no contiene nombre, rol ni delegación.
        self.assertNotIn('.', cookie.value)
        self.assertLessEqual(len(cookie.value), 40)
        self.client.post('/logout/')
        self.assertEqual(self.client.get('/control/tubo-trabajo/').status_code, 302)

    def test_csrf_obligatorio_en_formularios(self):
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post('/login/', {'rut': 'x', 'password': 'y'}).status_code, 403)

    def test_cabeceras_defensivas(self):
        respuesta = self.client.get('/login/')
        self.assertEqual(respuesta['X-Frame-Options'], 'DENY')
        self.assertEqual(respuesta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(respuesta['Referrer-Policy'], 'same-origin')
        self.assertIn('camera=()', respuesta['Permissions-Policy'])
        self.assertIn('no-store', respuesta['Cache-Control'])

    # --- Cuotas -----------------------------------------------------------------------------
    @override_settings(SIGED_LIMITE_LOGIN_CUENTA=3)
    def test_login_limita_por_cuenta_y_libera_al_ingresar(self):
        rut = self.funcionario.user.username
        for _ in range(2):
            self.assertEqual(self.client.post('/login/', {'rut': rut, 'password': 'incorrecta'}).status_code, 200)
        self.assertEqual(self.client.post('/login/', {'rut': rut, 'password': CLAVE}).status_code, 302)
        self.client.post('/logout/')
        for _ in range(3):
            self.client.post('/login/', {'rut': rut, 'password': 'incorrecta'})
        bloqueado = self.client.post('/login/', {'rut': rut, 'password': CLAVE})
        self.assertEqual(bloqueado.status_code, 429)
        self.assertContains(bloqueado, 'Demasiados intentos', status_code=429)
        # La tabla de cuotas guarda HMAC, no RUT ni IP.
        self.assertFalse(IntentosMovil.objects.filter(clave__contains=rut).exists())

    @override_settings(SIGED_LIMITE_LOGIN_IP=2, SIGED_PROXY_CONFIABLE=[])
    def test_login_limita_por_ip(self):
        for rut in ('11111111-1', '22222222-2'):
            self.client.post('/login/', {'rut': rut, 'password': 'x'})
        self.assertEqual(self.client.post('/login/', {'rut': '33333333-3', 'password': 'x'}).status_code, 429)

    def test_ip_del_proxy_solo_si_es_confiable(self):
        import ipaddress
        factory = RequestFactory()
        pedido = factory.get('/', REMOTE_ADDR='172.18.0.1', HTTP_X_FORWARDED_FOR='1.2.3.4, 203.0.113.9')
        self.assertEqual(ip_cliente(pedido), '172.18.0.1')
        with override_settings(SIGED_PROXIES_CONFIABLES=[ipaddress.ip_network('172.18.0.1/32')]):
            self.assertEqual(ip_cliente(pedido), '203.0.113.9')
            directo = factory.get('/', REMOTE_ADDR='198.51.100.7', HTTP_X_FORWARDED_FOR='9.9.9.9')
            self.assertEqual(ip_cliente(directo), '198.51.100.7')

    def test_recuperacion_no_revela_si_el_correo_existe(self):
        real = self.client.post('/recuperar/', {'correo': self.admin.correo}, follow=True)
        otro = Client().post('/recuperar/', {'correo': 'nadie@ejemplo.test'}, follow=True)
        self.assertEqual(real.redirect_chain[-1][0], otro.redirect_chain[-1][0])
        for respuesta in (real, otro):
            self.assertContains(respuesta, 'Si el correo corresponde a una cuenta activa')
        self.assertEqual(len(mail.outbox), 1)
        falso = Client()
        falso.post('/recuperar/', {'correo': 'nadie@ejemplo.test'})
        intento = falso.post('/recuperar/codigo/', {f'd{i}': '1' for i in range(1, 7)})
        self.assertContains(intento, 'no coincide')
        self.assertEqual(falso.get('/recuperar/nueva/').status_code, 302)

    @override_settings(SIGED_LIMITE_RECUPERAR_CORREO=2)
    def test_recuperacion_limita_envios_por_correo(self):
        for _ in range(2):
            Client().post('/recuperar/', {'correo': self.admin.correo})
        self.assertEqual(Client().post('/recuperar/', {'correo': self.admin.correo}).status_code, 429)
        self.assertEqual(len(mail.outbox), 2)

    # --- Cargas -----------------------------------------------------------------------------
    @override_settings(SIGED_MAX_PETICION=1024)
    def test_peticion_grande_se_rechaza_antes_de_leerla(self):
        respuesta = self.client.post('/login/', {'rut': 'x' * 2048, 'password': 'y'})
        self.assertEqual(respuesta.status_code, 413)

    def test_imagen_gigante_y_nombre_aleatorio(self):
        from control_gestion.evidencias import validar_archivo
        from unittest import mock
        out = BytesIO(); Image.new('RGB', (4, 4)).save(out, format='PNG')
        with mock.patch('control_gestion.evidencias.MAX_PIXELES', 10):
            with self.assertRaisesMessage(ValueError, 'resolución máxima'):
                validar_archivo(SimpleUploadedFile('a.png', out.getvalue()))
        with TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            actividad = Actividad.objects.create(
                funcionario=self.funcionario.funcionario, delegacion=self.centro,
                meta=Meta.objects.create(nombre='Meta ficticia'), servicio='Visita ficticia',
                evidencia_archivo=SimpleUploadedFile('rut-12345678-5 Juan Perez.png', out.getvalue()))
            nombre = actividad.evidencia_archivo.name
            self.assertNotIn('Juan', nombre)
            self.assertNotIn('12345678', nombre)
            self.assertRegex(nombre, r'^evidencias/\d{4}/\d{2}/[0-9a-f]{32}\.png$')
            self.autenticar(self.rural_fun)
            self.assertEqual(self.client.get(f'/control/actividades/{actividad.codigo}/evidencia/').status_code, 404)
            actividad.evidencia_archivo.delete(save=False)

    # --- Permisos por módulo, delegación y objeto -------------------------------------------
    def test_paneles_exigen_modulo(self):
        self.autenticar(self.ventanilla)
        for url in ('/control/', '/control/areas/', '/control/semaforo-sgr/', '/control/funcionarios/',
                    '/control/resumen/', f'/control/funcionarios/{self.funcionario.funcionario.codigo}/'):
            self.assertRedirects(self.client.get(url), '/', fetch_redirect_response=False, msg_prefix=url)
        self.autenticar(self.funcionario)
        self.assertRedirects(self.client.get('/control/'), '/', fetch_redirect_response=False)

    def test_listados_limitados_a_la_delegacion_propia(self):
        self.autenticar(self.funcionario)
        for url in ('/control/funcionarios/', '/control/semaforo-sgr/'):
            delegaciones = {f.get('delegacion') for f in self.client.get(url).context['funcionarios']}
            self.assertEqual(delegaciones, {self.centro.nombre}, url)
        self.assertRedirects(self.client.get('/control/funcionarios/?delegacion=Delegación Rural'), '/',
                             fetch_redirect_response=False)
        self.assertEqual(self.client.get('/control/resumen/').context['filtro_delegacion'], self.centro.nombre)
        self.autenticar()
        delegaciones = {f.get('delegacion') for f in self.client.get('/control/funcionarios/').context['funcionarios']}
        self.assertIn(self.rural.nombre, delegaciones)

    def test_detalle_de_otra_delegacion_o_sin_delegacion(self):
        self.autenticar(self.funcionario)
        ajeno = f'/control/funcionarios/{self.rural_fun.funcionario.codigo}/'
        self.assertRedirects(self.client.get(ajeno), '/', fetch_redirect_response=False)
        self.assertEqual(self.client.get(f'/control/funcionarios/{self.funcionario.funcionario.codigo}/').status_code, 200)

    def test_sesion_no_administradora_sin_delegacion_no_ve_ninguna(self):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from cuentas.ambito import denegar_otra_delegacion, limitar_a_delegacion
        pedido = RequestFactory().get('/')
        pedido.session = {'usuario': {'rol': 'funcionario', 'delegacion': ''}}
        pedido._messages = FallbackStorage(pedido)
        self.assertEqual(limitar_a_delegacion(pedido, [{'delegacion': 'Delegación Centro'}]), [])
        self.assertEqual(denegar_otra_delegacion(pedido, 'Delegación Centro').status_code, 302)
        self.assertIsNone(denegar_otra_delegacion(pedido, ''))

    def test_salud_sin_sesion_y_sin_detalles(self):
        respuesta = Client().get('/salud/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'estado': 'ok'})

    # --- Logs -------------------------------------------------------------------------------
    def test_logs_sin_datos_personales(self):
        texto = enmascarar('GET /lista/?q=12.345.678-5 de ana.perez@ejemplo.test token=abc123 RUT 9876543-3')
        for dato in ('12.345.678', 'ana.perez', 'abc123', '9876543-3'):
            self.assertNotIn(dato, texto)
        registro = logging.LogRecord('django.request', logging.ERROR, __file__, 1,
                                     'Error en %s para %s', ('/x/?rut=11111111-1', 'b@c.cl'), None)
        registro.request = object()
        FiltroDatosPersonales().filter(registro)
        self.assertNotIn('11111111', registro.getMessage())
        self.assertNotIn('b@c.cl', registro.getMessage())
        self.assertIsNone(registro.request)
        with self.assertLogs('siged.seguridad', level='WARNING') as capturado, \
                override_settings(SIGED_LIMITE_LOGIN_CUENTA=0):
            self.client.post('/login/', {'rut': self.funcionario.user.username, 'password': 'x'})
        self.assertEqual(capturado.output, ['WARNING:siged.seguridad:login_web_limitado'])


class PermisosArchivosTests(TestCase):
    def test_estaticos_legibles_por_el_proxy_y_evidencias_privadas(self):
        from django.contrib.staticfiles.storage import staticfiles_storage
        from django.core.files.storage import default_storage
        self.assertEqual(staticfiles_storage.file_permissions_mode, 0o644)
        self.assertEqual(staticfiles_storage.directory_permissions_mode, 0o755)
        self.assertEqual(default_storage.file_permissions_mode, 0o640)
        self.assertEqual(default_storage.directory_permissions_mode, 0o750)
