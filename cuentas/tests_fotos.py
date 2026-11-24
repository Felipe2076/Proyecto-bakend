"""Foto de perfil: validación, recorte, metadatos, entrega con alcance. Imágenes generadas en memoria."""
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from control_gestion import tests_kanban
from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.fotos import FotoInvalida, procesar_foto
from cuentas.perfiles import sincronizar_usuario

MEDIA = tempfile.mkdtemp(prefix='siged-fotos-')


def imagen(formato='JPEG', tamano=(900, 600), color=(200, 30, 40), exif=False):
    salida = BytesIO()
    img = Image.new('RGB', tamano, color)
    extra = {}
    if exif:
        datos = Image.Exif()
        datos[0x010F] = 'CamaraFicticia'  # Make
        extra['exif'] = datos
    img.save(salida, formato, **extra)
    ext = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'GIF': 'gif'}[formato]
    return SimpleUploadedFile(f'foto.{ext}', salida.getvalue(), content_type=f'image/{ext}')


@override_settings(MEDIA_ROOT=MEDIA, SESSION_ENGINE='django.contrib.sessions.backends.db',
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FotoPerfilTests(TestCase):
    autenticar = tests_kanban.KanbanTests.autenticar

    @classmethod
    def setUpTestData(cls):
        tests_kanban.KanbanTests.setUpTestData.__func__(cls)
        cls.otro = crear_cuenta(codigo='USR-FT', rut='33100121-1', password='Prueba123!', rol_codigo='funcionario',
                                correo='foto.rural@siged.test', nombre='Persona Rural Foto', delegacion=cls.rural)
        for perfil in (cls.admin, cls.funcionario, cls.otro):
            sincronizar_usuario(perfil)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def test_recorta_a_512_y_quita_metadatos(self):
        contenido = procesar_foto(imagen(exif=True))
        resultado = Image.open(BytesIO(contenido.read()))
        self.assertEqual((resultado.format, resultado.size), ('JPEG', (512, 512)))
        self.assertNotIn(0x010F, resultado.getexif())

    def test_rechaza_formato_peso_y_contenido_falso(self):
        with self.assertRaises(FotoInvalida):
            procesar_foto(imagen('GIF'))
        with self.assertRaises(FotoInvalida):
            procesar_foto(SimpleUploadedFile('foto.jpg', b'<?php echo 1; ?>', content_type='image/jpeg'))
        grande = SimpleUploadedFile('foto.jpg', b'0' * (5 * 1024 * 1024 + 1), content_type='image/jpeg')
        with self.assertRaises(FotoInvalida):
            procesar_foto(grande)
        with self.assertRaises(FotoInvalida):
            procesar_foto(imagen(tamano=(30, 30)))

    def test_subir_reemplazar_y_quitar_desde_mi_perfil(self):
        self.autenticar(self.funcionario)
        self.assertEqual(self.client.post('/perfil/', {'foto': imagen('PNG')}).status_code, 302)
        self.funcionario.refresh_from_db()
        primera = self.funcionario.foto.name
        self.assertTrue(primera.startswith('fotos/') and primera.endswith('.jpg'))
        self.client.post('/perfil/', {'foto': imagen('WEBP')})
        self.funcionario.refresh_from_db()
        self.assertNotEqual(self.funcionario.foto.name, primera)
        self.assertFalse(self.funcionario.foto.storage.exists(primera))  # la anterior se borró
        self.client.post('/perfil/', {'accion': 'quitar'})
        self.funcionario.refresh_from_db()
        self.assertFalse(self.funcionario.foto)

    def test_archivo_invalido_muestra_error_en_la_pagina(self):
        self.autenticar(self.funcionario)
        r = self.client.post('/perfil/', {'foto': SimpleUploadedFile('x.jpg', b'nada', content_type='image/jpeg')})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no es una imagen válida')

    def test_foto_solo_visible_dentro_del_alcance(self):
        self.autenticar(self.otro)
        self.client.post('/perfil/', {'foto': imagen()})
        self.otro.refresh_from_db()
        url = f'/cuentas/foto/{self.otro.codigo}/'
        r = self.client.get(url)
        self.assertEqual((r.status_code, r['Content-Type']), (200, 'image/jpeg'))
        self.assertEqual(self.client.get(url, HTTP_IF_NONE_MATCH=r['ETag']).status_code, 304)
        self.autenticar(self.funcionario)  # otra delegación
        self.assertEqual(self.client.get(url).status_code, 404)
        self.autenticar(self.admin)  # superusuario
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)  # anónimo: al login
