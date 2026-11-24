from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from control_gestion.consultas import (
    actividad_a_dict,
    compromiso_a_dict,
    funcionario_base,
    queryset_actividades,
    queryset_compromisos,
    queryset_funcionarios,
    registrar_actividad_desde_formulario,
)
from control_gestion.indicadores import color_semaforo_diario, cumplimiento_item, construir_panel
from cuentas.ambito import delegacion_por_defecto, denegar_otra_delegacion, limitar_a_delegacion
from cuentas.auth import puede_ver, requerir_modulo, usuario_sesion
from cuentas.servicios import nombres_delegaciones, obtener_parametros
from requerimientos.consultas import queryset_requerimientos, ticket_a_dict
from requerimientos.models import AreaSoporte

ESTADOS_TUBO = ["INGRESADO", "PENDIENTE", "EN PROCESO", "REALIZADO"]
META_TUBO_PORCENTAJE = 80


def parsear_fecha(valor):
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def cargar_periodo_medicion():
    from control_gestion.indicadores import _periodo
    periodo = _periodo(timezone.localdate())
    for campo in ('fecha_inicio', 'fecha_termino', 'fecha_hoy'):
        periodo[campo] = periodo[campo].isoformat()
    return periodo


def calcular_item_medicion(item):
    meta = float(item.get("meta_trimestre") or 0)
    avance = float(item.get("avance_actual") or 0)
    ponderador = float(item.get("ponderador") or 0)
    pct, ponderado = cumplimiento_item(ponderador, meta, avance)
    resultado = dict(item)
    resultado["meta_trimestre"] = meta
    resultado["avance_actual"] = avance
    resultado["ponderador"] = ponderador
    resultado["pct_cumplimiento"] = pct
    resultado["cumplimiento_ponderado"] = ponderado
    return resultado


def asignar_semaforo_sgr(pct_logrado, pct_esperado, dias_totales=None):
    params = obtener_parametros()
    return color_semaforo_diario(
        pct_logrado,
        pct_esperado,
        dias_totales or 90,
        params["sla_verde_max_dias"],
        params["sla_amarillo_max_dias"],
    )


def resumen_tubo_por_funcionario(compromisos):
    resumen = {}
    for item in compromisos:
        clave = item.get("id_funcionario") or item.get("funcionario")
        if clave not in resumen:
            resumen[clave] = {"total": 0, "realizados": 0, "pendientes": 0}
        resumen[clave]["total"] += 1
        estado = (item.get("estado") or "").upper()
        if estado == "REALIZADO":
            resumen[clave]["realizados"] += 1
        else:
            resumen[clave]["pendientes"] += 1
    return resumen


