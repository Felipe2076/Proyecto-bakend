import logging
import re
from datetime import timedelta

import requests
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cuentas.auth import requerir_modulo
from cuentas.servicios import nombres_delegaciones, obtener_parametros
from cuentas.vocabulario import normalizar_canal, normalizar_delegacion, normalizar_tipo
from requerimientos.consultas import (
    FUNCIONARIOS_REFERENCIA,
    crear_requerimiento,
    opciones_areas,
    opciones_canales,
    opciones_funcionarios,
    opciones_tipos,
    queryset_requerimientos,
    ticket_a_dict,
)
from requerimientos.models import Requerimiento

logger = logging.getLogger(__name__)

TIPOS_ENTRADA = opciones_tipos()


def _sla_limites():
    params = obtener_parametros()
    return params["sla_verde_max_dias"], params["sla_amarillo_max_dias"]


def validar_telefono_chileno(telefono):
    digitos = re.sub(r"\D", "", telefono or "")
    if digitos.startswith("56"):
        digitos = digitos[2:]
    return bool(re.fullmatch(r"9\d{8}", digitos))


def validar_email(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def validar_formulario_requerimiento(post):
    valores = {
        "vecino_nombre": (post.get("vecino_nombre") or "").strip(),
        "telefono_whatsapp": (post.get("telefono_whatsapp") or "").strip(),
        "email": (post.get("email") or "").strip(),
        "delegacion": (post.get("delegacion") or "").strip(),
        "canal_ingreso": (post.get("canal_ingreso") or "").strip(),
        "tipo_entrada": (post.get("tipo_entrada") or "").strip(),
        "area_tematica": (post.get("area_tematica") or "").strip(),
        "descripcion": (post.get("descripcion") or "").strip(),
        "funcionario_asignado": (post.get("funcionario_asignado") or "").strip(),
    }
    errores = {}
    if len(valores["vecino_nombre"]) < 5:
        errores["vecino_nombre"] = "Indique el nombre del ciudadano (mínimo 5 caracteres)."
    if not validar_telefono_chileno(valores["telefono_whatsapp"]):
        errores["telefono_whatsapp"] = "Ingrese un celular chileno válido, por ejemplo +56 9 1234 5678."
    valores["canal_ingreso"] = normalizar_canal(valores["canal_ingreso"])
    valores["delegacion"] = normalizar_delegacion(valores["delegacion"])
    valores["tipo_entrada"] = normalizar_tipo(valores["tipo_entrada"])
    canal = valores["canal_ingreso"]
    if canal == "correo" and not valores["email"]:
        errores["email"] = "Si el ticket entra por correo, el e-mail del ciudadano es obligatorio."
    elif valores["email"] and not validar_email(valores["email"]):
        errores["email"] = "Revise el formato del correo (ejemplo: vecino@correo.cl)."
    if valores["delegacion"] not in nombres_delegaciones():
        errores["delegacion"] = (
            "Seleccione la delegación (Centro, Rural, La Antena, La Pampa, Av. del Mar o Las Compañías)."
        )
    if canal not in opciones_canales():
        errores["canal_ingreso"] = "El canal debe ser ventanilla, WhatsApp o correo."
    if valores["tipo_entrada"] not in TIPOS_ENTRADA:
        errores["tipo_entrada"] = "Tipifique el ticket: RECLAMO, SOLICITUD, CONSULTA, SUGERENCIA o FELICITACIÓN."
    if valores["area_tematica"] not in opciones_areas():
        errores["area_tematica"] = "Seleccione el área temática."
    if len(valores["descripcion"]) < 15:
        errores["descripcion"] = "Cuente qué pasó y dónde, en al menos 15 caracteres."
    return valores, errores


def asignar_semaforo(item, sla_verde=None, sla_amarillo=None):
    if sla_verde is None or sla_amarillo is None:
        sla_verde, sla_amarillo = _sla_limites()
    dias = item.get("dias_transcurridos", 0)
    try:
        dias = int(dias)
    except (ValueError, TypeError):
        dias = 0
    if dias <= sla_verde:
        nivel = "Verde"
        badge_class = "bg-success text-white"
        texto = f"DÍA 1-{sla_verde} (NORMAL)"
        alerta_texto = "Dentro del plazo estándar"
    elif dias <= sla_amarillo:
        nivel = "Amarillo"
        badge_class = "bg-warning text-dark"
        texto = f"DÍA {dias} (ALERTA)"
        alerta_texto = "Próximo a vencer / Alerta de gestión"
    else:
        nivel = "Rojo"
        badge_class = "bg-danger text-white"
        texto = f"DÍA {dias} (CRÍTICO)"
        alerta_texto = "Excedido / Cuello de botella"
    item_copia = dict(item)
    item_copia["dias_transcurridos"] = dias
    item_copia["semaforo_nivel"] = nivel
    item_copia["semaforo_clase"] = badge_class
    item_copia["semaforo_texto"] = texto
    item_copia["alerta_texto"] = alerta_texto
    return item_copia


def _tickets_con_semaforo(qs=None):
    if qs is None:
        qs = queryset_requerimientos()
    sla_verde, sla_amarillo = _sla_limites()
    return [asignar_semaforo(ticket_a_dict(req), sla_verde, sla_amarillo) for req in qs]


def obtener_clima_la_serena():
    url_api = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=-29.90453&longitude=-71.24894&current_weather=true"
    )
    datos_clima = {
        "temperatura": 18.5,
        "velocidad_viento": 14.2,
        "codigo_clima": 1,
        "condicion": "Despejado / Brisa Costera Serenense",
        "ciudad": "La Serena, Región de Coquimbo",
        "estado_conexion": "Estimación Local (Fallback)",
        "conectado": False,
    }
    try:
        respuesta = requests.get(url_api, timeout=3.5)
        if respuesta.status_code == 200:
            payload = respuesta.json()
            current = payload.get("current_weather", {})
            temp = current.get("temperature", 18.5)
            viento = current.get("windspeed", 14.2)
            codigo = current.get("weathercode", 0)
            if codigo == 0:
                condicion_str = "Cielo Despejado y Soleado"
            elif codigo in [1, 2, 3]:
                condicion_str = "Parcialmente Nublado / Camanchaca"
            elif codigo in [45, 48]:
                condicion_str = "Neblina Matinal Costera"
            elif codigo in [51, 53, 55, 61, 63, 65]:
                condicion_str = "Llovizna / Precipitación Ligera"
            else:
                condicion_str = "Nublado con Viento Costero"
            datos_clima.update(
                {
                    "temperatura": round(float(temp), 1),
                    "velocidad_viento": round(float(viento), 1),
                    "codigo_clima": codigo,
                    "condicion": condicion_str,
                    "estado_conexion": "API en Vivo (Open-Meteo)",
                    "conectado": True,
                }
            )
    except (requests.RequestException, ValueError, KeyError) as err:
        logger.warning("Fallo al conectar con la API de clima de La Serena: %s", err)
    return datos_clima


