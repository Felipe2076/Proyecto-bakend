"""Panel personal: cada usuario ve solo sus tickets, su semáforo y sus metas.

HU-16: el avance real se compara con el % esperado del periodo.
Rojo bajo el 60 % de lo esperado, ámbar desde 60 % y menos de 100 %, verde desde 100 %.
HU-40 / HU-48: el semáforo del ticket usa los días de ParametroSistema
(por defecto 1-3 verde, 4-5 ámbar, 6 o más rojo).
"""

from django.db.models import Count, Max, Q
from django.utils import timezone

from control_gestion.indicadores import _periodo, cumplimiento_item
from control_gestion.models import Actividad, ItemFuncionario
from cuentas.models import Funcionario, Usuario
from cuentas.servicios import nombres_delegaciones, obtener_parametros
from requerimientos.models import Requerimiento


def color_avance_diario(pct_logrado, pct_esperado):
    """HU-16. ``pct_logrado`` y ``pct_esperado`` van de 0 a 100."""
    logrado = float(pct_logrado or 0)
    esperado = float(pct_esperado or 0)
    if esperado <= 0:
        ratio = 100.0
    else:
        ratio = round(logrado * 100 / esperado, 1)
    if ratio < 60:
        return {
            "ratio": ratio,
            "nivel": "Rojo",
            "clase": "bg-danger",
            "texto": "Bajo el 60 % de lo esperado",
        }
    if ratio < 100:
        return {
            "ratio": ratio,
            "nivel": "Ámbar",
            "clase": "bg-warning text-dark",
            "texto": "Entre el 60 % y menos del 100 % de lo esperado",
        }
    return {
        "ratio": ratio,
        "nivel": "Verde",
        "clase": "bg-success",
        "texto": "En el 100 % o más de lo esperado",
    }


def color_ticket(dias, sla_verde=3, sla_amarillo=5):
    """HU-40. Los umbrales salen de ParametroSistema (HU-48)."""
    try:
        dias = int(dias)
    except (TypeError, ValueError):
        dias = 0
    verde = int(sla_verde if sla_verde is not None else 3)
    ambar = int(sla_amarillo if sla_amarillo is not None else 5)
    if dias <= verde:
        return {"nivel": "Verde", "clase": "bg-success", "texto": f"Día {dias} · en plazo"}
    if dias <= ambar:
        return {"nivel": "Ámbar", "clase": "bg-warning text-dark", "texto": f"Día {dias} · alerta"}
    return {"nivel": "Rojo", "clase": "bg-danger", "texto": f"Día {dias} · crítico"}


def perfil_de_request(request):
    user = getattr(request, "user", None)
    qs = Usuario.objects.select_related("rol", "funcionario", "funcionario__delegacion", "delegacion", "cargo")
    if user is not None and getattr(user, "is_authenticated", False):
        perfil = qs.filter(user=user).first()
        if perfil is not None:
            return perfil
    username = (request.session.get("usuario") or {}).get("username")
    if username:
        return qs.filter(username=username).first()
    return None


def _sla():
    params = obtener_parametros()
    return int(params["sla_verde_max_dias"]), int(params["sla_amarillo_max_dias"])


def _tickets_de(funcionario):
    if funcionario is None:
        return Requerimiento.objects.none()
    return Requerimiento.objects.select_related(
        "vecino", "delegacion", "tipo_gestion", "funcionario"
    ).filter(funcionario=funcionario)


def _fila_ticket(req, sla_verde, sla_amarillo):
    color = color_ticket(req.dias_transcurridos, sla_verde, sla_amarillo)
    return {
        "codigo": req.codigo,
        "vecino": req.vecino.nombre,
        "delegacion": req.delegacion.nombre,
        "tipo": req.tipo_gestion.nombre,
        "estado": req.estado,
        "dias": req.dias_transcurridos,
        "descripcion": req.descripcion,
        **color,
    }


def _cifras(qs):
    total = qs.count()
    resueltos = qs.filter(estado=Requerimiento.Estado.RESUELTO).count()
    pendientes = total - resueltos
    tasa = round(resueltos * 100 / total, 1) if total else 0.0
    return {
        "total": total,
        "resueltos": resueltos,
        "pendientes": pendientes,
        "tasa": tasa,
    }


