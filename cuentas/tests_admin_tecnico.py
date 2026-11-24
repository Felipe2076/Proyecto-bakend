from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase,override_settings
from django.conf import settings


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],ALLOWED_HOSTS=['testserver'])
class AccesoAdminTecnicoTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='tecnico_prueba',password='Solo-Pruebas-123!',is_staff=True)
        self.user.user_permissions.add(Permission.objects.get(codename='view_delegacion',content_type__app_label='cuentas'))

    def test_cuenta_staff_sin_perfil_municipal_conserva_sesion_admin(self):
        self.assertTrue(self.client.login(username='tecnico_prueba',password='Solo-Pruebas-123!'))
        self.assertEqual(self.client.get('/admin/').status_code,200)
        self.assertEqual(self.client.get('/admin/cuentas/delegacion/').status_code,200)

    def test_visitante_no_entra_a_admin(self):
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,302)
        self.assertIn('/admin/login/',response.url)

    def test_no_staff_no_entra_a_admin(self):
        self.user.is_staff=False
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/').status_code,302)

    def test_consulta_no_permite_crear_o_modificar(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/cuentas/delegacion/add/').status_code,403)
        self.assertEqual(self.client.post('/admin/cuentas/delegacion/add/',{'nombre':'No autorizado','comuna':'La Serena'}).status_code,403)

    def test_cuenta_tecnica_no_abre_sistema_municipal_sin_perfil(self):
        self.client.force_login(self.user)
        response=self.client.get('/mantenedores/delegaciones/')
        self.assertEqual(response.status_code,302)
        self.assertIn('/login/',response.url)

    def test_staff_sin_permiso_no_ve_tablas(self):
        self.user.user_permissions.clear()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/cuentas/delegacion/').status_code,403)

    def test_staff_con_crud_puede_agregar_modificar_y_eliminar(self):
        from cuentas.models import Delegacion
        for accion in ('add','change','delete'):
            self.user.user_permissions.add(Permission.objects.get(codename=accion+'_delegacion',content_type__app_label='cuentas'))
        self.client.force_login(self.user)
        response=self.client.post('/admin/cuentas/delegacion/add/',{'nombre':'Delegación de prueba','direccion':'Calle de prueba','comuna':'La Serena','_save':'Guardar'})
        self.assertEqual(response.status_code,302)
        obj=Delegacion.objects.get(nombre='Delegación de prueba')
        response=self.client.post(f'/admin/cuentas/delegacion/{obj.pk}/change/',{'nombre':'Delegación modificada','direccion':'Calle de prueba','comuna':'La Serena','_save':'Guardar'})
        self.assertEqual(response.status_code,302)
        obj.refresh_from_db()
        self.assertEqual(obj.nombre,'Delegación modificada')
        response=self.client.post(f'/admin/cuentas/delegacion/{obj.pk}/delete/',{'post':'yes'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(Delegacion.objects.filter(pk=obj.pk).exists())

    def test_recursos_y_rutas_sin_perfil_no_cierran_sesion_staff(self):
        self.client.force_login(self.user)
        for ruta in ('/static/admin/css/base.css','/favicon.ico','/mantenedores/delegaciones/'):
            self.client.get(ruta)
            self.assertEqual(self.client.get('/admin/cuentas/delegacion/').status_code,200)
        self.assertNotIn('usuario',self.client.session)
        self.assertEqual(self.client.get('/admin/cuentas/delegacion/add/').status_code,403)

    def test_no_staff_sin_perfil_pierde_sesion(self):
        self.user.is_staff=False
        self.user.save(update_fields=['is_staff'])
        self.client.force_login(self.user)
        self.client.get('/favicon.ico')
        self.assertNotIn('_auth_user_id',self.client.session)
