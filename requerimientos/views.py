import logging
import re
from datetime import timedelta

import requests
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cuentas.auth import requerir_modulo
from cuentas.servicios import nombres_delegaciones, obtener_parametros
from cuentas.vocabulario import normalizar_canal, normalizar_delegacion, normalizar_tipo
from core.validaciones import MENSAJE_NOMBRE, motivo_rut_invalido, rut_canonico, validar_nombre
from requerimientos.consultas import (
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

ESTADOS_TICKET = list(Requerimiento.Estado.values)


def tipos_entrada():
    return opciones_tipos()


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


PAISES = ["Venezuela", "Perú", "Colombia", "Bolivia", "Haití", "Argentina", "Ecuador", "República Dominicana", "Cuba",
          "Paraguay", "Brasil", "Uruguay", "México", "España", "China", "Estados Unidos"]


def validar_formulario_requerimiento(post):
    valores = {
        "vecino_nombre": " ".join((post.get("vecino_nombre") or "").split()),
        "vecino_rut": (post.get("vecino_rut") or "").strip(),
        "telefono_whatsapp": (post.get("telefono_whatsapp") or "").strip(),
        "email": (post.get("email") or "").strip(),
        "delegacion": (post.get("delegacion") or "").strip(),
        "canal_ingreso": (post.get("canal_ingreso") or "").strip(),
        "tipo_entrada": (post.get("tipo_entrada") or "").strip(),
        "area_tematica": (post.get("area_tematica") or "").strip(),
        "descripcion": (post.get("descripcion") or "").strip(),
        "funcionario_asignado": (post.get("funcionario_asignado") or "").strip(),
        "es_extranjero": (post.get("es_extranjero") or "").strip().lower(),
        "nacionalidad": " ".join((post.get("nacionalidad") or "").split())[:60],
    }
    errores = {}
    if valores["es_extranjero"] not in ("si", "no"):
        errores["es_extranjero"] = "Indique si la persona es extranjera."
    elif valores["es_extranjero"] == "si" and len(valores["nacionalidad"]) < 3:
        errores["nacionalidad"] = "Indique el país de origen."
    if valores["es_extranjero"] != "si":
        valores["nacionalidad"] = ""
    if len(valores["vecino_nombre"]) < 5:
        errores["vecino_nombre"] = "Indique el nombre del ciudadano (mínimo 5 caracteres)."
    elif not validar_nombre(valores["vecino_nombre"]):
        errores["vecino_nombre"] = MENSAJE_NOMBRE
    if valores["vecino_rut"]:
        canonico = rut_canonico(valores["vecino_rut"])
        if canonico:
            valores["vecino_rut"] = canonico
        else:
            errores["vecino_rut"] = motivo_rut_invalido(valores["vecino_rut"])
    valores["canal_ingreso"] = normalizar_canal(valores["canal_ingreso"])
    telefono_obligatorio = valores["canal_ingreso"] != "correo"
    if valores["telefono_whatsapp"] or telefono_obligatorio:
        if not validar_telefono_chileno(valores["telefono_whatsapp"]):
            errores["telefono_whatsapp"] = "Ingrese un celular chileno válido, por ejemplo +56 9 1234 5678."
    valores["delegacion"] = normalizar_delegacion(valores["delegacion"])
    valores["tipo_entrada"] = normalizar_tipo(valores["tipo_entrada"])
    canal = valores["canal_ingreso"]
    if canal == "correo" and not valores["email"]:
        errores["email"] = "Si el ticket entra por correo, el e-mail del ciudadano es obligatorio."
    elif valores["email"] and not validar_email(valores["email"]):
        errores["email"] = "Revise el formato del correo (ejemplo: vecino@correo.cl)."
    if valores["delegacion"] not in nombres_delegaciones():
        errores["delegacion"] = "Seleccione una de las delegaciones de la lista."
    if canal not in opciones_canales():
        errores["canal_ingreso"] = "Seleccione un canal de ingreso de la lista."
    if valores["tipo_entrada"] not in tipos_entrada():
        errores["tipo_entrada"] = "Tipifique el ticket con una opción de la lista."
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


CLAVE_CLIMA = "siged:clima-la-serena"


def obtener_clima_la_serena():
    """Clima real de Open-Meteo, guardado 15 minutos en caché.

    Si el servicio no responde no se inventa un dato: se informa "no disponible"
    y se reintenta a los 5 minutos.
    """
    datos = cache.get(CLAVE_CLIMA)
    if datos is not None:
        return datos
    url_api = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=-29.90453&longitude=-71.24894&current_weather=true"
    )
    datos = {
        "temperatura": None,
        "velocidad_viento": None,
        "codigo_clima": None,
        "condicion": "Clima no disponible",
        "ciudad": "La Serena, Región de Coquimbo",
        "estado_conexion": "Sin conexión con el servicio de clima",
        "conectado": False,
    }
    try:
        respuesta = requests.get(url_api, timeout=2)
        if respuesta.status_code == 200:
            current = respuesta.json().get("current_weather") or {}
            codigo = current.get("weathercode", 0)
            if codigo == 0:
                condicion_str = "Cielo despejado"
            elif codigo in [1, 2, 3]:
                condicion_str = "Parcialmente nublado"
            elif codigo in [45, 48]:
                condicion_str = "Neblina costera"
            elif codigo in [51, 53, 55, 61, 63, 65]:
                condicion_str = "Llovizna o lluvia ligera"
            else:
                condicion_str = "Nublado"
            datos.update(
                {
                    "temperatura": round(float(current["temperature"]), 1),
                    "velocidad_viento": round(float(current["windspeed"]), 1),
                    "codigo_clima": codigo,
                    "condicion": condicion_str,
                    "estado_conexion": "Open-Meteo, actualizado cada 15 minutos",
                    "conectado": True,
                }
            )
    except (requests.RequestException, ValueError, KeyError, TypeError) as err:
        logger.warning("Fallo al conectar con la API de clima de La Serena: %s", err)
    cache.set(CLAVE_CLIMA, datos, 900 if datos["conectado"] else 300)
    return datos