def enriquecer_funcionario(funcionario, periodo, resumen_tubo):
    items = [calcular_item_medicion(item) for item in funcionario.get("items", [])]
    ponderado_total = round(sum(item["cumplimiento_ponderado"] for item in items), 2)
    # Las vistas de desempeño comparten los ajustes del panel personal.
    from control_gestion.ausencias import ajustar_periodo
    from control_gestion.evidencias import bonificacion
    periodo_personal = dict(periodo)
    for campo in ('fecha_inicio', 'fecha_termino', 'fecha_hoy'):
        periodo_personal[campo] = parsear_fecha(periodo_personal.get(campo))
    funcionario_pk = funcionario.get('pk_funcionario')
    if funcionario_pk and all(periodo_personal.get(c) for c in ('fecha_inicio','fecha_termino','fecha_hoy')):
        periodo_personal = ajustar_periodo(funcionario_pk, periodo_personal)
        ponderado_total = min(150, ponderado_total + bonificacion(funcionario_pk, periodo_personal))
    semaforo = asignar_semaforo_sgr(
        ponderado_total, periodo_personal["pct_esperado"], periodo_personal.get("dias_totales")
    )
    clave = funcionario.get("id_funcionario")
    tubo = resumen_tubo.get(clave, {"total": 0, "realizados": 0, "pendientes": 0})
    pct_tubo = round((tubo["realizados"] / tubo["total"]) * 100, 1) if tubo["total"] else 0.0
    cumple_tubo = pct_tubo >= periodo["meta_cumplimiento_tubo"] if tubo["total"] else False
    ultimo = parsear_fecha(funcionario.get("fecha_ultimo_ingreso"))
    dias_sin_ingreso = (timezone.localdate() - ultimo).days if ultimo else None
    copia = dict(funcionario)
    copia["items"] = items
    copia["ponderado_total"] = ponderado_total
    copia["pct_esperado"] = periodo_personal["pct_esperado"]
    copia["dias_ausencia"] = periodo_personal.get("dias_ausencia", 0)
    copia["semaforo_nivel"] = semaforo["nivel"]
    copia["semaforo_clase"] = semaforo["clase"]
    copia["semaforo_texto"] = semaforo["texto"]
    copia["tubo_total"] = tubo["total"]
    copia["tubo_realizados"] = tubo["realizados"]
    copia["tubo_pendientes"] = tubo["pendientes"]
    copia["tubo_pct"] = pct_tubo
    copia["cumple_tubo"] = cumple_tubo
    copia["dias_sin_ingreso"] = dias_sin_ingreso
    return copia


def calcular_semaforo_ticket(item, params=None):
    params = params or obtener_parametros()
    sla_verde = params["sla_verde_max_dias"]
    sla_amarillo = params["sla_amarillo_max_dias"]
    dias = item.get("dias_transcurridos", 0)
    try:
        dias = int(dias)
    except (ValueError, TypeError):
        dias = 0
    if item.get("estado_proceso") == "Resuelto":
        nivel, clase, color_dot = "Resuelto", "bg-secondary", "Gris"
    elif dias <= sla_verde:
        nivel, clase, color_dot = "Verde", "bg-success", "Verde"
    elif dias <= sla_amarillo:
        nivel, clase, color_dot = "Amarillo", "bg-warning text-dark", "Amarillo"
    else:
        nivel, clase, color_dot = "Rojo", "bg-danger", "Rojo"
    item_copia = dict(item)
    item_copia["dias_transcurridos"] = dias
    item_copia["semaforo_nivel"] = nivel
    item_copia["semaforo_clase"] = clase
    item_copia["color_dot"] = color_dot
    return item_copia


def _tickets(qs=None):
    params = obtener_parametros()
    qs = queryset_requerimientos() if qs is None else qs
    return [calcular_semaforo_ticket(ticket_a_dict(req), params) for req in qs]


def _compromisos():
    return [compromiso_a_dict(item) for item in queryset_compromisos()]


def _funcionarios_enriquecidos(periodo, compromisos=None):
    if compromisos is None:
        compromisos = _compromisos()
    resumen = resumen_tubo_por_funcionario(compromisos)
    return [enriquecer_funcionario(funcionario_base(fun), periodo, resumen) for fun in queryset_funcionarios()]


