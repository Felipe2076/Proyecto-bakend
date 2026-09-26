"""Portada pública (/) de SIGED-SGR.

- Visitante anónimo: ve la página principal con presentación del sistema.
- Usuario con sesión: se delega al tablero de inicio de siempre (inicio_view).
"""

import logging

from django.db import DatabaseError
from django.shortcuts import render

from cuentas.vocabulario import DELEGACIONES_OFICIALES
from requerimientos.views import inicio_view

logger = logging.getLogger(__name__)


def _estadisticas_publicas():
    """Cifras agregadas (sin datos personales) leídas de la base."""
    stats = {"delegaciones": len(DELEGACIONES_OFICIALES), "total": 0, "resueltos": 0, "fuente": "base de datos municipal"}
    try:
        from cuentas.models import Delegacion
        from requerimientos.models import Requerimiento

        stats["delegaciones"] = Delegacion.objects.count() or len(DELEGACIONES_OFICIALES)
        stats["total"] = Requerimiento.objects.count()
        stats["resueltos"] = Requerimiento.objects.filter(estado=Requerimiento.Estado.RESUELTO).count()
    except DatabaseError as err:
        logger.warning("Portada: sin acceso a la base de datos (%s)", err)
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


def creditos_view(request):
    """Página pública con la fuente y licencia de cada imagen (ver static/img/laserena/CREDITOS.md)."""
    return render(request, "publico/creditos.html")
