"""RUT libre al crear organizaciones, trimestre con nombre y días automáticos, y barra fija del trimestre."""
from datetime import date

from django.test import TestCase, override_settings

from control_gestion import tests_kanban
from control_gestion.forms import MedicionForm
from control_gestion.models import Medicion, OrganizacionComunitaria, TerritorioDelegacion


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class MejorasDeCreacionTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        TerritorioDelegacion.objects.create(delegacion=cls.centro, nombre='Territorio Ficticio A')

    def crear_organizacion(self, **cambios):
        datos = {'nombre': 'Organización Ficticia Nueva', 'delegacion': self.centro.pk,
                 'territorio': 'Territorio Ficticio A', 'activa': 'on'}
        datos.update(cambios)
        return self.client.post('/mantenedores/organizaciones/nuevo/', datos)

    # --- RUT al crear una organización ---
    def test_la_organizacion_acepta_cualquier_rut_al_crearse(self):
        self.autenticar()
        respuesta = self.crear_organizacion(presidente_nombre='Persona Uno', presidente_rut='11.111.111-9',
                                            tesorero_nombre='Persona Dos', tesorero_rut='12345678-0',
                                            secretario_nombre='Persona Tres', secretario_rut='1')
        self.assertEqual(respuesta.status_code, 302)
        org = OrganizacionComunitaria.objects.get(nombre='Organización Ficticia Nueva')
        self.assertEqual((org.tesorero_rut, org.secretario_rut), ('12345678-0', '1'))

    def test_un_rut_valido_se_sigue_normalizando(self):
        self.autenticar()
        self.assertEqual(self.crear_organizacion(presidente_nombre='Persona', presidente_rut='12.345.678-5').status_code, 302)
        self.assertEqual(OrganizacionComunitaria.objects.get().presidente_rut, '12345678-5')

    def test_un_rut_con_letras_o_sin_numeros_se_rechaza_y_no_se_repite(self):
        self.autenticar()
        for rut in ('abcdef', '---', '<script>'):
            respuesta = self.crear_organizacion(presidente_nombre='Persona', presidente_rut=rut)
            self.assertEqual(respuesta.status_code, 200, rut)
            self.assertIn('presidente_rut', respuesta.context['form'].errors, rut)
        respuesta = self.crear_organizacion(presidente_nombre='A', presidente_rut='1.234',
                                            tesorero_nombre='B', tesorero_rut='1234')
        self.assertIn('tesorero_rut', respuesta.context['form'].errors)
        self.assertFalse(OrganizacionComunitaria.objects.exists())

    # --- Trimestre automático ---
    def test_trimestre_con_nombre_y_dias_automaticos(self):
        form = MedicionForm({'fecha_inicio': date(2027, 1, 1), 'fecha_termino': date(2027, 3, 31),
                             'meta_cumplimiento_tubo': 80})
        self.assertTrue(form.is_valid(), form.errors)
        creada = form.save()
        self.assertEqual((creada.periodo, creada.dias_totales), ('Trimestre 1 de 2027', 90))

    def test_los_dias_se_calculan_aunque_se_envie_otro_numero(self):
        form = MedicionForm({'fecha_inicio': date(2027, 4, 1), 'fecha_termino': date(2027, 6, 30),
                             'dias_totales': 5, 'meta_cumplimiento_tubo': 80})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().dias_totales, 91)

    def test_nombre_repetido_o_periodo_corto_se_resuelven_solos(self):
        Medicion.objects.create(periodo='Trimestre 3 de 2027', delegacion_piloto=self.centro,
                                fecha_inicio=date(2027, 7, 1), fecha_termino=date(2027, 7, 10), dias_totales=10)
        form = MedicionForm({'fecha_inicio': date(2027, 7, 11), 'fecha_termino': date(2027, 9, 30),
                             'meta_cumplimiento_tubo': 80})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().periodo, 'Trimestre 3 de 2027 (2)')
        corto = MedicionForm({'fecha_inicio': date(2027, 11, 1), 'fecha_termino': date(2027, 11, 30),
                              'meta_cumplimiento_tubo': 80})
        self.assertTrue(corto.is_valid(), corto.errors)
        self.assertEqual(corto.save().periodo, 'Período 01/11/27 al 30/11/27')

    def test_un_nombre_escrito_se_respeta(self):
        form = MedicionForm({'periodo': 'Mi período', 'fecha_inicio': date(2028, 1, 1),
                             'fecha_termino': date(2028, 3, 31), 'meta_cumplimiento_tubo': 80})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().periodo, 'Mi período')

    def test_pantalla_de_alta_ya_no_pide_dias(self):
        self.autenticar()
        formulario = self.client.get('/mantenedores/periodos/nuevo/')
        self.assertNotContains(formulario, 'name="dias_totales"')
        respuesta = self.client.post('/mantenedores/periodos/nuevo/', {
            'fecha_inicio': '2029-01-01', 'fecha_termino': '2029-03-31', 'meta_cumplimiento_tubo': 80})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Medicion.objects.get(fecha_inicio=date(2029, 1, 1)).periodo, 'Trimestre 1 de 2029')

    # --- Barra fija del trimestre ---
    def test_el_trimestre_se_ve_arriba_en_todas_las_paginas_para_quien_inicio_sesion(self):
        self.autenticar(self.funcionario)
        for ruta in ('/', '/control/tubo-cartas/', '/control/agenda/'):
            pagina = self.client.get(ruta, follow=True)
            self.assertContains(pagina, 'data-trimestre-barra', msg_prefix=ruta)
            self.assertContains(pagina, 'aria-label="Avance del trimestre"', msg_prefix=ruta)
        self.client.logout()
        self.assertNotContains(self.client.get('/login/'), 'data-trimestre-barra')
