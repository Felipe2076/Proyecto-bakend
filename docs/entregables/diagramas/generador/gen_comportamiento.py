"""Diagramas de comportamiento: secuencia, actividad y estados (según el código)."""
from drawio import Pagina, FLUJO

SYNC = 'endArrow=block;endFill=1;endSize=8;'
RET = 'endArrow=open;endSize=8;dashed=1;'
TRANS = 'endArrow=open;endSize=10;edgeStyle=orthogonalEdgeStyle;rounded=1;'


def secuencia(nombre, titulo, sub, participantes, mensajes, notas=(), ancho_col=210):
    """participantes: [(clave, etiqueta, es_actor)]; mensajes: [(de, a, texto, tipo)] tipo sync|ret|self|frag."""
    ancho = 80 + ancho_col * len(participantes)
    x = {k: 100 + i * ancho_col + ancho_col / 2 for i, (k, _, _) in enumerate(participantes)}
    # Primero se calcula el alto que ocupan los mensajes.
    y = 245
    for _, _, _, tipo in mensajes:
        y += 34 if tipo == 'frag' else 54 if tipo == 'self' else 44
    fin = y + 10
    p = Pagina(nombre, max(1400, ancho + 60), fin + 90)
    p.titulo(titulo, 30, 10, sub=sub)
    p.marco(f'[interaction] {titulo.split("·")[-1].strip()}', 20, 70, max(1360, ancho + 20), fin - 40, tipo='sd')
    linea = 'endArrow=none;dashed=1;strokeColor=#666666;'
    for k, etq, actor in participantes:
        cx = x[k]
        if actor:
            p.actor(etq, cx - 15, 112)
            p.flecha(cx, 196, cx, fin, '', linea)
        else:
            p.vertice(f'<b>{etq}</b>', cx - 85, 120, 170, 46, 'rounded=0;whiteSpace=wrap;html=1;fontSize=10;fillColor=#F3E7E9;strokeColor=#7A1F2B;')
            p.flecha(cx, 166, cx, fin, '', linea)
    y, n = 245, 0
    barra = 'rounded=0;fillColor=#FFFFFF;strokeColor=#333;'
    for de, a, texto, tipo in mensajes:
        if tipo == 'frag':
            p.vertice('', 40, y - 12, ancho, 12, 'line;strokeColor=#7A1F2B;dashed=1;dashPattern=6 4;strokeWidth=1;', obst=False)
            p.vertice(f'<b>{texto}</b>', 44, y - 4, 360, 20, 'text;html=1;fontSize=10;align=left;fontColor=#7A1F2B;labelBackgroundColor=#FFFFFF;')
            y += 34
            continue
        n += 1
        etq = f'{n}. {texto}'
        if tipo == 'self':
            p.vertice('', x[de] - 5, y - 4, 10, 34, barra)
            p.flecha(x[de] + 5, y, x[de] + 5, y + 24, etq, SYNC + 'align=left;spacingLeft=4;', puntos=[(x[de] + 42, y), (x[de] + 42, y + 24)])
            y += 54
            continue
        derecha = x[a] > x[de]
        if tipo == 'sync':
            p.vertice('', x[a] - 5, y - 4, 10, 30, barra)
        p.flecha(x[de] + (5 if derecha else -5), y, x[a] + (-5 if derecha else 5), y, etq, SYNC if tipo == 'sync' else RET)
        y += 44
    for texto, nx, ny, nw, nh in notas:
        p.nota(texto, nx, ny, nw, nh)
    return p


