from datetime import timedelta

from django.conf import settings
from django.forms.models import model_to_dict
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Delegacion, EstadoRegistro, Rol
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class KanbanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro=Delegacion.objects.create(nombre='Delegación Centro')
        cls.rural=Delegacion.objects.create(nombre='Delegación Rural')
        cls.admin=crear_cuenta(codigo='USR-A', rut='33100011-6', password='Prueba123!',
            rol_codigo='superusuario', correo='admin@siged.test', nombre='Admin Prueba', delegacion=cls.centro)
        cls.funcionario=crear_cuenta(codigo='USR-F', rut='33100032-9', password='Prueba123!',
            rol_codigo='funcionario', correo='funcionario@siged.test', nombre='Ana Prueba', delegacion=cls.centro)
        vecino=Vecino.objects.create(nombre='Vecino Prueba', delegacion=cls.centro)
        canal=CanalIngreso.objects.create(nombre='Ventanilla')
        tipo=TipoGestion.objects.create(nombre='Solicitud')
        area=AreaSoporte.objects.create(codigo='AREA-001',nombre='Operaciones')
        cls.ticket=Requerimiento.objects.create(codigo='TK-PRUEBA',vecino=vecino,delegacion=cls.centro,
            canal_ingreso=canal,tipo_gestion=tipo,area=area,descripcion='Revisar luminaria',
            fecha_ingreso=timezone.localdate()-timedelta(days=20),asignado_a='Equipo original')
        cls.otro=Requerimiento.objects.create(codigo='TK-RURAL',vecino=vecino,delegacion=cls.rural,
            canal_ingreso=canal,tipo_gestion=tipo,area=area,descripcion='Ticket de otra delegación')

    def autenticar(self, perfil=None, client=None):
        client=client or self.client
        perfil=perfil or self.admin
        client.force_login(perfil.user)
        sesion=client.session
        sesion['usuario']={'rol':perfil.rol.codigo,'nombre':perfil.nombre,'delegacion':perfil.delegacion.nombre if perfil.delegacion else ''}
        sesion.save()
        client.cookies[settings.SESSION_COOKIE_NAME]=sesion.session_key
        return client

    def mover(self, estado='En Proceso', anterior='Pendiente', ticket=None, client=None, **kwargs):
        return (client or self.client).post(reverse('kanban_mover',args=[(ticket or self.ticket).codigo]),
            {'estado':estado,'estado_anterior':anterior},HTTP_ACCEPT='application/json',**kwargs)

    def test_mover_guarda_solo_estado_y_se_conserva_al_recargar(self):
        self.autenticar()
        antes=model_to_dict(self.ticket)
        response=self.mover()
        self.assertEqual(response.status_code,200)
        self.ticket.refresh_from_db()
        antes['estado']='En Proceso'
        self.assertEqual(model_to_dict(self.ticket),antes)
        response=self.client.get(reverse('kanban'))
        columnas={col['estado']:col for col in response.context['columnas']}
        self.assertIn(self.ticket.codigo,[t['id_ticket'] for t in columnas['En Proceso']['tickets']])
        self.assertNotIn(self.ticket.codigo,[t['id_ticket'] for t in columnas['Cuello Botella Central']['tickets']])
        self.assertContains(response,'bg-danger')  # La alerta por antigüedad sigue visible.

    def test_permite_cerrar_y_reabrir(self):
        self.autenticar()
        for anterior, nuevo in [('Pendiente','Resuelto'),('Resuelto','Cuello Botella Central'),
                                ('Cuello Botella Central','Pendiente')]:
            self.assertEqual(self.mover(nuevo,anterior).status_code,200)
            self.ticket.refresh_from_db()
            self.assertEqual(self.ticket.estado,nuevo)

    def test_no_sobrescribe_un_cambio_concurrente(self):
        self.autenticar()
        Requerimiento.objects.filter(pk=self.ticket.pk).update(estado='Resuelto')
        response=self.mover()
        self.assertEqual(response.status_code,409)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado,'Resuelto')

    def test_rechaza_estados_invalidos_y_anterior_ausente(self):
        self.autenticar()
        for nuevo, anterior in [('Borrado','Pendiente'),('En Proceso',''),('', 'Pendiente')]:
            self.assertEqual(self.mover(nuevo,anterior).status_code,422)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado,'Pendiente')

    def test_get_no_modifica_estado(self):
        self.autenticar()
        self.assertEqual(self.client.get(reverse('kanban_mover',args=[self.ticket.codigo])).status_code,405)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado,'Pendiente')

    def test_anonimo_no_mueve(self):
        self.assertEqual(self.mover().status_code,401)  # Las peticiones JSON reciben un error de autenticación.
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado,'Pendiente')

    def test_sesion_sin_identidad_django_no_mueve(self):
        sesion=self.client.session
        sesion['usuario']={'rol':'administrador'}
        sesion.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME]=sesion.session_key
        self.assertEqual(self.mover().status_code,401)

    def test_no_consulta_ni_mueve_otra_delegacion(self):
        self.autenticar(self.funcionario)
        response=self.client.get(reverse('kanban'))
        self.assertContains(response,self.ticket.codigo)
        self.assertNotContains(response,self.otro.codigo)
        self.assertEqual(self.mover(ticket=self.otro).status_code,404)
        self.assertEqual(self.mover().status_code,200)

    def test_sin_delegacion_no_tiene_tickets(self):
        self.funcionario.delegacion=None
        self.funcionario.save(update_fields=['delegacion'])
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get(reverse('kanban')).context['total_general'],0)
        self.assertEqual(self.mover().status_code,404)

    def test_rol_revocado_se_consulta_en_base(self):
        self.autenticar()
        self.admin.rol=Rol.objects.create(codigo='sin-acceso',nombre='Sin acceso')
        self.admin.save(update_fields=['rol'])
        self.assertEqual(self.mover().status_code,403)

    def test_cuenta_inactiva_no_mueve(self):
        self.autenticar()
        self.admin.estado=EstadoRegistro.INACTIVO
        self.admin.save(update_fields=['estado'])
        self.assertEqual(self.mover().status_code,401)

    def test_token_csrf_obligatorio_y_valido(self):
        client=self.autenticar(client=Client(enforce_csrf_checks=True))
        response=client.get(reverse('kanban'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.mover(client=client).status_code,403)
        self.assertEqual(self.mover(client=client,HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)

    def test_formulario_sin_javascript_guarda_y_redirige(self):
        self.autenticar()
        response=self.client.post(reverse('kanban_mover',args=[self.ticket.codigo]),
            {'estado':'En Proceso','estado_anterior':'Pendiente'})
        self.assertRedirects(response,reverse('kanban'))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado,'En Proceso')

    def test_ticket_inexistente_y_estado_sin_cambio(self):
        self.autenticar()
        response=self.client.post(reverse('kanban_mover',args=['TK-NO-EXISTE']),
            {'estado':'En Proceso','estado_anterior':'Pendiente'},HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code,404)
        self.assertEqual(self.mover('Pendiente','Pendiente').status_code,200)
