"""Trazabilidad RF → Épica → CU general → CU detallado → pantalla, y reflejo de los casos de uso en el prototipo."""
import html
from drawio import Pagina, DEPENDE, ASOC

NUEVO = '#FBE3E6'
ESTADO = {'I': '#E3F2E1', 'P': '#FFF2C2', 'X': '#EEEEEE'}
TRACE = DEPENDE

FILAS = [  # (RF, épica, CU-G, CU-E, pantalla, estado, nuevo)
    ('RF-09, RF-10, RF-22', 'EP-09 Captura multicanal', 'CU-G01', 'CU-E01 Registrar requerimiento\nCU-E19 Registrar atención', 'Ingresar ticket · Mantenedores › Atenciones', 'I', False),
    ('RF-11, RF-12', 'EP-10 Enrutamiento y asignación', 'CU-G01', 'CU-E06 Enrutar y asignar ticket', 'Detalle del ticket · Áreas de soporte', 'P', False),
    ('RF-13, RF-14', 'EP-11 Semáforo y cuellos de botella', 'CU-G01', 'CU-E07 Semáforo y Kanban', 'Listado de tickets · Tablero Kanban · Panel de gestión', 'I', False),
    ('RF-15, RF-16', 'EP-12 Notificaciones y satisfacción', 'CU-G01', 'CU-E08 Medir satisfacción', 'Encuesta 1–5 · enlace firmado del vecino', 'I', False),
    ('RF-01, RF-02', 'EP-01 Registro de actividades', 'CU-G02', 'CU-E02 Registrar actividad', 'Actividad y evidencia', 'I', False),
    ('RF-04', 'EP-03 Evidencias y verificación', 'CU-G02', 'CU-E04 Evidencias y revisión', 'Actividad y evidencia › Revisar', 'I', False),
    ('RF-03', 'EP-04 Agenda y compromisos', 'CU-G02', 'CU-E03 Gestionar compromisos\nCU-E11 Agenda colectiva', 'Compromisos · Agenda colectiva', 'I', False),
    ('RF-20', 'EP-15 Tubo en tarjetas', 'CU-G02', 'CU-E14 Mover en tubo de tarjetas', 'Tubo de cartas', 'I', True),
    ('RF-25', 'EP-07 Plataforma colaborativa', 'CU-G02', 'CU-E20 Operar desde app móvil', 'App Android (API /api/v1/)', 'P', True),
    ('RF-05, RF-06, RF-21', 'EP-02 Medición · EP-05 Monitoreo', 'CU-G03', 'CU-E05 Desempeño y semáforo', 'Semáforo / indicadores · Metas por funcionario', 'I', False),
    ('RF-18, RF-19', 'EP-14 Reglas de la matriz SGR', 'CU-G03', 'CU-E16 Ausencias y metas\n(reglas en CU-E02)', 'Mantenedores › Ausencias · Actividad y evidencia', 'I', True),
    ('RF-07, RF-26', 'EP-06 Reportabilidad', 'CU-G03', 'CU-E09 Dashboard\nCU-E12 Cierre mensual (propuesto)', 'Resumen delegación · Panel de gestión · Excel', 'P', False),
    ('RF-08', 'EP-08 Administración', 'CU-G04', 'CU-E10 Usuarios, cargos, parámetros\nCU-E15 Configurar trimestre', 'Usuarios · Cargos · Parámetros · Configuración trimestral', 'I', False),
    ('RF-24', 'EP-16 Acceso y alcance', 'CU-G04', 'CU-E18 Alcance por delegación', 'Grupos y permisos · filtro de delegación en todas las pantallas', 'I', True),
    ('RF-23', 'EP-16 Acceso y alcance', 'CU-G06', 'CU-E17 Ingresar y recuperar clave', 'Login · Recuperar contraseña · Activar cuenta', 'I', True),
    ('RF-17', 'EP-13 Organizaciones comunitarias', 'CU-G05', 'CU-E13 Organizaciones comunitarias', 'Mantenedores › Organizaciones · Agenda de organizaciones', 'I', True),
]

