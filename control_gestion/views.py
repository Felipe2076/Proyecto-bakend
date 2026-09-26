from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render
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
from control_gestion.models import Medicion
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
    medicion = Medicion.objects.select_related("delegacion_piloto").order_by("-fecha_inicio").first()
    params = obtener_parametros()
    if medicion is None:
        fecha_inicio = date(2026, 7, 1)
        fecha_termino = date(2026, 9, 28)
        dias_totales = 90
        periodo_nombre = "Trimestre en curso"
        piloto = "Delegación Rural"
        meta = int(params["meta_tubo_porcentaje"] or META_TUBO_PORCENTAJE)
    else:
        fecha_inicio = medicion.fecha_inicio
        fecha_termino = medicion.fecha_termino
        dias_totales = int(medicion.dias_totales or 90)
        periodo_nombre = medicion.periodo
        piloto = medicion.delegacion_piloto.nombre
        meta = int(medicion.meta_cumplimiento_tubo or params["meta_tubo_porcentaje"] or META_TUBO_PORCENTAJE)
    hoy = timezone.localdate()
    if hoy < fecha_inicio:
        dias_avance = 0
    elif hoy > fecha_termino:
        dias_avance = dias_totales
    else:
        dias_avance = (hoy - fecha_inicio).days
    pct_esperado = round((dias_avance / dias_totales) * 100, 1) if dias_totales else 0.0
    return {
        "periodo": periodo_nombre,
        "delegacion_piloto": piloto,
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_termino": fecha_termino.strftime("%Y-%m-%d"),
        "fecha_hoy": hoy.strftime("%Y-%m-%d"),
        "dias_totales": dias_totales,
        "dias_avance": dias_avance,
        "pct_esperado": pct_esperado,
        "meta_cumplimiento_tubo": meta,
    }


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
    semaforo = asignar_semaforo_sgr(
        ponderado_total, periodo["pct_esperado"], periodo.get("dias_totales")
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


def calcular_semaforo_ticket(item):
    params = obtener_parametros()
    sla_verde = params["sla_verde_max_dias"]
    sla_amarillo = params["sla_amarillo_max_dias"]
    dias = item.get("dias_transcurridos", 0)
    try:
        dias = int(dias)
    except (ValueError, TypeError):
        dias = 0
    if dias <= sla_verde:
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


def _tickets():
    return [calcular_semaforo_ticket(ticket_a_dict(req)) for req in queryset_requerimientos()]


def _compromisos():
    return [compromiso_a_dict(item) for item in queryset_compromisos()]


def _funcionarios_enriquecidos(periodo, compromisos=None):
    if compromisos is None:
        compromisos = _compromisos()
    resumen = resumen_tubo_por_funcionario(compromisos)
    return [enriquecer_funcionario(funcionario_base(fun), periodo, resumen) for fun in queryset_funcionarios()]


def dashboard_cuellos_botella_view(request):
    requerimientos = _tickets()
    total_requerimientos = len(requerimientos)
    cuellos_botella = [item for item in requerimientos if item["dias_transcurridos"] >= 6]
    total_criticos = len(cuellos_botella)
    porcentaje_criticos = (
        round((total_criticos / total_requerimientos) * 100, 1) if total_requerimientos > 0 else 0.0
    )
    tiempo_promedio = (
        round(sum(item["dias_transcurridos"] for item in requerimientos) / total_requerimientos, 1)
        if total_requerimientos > 0
        else 0.0
    )
    delegaciones = nombres_delegaciones()
    stats_delegaciones = []
    conteo_por_delegacion = {}
    for delegacion in delegaciones:
        casos_del = [item for item in requerimientos if item.get("delegacion") == delegacion]
        total_del = len(casos_del)
        criticos_del = sum(1 for item in casos_del if item["dias_transcurridos"] >= 6)
        tiempo_prom_del = (
            round(sum(item["dias_transcurridos"] for item in casos_del) / total_del, 1) if total_del > 0 else 0.0
        )
        pct_carga = (
            round((total_del / total_requerimientos) * 100, 1) if total_requerimientos > 0 else 0.0
        )
        conteo_por_delegacion[delegacion] = total_del
        stats_delegaciones.append(
            {
                "nombre": delegacion,
                "total": total_del,
                "criticos": criticos_del,
                "tiempo_promedio": tiempo_prom_del,
                "porcentaje_carga": pct_carga,
            }
        )
    if conteo_por_delegacion and max(conteo_por_delegacion.values(), default=0) > 0:
        delegacion_mayor_demanda = max(conteo_por_delegacion, key=lambda clave: conteo_por_delegacion[clave])
    else:
        delegacion_mayor_demanda = "Sin datos"
    contexto = {
        "total_requerimientos": total_requerimientos,
        "total_criticos": total_criticos,
        "porcentaje_criticos": porcentaje_criticos,
        "tiempo_promedio": tiempo_promedio,
        "delegacion_mayor_demanda": delegacion_mayor_demanda,
        "cuellos_botella": cuellos_botella,
        "stats_delegaciones": stats_delegaciones,
        "panel": construir_panel(),
    }
    return render(request, "control_gestion/dashboard.html", contexto)


def kanban_view(request):
    requerimientos = _tickets()
    pendientes, en_proceso, cuello_botella, resueltos = [], [], [], []
    for req in requerimientos:
        estado = req.get("estado_proceso", "")
        dias = req.get("dias_transcurridos", 0)
        if estado == "Resuelto":
            resueltos.append(req)
        elif estado == "Cuello Botella Central" or dias >= 6:
            cuello_botella.append(req)
        elif estado == "En Proceso":
            en_proceso.append(req)
        else:
            pendientes.append(req)
    contexto = {
        "pendientes": pendientes,
        "en_proceso": en_proceso,
        "cuello_botella": cuello_botella,
        "resueltos": resueltos,
        "total_pendientes": len(pendientes),
        "total_en_proceso": len(en_proceso),
        "total_cuello_botella": len(cuello_botella),
        "total_resueltos": len(resueltos),
        "total_general": len(requerimientos),
    }
    return render(request, "control_gestion/kanban.html", contexto)


def areas_soporte_view(request):
    criterio_orden = request.GET.get("orden", "").strip().lower()
    areas_procesadas = []
    for area in AreaSoporte.objects.select_related("encargado").order_by("codigo"):
        pct = int(area.porcentaje_cumplimiento or 0)
        satisfaccion = float(area.satisfaccion_promedio or 0.0)
        if pct >= 80:
            nivel_rendimiento, badge_clase, tarjeta_borde, color_barra = (
                "Alto Rendimiento",
                "bg-success",
                "border-success",
                "bg-success",
            )
        elif 60 <= pct < 80:
            nivel_rendimiento, badge_clase, tarjeta_borde, color_barra = (
                "Rendimiento Medio / En Observación",
                "bg-warning text-dark",
                "border-warning",
                "bg-warning",
            )
        else:
            nivel_rendimiento, badge_clase, tarjeta_borde, color_barra = (
                "Alerta Operativa / Crítico",
                "bg-danger",
                "border-danger",
                "bg-danger",
            )
        encargado = area.encargado.nombre if area.encargado_id else area.encargado_nombre
        areas_procesadas.append(
            {
                "id_area": area.codigo,
                "nombre_area": area.nombre,
                "encargado": encargado,
                "descripcion": area.descripcion,
                "porcentaje_cumplimiento": pct,
                "satisfaccion_promedio": satisfaccion,
                "tiempo_promedio_dias": area.tiempo_promedio_dias,
                "total_casos_mes": area.total_casos_mes,
                "nivel_rendimiento": nivel_rendimiento,
                "badge_clase": badge_clase,
                "tarjeta_borde": tarjeta_borde,
                "color_barra": color_barra,
                "satisfaccion_formato": f"{satisfaccion:.1f} / 5.0",
            }
        )
    if criterio_orden == "satisfaccion":
        areas_procesadas.sort(key=lambda item: (item.get("satisfaccion_promedio") or 0.0), reverse=True)
    elif criterio_orden == "cumplimiento":
        areas_procesadas.sort(key=lambda item: (item.get("porcentaje_cumplimiento") or 0), reverse=True)
    elif criterio_orden == "tiempo":
        areas_procesadas.sort(key=lambda item: float(item.get("tiempo_promedio_dias") or 0))
    elif criterio_orden == "casos":
        areas_procesadas.sort(key=lambda item: (item.get("total_casos_mes") or 0), reverse=True)
    if criterio_orden:
        messages.info(request, f"Áreas ordenadas por: {criterio_orden.capitalize()}")
    contexto = {"areas": areas_procesadas, "criterio_orden": criterio_orden, "total_areas": len(areas_procesadas)}
    return render(request, "control_gestion/areas.html", contexto)


def semaforo_sgr_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    funcionarios = _funcionarios_enriquecidos(periodo)
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


def tubo_trabajo_view(request):
    if request.method == "POST":
        id_compromiso = request.POST.get("id_compromiso", "").strip()
        nuevo_estado = request.POST.get("estado", "").strip().upper()
        if nuevo_estado not in ESTADOS_TUBO:
            messages.error(request, "Estado del tubo de trabajo no válido.")
        else:
            from control_gestion.models import Compromiso

            actualizado = Compromiso.objects.filter(codigo=id_compromiso).update(estado=nuevo_estado)
            if actualizado:
                messages.success(request, f"Compromiso {id_compromiso} actualizado a {nuevo_estado}.")
            else:
                messages.error(request, "No fue posible actualizar el compromiso.")
        return redirect("tubo_trabajo")

    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_estado = request.GET.get("estado", "").strip().upper()
    qs = queryset_compromisos()
    if filtro_delegacion:
        qs = qs.filter(delegacion__nombre=filtro_delegacion)
    if filtro_estado:
        qs = qs.filter(estado=filtro_estado)
    compromisos = [compromiso_a_dict(item) for item in qs]
    columnas = {estado: [] for estado in ESTADOS_TUBO}
    for item in compromisos:
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
        {"estado": estado, "items": columnas[estado], "total": len(columnas[estado]), "borde": bordes[estado]}
        for estado in ESTADOS_TUBO
    ]
    total = len(compromisos)
    realizados = len(columnas["REALIZADO"])
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
        "estados": ESTADOS_TUBO,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "filtro_estado": filtro_estado,
        "total_compromisos": total,
        "pct_realizado": pct_realizado,
        "pct_pendiente": pct_pendiente,
        "ranking": ranking,
        "meta_tubo": meta_tubo,
    }
    return render(request, "control_gestion/tubo_trabajo.html", contexto)


