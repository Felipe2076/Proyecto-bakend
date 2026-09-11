import json
import logging
import re
from datetime import date
from pathlib import Path

import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render

from cuentas.auth import requerir_modulo
from cuentas.store import cargar_parametros
from cuentas.vocabulario import (
    AREAS_ESTRATEGICAS,
    CANALES_INGRESO,
    DELEGACIONES_OFICIALES,
    TIPOS_TICKET,
    normalizar_canal,
    normalizar_delegacion,
    normalizar_tipo,
)

logger = logging.getLogger(__name__)

TIPOS_ENTRADA = TIPOS_TICKET

FUNCIONARIOS_REFERENCIA = [
    "Patrulla Sector 3 (Seguridad)",
    "Gonzalo Pizarro (Seguridad)",
    "Cuadrilla Verde (Aseo y Alumbrado)",
    "Juan Carlos Pérez (Cuadrilla Aseo)",
    "Valeria Moraga (Áreas Verdes)",
    "Esteban Barraza (Obras Viales)",
    "Rodrigo Santander (Operaciones)",
    "DIDECO Soporte Social",
    "Marcela Cárdenas (Atención Vecinal)",
]


def cargar_requerimientos_json():
    assert settings.BASE_DIR is not None
    ruta_archivo = Path(settings.BASE_DIR) / "data" / "requerimientos.json"
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            if isinstance(datos, list):
                return datos
            return []
    except FileNotFoundError:
        logger.error("El archivo requerimientos.json no existe en %s", ruta_archivo)
        return []
    except json.JSONDecodeError as err:
        logger.error("Formato inválido en requerimientos.json: %s", err)
        return []
    except Exception as err:
        logger.error("Error inesperado al leer requerimientos.json: %s", err)
        return []


def guardar_requerimientos_json(lista_requerimientos):
    ruta_archivo = Path(str(settings.BASE_DIR)) / "data" / "requerimientos.json"
    try:
        with open(ruta_archivo, "w", encoding="utf-8") as archivo:
            json.dump(lista_requerimientos, archivo, ensure_ascii=False, indent=2)
        return True
    except Exception as err:
        logger.error("Error al escribir en requerimientos.json: %s", err)
        return False


def _sla_limites():
    params = cargar_parametros()
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
    if valores["delegacion"] not in DELEGACIONES_OFICIALES:
        errores["delegacion"] = "Seleccione la delegación (Centro, Rural, La Antena, La Pampa, Av. del Mar o Las Compañías)."
    canales = cargar_parametros().get("canales_ingreso") or CANALES_INGRESO
    if canal not in canales:
        errores["canal_ingreso"] = "El canal debe ser ventanilla, WhatsApp o correo."
    if valores["tipo_entrada"] not in TIPOS_ENTRADA:
        errores["tipo_entrada"] = "Tipifique el ticket: RECLAMO, SOLICITUD, CONSULTA, SUGERENCIA o FELICITACIÓN."
    if valores["area_tematica"] not in AREAS_ESTRATEGICAS:
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
    requerimientos_crudos = cargar_requerimientos_json()
    requerimientos_procesados = [asignar_semaforo(req) for req in requerimientos_crudos]
    total_casos = len(requerimientos_procesados)
    casos_resueltos = sum(
        1 for item in requerimientos_procesados if item.get("estado_proceso") == "Resuelto"
    )
    casos_criticos = sum(
        1 for item in requerimientos_procesados if item.get("semaforo_nivel") == "Rojo"
    )
    casos_en_proceso = sum(
        1 for item in requerimientos_procesados if item.get("estado_proceso") == "En Proceso"
    )
    casos_pendientes = sum(
        1 for item in requerimientos_procesados if item.get("estado_proceso") == "Pendiente"
    )
    clima_serena = obtener_clima_la_serena()
    contexto = {
        "total_casos": total_casos,
        "casos_resueltos": casos_resueltos,
        "casos_criticos": casos_criticos,
        "casos_en_proceso": casos_en_proceso,
        "casos_pendientes": casos_pendientes,
        "clima": clima_serena,
        "delegaciones": DELEGACIONES_OFICIALES,
    }
    return render(request, "requerimientos/inicio.html", contexto)


