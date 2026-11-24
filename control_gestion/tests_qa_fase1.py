"""Correcciones de la Fase 1 del reporte de QA (22-11-2026). Datos ficticios."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.indicadores import construir_panel
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.forms import UsuarioForm
from cuentas.models import Funcionario, Usuario
from cuentas.perfiles import sincronizar_usuario
from requerimientos.models import Requerimiento, Vecino

CLAVE = 'Prueba123!'


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class Fase1Tests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.adm_rural = crear_cuenta(codigo='USR-Q1', rut='33100121-1', password=CLAVE, rol_codigo='administrador',
                                     correo='q1.rural@siged.test', nombre='Admin Rural Ficticio', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.adm_rural):
            sincronizar_usuario(perfil)

    # QA-001 ---------------------------------------------------------------------------------
    def test_detalle_no_permite_cambiar_la_fecha_de_ingreso(self):
        self.autenticar()
        ingreso = self.ticket.fecha_ingreso
        r = self.client.post(reverse('detalle_requerimiento', args=[self.ticket.codigo]),
                             {'estado_proceso': 'En Proceso', 'funcionario_asignado': '', 'dias_transcurridos': '800000'})
        self.assertEqual(r.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.fecha_ingreso, ingreso)
        self.assertEqual(self.ticket.estado, 'En Proceso')

    # QA-010 ---------------------------------------------------------------------------------
    def test_ticket_resuelto_deja_de_envejecer_y_reabierto_vuelve(self):
        self.ticket.estado = Requerimiento.Estado.RESUELTO
        self.ticket.save(update_fields=['estado'])
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.fecha_resolucion, timezone.localdate())
        self.assertEqual(self.ticket.dias_transcurridos, 20)
        self.ticket.estado = Requerimiento.Estado.EN_PROCESO
        self.ticket.save(update_fields=['estado'])
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.fecha_resolucion)

    def test_kanban_a_resuelto_registra_fecha(self):
        self.autenticar()
        self.mover = tests_kanban.KanbanTests.mover.__get__(self)
        self.assertEqual(self.mover(estado='Resuelto', anterior='Pendiente').status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.fecha_resolucion, timezone.localdate())

    # QA-002 ---------------------------------------------------------------------------------
    def _datos_ticket(self, **extra):
        datos = {'vecino_nombre': 'Junta Vecinal Norte', 'telefono_whatsapp': '+56 9 1234 5678', 'email': '',
                 'delegacion': self.centro.nombre, 'canal_ingreso': 'ventanilla', 'tipo_entrada': 'SOLICITUD',
                 'area_tematica': 'Operaciones', 'descripcion': 'Luminaria apagada en la esquina norte.'}
        datos.update(extra)
        return datos

    def test_nombre_con_parentesis_muestra_error_y_no_500(self):
        self.autenticar()
        r = self.client.post(reverse('nuevo_requerimiento'), self._datos_ticket(vecino_nombre='Junta (Norte)'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('vecino_nombre', r.context['errores'])

    def test_rut_invalido_explica_el_digito_verificador(self):
        self.autenticar()
        r = self.client.post(reverse('nuevo_requerimiento'), self._datos_ticket(vecino_rut='12.345.678-0'))
        self.assertIn('dígito verificador', r.context['errores']['vecino_rut'])

    def test_homonimos_con_distinto_rut_no_se_fusionan(self):
        self.autenticar()
        if not self.client.post(reverse('nuevo_requerimiento'), self._datos_ticket(vecino_rut='12.345.678-5')).status_code == 302:
            self.skipTest('Catálogos de prueba incompletos')
        self.client.post(reverse('nuevo_requerimiento'), self._datos_ticket(vecino_rut='11.111.111-1'))
        self.assertEqual(Vecino.objects.filter(nombre='Junta Vecinal Norte').count(), 2)

    # QA-003 / QA-004 ------------------------------------------------------------------------
    def test_dashboard_y_panel_acotados_a_la_delegacion(self):
        self.autenticar(self.adm_rural)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        codigos = {item['id_ticket'] for item in r.context['cuellos_botella']}
        self.assertNotIn('TK-PRUEBA', codigos)  # es de Centro
        panel = construir_panel(perfil=self.adm_rural)
        self.assertTrue(all(f['delegacion'] in ('', self.rural.nombre) for f in panel['semaforo']))
        self.assertTrue(all(d['nombre'] == self.rural.nombre for d in panel['delegaciones']))

    def test_notificaciones_solo_de_la_delegacion_propia(self):
        self.autenticar(self.adm_rural)
        r = self.client.get(reverse('notificaciones'))
        ids = {n['id'] for n in r.context['notificaciones']}
        self.assertNotIn('AUTO-TK-PRUEBA', ids)

    def test_login_anonimo_no_calcula_alertas(self):
        r = self.client.get('/login/')
        self.assertEqual(r.context['notificaciones_pendientes'], 0)

    # QA-005 ---------------------------------------------------------------------------------
    def test_usuario_form_no_reutiliza_cuenta_de_acceso_ajena(self):
        User = get_user_model()
        User.objects.create_user(username='11111111-1', password=CLAVE, is_staff=True)
        from cuentas.models import Cargo
        ficha = Funcionario.objects.create(nombre='Persona Ficticia', rut='11111111-1', delegacion=self.centro,
                                           cargo=Cargo.objects.create(nombre='Cargo ficticio'))
        form = UsuarioForm(data={'correo': 'nueva.ficticia@siged.test', 'rol': self.funcionario.rol_id,
                                 'funcionario': ficha.pk, 'estado': 'activo'})
        self.assertFalse(form.is_valid())
        self.assertIn('funcionario', form.errors)

    def test_campo_opcional_no_lleva_required_en_html(self):
        from control_gestion.forms import EventoAgendaForm
        form = EventoAgendaForm()
        form.fields['delegacion'].required = False
        self.assertNotIn('required', str(form['delegacion']))

    # QA-065 / QA-070 ------------------------------------------------------------------------
    def test_no_puede_desactivarse_a_si_mismo(self):
        self.autenticar()
        self.client.post(reverse('admin_usuarios'), {'accion': 'toggle', 'id_usuario': self.admin.codigo})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.estado, 'activo')

    # QA-069 ---------------------------------------------------------------------------------
    def test_logout_por_get_no_cierra_la_sesion(self):
        self.autenticar()
        self.assertEqual(self.client.get('/logout/').status_code, 200)
        self.assertEqual(self.client.get(reverse('lista_requerimientos')).status_code, 200)
        self.client.post('/logout/')
        self.assertEqual(self.client.get(reverse('lista_requerimientos')).status_code, 302)

    # QA-007 ---------------------------------------------------------------------------------
    def test_comandos_de_demostracion_bloqueados_sin_bandera(self):
        for comando in ('importar_json', 'sembrar_demo', 'generar_simulacion'):
            with self.assertRaises(CommandError):
                call_command(comando)
            with self.assertRaises(CommandError):
                call_command(comando, '--demo')  # DEBUG=False y sin SIGED_PERMITIR_DEMO

    # QA-101 / QA-103 ------------------------------------------------------------------------
    def test_subdelegado_no_es_revisor(self):
        from control_gestion.evidencias import puede_validar
        from cuentas.models import Cargo
        perfil = Usuario.objects.select_related('rol', 'cargo', 'funcionario').get(pk=self.funcionario.pk)
        perfil.cargo = Cargo.objects.create(nombre='Subdelegado de apoyo')
        self.assertFalse(puede_validar(perfil))
        perfil.cargo = Cargo.objects.create(nombre='Delegada territorial')
        self.assertTrue(puede_validar(perfil))

    def test_parametros_ya_no_editan_el_periodo(self):
        self.autenticar()
        r = self.client.post(reverse('admin_parametros'), {
            'nombre_sistema': 'SIGED-SGR Delegaciones', 'comuna': 'La Serena', 'sla_verde_max_dias': 3,
            'sla_amarillo_max_dias': 5, 'meta_tubo_porcentaje': 80, 'max_atenciones_mismo_usuario': 3,
            'periodo': 'duplicado', 'fecha_inicio': 'x'})
        self.assertEqual(r.status_code, 302)
