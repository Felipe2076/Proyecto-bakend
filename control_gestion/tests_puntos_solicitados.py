from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from datetime import timedelta
from django.test import TestCase,override_settings
from django.utils import timezone
from control_gestion import tests_kanban
from control_gestion.models import Meta,ItemFuncionario,Actividad,Compromiso,EventoAgenda,Medicion
from cuentas.models import Cargo,Usuario,EstadoRegistro,SecuenciaCodigo
from cuentas.servicios import siguiente_codigo
from requerimientos.models import Vecino,Atencion,TipoAtencion,SubAtencion
from requerimientos.forms import AtencionForm
from core.busqueda import buscar

def hojas(response):
    assert response.status_code==200
    result={}
    with ZipFile(BytesIO(response.content)) as z:
        assert z.testzip() is None
        workbook=ET.fromstring(z.read('xl/workbook.xml'))
        for i,sheet in enumerate(workbook.findall('{*}sheets/{*}sheet'),1):
            root=ET.fromstring(z.read(f'xl/worksheets/sheet{i}.xml'))
            assert not root.findall('.//{*}f')
            rows=[]
            for row in root.findall('{*}sheetData/{*}row'):
                rows.append([''.join(cell.itertext()) for cell in row])
            result[sheet.attrib['name']]=rows
    return result

