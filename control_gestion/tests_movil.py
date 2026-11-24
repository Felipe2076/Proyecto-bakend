import io,json,uuid,tempfile
from datetime import timedelta
from PIL import Image
from django.test import TestCase,Client,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Cargo,Delegacion
from control_gestion.models import Actividad,Compromiso,ItemFuncionario,Meta,SesionMovil
from requerimientos.models import Vecino

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class MovilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.centro=Delegacion.objects.create(nombre='Centro ficticio')
        cls.rural=Delegacion.objects.create(nombre='Rural ficticio')
        for attr,rut,rol,delegacion,cargo in [('fun','33100032-9','funcionario',cls.centro,None),('delegado','33100011-6','jefatura',cls.centro,Cargo.objects.create(nombre='Delegado territorial')),('otro','33100013-2','funcionario',cls.rural,None)]:
            setattr(cls,attr,crear_cuenta(codigo=attr,rut=rut,password='SoloPrueba123!',rol_codigo=rol,correo=attr+'@siged.test',nombre=attr+' Ficticio',delegacion=delegacion,cargo=cargo))
        cls.meta=Meta.objects.create(nombre='Visitas de prueba')
        for p in (cls.fun,cls.delegado,cls.otro):
            ItemFuncionario.objects.create(funcionario=p.funcionario,meta=cls.meta,ponderador=100,meta_trimestre=10)
        v=Vecino.objects.create(nombre='Vecino ficticio',delegacion=cls.centro)
        cls.tubo=Compromiso.objects.create(vecino=v,funcionario=cls.fun.funcionario,delegacion=cls.centro,descripcion='Trabajo propio prueba',fecha_compromiso=timezone.localdate())
        cls.ajeno=Compromiso.objects.create(vecino=v,funcionario=cls.otro.funcionario,delegacion=cls.rural,descripcion='Trabajo rural restringido',fecha_compromiso=timezone.localdate())
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        cfg=override_settings(MEDIA_ROOT=tmp.name);cfg.enable();self.addCleanup(cfg.disable)
    def auth(self,perfil):
        r=self.client.post('/api/v1/sesion/',{'rut':perfil.funcionario.rut,'password':'SoloPrueba123!'},content_type='application/json',secure=True)
        self.assertEqual(r.status_code,200,r.content)
        return {'HTTP_AUTHORIZATION':'Bearer '+r.json()['token'],'secure':True}
    def documento(self):
        b=io.BytesIO();Image.new('RGB',(24,24),'#891127').save(b,format='PNG')
        return SimpleUploadedFile('evidencia.png',b.getvalue(),content_type='image/png')
    def enviar(self,auth,client_id=None,fecha=None,tipo='RESULTADO'):
        return self.client.post('/api/v1/actividades/',{'client_id':client_id or str(uuid.uuid4()),'meta':self.meta.codigo,'fecha_actividad':fecha or timezone.localdate().isoformat(),'tipo_registro':tipo,'servicio':'Visita ficticia demostrable','contacto':'Contacto ficticio','evidencia':self.documento()},**auth)
    def decidir(self,auth,codigo,decision,version):
        return self.client.post(f'/api/v1/actividades/{codigo}/revision/',{'version':version,'decision':decision,'comentario':'Observación ficticia de prueba'},content_type='application/json',**auth)
    def test_guardar_reintentar_y_revisar_con_permisos(self):
        f=self.auth(self.fun);d=self.auth(self.delegado);o=self.auth(self.otro);uid=str(uuid.uuid4())
        r=self.enviar(f,uid);self.assertEqual(r.status_code,201,r.content);a=r.json()['actividad'];codigo=a['codigo']
        self.assertEqual(a['estado'],'PENDIENTE')
        self.assertEqual(self.enviar(f,uid).json()['actividad']['codigo'],codigo)
        self.assertEqual(Actividad.objects.count(),1)
        self.assertEqual(self.client.get(a['evidencia'],**o).status_code,404)
        file=self.client.get(a['evidencia'],**d);self.assertEqual(file.status_code,200);self.assertTrue(b''.join(file.streaming_content).startswith(b'\x89PNG'))
        self.assertEqual(self.decidir(f,codigo,'APROBADA',0).status_code,403)
        self.assertEqual(self.decidir(d,codigo,'CORRECCION',0).status_code,200)
        url=f'/api/v1/actividades/{codigo}/'
        self.assertEqual(self.client.post(url,{'version':1,'contacto':'Contacto corregido','servicio':'Servicio corregido','evidencia':self.documento()},**f).status_code,200)
        self.assertEqual(self.decidir(d,codigo,'APROBADA',2).status_code,200)
        self.assertEqual(self.decidir(d,codigo,'APROBADA',2).status_code,409)
        self.assertEqual(ItemFuncionario.objects.get(funcionario=self.fun.funcionario).avance_actual,1)
        self.assertEqual(len(self.client.get(url,**f).json()['historial']),3)
    def test_rechazo_fecha_fuera_de_plazo_y_autoaprobacion(self):
        f=self.auth(self.fun);d=self.auth(self.delegado)
        self.assertEqual(self.enviar(f,fecha=(timezone.localdate()-timedelta(days=14)).isoformat()).status_code,422)
        a=self.enviar(f).json()['actividad']
        self.assertEqual(self.decidir(d,a['codigo'],'RECHAZADA',0).status_code,200)
        propio=self.enviar(d).json()['actividad']
        self.assertEqual(self.decidir(d,propio['codigo'],'APROBADA',0).status_code,403)
        self.assertEqual(ItemFuncionario.objects.get(funcionario=self.fun.funcionario).avance_actual,0)
    def test_api_web_comparten_revision_y_mantienen_csrf(self):
        f=self.auth(self.fun);a=self.enviar(f).json()['actividad'];url=f'/control/actividades/{a["codigo"]}/revision/'
        web=Client(enforce_csrf_checks=True);web.force_login(self.delegado.user)
        self.assertEqual(web.post(url,{'version':0,'decision':'APROBADA','comentario':'Revisión web'},secure=True).status_code,403)
        self.assertEqual(web.get(url,secure=True).status_code,200)
        token=web.cookies['csrftoken'].value
        r=web.post(url,{'csrfmiddlewaretoken':token,'version':0,'decision':'APROBADA','comentario':'Revisión web'},HTTP_ORIGIN='https://testserver',secure=True)
        self.assertEqual(r.status_code,302,r.content)
        self.assertEqual(self.client.get(f'/api/v1/actividades/{a["codigo"]}/',**f).json()['estado'],'APROBADA')
    def test_tubo_excel_y_revocacion(self):
        f=self.auth(self.fun)
        self.assertEqual(self.client.get('/api/v1/panel/',**f).json()['compromisos'],1)
        self.assertEqual(self.client.get('/api/v1/compromisos/?equipo=1',**f).status_code,403)
        url=f'/api/v1/compromisos/{self.tubo.codigo}/estado/'
        datos={'estado':'EN PROCESO','estado_anterior':self.tubo.estado,'observaciones_anteriores':'','observaciones':'Trabajando'}
        self.assertEqual(self.client.post(url,datos,content_type='application/json',**f).status_code,200)
        self.assertEqual(self.client.post(url,datos,content_type='application/json',**f).status_code,409)
        from zipfile import ZipFile
        r=self.client.get('/api/v1/excel/',**f);self.assertEqual(r.status_code,200)
        with ZipFile(io.BytesIO(r.content)) as z:
            s=z.read('xl/worksheets/sheet2.xml').decode();self.assertIn('Trabajo propio prueba',s);self.assertNotIn('rural restringido',s)
        self.assertEqual(self.client.post('/api/v1/sesion/cerrar/',**f).status_code,200)
        self.assertEqual(self.client.get('/api/v1/panel/',**f).status_code,401)
    def test_vencida_archivo_invalido_y_cookie_no_autentica(self):
        f=self.auth(self.fun)
        r=self.client.post('/api/v1/actividades/',{'client_id':str(uuid.uuid4()),'meta':self.meta.codigo,'fecha_actividad':timezone.localdate().isoformat(),'tipo_registro':'RESULTADO','servicio':'Visita ficticia','contacto':'Contacto ficticio','evidencia':SimpleUploadedFile('falso.png',b'texto')},**f)
        self.assertEqual(r.status_code,422);self.assertEqual(Actividad.objects.count(),0)
        SesionMovil.objects.update(expira=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.client.get('/api/v1/panel/',**f).status_code,401)
        self.client.force_login(self.fun.user)
        self.assertEqual(self.client.get('/api/v1/panel/',secure=True).status_code,401)
