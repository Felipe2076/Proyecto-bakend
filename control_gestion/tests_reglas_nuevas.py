from datetime import date
from unittest.mock import patch
from django.test import TestCase, override_settings
from control_gestion.tests_kanban import KanbanTests
from control_gestion.consultas import registrar_actividad_desde_formulario
from control_gestion.models import Actividad,Meta,ItemFuncionario
from control_gestion.indicadores import cumplimiento_item

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReglasNuevasTests(TestCase):
    setUpTestData=classmethod(KanbanTests.setUpTestData.__func__)
    def setUp(self):
        self.fun=self.funcionario.funcionario
        self.meta=Meta.objects.create(nombre='Actividad de terreno')
        self.item=ItemFuncionario.objects.create(funcionario=self.fun,meta=self.meta,ponderador=100,meta_trimestre=10)
        self.datos={'contacto':'Vecino prueba','item':self.meta.nombre,'servicio':'Trabajo realizado en terreno','fecha_actividad':'2026-11-02'}
    @patch('control_gestion.consultas.timezone.localdate',return_value=date(2026,11,3))
    def test_maximo_siete_y_ningun_octavo_puntaje(self,_):
        for i in range(7):
            registro,errores=registrar_actividad_desde_formulario(self.fun.codigo,self.datos,{})
            self.assertEqual(errores,{})
        registro,errores=registrar_actividad_desde_formulario(self.fun.codigo,self.datos,{})
        self.assertIsNone(registro);self.assertIn('fecha_actividad',errores)
        self.item.refresh_from_db();self.assertEqual(self.item.avance_actual,0)  # Sin aprobación todavía.
    @patch('control_gestion.consultas.timezone.localdate',return_value=date(2026,11,3))
    def test_semana_anterior_permitida_martes(self,_):
        self.datos['fecha_actividad']='2026-10-26'
        self.assertEqual(registrar_actividad_desde_formulario(self.fun.codigo,self.datos,{})[1],{})
    @patch('control_gestion.consultas.timezone.localdate',return_value=date(2026,11,4))
    def test_semana_anterior_cerrada_miercoles(self,_):
        self.datos['fecha_actividad']='2026-10-26'
        self.assertIsNone(registrar_actividad_desde_formulario(self.fun.codigo,self.datos,{})[0])
    @patch('control_gestion.consultas.timezone.localdate',return_value=date(2026,11,3))
    def test_coordinaciones_y_felicitaciones_no_autovalidan(self,_):
        for tipo in ('COORDINACION','DELEGADO','FELICITACION'):
            self.datos['tipo_registro']=tipo
            registro,errores=registrar_actividad_desde_formulario(self.fun.codigo,self.datos,{})
            self.assertEqual(errores,{})
            self.assertFalse(registro['punto_validado'])
        self.item.refresh_from_db();self.assertEqual(self.item.avance_actual,0)
    def test_tope_120_coincide_entre_modelo_y_calculo(self):
        self.item.avance_actual=100
        self.assertEqual(self.item.porcentaje_avance,120)
        self.assertEqual(cumplimiento_item(100,10,100),(120,120))
