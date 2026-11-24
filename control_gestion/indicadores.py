"""Cálculos del panel SGR (presentación Matriz SGR, diapositivas 12 a 18).

Semáforo diario: el trimestre vale 100% en ``dias_totales``. El % esperado al
día es ``dias_avance / dias_totales``. Verde si el % logrado (suma de
cumplimientos ponderados) está en esa línea o sobre ella. Bajo la línea, el
atraso se mide en días equivalentes del periodo. El tope amarillo es el mayor
entre ``sla_verde_max_dias`` y ``sla_amarillo_max_dias`` de
``ParametroSistema``; un atraso mayor es rojo.
"""

from django.db.models import Count, Max, Q
from django.utils import timezone

from control_gestion.models import Actividad, Compromiso, ItemFuncionario
from cuentas.models import Delegacion, Funcionario
from cuentas.servicios import obtener_parametros

META_TUBO_DEFECTO = 80


def porcentaje_esperado(fecha_inicio, fecha_termino, dias_totales, hoy):
    dias_totales = int(dias_totales or 0)
    if hoy < fecha_inicio:
        dias_avance = 0
    elif hoy > fecha_termino:
        dias_avance = dias_totales
    else:
        dias_avance = (hoy - fecha_inicio).days
    pct = round((dias_avance / dias_totales) * 100, 1) if dias_totales else 0.0
    return {"dias_avance": dias_avance, "dias_totales": dias_totales, "pct_esperado": pct}


def cumplimiento_item(ponderador, meta_trimestre, avance_actual):
    """% de cumplimiento y cumplimiento ponderado de un ítem (diapositiva 12)."""
    meta = float(meta_trimestre or 0)
    avance = float(avance_actual or 0)
    peso = float(ponderador or 0)
    pct = round((avance / meta) * 100, 1) if meta else 0.0
    if pct > 120:
        pct = 120.0
    ponderado = round((peso * pct) / 100.0, 2)
    return pct, ponderado


def limite_amarillo(sla_verde, sla_amarillo):
    """Tope de la franja amarilla: el mayor umbral de días configurado."""
    return max(int(sla_verde or 0), int(sla_amarillo or 0))


def color_semaforo_diario(pct_logrado, pct_esperado, dias_totales, sla_verde, sla_amarillo):
    dias_totales = int(dias_totales or 0)
    if dias_totales:
        brecha_dias = (float(pct_esperado) - float(pct_logrado)) * dias_totales / 100.0
    else:
        brecha_dias = 0.0
    tope = limite_amarillo(sla_verde, sla_amarillo)
    if brecha_dias <= 0:
        return {
            "nivel": "Verde",
            "clase": "bg-success",
            "texto": "En línea con la meta diaria",
            "brecha_dias": round(brecha_dias, 1),
        }
    if brecha_dias <= tope:
        return {
            "nivel": "Amarillo",
            "clase": "bg-warning text-dark",
            "texto": "Bajo la línea esperada",
            "brecha_dias": round(brecha_dias, 1),
        }
    return {
        "nivel": "Rojo",
        "clase": "bg-danger",
        "texto": "Rezagado / requiere acompañamiento",
        "brecha_dias": round(brecha_dias, 1),
    }


def _periodo(hoy):
    from control_gestion.trimestres import trimestre_actual
    periodo = trimestre_actual(hoy)
    params = obtener_parametros()
    avance = porcentaje_esperado(periodo['fecha_inicio'], periodo['fecha_termino'], periodo['dias_totales'], hoy)
    return {
        **periodo,
        'fecha_hoy': hoy,
        'delegacion_piloto': periodo.get('delegacion_piloto', 'Delegación Rural'),
        'meta_cumplimiento_tubo': int(periodo.get('meta_cumplimiento_tubo') or params['meta_tubo_porcentaje'] or META_TUBO_DEFECTO),
        'sla_verde_max_dias': int(params['sla_verde_max_dias']),
        'sla_amarillo_max_dias': int(params['sla_amarillo_max_dias']),
        **avance,
    }


def _fila_tubo(conteo, meta):
    total = int(conteo.get("total") or 0)
    realizados = int(conteo.get("realizado") or 0)
    pct = round(realizados * 100 / total, 1) if total else 0.0
    return {
        "ingresado": int(conteo.get("ingresado") or 0),
        "pendiente": int(conteo.get("pendiente") or 0),
        "en_proceso": int(conteo.get("en_proceso") or 0),
        "realizado": realizados,
        "total": total,
        "pct_realizado": pct,
        "pct_pendiente": round(100 - pct, 1) if total else 0.0,
        "cumple_meta": bool(total) and pct >= meta,
    }


def _conteo_estados():
    estado = Compromiso.Estado
    return dict(
        total=Count("pk"),
        ingresado=Count("pk", filter=Q(estado=estado.INGRESADO)),
        pendiente=Count("pk", filter=Q(estado=estado.PENDIENTE)),
        en_proceso=Count("pk", filter=Q(estado=estado.EN_PROCESO)),
        realizado=Count("pk", filter=Q(estado=estado.REALIZADO)),
    )


def _tubo_agrupado(campo_id, campo_nombre, meta, compromisos=None):
    compromisos = Compromiso.objects.all() if compromisos is None else compromisos
    filas = (
        compromisos.values(campo_id, campo_nombre)
        .annotate(**_conteo_estados())
        .order_by(campo_nombre)
    )
    resultado = []
    for fila in filas:
        item = _fila_tubo(fila, meta)
        item["nombre"] = fila[campo_nombre]
        resultado.append(item)
    return resultado


