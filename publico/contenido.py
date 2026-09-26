"""Contenido del sitio público de SIGED-SGR.

Estructura espejo de https://laserena.cl/ (menú, trámites, servicios, sitios,
accesos rápidos, transparencia y pie institucional) revisada el 25-09-2026.

Regla: toda función real (pagos, trámites en línea, transparencia, noticias
completas, etc.) vive en el sitio oficial y aquí sólo se enlaza. Las noticias
son tarjetas con títulos breves redactados por el equipo que llevan a la nota
oficial; no se copian textos ni fotografías.
"""

SITIO = "https://laserena.cl"

# ---------------------------------------------------------------------------
# Datos institucionales (pie de laserena.cl)
# ---------------------------------------------------------------------------
CONTACTO = {
    "institucion": "Ilustre Municipalidad de La Serena",
    "direccion": "Arturo Prat 451, La Serena",
    "mapa": "https://www.google.com/maps/search/?api=1&query=Arturo%20Prat%20451%2C%20La%20Serena",
    "telefono": "(56) 51 2 206601",
    "telefono_href": "tel:+56512206601",
    "telefonos_extra": ["51 2 206620", "51 2 206680"],
    "correo": "oficinadepartes@laserena.cl",
    "emergencias": "1457",
    "horarios": [
        ("Lunes a jueves", "08:30 – 14:00 y 15:00 – 17:30"),
        ("Viernes", "08:30 – 14:00 y 15:00 – 16:30"),
    ],
    "linea_directa": "https://lineadirecta.laserena.cl/",
}

REDES = [
    {"nombre": "Facebook", "icono": "bi-facebook", "url": "https://www.facebook.com/Munilaserena/"},
    {"nombre": "Instagram", "icono": "bi-instagram", "url": "https://www.instagram.com/muni_laserena"},
    {"nombre": "X", "icono": "bi-twitter-x", "url": "https://x.com/munilaserena"},
    {"nombre": "YouTube", "icono": "bi-youtube", "url": "https://www.youtube.com/user/munilaserena"},
    {"nombre": "TikTok", "icono": "bi-tiktok", "url": "https://www.tiktok.com/@munilaserena"},
]

# ---------------------------------------------------------------------------
# Menú principal (mismo orden que laserena.cl + acceso al sistema)
# "ruta" = nombre de URL interna; "url" = enlace externo al sitio oficial.
# ---------------------------------------------------------------------------
CONOCENOS = [
    {"titulo": "Historia de La Serena", "icono": "bi-hourglass-split", "url": f"{SITIO}/conocenos/historia-de-la-serena",
     "texto": "Segunda ciudad más antigua de Chile, fundada en 1544."},
    {"titulo": "Himno de La Serena", "icono": "bi-music-note-beamed", "url": f"{SITIO}/conocenos/himno-de-la-serena",
     "texto": "Letra y música del himno comunal."},
    {"titulo": "Visión y misión", "icono": "bi-compass", "url": f"{SITIO}/conocenos/vision-y-mision",
     "texto": "Hacia dónde apunta la gestión municipal."},
    {"titulo": "Políticas municipales", "icono": "bi-journal-text", "url": f"{SITIO}/conocenos/politicas-municipales",
     "texto": "Lineamientos que guían al municipio."},
    {"titulo": "Normas gráficas", "icono": "bi-palette", "url": f"{SITIO}/conocenos/normas-graficas",
     "texto": "Uso correcto del escudo, logo y colores."},
    {"titulo": "Privacidad y datos personales", "icono": "bi-shield-lock",
     "url": f"{SITIO}/conocenos/politicas-de-privacidad-y-proteccion-de-datos-personales",
     "texto": "Cómo se protegen los datos de las personas."},
]

MUNICIPIO = [
    {"titulo": "El Municipio", "icono": "bi-bank", "url": f"{SITIO}/el-municipio",
     "texto": "Alcaldía, direcciones y autoridades municipales."},
    {"titulo": "Concejo Municipal", "icono": "bi-people", "url": f"{SITIO}/concejo-municipal",
     "texto": "Concejales y concejalas de la comuna."},
    {"titulo": "Concejo Online", "icono": "bi-person-video2",
     "url": "https://www.youtube.com/playlist?list=PLcyI03xWq5PSGHhbwSKp0nw0tKNPCt6RM",
     "texto": "Sesiones del Concejo transmitidas en video."},
    {"titulo": "Organigrama", "icono": "bi-diagram-3", "url": f"{SITIO}/documentos/municipalidad/organigrama.pdf",
     "texto": "Estructura de la Municipalidad (PDF)."},
    {"titulo": "Primer Juzgado de Policía Local", "icono": "bi-bank2",
     "url": f"{SITIO}/organigrama/primer-juzgado-policia-local", "texto": "Documentos y preguntas frecuentes."},
    {"titulo": "Segundo Juzgado de Policía Local", "icono": "bi-bank2",
     "url": f"{SITIO}/organigrama/segundo-juzgado-policia-local", "texto": "Información y contacto del juzgado."},
]

