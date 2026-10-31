"""Búsqueda local por palabras, tildes y RUT con o sin separadores."""
import re
import unicodedata

def normalizar(valor):
    texto=unicodedata.normalize('NFKD',str(valor or '')).casefold()
    return ''.join(c for c in texto if not unicodedata.combining(c))

def buscar(qs,texto,campos):
    texto=normalizar(texto).strip()[:200]
    if not texto:
        return qs
    palabras=texto.split()
    rut=bool(re.fullmatch(r'[\d.\s-]+[\dkK]?',texto)) and sum(c.isdigit() for c in texto)>=4
    compacto=lambda s:re.sub(r'[^a-z0-9]','',s)
    ids=[]
    for obj in qs:
        valores=[]
        for campo in campos:
            valor=obj
            for parte in campo.split('__'):
                valor=getattr(valor,parte,'') if valor is not None else ''
            valores.append(normalizar(valor))
        documento=' '.join(valores)
        coincide=any(compacto(texto) in compacto(v) for v in valores) if rut else all(p in documento for p in palabras)
        if coincide:
            ids.append(obj.pk)
    return qs.filter(pk__in=ids)
