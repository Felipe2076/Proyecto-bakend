"""Pantallas adicionales del mockup: agenda, actividades, compromisos y notificaciones."""

import calendar
from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render

from cuentas.auth import requerir_modulo
from cuentas.store import cargar_json_seguro, guardar_json_seguro
from control_gestion.views import (
    DELEGACIONES_OFICIALES,
    ESTADOS_TUBO,
    registrar_actividad_desde_formulario,
)

from config.context_processors import _notificaciones_base


def _parse_fecha(valor):
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _siguiente_id(prefijo, existentes, campo, ancho=3):
    maximo = 0
    for item in existentes:
        bruto = str(item.get(campo) or "")
        if not bruto.startswith(prefijo):
            continue
        cola = bruto.replace(prefijo, "").lstrip("-")
        try:
            maximo = max(maximo, int(cola))
        except ValueError:
            continue
    return f"{prefijo}{maximo + 1:0{ancho}d}"


def agenda_view(request):
    bloqueo = requerir_modulo(request, "agenda")
    if bloqueo:
        return bloqueo
    hoy = date.today()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
        mes = int(request.GET.get("mes") or hoy.month)
        if mes < 1 or mes > 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    vista = (request.GET.get("vista") or "calendario").strip().lower()
    if vista not in {"calendario", "lista"}:
        vista = "calendario"

    eventos_agenda = cargar_json_seguro("agenda.json", [])
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    actividades = cargar_json_seguro("actividades.json", [])

    eventos = []
    for item in eventos_agenda:
        fecha = _parse_fecha(item.get("fecha"))
        if not fecha:
            continue
        eventos.append(
            {
                "id": item.get("id_evento"),
                "titulo": item.get("titulo"),
                "detalle": f"{item.get('hora') or ''} · {item.get('lugar') or ''}".strip(" ·"),
                "tipo": item.get("tipo") or "Agenda",
                "fecha": fecha,
                "fecha_iso": fecha.strftime("%Y-%m-%d"),
                "delegacion": item.get("delegacion"),
                "responsable": item.get("responsable"),
                "origen": "agenda",
                "clase": "text-bg-primary",
            }
        )
    for item in compromisos:
        fecha = _parse_fecha(item.get("fecha_compromiso"))
        if not fecha:
            continue
        eventos.append(
            {
                "id": item.get("id_compromiso"),
                "titulo": item.get("descripcion"),
                "detalle": f"{item.get('vecino')} · {item.get('estado')}",
                "tipo": "Compromiso ciudadano",
                "fecha": fecha,
                "fecha_iso": fecha.strftime("%Y-%m-%d"),
                "delegacion": item.get("delegacion"),
                "responsable": item.get("funcionario"),
                "origen": "compromiso",
                "clase": "text-bg-warning",
            }
        )
    for item in actividades:
        fecha = _parse_fecha(item.get("fecha_actividad"))
        if not fecha:
            continue
        eventos.append(
            {
                "id": item.get("id_actividad"),
                "titulo": item.get("servicio"),
                "detalle": f"{item.get('contacto')} · {item.get('codigo_verificador')}",
                "tipo": "Actividad diaria",
                "fecha": fecha,
                "fecha_iso": fecha.strftime("%Y-%m-%d"),
                "delegacion": item.get("delegacion"),
                "responsable": item.get("funcionario_nombre"),
                "origen": "actividad",
                "clase": "text-bg-success",
            }
        )
    eventos.sort(key=lambda item: (item["fecha"], item.get("titulo") or ""))

    por_dia = {}
    for evento in eventos:
        if evento["fecha"].year == anio and evento["fecha"].month == mes:
            por_dia.setdefault(evento["fecha"].day, []).append(evento)

    cal = calendar.Calendar(firstweekday=0)
    semanas = []
    for semana in cal.monthdayscalendar(anio, mes):
        fila = []
        for dia in semana:
            fila.append(
                {
                    "dia": dia,
                    "eventos": por_dia.get(dia, []) if dia else [],
                    "es_hoy": bool(dia) and date(anio, mes, dia) == hoy,
                }
            )
        semanas.append(fila)

    if mes == 1:
        prev_anio, prev_mes = anio - 1, 12
    else:
        prev_anio, prev_mes = anio, mes - 1
    if mes == 12:
        next_anio, next_mes = anio + 1, 1
    else:
        next_anio, next_mes = anio, mes + 1

    lista_mes = [item for item in eventos if item["fecha"].year == anio and item["fecha"].month == mes]
    contexto = {
        "vista": vista,
        "anio": anio,
        "mes": mes,
        "nombre_mes": calendar.month_name[mes].capitalize() if calendar.month_name[mes] else str(mes),
        "semanas": semanas,
        "dias_semana": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
        "lista_mes": lista_mes,
        "total_mes": len(lista_mes),
        "prev_anio": prev_anio,
        "prev_mes": prev_mes,
        "next_anio": next_anio,
        "next_mes": next_mes,
        "hoy": hoy.strftime("%Y-%m-%d"),
    }
    # calendar.month_name is English by default; force Spanish labels
    meses_es = [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    contexto["nombre_mes"] = meses_es[mes]
    return render(request, "control_gestion/agenda.html", contexto)


def actividades_diarias_view(request):
    bloqueo = requerir_modulo(request, "actividades")
    if bloqueo:
        return bloqueo
    funcionarios = cargar_json_seguro("funcionarios.json", [])
    errores = {}
    valores = {}
    if request.method == "POST":
        id_funcionario = (request.POST.get("id_funcionario") or "").strip()
        valores = {
            "id_funcionario": id_funcionario,
            "contacto": request.POST.get("contacto", ""),
            "item": request.POST.get("item", ""),
            "servicio": request.POST.get("servicio", ""),
            "fecha_actividad": request.POST.get("fecha_actividad", ""),
            "imagen_verificadora": request.POST.get("imagen_verificadora", ""),
        }
        if not id_funcionario:
            errores["id_funcionario"] = "Seleccione el funcionario que registra la actividad."
            messages.error(request, "Seleccione un funcionario para registrar la actividad.")
        else:
            nueva, errores_form = registrar_actividad_desde_formulario(
                id_funcionario, request.POST, request.FILES
            )
            errores.update(errores_form)
            if errores:
                messages.error(request, "Revise los campos obligatorios y el formato de la actividad.")
            elif nueva:
                messages.success(
                    request,
                    f"Actividad {nueva.get('id_actividad')} registrada con evidencia «{nueva.get('imagen_verificadora')}».",
                )
                return redirect("actividades_diarias")

    actividades = cargar_json_seguro("actividades.json", [])
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_funcionario = request.GET.get("funcionario", "").strip()
    if filtro_delegacion:
        actividades = [item for item in actividades if item.get("delegacion") == filtro_delegacion]
    if filtro_funcionario:
        actividades = [item for item in actividades if item.get("id_funcionario") == filtro_funcionario]

    items_por_funcionario = {
        item.get("id_funcionario"): [meta.get("item") for meta in item.get("items", [])]
        for item in funcionarios
    }
    contexto = {
        "actividades": actividades,
        "funcionarios": funcionarios,
        "delegaciones": DELEGACIONES_OFICIALES,
        "filtro_delegacion": filtro_delegacion,
        "filtro_funcionario": filtro_funcionario,
        "errores": errores,
        "valores": valores,
        "items_por_funcionario": items_por_funcionario,
        "fecha_hoy": date.today().strftime("%Y-%m-%d"),
        "total": len(actividades),
    }
    return render(request, "control_gestion/actividades.html", contexto)


def _funcionarios_opciones():
    return [
        {
            "id_funcionario": item.get("id_funcionario"),
            "nombre": item.get("nombre"),
            "delegacion": item.get("delegacion"),
        }
        for item in cargar_json_seguro("funcionarios.json", [])
    ]


def compromiso_form_view(request, id_compromiso=None):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    actual = None
    if id_compromiso:
        actual = next((item for item in compromisos if item.get("id_compromiso") == id_compromiso), None)
        if actual is None:
            messages.error(request, f"No existe el compromiso {id_compromiso}.")
            return redirect("tubo_trabajo")
    errores = {}
    valores = dict(actual or {})
    if request.method == "POST":
        valores = {
            "descripcion": (request.POST.get("descripcion") or "").strip(),
            "vecino": (request.POST.get("vecino") or "").strip(),
            "id_funcionario": (request.POST.get("id_funcionario") or "").strip(),
            "delegacion": (request.POST.get("delegacion") or "").strip(),
            "fecha_compromiso": (request.POST.get("fecha_compromiso") or "").strip(),
            "estado": (request.POST.get("estado") or "").strip().upper(),
        }
        if len(valores["descripcion"]) < 10:
            errores["descripcion"] = "Describa el compromiso (mínimo 10 caracteres)."
        if len(valores["vecino"]) < 3:
            errores["vecino"] = "Indique el vecino u organización (mínimo 3 caracteres)."
        funcionarios = {item["id_funcionario"]: item for item in _funcionarios_opciones()}
        if valores["id_funcionario"] not in funcionarios:
            errores["id_funcionario"] = "Seleccione el funcionario responsable."
        if valores["delegacion"] not in DELEGACIONES_OFICIALES:
            errores["delegacion"] = "Seleccione la delegación."
        if not _parse_fecha(valores["fecha_compromiso"]):
            errores["fecha_compromiso"] = "Ingrese una fecha de compromiso válida."
        if valores["estado"] not in ESTADOS_TUBO:
            errores["estado"] = "Seleccione un estado del tubo de trabajo."
        if errores:
            messages.error(request, "Hay errores de validación en el compromiso. Revise los campos marcados.")
        else:
            funcionario = funcionarios[valores["id_funcionario"]]
            payload = {
                "descripcion": valores["descripcion"],
                "vecino": valores["vecino"],
                "funcionario": funcionario["nombre"],
                "id_funcionario": valores["id_funcionario"],
                "delegacion": valores["delegacion"],
                "fecha_compromiso": valores["fecha_compromiso"],
                "estado": valores["estado"],
            }
            if actual:
                actual.update(payload)
                mensaje = f"Compromiso {id_compromiso} actualizado."
            else:
                nuevo_id = _siguiente_id("TUB-", compromisos, "id_compromiso")
                payload["id_compromiso"] = nuevo_id
                payload["fecha_ingreso"] = date.today().strftime("%Y-%m-%d")
                compromisos.insert(0, payload)
                mensaje = f"Compromiso {nuevo_id} registrado en la agenda colectiva."
            if guardar_json_seguro("tubo_trabajo.json", compromisos):
                messages.success(request, mensaje)
                return redirect("tubo_trabajo")
            messages.error(request, "No fue posible guardar tubo_trabajo.json.")
    contexto = {
        "valores": valores,
        "errores": errores,
        "estados": ESTADOS_TUBO,
        "delegaciones": DELEGACIONES_OFICIALES,
        "funcionarios": _funcionarios_opciones(),
        "modo_edicion": bool(actual),
        "id_compromiso": id_compromiso,
    }
    return render(request, "control_gestion/compromiso_form.html", contexto)


def compromiso_eliminar_view(request, id_compromiso):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    compromisos = cargar_json_seguro("tubo_trabajo.json", [])
    actual = next((item for item in compromisos if item.get("id_compromiso") == id_compromiso), None)
    if actual is None:
        messages.error(request, f"No existe el compromiso {id_compromiso}.")
        return redirect("tubo_trabajo")
    if request.method == "POST":
        restantes = [item for item in compromisos if item.get("id_compromiso") != id_compromiso]
        if guardar_json_seguro("tubo_trabajo.json", restantes):
            messages.success(request, f"Compromiso {id_compromiso} eliminado del mockup.")
        else:
            messages.error(request, "No fue posible actualizar tubo_trabajo.json.")
        return redirect("tubo_trabajo")
    return render(
        request,
        "control_gestion/compromiso_eliminar.html",
        {"compromiso": actual},
    )


def notificaciones_view(request):
    bloqueo = requerir_modulo(request, "notificaciones")
    if bloqueo:
        return bloqueo
    leidas = set(request.session.get("notificaciones_leidas") or [])
    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if accion == "leer_todas":
            ids = [item.get("id") for item in _notificaciones_base() if item.get("id")]
            request.session["notificaciones_leidas"] = ids
            messages.success(request, "Todas las notificaciones se marcaron como leídas.")
        else:
            notif_id = (request.POST.get("id") or "").strip()
            if notif_id:
                leidas.add(notif_id)
                request.session["notificaciones_leidas"] = list(leidas)
                messages.info(request, "Notificación marcada como leída.")
        return redirect("notificaciones")

    items = []
    for item in _notificaciones_base():
        copia = dict(item)
        copia["leida"] = copia.get("id") in leidas
        items.append(copia)
    contexto = {
        "notificaciones": items,
        "total": len(items),
        "total_pendientes": sum(1 for item in items if not item["leida"]),
    }
    return render(request, "control_gestion/notificaciones.html", contexto)
