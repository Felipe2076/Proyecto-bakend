"""App móvil: recuperación de clave con código, «mi trabajo» y evidencias de compromisos. Datos ficticios."""
import io
import re
from datetime import timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image

from control_gestion.models import Actividad, Compromiso, EvidenciaCompromiso
from control_gestion.tests_movil import MovilTests

API = '/api/v1/'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ApiCuentaTests(MovilTests):
    test_guardar_reintentar_y_revisar_con_permisos = None

    def json(self, ruta, cuerpo, **extra):
        return self.client.post(API + ruta, cuerpo, content_type='application/json', secure=True, **extra)

    def test_recuperacion_en_dos_pasos_y_cierre_de_sesiones(self):
        a = self.auth(self.fun)
        r = self.json('recuperar/', {'correo': self.fun.correo})
        self.assertEqual(r.status_code, 200)
        codigo = re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)
        # Un correo inexistente responde igual y no envía nada.
        enviados = len(mail.outbox)
        self.assertEqual(self.json('recuperar/', {'correo': 'nadie@siged.test'}).json()['mensaje'], r.json()['mensaje'])
        self.assertEqual(len(mail.outbox), enviados)
        malo = self.json('recuperar/verificar/', {'correo': self.fun.correo, 'codigo': '000000' if codigo != '000000' else '111111'})
        self.assertEqual(malo.status_code, 422)
        ok = self.json('recuperar/verificar/', {'correo': self.fun.correo, 'codigo': codigo})
        self.assertEqual(ok.status_code, 200, ok.content)
        permiso = ok.json()['permiso']
        corta = self.json('recuperar/nueva/', {'permiso': permiso, 'password': 'corta', 'confirmacion': 'corta'})
        self.assertEqual(corta.status_code, 422)
        nueva = 'OtraClaveSegura#2026'
        self.assertEqual(self.json('recuperar/nueva/', {'permiso': permiso, 'password': nueva, 'confirmacion': nueva}).status_code, 200)
        self.assertEqual(self.json('recuperar/nueva/', {'permiso': permiso, 'password': nueva + 'x', 'confirmacion': nueva + 'x'}).status_code, 401)
        self.assertEqual(self.client.get(API + 'perfil/', **a).status_code, 401)  # sesiones anteriores anuladas
        self.assertEqual(self.json('sesion/', {'rut': self.fun.funcionario.rut, 'password': nueva}).status_code, 200)

    def test_mi_trabajo_trimestre_asistencia_y_estados(self):
        hoy = timezone.localdate()
        self.tubo.fecha_compromiso = hoy - timedelta(days=3)
        self.tubo.save()
        Actividad.objects.create(funcionario=self.fun.funcionario, delegacion=self.centro, meta=self.meta,
                                 servicio='Visita ficticia', fecha_actividad=hoy)
        d = self.client.get(API + 'mi-trabajo/', **self.auth(self.fun)).json()
        self.assertEqual(d['perfil']['codigo'], self.fun.codigo)
        self.assertGreaterEqual(d['trimestre']['dia'], 1)
        self.assertTrue(d['asistencia']['registro_hoy'] or hoy.weekday() >= 5)
        self.assertEqual([c['codigo'] for c in d['compromisos']], [self.tubo.codigo])  # solo los propios
        self.assertEqual(d['compromisos'][0]['estado'], 'VENCIDO')
        self.assertEqual(d['conteo']['VENCIDO'], 1)

    def test_subir_foto_y_documento_y_verlos(self):
        a = self.auth(self.fun)
        url = f'{API}compromisos/{self.tubo.codigo}/evidencias/'
        r = self.client.post(url, {'archivo': self.documento(), 'descripcion': 'Foto en terreno'}, **a)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['evidencia']['tipo'], 'FOTO')
        pdf = SimpleUploadedFile('acta.pdf', b'%PDF-1.4 ficticio', content_type='application/pdf')
        self.assertEqual(self.client.post(url, {'archivo': pdf}, **a).json()['evidencia']['tipo'], 'DOCUMENTO')
        falso = SimpleUploadedFile('virus.pdf', b'MZ no es pdf', content_type='application/pdf')
        self.assertEqual(self.client.post(url, {'archivo': falso}, **a).status_code, 422)
        ajeno = f'{API}compromisos/{self.ajeno.codigo}/evidencias/'
        self.assertEqual(self.client.post(ajeno, {'archivo': self.documento()}, **a).status_code, 404)
        evidencia = EvidenciaCompromiso.objects.filter(tipo='FOTO').first()
        r = self.client.get(f'{API}evidencias/{evidencia.pk}/', **a)
        self.assertEqual(r['Content-Type'], 'image/png')
        r.close()  # Windows no borra un archivo abierto
        self.assertEqual(self.client.get(f'{API}evidencias/{evidencia.pk}/', **self.auth(self.otro)).status_code, 404)
        d = self.client.get(API + 'mi-trabajo/', **a).json()
        self.assertEqual(len(d['compromisos'][0]['evidencias']), 2)
