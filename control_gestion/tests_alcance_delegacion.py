"""El administrador queda encapsulado en su delegación; solo el superusuario ve todas. Datos ficticios."""
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from control_gestion import tests_kanban
from control_gestion.models import Compromiso, Medicion, OrganizacionComunitaria
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Cargo, Delegacion, Funcionario, Usuario
from cuentas.perfiles import sincronizar_usuario
from requerimientos.models import Atencion, SubAtencion, TipoAtencion, Vecino

CLAVE = 'Prueba123!'


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AlcancePorDelegacionTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)  # cls.admin es el superusuario
        cls.adm_centro = crear_cuenta(codigo='USR-AC', rut='33100120-3', password=CLAVE, rol_codigo='administrador',
                                      correo='adm.centro@siged.test', nombre='Admin Centro', delegacion=cls.centro)
        cls.adm_rural = crear_cuenta(codigo='USR-AR', rut='33100121-1', password=CLAVE, rol_codigo='administrador',
                                     correo='adm.rural@siged.test', nombre='Admin Rural', delegacion=cls.rural)
        cls.func_rural = crear_cuenta(codigo='USR-FR', rut='33100122-K', password=CLAVE, rol_codigo='funcionario',
                                      correo='func.rural@siged.test', nombre='Func Rural', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.adm_centro, cls.adm_rural, cls.func_rural):
            sincronizar_usuario(perfil)
        tipo = TipoAtencion.objects.create(nombre='Salud ficticia')
        sub = SubAtencion.objects.create(nombre='Consulta ficticia', tipo_atencion=tipo)
        vecino = Vecino.objects.create(nombre='Vecino Ficticio Alcance', delegacion=cls.centro)
        cls.at_centro = Atencion.objects.create(vecino=vecino, tipo_atencion=tipo, sub_atencion=sub,
                                                delegacion=cls.centro, usuario=cls.admin, estado='pendiente')
        cls.at_rural = Atencion.objects.create(vecino=vecino, tipo_atencion=tipo, sub_atencion=sub,
                                               delegacion=cls.rural, usuario=cls.admin, estado='pendiente')
        hoy = timezone.localdate()
        cls.comp_centro = Compromiso.objects.create(descripcion='Compromiso Centro', vecino=vecino,
                                                    funcionario=cls.funcionario.funcionario, delegacion=cls.centro,
                                                    fecha_compromiso=hoy + timedelta(days=5))
        cls.comp_rural = Compromiso.objects.create(descripcion='Compromiso Rural', vecino=vecino,
                                                   funcionario=cls.func_rural.funcionario, delegacion=cls.rural,
                                                   fecha_compromiso=hoy + timedelta(days=5))

    def codigos_del_tubo(self):
        columnas = self.client.get('/control/tubo-cartas/').context['columnas_lista']
        return {i['id_compromiso'] for c in columnas for i in c['items']}

    # --- Lo que se ve ---
    def test_el_administrador_solo_ve_su_delegacion_y_el_superusuario_todas(self):
        self.autenticar(self.adm_centro)
        visibles = self.codigos_del_tubo()
        self.assertIn(self.comp_centro.codigo, visibles)
        self.assertNotIn(self.comp_rural.codigo, visibles)
        self.assertIn(f'ATN-{self.at_centro.pk:04d}', visibles)
        self.assertNotIn(f'ATN-{self.at_rural.pk:04d}', visibles)
        self.autenticar(self.admin)
        todos = self.codigos_del_tubo()
        self.assertTrue({self.comp_centro.codigo, self.comp_rural.codigo} <= todos)

    def test_el_administrador_no_mueve_ni_consulta_otra_delegacion(self):
        self.autenticar(self.adm_centro)
        respuesta = self.client.post('/control/tubo-cartas/', {
            'id_compromiso': self.comp_rural.codigo, 'estado': 'PENDIENTE', 'estado_anterior': self.comp_rural.estado},
            HTTP_ACCEPT='application/json')
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.client.get('/lista/', {'delegacion': 'Delegación Rural'}).status_code, 302)
        self.assertEqual(self.client.get('/control/kanban/').status_code, 200)
        self.assertNotContains(self.client.get('/control/kanban/'), 'TK-RURAL')

    def test_los_mantenedores_del_administrador_solo_listan_su_delegacion(self):
        OrganizacionComunitaria.objects.create(nombre='Org Centro Ficticia', delegacion=self.centro)
        OrganizacionComunitaria.objects.create(nombre='Org Rural Ficticia', delegacion=self.rural)
        self.autenticar(self.adm_centro)
        pagina = self.client.get('/mantenedores/organizaciones/')
        self.assertContains(pagina, 'Org Centro Ficticia')
        self.assertNotContains(pagina, 'Org Rural Ficticia')
        delegaciones = self.client.get('/mantenedores/delegaciones/')
        self.assertContains(delegaciones, 'Delegación Centro')
        self.assertNotContains(delegaciones, 'Delegación Rural')
        self.autenticar(self.admin)
        self.assertContains(self.client.get('/mantenedores/delegaciones/'), 'Delegación Rural')

    # --- Usuarios ---
    def test_la_pantalla_de_usuarios_solo_muestra_cuentas_de_la_delegacion(self):
        self.autenticar(self.adm_centro)
        pagina = self.client.get('/administracion/usuarios/')
        self.assertContains(pagina, 'Ana Prueba')
        self.assertNotContains(pagina, 'Func Rural')
        self.assertNotContains(pagina, '>USR-A</strong>')  # la cuenta de superusuario no se lista
        self.assertContains(pagina, '>USR-AC</strong>')
        roles = [clave for clave, _ in pagina.context['roles']]
        self.assertNotIn('superusuario', roles)
        self.assertEqual(pagina.context['delegaciones'], ['Delegación Centro'])
        self.autenticar(self.admin)
        pagina = self.client.get('/administracion/usuarios/')
        self.assertContains(pagina, 'Func Rural')
        self.assertIn('superusuario', [clave for clave, _ in pagina.context['roles']])

    def test_el_administrador_no_activa_ni_desactiva_cuentas_ajenas(self):
        self.autenticar(self.adm_centro)
        for objetivo in (self.func_rural, self.admin):
            self.client.post('/administracion/usuarios/', {'accion': 'toggle', 'id_usuario': objetivo.codigo})
            objetivo.refresh_from_db()
            self.assertEqual(objetivo.estado, 'activo')
        self.client.post('/administracion/usuarios/', {'accion': 'toggle', 'id_usuario': self.funcionario.codigo})
        self.funcionario.refresh_from_db()
        self.assertEqual(self.funcionario.estado, 'inactivo')

    def test_el_administrador_solo_crea_cuentas_de_su_delegacion_y_sin_superusuario(self):
        cargo = Cargo.objects.get_or_create(nombre='Cargo de prueba')[0]
        base = {'rut': '33100130-9', 'nombre': 'Persona Nueva Ficticia', 'email': 'nueva@siged.test',
                'cargo': cargo.nombre, 'delegacion': 'Delegación Rural', 'rol': 'funcionario'}
        self.autenticar(self.adm_centro)
        self.client.post('/administracion/usuarios/', base)
        creada = Usuario.objects.get(username='33100130-9')
        self.assertEqual(creada.delegacion_id, self.centro.pk)  # se fuerza la propia, aunque pida otra
        self.assertEqual(len(mail.outbox), 1)
        escalada = dict(base, rut='33100131-7', email='otra@siged.test', rol='superusuario')
        respuesta = self.client.post('/administracion/usuarios/', escalada)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('rol', respuesta.context['errores'])
        self.assertFalse(Usuario.objects.filter(username='33100131-7').exists())
        ajena = dict(base, rut='33100132-5', email='tercera@siged.test', id_funcionario=self.func_rural.funcionario.codigo)
        respuesta = self.client.post('/administracion/usuarios/', ajena)
        self.assertIn('id_funcionario', respuesta.context['errores'])

    # --- Lo global ---
    def test_lo_global_solo_lo_modifica_el_superusuario(self):
        self.autenticar(self.adm_centro)
        for ruta in ('/administracion/parametros/', '/administracion/cargos/', '/administracion/grupos/'):
            self.assertEqual(self.client.get(ruta).status_code, 302, ruta)
        # Puede consultar los catálogos globales, pero no crearlos ni modificarlos.
        self.assertEqual(self.client.post('/mantenedores/delegaciones/nuevo/', {'nombre': 'Delegación Nueva'}).status_code, 302)
        self.assertFalse(Delegacion.objects.filter(nombre='Delegación Nueva').exists())
        self.assertEqual(self.client.post('/mantenedores/periodos/nuevo/', {
            'fecha_inicio': '2031-01-01', 'fecha_termino': '2031-03-31', 'meta_cumplimiento_tubo': 80}).status_code, 302)
        self.assertFalse(Medicion.objects.filter(fecha_inicio='2031-01-01').exists())
        self.autenticar(self.admin)
        for ruta in ('/administracion/parametros/', '/administracion/cargos/', '/administracion/grupos/'):
            self.assertEqual(self.client.get(ruta).status_code, 200, ruta)
        self.client.post('/mantenedores/periodos/nuevo/', {
            'fecha_inicio': '2031-01-01', 'fecha_termino': '2031-03-31', 'meta_cumplimiento_tubo': 80})
        self.assertTrue(Medicion.objects.filter(fecha_inicio='2031-01-01').exists())

    def test_el_menu_del_administrador_oculta_lo_global(self):
        self.autenticar(self.adm_centro)
        menu = self.client.get('/').content.decode()
        self.assertNotIn('Grupos y permisos', menu)
        self.assertNotIn('Parámetros', menu)
        self.autenticar(self.admin)
        self.assertIn('Grupos y permisos', self.client.get('/').content.decode())

    def test_el_administrador_no_puede_asignar_el_rol_superusuario(self):
        self.autenticar(self.adm_centro)
        self.assertEqual(self.client.post('/administracion/grupos/', {
            'accion': 'asignar', 'usuario': self.funcionario.pk, 'rol': self.admin.rol_id}).status_code, 302)
        self.funcionario.refresh_from_db()
        self.assertEqual(self.funcionario.rol.codigo, 'funcionario')
