"""Formato JSON único para los errores de la API v2."""
import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

log = logging.getLogger(__name__)


def manejar_error(exc, context):
    respuesta = exception_handler(exc, context)
    if respuesta is None:
        # Error no previsto: 500 sin exponer detalles internos; el detalle queda en el log.
        log.exception("Error no controlado en la API v2")
        return Response({"error": "Internal Server Error", "detalle": "Error interno del servidor."}, status=500)
    respuesta.data = {"error": respuesta.status_text, "detalle": respuesta.data}
    return respuesta
