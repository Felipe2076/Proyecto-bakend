"""Pruebas de mantenedores y de autenticación contra la base de datos."""

import builtins
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from cuentas.models import EstadoRegistro, Rol, Usuario


class RolesMantenedorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.rol_admin = Rol.objects.create(
            codigo="administrador", nombre="Administrador", descripcion="Acceso total"
        )
        self.user = User.objects.create_user("admin", "admin.siged@laserena.cl", "Admin123!")
        Usuario.objects.create(
            codigo="USR-001",
            user=self.user,
            username="admin",
            nombre="Administrador SIGED",
            correo="admin.siged@laserena.cl",
            rol=self.rol_admin,
            estado=EstadoRegistro.ACTIVO,
        )
        self.client = Client()
        self.client.post("/login/", {"username": "admin", "password": "Admin123!"})

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
        User = get_user_model()
        rol = Rol.objects.create(codigo="ventanilla", nombre="Ventanilla", descripcion="Ingreso")
        user = User.objects.create_user("ventanilla", "ventanilla@laserena.cl", "Ventanilla1!")
        Usuario.objects.create(
            codigo="USR-004",
            user=user,
            username="ventanilla",
            nombre="Marisol Tapia",
            correo="ventanilla@laserena.cl",
            rol=rol,
            estado=EstadoRegistro.ACTIVO,
        )
        self.client.logout()
        self.client.post("/login/", {"username": "ventanilla", "password": "Ventanilla1!"})
        respuesta = self.client.get("/mantenedores/roles/", follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no tiene acceso")


PERFILES_DEMO = (
    ("admin", "admin123", "administrador", "admin.siged@laserena.cl", "/mantenedores/roles/", True),
    ("jefatura", "jefatura123", "jefatura", "elizabeth.rojas@laserena.cl", "/mantenedores/roles/", False),
    ("funcionario", "funcionario123", "funcionario", "camila.oyarzun@laserena.cl", "/administracion/usuarios/", False),
    ("ventanilla", "ventanilla123", "ventanilla", "marisol.tapia@laserena.cl", "/control/actividades/", False),
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
        User = get_user_model()
        self.users = {}
        for username, password, rol_codigo, correo, _ruta, _permitido in PERFILES_DEMO:
            rol = Rol.objects.create(codigo=rol_codigo, nombre=rol_codigo.capitalize(), descripcion=rol_codigo)
            user = User.objects.create_user(username, correo, password)
            Usuario.objects.create(
                codigo=f"USR-{username[:3].upper()}",
                user=user,
                username=username,
                nombre=f"Perfil {username}",
                correo=correo,
                rol=rol,
                estado=EstadoRegistro.ACTIVO,
            )
            self.users[username] = user

    def _abrir(self, path, *args, **kwargs):
        if "usuarios.json" in str(path):
            raise AssertionError(f"el flujo abrió {path}")
        return self._open_real(path, *args, **kwargs)

    def test_login_usa_la_base_y_no_el_json(self):
        self._open_real = builtins.open
        builtins.open = self._abrir
        try:
            for username, password, rol_codigo, _correo, ruta, permitido in PERFILES_DEMO:
                cliente = Client()
                respuesta = cliente.post("/login/", {"username": username, "password": password})
                self.assertEqual(respuesta.status_code, 302, username)
                self.assertNotIn("/login/", respuesta["Location"])
                sesion = cliente.session["usuario"]
                self.assertEqual(sesion["rol"], rol_codigo)
                self.assertEqual(sesion["username"], username)
                self.assertEqual(int(cliente.session["_auth_user_id"]), self.users[username].pk)
                pantalla = cliente.get(ruta, follow=True)
                self.assertEqual(pantalla.status_code, 200)
                if permitido:
                    self.assertNotContains(pantalla, "no tiene acceso")
                else:
                    self.assertContains(pantalla, "no tiene acceso")
                ajeno = Client()
                clave_mala = ajeno.post("/login/", {"username": username, "password": "no-es-la-clave"})
                self.assertContains(clave_mala, "incorrectos")
        finally:
            builtins.open = self._open_real

    def test_recuperacion_guarda_la_clave_en_user(self):
        self._open_real = builtins.open
        builtins.open = self._abrir
        cliente = Client()
        try:
            pedido = cliente.post("/recuperar/", {"correo": "admin.siged@laserena.cl"}, follow=True)
            self.assertEqual(pedido.status_code, 200)
            codigo = re.search(r"(\d{6})", pedido.content.decode()).group(1)
            digitos = {f"d{i}": digito for i, digito in enumerate(codigo, start=1)}
            validado = cliente.post("/recuperar/codigo/", digitos)
            self.assertEqual(validado.status_code, 302)
            nueva = "NuevaClave1!"
            guardada = cliente.post(
                "/recuperar/nueva/",
                {"password": nueva, "confirmacion": nueva},
                follow=True,
            )
            self.assertEqual(guardada.status_code, 200)
            self.assertContains(guardada, "actualizada")
        finally:
            builtins.open = self._open_real
        user = self.users["admin"]
        user.refresh_from_db()
        self.assertTrue(user.check_password(nueva))
        self.assertFalse(user.check_password("admin123"))
        ingreso = Client()
        respuesta = ingreso.post("/login/", {"username": "admin", "password": nueva})
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotIn("/login/", respuesta["Location"])
