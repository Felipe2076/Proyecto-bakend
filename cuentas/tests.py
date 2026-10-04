"""Pruebas de mantenedores y de autenticación contra la base de datos."""

import builtins
import re

from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import Client, TestCase, override_settings

from cuentas.fabrica_pruebas import crear_cuenta
from cuentas.models import Delegacion, Rol


class RolesMantenedorTests(TestCase):
    def setUp(self):
        self.rol_admin = Rol.objects.create(
            codigo="administrador", nombre="Administrador", descripcion="Acceso total"
        )
        delegacion = Delegacion.objects.create(nombre="Delegación Centro")
        perfil = crear_cuenta(
            codigo="USR-001",
            rut="33100011-6",
            password="Admin123!",
            rol_codigo="administrador",
            correo="usr-001@siged.test",
            nombre="Admin Prueba",
            delegacion=delegacion,
        )
        self.user = perfil.user
        self.client = Client()
        self.client.post("/login/", {"rut": "33100011-6", "password": "Admin123!"})

    def test_anonimo_redirige_al_login(self):
        anon = Client()
        respuesta = anon.get("/mantenedores/roles/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/", respuesta["Location"])

    def test_sesion_mock_sin_usuario_django_no_entra(self):
        cliente = Client()
        sesion = cliente.session
        sesion["usuario"] = {"rol": "administrador", "nombre": "Prueba", "rol_etiqueta": "Administrador"}
        sesion.save()
        respuesta = cliente.get("/mantenedores/roles/")
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/", respuesta["Location"])

    def test_listado_muestra_busqueda_y_acciones(self):
        respuesta = self.client.get("/mantenedores/roles/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Agregar")
        self.assertContains(respuesta, "Buscar")
        self.assertContains(respuesta, "Modificar")
        self.assertContains(respuesta, "Eliminar")
        self.assertContains(respuesta, "Administrador")

    def test_busqueda_icontains(self):
        Rol.objects.create(codigo="alfa", nombre="Alfa búsqueda", descripcion="uno")
        Rol.objects.create(codigo="beta", nombre="Beta otro", descripcion="dos")
        respuesta = self.client.get("/mantenedores/roles/", {"q": "búsqueda"})
        self.assertContains(respuesta, "Alfa búsqueda")
        self.assertNotContains(respuesta, "Beta otro")

    def test_crear_editar_eliminar(self):
        alta = self.client.post(
            "/mantenedores/roles/nuevo/",
            {"codigo": "operador", "nombre": "Operador", "descripcion": "Gestiona atenciones"},
            follow=True,
        )
        self.assertEqual(alta.status_code, 200)
        rol = Rol.objects.get(codigo="operador")
        self.assertContains(alta, "Se guardó")

        edicion = self.client.post(
            f"/mantenedores/roles/{rol.pk}/editar/",
            {
                "codigo": "operador",
                "nombre": "Operador de terreno",
                "descripcion": "Gestiona atenciones en terreno",
            },
            follow=True,
        )
        self.assertEqual(edicion.status_code, 200)
        rol.refresh_from_db()
        self.assertEqual(rol.nombre, "Operador de terreno")

        confirmacion = self.client.get(f"/mantenedores/roles/{rol.pk}/eliminar/")
        self.assertContains(confirmacion, "Confirmar eliminación")
        self.assertTrue(Rol.objects.filter(pk=rol.pk).exists())

        baja = self.client.post(f"/mantenedores/roles/{rol.pk}/eliminar/", follow=True)
        self.assertEqual(baja.status_code, 200)
        self.assertFalse(Rol.objects.filter(pk=rol.pk).exists())

    def test_crear_invalido_muestra_errores(self):
        antes = Rol.objects.count()
        respuesta = self.client.post("/mantenedores/roles/nuevo/", {"codigo": "", "nombre": "", "descripcion": ""})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "obligatorio")
        self.assertEqual(Rol.objects.count(), antes)

    def test_ventanilla_no_administra(self):
        Rol.objects.create(codigo="ventanilla", nombre="Ventanilla", descripcion="Ingreso")
        delegacion = Delegacion.objects.get(nombre="Delegación Centro")
        crear_cuenta(
            codigo="USR-004",
            rut="33100004-3",
            password="Ventanilla1!",
            rol_codigo="ventanilla",
            correo="usr-004@siged.test",
            nombre="Ventanilla Prueba",
            delegacion=delegacion,
        )
        self.client.logout()
        self.client.post("/login/", {"rut": "33100004-3", "password": "Ventanilla1!"})
        respuesta = self.client.get("/mantenedores/roles/", follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no tiene acceso")


PERFILES_DEMO = (
    ("33100011-6", "ClaveAdmin1!", "administrador", "admin.prueba@siged.test", "/mantenedores/roles/", True),
    ("33100001-9", "ClaveJefatura1!", "jefatura", "jefatura.prueba@siged.test", "/mantenedores/roles/", False),
    ("33100002-7", "ClaveFuncionario1!", "funcionario", "funcionario.prueba@siged.test", "/administracion/usuarios/", False),
    ("33100004-3", "ClaveVentanilla1!", "ventanilla", "ventanilla.prueba@siged.test", "/control/actividades/", False),
)


class PortadaPublicaTests(TestCase):
    def test_portada_publica_y_dashboard_privado(self):
        anon = Client()
        portada = anon.get("/")
        self.assertEqual(portada.status_code, 200)
        self.assertContains(portada, "Ingresar")
        tablero = anon.get("/control/")
        self.assertEqual(tablero.status_code, 302)
        self.assertIn("/login/", tablero["Location"])


class AutenticacionOrmTests(TestCase):
    """Los cuatro perfiles entran por Usuario.user y el rol sale de Usuario.rol."""

    def setUp(self):
        self.delegacion = Delegacion.objects.create(nombre="Delegación Rural")
        self.users = {}
        for indice, (rut, password, rol_codigo, correo, _ruta, _permitido) in enumerate(PERFILES_DEMO, start=1):
            perfil = crear_cuenta(
                codigo=f"USR-10{indice}",
                rut=rut,
                password=password,
                rol_codigo=rol_codigo,
                correo=correo,
                nombre=f"Perfil {rol_codigo}",
                delegacion=self.delegacion,
            )
            self.users[rut] = perfil.user

    def _abrir(self, path, *args, **kwargs):
        if "usuarios.json" in str(path):
            raise AssertionError(f"el flujo abrió {path}")
        return self._open_real(path, *args, **kwargs)

    def test_login_usa_la_base_y_no_el_json(self):
        self._open_real = builtins.open
        builtins.open = self._abrir
        try:
            for rut, password, rol_codigo, _correo, ruta, permitido in PERFILES_DEMO:
                cliente = Client()
                respuesta = cliente.post("/login/", {"rut": rut, "password": password})
                self.assertEqual(respuesta.status_code, 302, rut)
                self.assertNotIn("/login/", respuesta["Location"])
                sesion = cliente.session["usuario"]
                self.assertEqual(sesion["rol"], rol_codigo)
                self.assertEqual(sesion["username"], rut)
                self.assertEqual(sesion["delegacion"], "Delegación Rural")
                self.assertEqual(int(cliente.session["_auth_user_id"]), self.users[rut].pk)
                pantalla = cliente.get(ruta, follow=True)
                self.assertEqual(pantalla.status_code, 200)
                if permitido:
                    self.assertNotContains(pantalla, "no tiene acceso")
                else:
                    self.assertContains(pantalla, "no tiene acceso")
                ajeno = Client()
                clave_mala = ajeno.post("/login/", {"rut": rut, "password": "no-es-la-clave"})
                self.assertContains(clave_mala, "incorrectos")
        finally:
            builtins.open = self._open_real

    def _codigo_del_correo(self):
        self.assertEqual(len(mail.outbox), 1)
        encontrado = re.search(r"(\d{6})", mail.outbox[0].body)
        self.assertIsNotNone(encontrado)
        return encontrado.group(1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_recuperacion_guarda_la_clave_en_user(self):
        from cuentas.models import CodigoRecuperacion

        self._open_real = builtins.open
        builtins.open = self._abrir
        cliente = Client()
        try:
            mail.outbox.clear()
            pedido = cliente.post("/recuperar/", {"correo": "admin.prueba@siged.test"}, follow=True)
            self.assertEqual(pedido.status_code, 200)
            codigo = self._codigo_del_correo()
            self.assertNotIn(codigo, pedido.content.decode())
            fila = CodigoRecuperacion.objects.get()
            self.assertNotEqual(fila.codigo_hash, codigo)
            self.assertTrue(check_password(codigo, fila.codigo_hash))
            self.assertTrue(fila.codigo_hash.startswith("pbkdf2_"))
            sesion = cliente.session["recuperacion"]
            self.assertNotIn("codigo", sesion)
            self.assertNotIn(codigo, str(sesion))
            digitos = {f"d{i}": digito for i, digito in enumerate(codigo, start=1)}
            validado = cliente.post("/recuperar/codigo/", digitos)
            self.assertEqual(validado.status_code, 302)
            fila.refresh_from_db()
            self.assertTrue(fila.usado)
            sesion = cliente.session
            sesion["recuperacion"] = {"usuario_id": fila.usuario_id, "verificado": False}
            sesion.save()
            reuso = cliente.post("/recuperar/codigo/", digitos)
            self.assertEqual(reuso.status_code, 200)
            self.assertContains(reuso, "ya no es válido")
            nueva = "NuevaClave1!"
            sesion = cliente.session
            sesion["recuperacion"] = {"usuario_id": fila.usuario_id, "verificado": True}
            sesion.save()
            guardada = cliente.post(
                "/recuperar/nueva/",
                {"password": nueva, "confirmacion": nueva},
                follow=True,
            )
            self.assertEqual(guardada.status_code, 200)
            self.assertContains(guardada, "actualizada")
        finally:
            builtins.open = self._open_real
        user = self.users["33100011-6"]
        user.refresh_from_db()
        self.assertTrue(user.check_password(nueva))
        self.assertFalse(user.check_password("ClaveAdmin1!"))
        ingreso = Client()
        respuesta = ingreso.post("/login/", {"rut": "33.100.011-6", "password": nueva})
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotIn("/login/", respuesta["Location"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_un_codigo_nuevo_invalida_el_anterior(self):
        self._open_real = builtins.open
        builtins.open = self._abrir
        cliente = Client()
        try:
            mail.outbox.clear()
            cliente.post("/recuperar/", {"correo": "admin.prueba@siged.test"})
            primero = self._codigo_del_correo()
            mail.outbox.clear()
            cliente.post("/recuperar/codigo/", {"accion": "reenviar"})
            segundo = self._codigo_del_correo()
            self.assertNotEqual(primero, segundo)
            viejo = {f"d{i}": digito for i, digito in enumerate(primero, start=1)}
            rechazado = cliente.post("/recuperar/codigo/", viejo)
            self.assertEqual(rechazado.status_code, 200)
            self.assertContains(rechazado, "no coincide")
            self.assertNotContains(rechazado, primero)
            nuevo = {f"d{i}": digito for i, digito in enumerate(segundo, start=1)}
            aceptado = cliente.post("/recuperar/codigo/", nuevo)
            self.assertEqual(aceptado.status_code, 302)
            self.assertIn("/recuperar/nueva/", aceptado["Location"])
        finally:
            builtins.open = self._open_real

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_el_quinto_intento_invalida_el_codigo(self):
        self._open_real = builtins.open
        builtins.open = self._abrir
        cliente = Client()
        try:
            mail.outbox.clear()
            cliente.post("/recuperar/", {"correo": "admin.prueba@siged.test"})
            codigo = self._codigo_del_correo()
            malo = "222222" if codigo != "222222" else "333333"
            digitos_malos = {f"d{i}": digito for i, digito in enumerate(malo, start=1)}
            for _ in range(4):
                respuesta = cliente.post("/recuperar/codigo/", digitos_malos)
                self.assertContains(respuesta, "no coincide")
            agotado = cliente.post("/recuperar/codigo/", digitos_malos)
            self.assertContains(agotado, "Demasiados intentos")
            correcto = {f"d{i}": digito for i, digito in enumerate(codigo, start=1)}
            despues = cliente.post("/recuperar/codigo/", correcto)
            self.assertContains(despues, "ya no es válido")
            self.assertNotContains(despues, codigo)
        finally:
            builtins.open = self._open_real
