"""Vistas del sitio público (antes del login).

Cada sección espeja una sección de https://laserena.cl/; las funciones reales
(pagos, trámites, transparencia, noticias completas) se enlazan al sitio oficial.
"""
from django.shortcuts import render

from cuentas.vocabulario import DELEGACIONES_OFICIALES
from publico import contenido as c


def portada_view(request):
    """Visitante anónimo: portada pública. Con sesión: tablero de siempre."""
    if request.session.get("usuario"):
        from requerimientos.views import inicio_view

        return inicio_view(request)
    return render(request, "publico/portada.html", {
        "tramites": c.TRAMITES,
        "servicios": c.SERVICIOS[:3],
        "noticias": c.NOTICIAS[:3],
        "agenda": c.AGENDA,
        "accesos": c.ACCESOS,
        "delegaciones": DELEGACIONES_OFICIALES,
        "url_noticias": c.URL_NOTICIAS,
        "seccion": "inicio",
    })


def municipio_view(request):
    return render(request, "publico/municipio.html", {
        "conocenos": c.CONOCENOS,
        "municipio": c.MUNICIPIO,
        "seccion": "publico_municipio",
    })


def servicios_view(request):
    return render(request, "publico/servicios.html", {
        "servicios": c.SERVICIOS,
        "admision": c.ADMISION_LABORAL,
        "accesos": c.ACCESOS,
        "seccion": "publico_servicios",
    })


def tramites_view(request):
    return render(request, "publico/tramites.html", {
        "tramites": c.TRAMITES,
        "seccion": "publico_servicios",
    })


def delegaciones_view(request):
    return render(request, "publico/delegaciones.html", {
        "delegaciones": DELEGACIONES_OFICIALES,
        "url_delegaciones": c.URL_DELEGACIONES,
        "seccion": "publico_delegaciones",
    })


def noticias_view(request):
    return render(request, "publico/noticias.html", {
        "noticias": c.NOTICIAS,
        "agenda": c.AGENDA,
        "url_noticias": c.URL_NOTICIAS,
        "seccion": "publico_noticias",
    })


def transparencia_view(request):
    return render(request, "publico/transparencia.html", {
        "items": c.TRANSPARENCIA,
        "seccion": "publico_transparencia",
    })


def contacto_view(request):
    return render(request, "publico/contacto.html", {
        "seccion": "publico_contacto",
    })
