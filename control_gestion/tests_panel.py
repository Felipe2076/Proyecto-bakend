"""El panel personal no mezcla datos entre usuarios y aplica HU-16."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from control_gestion.models import ItemFuncionario, Medicion, Meta
from control_gestion.panel_personal import color_avance_diario, color_ticket, construir_panel_personal
from cuentas.models import Cargo, Delegacion, EstadoRegistro, Funcionario, Rol, Usuario
from requerimientos.models import AreaSoporte, CanalIngreso, Requerimiento, TipoGestion, Vecino


class UmbralAvanceDiarioTests(TestCase):
    def test_hu16_59_rojo_60_ambar_100_verde(self):
        self.assertEqual(color_avance_diario(59, 100)["nivel"], "Rojo")
        self.assertEqual(color_avance_diario(60, 100)["nivel"], "Ámbar")
        self.assertEqual(color_avance_diario(99.9, 100)["nivel"], "Ámbar")
        self.assertEqual(color_avance_diario(100, 100)["nivel"], "Verde")
        self.assertEqual(color_avance_diario(140, 100)["nivel"], "Verde")

    def test_semaforo_ticket_usa_umbrales(self):
        self.assertEqual(color_ticket(3, 3, 5)["nivel"], "Verde")
        self.assertEqual(color_ticket(4, 3, 5)["nivel"], "Ámbar")
        self.assertEqual(color_ticket(5, 3, 5)["nivel"], "Ámbar")
        self.assertEqual(color_ticket(6, 3, 5)["nivel"], "Rojo")


class AislamientoPanelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.rol = Rol.objects.create(codigo="funcionario", nombre="Funcionario")
        self.delegacion = Delegacion.objects.create(nombre="Delegación Rural")
        self.otra = Delegacion.objects.create(nombre="Delegación Centro")
        cargo = Cargo.objects.create(nombre="Gestor social")
        self.fun_a = Funcionario.objects.create(
            codigo="FUN-A", nombre="Ana Soto", cargo=cargo, delegacion=self.delegacion
        )
        self.fun_b = Funcionario.objects.create(
            codigo="FUN-B", nombre="Bruno Díaz", cargo=cargo, delegacion=self.otra
        )
        self.user_a = User.objects.create_user("ana", "ana@laserena.cl", "AnaClave1!")
        self.user_b = User.objects.create_user("bruno", "bruno@laserena.cl", "BrunoClave1!")
        self.perfil_a = Usuario.objects.create(
            codigo="USR-A", user=self.user_a, username="ana", nombre="Ana Soto",
            correo="ana@laserena.cl", rol=self.rol, delegacion=self.delegacion,
            funcionario=self.fun_a, estado=EstadoRegistro.ACTIVO,
        )
        self.perfil_b = Usuario.objects.create(
            codigo="USR-B", user=self.user_b, username="bruno", nombre="Bruno Díaz",
            correo="bruno@laserena.cl", rol=self.rol, delegacion=self.otra,
            funcionario=self.fun_b, estado=EstadoRegistro.ACTIVO,
        )
        meta_a = Meta.objects.create(nombre="Meta exclusiva de Ana")
        meta_b = Meta.objects.create(nombre="Meta exclusiva de Bruno")
        ItemFuncionario.objects.create(
            funcionario=self.fun_a, meta=meta_a, ponderador=100, meta_trimestre=10, avance_actual=8
        )
        ItemFuncionario.objects.create(
            funcionario=self.fun_b, meta=meta_b, ponderador=100, meta_trimestre=10, avance_actual=1
        )
        Medicion.objects.create(
            periodo="Trimestre prueba",
            delegacion_piloto=self.delegacion,
            fecha_inicio=date(2026, 4, 1),
            fecha_termino=date(2026, 6, 29),
            dias_totales=90,
            meta_cumplimiento_tubo=80,
        )
        canal = CanalIngreso.objects.create(nombre="ventanilla-test")
        tipo = TipoGestion.objects.create(nombre="Solicitud test")
        area = AreaSoporte.objects.create(codigo="AREA-T", nombre="Área test")
        vecino_a = Vecino.objects.create(nombre="Vecino de Ana", delegacion=self.delegacion)
        vecino_b = Vecino.objects.create(nombre="Vecino de Bruno", delegacion=self.otra)
        hoy = timezone.localdate()
        Requerimiento.objects.create(
            codigo="TK-ANA", vecino=vecino_a, delegacion=self.delegacion, canal_ingreso=canal,
            tipo_gestion=tipo, area=area, descripcion="Caso solo de Ana Soto en terreno.",
            fecha_ingreso=hoy - timedelta(days=2), funcionario=self.fun_a,
            estado=Requerimiento.Estado.PENDIENTE,
        )
        Requerimiento.objects.create(
            codigo="TK-BRUNO", vecino=vecino_b, delegacion=self.otra, canal_ingreso=canal,
            tipo_gestion=tipo, area=area, descripcion="Caso solo de Bruno Díaz en el centro.",
            fecha_ingreso=hoy - timedelta(days=8), funcionario=self.fun_b,
            estado=Requerimiento.Estado.PENDIENTE,
        )

    def test_servicio_no_mezcla_tickets_ni_metas(self):
        panel = construir_panel_personal(self.perfil_a, hoy=date(2026, 6, 2))
        codigos = [ticket["codigo"] for ticket in panel["tickets"]]
        metas = [fila["item"] for fila in panel["desempeno"]]
        self.assertEqual(codigos, ["TK-ANA"])
        self.assertEqual(panel["tickets"][0]["nivel"], "Verde")
        self.assertIn("Meta exclusiva de Ana", metas)
        self.assertNotIn("TK-BRUNO", codigos)
        self.assertNotIn("Meta exclusiva de Bruno", metas)
        self.assertFalse(panel["ver_delegacion"])
        self.assertFalse(panel["ver_global"])
        self.assertEqual(panel["cifras"]["total"], 1)

    def test_pantalla_de_ana_oculta_a_bruno(self):
        cliente = Client()
        ingreso = cliente.post("/login/", {"username": "ana", "password": "AnaClave1!"})
        self.assertEqual(ingreso.status_code, 302)
        respuesta = cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "TK-ANA")
        self.assertContains(respuesta, "Meta exclusiva de Ana")
        self.assertNotContains(respuesta, "TK-BRUNO")
        self.assertNotContains(respuesta, "Meta exclusiva de Bruno")
        self.assertNotContains(respuesta, "Caso solo de Bruno")