def funcionarios_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    funcionarios = _funcionarios_enriquecidos(periodo)
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


def detalle_funcionario_view(request, id_funcionario):
    periodo = cargar_periodo_medicion()
    if request.method == "POST":
        nueva, errores = registrar_actividad_desde_formulario(id_funcionario, request.POST, request.FILES)
        if errores:
            messages.error(request, " ".join(errores.values()))
        elif nueva:
            messages.success(
                request,
                f"Actividad registrada. Código verificador {nueva.get('codigo_verificador')}.",
            )
        return redirect("detalle_funcionario", id_funcionario=id_funcionario)

    funcionario_obj = queryset_funcionarios().filter(codigo=id_funcionario).first()
    if funcionario_obj is None:
        messages.error(request, f"No se encontró el funcionario {id_funcionario}.")
        return redirect("funcionarios")
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
    contexto = {
        "periodo": periodo,
        "funcionario": funcionario,
        "actividades": actividades,
        "atenciones_por_contacto": atenciones_por_contacto,
        "compromisos": compromisos,
        "fecha_hoy": timezone.localdate().strftime("%Y-%m-%d"),
    }
    return render(request, "control_gestion/detalle_funcionario.html", contexto)


def resumen_delegacion_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip() or periodo["delegacion_piloto"]
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
