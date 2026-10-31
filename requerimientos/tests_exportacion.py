from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from unittest.mock import patch
import re
from django.test import TestCase, override_settings
from django.core import mail
from control_gestion import tests_kanban
from requerimientos.models import Requerimiento
from cuentas.models import CodigoUnUso
from cuentas.recuperacion import emitir_codigo

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ExportacionTests(TestCase):
    setUpTestData=classmethod(tests_kanban.KanbanTests.setUpTestData.__func__)
    autenticar=tests_kanban.KanbanTests.autenticar

    def test_excel_real_y_sin_formulas(self):
        self.autenticar()
        Requerimiento.objects.filter(pk=self.ticket.pk).update(descripcion='=HYPERLINK("x") & á\x01')
        response=self.client.get('/lista/exportar/')
        self.assertEqual(response.status_code,200)
        self.assertIn('.xlsx',response['Content-Disposition'])
        with ZipFile(BytesIO(response.content)) as z:
            self.assertIsNone(z.testzip())
            for name in z.namelist():
                ET.fromstring(z.read(name))
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        self.assertEqual(len(sheet.findall('.//s:row',ns)),3)
        self.assertEqual(sheet.findall('.//s:f',ns),[])
        self.assertIn('=HYPERLINK',response.content.decode('latin1') if False else ''.join(sheet.itertext()))

    def test_paginador_y_excel_exporta_todo_el_filtro(self):
        self.autenticar()
        for i in range(15):
            req=Requerimiento.objects.get(pk=self.ticket.pk)
            req.pk=None
            req.codigo=f'TK-EX-{i:03d}'
            req.descripcion='Grupo exportación'
            req.save()
        response=self.client.get('/lista/',{'busqueda':'Grupo exportación'})
        self.assertEqual(len(response.context['requerimientos']),10)
        self.assertEqual(response.context['total_resultados'],15)
        self.assertContains(response,'Exportar a Excel')
        response=self.client.get('/lista/',{'busqueda':'Grupo exportación','page':2})
        self.assertEqual(len(response.context['requerimientos']),5)
        self.assertContains(response,'busqueda=Grupo+exportaci%C3%B3n')
        excel=self.client.get('/lista/exportar/',{'busqueda':'Grupo exportación','page':2})
        with ZipFile(BytesIO(excel.content)) as z:
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        self.assertEqual(len(sheet.findall('{*}sheetData/{*}row')),16)

    def test_exportar_y_lista_respetan_delegacion(self):
        self.autenticar(self.funcionario)
        self.assertNotContains(self.client.get('/lista/'),self.otro.codigo)
        for query in ({},{'delegacion':self.rural.nombre}):
            response=self.client.get('/lista/exportar/',query)
            with ZipFile(BytesIO(response.content)) as z:
                self.assertNotIn(self.otro.codigo,z.read('xl/worksheets/sheet1.xml').decode())

    def test_excel_sin_resultados_y_pagina_invalida(self):
        self.autenticar()
        for page in ('xxx','-1','9999'):
            self.assertEqual(self.client.get('/lista/',{'page':page}).status_code,200)
        response=self.client.get('/lista/exportar/',{'busqueda':'sin-resultados-xyz'})
        with ZipFile(BytesIO(response.content)) as z:
            sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        self.assertEqual(len(sheet.findall('{*}sheetData/{*}row')),1)

    def test_exportar_anonimo_no_descarga(self):
        self.assertEqual(self.client.get('/lista/exportar/').status_code,302)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='localhost')
    def test_recuperacion_sin_smtp_no_crea_codigo_ni_finge_envio(self):
        response=self.client.post('/recuperar/',{'correo':self.admin.correo})
        self.assertContains(response,'aún no está habilitada')
        self.assertNotContains(response,'Enviar instrucciones')
        self.assertFalse(CodigoUnUso.objects.exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',EMAIL_HOST='smtp.example.test')
    @patch('cuentas.views.enviar_codigo',side_effect=OSError('connection failed'))
    def test_fallo_smtp_no_rompe_y_conserva_codigo_previo(self,mock):
        emitir_codigo(self.admin)
        response=self.client.post('/recuperar/',{'correo':self.admin.correo},follow=True)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'No se pudo enviar el correo')
        self.assertEqual(CodigoUnUso.objects.count(),1)
        self.assertIsNone(CodigoUnUso.objects.get().anulado_en)
        self.assertNotIn('recuperacion',self.client.session)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recuperacion_completa_con_correo_configurado(self):
        response=self.client.post('/recuperar/',{'correo':self.admin.correo})
        self.assertEqual(response.status_code,302)
        codigo=re.search(r'\d{6}',mail.outbox[-1].body).group()
        response=self.client.post('/recuperar/codigo/',{f'd{i}':n for i,n in enumerate(codigo,1)})
        self.assertEqual(response.status_code,302)
        # Solo se modifica una cuenta de la base temporal de pruebas.
        response=self.client.post('/recuperar/nueva/',{'password':'NuevaClaveSegura9!','confirmacion':'NuevaClaveSegura9!'})
        self.admin.user.refresh_from_db()
        if response.status_code==200:
            self.fail(str(response.context['form'].errors))
        self.assertTrue(self.admin.user.check_password('NuevaClaveSegura9!'))
