from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from cuentas.store import cargar_json_seguro, cargar_parametros, guardar_json_seguro
from cuentas.vocabulario import DELEGACIONES_OFICIALES

ESTADOS_TUBO = ["INGRESADO", "PENDIENTE", "EN PROCESO", "REALIZADO"]
META_TUBO_PORCENTAJE = 80


def parsear_fecha(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def cargar_periodo_medicion():
    medicion = cargar_json_seguro("medicion.json", {})
    if not isinstance(medicion, dict):
        medicion = {}
    fecha_inicio = parsear_fecha(medicion.get("fecha_inicio")) or date(2026, 7, 1)
    fecha_termino = parsear_fecha(medicion.get("fecha_termino")) or date(2026, 9, 28)
    dias_totales = int(medicion.get("dias_totales") or 90)
    hoy = date.today()
    if hoy < fecha_inicio:
        dias_avance = 0
    elif hoy > fecha_termino:
        dias_avance = dias_totales
    else:
        dias_avance = (hoy - fecha_inicio).days
    pct_esperado = round((dias_avance / dias_totales) * 100, 1) if dias_totales else 0.0
    return {
        "periodo": medicion.get("periodo", "Trimestre en curso"),
        "delegacion_piloto": medicion.get("delegacion_piloto", "Delegación Rural"),
        "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
        "fecha_termino": fecha_termino.strftime("%Y-%m-%d"),
        "fecha_hoy": hoy.strftime("%Y-%m-%d"),
        "dias_totales": dias_totales,
        "dias_avance": dias_avance,
        "pct_esperado": pct_esperado,
        "meta_cumplimiento_tubo": int(medicion.get("meta_cumplimiento_tubo") or META_TUBO_PORCENTAJE),
    }


def calcular_item_medicion(item):
    meta = float(item.get("meta_trimestre") or 0)
    avance = float(item.get("avance_actual") or 0)
    ponderador = float(item.get("ponderador") or 0)
    pct = round((avance / meta) * 100, 1) if meta else 0.0
    if pct > 100:
        pct = 100.0
    ponderado = round((ponderador * pct) / 100.0, 2)
    resultado = dict(item)
    resultado["meta_trimestre"] = meta
    resultado["avance_actual"] = avance
    resultado["ponderador"] = ponderador
    resultado["pct_cumplimiento"] = pct
    resultado["cumplimiento_ponderado"] = ponderado
    return resultado


def asignar_semaforo_sgr(pct_logrado, pct_esperado):
    diferencia = pct_logrado - pct_esperado
    if diferencia >= 0:
        return {
            "nivel": "Verde",
            "clase": "bg-success",
            "texto": "En línea con la meta diaria",
        }
    if diferencia >= -10:
        return {
            "nivel": "Amarillo",
            "clase": "bg-warning text-dark",
            "texto": "Bajo la línea esperada",
        }
    return {
        "nivel": "Rojo",
        "clase": "bg-danger",
        "texto": "Rezagado / requiere acompañamiento",
    }


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
    semaforo = asignar_semaforo_sgr(ponderado_total, periodo["pct_esperado"])
    clave = funcionario.get("id_funcionario")
    tubo = resumen_tubo.get(clave, {"total": 0, "realizados": 0, "pendientes": 0})
    pct_tubo = (
        round((tubo["realizados"] / tubo["total"]) * 100, 1) if tubo["total"] else 0.0
    )
    cumple_tubo = pct_tubo >= periodo["meta_cumplimiento_tubo"] if tubo["total"] else False
    ultimo = parsear_fecha(funcionario.get("fecha_ultimo_ingreso"))
    dias_sin_ingreso = (date.today() - ultimo).days if ultimo else None
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
    params = cargar_parametros()
    sla_verde = params["sla_verde_max_dias"]
    sla_amarillo = params["sla_amarillo_max_dias"]
    dias = item.get("dias_transcurridos", 0)
    try:
        dias = int(dias)
    except (ValueError, TypeError):
        dias = 0
    if dias <= sla_verde:
        nivel = "Verde"
        clase = "bg-success"
        color_dot = "Verde"
    elif dias <= sla_amarillo:
        nivel = "Amarillo"
        clase = "bg-warning text-dark"
        color_dot = "Amarillo"
    else:
        nivel = "Rojo"
        clase = "bg-danger"
        color_dot = "Rojo"
    item_copia = dict(item)
    item_copia["dias_transcurridos"] = dias
    item_copia["semaforo_nivel"] = nivel
    item_copia["semaforo_clase"] = clase
    item_copia["color_dot"] = color_dot
    return item_copia


def dashboard_cuellos_botella_view(request):
    requerimientos_crudos = cargar_json_seguro("requerimientos.json", [])
    requerimientos = [calcular_semaforo_ticket(item) for item in requerimientos_crudos]
    total_requerimientos = len(requerimientos)
    cuellos_botella = [item for item in requerimientos if item["dias_transcurridos"] >= 6]
    total_criticos = len(cuellos_botella)
    porcentaje_criticos = (
        round((total_criticos / total_requerimientos) * 100, 1)
        if total_requerimientos > 0
        else 0.0
    )
    tiempo_promedio = (
        round(sum(item["dias_transcurridos"] for item in requerimientos) / total_requerimientos, 1)
        if total_requerimientos > 0
        else 0.0
    )
    stats_delegaciones = []
    conteo_por_delegacion = {}
    for delegacion in DELEGACIONES_OFICIALES:
        casos_del = [item for item in requerimientos if item.get("delegacion") == delegacion]
        total_del = len(casos_del)
        criticos_del = sum(1 for item in casos_del if item["dias_transcurridos"] >= 6)
        tiempo_prom_del = (
            round(sum(item["dias_transcurridos"] for item in casos_del) / total_del, 1)
            if total_del > 0
            else 0.0
        )
        pct_carga = (
            round((total_del / total_requerimientos) * 100, 1)
            if total_requerimientos > 0
            else 0.0
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
    }
    return render(request, "control_gestion/dashboard.html", contexto)


def kanban_view(request):
    requerimientos_crudos = cargar_json_seguro("requerimientos.json", [])
    requerimientos = [calcular_semaforo_ticket(item) for item in requerimientos_crudos]
    pendientes = []
    en_proceso = []
    cuello_botella = []
    resueltos = []
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
    areas_crudo = cargar_json_seguro("areas_soporte.json", [])
    criterio_orden = request.GET.get("orden", "").strip().lower()
    areas_procesadas = []
    for area in areas_crudo:
        pct = area.get("porcentaje_cumplimiento") or 0
        satisfaccion = float(area.get("satisfaccion_promedio") or 0.0)
        if pct >= 80:
            nivel_rendimiento = "Alto Rendimiento"
            badge_clase = "bg-success"
            tarjeta_borde = "border-success"
            color_barra = "bg-success"
        elif 60 <= pct < 80:
            nivel_rendimiento = "Rendimiento Medio / En Observación"
            badge_clase = "bg-warning text-dark"
            tarjeta_borde = "border-warning"
            color_barra = "bg-warning"
        else:
            nivel_rendimiento = "Alerta Operativa / Crítico"
            badge_clase = "bg-danger"
            tarjeta_borde = "border-danger"
            color_barra = "bg-danger"
        area_item = dict(area)
        area_item["porcentaje_cumplimiento"] = pct
        area_item["satisfaccion_promedio"] = satisfaccion
        area_item["nivel_rendimiento"] = nivel_rendimiento
        area_item["badge_clase"] = badge_clase
        area_item["tarjeta_borde"] = tarjeta_borde
        area_item["color_barra"] = color_barra
        area_item["satisfaccion_formato"] = f"{satisfaccion:.1f} / 5.0"
        areas_procesadas.append(area_item)
    if criterio_orden == "satisfaccion":
        areas_procesadas.sort(key=lambda item: (item.get("satisfaccion_promedio") or 0.0), reverse=True)
    elif criterio_orden == "cumplimiento":
        areas_procesadas.sort(key=lambda item: (item.get("porcentaje_cumplimiento") or 0), reverse=True)
    elif criterio_orden == "tiempo":
        areas_procesadas.sort(key=lambda item: (item.get("tiempo_promedio_dias") or 0.0))
    elif criterio_orden == "casos":
        areas_procesadas.sort(key=lambda item: (item.get("total_casos_mes") or 0), reverse=True)
    if criterio_orden:
        messages.info(request, f"Áreas ordenadas por: {criterio_orden.capitalize()}")
    contexto = {
        "areas": areas_procesadas,
        "criterio_orden": criterio_orden,
        "total_areas": len(areas_procesadas),
    }
    return render(request, "control_gestion/areas.html", contexto)


def semaforo_sgr_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    funcionarios_crudos = cargar_json_seguro("funcionarios.json", [])
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    resumen_tubo = resumen_tubo_por_funcionario(compromisos)
    funcionarios = [
        enriquecer_funcionario(item, periodo, resumen_tubo) for item in funcionarios_crudos
    ]
    if filtro_delegacion:
        funcionarios = [
            item for item in funcionarios if (item.get("delegacion") or "") == filtro_delegacion
        ]
    total = len(funcionarios)
    verdes = sum(1 for item in funcionarios if item["semaforo_nivel"] == "Verde")
    amarillos = sum(1 for item in funcionarios if item["semaforo_nivel"] == "Amarillo")
    rojos = sum(1 for item in funcionarios if item["semaforo_nivel"] == "Rojo")
    contexto = {
        "periodo": periodo,
        "funcionarios": funcionarios,
        "delegaciones": DELEGACIONES_OFICIALES,
        "filtro_delegacion": filtro_delegacion,
        "total_funcionarios": total,
        "total_verde": verdes,
        "total_amarillo": amarillos,
        "total_rojo": rojos,
    }
    return render(request, "control_gestion/semaforo_sgr.html", contexto)


def tubo_trabajo_view(request):
    if request.method == "POST":
        id_compromiso = request.POST.get("id_compromiso", "").strip()
        nuevo_estado = request.POST.get("estado", "").strip().upper()
        compromisos = cargar_json_seguro("tubo_trabajo.json", [])
        estados_validos = set(ESTADOS_TUBO)
        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado del tubo de trabajo no válido.")
        else:
            actualizado = False
            for item in compromisos:
                if item.get("id_compromiso") == id_compromiso:
                    item["estado"] = nuevo_estado
                    actualizado = True
                    break
            if actualizado and guardar_json_seguro("tubo_trabajo.json", compromisos):
                messages.success(
                    request,
                    f"Compromiso {id_compromiso} actualizado a {nuevo_estado}.",
                )
            else:
                messages.error(request, "No fue posible actualizar el compromiso.")
        return redirect("tubo_trabajo")

    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_estado = request.GET.get("estado", "").strip().upper()
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    if filtro_delegacion:
        compromisos = [
            item for item in compromisos if (item.get("delegacion") or "") == filtro_delegacion
        ]
    if filtro_estado:
        compromisos = [
            item for item in compromisos if (item.get("estado") or "").upper() == filtro_estado
        ]
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
        {
            "estado": estado,
            "items": columnas[estado],
            "total": len(columnas[estado]),
            "borde": bordes[estado],
        }
        for estado in ESTADOS_TUBO
    ]
    total = len(compromisos)
    realizados = len(columnas["REALIZADO"])
    pct_realizado = round((realizados / total) * 100, 1) if total else 0.0
    pct_pendiente = round(100 - pct_realizado, 1) if total else 0.0
    por_funcionario = {}
    for item in compromisos:
        nombre = item.get("funcionario") or "Sin asignar"
        if nombre not in por_funcionario:
            por_funcionario[nombre] = {"total": 0, "realizados": 0}
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
                "cumple_meta": pct >= META_TUBO_PORCENTAJE,
            }
        )
    ranking.sort(key=lambda item: item["pct"])
    contexto = {
        "columnas_lista": columnas_lista,
        "estados": ESTADOS_TUBO,
        "delegaciones": DELEGACIONES_OFICIALES,
        "filtro_delegacion": filtro_delegacion,
        "filtro_estado": filtro_estado,
        "total_compromisos": total,
        "pct_realizado": pct_realizado,
        "pct_pendiente": pct_pendiente,
        "ranking": ranking,
        "meta_tubo": META_TUBO_PORCENTAJE,
    }
    return render(request, "control_gestion/tubo_trabajo.html", contexto)