# Trámites en línea (tramitesPortal de laserena.cl, en su mismo orden)
TRAMITES = [
    {"titulo": "Permiso de circulación 2026", "icono": "bi-car-front-fill",
     "url": "https://ww18.e-com.cl/Pagos/PermisoCirculacion/renovacion/ecomv3/?id=5",
     "texto": "Pago en línea del permiso de circulación."},
    {"titulo": "Permiso de circulación (automotoras)", "icono": "bi-car-front",
     "url": "https://ww18.e-com.cl/Pagos/PermisoCirculacion/renovacion/ecomv4/vista/?id=5&plebcas=12&portal=%2728/01/2025%27&html=70&opc=1",
     "texto": "Canal exclusivo para automotoras."},
    {"titulo": "Patentes comerciales", "icono": "bi-cash-coin",
     "url": "https://ww18.e-com.cl/Pagos/PatentesComerciales/Pago%20Patentes/onlinev3/inicio.asp?codMunic=5",
     "texto": "Pago de patentes comerciales."},
    {"titulo": "Derechos de aseo", "icono": "bi-trash3",
     "url": "https://ww18.e-com.cl/Pagos/DerechodeAseo/onlinev3/inicio.asp?codMunic=5",
     "texto": "Pago de derechos de aseo domiciliario."},
    {"titulo": "SmartDOM", "icono": "bi-building",
     "url": "https://laserena.smartdom.cl/#/login?returnUrl=%2F",
     "texto": "Trámites de la Dirección de Obras en línea."},
    {"titulo": "Infracciones del Primer Juzgado", "icono": "bi-exclamation-octagon",
     "url": "https://ww18.e-com.cl/Pagos/JPL_v3/partes_online/ingresoJuzgado.asp?codMunic=5",
     "texto": "Pago de partes del Juzgado de Policía Local."},
]

# Servicios municipales (serviciosPortal + menú "Servicios Municipales")
SERVICIOS = [
    {"titulo": "Línea Directa Municipal", "icono": "bi-envelope-at-fill", "url": "https://lineadirecta.laserena.cl/",
     "texto": "Consultas, reclamos y sugerencias al municipio."},
    {"titulo": "Subsidios", "icono": "bi-house-heart", "url": f"{SITIO}/servicios-municipales/subsidios",
     "texto": "Beneficios y requisitos para postular."},
    {"titulo": "Programas", "icono": "bi-grid-1x2", "url": f"{SITIO}/servicios-municipales/programas",
     "texto": "Programas sociales y comunitarios vigentes."},
    {"titulo": "Calendario de juzgados", "icono": "bi-calendar2-range-fill", "url": f"{SITIO}/juzgados",
     "texto": "Audiencias de los Juzgados de Policía Local."},
    {"titulo": "Solicitud de patrocinio", "icono": "bi-pass-fill",
     "url": f"{SITIO}/documentos/docs/patrocinios/index.html",
     "texto": "Patrocinio municipal para actividades."},
    {"titulo": "Concejo Online", "icono": "bi-person-video2",
     "url": "https://www.youtube.com/playlist?list=PLcyI03xWq5PSGHhbwSKp0nw0tKNPCt6RM",
     "texto": "Sesiones del Concejo en video."},
]

ADMISION_LABORAL = [
    {"titulo": "Concurso público 2025", "url": f"{SITIO}/AdmisionLaboral/concurso-planta-municipal/2025/"},
    {"titulo": "Cargos municipales", "url": f"{SITIO}/AdmisionLaboral/concursos-publicos/2026/index.html"},
    {"titulo": "Trabaja con nosotros", "url": "https://trabaja2.munilaserena.cl/"},
]

