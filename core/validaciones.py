"""Validación de RUT chileno (módulo 11) y normalización.

El mismo algoritmo vive en ``static/js/modulos/validaciones.js``.
El RUT se guarda sin puntos, con guion y con el dígito verificador en mayúscula
(``33100001-9``). En pantalla se muestra con puntos (``33.100.001-9``).
"""

import re

PATRON_RUT = r"^(\d{1,2}(\.\d{3}){2}|\d{7,8})-[\dkK]$"
_RUT = re.compile(PATRON_RUT)

MENSAJE_RUT = "Ingrese un RUT válido, por ejemplo 33.100.001-9."


def dv_rut(cuerpo: str) -> str:
    """Dígito verificador por módulo 11. ``cuerpo`` son solo dígitos."""
    suma, factor = 0, 2
    for digito in reversed(cuerpo):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def normalizar_rut(rut: str) -> str:
    """Quita puntos y espacios y deja el dígito verificador en mayúscula."""
    limpio = (rut or "").strip().replace(".", "").replace(" ", "").upper()
    return limpio


def validar_rut(rut: str) -> bool:
    """True si el formato es aceptable y el dígito verificador es correcto."""
    if not _RUT.fullmatch((rut or "").strip()):
        return False
    cuerpo, dv = normalizar_rut(rut).split("-")
    if not cuerpo.isdigit():
        return False
    return dv_rut(cuerpo) == dv


def rut_normalizado_valido(rut: str):
    """Devuelve el RUT normalizado, o None si el formato o el DV no calzan."""
    if not validar_rut(rut):
        return None
    return normalizar_rut(rut)


def formatear_rut(rut: str) -> str:
    """``33100001-9`` → ``33.100.001-9``. Si no es válido, devuelve el texto tal cual."""
    normal = rut_normalizado_valido(rut)
    if not normal:
        return (rut or "").strip()
    cuerpo, dv = normal.split("-")
    if len(cuerpo) <= 3:
        return f"{cuerpo}-{dv}"
    grupos = []
    while cuerpo:
        grupos.append(cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    return f"{'.'.join(reversed(grupos))}-{dv}"


def enmascarar_rut(rut: str) -> str:
    """RUT para mostrar en sesión: ``33.1XX.XXX-9`` (conserva el DV)."""
    normal = rut_normalizado_valido(rut)
    if not normal:
        return ""
    cuerpo, dv = normal.split("-")
    if len(cuerpo) < 3:
        return f"{cuerpo}-{'X' * 0}{dv}"
    prefijo = cuerpo[:3]
    return f"{prefijo[:2]}.{prefijo[2]}XX.XXX-{dv}"


def cuerpo_en_rango_ficticio(rut: str) -> bool:
    """True si el cuerpo numérico cae en 33.000.000–33.999.999."""
    normal = rut_normalizado_valido(rut)
    if not normal:
        return False
    cuerpo = int(normal.split("-")[0])
    return 33_000_000 <= cuerpo <= 33_999_999
