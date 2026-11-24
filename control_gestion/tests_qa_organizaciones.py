"""Fase 3 del reporte de QA: ficha de organizaciones comunitarias. Datos ficticios."""
import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.contrib.messages import get_messages
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.forms import EventoAgendaForm, normalizar_telefono
from control_gestion.models import EventoAgenda, OrganizacionComunitaria, RegistroBaja, TerritorioDelegacion
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.perfiles import sincronizar_usuario

URL = '/mantenedores/organizaciones/'


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class OrganizacionesQATests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.adm_rural = crear_cuenta(codigo='USR-QO', rut='33100121-1', password='Prueba123!', rol_codigo='administrador',
                                     correo='qo.rural@siged.test', nombre='Admin Rural Org', delegacion=cls.rural)
        for perfil in (cls.admin, cls.adm_rural):
            sincronizar_usuario(perfil)
        TerritorioDelegacion.objects.create(delegacion=cls.centro, nombre='Territorio Ficticio A')
        TerritorioDelegacion.objects.create(delegacion=cls.rural, nombre='Territorio Rural B')

    def datos(self, **extra):
        base = {'nombre': 'Junta de Vecinos Ficticia Uno', 'tipo': 'JJVV', 'delegacion': self.centro.pk,
                'territorio': 'Territorio Ficticio A', 'activa': 'on'}
        base.update(extra)
        return base

    def test_crear_normaliza_telefono_y_correo(self):
        self.autenticar()
        r = self.client.post(URL + 'nuevo/', self.datos(telefono='9 1234 5678', correo='Directiva@Correo.CL'))
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        org = OrganizacionComunitaria.objects.get(nombre='Junta de Vecinos Ficticia Uno')
        self.assertEqual((org.telefono, org.correo, org.tipo), ('+56 9 1234 5678', 'directiva@correo.cl', 'JJVV'))
        self.assertIsNotNone(org.uuid)
        self.assertEqual(org.version, 1)

    def test_formulario_en_secciones(self):
        self.autenticar()
        html = self.client.get(URL + 'nuevo/').content.decode()
        for seccion in ('Identificación', 'Ubicación', 'Directiva', 'Antecedentes legales', 'Estado'):
            self.assertIn(f'<legend>{seccion}</legend>', html)
        self.assertIn('data-regla="rut-aviso"', html)

    def test_telefono_y_fechas_invalidos(self):
        self.autenticar()
        futuro = (timezone.localdate() + timedelta(days=3)).isoformat()
        r = self.client.post(URL + 'nuevo/', self.datos(telefono='123', fecha_constitucion=futuro,
                                                        fecha_inscripcion='2001-01-01', socios_activos='0'))
        errores = r.context['form'].errors
        for campo in ('telefono', 'fecha_constitucion', 'socios_activos'):
            self.assertIn(campo, errores)
        r = self.client.post(URL + 'nuevo/', self.datos(fecha_constitucion='2010-05-01', fecha_inscripcion='2009-01-01'))
        self.assertIn('fecha_inscripcion', r.context['form'].errors)
        self.assertIn('is-invalid', r.content.decode())

    def test_duplicado_en_la_misma_delegacion(self):
        self.autenticar()
        self.client.post(URL + 'nuevo/', self.datos())
        r = self.client.post(URL + 'nuevo/', self.datos(nombre='junta de vecinos ficticia uno'))
        self.assertIn('nombre', r.context['form'].errors)
        self.assertEqual(self.client.post(URL + 'nuevo/', self.datos(delegacion=self.rural.pk,
                                                                     territorio='Territorio Rural B')).status_code, 302)

    def test_rut_invalido_se_guarda_con_aviso(self):
        self.autenticar()
        r = self.client.post(URL + 'nuevo/', self.datos(presidente_nombre='Persona Uno', presidente_rut='12.345.678-0'),
                             follow=True)
        textos = [str(m) for m in get_messages(r.wsgi_request)] or [str(m) for m in r.context['messages']]
        self.assertTrue(any('dígito verificador' in t for t in textos), textos)
        self.assertEqual(OrganizacionComunitaria.objects.get().presidente_rut, '12345678-0')

    def test_dar_de_baja_conserva_agenda_y_se_puede_filtrar(self):
        self.autenticar()
        org = OrganizacionComunitaria.objects.create(nombre='Club Ficticio Baja', delegacion=self.centro)
        evento = EventoAgenda.objects.create(titulo='Asamblea ficticia', fecha=timezone.localdate(),
                                             hora='18:00', organizacion=org, delegacion=self.centro)
        self.assertEqual(self.client.post(f'{URL}{org.pk}/eliminar/').status_code, 302)
        org.refresh_from_db()
        evento.refresh_from_db()
        self.assertFalse(org.activa)
        self.assertIsNotNone(org.eliminado_en)
        self.assertEqual(evento.organizacion_id, org.pk)
        nombres = lambda r: [f['organizacion'].nombre for f in r.context['filas']]
        self.assertNotIn('Club Ficticio Baja', nombres(self.client.get(URL)))
        self.assertIn('Club Ficticio Baja', nombres(self.client.get(URL, {'estado': 'inactivas'})))

    def test_vuelve_a_la_misma_busqueda_tras_guardar(self):
        self.autenticar()
        org = OrganizacionComunitaria.objects.create(nombre='Junta Ficticia Vuelta', delegacion=self.centro,
                                                     territorio='Territorio Ficticio A')
        r = self.client.post(f'{URL}{org.pk}/editar/', self.datos(nombre='Junta Ficticia Vuelta', volver='q=vuelta&page=2&x=1'))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], URL + '?q=vuelta&page=2')

    def test_filtro_sin_delegacion_y_aviso_para_superusuario(self):
        OrganizacionComunitaria.objects.create(nombre='Organización Ficticia Huérfana')
        self.autenticar()
        r = self.client.get(URL, {'delegacion': 'sin'})
        self.assertContains(r, 'Organización Ficticia Huérfana')
        self.assertEqual(r.context['sin_delegacion'], 1)

    def test_buscador_respeta_la_delegacion(self):
        OrganizacionComunitaria.objects.create(nombre='Junta Buscable Centro', delegacion=self.centro)
        OrganizacionComunitaria.objects.create(nombre='Junta Buscable Rural', delegacion=self.rural)
        self.autenticar(self.adm_rural)
        nombres = [o['texto'] for o in self.client.get(URL + 'buscar/', {'q': 'buscable'}).json()['resultados']]
        self.assertEqual(nombres, ['Junta Buscable Rural'])

    def test_agenda_valida_delegacion_y_no_dibuja_todas(self):
        otra = OrganizacionComunitaria.objects.create(nombre='Junta Agenda Rural', delegacion=self.rural)
        OrganizacionComunitaria.objects.create(nombre='Junta Agenda Centro', delegacion=self.centro)
        form = EventoAgendaForm(data={'titulo': 'Reunión ficticia', 'fecha': timezone.localdate(), 'hora': '10:00',
                                      'organizacion': otra.pk, 'delegacion': self.centro.pk})
        self.assertFalse(form.is_valid())
        self.assertIn('organizacion', form.errors)
        self.assertNotIn('Junta Agenda Centro', str(EventoAgendaForm()['organizacion']))

    def test_telefonos(self):
        self.assertEqual(normalizar_telefono('+56 51 223 4567'), '+56 51 223 4567')
        self.assertEqual(normalizar_telefono('912345678'), '+56 9 1234 5678')
        self.assertIsNone(normalizar_telefono('12345'))

    def test_asignar_delegacion_solo_sin_ambiguedad(self):
        TerritorioDelegacion.objects.create(delegacion=self.rural, nombre='Territorio Ficticio A')  # ahora ambiguo
        unica = OrganizacionComunitaria.objects.create(nombre='Org Ficticia Única', territorio=' territorio rural b ')
        ambigua = OrganizacionComunitaria.objects.create(nombre='Org Ficticia Ambigua', territorio='Territorio Ficticio A')
        call_command('asignar_delegacion_organizaciones', stdout=StringIO())
        unica.refresh_from_db()
        self.assertIsNone(unica.delegacion_id)  # simulación: no guarda
        call_command('asignar_delegacion_organizaciones', '--aplicar', stdout=StringIO())
        unica.refresh_from_db()
        ambigua.refresh_from_db()
        self.assertEqual(unica.delegacion_id, self.rural.pk)
        self.assertIsNone(ambigua.delegacion_id)

    def test_importador_informa_filas_y_no_choca_codigos(self):
        base = {'domicilio_legal': '', 'territorio': '', 'socios_activos': None, 'fecha_constitucion': None,
                'registro_personalidad_juridica': '', 'fecha_inscripcion': None, 'registro_directiva': ''}
        filas = [dict(base, clave_origen='A-1', nombre='Org Importada Uno'),
                 dict(base, clave_origen='B-1', nombre='Org Importada Dos')]
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / 'orgs.json'
            ruta.write_text(json.dumps(filas), encoding='utf-8')
            call_command('importar_organizaciones', str(ruta), '--aplicar', stdout=StringIO())
            self.assertEqual(sorted(OrganizacionComunitaria.objects.values_list('codigo', flat=True)),
                             ['ORG-SRC-A1', 'ORG-SRC-B1'])
            ruta.write_text(json.dumps([dict(base, clave_origen='C-1', nombre='')]), encoding='utf-8')
            err = StringIO()
            with self.assertRaises(CommandError):
                call_command('importar_organizaciones', str(ruta), stdout=StringIO(), stderr=err)
            self.assertIn('Fila 1', err.getvalue())

    def test_completar_sincronizacion_y_registro_de_bajas(self):
        OrganizacionComunitaria.objects.bulk_create([OrganizacionComunitaria(codigo='ORG-BULK', nombre='Org Masiva')])
        self.assertIsNone(OrganizacionComunitaria.objects.get(codigo='ORG-BULK').uuid)
        call_command('completar_sincronizacion', '--aplicar', stdout=StringIO())
        self.assertIsNotNone(OrganizacionComunitaria.objects.get(codigo='ORG-BULK').uuid)
        territorio = TerritorioDelegacion.objects.create(delegacion=self.centro, nombre='Territorio Temporal')
        uuid = territorio.uuid
        territorio.delete()
        self.assertTrue(RegistroBaja.objects.filter(modelo='control_gestion.territoriodelegacion', uuid=uuid).exists())
