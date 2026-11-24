"""Un compromiso vencido debe verse en la columna de su estado (antes quedaba siempre en «Vencido»). Datos ficticios."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.models import Compromiso
from cuentas.perfiles import sincronizar_usuario
from requerimientos.models import Vecino

JSON = {'HTTP_ACCEPT': 'application/json'}
RUTAS = ('/control/tubo-cartas/', '/control/tubo-trabajo/')


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TuboConCompromisosVencidosTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        for perfil in (cls.admin, cls.funcionario):
            sincronizar_usuario(perfil)
        vecino = Vecino.objects.create(nombre='Vecino Ficticio Vencidos', delegacion=cls.centro)
        hoy = timezone.localdate()
        cls.vencido = Compromiso.objects.create(
            descripcion='Compromiso ficticio vencido', vecino=vecino, funcionario=cls.funcionario.funcionario,
            delegacion=cls.centro, fecha_compromiso=hoy - timedelta(days=30), estado='PENDIENTE')
        cls.vigente = Compromiso.objects.create(
            descripcion='Compromiso ficticio vigente', vecino=vecino, funcionario=cls.funcionario.funcionario,
            delegacion=cls.centro, fecha_compromiso=hoy + timedelta(days=30), estado='PENDIENTE')

    def columnas(self, ruta='/control/tubo-cartas/'):
        contexto = self.client.get(ruta).context['columnas_lista']
        return {c['estado']: [i['id_compromiso'] for i in c['items']] for c in contexto}

    def mover(self, codigo, estado, anterior, ruta='/control/tubo-cartas/'):
        return self.client.post(ruta, {'id_compromiso': codigo, 'estado': estado, 'estado_anterior': anterior}, **JSON)

    def test_el_vencido_esta_en_la_columna_de_su_estado_y_no_hay_columna_vencido(self):
        self.autenticar()
        for ruta in RUTAS:
            columnas = self.columnas(ruta)
            self.assertNotIn('VENCIDO', columnas)
            self.assertIn(self.vencido.codigo, columnas['PENDIENTE'])
            self.assertIn(self.vigente.codigo, columnas['PENDIENTE'])
        # El aviso «vencido(s)» y el indicador siguen contando los atrasados.
        self.assertEqual(self.client.get('/control/tubo-cartas/').context['vencidos'], 1)
        self.assertContains(self.client.get('/control/tubo-cartas/'), 'Vencido')

    def test_mover_un_vencido_entre_columnas_se_ve_y_se_conserva(self):
        self.autenticar()
        anterior = 'PENDIENTE'
        for nuevo in ('EN PROCESO', 'INGRESADO', 'PENDIENTE', 'EN PROCESO'):
            respuesta = self.mover(self.vencido.codigo, nuevo, anterior)
            self.assertEqual(respuesta.status_code, 200, respuesta.content)
            self.vencido.refresh_from_db()
            self.assertEqual(self.vencido.estado, nuevo)
            columnas = self.columnas()
            self.assertIn(self.vencido.codigo, columnas[nuevo])
            self.assertEqual([c for c, items in columnas.items() if self.vencido.codigo in items], [nuevo])
            anterior = nuevo

    def test_al_realizarse_deja_de_estar_vencido(self):
        self.autenticar()
        self.assertEqual(self.mover(self.vencido.codigo, 'REALIZADO', 'PENDIENTE', '/control/tubo-trabajo/').status_code, 200)
        self.assertIn(self.vencido.codigo, self.columnas()['REALIZADO'])
        self.assertEqual(self.client.get('/control/tubo-cartas/').context['vencidos'], 0)

    def test_los_totales_por_columna_siguen_el_estado(self):
        self.autenticar()
        self.mover(self.vencido.codigo, 'EN PROCESO', 'PENDIENTE')
        totales = {c['estado']: c['total'] for c in self.client.get('/control/tubo-cartas/').context['columnas_lista']}
        self.assertEqual(totales, {'INGRESADO': 0, 'PENDIENTE': 1, 'EN PROCESO': 1, 'REALIZADO': 0})

    def test_el_filtro_vencido_sigue_funcionando(self):
        self.autenticar()
        respuesta = self.client.get('/control/tubo-cartas/', {'estado': 'VENCIDO'})
        codigos = [c for items in {c['estado']: [i['id_compromiso'] for i in c['items']]
                                   for c in respuesta.context['columnas_lista']}.values() for c in items]
        self.assertEqual(codigos, [self.vencido.codigo])

    def test_la_tabla_muestra_el_estado_y_la_etiqueta_vencido(self):
        self.autenticar()
        self.mover(self.vencido.codigo, 'EN PROCESO', 'PENDIENTE', '/control/tubo-trabajo/')
        pagina = self.client.get('/control/tubo-trabajo/')
        self.assertContains(pagina, 'EN PROCESO')
        self.assertContains(pagina, 'Vencido')
