"""Pruebas del mantenedor de roles: listado, búsqueda, alta, edición y baja."""

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