def funcionarios_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    funcionarios_crudos = cargar_json_seguro("funcionarios.json", [])
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    resumen_tubo = resumen_tubo_por_funcionario(compromisos)
    funcionarios = [
        enriquecer_funcionario(item, periodo, resumen_tubo) for item in funcionarios_crudos
    ]
    if filtro_delegacion:
        funcionarios = [
            item for item in funcionarios if (item.get("delegacion") or "") == filtro_delegacion
        ]
    contexto = {
        "periodo": periodo,
        "funcionarios": funcionarios,
        "delegaciones": DELEGACIONES_OFICIALES,
        "filtro_delegacion": filtro_delegacion,
        "total_funcionarios": len(funcionarios),
    }
    return render(request, "control_gestion/funcionarios.html", contexto)


def registrar_actividad_desde_formulario(id_funcionario, post, archivos):
    contacto = (post.get("contacto") or "").strip()
    item_nombre = (post.get("item") or "").strip()
    servicio = (post.get("servicio") or "").strip()
    imagen = (post.get("imagen_verificadora") or "").strip()
    fecha_actividad = (post.get("fecha_actividad") or "").strip() or date.today().strftime("%Y-%m-%d")
    errores = {}
    if len(contacto) < 3:
        errores["contacto"] = "Indique el contacto o vecino atendido (mínimo 3 caracteres)."
    if not item_nombre:
        errores["item"] = "Seleccione el ítem de la matriz SGR."
    if len(servicio) < 5:
        errores["servicio"] = "Describa el servicio o atención (mínimo 5 caracteres)."
    try:
        datetime.strptime(fecha_actividad, "%Y-%m-%d")
    except ValueError:
        errores["fecha_actividad"] = "Ingrese una fecha válida (AAAA-MM-DD)."
    archivo = archivos.get("evidencia") if archivos else None
    if archivo:
        imagen = archivo.name
    elif not imagen:
        imagen = "Registro fotográfico pendiente de adjuntar"
    if errores:
        return None, errores

    funcionarios_crudos = cargar_json_seguro("funcionarios.json", [])
    actividades = cargar_json_seguro("actividades.json", [])
    funcionario_ref = next(
        (item for item in funcionarios_crudos if item.get("id_funcionario") == id_funcionario),
        None,
    )
    if funcionario_ref is None:
        return None, {"id_funcionario": "No se encontró el funcionario indicado."}

    correlativo = len(actividades) + 1
    codigo = f"VER-{fecha_actividad.replace('-', '')}-{id_funcionario}-{correlativo:03d}"
    nueva = {
        "id_actividad": f"ACT-{correlativo:03d}",
        "id_funcionario": id_funcionario,
        "funcionario_nombre": funcionario_ref.get("nombre", ""),
        "cargo": funcionario_ref.get("cargo", ""),
        "delegacion": funcionario_ref.get("delegacion", ""),
        "fecha_actividad": fecha_actividad,
        "contacto": contacto,
        "item": item_nombre,
        "servicio": servicio,
        "codigo_verificador": codigo,
        "imagen_verificadora": imagen,
        "punto_validado": True,
    }
    actividades.insert(0, nueva)
    if not guardar_json_seguro("actividades.json", actividades):
        return None, {"guardar": "No fue posible guardar la actividad en JSON."}
    for item in funcionarios_crudos:
        if item.get("id_funcionario") == id_funcionario:
            item["fecha_ultimo_ingreso"] = fecha_actividad
            for meta in item.get("items", []):
                if meta.get("item") == item_nombre:
                    meta["avance_actual"] = int(meta.get("avance_actual") or 0) + 1
            break
    guardar_json_seguro("funcionarios.json", funcionarios_crudos)
    return nueva, {}