def delegacion_visible(perfil):
    """None = todas (superusuario o sin perfil en pruebas); id = solo esa delegación."""
    if perfil is None or getattr(getattr(perfil, "rol", None), "codigo", "") == "superusuario":
        return None
    return perfil.delegacion_id or 0


def construir_panel(hoy=None, perfil=None):
    """Arma semáforo, tubo, metas y promedios de delegación desde el ORM.

    Con ``perfil`` de una delegación, todo queda acotado a ella.
    """
    hoy = hoy or timezone.localdate()
    solo = delegacion_visible(perfil)
    periodo = _periodo(hoy)
    meta = periodo["meta_cumplimiento_tubo"]
    sla_verde = periodo["sla_verde_max_dias"]
    sla_amarillo = periodo["sla_amarillo_max_dias"]

    por_funcionario = {}
    items = (
        ItemFuncionario.objects.select_related(
            "funcionario", "funcionario__cargo", "funcionario__delegacion", "meta"
        ).order_by("funcionario__nombre", "-ponderador", "meta__nombre")
    )
    funcionarios = Funcionario.objects.select_related("cargo", "delegacion").order_by("nombre")
    compromisos = Compromiso.objects.all()
    actividades_base = Actividad.objects.all()
    delegaciones_qs = Delegacion.objects.order_by("nombre")
    from django.conf import settings
    if getattr(settings, "SIGED_OCULTAR_SIMULACION", False):
        items = items.exclude(funcionario__es_simulacion=True)
        funcionarios = funcionarios.exclude(es_simulacion=True)
    if solo is not None:
        items = items.filter(funcionario__delegacion_id=solo)
        funcionarios = funcionarios.filter(delegacion_id=solo)
        compromisos = compromisos.filter(delegacion_id=solo)
        actividades_base = actividades_base.filter(delegacion_id=solo)
        delegaciones_qs = delegaciones_qs.filter(pk=solo)
    filas_items = []
    for item in items:
        pct, ponderado = cumplimiento_item(item.ponderador, item.meta_trimestre, item.avance_actual)
        fun = item.funcionario
        grupo = por_funcionario.setdefault(
            fun.pk,
            {
                "nombre": fun.nombre,
                "cargo": fun.cargo.nombre if fun.cargo_id else "",
                "delegacion": fun.delegacion.nombre if fun.delegacion_id else "",
                "pct_logrado": 0.0,
            },
        )
        grupo["pct_logrado"] = round(grupo["pct_logrado"] + ponderado, 2)
        filas_items.append(
            {
                "funcionario": fun.nombre,
                "cargo": grupo["cargo"],
                "delegacion": grupo["delegacion"],
                "item": item.meta.nombre,
                "ponderador": item.ponderador,
                "meta_trimestre": item.meta_trimestre,
                "avance_actual": item.avance_actual,
                "porcentaje_avance": pct,
                "cumplimiento_ponderado": ponderado,
            }
        )

    for fun in funcionarios:
        por_funcionario.setdefault(
            fun.pk,
            {
                "nombre": fun.nombre,
                "cargo": fun.cargo.nombre if fun.cargo_id else "",
                "delegacion": fun.delegacion.nombre if fun.delegacion_id else "",
                "pct_logrado": 0.0,
            },
        )

    semaforo = []
    for funcionario_id, grupo in por_funcionario.items():
        from control_gestion.evidencias import bonificacion
        grupo['pct_logrado'] = min(150, grupo['pct_logrado'] + bonificacion(funcionario_id,periodo))
        from control_gestion.ausencias import ajustar_periodo
        periodo_personal = ajustar_periodo(funcionario_id, periodo)
        color = color_semaforo_diario(
            grupo["pct_logrado"],
            periodo_personal["pct_esperado"],
            periodo_personal["dias_totales"],
            sla_verde,
            sla_amarillo,
        )
        semaforo.append({**grupo, "pct_esperado": periodo_personal["pct_esperado"], "dias_ausencia": periodo_personal.get("dias_ausencia",0), **color})
    semaforo.sort(key=lambda fila: (fila["delegacion"], fila["nombre"]))

    actividades_qs = actividades_base.values("delegacion_id", "delegacion__nombre").annotate(
        ultimo=Max("fecha_actividad"),
        cantidad=Count("pk"),
    )
    actividades = {
        fila["delegacion_id"]: fila for fila in actividades_qs
    }
    delegaciones = []
    dias_avance = periodo["dias_avance"]
    for delegacion in delegaciones_qs:
        fila = actividades.get(delegacion.pk)
        cantidad = int(fila["cantidad"]) if fila else 0
        ultimo = fila["ultimo"] if fila else None
        delegaciones.append(
            {
                "nombre": delegacion.nombre,
                "ultimo_ingreso": ultimo,
                "dias_desde_ultimo": (hoy - ultimo).days if ultimo else None,
                "cantidad": cantidad,
                "promedio_diario": round(cantidad / dias_avance, 2) if dias_avance else 0.0,
            }
        )

    return {
        "periodo": periodo,
        "tope_amarillo": limite_amarillo(sla_verde, sla_amarillo),
        "semaforo": semaforo,
        "tubo_funcionarios": _tubo_agrupado("funcionario_id", "funcionario__nombre", meta, compromisos),
        "tubo_delegaciones": _tubo_agrupado("delegacion_id", "delegacion__nombre", meta, compromisos),
        "tubo_total": _fila_tubo(compromisos.aggregate(**_conteo_estados()), meta),
        "items": filas_items,
        "delegaciones": delegaciones,
    }
