"""Pantallas adicionales del mockup: agenda, actividades, compromisos y notificaciones."""

import calendar
from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_safe
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
    from control_gestion.reportes import ambito, perfil_acceso
    perfil, error = perfil_acceso(request, 'agenda')
    if error is not None:
        return error
    from cuentas.auth import puede_ver
    puede_mover_compromisos = puede_ver(perfil, 'compromisos')
    puede_mover_agenda = request.user.has_perm('control_gestion.change_eventoagenda')
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get("anio") or hoy.year)
        mes = int(request.GET.get("mes") or hoy.month)
        if not 2 <= anio <= 9998 or not 1 <= mes <= 12:
            raise ValueError
    except (TypeError, ValueError):
        anio, mes = hoy.year, hoy.month
    vista = (request.GET.get("vista") or "calendario").strip().lower()
    if vista not in {"calendario", "lista"}:
        vista = "calendario"

    eventos = []
    from core.busqueda import buscar
    q = request.GET.get('q', '').strip()
    eventos_agenda = ambito(EventoAgenda.objects.select_related('delegacion', 'responsable', 'organizacion'), perfil)
    eventos_agenda = buscar(eventos_agenda.filter(fecha__year=anio, fecha__month=mes), q,
                            ['codigo', 'titulo', 'tipo', 'lugar', 'responsable__nombre', 'delegacion__nombre', 'organizacion__nombre'])
    for item in eventos_agenda:
        organizacion = item.organizacion.nombre if item.organizacion_id else ""
        eventos.append(
            {
                "id": item.codigo,
                "titulo": item.titulo,
                "detalle": " · ".join(x for x in (f"{item.hora:%H:%M}", organizacion, item.lugar or "") if x),
                "organizacion": organizacion,
                "tipo": f"Organización · {item.tipo or 'Actividad'}" if organizacion else (item.tipo or "Agenda"),
                "fecha": item.fecha,
                "fecha_iso": item.fecha.strftime("%Y-%m-%d"),
                "delegacion": item.delegacion.nombre,
                "responsable": item.responsable.nombre if item.responsable_id else "",
                "origen": "agenda",
                "movible": puede_mover_agenda,
                "clase": "text-bg-success" if organizacion else "text-bg-primary",
            }
        )
    compromisos = ambito(queryset_compromisos(), perfil).filter(fecha_compromiso__year=anio, fecha_compromiso__month=mes)
    compromisos = buscar(compromisos, q, ['codigo', 'descripcion', 'funcionario__nombre', 'delegacion__nombre'])
    for item in compromisos:
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
                "movible": puede_mover_compromisos,
                "clase": "text-bg-warning",
            }
        )
    actividades = ambito(queryset_actividades(), perfil).filter(fecha_actividad__year=anio, fecha_actividad__month=mes)
    actividades = buscar(actividades, q, ['codigo', 'servicio', 'funcionario__nombre', 'delegacion__nombre'])
    for item in actividades:
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
                    "fecha_iso": date(anio, mes, dia).isoformat() if dia else "",
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
        "q": q,
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
    from control_gestion.reportes import perfil_acceso,ambito
    from core.busqueda import buscar
    perfil,error=perfil_acceso(request,'actividades')
    if error is not None: return error
    from control_gestion.evidencias import puede_validar
    funcionarios_qs=ambito(queryset_funcionarios(),perfil)
    if not puede_validar(perfil):
        # Solo jefaturas con revisión registran a nombre de su equipo; el resto, lo propio.
        funcionarios_qs = funcionarios_qs.filter(pk=perfil.funcionario_id) if perfil.funcionario_id else funcionarios_qs.none()
    funcionarios = [funcionario_base(item) for item in funcionarios_qs]
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
        if not id_funcionario or not funcionarios_qs.filter(codigo=id_funcionario).exists():
            errores["id_funcionario"] = "Seleccione el funcionario que registra la actividad."
            messages.error(request, "Seleccione un funcionario para registrar la actividad.")
        else:
            nueva, errores_form = registrar_actividad_desde_formulario(
                id_funcionario, request.POST, request.FILES, autor=request.user
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

    from control_gestion.trimestres import opciones_trimestres, seleccionar_trimestre
    actividades_qs = ambito(queryset_actividades(), perfil)
    periodo, actual = seleccionar_trimestre(request.GET.get('trimestre', ''))
    trimestres = opciones_trimestres(actividades_qs, periodo, actual)
    if periodo:
        actividades_qs = actividades_qs.filter(fecha_actividad__range=(periodo['fecha_inicio'], periodo['fecha_termino']))
    actividades_qs = buscar(actividades_qs,request.GET.get('q',''),['codigo','servicio','contacto','meta__nombre','funcionario__nombre','funcionario__rut','delegacion__nombre','codigo_verificador'])
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_funcionario = request.GET.get("funcionario", "").strip()
    if filtro_delegacion:
        actividades_qs = actividades_qs.filter(delegacion__nombre=filtro_delegacion)
    if filtro_funcionario:
        actividades_qs = actividades_qs.filter(funcionario__codigo=filtro_funcionario)
    from core.paginacion import paginar
    pagina_actividades,paginacion=paginar(request,actividades_qs)
    actividades = [actividad_a_dict(item) for item in pagina_actividades]
    items_por_funcionario = {
        item.get("id_funcionario"): [meta.get("item") for meta in item.get("items", [])] for item in funcionarios
    }
    contexto = {
        "actividades": actividades,
        "trimestres": trimestres,
        "trimestre_actual": actual,
        "trimestre_seleccionado": periodo['clave'] if periodo else 'todos',
        "funcionarios": funcionarios,
        "delegaciones": nombres_delegaciones(),
        "filtro_delegacion": filtro_delegacion,
        "filtro_funcionario": filtro_funcionario,
        "errores": errores,
        "valores": valores,
        "items_por_funcionario": items_por_funcionario,
        "fecha_hoy": timezone.localdate().strftime("%Y-%m-%d"),
        "total": paginacion["paginator"].count,
        **paginacion,
        "q": request.GET.get("q", ""),
    }
    from control_gestion.evidencias import puede_validar
    contexto["puede_validar_evidencia"] = puede_validar(perfil)
    contexto["funcionario_actual_codigo"] = perfil.funcionario.codigo if perfil.funcionario_id else ""
    return render(request, "control_gestion/actividades.html", contexto)


def _funcionarios_opciones():
    return [
        {"id_funcionario": item.codigo, "nombre": item.nombre, "delegacion": item.delegacion.nombre}
        for item in Funcionario.objects.select_related("delegacion").order_by("nombre")
    ]


@require_safe
def compromiso_detalle_view(request, id_compromiso):
    from control_gestion.reportes import ambito, perfil_acceso
    perfil, error = perfil_acceso(request, 'compromisos')
    if error is not None:
        return error
    compromiso = get_object_or_404(ambito(queryset_compromisos(), perfil), codigo=id_compromiso)
    desde_tubo = request.GET.get('vista') == 'tarjetas'
    volver = reverse('tubo_cartas' if desde_tubo else 'tubo_trabajo')
    filtros = request.GET.copy()
    for key in set(filtros) - {'q', 'delegacion', 'estado', 'page', 'per_page'}:
        filtros.pop(key, None)
    if filtros:
        volver += '?' + filtros.urlencode()
    return render(request, 'control_gestion/compromiso_detalle.html', {
        'compromiso': compromiso_a_dict(compromiso), 'volver': volver, 'desde_tubo': desde_tubo,
        'estado': compromiso.get_estado_display(), 'origen': compromiso.get_origen_display(),
        'evidencias': compromiso.evidencias.select_related('subido_por'),
    })


def evidencia_compromiso_view(request, pk):
    """Archivo de evidencia de un compromiso, con el mismo alcance por delegación que la ficha."""
    from django.http import FileResponse, Http404
    from control_gestion.models import EvidenciaCompromiso
    from control_gestion.reportes import ambito, perfil_acceso
    perfil, error = perfil_acceso(request, 'compromisos')
    if error is not None:
        return error
    e = EvidenciaCompromiso.objects.select_related('compromiso').filter(pk=pk).first()
    if e is None or not ambito(Compromiso.objects.filter(pk=e.compromiso_id), perfil).exists():
        raise Http404('Sin evidencia')
    nombre = e.archivo.name.lower()
    tipo = 'application/pdf' if nombre.endswith('.pdf') else ('image/png' if nombre.endswith('.png') else 'image/jpeg')
    r = FileResponse(e.archivo.open('rb'), content_type=tipo)
    r['X-Content-Type-Options'] = 'nosniff'
    r['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return r


def compromiso_form_view(request, id_compromiso=None):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    from control_gestion.reportes import perfil_acceso, ambito
    perfil, error = perfil_acceso(request, 'compromisos')
    if error is not None: return error
    disponibles = ambito(Funcionario.objects.select_related('delegacion'), perfil)
    actual = None
    if id_compromiso:
        actual = get_object_or_404(
            ambito(Compromiso.objects.select_related("vecino", "funcionario", "delegacion"), perfil),
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
        for campo in ('territorio','apoyo','observaciones'):
            valores[campo] = request.POST.get(campo,'').strip()
        valores['origen'] = request.POST.get('origen','EXT')
        if valores['origen'] not in ('INT','EXT'):
            errores['origen'] = 'Seleccione Interno o Externo.'
        for campo, limite in (('territorio',150),('apoyo',200),('observaciones',5000)):
            if len(valores[campo]) > limite:
                errores[campo] = f'El máximo permitido es {limite} caracteres.'
        if len(valores["descripcion"]) < 10:
            errores["descripcion"] = "Describa el compromiso (mínimo 10 caracteres)."
        # La marca «(ficticio)» que se muestra en pantalla no es parte del nombre guardado.
        valores["vecino"] = " ".join(valores["vecino"].replace("(ficticio)", "").split())
        mismo_vecino = bool(actual) and valores["vecino"].casefold() == actual.vecino.nombre.casefold()
        if len(valores["vecino"]) < 3:
            errores["vecino"] = "Indique el vecino u organización (mínimo 3 caracteres)."
        elif not mismo_vecino and ("(" in valores["vecino"] or ")" in valores["vecino"]):
            errores["vecino"] = "No use paréntesis en el nombre del vecino u organización."
        funcionario = disponibles.filter(codigo=valores["id_funcionario"]).first()
        if funcionario is None:
            errores["id_funcionario"] = "Seleccione el funcionario responsable."
        elif funcionario.delegacion_id:
            # La delegación es la del responsable: no se pide elegirla por separado.
            valores["delegacion"] = funcionario.delegacion.nombre
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
            if mismo_vecino:
                vecino = actual.vecino  # editar sin cambiar el vecino no crea uno nuevo
            else:
                vecino = (Vecino.objects.filter(nombre__iexact=valores["vecino"], delegacion=delegacion).first()
                          or Vecino.objects.create(nombre=valores["vecino"], delegacion=delegacion))
            if actual:
                estado_anterior, obs_anterior = actual.estado, actual.observaciones
                actual.descripcion = valores["descripcion"]
                actual.vecino = vecino
                actual.funcionario = funcionario
                actual.delegacion = delegacion
                actual.fecha_compromiso = fecha
                actual.estado = valores["estado"]
                for campo in ('origen','territorio','apoyo','observaciones'):
                    setattr(actual,campo,valores[campo])
                actual.save()
                if (estado_anterior, obs_anterior) != (actual.estado, actual.observaciones):
                    from control_gestion.models import CambioCompromiso
                    CambioCompromiso.objects.create(
                        compromiso=actual, autor=request.user, estado_anterior=estado_anterior,
                        estado_nuevo=actual.estado, observacion_anterior=obs_anterior,
                        observacion_nueva=actual.observaciones)
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
                    **{campo:valores[campo] for campo in ('origen','territorio','apoyo','observaciones')},
                )
                messages.success(request, f"Compromiso {codigo} registrado en la agenda colectiva.")
            # Vuelve a la vista desde la que se abrió (Tabla o Kanban/tubo de cartas).
            return redirect("tubo_cartas" if request.GET.get("vista") == "tarjetas" else "tubo_trabajo")
    contexto = {
        "valores": valores,
        "errores": errores,
        "estados": ESTADOS_TUBO,
        "delegaciones": nombres_delegaciones(),
        "funcionarios": [{"id_funcionario": f.codigo, "nombre": f.nombre, "delegacion": f.delegacion.nombre} for f in disponibles],
        "modo_edicion": bool(actual),
        "id_compromiso": id_compromiso,
    }
    return render(request, "control_gestion/compromiso_form.html", contexto)


def compromiso_eliminar_view(request, id_compromiso):
    bloqueo = requerir_modulo(request, "compromisos")
    if bloqueo:
        return bloqueo
    from control_gestion.reportes import perfil_acceso, ambito
    perfil,error=perfil_acceso(request,'compromisos')
    if error is not None:return error
    actual = get_object_or_404(
        ambito(Compromiso.objects.select_related("vecino", "funcionario", "delegacion"),perfil),
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
    perfil = getattr(request, "_perfil_siged", None)
    leidas = set(request.session.get("notificaciones_leidas") or [])
    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if accion == "leer_todas":
            ids = [item.get("id") for item in _notificaciones_base(perfil) if item.get("id")]
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
    for item in _notificaciones_base(perfil):
        copia = dict(item)
        copia["leida"] = copia.get("id") in leidas
        items.append(copia)
    contexto = {
        "notificaciones": items,
        "total": len(items),
        "total_pendientes": sum(1 for item in items if not item["leida"]),
    }
    return render(request, "control_gestion/notificaciones.html", contexto)
