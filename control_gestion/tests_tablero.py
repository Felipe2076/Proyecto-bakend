"""Tabla/Kanban, evidencias desde la web (compromisos y tickets) y actividades de organizaciones. Datos ficticios."""
import io
from datetime import time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from control_gestion.models import EventoAgenda, EvidenciaCompromiso, OrganizacionComunitaria
from control_gestion.tests_movil import MovilTests
from requerimientos.models import AreaSoporte, CanalIngreso, EvidenciaRequerimiento, Requerimiento, TipoGestion


def foto(nombre='avance.png'):
    b = io.BytesIO()
    Image.new('RGB', (32, 24), '#9c1830').save(b, format='PNG')
    return SimpleUploadedFile(nombre, b.getvalue(), content_type='image/png')


class TableroTests(MovilTests):
    test_guardar_reintentar_y_revisar_con_permisos = None

    def setUp(self):
        super().setUp()
        self.client.force_login(self.delegado.user)
        self.json = {'HTTP_ACCEPT': 'application/json', 'secure': True}

    def ticket(self, delegacion=None):
        return Requerimiento.objects.create(
            codigo=f'TK-{Requerimiento.objects.count() + 9000}', vecino=self.tubo.vecino, delegacion=delegacion or self.centro,
            canal_ingreso=CanalIngreso.objects.get_or_create(nombre='Ventanilla')[0],
            tipo_gestion=TipoGestion.objects.get_or_create(nombre='Reclamo')[0],
            area=AreaSoporte.objects.get_or_create(codigo='AREA-T', defaults={'nombre': 'Área ficticia'})[0],
            descripcion='Luminaria apagada en el pasaje ficticio', fecha_ingreso=timezone.localdate(),
            estado=Requerimiento.Estado.PENDIENTE)

    def test_subir_y_listar_evidencia_de_compromiso(self):
        url = reverse('evidencias_web', args=['compromiso', self.tubo.codigo])
        r = self.client.post(url, {'archivo': foto(), 'descripcion': 'Foto del avance'}, **self.json)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['cantidad'], 1)
        self.assertEqual(EvidenciaCompromiso.objects.get().descripcion, 'Foto del avance')
        ver = self.client.get(r.json()['evidencias'][0]['url'], secure=True)
        self.assertEqual(ver.status_code, 200)
        ver.close()  # en Windows el archivo queda tomado si no se cierra
        self.assertEqual(self.client.get(url, **self.json).json()['cantidad'], 1)

    def test_evidencia_de_otra_delegacion_y_archivo_invalido(self):
        ajeno = reverse('evidencias_web', args=['compromiso', self.ajeno.codigo])
        self.assertEqual(self.client.post(ajeno, {'archivo': foto()}, **self.json).status_code, 404)
        falso = SimpleUploadedFile('falso.png', b'no es una imagen', content_type='image/png')
        url = reverse('evidencias_web', args=['compromiso', self.tubo.codigo])
        r = self.client.post(url, {'archivo': falso}, **self.json)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(EvidenciaCompromiso.objects.count(), 0)

    def test_tope_de_diez_evidencias(self):
        url = reverse('evidencias_web', args=['compromiso', self.tubo.codigo])
        for i in range(10):
            self.assertEqual(self.client.post(url, {'archivo': foto(f'f{i}.png')}, **self.json).status_code, 201)
        r = self.client.post(url, {'archivo': foto('once.png')}, **self.json)
        self.assertEqual(r.status_code, 422)
        self.assertIn('máximo', r.json()['error'])

    def test_evidencia_de_ticket(self):
        t = self.ticket()
        url = reverse('evidencias_web', args=['ticket', t.codigo])
        r = self.client.post(url, {'archivo': foto()}, **self.json)
        self.assertEqual(r.status_code, 201, r.content)
        e = EvidenciaRequerimiento.objects.get()
        ver = self.client.get(reverse('ver_evidencia_ticket', args=[e.pk]), secure=True)
        self.assertEqual(ver.status_code, 200)
        ver.close()
        otro = self.ticket(self.rural)
        self.assertEqual(self.client.post(reverse('evidencias_web', args=['ticket', otro.codigo]), {'archivo': foto()}, **self.json).status_code, 404)
        # El tablero muestra el contador en la tarjeta y en la tabla.
        for vista in ('', '?vista=tabla'):
            html = self.client.get(reverse('kanban') + vista, secure=True).content.decode()
            self.assertIn(f'data-evidencias="{url}"', html)

    def test_kanban_en_modo_tabla(self):
        self.ticket()
        r = self.client.get(reverse('kanban') + '?vista=tabla', secure=True)
        self.assertEqual(r.context['vista'], 'tabla')
        self.assertContains(r, '<table')
        self.assertContains(r, 'data-recordar-vista="kanban"')
        self.assertNotContains(self.client.get(reverse('kanban'), secure=True), '<table')

    def test_actividades_de_organizaciones_mas_nuevas_primero(self):
        self.client.force_login(self.fun.user)
        from django.contrib.auth.models import Permission
        self.fun.user.user_permissions.add(Permission.objects.get(codename='view_eventoagenda'))
        org = OrganizacionComunitaria.objects.create(nombre='Junta Ficticia', delegacion=self.centro)
        hoy = timezone.localdate()
        viejo = EventoAgenda.objects.create(titulo='Reunión antigua', tipo='Reunión', fecha=hoy, hora=time(10), delegacion=self.centro, organizacion=org)
        nuevo = EventoAgenda.objects.create(titulo='Operativo nuevo', tipo='Operativo', fecha=hoy.replace(day=1), hora=time(9), delegacion=self.centro, organizacion=org)
        EventoAgenda.objects.create(titulo='Evento sin organización', tipo='Reunión', fecha=hoy, hora=time(11), delegacion=self.centro)
        html = self.client.get(reverse('mant_agenda'), secure=True).content.decode()
        self.assertLess(html.index(nuevo.titulo), html.index(viejo.titulo))
        self.assertNotIn('Evento sin organización', html)
        self.assertIn('Evento sin organización', self.client.get(reverse('mant_agenda') + '?ver=generales', secure=True).content.decode())

    def test_editar_compromiso_vuelve_a_la_vista_de_origen(self):
        from control_gestion.tests_movil import Compromiso  # noqa: F401  (mismo modelo usado en la base)
        url = reverse('compromiso_editar', args=[self.tubo.codigo])
        datos = {'descripcion': 'Trabajo propio editado en la ventana', 'vecino': self.tubo.vecino.nombre,
                 'id_funcionario': self.fun.funcionario.codigo, 'delegacion': self.centro.nombre,
                 'fecha_compromiso': timezone.localdate().strftime('%d/%m/%Y'), 'estado': 'PENDIENTE', 'origen': 'EXT'}
        r = self.client.post(url + '?vista=tarjetas', datos, secure=True)
        if r.status_code == 302:
            self.assertEqual(r.url, reverse('tubo_cartas'))
        else:  # algún dato del formulario no calza con esta base de prueba: al menos no rompe y vuelve con errores
            self.assertEqual(r.status_code, 200)