def dashboard_cuellos_botella_view(request):
    from control_gestion.kanban import tickets_visibles
    from control_gestion.reportes import perfil_acceso

    perfil, error = perfil_acceso(request, "control_gestion")
    if error is not None:
        return error
    params = obtener_parametros()
    limite_critico = int(params["sla_amarillo_max_dias"])
    from requerimientos.consultas import para_indicadores
    qs = para_indicadores(tickets_visibles(perfil))
    requerimientos = _tickets(qs)
    abiertos = [item for item in requerimientos if item["estado_proceso"] != "Resuelto"]
    resueltos = [item for item in requerimientos if item["estado_proceso"] == "Resuelto" and item.get("fecha_resolucion")]
    total_requerimientos = len(requerimientos)
    cuellos_botella = sorted(
        (item for item in abiertos if item["dias_transcurridos"] > limite_critico),
        key=lambda item: -item["dias_transcurridos"],
    )
    total_criticos = len(cuellos_botella)
    porcentaje_criticos = round(total_criticos * 100 / len(abiertos), 1) if abiertos else 0.0

    def promedio(items):
        return round(sum(item["dias_transcurridos"] for item in items) / len(items), 1) if items else 0.0

    # Tiempo de resolución real: días entre ingreso y resolución de los tickets cerrados.
    tiempo_promedio = promedio(resueltos)
    antiguedad_abiertos = promedio(abiertos)
    stats_delegaciones = []
    conteo_por_delegacion = {}
    for delegacion in sorted({item["delegacion"] for item in requerimientos}):
        casos_del = [item for item in requerimientos if item["delegacion"] == delegacion]
        abiertos_del = [item for item in casos_del if item["estado_proceso"] != "Resuelto"]
        resueltos_del = [item for item in casos_del if item["estado_proceso"] == "Resuelto" and item.get("fecha_resolucion")]
        conteo_por_delegacion[delegacion] = len(casos_del)
        stats_delegaciones.append(
            {
                "nombre": delegacion,
                "total": len(casos_del),
                "abiertos": len(abiertos_del),
                "criticos": sum(1 for item in abiertos_del if item["dias_transcurridos"] > limite_critico),
                "tiempo_promedio": promedio(resueltos_del),
                "porcentaje_carga": round(len(casos_del) * 100 / total_requerimientos, 1) if total_requerimientos else 0.0,
            }
        )
    if conteo_por_delegacion:
        delegacion_mayor_demanda = max(conteo_por_delegacion, key=conteo_por_delegacion.get)
    else:
        delegacion_mayor_demanda = "Sin datos"
    contexto = {
        "total_requerimientos": total_requerimientos,
        "total_abiertos": len(abiertos),
        "total_resueltos": len(resueltos),
        "total_criticos": total_criticos,
        "porcentaje_criticos": porcentaje_criticos,
        "tiempo_promedio": tiempo_promedio,
        "antiguedad_abiertos": antiguedad_abiertos,
        "delegacion_mayor_demanda": delegacion_mayor_demanda,
        "cuellos_botella": cuellos_botella,
        "stats_delegaciones": stats_delegaciones,
        "sla_verde": int(params["sla_verde_max_dias"]),
        "sla_amarillo": limite_critico,
        "panel": construir_panel(perfil=perfil),
    }
    return render(request, "control_gestion/dashboard.html", contexto)


def kanban_view(request):
    from control_gestion.kanban import tablero
    return tablero(request)


def _indicadores_area(tickets, sla_amarillo, hoy):
    """KPIs reales de un área a partir de sus tickets (no de columnas escritas a mano)."""
    medibles = [t for t in tickets if not t.resuelto or t.fecha_resolucion]
    resueltos = [t for t in tickets if t.resuelto and t.fecha_resolucion]
    notas = [t.evaluacion_satisfaccion for t in tickets if t.evaluacion_satisfaccion]
    dentro = sum(1 for t in medibles if t.dias_transcurridos <= sla_amarillo)
    return {
        "total": len(tickets),
        "abiertos": sum(1 for t in tickets if not t.resuelto),
        "casos_30d": sum(1 for t in tickets if (hoy - t.fecha_ingreso).days <= 30),
        "porcentaje_cumplimiento": round(dentro * 100 / len(medibles)) if medibles else None,
        "tiempo_promedio_dias": round(sum(t.dias_transcurridos for t in resueltos) / len(resueltos), 1) if resueltos else None,
        "satisfaccion_promedio": round(sum(notas) / len(notas), 1) if notas else None,
        "encuestas": len(notas),
    }