def inicio_view(request):
    from control_gestion.panel_personal import construir_panel_personal, perfil_de_request

    panel = construir_panel_personal(perfil_de_request(request))
    contexto = {
        "panel": panel,
        "clima": obtener_clima_la_serena(),
        "delegaciones": panel["delegaciones"],
    }
    return render(request, "requerimientos/inicio.html", contexto)


def nuevo_requerimiento_view(request):
    bloqueo = requerir_modulo(request, "requerimientos")
    if bloqueo:
        return bloqueo

    def contexto_formulario(valores, errores):
        return {
            "delegaciones": nombres_delegaciones(),
            "areas": opciones_areas(),
            "canales": opciones_canales(),
            "tipos": tipos_entrada(),
            "funcionarios": opciones_funcionarios(),
            "paises": PAISES,
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
            f"Requerimiento {nuevo.codigo} ingresado para {valores['delegacion']}. "
            "Su plazo de gestión comienza hoy.",
        )
        return redirect("lista_requerimientos")
    # Valores automáticos: RUT desde el buscador y la delegación del propio funcionario.
    from control_gestion.kanban import perfil_actual
    perfil = perfil_actual(request)
    inicial = {"vecino_rut": (request.GET.get("vecino_rut") or "")[:12]}
    if perfil is not None and perfil.delegacion_id and perfil.rol.codigo != "superusuario":
        inicial["delegacion"] = perfil.delegacion.nombre
    return render(request, "requerimientos/registro.html", contexto_formulario(inicial, {}))


def detalle_requerimiento_view(request, ticket_id):
    from control_gestion.kanban import tickets_visibles
    from control_gestion.reportes import perfil_acceso
    from requerimientos.encuesta_vecinal import enlace_encuesta, guardar_respuesta
    perfil, error = perfil_acceso(request, 'requerimientos')
    if error is not None:
        return error
    requerimiento = get_object_or_404(tickets_visibles(perfil), codigo__iexact=ticket_id)
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
            if len(comentario) > 500:
                messages.error(request, 'El comentario puede tener hasta 500 caracteres.')
            elif guardar_respuesta(requerimiento.pk, nota, comentario):
                messages.success(request, f'Encuesta registrada: {nota} de 5 para el ticket {requerimiento.codigo}.')
            else:
                messages.error(request, 'La encuesta ya fue respondida o el ticket dejó de estar resuelto.')
            return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)

        nuevo_estado = request.POST.get("estado_proceso", "").strip()
        nuevo_funcionario = request.POST.get("funcionario_asignado", "").strip()
        if nuevo_estado not in ESTADOS_TICKET:
            messages.error(request, "Estado de proceso no válido.")
            return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)
        from cuentas.servicios import funcionario_por_texto

        validos = opciones_funcionarios(delegacion=requerimiento.delegacion)
        actual = requerimiento.funcionario.nombre if requerimiento.funcionario_id else ""
        if nuevo_funcionario and nuevo_funcionario not in validos and nuevo_funcionario != actual:
            messages.error(request, "Elija un funcionario activo de la delegación del ticket.")
            return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)
        requerimiento.estado = nuevo_estado
        requerimiento.funcionario = funcionario_por_texto(nuevo_funcionario) if nuevo_funcionario else None
        requerimiento.asignado_a = requerimiento.funcionario.nombre if requerimiento.funcionario else ""
        # La fecha de ingreso no se edita: el plazo del SLA se mide desde el ingreso real.
        requerimiento.save(update_fields=['estado', 'asignado_a', 'funcionario'])
        asignado = requerimiento.asignado_a or "sin asignar"
        messages.success(request, f"Ticket {requerimiento.codigo} actualizado: {nuevo_estado}, {asignado}.")
        return redirect("detalle_requerimiento", ticket_id=requerimiento.codigo)

    ticket = asignar_semaforo(ticket_a_dict(requerimiento))
    contexto = {
        "ticket": ticket,
        "ficha_tecnica": requerimiento,
        "estados_validos": ESTADOS_TICKET,
        "funcionarios": opciones_funcionarios(ticket.get("funcionario_asignado"), requerimiento.delegacion),
        "enlace_vecinal": enlace_encuesta(request, requerimiento) if (
            requerimiento.estado == Requerimiento.Estado.RESUELTO
            and requerimiento.evaluacion_satisfaccion is None
            and obtener_parametros().get('encuesta_habilitada', True)
        ) else '',
        "notas_encuesta": [1, 2, 3, 4, 5],
        "encuesta_habilitada": obtener_parametros().get("encuesta_habilitada", True),
        "evidencias": requerimiento.evidencias.select_related("subido_por"),
    }
    return render(request, "requerimientos/detalle.html", contexto)


def encuestas_view(request):
    bloqueo = requerir_modulo(request, "encuestas")
    if bloqueo:
        return bloqueo
    from control_gestion.kanban import tickets_visibles
    from control_gestion.reportes import perfil_acceso
    perfil, error = perfil_acceso(request, 'encuestas')
    if error is not None:
        return error
    requerimientos = _tickets_con_semaforo(tickets_visibles(perfil).filter(estado=Requerimiento.Estado.RESUELTO))
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