RF_NUEVOS = [
    ('RF-17', 'Gestionar organizaciones comunitarias', 'Catálogo OROC por delegación y territorio: directiva, datos legales, verificación e importación sin duplicados.'),
    ('RF-18', 'Aplicar reglas de puntaje de la matriz', 'Máx. 7 actividades/día, cierre semanal el martes, solo suma el resultado aprobado, tope 120 %, felicitaciones validadas por el delegado.'),
    ('RF-19', 'Registrar ausencias y ajustar metas', 'Licencias, vacaciones, días administrativos, emergencias y compensatorios ingresados por el delegado.'),
    ('RF-20', 'Ver el tubo en tarjetas (Card / Canvas)', 'Columnas por estado con KPI; mover arrastrando o eligiendo estado; vencido como distintivo.'),
    ('RF-21', 'Configurar el trimestre', 'Nombre y días automáticos, sin solapamiento; trimestre vigente visible arriba con % de días.'),
    ('RF-22', 'Registrar atenciones ciudadanas', 'Tipo y subatención dependiente; delegación y responsable desde el contexto del usuario.'),
    ('RF-23', 'Ingresar y recuperar el acceso', 'Login por RUT, recuperación con código de un uso por correo, activación de cuentas nuevas.'),
    ('RF-24', 'Encapsular cada delegación', 'Cada administrador ve solo su delegación; el superusuario ve todas y edita la configuración global.'),
    ('RF-25', 'Operar desde la app móvil', 'API v1 para actividades, evidencias, compromisos y Excel; la app nunca accede a MySQL.'),
    ('RF-26', 'Exportar el trabajo propio a Excel', 'Exportación del filtro aplicado, limitada al alcance autorizado y sin campos internos.'),
]

MENU = [('Atención ciudadana', ['Ingresar ticket', 'Listado de tickets', 'Tablero Kanban', 'Encuesta 1–5']),
        ('Gestión interna', ['Actividad y evidencia', 'Compromisos', 'Tubo de cartas', 'Agenda colectiva']),
        ('Desempeño', ['Semáforo / indicadores', 'Metas por funcionario', 'Resumen delegación', 'Panel de gestión', 'Áreas de soporte']),
        ('Mantenedores', ['Organizaciones comunitarias', 'Agenda de organizaciones', 'Configuración trimestral', 'Ausencias y ajuste de metas',
                          'Atenciones', 'Delegaciones, Roles, Metas, Tipos, Vecinos, Territorios']),
        ('Administración', ['Grupos y permisos', 'Usuarios', 'Cargos', 'Parámetros']),
        ('Fuera del menú', ['Login / Recuperar contraseña', 'Detalle del ticket', 'Revisar actividad', 'Enlace de encuesta del vecino', 'API móvil /api/v1/'])]