def areas_soporte_view(request):
    from control_gestion.kanban import tickets_visibles
    from control_gestion.reportes import perfil_acceso

    perfil, error = perfil_acceso(request, "control_gestion")
    if error is not None:
        return error
    criterio_orden = request.GET.get("orden", "").strip().lower()
    params = obtener_parametros()
    sla_amarillo = int(params["sla_amarillo_max_dias"])
    meta = int(params.get("meta_tubo_porcentaje") or 80)
    hoy = timezone.localdate()
    por_area = {}
    from requerimientos.consultas import para_indicadores
    for ticket in para_indicadores(tickets_visibles(perfil)):
        por_area.setdefault(ticket.area_id, []).append(ticket)
    areas_procesadas = []
    for area in AreaSoporte.objects.select_related("encargado").order_by("codigo"):
        kpi = _indicadores_area(por_area.get(area.pk, []), sla_amarillo, hoy)
        pct = kpi["porcentaje_cumplimiento"]
        if pct is None:
            nivel, badge, borde, barra = "Sin datos suficientes", "text-bg-light border", "border-secondary", "bg-secondary"
        elif pct >= meta:
            nivel, badge, borde, barra = "Dentro de la meta", "bg-success", "border-success", "bg-success"
        elif pct >= meta - 20:
            nivel, badge, borde, barra = "En observación", "bg-warning text-dark", "border-warning", "bg-warning"
        else:
            nivel, badge, borde, barra = "Bajo la meta", "bg-danger", "border-danger", "bg-danger"
        encargado = area.encargado.nombre if area.encargado_id else area.encargado_nombre
        areas_procesadas.append({
            "id_area": area.codigo,
            "nombre_area": area.nombre,
            "encargado": encargado or "Sin encargado registrado",
            "descripcion": area.descripcion,
            **kpi,
            "nivel_rendimiento": nivel,
            "badge_clase": badge,
            "tarjeta_borde": borde,
            "color_barra": barra,
        })
    claves = {
        "satisfaccion": (lambda a: a["satisfaccion_promedio"] or 0, True),
        "cumplimiento": (lambda a: a["porcentaje_cumplimiento"] or 0, True),
        "tiempo": (lambda a: a["tiempo_promedio_dias"] if a["tiempo_promedio_dias"] is not None else 9999, False),
        "casos": (lambda a: a["casos_30d"], True),
    }
    if criterio_orden in claves:
        clave, inverso = claves[criterio_orden]
        areas_procesadas.sort(key=clave, reverse=inverso)
    contexto = {
        "areas": areas_procesadas,
        "criterio_orden": criterio_orden,
        "total_areas": len(areas_procesadas),
        "sla_amarillo": sla_amarillo,
        "meta_cumplimiento": meta,
    }
    return render(request, "control_gestion/areas.html", contexto)


def semaforo_sgr_view(request):
    bloqueo = requerir_modulo(request, "matriz_sgr")
    if bloqueo:
        return bloqueo
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    bloqueo_ambito = denegar_otra_delegacion(request, filtro_delegacion)
    if bloqueo_ambito:
        return bloqueo_ambito
    funcionarios = limitar_a_delegacion(request, _funcionarios_enriquecidos(periodo))
    if filtro_delegacion:
        funcionarios = [item for item in funcionarios if (item.get("delegacion") or "") == filtro_delegacion]
    contexto = {
        "periodo": periodo,
        "funcionarios": funcionarios,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "total_funcionarios": len(funcionarios),
        "total_verde": sum(1 for item in funcionarios if item["semaforo_nivel"] == "Verde"),
        "total_amarillo": sum(1 for item in funcionarios if item["semaforo_nivel"] == "Amarillo"),
        "total_rojo": sum(1 for item in funcionarios if item["semaforo_nivel"] == "Rojo"),
    }
    return render(request, "control_gestion/semaforo_sgr.html", contexto)


def _sin_pagina(get):
    """Filtros de la URL sin el número de página (al cambiar entre Tabla y Kanban se vuelve a la página 1)."""
    datos = get.copy()
    datos.pop("page", None)
    return datos.urlencode()


