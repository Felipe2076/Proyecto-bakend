from datetime import date
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from control_gestion.tests_kanban import KanbanTests
from control_gestion.models import Ausencia,OrganizacionComunitaria,Actividad,Meta
from control_gestion.ausencias import ajustar_periodo
from control_gestion.forms import MedicionForm
from django.core.files.uploadedfile import SimpleUploadedFile

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ConfiguracionNuevaTests(TestCase):
    setUpTestData=classmethod(KanbanTests.setUpTestData.__func__)
    autenticar=KanbanTests.autenticar
    def setUp(self):
        from tempfile import TemporaryDirectory
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        setting=override_settings(MEDIA_ROOT=tmp.name)
        setting.enable()
        self.addCleanup(setting.disable)
    def test_ausencias_no_superpuestas_y_ajuste_de_dias(self):
        a=Ausencia(funcionario=self.funcionario.funcionario,delegacion=self.centro,tipo='LICENCIA',fecha_inicio=date(2026,11,1),fecha_termino=date(2026,11,3))
        a.full_clean();a.save()
        b=Ausencia(funcionario=self.funcionario.funcionario,delegacion=self.centro,tipo='VACACIONES',fecha_inicio=date(2026,11,3),fecha_termino=date(2026,11,5))
        with self.assertRaises(ValidationError):b.full_clean()
        periodo={'fecha_inicio':date(2026,11,1),'fecha_termino':date(2026,11,30),'fecha_hoy':date(2026,11,15),'dias_totales':30,'dias_avance':15,'pct_esperado':50}
        ajustado=ajustar_periodo(self.funcionario.funcionario,periodo)
        self.assertEqual(ajustado['dias_totales'],27)
        self.assertEqual(ajustado['dias_avance'],12)
        self.assertEqual(ajustado['pct_esperado'],44.4)
        self.assertEqual(periodo['dias_totales'],30)
    def test_catalogo_no_se_marca_verificado_automaticamente(self):
        org=OrganizacionComunitaria.objects.create(nombre='Junta de prueba')
        self.assertFalse(org.verificada)
        self.assertTrue(org.codigo.startswith('ORG-'))
    def test_felicitacion_solo_validador_autorizado_y_una_vez(self):
        from control_gestion.evidencias import bonificacion
        a=Actividad.objects.create(funcionario=self.funcionario.funcionario,delegacion=self.centro,meta=Meta.objects.create(nombre='Meta prueba'),tipo_registro='FELICITACION',estado_revision='HISTORICA',servicio='Felicitación formal',evidencia_archivo=SimpleUploadedFile('formal.pdf',b'%PDF-1.4\nprueba'),punto_validado=False)
        # Evitar guardar un archivo de prueba en almacenamiento real.
        self.addCleanup(lambda:a.evidencia_archivo.delete(save=False))
        url=f'/control/actividades/{a.codigo}/validar/'
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.post(url).status_code,403)
        a.refresh_from_db();self.assertIsNone(a.fecha_validacion)
        self.autenticar()
        self.assertEqual(self.client.post(url).status_code,302)
        a.refresh_from_db();timestamp=a.fecha_validacion
        self.assertTrue(a.punto_validado);self.assertEqual(a.validado_por_id,self.admin.user_id)
        self.client.post(url);a.refresh_from_db();self.assertEqual(a.fecha_validacion,timestamp)
        self.assertEqual(bonificacion(a.funcionario,{'fecha_inicio':a.fecha_actividad,'fecha_termino':a.fecha_actividad}),10)
    def test_periodo_invertido_no_se_guarda(self):
        form=MedicionForm(data={'periodo':'Trimestre invertido','delegacion_piloto':self.centro.pk,'fecha_inicio':'2026-12-31','fecha_termino':'2026-10-01','dias_totales':90,'meta_cumplimiento_tubo':80})
        self.assertFalse(form.is_valid());self.assertIn('fecha_termino',form.errors)

    def test_periodo_sin_dias_los_calcula_con_las_fechas(self):
        form=MedicionForm(data={'periodo':'Trimestre incompleto','delegacion_piloto':self.centro.pk,'fecha_inicio':'2026-10-01','fecha_termino':'2026-12-31','meta_cumplimiento_tubo':80})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.dias_totales,92)

    def test_desempeno_comparte_ausencias_y_bonificaciones(self):
        from control_gestion.consultas import funcionario_base
        from control_gestion.views import enriquecer_funcionario
        Ausencia.objects.create(funcionario=self.funcionario.funcionario,delegacion=self.centro,tipo='LICENCIA',fecha_inicio=date(2026,11,1),fecha_termino=date(2026,11,3))
        periodo={'fecha_inicio':'2026-11-01','fecha_termino':'2026-11-30','fecha_hoy':'2026-11-15','dias_totales':30,'dias_avance':15,'pct_esperado':50,'meta_cumplimiento_tubo':80}
        fila=enriquecer_funcionario(funcionario_base(self.funcionario.funcionario),periodo,{})
        self.assertEqual(fila['dias_ausencia'],3)
        self.assertEqual(fila['pct_esperado'],44.4)
        self.assertEqual(periodo['pct_esperado'],50)
