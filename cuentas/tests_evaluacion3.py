from datetime import timedelta
import re
from unittest.mock import patch
from django.contrib.auth.models import Group,Permission
from django.core import mail
from django.test import TestCase,Client,override_settings
from django.urls import reverse
from django.utils import timezone
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Usuario,CodigoUnUso,EstadoRegistro
from control_gestion.tests_kanban import KanbanTests
from requerimientos.models import Vecino

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class Evaluacion3Tests(TestCase):
    setUpTestData=classmethod(KanbanTests.setUpTestData.__func__)
    autenticar=KanbanTests.autenticar

    def jefatura(self):
        return crear_cuenta(codigo='USR-J',rut='33100001-9',password='Prueba123!',
            rol_codigo='jefatura',correo='jefatura@siged.test',nombre='Jefa Prueba',delegacion=self.centro)

    def enlace(self,client=None):
        (client or self.client).post('/recuperar/',{'correo':self.admin.correo})
        self.assertEqual(mail.outbox[-1].to,[self.admin.correo])
        return re.search(r'https?://\S+',mail.outbox[-1].body).group()

    def test_usuario_tiene_grupo_django_y_permisos(self):
        self.assertTrue(self.admin.user.groups.filter(pk=self.admin.rol.grupo_id).exists())
        self.assertTrue(self.admin.user.has_perm('cuentas.acceso_administracion'))
        self.assertTrue(self.admin.user.has_perm('cuentas.delete_rol'))
        self.assertFalse(self.funcionario.user.has_perm('cuentas.acceso_administracion'))

    def test_supervisor_tiene_mantenedores_intermedios(self):
        perfil=self.jefatura()
        self.autenticar(perfil)
        response=self.client.get('/mantenedores/vecinos/')
        self.assertContains(response,'Agregar')
        self.assertNotContains(response,'btn-outline-danger')
        self.assertNotContains(self.client.get('/mantenedores/metas/'),'Modificar')
        self.assertEqual(self.client.get('/administracion/usuarios/').status_code,302)

    def test_supervisor_no_borra_por_url_directa_ni_ve_otra_delegacion(self):
        perfil=self.jefatura()
        propio=Vecino.objects.create(nombre='Registro propio',delegacion=self.centro)
        otro=Vecino.objects.create(nombre='Registro reservado rural',delegacion=self.rural)
        self.autenticar(perfil)
        self.assertNotContains(self.client.get('/mantenedores/vecinos/'),otro.nombre)
        self.assertEqual(self.client.post(f'/mantenedores/vecinos/{propio.pk}/eliminar/').status_code,302)
        self.assertTrue(Vecino.objects.filter(pk=propio.pk).exists())
        self.assertEqual(self.client.get(f'/mantenedores/vecinos/{otro.pk}/editar/').status_code,404)

    def test_permisos_revocados_se_aplican_sin_cerrar_sesion(self):
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get('/control/actividades/').status_code,200)
        permiso=Permission.objects.get(codename='acceso_actividades',content_type__app_label='cuentas')
        self.funcionario.rol.grupo.permissions.remove(permiso)
        self.assertEqual(self.client.get('/control/actividades/').status_code,302)

    def test_asignacion_desde_templates_cambia_grupo_y_acceso(self):
        self.autenticar()
        response=self.client.post('/administracion/grupos/',{'accion':'asignar','usuario':self.funcionario.pk,'rol':self.admin.rol_id})
        self.assertEqual(response.status_code,302)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.user.groups.filter(pk=self.admin.rol.grupo_id).exists())
        self.assertEqual(self.funcionario.user.groups.filter(rol_municipal__isnull=False).count(),1)
        self.assertTrue(self.funcionario.user.has_perm('cuentas.acceso_administracion'))

    def test_editar_permisos_desde_templates(self):
        jefe=self.jefatura()
        self.autenticar()
        permission=Permission.objects.get(codename='view_vecino',content_type__app_label='requerimientos')
        response=self.client.post(reverse('admin_grupo',args=[jefe.rol_id]),{'accion':'permisos','permisos':[permission.pk]})
        self.assertEqual(response.status_code,302)
        self.assertEqual(list(jefe.rol.grupo.permissions.values_list('pk',flat=True)),[permission.pk])

    def test_no_administrador_no_edita_grupos(self):
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get('/administracion/grupos/').status_code,302)
        self.assertEqual(self.client.post(reverse('admin_grupo',args=[self.admin.rol_id]),{'accion':'permisos','permisos':[]}).status_code,302)
        self.assertTrue(self.admin.rol.grupo.permissions.filter(codename='acceso_administracion').exists())

    def test_administrador_no_puede_quitarse_su_grupo(self):
        self.autenticar()
        self.client.post('/administracion/grupos/',{'accion':'asignar','usuario':self.admin.pk,'rol':self.funcionario.rol_id})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol.codigo,'superusuario')

    def test_recuperacion_por_enlace_completa_y_no_reutilizable(self):
        enlace=self.enlace()
        destino=Client()
        primera=destino.get(enlace)
        self.assertEqual(primera.status_code,302)
        formulario=destino.get(primera['Location'])
        self.assertContains(formulario,'Restablecer contraseña')
        nueva='VentanaDePruebas78!'
        respuesta=destino.post(primera['Location'],{'new_password1':nueva,'new_password2':nueva})
        self.assertEqual(respuesta['Location'],'/login/')
        self.admin.user.refresh_from_db()
        self.assertTrue(self.admin.user.check_password(nueva))
        self.assertEqual(destino.post('/login/',{'rut':self.admin.username,'password':nueva}).status_code,302)
        self.assertFalse(Client().get(enlace).context['validlink'])
        self.assertFalse(CodigoUnUso.objects.filter(usuario=self.admin,anulado_en__isnull=True).exists())

    def test_enlace_alterado_no_permite_cambiar_clave(self):
        enlace=self.enlace()
        alterado=enlace.rstrip('/')+'alterado/'
        self.assertFalse(Client().get(alterado).context['validlink'])
        self.admin.user.refresh_from_db()
        self.assertTrue(self.admin.user.check_password('Prueba123!'))

    def test_enlace_caduca_en_diez_minutos(self):
        enlace=self.enlace()
        from datetime import datetime
        futuro=datetime.now()+timedelta(seconds=601)
        with patch('django.contrib.auth.tokens.PasswordResetTokenGenerator._now',return_value=futuro):
            self.assertFalse(Client().get(enlace).context['validlink'])

    def test_enlace_no_funciona_para_cuenta_desactivada(self):
        enlace=self.enlace()
        Usuario.objects.filter(pk=self.admin.pk).update(estado=EstadoRegistro.INACTIVO)
        self.assertFalse(Client().get(enlace).context['validlink'])

    def test_enlace_no_acepta_clave_debil(self):
        destino=Client()
        formulario=destino.get(self.enlace())['Location']
        response=destino.post(formulario,{'new_password1':'1234','new_password2':'1234'})
        self.assertContains(response,'Mínimo 8 caracteres')
        self.admin.user.refresh_from_db()
        self.assertTrue(self.admin.user.check_password('Prueba123!'))
