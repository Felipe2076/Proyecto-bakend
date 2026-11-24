from datetime import date, datetime
from django import template
from django.utils import timezone
from django.utils.dateparse import parse_date

register = template.Library()


@register.filter
def fecha_breve(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%d/%m/%y %H:%M')
    if isinstance(value, date):
        return value.strftime('%d/%m/%y')
    if isinstance(value, str) and len(value) == 10:
        try:
            fecha = parse_date(value)
        except ValueError:
            return value
        if fecha:
            return fecha.strftime('%d/%m/%y')
    return value


@register.filter
def rut_formato(value):
    """``12345678-5`` → ``12.345.678-5``; si no es un RUT válido lo deja igual."""
    from core.validaciones import formatear_rut, rut_canonico

    canonico = rut_canonico(value or "")
    return formatear_rut(canonico) if canonico else (value or "")


@register.filter
def telefono_formato(value):
    """Celular chileno ``+56912345678`` → ``+56 9 1234 5678``."""
    import re

    digitos = re.sub(r"\D", "", value or "")
    if digitos.startswith("56"):
        digitos = digitos[2:]
    if len(digitos) == 9 and digitos.startswith("9"):
        return f"+56 9 {digitos[1:5]} {digitos[5:]}"
    return value or ""


@register.filter
def ancho(value):
    """Porcentaje para CSS (``width:x%``): punto decimal y acotado a 0-100.

    Con ``es-cl`` Django escribiría ``33,3`` y el navegador ignoraría el ancho.
    """
    try:
        numero = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return "0"
    return f"{max(0.0, min(100.0, numero)):.1f}"
