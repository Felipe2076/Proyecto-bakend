"""Pantallas adicionales del mockup: agenda, actividades, compromisos y notificaciones."""

import calendar
from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.context_processors import _notificaciones_base
from control_gestion.consultas import (
    actividad_a_dict,
    compromiso_a_dict,
    funcionario_base,
    queryset_actividades,
    queryset_compromisos,
    queryset_funcionarios,
    registrar_actividad_desde_formulario,
)
from control_gestion.models import Compromiso, EventoAgenda
from control_gestion.views import ESTADOS_TUBO
from cuentas.auth import requerir_modulo
from cuentas.models import Delegacion, Funcionario
from cuentas.servicios import nombres_delegaciones, siguiente_codigo
from requerimientos.models import Vecino


def _parse_fecha(valor):
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def agenda_view(request):
    bloqueo = requerir_modulo(request, "agenda")
    if bloqueo:
        return bloqueo
    hoy = timezone.localdate()
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

    eventos = []
    eventos_agenda = EventoAgenda.objects.select_related("delegacion", "responsable")
    for item in eventos_agenda:
        eventos.append(
            {
                "id": item.codigo,
                "titulo": item.titulo,
                "detalle": f"{item.hora:%H:%M} · {item.lugar or ''}".strip(" ·"),
                "tipo": item.tipo or "Agenda",
                "fecha": item.fecha,
                "fecha_iso": item.fecha.strftime("%Y-%m-%d"),
                "delegacion": item.delegacion.nombre,
                "responsable": item.responsable.nombre if item.responsable_id else "",
                "origen": "agenda",
                "clase": "text-bg-primary",
            }
        )
    for item in queryset_compromisos():
        eventos.append(
            {
                "id": item.codigo,
                "titulo": item.descripcion,
                "detalle": f"{item.vecino.nombre_mostrado} · {item.estado}",
                "tipo": "Compromiso ciudadano",
                "fecha": item.fecha_compromiso,
                "fecha_iso": item.fecha_compromiso.strftime("%Y-%m-%d"),
                "delegacion": item.delegacion.nombre,
                "responsable": item.funcionario.nombre_mostrado,
                "origen": "compromiso",
                "clase": "text-bg-warning",
            }
        )
    for item in queryset_actividades():
        eventos.append(
            {
                "id": item.codigo,
                "titulo": item.servicio,
                "detalle": f"{item.contacto} · {item.codigo_verificador}",
                "tipo": "Actividad diaria",
                "fecha": item.fecha_actividad,
                "fecha_iso": item.fecha_actividad.strftime("%Y-%m-%d"),
                "delegacion": item.delegacion.nombre,
                "responsable": item.funcionario.nombre_mostrado,
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
    contexto = {
        "vista": vista,
        "anio": anio,
        "mes": mes,
        "nombre_mes": meses_es[mes],
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
    return render(request, "control_gestion/agenda.html", contexto)


def actividades_diarias_view(request):
    bloqueo = requerir_modulo(request, "actividades")
    if bloqueo:
        return bloqueo
    funcionarios = [funcionario_base(item) for item in queryset_funcionarios()]
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

    actividades_qs = queryset_actividades()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_funcionario = request.GET.get("funcionario", "").strip()
    if filtro_delegacion:
        actividades_qs = actividades_qs.filter(delegacion__nombre=filtro_delegacion)
    if filtro_funcionario:
        actividades_qs = actividades_qs.filter(funcionario__codigo=filtro_funcionario)
    actividades = [actividad_a_dict(item) for item in actividades_qs]
    items_por_funcionario = {
        item.get("id_funcionario"): [meta.get("item") for meta in item.get("items", [])] for item in funcionarios
    }
    contexto = {
        "actividades": actividades,
        "funcionarios": funcionarios,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "filtro_funcionario": filtro_funcionario,
        "errores": errores,
        "valores": valores,
        "items_por_funcionario": items_por_funcionario,
        "fecha_hoy": timezone.localdate().strftime("%Y-%m-%d"),
        "total": len(actividades),
    }
    return render(request, "control_gestion/actividades.html", contexto)


def _funcionarios_opciones():
    return [
        {"id_funcionario": item.codigo, "nombre": item.nombre, "delegacion": item.delegacion.nombre}
        for item in Funcionario.objects.select_related("delegacion").order_by("nombre")
    ]


def compromiso_form_view(request, id_compromiso=None):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    actual = None
    if id_compromiso:
        actual = get_object_or_404(
            Compromiso.objects.select_related("vecino", "funcionario", "delegacion"),
            codigo=id_compromiso,
        )
    errores = {}
    valores = compromiso_a_dict(actual) if actual else {}
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
        funcionario = Funcionario.objects.filter(codigo=valores["id_funcionario"]).first()
        if funcionario is None:
            errores["id_funcionario"] = "Seleccione el funcionario responsable."
        if valores["delegacion"] not in nombres_delegaciones():
            errores["delegacion"] = "Seleccione la delegación."
        fecha = _parse_fecha(valores["fecha_compromiso"])
        if not fecha:
            errores["fecha_compromiso"] = "Ingrese una fecha de compromiso válida."
        if valores["estado"] not in ESTADOS_TUBO:
            errores["estado"] = "Seleccione un estado del tubo de trabajo."
        if errores:
            messages.error(request, "Hay errores de validación en el compromiso. Revise los campos marcados.")
        else:
            delegacion, _ = Delegacion.objects.get_or_create(
                nombre=valores["delegacion"], defaults={"comuna": "La Serena"}
            )
            vecino = Vecino.objects.filter(nombre=valores["vecino"]).first()
            if vecino is None:
                vecino = Vecino.objects.create(nombre=valores["vecino"], delegacion=delegacion)
            if actual:
                actual.descripcion = valores["descripcion"]
                actual.vecino = vecino
                actual.funcionario = funcionario
                actual.delegacion = delegacion
                actual.fecha_compromiso = fecha
                actual.estado = valores["estado"]
                actual.save()
                messages.success(request, f"Compromiso {id_compromiso} actualizado.")
            else:
                codigo = siguiente_codigo(Compromiso, "codigo", "TUB-", 3)
                Compromiso.objects.create(
                    codigo=codigo,
                    descripcion=valores["descripcion"],
                    vecino=vecino,
                    funcionario=funcionario,
                    delegacion=delegacion,
                    fecha_ingreso=timezone.localdate(),
                    fecha_compromiso=fecha,
                    estado=valores["estado"],
                )
                messages.success(request, f"Compromiso {codigo} registrado en la agenda colectiva.")
            return redirect("tubo_trabajo")
    contexto = {
        "valores": valores,
        "errores": errores,
        "estados": ESTADOS_TUBO,
        "delegaciones": nombres_delegaciones(),
        "funcionarios": _funcionarios_opciones(),
        "modo_edicion": bool(actual),
        "id_compromiso": id_compromiso,
    }
    return render(request, "control_gestion/compromiso_form.html", contexto)


def compromiso_eliminar_view(request, id_compromiso):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    actual = get_object_or_404(
        Compromiso.objects.select_related("vecino", "funcionario", "delegacion"),
        codigo=id_compromiso,
    )
    if request.method == "POST":
        actual.delete()
        messages.success(request, f"Compromiso {id_compromiso} eliminado.")
        return redirect("tubo_trabajo")
    return render(
        request,
        "control_gestion/compromiso_eliminar.html",
        {"compromiso": compromiso_a_dict(actual)},
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