CU_PANTALLA = {
    'CU-E01': ['Ingresar ticket', 'Detalle del ticket'], 'CU-E06': ['Detalle del ticket', 'Áreas de soporte'],
    'CU-E07': ['Listado de tickets', 'Tablero Kanban', 'Panel de gestión'], 'CU-E08': ['Encuesta 1–5', 'Enlace de encuesta del vecino'],
    'CU-E19': ['Atenciones', 'Tubo de cartas'], 'CU-E02': ['Actividad y evidencia'], 'CU-E04': ['Revisar actividad'],
    'CU-E03': ['Compromisos'], 'CU-E14': ['Tubo de cartas'], 'CU-E11': ['Agenda colectiva'], 'CU-E20': ['API móvil /api/v1/'],
    'CU-E05': ['Semáforo / indicadores', 'Metas por funcionario'], 'CU-E09': ['Resumen delegación', 'Panel de gestión'],
    'CU-E16': ['Ausencias y ajuste de metas'], 'CU-E10': ['Usuarios', 'Cargos', 'Parámetros'], 'CU-E15': ['Configuración trimestral'],
    'CU-E18': ['Grupos y permisos', 'Usuarios'], 'CU-E17': ['Login / Recuperar contraseña'],
    'CU-E13': ['Organizaciones comunitarias', 'Agenda de organizaciones'],
    'CU-E12': [],
}
NOMBRE_CU = {'CU-E01': 'Registrar requerimiento', 'CU-E02': 'Registrar actividad', 'CU-E03': 'Gestionar compromisos', 'CU-E04': 'Evidencias y revisión',
             'CU-E05': 'Desempeño y semáforo', 'CU-E06': 'Enrutar y asignar ticket', 'CU-E07': 'Semáforo y Kanban', 'CU-E08': 'Medir satisfacción',
             'CU-E09': 'Dashboard ejecutivo', 'CU-E10': 'Usuarios, cargos y parámetros', 'CU-E11': 'Agenda colectiva', 'CU-E12': 'Cerrar mes (propuesto)',
             'CU-E13': 'Organizaciones comunitarias', 'CU-E14': 'Tubo de tarjetas', 'CU-E15': 'Configurar trimestre', 'CU-E16': 'Ausencias y metas',
             'CU-E17': 'Ingresar y recuperar clave', 'CU-E18': 'Alcance por delegación', 'CU-E19': 'Registrar atención', 'CU-E20': 'App móvil'}


def pagina_relacion():
    alto = 170 + 66 * len(FILAS)
    p = Pagina('01 Relación entre artefactos', 1860, alto + 100)
    p.titulo('Relación entre artefactos · Requerimiento → Épica → Caso de uso general → Caso de uso detallado → Pantalla', 30, 10,
             sub='Propuesta de trazabilidad pedida por el curso: cada requerimiento funcional llega a una pantalla real del prototipo. Rosado = nuevo (Unidad 3).')
    p.marco('[package] Trazabilidad SIGED-SGR', 20, 70, 1820, alto, tipo='req')
    cols = [('Requerimiento funcional', 40, 200), ('Épica', 320, 270), ('CU general', 670, 120), ('CU detallado', 870, 330), ('Pantalla del prototipo', 1280, 540)]
    for t, x, w in cols:
        p.vertice(f'<b>{t}</b>', x, 110, w, 34, 'rounded=0;whiteSpace=wrap;html=1;fillColor=#7A1F2B;fontColor=#FFFFFF;strokeColor=#7A1F2B;fontSize=11;')
    for i, (rf, ep, cg, ce, pant, est, nuevo) in enumerate(FILAS):
        y = 160 + i * 66
        fondo = NUEVO if nuevo else '#FFFFFF'
        caja = 'rounded=1;arcSize=10;whiteSpace=wrap;html=1;fontSize=10;strokeColor=#333;'
        a = p.vertice(f'«requirement»<br><b>{rf}</b>', 40, y, 200, 54, caja + f'fillColor={fondo};')
        b = p.vertice(ep, 320, y, 270, 54, caja + f'fillColor={fondo};')
        c = p.vertice(f'<b>{cg}</b>', 670, y, 120, 54, 'ellipse;whiteSpace=wrap;html=1;fontSize=10;strokeColor=#333;fillColor=#FFFFFF;')
        d = p.vertice(ce, 870, y, 330, 54, f'ellipse;whiteSpace=wrap;html=1;fontSize=10;strokeColor=#333;fillColor={ESTADO[est]};')
        e = p.vertice(pant, 1280, y, 540, 54, caja + 'fillColor=#F7F7F7;')
        for s, t, et in [(a, b, '«trace»'), (b, c, '«trace»'), (c, d, '«include»'), (d, e, '«realiza»')]:
            p.arista(s, t, et, TRACE)
    y = alto + 10
    for j, (color, txt) in enumerate([(ESTADO['I'], 'CU implementado'), (ESTADO['P'], 'CU parcial'), (NUEVO, 'Nuevo (Unidad 3)')]):
        p.vertice('', 60 + j * 230, y + 40, 18, 14, f'fillColor={color};strokeColor=#333;')
        p.vertice(txt, 84 + j * 230, y + 36, 190, 20, 'text;html=1;fontSize=10;align=left;')
    return p