def lista_requerimientos_view(request):
    requerimientos_crudos = cargar_requerimientos_json()
    requerimientos = [asignar_semaforo(req) for req in requerimientos_crudos]
    filtro_delegacion = request.GET.get("delegacion", "").strip()
    filtro_semaforo = request.GET.get("semaforo", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()
    filtro_busqueda = request.GET.get("busqueda", "").strip().lower()
    if filtro_delegacion:
        requerimientos = [
            item
            for item in requerimientos
            if (item.get("delegacion") or "").lower() == filtro_delegacion.lower()
        ]
    if filtro_semaforo:
        requerimientos = [
            item
            for item in requerimientos
            if (item.get("semaforo_nivel") or "").lower() == filtro_semaforo.lower()
        ]
    if filtro_estado:
        requerimientos = [
            item
            for item in requerimientos
            if (item.get("estado_proceso") or "").lower() == filtro_estado.lower()
        ]
    if filtro_busqueda:
        requerimientos = [
            item
            for item in requerimientos
            if filtro_busqueda in (item.get("id_ticket") or "").lower()
            or filtro_busqueda in (item.get("vecino_nombre") or "").lower()
            or filtro_busqueda in (item.get("descripcion") or "").lower()
            or filtro_busqueda in (item.get("tipo_entrada") or "").lower()
            or filtro_busqueda in (item.get("area_tematica") or "").lower()
            or filtro_busqueda in (item.get("funcionario_asignado") or "").lower()
        ]
    filtros_activos = any(
        [filtro_delegacion, filtro_semaforo, filtro_estado, filtro_busqueda]
    )
    contexto = {
        "requerimientos": requerimientos,
        "total_resultados": len(requerimientos),
        "delegaciones": DELEGACIONES_OFICIALES,
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
    params = cargar_parametros()
    canales = params.get("canales_ingreso") or CANALES_INGRESO

    def contexto_formulario(valores, errores):
        return {
            "delegaciones": DELEGACIONES_OFICIALES,
            "areas": AREAS_ESTRATEGICAS,
            "canales": canales,
            "tipos": TIPOS_ENTRADA,
            "funcionarios": FUNCIONARIOS_REFERENCIA,
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
        requerimientos = cargar_requerimientos_json()
        nuevo_numero = 1001 + len(requerimientos)
        nuevo_id = f"TK-{nuevo_numero}"
        nuevo_ticket = {
            "id_ticket": nuevo_id,
            "vecino_nombre": valores["vecino_nombre"],
            "telefono_whatsapp": valores["telefono_whatsapp"],
            "email": valores["email"] if valores["email"] else "no-registra@serena.cl",
            "delegacion": valores["delegacion"],
            "canal_ingreso": valores["canal_ingreso"],
            "tipo_entrada": valores["tipo_entrada"],
            "area_tematica": valores["area_tematica"],
            "descripcion": valores["descripcion"],
            "fecha_ingreso": date.today().strftime("%Y-%m-%d"),
            "dias_transcurridos": 1,
            "funcionario_asignado": valores["funcionario_asignado"]
            if valores["funcionario_asignado"]
            else "Por Asignar (Jefatura Delegacional)",
            "estado_proceso": "Pendiente",
            "evaluacion_satisfaccion": None,
            "comentario_satisfaccion": "",
        }
        requerimientos.insert(0, nuevo_ticket)
        if guardar_requerimientos_json(requerimientos):
            messages.success(
                request,
                f"Requerimiento {nuevo_id} ingresado exitosamente para {valores['delegacion']}. "
                "Semáforo asignado: DÍA 1 (NORMAL).",
            )
            return redirect("lista_requerimientos")
        messages.error(request, "Hubo un error al guardar el requerimiento en el archivo JSON.")
        return render(request, "requerimientos/registro.html", contexto_formulario(valores, {}))
    return render(request, "requerimientos/registro.html", contexto_formulario({}, {}))


def detalle_requerimiento_view(request, ticket_id):
    requerimientos_crudos = cargar_requerimientos_json()
    indice_encontrado = None
    for idx, req in enumerate(requerimientos_crudos):
        if req.get("id_ticket", "").upper() == ticket_id.upper():
            indice_encontrado = idx
            break
    if indice_encontrado is None:
        messages.error(request, f"No se encontró el requerimiento con ID '{ticket_id}'.")
        return redirect("lista_requerimientos")
    if request.method == "POST":
        accion = (request.POST.get("accion") or "actualizar").strip()
        if accion == "encuesta":
            params = cargar_parametros()
            if not params.get("encuesta_habilitada", True):
                messages.error(request, "La encuesta de satisfacción está deshabilitada en parámetros.")
                return redirect("detalle_requerimiento", ticket_id=ticket_id)
            if requerimientos_crudos[indice_encontrado].get("estado_proceso") != "Resuelto":
                messages.error(request, "La encuesta solo se aplica cuando el ticket está en estado Resuelto.")
                return redirect("detalle_requerimiento", ticket_id=ticket_id)
            nota_raw = (request.POST.get("evaluacion_satisfaccion") or "").strip()
            comentario = (request.POST.get("comentario_satisfaccion") or "").strip()
            try:
                nota = int(nota_raw)
                if nota < 1 or nota > 5:
                    raise ValueError
            except (TypeError, ValueError):
                messages.error(request, "Seleccione una nota de satisfacción entre 1 y 5.")
                return redirect("detalle_requerimiento", ticket_id=ticket_id)
            requerimientos_crudos[indice_encontrado]["evaluacion_satisfaccion"] = nota
            requerimientos_crudos[indice_encontrado]["comentario_satisfaccion"] = comentario
            if guardar_requerimientos_json(requerimientos_crudos):
                messages.success(
                    request,
                    f"Encuesta registrada: {nota} de 5 para el ticket {ticket_id}.",
                )
            else:
                messages.error(request, "No fue posible guardar la encuesta en JSON.")
            return redirect("detalle_requerimiento", ticket_id=ticket_id)
        nuevo_estado = request.POST.get("estado_proceso", "").strip()
        nuevo_funcionario = request.POST.get("funcionario_asignado", "").strip()
        nuevos_dias_raw = request.POST.get("dias_transcurridos", "").strip()
        try:
            nuevos_dias = max(0, int(nuevos_dias_raw))
        except (ValueError, TypeError):
            nuevos_dias = requerimientos_crudos[indice_encontrado].get(
                "dias_transcurridos", 1
            )
        estados_validos = [
            "Pendiente",
            "En Proceso",
            "Cuello Botella Central",
            "Resuelto",
        ]
        if nuevo_estado not in estados_validos:
            messages.error(request, "Estado de proceso no válido.")
        else:
            requerimientos_crudos[indice_encontrado]["estado_proceso"] = nuevo_estado
            if nuevo_funcionario:
                requerimientos_crudos[indice_encontrado]["funcionario_asignado"] = (
                    nuevo_funcionario
                )
            requerimientos_crudos[indice_encontrado]["dias_transcurridos"] = nuevos_dias
            if guardar_requerimientos_json(requerimientos_crudos):
                messages.success(
                    request,
                    f"Ticket {ticket_id} actualizado: Estado → {nuevo_estado}, "
                    f"Días → {nuevos_dias}.",
                )
            else:
                messages.error(request, "Error al guardar los cambios en el archivo JSON.")
        return redirect("detalle_requerimiento", ticket_id=ticket_id)
    ticket_encontrado = asignar_semaforo(requerimientos_crudos[indice_encontrado])
    contexto = {
        "ticket": ticket_encontrado,
        "estados_validos": [
            "Pendiente",
            "En Proceso",
            "Cuello Botella Central",
            "Resuelto",
        ],
        "funcionarios": FUNCIONARIOS_REFERENCIA,
        "notas_encuesta": [1, 2, 3, 4, 5],
        "encuesta_habilitada": cargar_parametros().get("encuesta_habilitada", True),
    }
    return render(request, "requerimientos/detalle.html", contexto)


def encuestas_view(request):
    bloqueo = requerir_modulo(request, "encuestas")
    if bloqueo:
        return bloqueo
    requerimientos = [asignar_semaforo(item) for item in cargar_requerimientos_json()]
    resueltos = [item for item in requerimientos if item.get("estado_proceso") == "Resuelto"]
    con_nota = [item for item in resueltos if item.get("evaluacion_satisfaccion")]
    pendientes = [item for item in resueltos if not item.get("evaluacion_satisfaccion")]
    promedio = (
        round(
            sum(int(item.get("evaluacion_satisfaccion") or 0) for item in con_nota) / len(con_nota),
            1,
        )
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
        "encuesta_habilitada": cargar_parametros().get("encuesta_habilitada", True),
    }
    return render(request, "requerimientos/encuestas.html", contexto)
