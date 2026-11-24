"""API de sincronización para la app móvil (SQLite ↔ MySQL). Datos ficticios."""
import io
import uuid
from datetime import timedelta

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from control_gestion.models import OrganizacionComunitaria, SesionMovil, TerritorioDelegacion
from control_gestion.tests_movil import MovilTests

API = '/api/v1/'


class ApiSincronizacionTests(MovilTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        permisos = Permission.objects.filter(codename__in=['view_organizacioncomunitaria', 'add_organizacioncomunitaria',
                                                           'change_organizacioncomunitaria'])
        cls.delegado.user.user_permissions.add(*permisos)
        cls.otro.user.user_permissions.add(*permisos)
        TerritorioDelegacion.objects.create(delegacion=cls.centro, nombre='Territorio Centro Ficticio')
        cls.org = OrganizacionComunitaria.objects.create(nombre='Junta API Centro', delegacion=cls.centro,
                                                         presidente_nombre='Persona Uno', presidente_rut='12345678-5')
        OrganizacionComunitaria.objects.create(nombre='Junta API Rural', delegacion=cls.rural)

    # Las pruebas heredadas de MovilTests ya corren en su propia clase.
    test_guardar_reintentar_y_revisar_con_permisos = None

    def test_token_de_30_dias_renovable_y_sesiones(self):
        a = self.auth(self.fun)
        sesion = SesionMovil.objects.get(usuario=self.fun)
        self.assertGreater(sesion.expira, timezone.now() + timedelta(days=29))
        r = self.client.post(API + 'sesion/renovar/', **a)
        self.assertEqual(r.status_code, 200)
        nuevo = {'HTTP_AUTHORIZATION': 'Bearer ' + r.json()['token'], 'secure': True}
        self.assertEqual(self.client.get(API + 'perfil/', **a).status_code, 401)  # el anterior quedó anulado
        lista = self.client.get(API + 'sesiones/', **nuevo).json()['sesiones']
        self.assertEqual(len(lista), 1)
        self.assertTrue(lista[0]['actual'])

    def test_perfil_y_foto_por_api(self):
        a = self.auth(self.fun)
        self.assertEqual(self.client.get(API + 'perfil/', **a).json()['codigo'], self.fun.codigo)
        b = io.BytesIO()
        Image.new('RGB', (300, 200), '#123456').save(b, format='JPEG')
        r = self.client.post(API + 'perfil/foto/', {'foto': SimpleUploadedFile('f.jpg', b.getvalue(), content_type='image/jpeg')}, **a)
        self.assertEqual(r.status_code, 200, r.content)
        url = r.json()['foto_url']
        self.assertTrue(url.startswith(f'/api/v1/usuarios/{self.fun.codigo}/foto/'))
        r = self.client.get(url, **a)
        self.assertEqual(r['Content-Type'], 'image/jpeg')
        r.close()  # Windows no borra un archivo abierto
        self.assertEqual(self.client.get(url, **self.auth(self.otro)).status_code, 404)  # otra delegación
        mala = self.client.post(API + 'perfil/foto/', {'foto': SimpleUploadedFile('f.jpg', b'no', content_type='image/jpeg')}, **a)
        self.assertEqual(mala.status_code, 422)

    def test_usuarios_acotados_y_sin_rut_ajeno(self):
        datos = self.client.get(API + 'usuarios/', **self.auth(self.fun)).json()
        codigos = {u['codigo'] for u in datos['usuarios']}
        self.assertIn(self.delegado.codigo, codigos)
        self.assertNotIn(self.otro.codigo, codigos)
        self.assertNotIn('rut', datos['usuarios'][0])

    def test_organizaciones_alcance_permisos_y_ruts(self):
        self.assertEqual(self.client.get(API + 'organizaciones/', **self.auth(self.fun)).status_code, 403)
        datos = self.client.get(API + 'organizaciones/', **self.auth(self.delegado)).json()
        nombres = [o['nombre'] for o in datos['organizaciones']]
        self.assertEqual(nombres, ['Junta API Centro'])
        self.assertEqual(datos['organizaciones'][0]['directiva'][0]['rut'], '12.345.678-5')

    def test_alta_idempotente_y_errores_en_json(self):
        a = self.auth(self.delegado)
        cid = str(uuid.uuid4())
        cuerpo = {'client_id': cid, 'nombre': 'Club Móvil Ficticio', 'tipo': 'DEPORTIVA', 'telefono': '912345678',
                  'delegacion': self.centro.pk, 'territorio': 'Territorio Centro Ficticio'}
        r = self.client.post(API + 'organizaciones/', cuerpo, content_type='application/json', **a)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['organizacion']['telefono'], '+56 9 1234 5678')
        repetido = self.client.post(API + 'organizaciones/', cuerpo, content_type='application/json', **a)
        self.assertTrue(repetido.json()['repetido'])
        self.assertEqual(OrganizacionComunitaria.objects.filter(nombre='Club Móvil Ficticio').count(), 1)
        otro = dict(cuerpo, nombre='Otro nombre')
        self.assertEqual(self.client.post(API + 'organizaciones/', otro, content_type='application/json', **a).status_code, 409)
        malo = self.client.post(API + 'organizaciones/', {'client_id': str(uuid.uuid4()), 'nombre': 'X', 'telefono': '1'},
                                content_type='application/json', **a)
        self.assertEqual(malo.status_code, 422)
        self.assertIn('telefono', malo.json()['campos'])
        # Fuera de su delegación no puede crear.
        fuera = dict(cuerpo, client_id=str(uuid.uuid4()), nombre='Club Rural Intruso', delegacion=self.rural.pk, territorio='')
        self.assertEqual(self.client.post(API + 'organizaciones/', fuera, content_type='application/json', **a).status_code, 422)

    def test_patch_con_version_y_conflicto(self):
        a = self.auth(self.delegado)
        url = f'{API}organizaciones/{self.org.codigo}/'
        version = self.client.get(url, **a).json()['organizacion']['version']
        r = self.client.patch(url, {'version': version, 'telefono': '+56 51 223 4567'}, content_type='application/json', **a)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['organizacion']['version'], version + 1)
        self.assertEqual(r.json()['organizacion']['presidente_nombre'] if False else r.json()['organizacion']['nombre'], 'Junta API Centro')
        viejo = self.client.patch(url, {'version': version, 'telefono': '+56 9 8765 4321'}, content_type='application/json', **a)
        self.assertEqual(viejo.status_code, 409)
        self.assertEqual(viejo.json()['servidor']['telefono'], '+56 51 223 4567')
        self.assertEqual(self.client.patch(f'{API}organizaciones/NO-EXISTE/', {}, content_type='application/json', **a).status_code, 404)

    def test_sync_incremental_con_bajas(self):
        a = self.auth(self.delegado)
        primero = self.client.get(API + 'sync/', **a).json()
        self.assertEqual({o['nombre'] for o in primero['organizaciones']}, {'Junta API Centro'})
        marca = primero['servidor_ahora']
        self.assertEqual(self.client.get(API + 'sync/', {'desde': marca}, **a).json()['organizaciones'], [])
        self.org.nombre = 'Junta API Centro Renombrada'
        self.org.save()
        territorio = TerritorioDelegacion.objects.get(nombre='Territorio Centro Ficticio')
        uid = str(territorio.uuid)
        territorio.delete()
        cambios = self.client.get(API + 'sync/', {'desde': marca}, **a).json()
        self.assertEqual([o['nombre'] for o in cambios['organizaciones']], ['Junta API Centro Renombrada'])
        self.assertIn(uid, {b['uuid'] for b in cambios['bajas']})
        self.assertEqual(self.client.get(API + 'sync/', {'desde': 'ayer'}, **a).status_code, 400)

    def test_catalogos(self):
        datos = self.client.get(API + 'catalogos/', **self.auth(self.fun)).json()
        self.assertTrue(any(t['valor'] == 'JJVV' for t in datos['tipos_organizacion']))
        self.assertTrue(datos['delegaciones'])