PANTALLA_CU = {
    'Ingresar ticket': ['CU-E01'], 'Listado de tickets': ['CU-E07'], 'Tablero Kanban': ['CU-E07'], 'Encuesta 1–5': ['CU-E08'],
    'Actividad y evidencia': ['CU-E02'], 'Compromisos': ['CU-E03'], 'Tubo de cartas': ['CU-E14', 'CU-E19'], 'Agenda colectiva': ['CU-E11'],
    'Semáforo / indicadores': ['CU-E05'], 'Metas por funcionario': ['CU-E05'], 'Resumen delegación': ['CU-E09'],
    'Panel de gestión': ['CU-E07', 'CU-E09'], 'Áreas de soporte': ['CU-E06'],
    'Organizaciones comunitarias': ['CU-E13'], 'Agenda de organizaciones': ['CU-E13'], 'Configuración trimestral': ['CU-E15'],
    'Ausencias y ajuste de metas': ['CU-E16'], 'Atenciones': ['CU-E19'], 'Delegaciones, Roles, Metas, Tipos, Vecinos, Territorios': ['CU-E10'],
    'Grupos y permisos': ['CU-E18'], 'Usuarios': ['CU-E10', 'CU-E18'], 'Cargos': ['CU-E10'], 'Parámetros': ['CU-E10'],
    'Login / Recuperar contraseña': ['CU-E17'], 'Detalle del ticket': ['CU-E01', 'CU-E06'], 'Revisar actividad': ['CU-E04'],
    'Enlace de encuesta del vecino': ['CU-E08'], 'API móvil /api/v1/': ['CU-E20'],
}
ESTADO_CU = {'CU-E06': 'P', 'CU-E20': 'P', 'CU-E09': 'I', 'CU-E12': 'X'}
RUTA = {
    'Ingresar ticket': '/requerimientos/nuevo/', 'Listado de tickets': '/lista/', 'Tablero Kanban': '/control/kanban/', 'Encuesta 1–5': '/encuestas/',
    'Actividad y evidencia': '/control/actividades/', 'Compromisos': '/control/tubo-trabajo/', 'Tubo de cartas': '/control/tubo-cartas/',
    'Agenda colectiva': '/control/agenda/', 'Semáforo / indicadores': '/control/semaforo-sgr/', 'Metas por funcionario': '/control/funcionarios/',
    'Resumen delegación': '/control/resumen/', 'Panel de gestión': '/control/', 'Áreas de soporte': '/control/areas/',
    'Organizaciones comunitarias': '/mantenedores/organizaciones/', 'Agenda de organizaciones': '/mantenedores/agenda/',
    'Configuración trimestral': '/mantenedores/periodos/', 'Ausencias y ajuste de metas': '/mantenedores/ausencias/',
    'Atenciones': '/mantenedores/atenciones/', 'Delegaciones, Roles, Metas, Tipos, Vecinos, Territorios': '/mantenedores/…',
    'Grupos y permisos': '/administracion/grupos/', 'Usuarios': '/administracion/usuarios/', 'Cargos': '/administracion/cargos/',
    'Parámetros': '/administracion/parametros/', 'Login / Recuperar contraseña': '/login/ · /recuperar/', 'Detalle del ticket': '/requerimientos/<ticket>/',
    'Revisar actividad': '/control/actividades/<código>/revision/', 'Enlace de encuesta del vecino': '/encuestas/responder/<token>/',
    'API móvil /api/v1/': '/api/v1/…',
}


