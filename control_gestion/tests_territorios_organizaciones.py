"""Selector de territorios por delegación y ficha de organizaciones con datos ficticios."""
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings

from control_gestion.models import OrganizacionComunitaria, TerritorioDelegacion
from control_gestion import tests_kanban
from cuentas.perfiles import sincronizar_usuario


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TerritoriosOrganizacionesTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        for perfil in (cls.admin, cls.funcionario):
            sincronizar_usuario(perfil)
        TerritorioDelegacion.objects.create(delegacion=cls.centro, nombre='Territorio Ficticio A')
        cls.org = OrganizacionComunitaria.objects.create(
            nombre='Organización Ficticia', delegacion=cls.centro, territorio='Territorio Ficticio A',
            presidente_nombre='Persona Uno', presidente_rut='12345678-5',
            tesorero_nombre='Persona Dos', tesorero_rut='9876543-3',
            secretario_nombre='Persona Tres', secretario_rut='11222333-9')

    def permitir(self, *codenames):
        grupo = self.funcionario.rol.grupo
        grupo.permissions.add(*Permission.objects.filter(codename__in=codenames))

    def opciones_territorio(self, response):
        return [str(etiqueta) for _valor, etiqueta in response.context['form'].fields['territorio'].choices]

    def test_estado_vacio_coincide_con_el_selector_dependiente(self):
        self.autenticar()
        sin_catalogo = OrganizacionComunitaria.objects.create(nombre='Organización Rural Ficticia', delegacion=self.rural)
        respuesta = self.client.get(f'/mantenedores/organizaciones/{sin_catalogo.pk}/editar/')
        self.assertEqual(self.opciones_territorio(respuesta), ['Esta delegación aún no tiene territorios'])
        self.assertEqual(self.opciones_territorio(self.client.get('/mantenedores/organizaciones/nuevo/')),
                         ['Seleccione una delegación'])
        json = self.client.get(f'/mantenedores/organizaciones/territorios/?delegacion={self.rural.pk}').json()
        self.assertEqual(json, {'territorios': []})

    def test_directiva_se_consulta_con_permiso_de_lectura(self):
        self.permitir('view_organizacioncomunitaria')
        self.autenticar(self.funcionario)
        respuesta = self.client.get('/mantenedores/organizaciones/')
        for texto in ('Presidente/a', 'Tesorero/a', 'Secretario/a', 'Persona Uno', 'Persona Dos', 'Persona Tres'):
            self.assertContains(respuesta, texto)
        self.assertNotContains(respuesta, 'Editar ficha')
        self.assertEqual(self.client.get(f'/mantenedores/organizaciones/{self.org.pk}/editar/').status_code, 302)
        self.assertEqual(self.client.get(f'/mantenedores/organizaciones/territorios/?delegacion={self.centro.pk}').status_code, 403)

    def test_no_administrador_no_deja_la_ficha_sin_delegacion(self):
        self.permitir('view_organizacioncomunitaria', 'change_organizacioncomunitaria', 'add_organizacioncomunitaria')
        self.autenticar(self.funcionario)
        url = f'/mantenedores/organizaciones/{self.org.pk}/editar/'
        respuesta = self.client.post(url, {'nombre': self.org.nombre, 'delegacion': '', 'territorio': '', 'activa': 'on'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('delegacion', respuesta.context['form'].errors)
        self.org.refresh_from_db()
        self.assertEqual(self.org.delegacion_id, self.centro.pk)
        nueva = self.client.get('/mantenedores/organizaciones/nuevo/')
        self.assertEqual(nueva.context['form']['delegacion'].value(), self.centro.pk)
        self.assertIn('Territorio Ficticio A', self.opciones_territorio(nueva))
        datos = {'nombre': self.org.nombre, 'delegacion': self.centro.pk, 'territorio': 'Territorio Ficticio A', 'activa': 'on',
                 'presidente_nombre': 'Persona Cuatro', 'presidente_rut': '12.345.678-5'}
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual((self.org.presidente_nombre, self.org.presidente_rut), ('Persona Cuatro', '12345678-5'))

    def test_administrador_edita_directiva_y_valida_territorio(self):
        self.autenticar()
        url = f'/mantenedores/organizaciones/{self.org.pk}/editar/'
        base = {'nombre': self.org.nombre, 'delegacion': self.rural.pk, 'territorio': 'Territorio Ficticio A', 'activa': 'on'}
        self.assertIn('territorio', self.client.post(url, base).context['form'].errors)
        base.update(delegacion=self.centro.pk, tesorero_nombre='Persona Cinco', tesorero_rut='9.876.543-3')
        self.assertEqual(self.client.post(url, base).status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.tesorero_rut, '9876543-3')
        self.assertIsNone(self.org.presidente_nombre)

    def test_selector_tabla_kanban_conserva_filtros(self):
        from datetime import timedelta
        from django.utils import timezone
        from control_gestion.models import Compromiso
        compromiso = Compromiso.objects.create(
            descripcion='Compromiso ficticio', vecino=self.ticket.vecino, funcionario=self.funcionario.funcionario,
            delegacion=self.centro, fecha_compromiso=timezone.localdate() + timedelta(days=5))
        self.autenticar()
        detalle = f'/control/compromisos/{compromiso.codigo}/ver/'
        tabla = self.client.get('/control/tubo-trabajo/?estado=INGRESADO')
        cartas = self.client.get('/control/tubo-cartas/?estado=INGRESADO')
        self.assertEqual(tabla.context['vista'], 'tabla')
        self.assertEqual(cartas.context['vista'], 'tarjetas')
        # Una sola entrada en el menú y, dentro de la pantalla, el selector Tabla/Kanban que conserva los filtros.
        for respuesta in (tabla, cartas):
            self.assertContains(respuesta, 'href="/control/tubo-trabajo/"')
            self.assertContains(respuesta, 'href="/control/tubo-trabajo/?estado=INGRESADO"')
            self.assertContains(respuesta, 'href="/control/tubo-cartas/?estado=INGRESADO"')
        self.assertContains(tabla, f'href="{detalle}?estado=INGRESADO"')
        self.assertContains(cartas, f'href="{detalle}?estado=INGRESADO&amp;vista=tarjetas"')
        desde_tabla = self.client.get(f'{detalle}?estado=INGRESADO')
        desde_cartas = self.client.get(f'{detalle}?estado=INGRESADO&vista=tarjetas')
        self.assertEqual(desde_tabla.context['volver'], '/control/tubo-trabajo/?estado=INGRESADO')
        self.assertEqual(desde_cartas.context['volver'], '/control/tubo-cartas/?estado=INGRESADO')
        self.assertContains(desde_tabla, 'Volver a Compromisos')
        self.assertContains(desde_cartas, 'Volver a Tubo de cartas')