def tubo_trabajo_view(request, vista="tabla"):
    from control_gestion.reportes import perfil_acceso,tubo_filtrado
    perfil,error=perfil_acceso(request,'compromisos')
    if error is not None: return error
    desde_tubo = vista == 'tarjetas'
    ruta_vista = 'tubo_cartas' if desde_tubo else 'tubo_trabajo'
    filtros = request.GET.copy()
    vista_anterior = filtros.pop('vista', [])
    if request.method == 'POST':
        from control_gestion.movimientos import mover_compromiso
        return mover_compromiso(request, perfil, ruta_vista)
    if vista_anterior:
        destino = 'tubo_cartas' if desde_tubo or vista_anterior[-1] == 'tarjetas' else 'tubo_trabajo'
        url = reverse(destino)
        return redirect(url + ('?' + filtros.urlencode() if filtros else ''))
    filtros_ficha = filtros.copy()
    if desde_tubo:
        filtros_ficha['vista'] = 'tarjetas' 

    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_estado = request.GET.get("estado", "").strip().upper()
    qs = tubo_filtrado(request,perfil)
    from django.db.models import Count
    compromisos = [{**compromiso_a_dict(item), "evidencias": item.n_evidencias}
                   for item in qs.annotate(n_evidencias=Count("evidencias", distinct=True))]
    # Las atenciones se muestran junto a los compromisos (de más antigua a más reciente); los indicadores
    # y el ranking siguen midiendo solo compromisos.
    from control_gestion.consultas import atenciones_para_tubo
    atenciones = atenciones_para_tubo(request, perfil, filtro_delegacion, filtro_estado, request.GET.get("q", ""))
    visibles = sorted([*compromisos, *atenciones], key=lambda i: i["fecha_compromiso"])
    from core.paginacion import paginar
    pagina_compromisos,paginacion=paginar(request,visibles)
    # Cada tarjeta va en la columna de su estado (así, al moverla, se ve el cambio); «vencido» es una etiqueta de la tarjeta.
    estados_tablero = list(ESTADOS_TUBO)
    columnas = {estado: [] for estado in estados_tablero}
    for item in pagina_compromisos:
        estado = (item.get("estado") or "INGRESADO").upper()
        if estado not in columnas:
            estado = "INGRESADO"
        columnas[estado].append(item)
    bordes = {
        "INGRESADO": "border-secondary",
        "PENDIENTE": "border-warning",
        "EN PROCESO": "border-info",
        "REALIZADO": "border-success",
    }
    columnas_lista = [
        {"estado": estado, "items": columnas[estado], "total": sum(
            (i.get("estado") or "INGRESADO").upper() == estado for i in visibles), "borde": bordes[estado]}
        for estado in estados_tablero
    ]
    total = len(compromisos)
    realizados = sum((i.get("estado") or "").upper()=="REALIZADO" for i in compromisos)
    pct_realizado = round((realizados / total) * 100, 1) if total else 0.0
    pct_pendiente = round(100 - pct_realizado, 1) if total else 0.0
    meta_tubo = obtener_parametros()["meta_tubo_porcentaje"] or META_TUBO_PORCENTAJE
    por_funcionario = {}
    for item in compromisos:
        nombre = item.get("funcionario") or "Sin asignar"
        por_funcionario.setdefault(nombre, {"total": 0, "realizados": 0})
        por_funcionario[nombre]["total"] += 1
        if (item.get("estado") or "").upper() == "REALIZADO":
            por_funcionario[nombre]["realizados"] += 1
    ranking = []
    for nombre, valores in por_funcionario.items():
        pct = round((valores["realizados"] / valores["total"]) * 100, 1) if valores["total"] else 0.0
        ranking.append(
            {
                "nombre": nombre,
                "total": valores["total"],
                "realizados": valores["realizados"],
                "pct": pct,
                "cumple_meta": pct >= meta_tubo,
            }
        )
    ranking.sort(key=lambda item: item["pct"])
    contexto = {
        "columnas_lista": columnas_lista,
        "pagina_compromisos": pagina_compromisos,
        "vista": vista,
        "ruta_vista": ruta_vista,
        "desde_tubo": desde_tubo,
        "consulta_ficha": filtros_ficha.urlencode(),
        "vencidos": sum(i['vencido'] for i in compromisos),
        "estados": ESTADOS_TUBO,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "filtro_estado": filtro_estado,
        "q": request.GET.get("q", ""),
        "consulta_tubo": request.GET.urlencode(),
        "consulta_vista": _sin_pagina(request.GET),
        "total_compromisos": total,
        "realizados": realizados,
        "en_proceso": sum((i.get("estado") or "").upper()=="EN PROCESO" for i in compromisos),
        "por_atender": sum((i.get("estado") or "INGRESADO").upper() in ("INGRESADO", "PENDIENTE") for i in compromisos),
        "pct_realizado": pct_realizado,
        "pct_pendiente": pct_pendiente,
        "ranking": ranking,
        "meta_tubo": meta_tubo,
        **paginacion,
    }
    return render(request, "control_gestion/tubo_trabajo.html", contexto)