def pagina_reflejo():
    columnas = [MENU[:3], MENU[3:]]
    FILA, X = 48, (50, 900)
    alturas = [sum(1 + len(it) for _, it in col) * FILA for col in columnas]
    alto = 130 + max(alturas)
    p = Pagina('02 Reflejo de los casos de uso en el prototipo', 1760, alto + 130)
    p.titulo('Reflejo de los casos de uso en el prototipo · menú real del sistema → caso de uso', 30, 10,
             sub='Rúbrica III Evaluación, punto 5. Cada pantalla del menú lateral de SIGED (con su ruta) apunta al caso de uso que realiza.')
    p.marco('[package] Mapa de navegación SIGED-SGR', 20, 70, 1720, alto + 30, tipo='uc')
    for col, x0 in zip(columnas, X):
        y = 120
        for grupo, items in col:
            p.vertice(f'<b>{grupo}</b>', x0, y, 800, 30, 'rounded=0;whiteSpace=wrap;html=1;fillColor=#7A1F2B;fontColor=#FFFFFF;'
                      'strokeColor=#7A1F2B;fontSize=11;align=left;spacingLeft=8;')
            y += FILA
            for it in items:
                pant = p.vertice(f'<b>{it}</b><br><span style="font-size:9px;color:#666">{html.escape(RUTA[it])}</span>', x0 + 20, y - 8, 330, 40,
                                 'rounded=1;arcSize=20;whiteSpace=wrap;html=1;fontSize=10;fillColor=#FFFFFF;strokeColor=#333;align=left;spacingLeft=8;')
                for j, cu in enumerate(PANTALLA_CU[it]):
                    est = ESTADO_CU.get(cu, 'I')
                    c = p.vertice(f'<b>{cu}</b> {NOMBRE_CU[cu]}', x0 + 400 + j * 205, y - 8, 195, 40,
                                  f'ellipse;whiteSpace=wrap;html=1;fontSize=9;strokeColor=#333;fillColor={ESTADO[est]};')
                    if j == 0:
                        p.arista(pant, c, '', 'endArrow=open;endSize=8;strokeColor=#7A1F2B;exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
                y += FILA
    yl = alto + 10
    for j, (color, txt) in enumerate([(ESTADO['I'], 'caso de uso implementado'), (ESTADO['P'], 'caso de uso parcial')]):
        p.vertice('', 60 + j * 260, yl + 14, 18, 14, f'fillColor={color};strokeColor=#333;')
        p.vertice(txt, 84 + j * 260, yl + 10, 220, 20, 'text;html=1;fontSize=10;align=left;')
    p.nota('CU-E12 (cierre mensual) no tiene pantalla: es diseño propuesto. Las 19 restantes se recorren en el prototipo desde el menú o desde '
           'otra pantalla ("Fuera del menú": detalle, revisión, login y enlace del vecino).', 620, yl, 1000)
    return p


def pagina_catalogo():
    p = Pagina('03 Nuevos requerimientos funcionales', 1500, 860)
    p.titulo('Catálogo de requerimientos funcionales nuevos (RF-17 a RF-26)', 30, 10,
             sub='Se suman a RF-01…RF-16 del informe de la Etapa 2. Origen: nuevo requerimiento del cliente (correo de la Coordinación de Delegaciones, '
                 'base de JJVV, formato del tubo en tarjetas y descriptor de funciones) y lo implementado en el código.')
    p.marco('[package] Requerimientos funcionales nuevos', 20, 70, 1460, 770, tipo='req')
    for i, (rid, nom, txt) in enumerate(RF_NUEVOS):
        f, c = divmod(i, 2)
        p.requisito(rid, nom, txt, 60 + c * 710, 110 + f * 140, 660, 115, NUEVO)
    return p


def paginas():
    return [pagina_relacion(), pagina_reflejo(), pagina_catalogo()]