def pag_ticket():
    part = [('op', 'Operador de ventanilla', True), ('ui', ':Pantalla nuevo ticket', False), ('req', ':requerimientos.views', False),
            ('amb', ':cuentas.ambito', False), ('bd', ':ORM / MySQL', False), ('jef', 'Jefatura', True), ('kan', ':control_gestion.kanban', False),
            ('vec', 'Vecino', True)]
    msj = [('', '', 'Ingreso del requerimiento (CU-E01)', 'frag'),
           ('op', 'ui', 'abrir /requerimientos/nuevo/', 'sync'), ('ui', 'req', 'GET formulario', 'sync'), ('req', 'amb', 'delegación autorizada del perfil', 'sync'),
           ('amb', 'req', 'delegación', 'ret'), ('op', 'ui', 'vecino, canal, tipo, área, descripción', 'sync'), ('ui', 'req', 'POST (token CSRF)', 'sync'),
           ('req', 'req', 'validar campos obligatorios y correo si canal = correo', 'self'), ('req', 'bd', 'crear/vincular Vecino y Requerimiento (Pendiente)', 'sync'),
           ('bd', 'req', 'código TK-xxxx', 'ret'), ('req', 'op', 'confirmación con código del ticket', 'ret'),
           ('', '', 'Asignación y avance (CU-E06, CU-E07)', 'frag'),
           ('jef', 'kan', 'arrastrar tarjeta a "En Proceso"', 'sync'), ('kan', 'amb', '¿ticket dentro de su delegación y permiso?', 'sync'),
           ('amb', 'kan', 'autorizado', 'ret'), ('kan', 'bd', 'actualizar estado y responsable', 'sync'), ('kan', 'jef', 'tablero actualizado', 'ret'),
           ('jef', 'kan', 'mover a "Resuelto"', 'sync'), ('kan', 'bd', 'guardar Resuelto', 'sync'),
           ('', '', 'Encuesta de satisfacción (CU-E08)', 'frag'),
           ('op', 'req', 'generar enlace de encuesta', 'sync'), ('req', 'op', 'enlace firmado (vigencia 30 días)', 'ret'),
           ('vec', 'req', 'abrir enlace y enviar nota 1–5', 'sync'), ('req', 'req', 'validar firma, vigencia y ticket Resuelto', 'self'),
           ('req', 'bd', 'guardar evaluación y comentario', 'sync'), ('req', 'vec', 'gracias por responder', 'ret')]
    return secuencia('01 Secuencia · ticket ciudadano', 'Diagrama de secuencia · Ticket ciudadano de punta a punta',
                     'Desde el ingreso por ventanilla, WhatsApp o correo hasta la encuesta 1–5. Reflejo: Ingresar ticket → Listado/Kanban → Encuesta.',
                     part, msj, ancho_col=180)


def pag_actividad():
    part = [('fun', 'Funcionario', True), ('ui', ':Actividad y evidencia', False), ('con', ':consultas', False), ('evi', ':evidencias', False),
            ('rev', ':revision', False), ('bd', ':ORM / MySQL', False), ('del', 'Administrador de delegación', True)]
    msj = [('', '', 'Registro (CU-E02)', 'frag'),
           ('fun', 'ui', 'ítem, tipo de registro, contacto, servicio, archivo', 'sync'), ('ui', 'con', 'registrar_actividad()', 'sync'),
           ('con', 'con', 'fecha no futura · semana abierta (martes) · < 7 en el día', 'self'), ('con', 'evi', 'validar tipo y tamaño (≤ 10 MB)', 'sync'),
           ('evi', 'con', 'archivo aceptado', 'ret'), ('con', 'bd', 'crear Actividad ACT + verificador (PENDIENTE, no suma)', 'sync'),
           ('con', 'fun', 'actividad registrada', 'ret'),
           ('', '', 'Revisión (CU-E04)', 'frag'),
           ('del', 'rev', 'decisión + comentario + versión vista', 'sync'), ('rev', 'rev', '¿revisor ≠ autor? ¿versión vigente? ¿hay archivo?', 'self'),
           ('rev', 'bd', 'bloquear fila y guardar estado (APROBADA | RECHAZADA | CORRECCION)', 'sync'),
           ('rev', 'bd', 'crear RevisionActividad (autor, comentario, versión)', 'sync'), ('rev', 'bd', 'si APROBADA y RESULTADO: sumar 1 al ítem (una vez)', 'sync'),
           ('rev', 'del', 'resultado de la revisión', 'ret'), ('fun', 'ui', 'consultar estado y comentario', 'sync')]
    return secuencia('02 Secuencia · actividad y revisión', 'Diagrama de secuencia · Registro de actividad y revisión de evidencia',
                     'Una actividad no suma al registrarse: solo cuando otra persona la aprueba. Reflejo: /control/actividades/ y /control/actividades/<código>/revision/.',
                     part, msj)