def funcionarios_view(request):
    bloqueo = requerir_modulo(request, "matriz_sgr")
    if bloqueo:
        return bloqueo
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    bloqueo_ambito = denegar_otra_delegacion(request, filtro_delegacion)
    if bloqueo_ambito:
        return bloqueo_ambito
    funcionarios = limitar_a_delegacion(request, _funcionarios_enriquecidos(periodo))
    if filtro_delegacion:
        funcionarios = [item for item in funcionarios if (item.get("delegacion") or "") == filtro_delegacion]
    contexto = {
        "periodo": periodo,
        "funcionarios": funcionarios,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "total_funcionarios": len(funcionarios),
    }
    return render(request, "control_gestion/funcionarios.html", contexto)


def _puede_registrar_para(perfil, objetivo_codigo, objetivo_delegacion_id):
    """Registra actividades: la propia persona, el superusuario o el administrador de esa delegación."""
    if perfil is None:
        return False
    propia = bool(perfil.funcionario_id and perfil.funcionario.codigo == objetivo_codigo)
    de_su_delegacion = bool(perfil.rol.codigo == 'administrador' and perfil.delegacion_id
                            and objetivo_delegacion_id == perfil.delegacion_id)
    return perfil.rol.codigo == 'superusuario' or propia or de_su_delegacion


