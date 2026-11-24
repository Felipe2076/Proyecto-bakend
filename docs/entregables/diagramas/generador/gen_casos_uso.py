import html
from drawio import Pagina, INCLUDE, EXTEND, ASOC, GENERAL
from contenido_cu import CU

NUEVO = '#FBE3E6'
COLX = (300, 640, 980)
CW, CH, FILA, TOP = 250, 62, 100, 150
GEN_IZQ = GENERAL + 'exitX=0;exitY=0.3;entryX=0;entryY=0.7;edgeStyle=orthogonalEdgeStyle;rounded=0;'
BR = '\n'

ROLES = [  # (actor, descripción, módulos)
    ('Operador de ventanilla', 'Registra lo que llega por ventanilla, WhatsApp o correo.', 'Atención ciudadana · Agenda · Avisos · Encuestas'),
    ('Funcionario', 'Hace lo del operador y además registra su trabajo territorial.', '+ Indicadores y metas · Actividad y evidencia · Compromisos'),
    ('Jefatura', 'Hace lo del funcionario y supervisa la delegación.', '+ Panel de gestión · Mantenedores autorizados'),
    ('Administrador de delegación', 'Hace lo de jefatura y administra las cuentas de SU delegación.', '+ Administración (solo su delegación)'),
    ('Superusuario', 'Hace lo del administrador en las seis delegaciones y edita lo global.', 'Todo, con alcance global'),
]


def pagina_actores():
    p = Pagina('01 Actores y permisos', 1500, 900)
    p.titulo('Actores del sistema y jerarquía de permisos', 30, 10,
             sub='Tomado del código (cuentas/perfiles.py): cada rol incluye los módulos del anterior. Vecino, Servidor de correo y App móvil son actores externos.')
    p.marco('[package] Actores SIGED-SGR', 20, 70, 1460, 810, tipo='uc')
    ids = []
    for i, (nom, desc, mods) in enumerate(ROLES):
        y = 130 + i * 140
        ids.append(p.actor(nom, 150, y))
        p.caja(f'<b>{nom}</b><br>{desc}<br><span style="color:#7A1F2B">Módulos: {mods}</span>', 330, y + 2, 560, 62,
               '#FFFFFF' if i < 3 else NUEVO)
    for hijo, padre in zip(ids[1:], ids[:-1]):
        p.arista(hijo, padre, '', GEN_IZQ)
    externos = [('Vecino', 'Vecino (externo)', 'Origina el requerimiento. No tiene cuenta: responde la encuesta por un enlace firmado.'),
                ('Servidor de correo', 'Servidor de correo («system»)', 'Envía códigos de recuperación y enlaces de activación.'),
                ('App móvil SIGED', 'App móvil SIGED («system», en desarrollo)', 'Usa la API /api/v1/ con la cuenta del funcionario; nunca accede a MySQL.')]
    for i, (nom, tit, desc) in enumerate(externos):
        y = 130 + i * 150
        p.actor(nom, 1000, y)
        p.caja(f'<b>{tit}</b><br>{desc}', 1080, y + 2, 370, 62)
    p.nota('Cómo leer la jerarquía: la flecha de punta blanca (generalización) apunta al rol más general. '
           'Ej.: Jefatura → Funcionario significa que la jefatura puede hacer todo lo del funcionario.' + BR + BR +
           'El alcance se valida en el servidor: Operador, Funcionario, Jefatura y Administrador solo ven su delegación; '
           'el Superusuario ve las seis y es el único que edita delegaciones, roles, metas, cargos, tipos y trimestres.',
           1000, 600, 450, 160)
    return p


