"""Persistencia JSON local para el mockup (sin MySQL ni APIs de negocio)."""

import json
import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def ruta_data(nombre_archivo):
    return Path(settings.BASE_DIR) / "data" / nombre_archivo


def cargar_json_seguro(nombre_archivo, fallback=None):
    if fallback is None:
        fallback = []
    ruta = ruta_data(nombre_archivo)
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        logger.error("Archivo no encontrado: %s", ruta)
        return fallback
    except json.JSONDecodeError as err:
        logger.error("Error al decodificar JSON %s: %s", nombre_archivo, err)
        return fallback
    except OSError as err:
        logger.error("Error inesperado en %s: %s", nombre_archivo, err)
        return fallback


def guardar_json_seguro(nombre_archivo, datos):
    ruta = ruta_data(nombre_archivo)
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        return True
    except OSError as err:
        logger.error("Error al escribir %s: %s", nombre_archivo, err)
        return False


def cargar_parametros():
    datos = cargar_json_seguro("parametros.json", {})
    if not isinstance(datos, dict):
        datos = {}
    canales = datos.get("canales_ingreso") or [
        "ventanilla",
        "WhatsApp",
        "correo",
    ]
    return {
        "nombre_sistema": datos.get("nombre_sistema", "SIGED-SGR Delegaciones La Serena"),
        "comuna": datos.get("comuna", "La Serena"),
        "region": datos.get("region", "Región de Coquimbo"),
        "sla_verde_max_dias": int(datos.get("sla_verde_max_dias") or 3),
        "sla_amarillo_max_dias": int(datos.get("sla_amarillo_max_dias") or 5),
        "meta_tubo_porcentaje": int(datos.get("meta_tubo_porcentaje") or 80),
        "encuesta_habilitada": bool(datos.get("encuesta_habilitada", True)),
        "max_atenciones_mismo_usuario": int(datos.get("max_atenciones_mismo_usuario") or 3),
        "canales_ingreso": list(canales),
    }
