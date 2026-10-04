"""Ámbito territorial de la sesión: un rol no administrador no consulta otra delegación."""

from django.contrib import messages
from django.shortcuts import redirect


def delegacion_sesion(request):
    return ((request.session.get("usuario") or {}).get("delegacion") or "").strip()


def es_administrador(request):
    return (request.session.get("usuario") or {}).get("rol") == "administrador"


def denegar_otra_delegacion(request, nombre):
    """Redirige al panel si ``nombre`` es una delegación distinta de la propia.

    El administrador no tiene esta restricción. Un nombre vacío no se niega:
    la vista puede aplicar su filtro por defecto.
    """
    if es_administrador(request):
        return None
    pedida = (nombre or "").strip()
    propia = delegacion_sesion(request)
    if pedida and propia and pedida != propia:
        messages.error(request, "No puede consultar otra delegación.")
        return redirect("inicio")
    return None