def _items_por_funcionario(funcionario_ids):
    grupos = {pk: [] for pk in funcionario_ids}
    if not funcionario_ids:
        return grupos
    items = (
        ItemFuncionario.objects.select_related("meta")
        .filter(funcionario_id__in=funcionario_ids)
        .order_by("-ponderador", "meta__nombre")
    )
    for item in items:
        pct, ponderado = cumplimiento_item(item.ponderador, item.meta_trimestre, item.avance_actual)
        grupos.setdefault(item.funcionario_id, []).append(
            {
                "item": item.meta.nombre,
                "ponderador": item.ponderador,
                "meta_trimestre": item.meta_trimestre,
                "avance_actual": item.avance_actual,
                "porcentaje_avance": pct,
                "cumplimiento_ponderado": ponderado,
            }
        )
    return grupos


def _logrado(filas):
    return round(sum(fila["cumplimiento_ponderado"] for fila in filas), 2)


def _asistencia(funcionario, hoy):
    if funcionario is None:
        return {"ultima": None, "hoy": 0}
    datos = Actividad.objects.filter(funcionario=funcionario).aggregate(
        ultima=Max("fecha_actividad"),
        hoy=Count("pk", filter=Q(fecha_actividad=hoy)),
    )
    return {"ultima": datos["ultima"], "hoy": int(datos["hoy"] or 0)}


def _semaforo_persona(funcionario, items, periodo, hoy):
    logrado = _logrado(items)
    color = color_avance_diario(logrado, periodo["pct_esperado"])
    asistencia = _asistencia(funcionario, hoy)
    return {
        "pct_logrado": logrado,
        "pct_esperado": periodo["pct_esperado"],
        "dias_avance": periodo["dias_avance"],
        "dias_totales": periodo["dias_totales"],
        "periodo": periodo["periodo"],
        "asistencia_hoy": asistencia["hoy"],
        "ultima_actividad": asistencia["ultima"],
        **color,
    }


def construir_panel_personal(perfil, hoy=None):
    """Arma el panel de un Usuario (o vacío si no hay perfil)."""
    hoy = hoy or timezone.localdate()
    periodo = _periodo(hoy)
    sla_verde, sla_amarillo = _sla()
    rol = perfil.rol.codigo if perfil is not None and perfil.rol_id else ""
    funcionario = perfil.funcionario if perfil is not None else None
    delegacion = None
    nombre = ""
    if perfil is not None:
        delegacion = (funcionario.delegacion if funcionario and funcionario.delegacion_id else None) or perfil.delegacion
        nombre = funcionario.nombre_mostrado if funcionario is not None else perfil.nombre_mostrado

    propios = _tickets_de(funcionario)
    filas_tickets = [_fila_ticket(req, sla_verde, sla_amarillo) for req in propios]
    ids = [funcionario.pk] if funcionario is not None else []
    items = _items_por_funcionario(ids).get(funcionario.pk, []) if funcionario is not None else []

    ver_delegacion = rol == "jefatura" and delegacion is not None
    ver_global = rol == "administrador"
    if rol == "funcionario" or rol == "ventanilla":
        delegaciones = [delegacion.nombre] if delegacion is not None else []
    elif ver_delegacion:
        delegaciones = [delegacion.nombre]
    else:
        delegaciones = nombres_delegaciones()

    return {
        "nombre": nombre,
        "delegacion_nombre": delegacion.nombre if delegacion is not None else "",
        "rol": rol,
        "tiene_funcionario": funcionario is not None,
        "sla_verde": sla_verde,
        "sla_amarillo": sla_amarillo,
        "cifras": _cifras(propios),
        "tickets": filas_tickets,
        "semaforo": _semaforo_persona(funcionario, items, periodo, hoy),
        "desempeno": items,
        "delegaciones": delegaciones,
        "ver_delegacion": ver_delegacion,
        "ver_global": ver_global,
        "delegacion": _resumen_delegacion(delegacion, periodo, hoy) if ver_delegacion else None,
        "global": _resumen_global() if ver_global else None,
    }


def _resumen_delegacion(delegacion, periodo, hoy):
    funcionarios = list(
        Funcionario.objects.filter(delegacion=delegacion).select_related("cargo").order_by("nombre")
    )
    grupos = _items_por_funcionario([fun.pk for fun in funcionarios])
    equipo = []
    for fun in funcionarios:
        logrado = _logrado(grupos.get(fun.pk, []))
        color = color_avance_diario(logrado, periodo["pct_esperado"])
        equipo.append(
            {
                "nombre": fun.nombre,
                "cargo": fun.cargo.nombre if fun.cargo_id else "",
                "pct_logrado": logrado,
                "nivel": color["nivel"],
                "clase": color["clase"],
            }
        )
    tickets = Requerimiento.objects.filter(delegacion=delegacion)
    return {
        "nombre": delegacion.nombre,
        "cifras": _cifras(tickets),
        "equipo": equipo,
    }


def _resumen_global():
    return {"cifras": _cifras(Requerimiento.objects.all())}
