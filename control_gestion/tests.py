"""Cálculos del semáforo diario y del panel SGR."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from control_gestion.indicadores import (
    color_semaforo_diario,
    construir_panel,
    porcentaje_esperado,
)
from control_gestion.models import Actividad, Compromiso, ItemFuncionario, Medicion, Meta
from cuentas.models import Cargo, Delegacion, EstadoRegistro, Funcionario, ParametroSistema, Rol, Usuario
from requerimientos.models import Vecino


class SemaforoDiarioTests(TestCase):
    def test_porcentaje_esperado_del_trimestre(self):
        # 1 de abril a 2 de junio son 62 días; 62/90 = 68,9%.
        avance = porcentaje_esperado(date(2026, 4, 1), date(2026, 6, 29), 90, date(2026, 6, 2))
        self.assertEqual(avance["dias_avance"], 62)
        self.assertEqual(avance["pct_esperado"], 68.9)

    def test_color_segun_linea_y_parametros(self):
        # En la línea o sobre ella: verde, aunque el umbral de días sea chico.
        self.assertEqual(color_semaforo_diario(50, 50, 90, 3, 5)["nivel"], "Verde")
        self.assertEqual(color_semaforo_diario(60, 50, 90, 3, 5)["nivel"], "Verde")

        cuatro_dias = 50 - (4 * 100 / 90)
        seis_dias = 50 - (6 * 100 / 90)
        # 4 días de atraso cabe en el mayor umbral (5) → amarillo.
        self.assertEqual(color_semaforo_diario(cuatro_dias, 50, 90, 3, 5)["nivel"], "Amarillo")
        # 6 días supera sla verde (3) y sla amarillo (5) → rojo.
        self.assertEqual(color_semaforo_diario(seis_dias, 50, 90, 3, 5)["nivel"], "Rojo")
        # Si el umbral verde queda sobre el amarillo, ese tope también pinta amarillo.
        self.assertEqual(color_semaforo_diario(seis_dias, 50, 90, 8, 5)["nivel"], "Amarillo")


class PanelOrmTests(TestCase):
    def setUp(self):
        ParametroSistema.objects.create(sla_verde_max_dias=3, sla_amarillo_max_dias=5, meta_tubo_porcentaje=80)
        self.delegacion = Delegacion.objects.create(nombre="Delegación Rural", direccion="Camino 1")
        self.cargo = Cargo.objects.create(nombre="Gestor social")
        self.ana = Funcionario.objects.create(
            codigo="FUN-001", nombre="Ana Soto", cargo=self.cargo, delegacion=self.delegacion
        )
        self.meta = Meta.objects.create(nombre="Cobertura territorial")
        ItemFuncionario.objects.create(
            funcionario=self.ana, meta=self.meta, ponderador=100, meta_trimestre=10, avance_actual=8
        )
        Medicion.objects.create(
            periodo="Trimestre 2",
            delegacion_piloto=self.delegacion,
            fecha_inicio=date(2026, 4, 1),
            fecha_termino=date(2026, 6, 29),
            dias_totales=90,
            meta_cumplimiento_tubo=80,
        )
        vecino = Vecino.objects.create(nombre="Pedro Rojas", delegacion=self.delegacion)
        for indice, estado in enumerate(("REALIZADO", "REALIZADO", "REALIZADO", "REALIZADO", "PENDIENTE"), start=1):
            Compromiso.objects.create(
                codigo=f"TUB-{indice:03d}",
                descripcion=f"Compromiso {indice}",
                vecino=vecino,
                funcionario=self.ana,
                delegacion=self.delegacion,
                fecha_compromiso=date(2026, 6, 10),
                estado=estado,
            )
        for indice, fecha in enumerate((date(2026, 6, 1), date(2026, 6, 2), date(2026, 5, 20)), start=1):
            Actividad.objects.create(
                codigo=f"ACT-{indice:03d}",
                funcionario=self.ana,
                delegacion=self.delegacion,
                meta=self.meta,
                fecha_actividad=fecha,
                servicio="Visita territorial",
            )

    def test_panel_calcula_tubo_metas_y_promedio(self):
        panel = construir_panel(hoy=date(2026, 6, 2))
        self.assertEqual(panel["periodo"]["pct_esperado"], 68.9)
        ana = panel["semaforo"][0]
        self.assertEqual(ana["nombre"], "Ana Soto")
        self.assertEqual(ana["pct_logrado"], 80.0)
        self.assertEqual(ana["nivel"], "Verde")

        tubo = panel["tubo_funcionarios"][0]
        self.assertEqual(tubo["realizado"], 4)
        self.assertEqual(tubo["pendiente"], 1)
        self.assertEqual(tubo["pct_realizado"], 80.0)
        self.assertTrue(tubo["cumple_meta"])
        self.assertEqual(panel["tubo_delegaciones"][0]["pct_realizado"], 80.0)

        item = panel["items"][0]
        self.assertEqual(item["porcentaje_avance"], 80.0)
        self.assertEqual(item["cumplimiento_ponderado"], 80.0)

        delegacion = panel["delegaciones"][0]
        self.assertEqual(delegacion["ultimo_ingreso"], date(2026, 6, 2))
        self.assertEqual(delegacion["dias_desde_ultimo"], 0)
        self.assertEqual(delegacion["cantidad"], 3)
        self.assertEqual(delegacion["promedio_diario"], round(3 / 62, 2))

    def test_dashboard_muestra_las_tarjetas(self):
        User = get_user_model()
        rol = Rol.objects.create(codigo="administrador", nombre="Administrador")
        user = User.objects.create_user("admin", "admin.siged@laserena.cl", "Admin123!")
        Usuario.objects.create(
            codigo="USR-001",
            user=user,
            username="admin",
            nombre="Administrador SIGED",
            correo="admin.siged@laserena.cl",
            rol=rol,
            estado=EstadoRegistro.ACTIVO,
        )
        cliente = Client()
        cliente.post("/login/", {"username": "admin", "password": "Admin123!"})
        respuesta = cliente.get("/control/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "card-calculo")
        self.assertContains(respuesta, "Semáforo diario")
        self.assertContains(respuesta, "Tubo de trabajo")
        self.assertContains(respuesta, "Metas por funcionario")
        self.assertContains(respuesta, "Promedio diario")
        self.assertContains(respuesta, "Ana Soto")