def detalle_funcionario_view(request, id_funcionario):
    periodo = cargar_periodo_medicion()
    valores_form, errores_form = {}, {}
    if request.method == "POST":
        from control_gestion.reportes import perfil_acceso
        from django.http import HttpResponseForbidden
        perfil,error=perfil_acceso(request,'actividades')
        if error is not None:return error
        from cuentas.models import Funcionario as _Funcionario
        objetivo=_Funcionario.objects.filter(codigo=id_funcionario).first()
        if not _puede_registrar_para(perfil, id_funcionario, objetivo.delegacion_id if objetivo else None):
            messages.error(request, 'Solo puede registrar actividades de su propia cuenta.')
            return redirect("detalle_funcionario", id_funcionario=id_funcionario)
        nueva, errores = registrar_actividad_desde_formulario(id_funcionario, request.POST, request.FILES, autor=request.user)
        if not errores and nueva:
            messages.success(
                request,
                f"Actividad registrada. Código verificador {nueva.get('codigo_verificador')}.",
            )
            return redirect("detalle_funcionario", id_funcionario=id_funcionario)
        # Con errores se vuelve a mostrar la ficha con lo escrito y cada error junto a su campo.
        messages.error(request, "No se registró la actividad: revise los campos marcados.")
        valores_form, errores_form = request.POST, errores

    sesion = usuario_sesion(request)
    if not (puede_ver(sesion, "matriz_sgr") or puede_ver(sesion, "actividades")):
        return requerir_modulo(request, "matriz_sgr")
    funcionario_obj = queryset_funcionarios().filter(codigo=id_funcionario).first()
    if funcionario_obj is None:
        messages.error(request, f"No se encontró el funcionario {id_funcionario}.")
        return redirect("funcionarios")
    # Un funcionario sin delegación solo lo consulta el administrador.
    bloqueo_ambito = denegar_otra_delegacion(
        request, funcionario_obj.delegacion.nombre if funcionario_obj.delegacion_id else "(sin delegación)"
    )
    if bloqueo_ambito:
        return bloqueo_ambito
    compromisos = [
        compromiso_a_dict(item)
        for item in queryset_compromisos().filter(funcionario__codigo=id_funcionario)
    ]
    resumen = resumen_tubo_por_funcionario(compromisos)
    funcionario = enriquecer_funcionario(funcionario_base(funcionario_obj), periodo, resumen)
    actividades = [
        actividad_a_dict(item)
        for item in queryset_actividades().filter(funcionario=funcionario_obj)
    ]
    atenciones_por_contacto = {}
    for actividad in actividades:
        clave = actividad.get("contacto") or "Sin contacto"
        atenciones_por_contacto[clave] = atenciones_por_contacto.get(clave, 0) + 1
    from control_gestion.reportes import perfil_actual
    contexto = {
        "periodo": periodo,
        "funcionario": funcionario,
        "actividades": actividades,
        "atenciones_por_contacto": atenciones_por_contacto,
        "fecha_hoy": timezone.localdate().strftime("%Y-%m-%d"),
        "puede_registrar": _puede_registrar_para(perfil_actual(request), funcionario_obj.codigo, funcionario_obj.delegacion_id),
        "valores": valores_form,
        "errores": errores_form,
        "tipos_registro": [("RESULTADO", "Resultado realizado"), ("COORDINACION", "Coordinación / seguimiento"),
                           ("DELEGADO", "Gestión del delegado"), ("FELICITACION", "Felicitación pendiente de validar")],
    }
    return render(request, "control_gestion/detalle_funcionario.html", contexto)


def resumen_delegacion_view(request):
    bloqueo = requerir_modulo(request, "matriz_sgr")
    if bloqueo:
        return bloqueo
    periodo = cargar_periodo_medicion()
    filtro_delegacion = delegacion_por_defecto(
        request, request.GET.get("delegacion", "").strip(), periodo["delegacion_piloto"])
    bloqueo_ambito = denegar_otra_delegacion(request, filtro_delegacion)
    if bloqueo_ambito:
        return bloqueo_ambito
    funcionarios = [
        item
        for item in _funcionarios_enriquecidos(periodo)
        if (item.get("delegacion") or "") == filtro_delegacion
    ]
    actividades = [
        actividad_a_dict(item)
        for item in queryset_actividades().filter(delegacion__nombre=filtro_delegacion)
    ]
    fechas = [parsear_fecha(item.get("fecha_actividad")) for item in actividades]
    fechas = [item for item in fechas if item]
    ultimo_ingreso = max(fechas) if fechas else None
    dias_desde_ultimo = (timezone.localdate() - ultimo_ingreso).days if ultimo_ingreso else None
    total_ingresos = len(actividades)
    promedio_diario = round(total_ingresos / periodo["dias_avance"], 2) if periodo["dias_avance"] else 0.0
    promedio_equipo = (
        round(sum(item["ponderado_total"] for item in funcionarios) / len(funcionarios), 1) if funcionarios else 0.0
    )
    contexto = {
        "periodo": periodo,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "funcionarios": funcionarios,
        "ultimo_ingreso": ultimo_ingreso.strftime("%Y-%m-%d") if ultimo_ingreso else "Sin registros",
        "dias_desde_ultimo": dias_desde_ultimo,
        "total_ingresos": total_ingresos,
        "promedio_diario": promedio_diario,
        "promedio_equipo": promedio_equipo,
        "total_funcionarios": len(funcionarios),
    }
    return render(request, "control_gestion/resumen.html", contexto)
