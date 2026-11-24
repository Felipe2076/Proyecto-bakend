"""El trimestre es único para todas las delegaciones y todo usuario lo ve en su bienvenida."""
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.forms import MedicionForm
from control_gestion.models import Medicion
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.perfiles import sincronizar_usuario

CLAVE = 'Prueba123!'


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TrimestreGlobalTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.rural_fun = crear_cuenta(codigo='USR-R', rut='33100065-5', password=CLAVE, rol_codigo='funcionario',
                                     correo='rural@siged.test', nombre='Rita Prueba', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.rural_fun):
            sincronizar_usuario(perfil)
        hoy = timezone.localdate()
        cls.medicion = Medicion.objects.create(
            periodo='Trimestre ficticio A', delegacion_piloto=cls.centro, fecha_inicio=hoy - timedelta(days=30),
            fecha_termino=hoy + timedelta(days=59), dias_totales=90)

    def inicio(self, perfil):
        self.autenticar(perfil)
        return self.client.get('/')

    def test_funcionario_de_cualquier_delegacion_ve_el_trimestre_vigente(self):
        for perfil in (self.funcionario, self.rural_fun, self.admin):
            respuesta = self.inicio(perfil)
            self.assertEqual(respuesta.status_code, 200)
            self.assertContains(respuesta, 'data-trimestre-vigente')
            self.assertContains(respuesta, 'Trimestre ficticio A')
            self.assertContains(respuesta, 'para todas las delegaciones')
            self.assertEqual(respuesta.context['trimestre_vigente']['dia'], 31)

    def test_al_cambiar_el_trimestre_cambia_para_todos_a_la_vez(self):
        Medicion.objects.filter(pk=self.medicion.pk).update(periodo='Trimestre ficticio B')
        for perfil in (self.funcionario, self.rural_fun):
            respuesta = self.inicio(perfil)
            self.assertContains(respuesta, 'Trimestre ficticio B')
            self.assertNotContains(respuesta, 'Trimestre ficticio A')

    def test_sin_trimestre_configurado_se_usa_el_calendario(self):
        Medicion.objects.all().delete()
        respuesta = self.inicio(self.rural_fun)
        self.assertRegex(respuesta.context['trimestre_vigente']['periodo'], r'^Trimestre [1-4] de \d{4}$')
        self.assertFalse(respuesta.context['trimestre_vigente']['configurado'])

    def test_pantallas_publicas_no_consultan_el_trimestre(self):
        respuesta = Client().get('/login/')
        self.assertIsNone(respuesta.context['trimestre_vigente'])

    def test_bienvenida_al_ingresar_incluye_el_trimestre(self):
        cliente = Client()
        pagina = cliente.post('/login/', {'rut': self.rural_fun.user.username, 'password': CLAVE}, follow=True)
        mensajes = [str(m) for m in pagina.context['messages']]
        self.assertTrue(any('Bienvenido/a' in m and 'Trimestre vigente: Trimestre ficticio A' in m for m in mensajes), mensajes)

    def test_configuracion_trimestral_ya_no_pide_delegacion(self):
        hoy = timezone.localdate()
        datos = {'periodo': 'Trimestre ficticio C', 'fecha_inicio': hoy + timedelta(days=100),
                 'fecha_termino': hoy + timedelta(days=190), 'dias_totales': 90, 'meta_cumplimiento_tubo': 80}
        form = MedicionForm(datos)
        self.assertNotIn('delegacion_piloto', form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        creada = form.save()
        self.assertEqual(creada.delegacion_piloto_id, self.centro.pk)  # se conserva la existente; no se elige

    def test_alta_desde_la_pantalla_sin_elegir_delegacion(self):
        hoy = timezone.localdate()
        self.autenticar()
        formulario = self.client.get('/mantenedores/periodos/nuevo/')
        self.assertNotContains(formulario, 'delegacion_piloto')
        respuesta = self.client.post('/mantenedores/periodos/nuevo/', {
            'periodo': 'Trimestre ficticio D', 'fecha_inicio': hoy + timedelta(days=200),
            'fecha_termino': hoy + timedelta(days=290), 'dias_totales': 90, 'meta_cumplimiento_tubo': 80})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Medicion.objects.filter(periodo='Trimestre ficticio D').exists())