def pagina_general():
    p = Pagina('02 Caso de uso general', 1500, 1080)
    p.titulo('Diagrama de casos de uso general (alto nivel) · SIGED-SGR', 30, 10,
             sub='Cada actor se asocia solo con lo que agrega a su rol y hereda, por generalización, los casos de los roles de arriba. Rosado = nuevo (Unidad 3).')
    p.marco('[package] Casos de uso generales', 20, 70, 1460, 990, tipo='uc')
    p.sistema('SIGED-SGR · Delegaciones Municipales de La Serena', 560, 100, 560, 900)
    yact = {'Usuario interno': 130, 'Operador de ventanilla': 270, 'Funcionario': 460, 'Jefatura': 650,
            'Administrador de delegación': 790, 'Superusuario': 930}
    act, prev = {}, None
    for nom, y in yact.items():
        act[nom] = p.actor(nom, 360, y)
        if prev:
            p.arista(act[nom], act[prev], '', GEN_IZQ)
        prev = nom
    filas = [('Usuario interno', 'G06', 'CU-G06' + BR + 'Ingresar y recuperar acceso', True, 130, 'Servidor de correo'),
             ('Operador de ventanilla', 'G01', 'CU-G01' + BR + 'Atender requerimientos ciudadanos', False, 270, 'Vecino'),
             ('Funcionario', 'G02', 'CU-G02' + BR + 'Gestionar trabajo territorial', False, 400, 'App móvil SIGED'),
             ('Funcionario', 'G05', 'CU-G05' + BR + 'Gestionar organizaciones comunitarias', True, 520, None),
             ('Jefatura', 'G03', 'CU-G03' + BR + 'Supervisar resultados', False, 650, None),
             ('Administrador de delegación', 'G04', 'CU-G04' + BR + 'Administrar la plataforma', False, 790, None)]
    for izq, k, nombre, nuevo, y, der in filas:
        c = p.caso(nombre, 700, y - 8, 280, 80, NUEVO if nuevo else '#FFFFFF')
        p.arista(act[izq], c, '', ASOC)
        if der:
            etiqueta = der if der == 'Vecino' else '«system»' + BR + der
            p.arista(p.actor(etiqueta, 1270, y), c, '', ASOC)
        if k == 'G04':
            p.arista(act['Superusuario'], c, 'alcance global', ASOC)
    p.nota('Desglose en casos específicos:' + BR + 'CU-G01 → CU-E01, E06, E07, E08, E19' + BR +
           'CU-G02 → CU-E02, E03, E04, E11, E14, E20' + BR + 'CU-G03 → CU-E05, E09, E12, E16' + BR +
           'CU-G04 → CU-E10, E15, E18' + BR + 'CU-G05 → CU-E13' + BR + 'CU-G06 → CU-E17', 1160, 720, 300, 150)
    p.nota('Generalización (flecha blanca a la izquierda): cada rol hereda los casos del rol de arriba, '
           'por eso el diagrama no repite asociaciones.', 1160, 890, 300, 80)
    return p


def cuadro(c, incluidos, extendidos):
    filas = [('Identificador', c['id']), ('Nombre', c['nombre']), ('Caso general', c['general']),
             ('Actor principal', ', '.join(c['izq'])), ('Actores secundarios', ', '.join(c['der']) or '—'),
             ('Propósito', c['proposito']), ('Precondiciones', c['pre']), ('Postcondiciones', c['post']),
             ('Flujo principal', c['flujo']), ('Casos incluidos', ', '.join(incluidos) or 'Ninguno'),
             ('Casos extendidos', ', '.join(extendidos) or 'Ninguno'), ('Pantalla / ruta en el prototipo', c['ruta']),
             ('Estado en el código', c['estado'])]
    cuerpo = ''.join(f'<tr><td style="background:#F3E7E9;width:190px;padding:3px 6px"><b>{html.escape(k)}</b></td>'
                     f'<td style="padding:3px 6px">{html.escape(v)}</td></tr>' for k, v in filas)
    return (f'<table border="1" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:10px;border-color:#888">'
            f'<tr><td colspan="2" style="background:#7A1F2B;color:#fff;padding:4px 6px"><b>Cuadro de descripción · {html.escape(c["id"])} '
            f'{html.escape(c["nombre"])}</b></td></tr>{cuerpo}</table>')


