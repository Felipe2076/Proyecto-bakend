"""Alta de usuarios desde «Administración → Usuarios»: RUT, duplicados y errores de base, con datos ficticios."""
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from control_gestion import tests_kanban
from core.validaciones import dv_rut, motivo_rut_invalido, rut_canonico
from cuentas.models import Cargo, Delegacion, Funcionario, Usuario

URL = '/administracion/usuarios/'


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AltaUsuariosTests(TestCase):
    setUpTestData = classmethod(tests_kanban.KanbanTests.setUpTestData.__func__)
    autenticar = tests_kanban.KanbanTests.autenticar

    def datos(self, **cambios):
        base = dict(accion='crear', rut='33.200.032-2', nombre='Persona Ficticia Prueba', email='nueva@siged.test',
                    rol='funcionario', cargo='Cargo de prueba', delegacion=self.centro.nombre)
        base.update(cambios)
        return base

    def enviar(self, **cambios):
        self.autenticar()
        return self.client.post(URL, self.datos(**cambios))

    # --- RUT --------------------------------------------------------------------------------
    def test_digito_verificador_incorrecto_dice_cual_corresponde(self):
        self.assertEqual(dv_rut('33200032'), '2')
        respuesta = self.enviar(rut='33.200.032-9')
        self.assertEqual(respuesta.status_code, 200)
        mensaje = respuesta.context['errores']['rut']
        self.assertIn('dígito verificador', mensaje)
        self.assertIn('33.200.032-2', mensaje)
        self.assertFalse(Usuario.objects.filter(username__startswith='33200032').exists())
        self.assertEqual(respuesta.context['valores']['rut'], '33.200.032-9')  # no pierde lo escrito

    def test_motivos_distintos_segun_el_error(self):
        self.assertIn('formato', motivo_rut_invalido('abc'))
        self.assertIn('vacío', motivo_rut_invalido('  '))
        self.assertIn('33.200.032-2', motivo_rut_invalido('33200032-9'))
        self.assertIsNone(motivo_rut_invalido('33.200.032-2'))

    def test_acepta_rut_con_puntos_sin_guion_o_con_k_minuscula(self):
        self.assertEqual(rut_canonico(' 33.200.032-2 '), '33200032-2')
        self.assertEqual(rut_canonico('332000322'), '33200032-2')
        self.assertEqual(rut_canonico('33200032 2'), '33200032-2')
        self.assertEqual(rut_canonico('7.654.321-6'), '7654321-6')
        self.assertEqual(rut_canonico('21.356.658-k'), '21356658-K')
        self.assertIsNone(rut_canonico('33200032-9'))
        self.assertIsNone(rut_canonico('1234'))
        self.assertEqual(self.enviar(rut='332000322').status_code, 302)
        self.assertTrue(Usuario.objects.filter(username='33200032-2').exists())

    # --- Alta correcta ----------------------------------------------------------------------
    def test_alta_correcta_crea_todo_y_envia_invitacion(self):
        respuesta = self.enviar()
        self.assertEqual(respuesta.status_code, 302)
        usuario = Usuario.objects.select_related('user', 'funcionario').get(username='33200032-2')
        self.assertEqual(usuario.funcionario.rut, '33200032-2')
        self.assertFalse(usuario.user.has_usable_password())
        self.assertEqual(mail.outbox[-1].to, ['nueva@siged.test'])

    def test_rut_repetido_con_otro_formato_se_detecta(self):
        self.assertEqual(self.enviar().status_code, 302)
        otra = self.enviar(rut='33200032-2', email='otra@siged.test')
        self.assertEqual(otra.status_code, 200)
        self.assertIn('ya está registrado', otra.context['errores']['rut'])

    # --- Errores que antes terminaban en HTTP 500 -------------------------------------------
    def test_cuenta_de_acceso_huerfana_no_provoca_error_500(self):
        get_user_model().objects.create_user('33200032-2', 'huerfana@siged.test', 'x')
        respuesta = self.enviar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('acceso', respuesta.context['errores']['rut'])
        self.assertFalse(Funcionario.objects.filter(rut='33200032-2').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_textos_demasiado_largos_se_rechazan_con_mensaje(self):
        respuesta = self.enviar(email='a' * 250 + '@siged.test', delegacion='D' * 101)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('email', respuesta.context['errores'])
        self.assertIn('delegacion', respuesta.context['errores'])

    def test_delegacion_inexistente_no_se_crea_por_escribirla_mal(self):
        antes = Delegacion.objects.count()
        respuesta = self.enviar(delegacion='Delegacion Escrita Mal')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('delegacion', respuesta.context['errores'])
        self.assertEqual(Delegacion.objects.count(), antes)

    def test_error_inesperado_de_base_no_deja_datos_parciales_ni_500(self):
        from unittest import mock
        from django.db import IntegrityError
        self.autenticar()
        with mock.patch('cuentas.views.emitir_codigo', side_effect=IntegrityError('simulado')):
            respuesta = self.client.post(URL, self.datos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'No se pudo crear el usuario')
        self.assertFalse(Funcionario.objects.filter(rut='33200032-2').exists())
        self.assertFalse(get_user_model().objects.filter(username='33200032-2').exists())

    # --- Ficha SGR existente ----------------------------------------------------------------
    def crear_ficha(self, rut='33200032-2'):
        cargo = Cargo.objects.get_or_create(nombre='Cargo de prueba')[0]
        return Funcionario.objects.create(codigo='FUN-900', rut=rut, nombres='Ficha', apellido_paterno='Ficticia',
                                          cargo=cargo, delegacion=self.centro)

    def test_vincula_ficha_existente_con_el_mismo_rut(self):
        ficha = self.crear_ficha()
        respuesta = self.enviar(id_funcionario=ficha.codigo)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Usuario.objects.get(username='33200032-2').funcionario_id, ficha.pk)
        self.assertEqual(Funcionario.objects.filter(rut='33200032-2').count(), 1)

    def test_ficha_con_otro_rut_no_se_sobrescribe(self):
        ficha = self.crear_ficha(rut='33100001-9')
        respuesta = self.enviar(id_funcionario=ficha.codigo)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('no coincide', respuesta.context['errores']['rut'])
        ficha.refresh_from_db()
        self.assertEqual(ficha.rut, '33100001-9')

    def test_ficha_con_cuenta_no_se_reutiliza(self):
        ficha = self.crear_ficha()
        self.assertEqual(self.enviar(id_funcionario=ficha.codigo).status_code, 302)
        otra = self.enviar(id_funcionario=ficha.codigo, rut='33100001-9', email='otra@siged.test')
        self.assertEqual(otra.status_code, 200)
        self.assertIn('id_funcionario', otra.context['errores'])


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AdminDjangoTests(TestCase):
    setUpTestData = classmethod(tests_kanban.KanbanTests.setUpTestData.__func__)

    def setUp(self):
        User = get_user_model()
        self.tecnico = User.objects.create_superuser('tecnico-ficticio', 'tec@siged.test', 'x')
        self.client.force_login(self.tecnico)

    def datos_ficha(self, **cambios):
        cargo = Cargo.objects.get_or_create(nombre='Cargo admin')[0]
        base = dict(codigo='FUN-910', rut='33.200.032-2', nombres='Ana', apellido_paterno='Ficticia', apellido_materno='',
                    nombre='Ana Ficticia', cargo=cargo.pk, delegacion=self.centro.pk, estado='activo')
        base.update(cambios)
        return base

    def test_ficha_en_admin_acepta_rut_con_puntos_y_lo_normaliza(self):
        from cuentas.admin import FuncionarioAdminForm
        self.assertEqual(self.client.get('/admin/cuentas/funcionario/add/').status_code, 200)
        form = FuncionarioAdminForm(self.datos_ficha())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().rut, '33200032-2')

    def test_ficha_en_admin_explica_el_rut_invalido_y_el_repetido(self):
        from cuentas.admin import FuncionarioAdminForm
        malo = FuncionarioAdminForm(self.datos_ficha(rut='33.200.032-9'))
        self.assertFalse(malo.is_valid())
        self.assertIn('33.200.032-2', ' '.join(malo.errors['rut']))
        FuncionarioAdminForm(self.datos_ficha()).save()
        repetido = FuncionarioAdminForm(self.datos_ficha(codigo='FUN-911', rut='332000322'))
        self.assertFalse(repetido.is_valid())
        self.assertIn('FUN-910', ' '.join(repetido.errors['rut']))

    def test_usuario_en_admin_normaliza_el_nombre_de_usuario(self):
        from cuentas.admin import UsuarioAdminForm
        form = UsuarioAdminForm({'username': '33.200.032-2'})
        form.is_valid()
        self.assertEqual(form.cleaned_data.get('username'), '33200032-2')
        malo = UsuarioAdminForm({'username': '33.200.032-9'})
        malo.is_valid()
        self.assertIn('dígito verificador', ' '.join(malo.errors['username']))
        antiguo = UsuarioAdminForm({'username': 'cuenta-antigua'})
        antiguo.is_valid()
        self.assertEqual(antiguo.cleaned_data.get('username'), 'cuenta-antigua')

    def test_borrar_usuario_en_admin_libera_el_rut_para_volver_a_crearlo(self):
        otro = self.funcionario
        pk_user = otro.user_id
        respuesta = self.client.post(f'/admin/cuentas/usuario/{otro.pk}/delete/', {'post': 'yes'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Usuario.objects.filter(pk=otro.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=pk_user).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.tecnico.pk).exists())

    def test_borrar_usuario_no_elimina_cuentas_tecnicas(self):
        perfil = self.funcionario
        perfil.user.is_staff = True
        perfil.user.save()
        self.client.post(f'/admin/cuentas/usuario/{perfil.pk}/delete/', {'post': 'yes'})
        self.assertTrue(get_user_model().objects.filter(pk=perfil.user_id).exists())

    def test_comando_de_cuentas_huerfanas_informa_sin_borrar(self):
        from io import StringIO
        from django.core.management import call_command
        User = get_user_model()
        User.objects.create_user('33200032-2', 'h@siged.test', 'x')
        salida = StringIO()
        call_command('cuentas_huerfanas', stdout=salida)
        texto = salida.getvalue()
        self.assertIn('eliminables: 1', texto)
        self.assertNotIn('33200032', texto)  # el RUT sale enmascarado
        self.assertTrue(User.objects.filter(username='33200032-2').exists())
        call_command('cuentas_huerfanas', '--eliminar', stdout=StringIO())
        self.assertFalse(User.objects.filter(username='33200032-2').exists())
        self.assertTrue(User.objects.filter(pk=self.tecnico.pk).exists())
