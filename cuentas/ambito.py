"""Ámbito territorial de la sesión: solo el superusuario consulta otras delegaciones."""

from django.contrib import messages
from django.shortcuts import redirect


def delegacion_sesion(request):
    return ((request.session.get("usuario") or {}).get("delegacion") or "").strip()


def es_administrador(request):
    """Quien ve todas las delegaciones: el superusuario (el administrador queda en su delegación)."""
    return (request.session.get("usuario") or {}).get("rol") == "superusuario"


def denegar_otra_delegacion(request, nombre):
    """Redirige al panel si ``nombre`` es una delegación distinta de la propia.

    El administrador no tiene esta restricción. Un nombre vacío no se niega:
    la vista puede aplicar su filtro por defecto.
    """
    if es_administrador(request):
        return None
    pedida = (nombre or "").strip()
    propia = delegacion_sesion(request)
    # Sin delegación propia, un perfil no administrador no consulta ninguna delegación.
    if pedida and pedida != propia:
        messages.error(request, "No puede consultar otra delegación.")
        return redirect("inicio")
    return None


def limitar_a_delegacion(request, filas, clave="delegacion"):
    """Filas de la delegación propia; el administrador ve todas (ISO 27002 8.3)."""
    if es_administrador(request):
        return filas
    propia = delegacion_sesion(request)
    return [fila for fila in filas if propia and (fila.get(clave) or "") == propia]


def delegacion_por_defecto(request, pedida, por_defecto=""):
    if pedida or es_administrador(request):
        # Sin elección, el superusuario parte por su propia delegación (antes, una fija: «Rural»).
        return pedida or delegacion_sesion(request) or por_defecto
    return delegacion_sesion(request) or por_defecto
