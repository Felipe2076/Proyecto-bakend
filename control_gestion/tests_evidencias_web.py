from io import BytesIO
from tempfile import TemporaryDirectory
from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from control_gestion.tests_kanban import KanbanTests
from control_gestion.models import Actividad, Meta
from control_gestion.evidencias import validar_archivo
from core.paginacion import paginar
from django.test import RequestFactory

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db', PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class EvidenciasWebTests(TestCase):
    setUpTestData=classmethod(KanbanTests.setUpTestData.__func__)
    autenticar=KanbanTests.autenticar
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override=override_settings(MEDIA_ROOT=self.tmp.name)
        self.override.enable();self.addCleanup(self.override.disable)
        out=BytesIO();Image.new('RGB',(3,3)).save(out,format='PNG')
        self.image=out.getvalue()
        self.meta=Meta.objects.create(nombre='Visita territorial')
        self.actividad=Actividad.objects.create(funcionario=self.funcionario.funcionario,delegacion=self.centro,meta=self.meta,servicio='Visita con respaldo',evidencia_archivo=SimpleUploadedFile('foto.png',self.image,content_type='image/png'))
        self.url=f'/control/actividades/{self.actividad.codigo}/evidencia/'
    def test_funcionario_puede_ver_archivo_real_de_su_delegacion(self):
        self.autenticar(self.funcionario)
        r=self.client.get(self.url)
        self.assertEqual(r.status_code,200)
        self.assertEqual(b''.join(r.streaming_content),self.image)
        self.assertEqual(r['Content-Type'],'image/png')
        self.assertIn('no-store',r['Cache-Control'])
    def test_otro_ambito_no_accede_a_la_evidencia(self):
        self.actividad.delegacion=self.rural;self.actividad.save()
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get(self.url).status_code,404)
    def test_anonimo_no_accede(self):
        self.assertEqual(self.client.get(self.url).status_code,302)
    def test_rechaza_archivo_falso_y_svg(self):
        for name in ('foto.png','documento.pdf','archivo.svg'):
            with self.assertRaises(ValueError): validar_archivo(SimpleUploadedFile(name,b'<script>alert(1)</script>'))
    def test_acepta_png_y_rebobina_archivo(self):
        f=SimpleUploadedFile('foto.png',self.image)
        validar_archivo(f);self.assertEqual(f.tell(),0)
    def test_paginacion_20_preserva_filtros(self):
        r=RequestFactory().get('/',{'q':'José','per_page':'20','page':'2'})
        page,ctx=paginar(r,list(range(45)))
        self.assertEqual(list(page),list(range(20,40)))
        self.assertIn('q=Jos',ctx['consulta_pagina'])
        self.assertEqual(ctx['opciones_pagina'],(10,20,50,100))