def detalle_funcionario_view(request, id_funcionario):
    periodo = cargar_periodo_medicion()
    funcionarios_crudos = cargar_json_seguro("funcionarios.json", [])
    actividades = cargar_json_seguro("actividades.json", [])
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])

    if request.method == "POST":
        nueva, errores = registrar_actividad_desde_formulario(
            id_funcionario, request.POST, request.FILES
        )
        if errores:
            messages.error(
                request,
                " ".join(errores.values())
                if errores
                else "Complete contacto, ítem y servicio para registrar la actividad.",
            )
        elif nueva:
            messages.success(
                request,
                f"Actividad registrada. Código verificador {nueva.get('codigo_verificador')}.",
            )
        return redirect("detalle_funcionario", id_funcionario=id_funcionario)

    funcionario_crudo = next(
        (item for item in funcionarios_crudos if item.get("id_funcionario") == id_funcionario),
        None,
    )
    if funcionario_crudo is None:
        messages.error(request, f"No se encontró el funcionario {id_funcionario}.")
        return redirect("funcionarios")

    resumen_tubo = resumen_tubo_por_funcionario(compromisos)
    funcionario = enriquecer_funcionario(funcionario_crudo, periodo, resumen_tubo)
    actividades_func = [
        item for item in actividades if item.get("id_funcionario") == id_funcionario
    ]
    atenciones_por_contacto = {}
    for actividad in actividades_func:
        clave = actividad.get("contacto") or "Sin contacto"
        atenciones_por_contacto[clave] = atenciones_por_contacto.get(clave, 0) + 1
    contexto = {
        "periodo": periodo,
        "funcionario": funcionario,
        "actividades": actividades_func,
        "atenciones_por_contacto": atenciones_por_contacto,
        "compromisos": [
            item for item in compromisos if item.get("id_funcionario") == id_funcionario
        ],
        "fecha_hoy": date.today().strftime("%Y-%m-%d"),
    }
    return render(request, "control_gestion/detalle_funcionario.html", contexto)


