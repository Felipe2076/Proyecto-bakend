"""Autenticación mock y permisos por rol (sin base de datos)."""

from django.contrib import messages
from django.shortcuts import redirect

ROLES_ETIQUETA = {
    "administrador": "Administrador",
    "jefatura": "Jefatura / Control de gestión",
    "funcionario": "Funcionario territorial",
    "ventanilla": "Ventanilla ciudadana",
}

MODULOS_POR_ROL = {
    "administrador": {
        "requerimientos",
        "matriz_sgr",
        "control_gestion",
        "actividades",
        "agenda",
        "compromisos",
        "notificaciones",
        "encuestas",
        "administracion",
    },
    "jefatura": {
        "requerimientos",
        "matriz_sgr",
        "control_gestion",
        "actividades",
        "agenda",
        "compromisos",
        "notificaciones",
        "encuestas",
    },
    "funcionario": {
        "requerimientos",
        "matriz_sgr",
        "actividades",
        "agenda",
        "compromisos",
        "notificaciones",
        "encuestas",
    },
    "ventanilla": {
        "requerimientos",
        "agenda",
        "notificaciones",
        "encuestas",
    },
}


def usuario_sesion(request):
    return request.session.get("usuario") or {}


def rol_actual(request):
    return usuario_sesion(request).get("rol", "")


def etiqueta_rol(rol):
    return ROLES_ETIQUETA.get(rol, rol or "Sin rol")


def puede_ver(usuario, modulo):
    if not usuario:
        return False
    rol = usuario.get("rol")
    return modulo in MODULOS_POR_ROL.get(rol, set())


def requerir_modulo(request, modulo):
    if puede_ver(usuario_sesion(request), modulo):
        return None
    messages.error(
        request,
        "Su perfil no tiene acceso a este módulo. Inicie sesión con otro usuario de demostración.",
    )
    return redirect("inicio")


def public_user(usuario):
    """Copia segura para la sesión (sin mutar el JSON original)."""
    if not usuario:
        return {}
    copia = dict(usuario)
    copia.pop("password", None)
    copia["rol_etiqueta"] = etiqueta_rol(copia.get("rol"))
    return copia