def pag_tubo():
    part = [('fun', 'Funcionario', True), ('js', ':tubo de tarjetas (kanban.js)', False), ('kan', ':movimientos (mover estado)', False), ('amb', ':cuentas.ambito', False),
            ('bd', ':ORM / MySQL', False)]
    msj = [('fun', 'js', 'arrastrar tarjeta TUB a "En proceso"', 'sync'), ('js', 'kan', 'POST id, estado nuevo, estado anterior (CSRF)', 'sync'),
           ('kan', 'amb', '¿compromiso o atención dentro del ámbito?', 'sync'), ('amb', 'kan', 'sí / 404 si es de otra delegación', 'ret'),
           ('kan', 'bd', 'select_for_update() del compromiso', 'sync'), ('kan', 'kan', '¿estado anterior = estado en BD?', 'self'),
           ('', '', 'alt  [otra persona lo cambió]', 'frag'), ('kan', 'js', '409 "Otra persona cambió este compromiso. Recargue la página."', 'ret'),
           ('', '', 'else  [sin conflicto]', 'frag'), ('kan', 'bd', 'guardar estado + CambioCompromiso (autor, anterior, nuevo)', 'sync'),
           ('kan', 'js', 'OK + totales recalculados', 'ret'), ('js', 'fun', 'tarjeta en la nueva columna; "Vencido" sigue como distintivo', 'ret')]
    return secuencia('03 Secuencia · mover tarjeta del tubo', 'Diagrama de secuencia · Mover un compromiso en el tubo de tarjetas',
                     'Formato Card/Canvas pedido por el cliente. Vencido es un distintivo calculado por fecha, no una columna. Reflejo: /control/tubo-cartas/.',
                     part, msj, ancho_col=260)


def pag_recuperar():
    part = [('usr', 'Usuario', True), ('ui', ':Recuperar contraseña', False), ('rec', ':cuentas.recuperacion', False), ('bd', ':ORM / MySQL', False),
            ('smtp', 'Servidor de correo', True)]
    msj = [('usr', 'ui', 'ingresar correo', 'sync'), ('ui', 'rec', 'solicitar_codigo(correo)', 'sync'), ('rec', 'bd', 'buscar cuenta activa', 'sync'),
           ('rec', 'bd', 'guardar CodigoUnUso (hash, vence, intentos = 0)', 'sync'), ('rec', 'smtp', 'enviar código de 6 dígitos', 'sync'),
           ('rec', 'usr', 'mensaje genérico (no revela si el correo existe)', 'ret'), ('usr', 'ui', 'ingresar código', 'sync'),
           ('ui', 'rec', 'validar_codigo()', 'sync'), ('rec', 'rec', 'vigente · no usado · intentos bajo el límite', 'self'),
           ('usr', 'ui', 'nueva contraseña + confirmación', 'sync'), ('ui', 'rec', 'cambiar_clave()', 'sync'),
           ('rec', 'bd', 'guardar hash de la clave y marcar código usado', 'sync'), ('rec', 'usr', 'volver al login con la nueva clave', 'ret')]
    return secuencia('04 Secuencia · recuperar contraseña', 'Diagrama de secuencia · Recuperación de contraseña con código de un uso',
                     'Rutas /recuperar/ → /recuperar/codigo/ → /recuperar/nueva/. El código se guarda como hash y se invalida al usarse.', part, msj, ancho_col=260)


def carril(p, titulo, x, y, w, h, color):
    p.vertice(f'<b>{titulo}</b>', x, y, w, 30, f'rounded=0;whiteSpace=wrap;html=1;fillColor={color};strokeColor=#333;fontSize=11;')
    p.vertice('', x, y + 30, w, h - 30, 'rounded=0;fillColor=none;strokeColor=#333;', obst=False)


def accion(p, texto, x, y, w=220, h=50):
    return p.vertice(texto, x, y, w, h, 'rounded=1;arcSize=30;whiteSpace=wrap;html=1;fontSize=10;fillColor=#FFFFFF;strokeColor=#333;')


def decision(p, texto, x, y):
    return p.vertice(texto, x, y, 150, 80, 'rhombus;whiteSpace=wrap;html=1;fontSize=9;fillColor=#FFF8E1;strokeColor=#333;', forma='centro')


def inicio(p, x, y):
    return p.vertice('', x, y, 26, 26, 'ellipse;fillColor=#000000;strokeColor=#000;', forma='centro')


def fin(p, x, y):
    return p.vertice('', x, y, 30, 30, 'ellipse;shape=endState;fillColor=#000000;strokeColor=#000;', forma='centro')