def acomodar(c):
    """Calcula columna y fila de cada caso a partir de las relaciones.

    Columna 0: casos asociados a un actor (base). Columna 1: «include» y «extend» directos del caso base.
    Columna 2: extensiones o inclusiones de un caso de la columna 1, en su misma fila.
    """
    nombres = {k: n for k, n, *_ in c['casos']}
    prop = {k: pr for k, n, col, fila, pr in c['casos']}
    hijos = {}  # padre -> [hijo]
    for t, a, b in c['rel']:
        if t == 'i':
            hijos.setdefault(a, []).append(b)
        elif t == 'e':
            hijos.setdefault(b, []).append(a)
    bases = []
    for t, a, b in c['rel']:
        if t == 'a' and b not in bases and not any(b in v for v in hijos.values()):
            bases.append(b)
    for k in nombres:  # casos sin actor ni padre
        if k not in bases and not any(k in v for v in hijos.values()):
            bases.append(k)
    pos, fila = {}, 0
    for b in bases:
        nivel1 = [h for h in hijos.get(b, []) if h not in pos and h not in bases]
        inicio = fila
        for h in nivel1:
            pos[h] = (1, fila)
            nivel2 = [x for x in hijos.get(h, []) if x not in pos and x not in bases]
            for j, x in enumerate(nivel2):
                pos[x] = (2, fila + j)
            fila += max(1, len(nivel2))
        fin = max(fila, inicio + 1)
        pos[b] = (0, (inicio + fin - 1) / 2)
        fila = fin
    for k in nombres:
        pos.setdefault(k, (2, fila))
    return [(k, nombres[k], pos[k][0], pos[k][1], prop[k]) for k in nombres]


def pagina_detalle(c, n):
    c = dict(c, casos=acomodar(c))
    filas = int(max(f for _, _, _, f, _ in c['casos'])) + 1
    alto_diag = TOP + filas * FILA + 40
    p = Pagina(f'{n:02d} {c["id"]} {c["nombre"]}'[:60], 1400, alto_diag + 380)
    p.titulo(f'Caso de uso detallado · {c["id"]} {c["nombre"]}', 30, 10,
             sub=f'Pertenece a {c["general"]}. Estado en el código: {c["estado"]}. Pantalla: {c["ruta"]}')
    p.marco(f'[package] {c["id"]} {c["nombre"]}', 20, 70, 1360, alto_diag + 300, tipo='uc')
    derecha = max(COLX[col] + CW for _, _, col, _, _ in c['casos']) + 50
    p.sistema('SIGED-SGR', 260, 100, derecha - 260, alto_diag - 150)
    ids, nombres, ys, cols = {}, {}, {}, {}
    for k, nombre, col, fila, prop in c['casos']:
        nombres[k] = nombre
        ys[k] = TOP + fila * FILA
        cols[k] = col
        ids[k] = p.caso(nombre, COLX[col], ys[k], CW, CH, '#F2F2F2' if prop else '#FFFFFF', punteado=prop)
    # Actores: a la izquierda si se asocian a casos base; a la derecha si solo tocan casos internos.
    actores, ocupado, lados = {}, {'izq': [], 'der': []}, {}
    for nom in c['izq'] + c['der']:
        mis = [b for t, a, b in c['rel'] if t == 'a' and a == nom]
        lado = 'izq' if any(cols[b] == 0 for b in mis) else 'der'
        y = sum(ys[b] for b in mis) / len(mis) if mis else TOP
        while any(abs(y - o) < 115 for o in ocupado[lado]):
            y += 20
        ocupado[lado].append(y)
        etiqueta = ('«system»' + BR + nom) if nom == 'Servidor de correo' else nom
        actores[nom] = p.actor(etiqueta, 130 if lado == 'izq' else derecha + 70, y - 2)
        lados[nom] = lado
    inc, ext = [], []
    for tipo, a, b in c['rel']:
        if tipo == 'a':
            # Del costado del actor al extremo de la elipse más cercano: así la línea no cruza otros casos.
            if lados[a] == 'izq':
                p.arista(actores[a], ids[b], '', ASOC + 'exitX=1;exitY=0.5;exitPerimeter=0;entryX=0;entryY=0.5;entryPerimeter=0;')
            else:
                p.arista(actores[a], ids[b], '', ASOC + 'exitX=0;exitY=0.5;exitPerimeter=0;entryX=1;entryY=0.5;entryPerimeter=0;')
        elif tipo == 'i':
            p.arista(ids[a], ids[b], '«include»', INCLUDE)
            inc.append(nombres[b])
        else:
            p.arista(ids[a], ids[b], '«extend»', EXTEND)
            ext.append(nombres[a])
    inc, ext = list(dict.fromkeys(inc)), list(dict.fromkeys(ext))
    p.vertice(cuadro(c, inc, ext), 60, alto_diag + 30, 1280, 290,
              'text;html=1;whiteSpace=wrap;overflow=fill;verticalAlign=top;align=left;fontSize=10;')
    return p


def paginas():
    return [pagina_actores(), pagina_general()] + [pagina_detalle(c, i) for i, c in enumerate(CU, 3)]
