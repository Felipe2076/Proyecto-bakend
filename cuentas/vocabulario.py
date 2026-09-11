"""Vocabulario alineado al DER y a las fichas CU-E01..E12."""

DELEGACIONES_OFICIALES = [
    "Delegación Centro",
    "Delegación Rural",
    "Delegación La Antena",
    "Delegación La Pampa",
    "Delegación Av. del Mar",
    "Delegación Las Compañías",
]

TIPOS_TICKET = [
    "RECLAMO",
    "SOLICITUD",
    "CONSULTA",
    "SUGERENCIA",
    "FELICITACIÓN",
]

CANALES_INGRESO = [
    "ventanilla",
    "WhatsApp",
    "correo",
]

AREAS_ESTRATEGICAS = [
    "Seguridad Ciudadana",
    "Gestión Social y Comunitaria",
    "Servicio a la Comunidad",
    "Instituciones Municipales y Participación",
]

_DELEG_ALIAS = {
    "delegación central": "Delegación Centro",
    "delegacion central": "Delegación Centro",
    "delegación centro": "Delegación Centro",
    "delegacion centro": "Delegación Centro",
    "centro": "Delegación Centro",
    "delegación avenida del mar": "Delegación Av. del Mar",
    "delegacion avenida del mar": "Delegación Av. del Mar",
    "delegación av. del mar": "Delegación Av. del Mar",
    "av. del mar": "Delegación Av. del Mar",
}

_TIPO_ALIAS = {
    "reclamo": "RECLAMO",
    "solicitud de ayuda": "SOLICITUD",
    "solicitud": "SOLICITUD",
    "consulta": "CONSULTA",
    "sugerencia": "SUGERENCIA",
    "felicitación": "FELICITACIÓN",
    "felicitacion": "FELICITACIÓN",
}

_CANAL_ALIAS = {
    "whatsapp bot": "WhatsApp",
    "whatsapp": "WhatsApp",
    "presencial": "ventanilla",
    "ventanilla (presencial)": "ventanilla",
    "ventanilla": "ventanilla",
    "correo electrónico": "correo",
    "correo electronico": "correo",
    "correo": "correo",
    "telefónico": "ventanilla",
    "telefonico": "ventanilla",
    "teléfono": "ventanilla",
    "telefono": "ventanilla",
    "portal web": "correo",
}


def normalizar_delegacion(valor):
    clave = (valor or "").strip().lower()
    if valor in DELEGACIONES_OFICIALES:
        return valor
    return _DELEG_ALIAS.get(clave, valor)


def normalizar_tipo(valor):
    clave = (valor or "").strip().lower()
    if (valor or "").strip().upper() in TIPOS_TICKET:
        if (valor or "").strip().upper() == "FELICITACIÓN":
            return "FELICITACIÓN"
        return (valor or "").strip().upper()
    return _TIPO_ALIAS.get(clave, (valor or "").strip())


def normalizar_canal(valor):
    clave = (valor or "").strip().lower()
    if valor in CANALES_INGRESO:
        return valor
    return _CANAL_ALIAS.get(clave, valor)