@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.db',PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PuntosSolicitadosTests(TestCase):
    setUpTestData=classmethod(tests_kanban.KanbanTests.setUpTestData.__func__)
    autenticar=tests_kanban.KanbanTests.autenticar

    def setUp(self):
        self.vecino=Vecino.objects.create(nombre='José Pérez',rut='33500001-3',delegacion=self.centro)
        self.meta=Meta.objects.create(nombre='Visitas territoriales')
        self.item=ItemFuncionario.objects.create(funcionario=self.funcionario.funcionario,meta=self.meta,
            ponderador=50,meta_trimestre=10,avance_actual=8)
        self.compromiso=Compromiso.objects.create(descripcion='Visita José plaza pública',vecino=self.vecino,
            funcionario=self.funcionario.funcionario,delegacion=self.centro,fecha_compromiso=timezone.localdate()+timedelta(days=1),estado='REALIZADO')
        self.otro_compromiso=Compromiso.objects.create(descripcion='Dato rural restringido',vecino=self.vecino,
            funcionario=self.admin.funcionario,delegacion=self.rural,fecha_compromiso=timezone.localdate(),estado='PENDIENTE')
        self.actividad=Actividad.objects.create(funcionario=self.funcionario.funcionario,delegacion=self.centro,
            meta=self.meta,contacto='José Pérez',servicio='Visita plaza pública',punto_validado=True)
        Actividad.objects.create(funcionario=self.admin.funcionario,delegacion=self.rural,meta=self.meta,
            servicio='Actividad rural restringida')

    def test_codigos_generados_en_todo_el_ambito(self):
        cargo=Cargo.objects.create(nombre='Cargo sin código')
        medicion=Medicion.objects.create(periodo='Trimestre prueba',delegacion_piloto=self.centro,
            fecha_inicio=timezone.localdate(),fecha_termino=timezone.localdate()+timedelta(days=90))
        evento=EventoAgenda.objects.create(titulo='Reunión',tipo='Reunión',fecha=timezone.localdate(),hora='10:00',delegacion=self.centro)
        for obj,prefijo in ((cargo,'CARGO-'),(self.meta,'META-'),(self.item,'ITEM-'),
            (self.compromiso,'TUB-'),(self.actividad,'ACT-'),(medicion,'MED-'),(evento,'AG-')):
            self.assertTrue(obj.codigo.startswith(prefijo),obj.codigo)
        self.assertTrue(self.actividad.codigo_verificador.startswith('VER-'))

    def test_codigo_no_cambia_al_editar(self):
        codigo=self.compromiso.codigo
        self.compromiso.codigo='TUB-CAMBIADO'
        self.compromiso.descripcion='Texto editado'
        self.compromiso.save()
        self.compromiso.refresh_from_db()
        self.assertEqual(self.compromiso.codigo,codigo)

    def test_contador_no_reutiliza_codigos_borrados_ni_colisiona_con_existentes(self):
        viejo=Meta.objects.create(codigo='META-900',nombre='Legado')
        nuevo=Meta.objects.create(nombre='Meta nueva')
        self.assertEqual(nuevo.codigo,'META-901')
        nuevo.delete()
        self.assertEqual(Meta.objects.create(nombre='Otra meta').codigo,'META-902')
        self.assertEqual(viejo.codigo,'META-900')
        self.assertNotEqual(siguiente_codigo(Meta,'codigo','META-'),siguiente_codigo(Meta,'codigo','META-'))

    def test_busqueda_palabras_en_cualquier_orden_y_tildes(self):
        qs=buscar(Compromiso.objects.all(),'publica jose',['descripcion'])
        self.assertEqual(list(qs.values_list('pk',flat=True)),[self.compromiso.pk])
        self.assertFalse(buscar(qs,'inexistente',['descripcion']).exists())

    def test_busqueda_rut_con_y_sin_puntos(self):
        for q in ('33.500.001-3','335000013','33500001-3'):
            self.assertEqual(buscar(Vecino.objects.all(),q,['rut']).get().pk,self.vecino.pk)

    def test_atencion_incluye_buscador_rut_y_lista_busca_por_rut(self):
        tipo=TipoAtencion.objects.create(nombre='Consulta social')
        sub=SubAtencion.objects.create(nombre='Primera consulta',tipo_atencion=tipo)
        atencion=Atencion.objects.create(vecino=self.vecino,tipo_atencion=tipo,sub_atencion=sub,delegacion=self.centro,usuario=self.admin)
        self.autenticar()
        self.assertIn('busqueda_vecino',AtencionForm().fields)
        form=self.client.get('/mantenedores/atenciones/nuevo/')
        self.assertContains(form,'data-buscar-vecino')
        self.assertContains(form,'data-selector-vecino')
        self.assertContains(self.client.get('/mantenedores/atenciones/',{'q':'335000013'}),'José Pérez')
        self.assertNotContains(self.client.get('/mantenedores/atenciones/',{'q':'11111111'}),'José Pérez')

    def test_excel_usuarios_todas_cuentas_sin_claves(self):
        self.autenticar()
        self.funcionario.estado=EstadoRegistro.INACTIVO
        self.funcionario.save(update_fields=['estado'])
        response=self.client.get('/administracion/usuarios/excel/')
        rows=hojas(response)['Usuarios']
        self.assertEqual(len(rows),Usuario.objects.count()+1)
        self.assertIn('Inactivo',str(rows))
        self.assertIn('RUT',rows[0])
        self.assertIn('Código cargo',rows[0])
        self.assertNotIn('password',str(rows).lower())
        self.assertNotIn(self.admin.user.password,str(rows))

    def test_excel_usuarios_restringido_a_administracion(self):
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.get('/administracion/usuarios/excel/').status_code,403)

    def test_busqueda_usuarios_por_rut_y_palabras(self):
        self.autenticar()
        response=self.client.get('/administracion/usuarios/',{'q':'33.100.032-9'})
        self.assertEqual(len(response.context['usuarios']),1)
        self.assertEqual(response.context['usuarios'][0]['id_usuario'],self.funcionario.codigo)
        self.assertEqual(len(self.client.get('/administracion/usuarios/',{'q':'Prueba Ana'}).context['usuarios']),1)

    def test_excel_trabajo_seis_hojas_y_resumen_correcto(self):
        self.autenticar(self.funcionario)
        result=hojas(self.client.get('/control/tubo-trabajo/excel/'))
        self.assertEqual(set(result),{'Resumen','Tubo de trabajo','Por funcionario','Por delegación','Actividades','Metas'})
        self.assertEqual(len(result['Tubo de trabajo']),2)
        self.assertEqual(len(result['Actividades']),2)
        self.assertEqual(len(result['Metas']),2)
        self.assertNotIn('restringid',str(result))
        resumen=dict(result['Resumen'][1:])
        self.assertEqual(resumen['Total compromisos'],'1')
        self.assertEqual(resumen['Realizado (%)'],'100.0')
        self.assertEqual(result['Metas'][1][-2:],['80.0','40.0'])

    def test_filtros_tubo_y_exportacion_coinciden(self):
        self.autenticar()
        query={'q':'publica jose','estado':'REALIZADO','delegacion':self.centro.nombre}
        page=self.client.get('/control/tubo-trabajo/',query)
        self.assertContains(page,self.compromiso.codigo)
        self.assertNotContains(page,self.otro_compromiso.codigo)
        exported=hojas(self.client.get('/control/tubo-trabajo/excel/',query))
        self.assertEqual(len(exported['Tubo de trabajo'])-1,page.context['total_compromisos'])

    def test_fuera_de_ambito_no_lee_ni_mueve_tubo(self):
        self.autenticar(self.funcionario)
        self.assertNotContains(self.client.get('/control/tubo-trabajo/'),self.otro_compromiso.codigo)
        self.client.post('/control/tubo-trabajo/',{'id_compromiso':self.otro_compromiso.codigo,'estado':'REALIZADO'})
        self.otro_compromiso.refresh_from_db()
        self.assertEqual(self.otro_compromiso.estado,'PENDIENTE')
        for url in ('/control/tubo-trabajo/','/control/tubo-trabajo/excel/'):
            response=self.client.get(url,{'delegacion':self.rural.nombre})
            if url.endswith('excel/'):
                self.assertEqual(len(hojas(response)['Tubo de trabajo']),1)
            else:
                self.assertEqual(response.context['total_compromisos'],0)

    def test_actividades_busqueda_y_ambito(self):
        self.autenticar(self.funcionario)
        response=self.client.get('/control/actividades/',{'q':'publica jose'})
        self.assertEqual(response.context['total'],1)
        self.assertContains(response,self.actividad.codigo)
        self.assertNotContains(response,'Actividad rural restringida')

    def test_anonimos_no_exportan(self):
        for url in ('/administracion/usuarios/excel/','/control/tubo-trabajo/excel/'):
            self.assertEqual(self.client.get(url).status_code,302)

    def test_textos_excel_no_son_formulas(self):
        self.autenticar()
        self.compromiso.descripcion='=HYPERLINK("x") & ñ\x01'
        self.compromiso.save(update_fields=['descripcion'])
        result=hojas(self.client.get('/control/tubo-trabajo/excel/'))
        self.assertIn('=HYPERLINK',str(result))

    def test_paginador_tamano_salto_filtros_y_limites(self):
        from core.paginacion import paginar
        from django.test import RequestFactory
        request=RequestFactory().get('/',{'q':'José plaza','estado':'REALIZADO','per_page':'25','page':'2'})
        page,ctx=paginar(request,list(range(61)))
        self.assertEqual(list(page),list(range(25,50)))
        self.assertEqual(ctx['paginator'].count,61)
        self.assertIn('q=Jos%C3%A9+plaza',ctx['consulta_pagina'])
        self.assertIn(('estado','REALIZADO'),ctx['filtros_pagina'])
        for size in ('0','500','abc','-1'):
            page,ctx=paginar(RequestFactory().get('/',{'per_page':size,'page':'999'}),list(range(31)))
            self.assertEqual(ctx['por_pagina'],10)
            self.assertEqual(page.number,4)

    def test_paginador_no_limita_exportacion_ni_resumen(self):
        for n in range(20):
            Compromiso.objects.create(descripcion=f'Compromiso {n}',vecino=self.vecino,funcionario=self.funcionario.funcionario,
                delegacion=self.centro,fecha_compromiso=timezone.localdate(),estado='REALIZADO')
        self.autenticar(self.funcionario)
        page=self.client.get('/control/tubo-trabajo/',{'page':2,'per_page':10})
        self.assertEqual(page.context['total_compromisos'],21)
        self.assertEqual(page.context['pct_realizado'],100)
        self.assertEqual(len(page.context['page_obj']),10)
        excel=hojas(self.client.get('/control/tubo-trabajo/excel/',{'page':2,'per_page':10}))
        self.assertEqual(len(excel['Tubo de trabajo']),22)

    def test_paginador_vacio_visible(self):
        self.autenticar()
        response=self.client.get('/administracion/usuarios/',{'q':'sin-resultados-abcdefg'})
        self.assertContains(response,'0</strong> resultados')