def pag_actividad_evidencia():
    p = Pagina('05 Actividad · revisión de evidencia', 1500, 1100)
    p.titulo('Diagrama de actividad · Registro y revisión de una actividad con evidencia', 30, 10,
             sub='Carriles por responsable. Una aprobación suma una sola vez; el autor no puede revisarse a sí mismo; la corrección vuelve al funcionario.')
    p.marco('[activity] Actividad con evidencia', 20, 70, 1460, 1010, tipo='act')
    carril(p, 'Funcionario', 40, 110, 440, 950, '#EAF1FB')
    carril(p, 'Sistema SIGED', 500, 110, 480, 950, '#EAF6EA')
    carril(p, 'Administrador de delegación (revisor)', 1000, 110, 460, 950, '#FBE3E6')
    i = inicio(p, 247, 150)
    a1 = accion(p, 'Completar actividad (ítem, tipo, contacto, servicio) y adjuntar archivo', 150, 235)
    d1 = decision(p, '¿Reglas OK? (≤ 7 / día, semana abierta, archivo ≤ 10 MB)', 560, 220)
    a2 = accion(p, 'Mostrar errores y conservar datos', 770, 235, 195)
    a3 = accion(p, 'Guardar ACT + verificador; estado PENDIENTE (no suma)', 525, 440)
    a4 = accion(p, 'Abrir actividad y ver evidencia', 1120, 440)
    d2 = decision(p, '¿Revisor distinto del autor y versión vigente?', 1155, 540)
    a5 = accion(p, 'Rechazar operación (403 / 409)', 640, 560, 200)
    d3 = decision(p, 'Decisión', 1155, 680)
    a6 = accion(p, 'APROBADA: guardar revisión y sumar 1 al ítem (si es RESULTADO)', 630, 690)
    a7 = accion(p, 'RECHAZADA: guardar revisión con comentario', 630, 800)
    a8 = accion(p, 'CORRECCIÓN: guardar revisión y devolver', 630, 900)
    a9 = accion(p, 'Corregir y volver a enviar', 150, 900)
    f = fin(p, 727, 1010)
    for a, b, g in [(i, a1, ''), (a1, d1, ''), (d1, a2, '[no]'), (a2, a1, ''), (d1, a3, '[sí]'), (a3, a4, ''), (a4, d2, ''), (d2, a5, '[no]'),
                    (d2, d3, '[sí]'), (d3, a6, '[aprobar]'), (d3, a7, '[rechazar]'), (d3, a8, '[pedir corrección]'), (a8, a9, ''), (a9, a3, ''),
                    (a6, f, ''), (a7, f, '')]:
        p.arista(a, b, g, FLUJO, rutear=True)
    return p


def estado(p, nombre, x, y, w=170, h=50, color='#FFFFFF', extra=''):
    return p.vertice(nombre, x, y, w, h, f'rounded=1;arcSize=40;whiteSpace=wrap;html=1;fontSize=11;fontStyle=1;fillColor={color};strokeColor=#333;' + extra)


def pag_estados():
    p = Pagina('06 Estados · compromiso, ticket y actividad', 1500, 1200)
    p.titulo('Diagramas de estados · Compromiso, Ticket y revisión de Actividad', 30, 10,
             sub='Estados tal como están definidos en los modelos (TextChoices). "Vencido" del compromiso es una condición, no un estado.')
    p.marco('[state machine] Compromiso', 20, 70, 1460, 330, tipo='stm')
    i = inicio(p, 50, 210)
    e1, e2, e3, e4 = (estado(p, n, x, 195) for n, x in [('INGRESADO', 140), ('PENDIENTE', 430), ('EN PROCESO', 720), ('REALIZADO', 1010)])
    f = fin(p, 1260, 205)
    for a, b, t in [(i, e1, 'crear'), (e1, e2, 'mover'), (e2, e3, 'mover'), (e3, e4, 'mover'), (e4, f, '')]:
        p.arista(a, b, t, TRANS, rutear=True)
    p.arista(e3, e2, 'devolver', TRANS + 'exitX=0.5;exitY=1;entryX=0.5;entryY=1;', puntos=[(805, 290), (515, 290)])
    p.arista(e4, e1, 'reabrir (mover a otra columna)', TRANS + 'exitX=0.5;exitY=0;entryX=0.5;entryY=0;', puntos=[(1095, 140), (225, 140)])
    p.nota('Condición calculada «Vencido» = fecha_compromiso < hoy y estado ≠ REALIZADO. Se muestra como distintivo rojo en '
           'cualquier columna y cuenta en el resumen. Cada transición crea un CambioCompromiso con su autor.', 140, 310, 900, 50)
    p.marco('[state machine] Ticket (Requerimiento)', 20, 420, 1460, 330, tipo='stm')
    i2 = inicio(p, 50, 560)
    t1, t2, t3, t4 = (estado(p, n, x, 545, 190) for n, x in [('Pendiente', 140), ('En Proceso', 440), ('Cuello Botella Central', 740), ('Resuelto', 1040)])
    f2 = fin(p, 1300, 555)
    for a, b, t in [(i2, t1, 'registrar'), (t1, t2, 'asignar / mover'), (t2, t3, 'bloqueo detectado'), (t2, t4, 'resolver'), (t4, f2, 'encuesta 1–5')]:
        p.arista(a, b, t, TRANS, rutear=True)
    p.arista(t3, t2, 'desbloquear', TRANS + 'exitX=0.5;exitY=1;entryX=0.5;entryY=1;', puntos=[(835, 640), (535, 640)])
    p.nota('Semáforo por antigüedad (no es un estado): verde ≤ 3 días, amarillo ≤ 5, rojo > 5 (ParametroSistema).', 140, 670, 700, 40)
    p.marco('[state machine] Revisión de Actividad (estado_revision)', 20, 770, 1460, 400, tipo='stm')
    i3 = inicio(p, 50, 930)
    r1 = estado(p, 'PENDIENTE', 140, 915, 170, 50, '#FFF8E1')
    r2 = estado(p, 'APROBADA', 520, 830, 170, 50, '#E3F2E1')
    r3 = estado(p, 'RECHAZADA', 520, 920, 170, 50, '#F8D7DA')
    r4 = estado(p, 'CORRECCION', 520, 1010, 170, 50, '#EEEEEE')
    r5 = estado(p, 'HISTORICA', 900, 1090, 200, 50, '#F2F2F2', 'dashed=1;')
    f3 = fin(p, 900, 925)
    for a, b, t in [(i3, r1, 'registrar'), (r1, r2, 'aprobar [revisor ≠ autor, hay archivo]'), (r1, r3, 'rechazar'), (r1, r4, 'pedir corrección'),
                    (r2, f3, 'suma 1 vez'), (r3, f3, '')]:
        p.arista(a, b, t, TRANS, rutear=True)
    p.arista(r4, r1, 'funcionario corrige', TRANS, rutear=True)
    p.nota('HISTORICA: registros anteriores a la revisión; se conservan sin cambios y no pueden revisarse.', 1120, 1080, 330, 60)
    return p