def inicio_view(request):
    from control_gestion.panel_personal import construir_panel_personal, perfil_de_request

    panel = construir_panel_personal(perfil_de_request(request))
    contexto = {
        "panel": panel,
        "clima": obtener_clima_la_serena(),
        "delegaciones": panel["delegaciones"],
    }
    return render(request, "requerimientos/inicio.html", contexto)


def lista_requerimientos_view(request):
    qs = queryset_requerimientos()
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_semaforo = request.GET.get("semaforo", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()
    filtro_busqueda = request.GET.get("busqueda", "").strip()
    if filtro_delegacion:
        qs = qs.filter(delegacion__nombre__iexact=filtro_delegacion)
    if filtro_estado:
        qs = qs.filter(estado__iexact=filtro_estado)
    if filtro_busqueda:
        qs = qs.filter(
            Q(codigo__icontains=filtro_busqueda)
            | Q(vecino__nombre__icontains=filtro_busqueda)
            | Q(descripcion__icontains=filtro_busqueda)
            | Q(tipo_gestion__nombre__icontains=filtro_busqueda)
            | Q(area__nombre__icontains=filtro_busqueda)
            | Q(asignado_a__icontains=filtro_busqueda)
            | Q(funcionario__nombre__icontains=filtro_busqueda)
        ).distinct()
    requerimientos = _tickets_con_semaforo(qs)
    if filtro_semaforo:
        requerimientos = [
            item for item in requerimientos if (item.get("semaforo_nivel") or "").lower() == filtro_semaforo.lower()
        ]
    filtros_activos = any([filtro_delegacion, filtro_semaforo, filtro_estado, filtro_busqueda])
    contexto = {
        "requerimientos": requerimientos,
        "total_resultados": len(requerimientos),
        "delegaciones": nombres_delegaciones(),
        "niveles_semaforo": ["Verde", "Amarillo", "Rojo"],
        "estados_proceso": ["Pendiente", "En Proceso", "Cuello Botella Central", "Resuelto"],
        "filtro_delegacion": filtro_delegacion,
        "filtro_semaforo": filtro_semaforo,
        "filtro_estado": filtro_estado,
        "filtro_busqueda": filtro_busqueda,
        "filtros_activos": filtros_activos,
    }
    return render(request, "requerimientos/lista.html", contexto)


def nuevo_requerimiento_view(request):
    bloqueo = requerir_modulo(request, "requerimientos")
    if bloqueo:
        return bloqueo

    def contexto_formulario(valores, errores):
        return {
            "delegaciones": nombres_delegaciones(),
            "areas": opciones_areas(),
            "canales": opciones_canales(),
            "tipos": TIPOS_ENTRADA,
            "funcionarios": opciones_funcionarios(),
            "valores": valores,
            "errores": errores,
        }

    if request.method == "POST":
        valores, errores = validar_formulario_requerimiento(request.POST)
        if errores:
            messages.error(
                request,
                "Por favor corrija los campos obligatorios o con formato inválido. Los mensajes aparecen bajo cada campo.",
            )
            return render(request, "requerimientos/registro.html", contexto_formulario(valores, errores))
        nuevo = crear_requerimiento(valores)
        messages.success(
            request,
            f"Requerimiento {nuevo.codigo} ingresado exitosamente para {valores['delegacion']}. "
            f"Semáforo asignado: DÍA {nuevo.dias_transcurridos} (NORMAL).",
        )
        return redirect("lista_requerimientos")
    return render(request, "requerimientos/registro.html", contexto_formulario({}, {}))


def detalle_requerimiento_view(request, ticket_id):
    requerimiento = get_object_or_404(queryset_requerimientos(), codigo__iexact=ticket_id)
    if request.method == "POST":
        accion = (request.POST.get("accion") or "actualizar").strip()
        if accion == "encuesta":
            params = obtener_parametros()
            if not params.get("encuesta_habilitada", True):
                messages.error(request, "La encuesta de satisfacción está deshabilitada en parámetros.")
                return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)
            if requerimiento.estado != Requerimiento.Estado.RESUELTO:
                messages.error(request, "La encuesta solo se aplica cuando el ticket está en estado Resuelto.")
                return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)
            nota_raw = (request.POST.get("evaluacion_satisfaccion") or "").strip()
            comentario = (request.POST.get("comentario_satisfaccion") or "").strip()
            try:
                nota = int(nota_raw)
                if nota < 1 or nota > 5:
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, "Seleccione una nota de satisfacción entre 1 y 5.")
                return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)
            requerimiento.evaluacion_satisfaccion = nota
            requerimiento.comentario_satisfaccion = comentario
            requerimiento.save(update_fields=["evaluacion_satisfaccion", "comentario_satisfaccion"])
            messages.success(request, f"Encuesta registrada: {nota} de 5 para el ticket {requerimiento.codigo}.")
            return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)

        nuevo_estado = request.POST.get("estado_proceso", "").strip()
        nuevo_funcionario = request.POST.get("funcionario_asignado", "").strip()
        nuevos_dias_raw = request.POST.get("dias_transcurridos", "").strip()
        try:
            nuevos_dias = max(0, int(nuevos_dias_raw))
        except (ValueError, TypeError):
            nuevos_dias = requerimiento.dias_transcurridos
        estados_validos = [
            "Pendiente",
            "En Proceso",
            "Cuello Botella Central",
            "Resuelto",
        ]
        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado de proceso no válido.")
        else:
            requerimiento.estado = nuevo_estado
            if nuevo_funcionario:
                requerimiento.asignado_a = nuevo_funcionario
                requerimiento.funcionario = None
                from cuentas.servicios import funcionario_por_texto

                requerimiento.funcionario = funcionario_por_texto(nuevo_funcionario)
            requerimiento.fecha_ingreso = timezone.localdate() - timedelta(days=nuevos_dias)
            requerimiento.save()
            messages.success(
                request,
                f"Ticket {requerimiento.codigo} actualizado: Estado → {nuevo_estado}, Días → {nuevos_dias}.",
            )
        return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)

    ticket = asignar_semaforo(ticket_a_dict(requerimiento))
    contexto = {
        "ticket": ticket,
        "estados_validos": [
            "Pendiente",
            "En Proceso",
            "Cuello Botella Central",
            "Resuelto",
        ],
        "funcionarios": opciones_funcionarios(ticket.get("funcionario_asignado")),
        "notas_encuesta": [1, 2, 3, 4, 5],
        "encuesta_habilitada": obtener_parametros().get("encuesta_habilitada", True),
    }
    return render(request, "requerimientos/detalle.html", contexto)


def encuestas_view(request):
    bloqueo = requerir_modulo(request, "encuestas")
    if bloqueo:
        return bloqueo
    requerimientos = _tickets_con_semaforo()
    resueltos = [item for item in requerimientos if item.get("estado_proceso") == "Resuelto"]
    con_nota = [item for item in resueltos if item.get("evaluacion_satisfaccion")]
    pendientes = [item for item in resueltos if not item.get("evaluacion_satisfaccion")]
    promedio = (
        round(sum(int(item.get("evaluacion_satisfaccion") or 0) for item in con_nota) / len(con_nota), 1)
        if con_nota
        else 0.0
    )
    contexto = {
        "resueltos": resueltos,
        "con_nota": con_nota,
        "pendientes": pendientes,
        "promedio": promedio,
        "total_resueltos": len(resueltos),
        "total_con_nota": len(con_nota),
        "total_pendientes": len(pendientes),
        "encuesta_habilitada": obtener_parametros().get("encuesta_habilitada", True),
    }
    return render(request, "requerimientos/encuestas.html", contexto)
