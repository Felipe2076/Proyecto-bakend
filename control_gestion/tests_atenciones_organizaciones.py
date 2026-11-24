"""Atenciones dentro del Tubo y actividades de organizaciones en el calendario (datos ficticios)."""
from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.models import Compromiso, EventoAgenda, OrganizacionComunitaria
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.perfiles import sincronizar_usuario
from requerimientos.models import Atencion, SubAtencion, TipoAtencion, Vecino

CLAVE = 'Prueba123!'
JSON = {'HTTP_ACCEPT': 'application/json'}


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AtencionesEnElTuboTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.jefe = crear_cuenta(codigo='USR-J', rut='33100076-6', password=CLAVE, rol_codigo='jefatura',
                                correo='jefe@siged.test', nombre='Juana Prueba', delegacion=cls.centro)
        for perfil in (cls.admin, cls.funcionario, cls.jefe):
            sincronizar_usuario(perfil)
        tipo = TipoAtencion.objects.create(nombre='Salud ficticia')
        sub = SubAtencion.objects.create(nombre='Consulta ficticia', tipo_atencion=tipo)
        cls.vecino = Vecino.objects.create(nombre='Vecino Ficticio Atención', delegacion=cls.centro)
        cls.atencion = Atencion.objects.create(vecino=cls.vecino, tipo_atencion=tipo, sub_atencion=sub,
                                               delegacion=cls.centro, usuario=cls.admin, estado='pendiente')
        cls.ajena = Atencion.objects.create(vecino=cls.vecino, tipo_atencion=tipo, sub_atencion=sub,
                                            delegacion=cls.rural, usuario=cls.admin, estado='en_proceso')
        cls.codigo = f'ATN-{cls.atencion.pk:04d}'
        cls.codigo_ajena = f'ATN-{cls.ajena.pk:04d}'

    def mover(self, codigo, estado, anterior, ruta='/control/tubo-cartas/'):
        return self.client.post(ruta, {'id_compromiso': codigo, 'estado': estado, 'estado_anterior': anterior}, **JSON)

    def columnas(self, ruta='/control/tubo-cartas/'):
        contexto = self.client.get(ruta).context['columnas_lista']
        return {c['estado']: [i['id_compromiso'] for i in c['items']] for c in contexto}

    def test_administrador_ve_las_atenciones_en_las_columnas_del_tubo(self):
        self.autenticar()
        for ruta in ('/control/tubo-cartas/', '/control/tubo-trabajo/'):
            columnas = self.columnas(ruta)
            self.assertIn(self.codigo, columnas['PENDIENTE'])
            self.assertIn(self.codigo_ajena, columnas['EN PROCESO'])
        pagina = self.client.get('/control/tubo-cartas/')
        self.assertContains(pagina, 'Atención')
        self.assertContains(pagina, 'Salud ficticia · Consulta ficticia')
        self.assertContains(self.client.get('/control/tubo-trabajo/'), 'Modificar atención')

    def test_cada_atencion_cae_en_la_columna_de_su_estado(self):
        self.autenticar()
        Atencion.objects.filter(pk=self.atencion.pk).update(estado='cerrada')
        self.assertIn(self.codigo, self.columnas()['REALIZADO'])
        self.assertNotIn(self.codigo, self.columnas()['INGRESADO'])

    def test_sin_permiso_de_consulta_no_se_muestran(self):
        self.autenticar(self.funcionario)
        todas = [c for items in self.columnas().values() for c in items]
        self.assertNotIn(self.codigo, todas)

    def test_jefatura_solo_ve_las_de_su_delegacion(self):
        self.autenticar(self.jefe)
        todas = [c for items in self.columnas().values() for c in items]
        self.assertIn(self.codigo, todas)
        self.assertNotIn(self.codigo_ajena, todas)

    def test_funcionario_con_los_permisos_del_plan_ve_y_mueve_solo_las_de_su_delegacion(self):
        Group.objects.get(name='SIGED: funcionario').permissions.add(*Permission.objects.filter(
            content_type__app_label='requerimientos', codename__in=('view_atencion', 'change_atencion')))
        self.autenticar(self.funcionario)
        todas = [c for items in self.columnas().values() for c in items]
        self.assertIn(self.codigo, todas)
        self.assertNotIn(self.codigo_ajena, todas)
        self.assertEqual(self.mover(self.codigo, 'EN PROCESO', 'PENDIENTE').status_code, 200)
        self.assertEqual(self.mover(self.codigo_ajena, 'REALIZADO', 'EN PROCESO').status_code, 404)

    def test_mover_una_atencion_cambia_su_estado_y_se_conserva(self):
        self.autenticar()
        respuesta = self.mover(self.codigo, 'EN PROCESO', 'PENDIENTE')
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado, 'en_proceso')
        self.assertIn(self.codigo, self.columnas()['EN PROCESO'])
        self.assertEqual(self.mover(self.codigo, 'REALIZADO', 'EN PROCESO').status_code, 200)
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado, 'cerrada')
        self.assertEqual(self.mover(self.codigo, 'PENDIENTE', 'REALIZADO', '/control/tubo-trabajo/').status_code, 200)
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado, 'pendiente')

    def test_una_atencion_no_puede_pasar_a_ingresado(self):
        self.autenticar()
        respuesta = self.mover(self.codigo, 'INGRESADO', 'PENDIENTE')
        self.assertEqual(respuesta.status_code, 422)
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado, 'pendiente')
        self.assertNotContains(self.client.get('/control/tubo-cartas/'),
                               f'aria-label="Estado de {self.codigo}"><option value="INGRESADO"')

    def test_estado_anterior_desactualizado_da_conflicto(self):
        self.autenticar()
        self.assertEqual(self.mover(self.codigo, 'REALIZADO', 'EN PROCESO').status_code, 409)
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.estado, 'pendiente')

    def test_mover_exige_permiso_de_modificar_y_la_delegacion(self):
        self.autenticar(self.funcionario)
        self.assertEqual(self.mover(self.codigo, 'REALIZADO', 'PENDIENTE').status_code, 403)
        self.autenticar(self.jefe)
        self.assertEqual(self.mover(self.codigo_ajena, 'REALIZADO', 'EN PROCESO').status_code, 404)
        self.assertEqual(self.mover(self.codigo, 'REALIZADO', 'PENDIENTE').status_code, 200)

    def test_los_compromisos_siguen_moviendose_igual(self):
        compromiso = Compromiso.objects.create(
            descripcion='Compromiso ficticio', vecino=self.vecino, funcionario=self.funcionario.funcionario,
            delegacion=self.centro, fecha_compromiso=timezone.localdate() + timedelta(days=5))
        self.autenticar()
        respuesta = self.mover(compromiso.codigo, 'PENDIENTE', compromiso.estado)
        self.assertEqual(respuesta.status_code, 200)
        compromiso.refresh_from_db()
        self.assertEqual(compromiso.estado, 'PENDIENTE')
        # Los indicadores del Tubo siguen midiendo solo compromisos.
        self.assertEqual(self.client.get('/control/tubo-cartas/').context['total_compromisos'], 1)


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AgendaDeOrganizacionesTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.rural_fun = crear_cuenta(codigo='USR-R', rut='33100065-5', password=CLAVE, rol_codigo='funcionario',
                                     correo='rural@siged.test', nombre='Rita Prueba', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.rural_fun):
            sincronizar_usuario(perfil)
        cls.org = OrganizacionComunitaria.objects.create(nombre='Junta de Vecinos Ficticia Norte', delegacion=cls.centro)
        cls.org_sin_deleg = OrganizacionComunitaria.objects.create(nombre='Club Ficticio Sin Delegación')
        cls.hoy = timezone.localdate()

    def crear(self, **cambios):
        datos = {'titulo': 'Asamblea ficticia', 'tipo': 'Asamblea', 'fecha': self.hoy.isoformat(), 'hora': '18:30',
                 'organizacion': self.org.pk, 'delegacion': self.centro.pk, 'lugar': 'Sede ficticia'}
        datos.update(cambios)
        return self.client.post('/mantenedores/agenda/nuevo/', datos)

    def calendario(self, perfil=None):
        self.autenticar(perfil)
        return self.client.get('/control/agenda/', {'vista': 'lista', 'anio': self.hoy.year, 'mes': self.hoy.month})

    def test_la_actividad_de_una_organizacion_aparece_en_el_calendario(self):
        self.autenticar()
        self.assertEqual(self.crear().status_code, 302)
        evento = EventoAgenda.objects.get(titulo='Asamblea ficticia')
        self.assertEqual(evento.organizacion_id, self.org.pk)
        respuesta = self.calendario()
        self.assertContains(respuesta, 'Asamblea ficticia')
        self.assertContains(respuesta, 'Junta de Vecinos Ficticia Norte')
        self.assertContains(respuesta, 'Organización · Asamblea')
        mensajes = [e for e in respuesta.context['lista_mes'] if e['titulo'] == 'Asamblea ficticia']
        self.assertEqual(mensajes[0]['clase'], 'text-bg-success')

    def test_un_evento_sin_organizacion_se_ve_como_antes(self):
        self.autenticar()
        self.assertEqual(self.crear(titulo='Reunión interna', organizacion='').status_code, 302)
        evento = [e for e in self.calendario().context['lista_mes'] if e['titulo'] == 'Reunión interna'][0]
        self.assertEqual(evento['clase'], 'text-bg-primary')
        self.assertEqual(evento['organizacion'], '')

    def test_la_delegacion_se_toma_de_la_organizacion_si_se_deja_vacia(self):
        self.autenticar()
        self.assertEqual(self.crear(delegacion='').status_code, 302)
        self.assertEqual(EventoAgenda.objects.get().delegacion_id, self.centro.pk)

    def test_si_no_hay_delegacion_ni_la_organizacion_la_tiene_se_pide(self):
        self.autenticar()
        respuesta = self.crear(organizacion=self.org_sin_deleg.pk, delegacion='')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('delegacion', respuesta.context['form'].errors)
        self.assertFalse(EventoAgenda.objects.exists())

    def test_el_calendario_respeta_la_delegacion_de_cada_usuario(self):
        self.autenticar()
        self.crear()
        self.assertContains(self.calendario(self.funcionario), 'Asamblea ficticia')
        self.assertNotContains(self.calendario(self.rural_fun), 'Asamblea ficticia')

    def test_buscar_por_nombre_de_organizacion(self):
        self.autenticar()
        self.crear()
        self.crear(titulo='Otro evento', organizacion='')
        respuesta = self.client.get('/control/agenda/', {'vista': 'lista', 'q': 'Ficticia Norte',
                                                          'anio': self.hoy.year, 'mes': self.hoy.month})
        titulos = [e['titulo'] for e in respuesta.context['lista_mes']]
        self.assertIn('Asamblea ficticia', titulos)
        self.assertNotIn('Otro evento', titulos)

    def test_quien_no_es_administrador_solo_elige_organizaciones_de_su_delegacion(self):
        ajena = OrganizacionComunitaria.objects.create(nombre='Junta Ficticia Rural', delegacion=self.rural)
        Group.objects.get(name='SIGED: funcionario').permissions.add(*Permission.objects.filter(
            content_type__app_label='control_gestion', codename__in=('view_eventoagenda', 'add_eventoagenda')))
        self.autenticar(self.funcionario)
        form = self.client.get('/mantenedores/agenda/nuevo/').context['form']
        opciones = set(form.fields['organizacion'].queryset.values_list('pk', flat=True))
        self.assertEqual(opciones, {self.org.pk})
        # Con la delegación vacía no se puede «colar» la actividad en otra delegación.
        respuesta = self.crear(organizacion=ajena.pk, delegacion='')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('organizacion', respuesta.context['form'].errors)
        self.assertFalse(EventoAgenda.objects.exists())
        self.assertEqual(self.crear(organizacion=self.org.pk, delegacion='').status_code, 302)
        self.assertEqual(EventoAgenda.objects.get().delegacion_id, self.centro.pk)

    def test_el_mantenedor_esta_en_el_menu_y_exige_permiso(self):
        self.autenticar()
        menu = self.client.get('/').context['mantenedores_autorizados']
        self.assertIn('Actividades de organizaciones', [m['titulo'] for m in menu])
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get('/mantenedores/agenda/').status_code, 302)
        self.assertEqual(self.crear().status_code, 302)
        self.assertFalse(EventoAgenda.objects.exists())
