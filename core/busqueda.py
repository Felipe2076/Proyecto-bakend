"""Búsqueda local por palabras, tildes y RUT con o sin separadores."""
import re
import unicodedata

from django.db.models import Q

def normalizar(valor):
    texto=unicodedata.normalize('NFKD',str(valor or '')).casefold()
    return ''.join(c for c in texto if not unicodedata.combining(c))

_ACENTOS = {"a": "[aáàäâ]", "e": "[eéèëê]", "i": "[iíìïî]", "o": "[oóòöô]", "u": "[uúùüû]", "n": "[nñ]", "c": "[cç]"}


def _patron(palabra):
    """Expresión regular que ignora tildes y ñ: «jose» encuentra «José»; «pena», «peña».

    Funciona igual en MySQL (REGEXP) y en SQLite (las pruebas), sin depender de la intercalación.
    """
    return "".join(_ACENTOS.get(c, re.escape(c)) for c in normalizar(palabra))


def buscar(qs, texto, campos):
    """Filtra en la base de datos: cada palabra debe aparecer en alguno de los campos.

    Antes se cargaba la tabla completa en Python en cada búsqueda (y en cada tecla de la
    búsqueda en vivo). Un RUT se busca también sin puntos ni guion.
    """
    texto = " ".join(str(texto or "").split())[:200]
    if not texto:
        return qs
    digitos = re.sub(r"[^0-9kK]", "", texto)
    es_rut = bool(re.fullmatch(r"[\d.\s-]+[\dkK]?", texto)) and sum(c.isdigit() for c in texto) >= 4
    if es_rut:
        condicion = Q()
        cuerpo = digitos.upper()
        # RUT guardado normalizado (12345678-5): se prueba con y sin guion antes del DV.
        candidatos = {cuerpo, f"{cuerpo[:-1]}-{cuerpo[-1]}" if len(cuerpo) > 1 else cuerpo, texto}
        for campo in campos:
            for valor in candidatos:
                condicion |= Q(**{f"{campo}__icontains": valor})
        return qs.filter(condicion).distinct()
    for palabra in texto.split()[:8]:
        patron = _patron(palabra)
        condicion = Q()
        for campo in campos:
            condicion |= Q(**{f"{campo}__iregex": patron})
        qs = qs.filter(condicion)
    return qs.distinct()
