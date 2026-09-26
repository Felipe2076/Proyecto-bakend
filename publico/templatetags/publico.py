"""{% load publico %} — datos compartidos por la cabecera y el pie públicos.

Se usa como tag (y no como context processor) para que sólo las plantillas
públicas carguen este contenido y no haya que tocar settings.TEMPLATES.
"""
from django import template

from publico import contenido

register = template.Library()


@register.simple_tag
def sitio_publico():
    return {
        "menu": contenido.MENU,
        "contacto": contenido.CONTACTO,
        "redes": contenido.REDES,
        "transparencia": contenido.TRANSPARENCIA,
        "sitios": contenido.SITIOS,
        "sitio_oficial": contenido.SITIO,
    }
