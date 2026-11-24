from drawio import Pagina, DERIVE, REFINE, CONTIENE
from contenido_req import EPICAS, RNF

NUEVO = '#FBE3E6'
COLOR_ESTADO = {'I': '#E3F2E1', 'P': '#FFF2C2', 'X': '#EEEEEE'}
NOMBRE_ESTADO = {'I': 'Implementado', 'P': 'Parcial', 'X': 'Propuesto'}


def leyenda(p, x, y):
    p.vertice('<b>Leyenda</b>', x, y, 250, 20, 'text;html=1;fontSize=11;align=left;')
    filas = [(NUEVO, 'Nuevo: Unidad 3 o codificado después de la Etapa 2'), ('#FFFFFF', 'Requerimiento de Unidades 1 y 2'),
             (COLOR_ESTADO['I'], 'Implementado y probado'), (COLOR_ESTADO['P'], 'Parcial'), (COLOR_ESTADO['X'], 'Propuesto (no implementado)')]
    for i, (color, texto) in enumerate(filas):
        p.vertice('', x, y + 24 + i * 22, 18, 14, f'rounded=0;fillColor={color};strokeColor=#333;')
        p.vertice(texto, x + 24, y + 20 + i * 22, 300, 20, 'text;html=1;fontSize=10;align=left;verticalAlign=middle;')


def alto_req(texto, w=330):
    return 64 + 13 * (len(texto) // int(w / 6.1) + 1)


def pagina_general():
    p = Pagina('01 Requerimientos · vista general', 1600, 1130)
    p.titulo('Diagrama de requerimientos · Vista general SIGED-SGR', 30, 10,
             sub='16 épicas derivadas del requerimiento raíz. Las épicas EP-13 a EP-16 incorporan el nuevo requerimiento del cliente (Unidad 3).')
    p.marco('[package] Requerimientos SIGED-SGR [Vista general]', 20, 70, 1550, 1030)
    w, gx, x0, y0 = 340, 40, 50, 280
    tronco = x0 + 2 * w + gx + gx / 2
    raiz = p.requisito('RQ-SIGED', 'Sistema de Gestión de Delegaciones (SIGED-SGR)',
                       'El sistema debe centralizar la atención ciudadana, la gestión interna y la medición de desempeño de las 6 delegaciones municipales de La Serena.',
                       tronco - 200, 105, 400, 100)
    for i, (eid, nombre, texto, nuevo, hus) in enumerate(EPICAS):
        f, c = divmod(i, 4)
        x, y = x0 + c * (w + gx), y0 + f * 175
        e = p.requisito(eid, nombre, texto + f' ({len(hus)} HU)', x, y, w, 100, NUEVO if nuevo else '#FFFFFF')
        bus = y - 25
        p.arista(raiz, e, '', CONTIENE + 'exitX=0.5;exitY=1;entryX=0.5;entryY=0;', puntos=[(tronco, bus), (x + w / 2, bus)])
    leyenda(p, 60, 960)
    p.nota('El símbolo ⊕ indica contención: cada épica es parte del requerimiento raíz. '
           'Cada épica se detalla en su propia página con «deriveReqt» (historias) y «refine» (criterios verificables).', 1150, 975, 400)
    return p


def pagina_epica(eid, nombre, texto, nuevo, hus, n):
    filas = []
    for hu in hus:
        h_hu = alto_req(hu[2])
        h_ref = sum(alto_req(r[1]) + 14 for r in hu[3]) - 14
        filas.append((hu, h_hu, max(h_hu, h_ref)))
    alto = 140 + sum(f[2] + 26 for f in filas)
    y_fin = alto - 20
    p = Pagina(f'{n:02d} {eid} {nombre}'[:60], 1400, y_fin + 200)
    p.titulo(f'Diagrama de requerimientos · {eid} {nombre}', 30, 10,
             sub='Épica → historias de usuario («deriveReqt») → criterios verificables («refine»). El color de cada criterio indica su estado en el código.')
    p.marco(f'[package] {eid} {nombre}', 20, 70, 1360, y_fin + 90)
    y = 120
    centro = 120 + (alto - 140) / 2
    epi = p.requisito(eid, nombre, texto, 40, centro - 60, 300, 130, NUEVO if nuevo else '#FFFFFF')
    for hu, h_hu, h_fila in filas:
        hid, hnom, htxt, refs, hnuevo = hu
        yh = y + (h_fila - h_hu) / 2
        nodo = p.requisito(hid, hnom, htxt, 470, yh, 330, h_hu, NUEVO if hnuevo else '#FFFFFF')
        p.arista(epi, nodo, '«deriveReqt»', DERIVE + 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;', pos_etiqueta=0.62)
        h_ref_total = sum(alto_req(r[1]) + 14 for r in refs) - 14
        yr = y + (h_fila - h_ref_total) / 2
        for rid, rtxt, est in refs:
            hr = alto_req(rtxt)
            r = p.requisito(rid, NOMBRE_ESTADO[est], rtxt, 960, yr, 330, hr, COLOR_ESTADO[est])
            p.arista(nodo, r, '«refine»', REFINE + 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;')
            yr += hr + 14
        y += h_fila + 26
    leyenda(p, 40, y_fin + 10)
    return p


def pagina_rnf(n):
    p = Pagina(f'{n:02d} Requerimientos no funcionales', 1400, 980)
    p.titulo('Diagrama de requerimientos · No funcionales', 30, 10,
             sub='Atributos de calidad que restringen a todas las épicas. RNF-09 y RNF-10 se agregan por la segunda y tercera evaluación (normas gráficas y OWASP).')
    p.marco('[package] Requerimientos no funcionales', 20, 70, 1360, 890)
    raiz = p.requisito('RQ-CAL', 'Calidad del servicio SIGED-SGR', 'El sistema debe operar de forma segura, confiable, usable y mantenible.', 520, 110, 360, 90)
    for i, (rid, nom, txt, nuevo) in enumerate(RNF):
        f, c = divmod(i, 2)
        x = 80 if c == 0 else 990
        y = 240 + f * 140
        r = p.requisito(rid, nom, txt, x, y, 330, 110, NUEVO if nuevo else '#FFFFFF')
        p.arista(raiz, r, '', CONTIENE + ('exitX=0;exitY=0.5;entryX=1;entryY=0.5;' if c == 0 else 'exitX=1;exitY=0.5;entryX=0;entryY=0.5;'),
                 puntos=[(500 if c == 0 else 900, 155), (500 if c == 0 else 900, y + 55)])
    p.nota('Cómo se cumple hoy (evidencia en el código y en el servidor):\n'
           '• RNF-01: permisos por grupo de rol + ámbito por delegación validado en servidor.\n'
           '• RNF-05/10: HTTPS en Apache, CSRF y cookies seguras de Django, hash de contraseñas.\n'
           '• RNF-07: cada despliegue respalda MySQL, .env y archivos y revierte solo si falla.\n'
           '• RNF-10: usuario MySQL de la aplicación solo con SELECT/INSERT/UPDATE/DELETE.\n'
           '• RNF-04: meta de diseño; la prueba de carga queda pendiente.', 470, 260, 470, 170)
    leyenda(p, 520, 820)
    return p


def paginas():
    ps = [pagina_general()]
    for i, e in enumerate(EPICAS, 2):
        ps.append(pagina_epica(*e, n=i))
    ps.append(pagina_rnf(len(ps) + 1))
    return ps