# Accesos rápidos (banners de la portada oficial)
ACCESOS = [
    {"titulo": "Registro Civil", "icono": "bi-person-vcard", "url": "https://www.registrocivil.cl/"},
    {"titulo": "Contribuciones TGR", "icono": "bi-receipt", "url": "https://www.tgr.cl/contribuciones/#pagar-contribuciones-en-linea"},
    {"titulo": "Pensión Garantizada (PGU)", "icono": "bi-person-heart", "url": "https://www.chileatiende.gob.cl/fichas/102077-pension-garantizada-universal-pgu"},
    {"titulo": "Beneficios sociales", "icono": "bi-heart-pulse", "url": "http://www.laserena.cl/DeptoSocial/departamento-social"},
    {"titulo": "Sección de la Mujer", "icono": "bi-gender-female", "url": "http://www.laserena.cl/seccion-de-la-mujer-y-equidad-de-genero#contratos"},
    {"titulo": "Juntas de vecinos", "icono": "bi-house-door", "url": "http://transparencia.laserena.cl/ptransact.php?n=177"},
    {"titulo": "Áreas verdes", "icono": "bi-tree", "url": "http://mapas.laserena.cl/mapas/areas_verdes_licitadas/index.html#13/-29.9061/-71.2433"},
    {"titulo": "Buses eléctricos", "icono": "bi-bus-front", "url": "https://coquimbo.transporteinforma.cl/recorrido-de-buses-electricos-coquimbo-la-serena/"},
    {"titulo": "Créditos y remates DICREP", "icono": "bi-bag-check", "url": "https://www.dicrep.cl/"},
    {"titulo": "Cuentas públicas", "icono": "bi-file-earmark-bar-graph", "url": "http://transparencia.laserena.cl/ptransact.php?n=64"},
]

# Sitios municipales (sección "Sitios" de laserena.cl)
SITIOS = [
    {"titulo": "Visita La Serena", "url": "https://visitalaserena.cl/"},
    {"titulo": "Panoramas comunales", "url": "https://panoramas.laserena.cl/"},
    {"titulo": "Cultura", "url": "https://cultura.laserena.cl/"},
    {"titulo": "Patrimonio", "url": "https://patrimonio.laserena.cl/"},
    {"titulo": "Medio Ambiente", "url": "https://medioambiente.laserena.cl/"},
    {"titulo": "Serena Activa", "url": "https://serenactiva.cl/"},
    {"titulo": "Social", "url": "https://social.laserena.cl"},
    {"titulo": "Presupuestos participativos", "url": "https://pp.laserena.cl/"},
    {"titulo": "Mapas SIG", "url": "https://mapas.laserena.cl/"},
    {"titulo": "Gestión de riesgos", "url": "https://gestionderiesgos.laserena.cl/"},
    {"titulo": "PLADECO", "url": "https://pladeco.laserena.cl"},
    {"titulo": "PIIMEP", "url": "https://piimep.laserena.cl"},
    {"titulo": "Ciudades hermanas", "url": "https://ciudadeshermanas.laserena.cl/"},
    {"titulo": "Centro Médico Veterinario", "url": "https://cmv.laserena.cl/"},
    {"titulo": "Estadio La Portada", "url": "https://estadiolaportada.cl/"},
    {"titulo": "Portal de Transparencia", "url": "https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/?org=MU126"},
]

# Transparencia y participación (pie y componente de transparencia de laserena.cl)
TRANSPARENCIA = [
    {"titulo": "Transparencia activa", "icono": "bi-eye",
     "url": "https://www.portaltransparencia.cl/PortalPdT/directorio-de-organismos-regulados/?org=MU126",
     "texto": "Información que el municipio publica de forma permanente."},
    {"titulo": "Solicitar información", "icono": "bi-envelope-paper",
     "url": "https://www.portaltransparencia.cl/PortalPdT/web/guest/directorio-de-organismos-regulados?p_p_id=pdtorganismos_WAR_pdtorganismosportlet&orgcode=d67e38e61d6896e0e50080a9baaabf3f",
     "texto": "Solicitud de acceso a la información pública (Ley 20.285)."},
    {"titulo": "Ley del Lobby", "icono": "bi-briefcase",
     "url": "https://www.leylobby.gob.cl/instituciones/MU126",
     "texto": "Audiencias, viajes y donativos de autoridades."},
    {"titulo": "Cuentas públicas", "icono": "bi-file-earmark-bar-graph",
     "url": "http://transparencia.laserena.cl/ptransact.php?n=64",
     "texto": "Histórico de cuentas públicas de la gestión."},
    {"titulo": "Presupuestos participativos", "icono": "bi-hand-thumbs-up",
     "url": "https://pp.laserena.cl/", "texto": "Vecinas y vecinos deciden proyectos para su barrio."},
    {"titulo": "PLADECO", "icono": "bi-map",
     "url": "https://pladeco.laserena.cl", "texto": "Plan de Desarrollo Comunal."},
]