def resumen_delegacion_view(request):
    periodo = cargar_periodo_medicion()
    filtro_delegacion = request.GET.get("delegacion", "").strip() or periodo["delegacion_piloto"]
    funcionarios_crudos = cargar_json_seguro("funcionarios.json", [])
    actividades = cargar_json_seguro("actividades.json", [])
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    resumen_tubo = resumen_tubo_por_funcionario(compromisos)
    funcionarios = [
        enriquecer_funcionario(item, periodo, resumen_tubo)
        for item in funcionarios_crudos
        if (item.get("delegacion") or "") == filtro_delegacion
    ]
    actividades_del = [
        item for item in actividades if (item.get("delegacion") or "") == filtro_delegacion
    ]
    fechas = [parsear_fecha(item.get("fecha_actividad")) for item in actividades_del]
    fechas = [item for item in fechas if item]
    ultimo_ingreso = max(fechas) if fechas else None
    dias_desde_ultimo = (date.today() - ultimo_ingreso).days if ultimo_ingreso else None
    total_ingresos = len(actividades_del)
    promedio_diario = (
        round(total_ingresos / periodo["dias_avance"], 2) if periodo["dias_avance"] else 0.0
    )
    promedio_equipo = (
        round(sum(item["ponderado_total"] for item in funcionarios) / len(funcionarios), 1)
        if funcionarios
        else 0.0
    )
    contexto = {
        "periodo": periodo,
        "delegaciones": DELEGACIONES_OFICIALES,
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
