"""Portada pública (/) de SIGED-SGR.

- Visitante anónimo: ve la página principal con presentación del sistema.
- Usuario con sesión: se delega al tablero de inicio de siempre (inicio_view).
"""

import logging

from django.db import DatabaseError
from django.shortcuts import render

from cuentas.vocabulario import DELEGACIONES_OFICIALES
from requerimientos.views import cargar_requerimientos_json, inicio_view

logger = logging.getLogger(__name__)


def _estadisticas_publicas():
    """Cifras agregadas (sin datos personales). ORM primero; JSON local como respaldo."""
    stats = {"delegaciones": len(DELEGACIONES_OFICIALES), "total": 0, "resueltos": 0, "fuente": "datos locales"}
    try:
        from cuentas.models import Delegacion
        from requerimientos.models import Requerimiento

        stats["delegaciones"] = Delegacion.objects.count() or len(DELEGACIONES_OFICIALES)
        stats["total"] = Requerimiento.objects.count()
        stats["resueltos"] = Requerimiento.objects.filter(estado=Requerimiento.Estado.RESUELTO).count()
        stats["fuente"] = "base de datos municipal"
    except DatabaseError as err:
        logger.warning("Portada: sin acceso a la base de datos, se usa JSON local (%s)", err)
        try:
            tickets = cargar_requerimientos_json()
            stats["total"] = len(tickets)
            stats["resueltos"] = sum(1 for t in tickets if t.get("estado_proceso") == "Resuelto")
        except Exception:  # noqa: BLE001 - la portada nunca debe caerse por las cifras
            pass
    stats["porcentaje"] = round(stats["resueltos"] * 100 / stats["total"]) if stats["total"] else 0
    return stats


def portada_view(request):
    if request.session.get("usuario"):
        return inicio_view(request)
    contexto = {
        "stats": _estadisticas_publicas(),
        "delegaciones": DELEGACIONES_OFICIALES,
    }
    return render(request, "publico/portada.html", contexto)
