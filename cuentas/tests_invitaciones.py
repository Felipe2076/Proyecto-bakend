from django.test import TestCase,Client,override_settings
from django.core import mail,signing
from django.utils import timezone
from unittest.mock import patch
from datetime import timedelta
import re
from cuentas.models import Usuario,Funcionario,CodigoUnUso
from control_gestion import tests_kanban

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InvitacionTests(TestCase):
    setUpTestData=classmethod(tests_kanban.KanbanTests.setUpTestData.__func__)
    autenticar=tests_kanban.KanbanTests.autenticar

    def payload(self,**overrides):
        return dict(accion='crear',rut='33100001-9',nombre='Pedro Rojas Perez',email='destinatario@siged.test',
            rol='funcionario',cargo='Cargo de prueba',delegacion=self.centro.nombre,**overrides)

    def crear(self):
        self.autenticar()
        response=self.client.post('/administracion/usuarios/',self.payload())
        self.assertEqual(response.status_code,302)
        return Usuario.objects.select_related('user').get(username='33100001-9')

    def test_admin_no_define_clave_y_correo_al_destinatario(self):
        self.autenticar()
        response=self.client.get('/administracion/usuarios/')
        self.assertNotContains(response,'name="password"')
        data=self.payload()
        data['password']='ClaveElegidaPorAdmin123!'
        self.client.post('/administracion/usuarios/',data)
        user=Usuario.objects.select_related('user').get(username=data['rut'])
        self.assertFalse(user.user.has_usable_password())
        self.assertEqual(mail.outbox[-1].to,[data['email']])
        self.assertNotIn(data['password'],mail.outbox[-1].body)
        self.assertEqual(user.delegacion_id,self.centro.pk)

    def test_activacion_completa_en_sesion_del_destinatario(self):
        user=self.crear()
        body=mail.outbox[-1].body
        link=re.search(r'https?://\S+',body).group()
        code=re.search(r'\d{6}',body).group()
        recipient=Client()
        response=recipient.get(link)
        self.assertEqual(response.status_code,302)
        self.assertNotIn('usuario',recipient.session)
        self.assertNotIn(code,str(recipient.session.items()))
        response=recipient.post('/recuperar/codigo/',{f'd{i}':c for i,c in enumerate(code,1)})
        self.assertEqual(response.status_code,302)
        response=recipient.post('/recuperar/nueva/',{'password':'ClavePropiaSegura8!','confirmacion':'ClavePropiaSegura8!'})
        self.assertEqual(response.status_code,302)
        user.user.refresh_from_db()
        self.assertTrue(user.user.check_password('ClavePropiaSegura8!'))
        self.assertEqual(recipient.post('/login/',{'rut':user.username,'password':'ClavePropiaSegura8!'}).status_code,302)
        self.assertRedirects(recipient.get(link),'/recuperar/',fetch_redirect_response=False)

    def test_smtp_falla_no_deja_usuario_ni_funcionario_parcial(self):
        self.autenticar()
        before=(Usuario.objects.count(),Funcionario.objects.count())
        with patch('cuentas.views.enviar_codigo',side_effect=OSError('SMTP unavailable')):
            response=self.client.post('/administracion/usuarios/',self.payload())
        self.assertContains(response,'No se creó el usuario')
        self.assertEqual((Usuario.objects.count(),Funcionario.objects.count()),before)
        self.assertFalse(CodigoUnUso.objects.exists())

    def test_requiere_correo_y_no_permite_duplicado(self):
        self.autenticar()
        for address in ('','incorrecto',self.admin.correo):
            data=self.payload()
            data['email']=address
            response=self.client.post('/administracion/usuarios/',data)
            self.assertEqual(response.status_code,200)
            self.assertFalse(Usuario.objects.filter(username=data['rut']).exists())

    def test_invitacion_alterada_no_inicia_recuperacion(self):
        self.assertRedirects(Client().get('/activar/?token=invalido'),'/recuperar/',fetch_redirect_response=False)

    def test_codigo_caducado_y_cinco_intentos(self):
        user=self.crear()
        link=re.search(r'https?://\S+',mail.outbox[-1].body).group()
        recipient=Client()
        recipient.get(link)
        row=CodigoUnUso.objects.get(usuario=user)
        row.expira_en=timezone.now()-timedelta(seconds=1)
        row.save(update_fields=['expira_en'])
        response=recipient.post('/recuperar/codigo/',{f'd{i}':'0' for i in range(1,7)})
        self.assertContains(response,'expiró')
        self.assertFalse(recipient.session['recuperacion']['verificado'])

    def test_otro_rol_no_puede_crear_cuenta(self):
        self.autenticar(self.funcionario)
        response=self.client.post('/administracion/usuarios/',self.payload())
        self.assertEqual(response.status_code,302)
        self.assertFalse(Usuario.objects.filter(username='33100001-9').exists())

    def test_mantenedor_tampoco_ofrece_password(self):
        from cuentas.forms import UsuarioForm
        self.assertNotIn('password',UsuarioForm(instance=self.admin).fields)
        self.autenticar()
        response=self.client.post('/mantenedores/usuarios/nuevo/',self.payload())
        self.assertRedirects(response,'/administracion/usuarios/',fetch_redirect_response=False)
        self.assertFalse(Usuario.objects.filter(username='33100001-9').exists())
