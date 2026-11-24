"""Búsqueda inteligente, autocompletado por RUT y avisos automáticos. Datos ficticios."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from control_gestion.models import Compromiso
from control_gestion.tests_movil import MovilTests
from requerimientos.models import Vecino


class AutomatizacionTests(MovilTests):
    test_guardar_reintentar_y_revisar_con_permisos = None

    def entrar(self, perfil):
        self.client.force_login(perfil.user)

    def test_busqueda_sin_tildes_y_con_faltas(self):
        Vecino.objects.create(nombre='María José González', rut='33500001-3', delegacion=self.centro)
        self.entrar(self.fun)
        d = self.client.get(reverse('buscador'), {'q': 'gonzalez'}, secure=True).json()
        self.assertIn('María José González', str(d['grupos']))
        d = self.client.get(reverse('buscador'), {'q': 'gonsales'}, secure=True).json()
        self.assertEqual(d['sugerencia'], 'gonzalez')
        self.assertIn('María José González', str(d['grupos']))

    def test_busqueda_respeta_la_delegacion(self):
        Vecino.objects.create(nombre='Vecina Rural Escondida', delegacion=self.rural)
        self.entrar(self.fun)
        d = self.client.get(reverse('buscador'), {'q': 'escondida'}, secure=True).json()
        self.assertNotIn('Escondida', str(d['grupos']))

    def test_busqueda_exige_sesion(self):
        self.assertIn(self.client.get(reverse('buscador'), {'q': 'algo'}, secure=True).status_code, (302, 401))

    def test_autocompletar_vecino_por_rut(self):
        Vecino.objects.create(nombre='María José González', rut='33500001-3', telefono='+56 9 1234 5678', delegacion=self.centro)
        self.entrar(self.fun)
        d = self.client.get(reverse('vecino_por_rut'), {'rut': '33.500.001-3'}, secure=True).json()
        self.assertTrue(d['encontrado'])
        self.assertEqual(d['vecino']['telefono'], '+56 9 1234 5678')
        self.assertFalse(self.client.get(reverse('vecino_por_rut'), {'rut': '33.500.001-4'}, secure=True).json()['valido'])
        # Un vecino de otra delegación no se revela.
        Vecino.objects.create(nombre='Otro Rural', rut='33500002-1', delegacion=self.rural)
        self.assertFalse(self.client.get(reverse('vecino_por_rut'), {'rut': '33500002-1'}, secure=True).json()['encontrado'])

    def test_aviso_automatico_de_compromiso_vencido(self):
        Compromiso.objects.filter(pk=self.tubo.pk).update(fecha_compromiso=timezone.localdate() - timedelta(days=3))
        self.entrar(self.fun)
        r = self.client.get(reverse('notificaciones'), secure=True)
        self.assertContains(r, f'Compromiso vencido {self.tubo.codigo}')
        # El compromiso de otra delegación no aparece.
        self.assertNotContains(r, self.ajeno.codigo)

    def test_ficha_vecino_con_nacionalidad_y_fases(self):
        v = Vecino.objects.create(nombre='Jean Pierre Louis', rut='33500001-3', delegacion=self.centro,
                                  es_extranjero=True, nacionalidad='Haití')
        Compromiso.objects.create(vecino=v, funcionario=self.fun.funcionario, delegacion=self.centro,
                                  descripcion='Orientación de residencia', fecha_compromiso=timezone.localdate(), estado='EN PROCESO')
        self.entrar(self.fun)
        d = self.client.get(reverse('ficha_vecino', args=[v.pk]), secure=True).json()
        self.assertEqual(d['vecino']['nacionalidad'], 'Sí · Haití')
        self.assertEqual(d['vecino']['rut'], '33.500.001-3')
        self.assertEqual(d['actividades'][0]['fase'], 2)
        self.assertIn('Trimestre', d['actividades'][0]['periodo'])
        # Vecino de otra delegación: no se muestra.
        otro = Vecino.objects.create(nombre='Persona Rural', delegacion=self.rural)
        self.assertEqual(self.client.get(reverse('ficha_vecino', args=[otro.pk]), secure=True).status_code, 404)

    def test_formulario_pregunta_si_es_extranjero(self):
        from requerimientos.views import validar_formulario_requerimiento
        base = {'vecino_nombre': 'Jean Pierre Louis', 'telefono_whatsapp': '+56 9 1234 5678', 'delegacion': self.centro.nombre,
                'descripcion': 'Luminaria apagada en la esquina del pasaje'}
        _, errores = validar_formulario_requerimiento(base)
        self.assertIn('es_extranjero', errores)
        _, errores = validar_formulario_requerimiento({**base, 'es_extranjero': 'si'})
        self.assertIn('nacionalidad', errores)
        valores, errores = validar_formulario_requerimiento({**base, 'es_extranjero': 'no', 'nacionalidad': 'Perú'})
        self.assertNotIn('es_extranjero', errores)
        self.assertEqual(valores['nacionalidad'], '')