def pag_despliegue_seguro():
    p = Pagina('07 Actividad · despliegue con respaldo', 1500, 1000)
    p.titulo('Diagrama de actividad · Despliegue de cambios con respaldo y reversión (gestión de versiones)', 30, 10,
             sub='Procedimiento usado en producción (despliegue/desplegar-cambios-docker.sh): primero se revisa sin tocar nada y luego se aplica con reversión automática.')
    p.marco('[activity] Despliegue seguro', 20, 70, 1460, 910, tipo='act')
    carril(p, 'Equipo de desarrollo (local)', 40, 110, 440, 850, '#EAF1FB')
    carril(p, 'AWS CloudShell', 500, 110, 440, 850, '#F1ECF8')
    carril(p, 'Servidor EC2 (Docker)', 960, 110, 500, 850, '#EAF6EA')
    i = inicio(p, 247, 150)
    a1 = accion(p, 'Programar cambio + pruebas automáticas con datos ficticios', 150, 195)
    a2 = accion(p, 'Construir paquete: nuevos.tgz + base.sha (SHA-256 del servidor)', 150, 300)
    a3 = accion(p, 'Subir paquete y ejecutar SOLO_REVISAR=1', 610, 300)
    d1 = decision(p, '¿Hash base coincide y SQL solo agrega?', 1135, 290)
    a4 = accion(p, 'Detener: no se toca nada', 1110, 420, 200)
    a5 = accion(p, 'Ejecutar despliegue real', 610, 520)
    a6 = accion(p, 'Respaldar MySQL, .env y archivos (~/respaldos-siged)', 1110, 520)
    a7 = accion(p, 'Construir imagen nueva FROM la actual y reiniciar solo app', 1110, 620)
    d2 = decision(p, '¿Sitio sano (salud / login)?', 1135, 720)
    a8 = accion(p, 'Fijar APP_IMAGE en .env', 1110, 850)
    a9 = accion(p, 'Reversión automática a la imagen y datos previos', 610, 730)
    f = fin(p, 1395, 860)
    for a, b, g in [(i, a1, ''), (a1, a2, ''), (a2, a3, ''), (a3, d1, ''), (d1, a4, '[no]'), (d1, a5, '[sí]'), (a5, a6, ''), (a6, a7, ''),
                    (a7, d2, ''), (d2, a8, '[sí]'), (d2, a9, '[no]'), (a8, f, '')]:
        p.arista(a, b, g, FLUJO, rutear=True)
    return p


def paginas():
    return [pag_ticket(), pag_actividad(), pag_tubo(), pag_recuperar(), pag_actividad_evidencia(), pag_estados(), pag_despliegue_seguro()]