# Agenda (laserena.cl no publica un calendario propio: enlaza a estos canales)
AGENDA = [
    {"titulo": "Panoramas comunales", "icono": "bi-calendar-event", "url": "https://panoramas.laserena.cl/",
     "texto": "Actividades, ferias y eventos de la semana en la comuna."},
    {"titulo": "Sesiones del Concejo", "icono": "bi-camera-video",
     "url": "https://www.youtube.com/playlist?list=PLcyI03xWq5PSGHhbwSKp0nw0tKNPCt6RM",
     "texto": "Revive o sigue en vivo las sesiones del Concejo Municipal."},
    {"titulo": "Cultura en La Serena", "icono": "bi-music-note-list", "url": "https://cultura.laserena.cl/",
     "texto": "Cartelera cultural, talleres y espacios municipales."},
]

# Noticias: títulos breves propios; el texto completo está en laserena.cl
NOTICIAS = [
    {"id": 1388, "fecha": "2026-09-25", "tema": "Medio ambiente", "icono": "bi-flower1",
     "titulo": "Paisajismo sustentable para recuperar espacios públicos"},
    {"id": 1387, "fecha": "2026-09-25", "tema": "Salud", "icono": "bi-capsule",
     "titulo": "Farmacia comunal anuncia grandes descuentos para vecinos"},
    {"id": 1386, "fecha": "2026-09-25", "tema": "Medio ambiente", "icono": "bi-recycle",
     "titulo": "Nueva chipeadora transformará ramas en material reutilizable"},
    {"id": 1385, "fecha": "2026-09-24", "tema": "Comunidad", "icono": "bi-people",
     "titulo": "Segundo seminario intersectorial contra la trata de personas"},
    {"id": 1384, "fecha": "2026-09-24", "tema": "Personas mayores", "icono": "bi-house-heart",
     "titulo": "Tres nuevas casas para personas mayores en distintos sectores"},
    {"id": 1383, "fecha": "2026-09-24", "tema": "Inclusión", "icono": "bi-puzzle",
     "titulo": "Avanza el proyecto de un centro de inclusión infantil"},
]
for _n in NOTICIAS:
    _n["url"] = f"{SITIO}/noticia/{_n['id']}"

URL_NOTICIAS = f"{SITIO}/noticias"
URL_DELEGACIONES = f"{SITIO}/Delegaciones"

# Menú principal. Los submenús reproducen los de laserena.cl.
MENU = [
    {"titulo": "Inicio", "ruta": "inicio"},
    {"titulo": "Municipio", "ruta": "publico_municipio", "hijos": [
        {"titulo": "Conócenos", "ruta": "publico_municipio", "ancla": "conocenos"},
        {"titulo": "El Municipio", "url": f"{SITIO}/el-municipio"},
        {"titulo": "Concejo Municipal", "url": f"{SITIO}/concejo-municipal"},
        {"titulo": "Organigrama (PDF)", "url": f"{SITIO}/documentos/municipalidad/organigrama.pdf"},
        {"titulo": "Juzgados de Policía Local", "ruta": "publico_municipio", "ancla": "juzgados"},
    ]},
    {"titulo": "Servicios", "ruta": "publico_servicios", "hijos": [
        {"titulo": "Trámites en línea", "ruta": "publico_tramites"},
        {"titulo": "Servicios municipales", "ruta": "publico_servicios"},
        {"titulo": "Subsidios", "url": f"{SITIO}/servicios-municipales/subsidios"},
        {"titulo": "Programas", "url": f"{SITIO}/servicios-municipales/programas"},
        {"titulo": "Admisión laboral", "ruta": "publico_servicios", "ancla": "admision"},
    ]},
    {"titulo": "Delegaciones", "ruta": "publico_delegaciones"},
    {"titulo": "Noticias", "ruta": "publico_noticias"},
    {"titulo": "Transparencia", "ruta": "publico_transparencia"},
    {"titulo": "Contacto", "ruta": "publico_contacto"},
]
