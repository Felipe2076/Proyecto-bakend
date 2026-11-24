from django.test import TestCase,override_settings
from control_gestion.tests_kanban import KanbanTests
from cuentas.recuperacion import emitir_codigo

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PrimerIngresoTests(TestCase):
    setUpTestData=classmethod(KanbanTests.setUpTestData.__func__)
    def test_clave_provisoria_exige_definir_password_sin_autenticar(self):
        user=self.funcionario.user
        user.set_unusable_password();user.save(update_fields=['password'])
        codigo=emitir_codigo(self.funcionario)
        response=self.client.post('/login/',{'rut':self.funcionario.username,'password':codigo})
        self.assertRedirects(response,'/recuperar/nueva/',fetch_redirect_response=False)
        self.assertTrue(self.client.session['recuperacion']['verificado'])
        self.assertNotIn('_auth_user_id',self.client.session)
        self.client.session.flush()
        response=self.client.post('/login/',{'rut':self.funcionario.username,'password':codigo})
        self.assertEqual(response.status_code,200)
        self.assertNotIn('_auth_user_id',self.client.session)
