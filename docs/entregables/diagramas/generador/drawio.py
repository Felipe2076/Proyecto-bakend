"""Mini librería para escribir archivos .drawio (mxGraph) con formas UML/SysML."""
from xml.sax.saxutils import escape
import html
import re

FUENTE = 'fontFamily=Arial;'
GRANATE = '#7A1F2B'


def esc(t):
    return escape(t, {'"': '&quot;'})


class Pagina:
    def __init__(self, nombre, ancho=1600, alto=1200):
        self.nombre = nombre
        self.ancho, self.alto = ancho, alto
        self.celdas = []
        self.n = 0
        self.cajas = {}      # id -> (x, y, w, h, obstaculo, forma) para el trazado de conectores
        self.pendientes = []  # conectores a trazar al final

    def _id(self):
        self.n += 1
        return f'c{self.n}'

    def vertice(self, etiqueta, x, y, w, h, estilo, padre='1', ident=None, obst=True, forma='rect'):
        i = ident or self._id()
        etiqueta = etiqueta.replace('\n', '<br>')
        if padre == '1':
            self.cajas[i] = (x, y, w, h, obst, forma)
        self.celdas.append(
            f'<mxCell id="{i}" value="{esc(etiqueta)}" style="{esc(FUENTE + estilo)}" vertex="1" parent="{padre}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def arista(self, a, b, etiqueta='', estilo='', puntos=None, ext_a='', ext_b='', rutear=False, pos_etiqueta=0):
        i = self._id()
        if rutear:
            self.pendientes.append((i, a, b, etiqueta, estilo, ext_a, ext_b, pos_etiqueta))
            return i
        return self._emitir_arista(i, a, b, etiqueta, estilo, puntos, ext_a, ext_b, pos_etiqueta)

    def _emitir_arista(self, i, a, b, etiqueta, estilo, puntos, ext_a, ext_b, pos_etiqueta=0, pos_ext=(-0.82, 0.82)):
        pts = ''
        if puntos:
            pts = '<Array as="points">' + ''.join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos) + '</Array>'
        self.celdas.append(
            f'<mxCell id="{i}" value="{esc(etiqueta)}" style="{esc(FUENTE + "html=1;fontSize=10;labelBackgroundColor=#ffffff;" + estilo)}" '
            f'edge="1" parent="1" source="{a}" target="{b}"><mxGeometry relative="1" as="geometry"'
            + (f' x="{pos_etiqueta}"' if pos_etiqueta else '') + f'>{pts}</mxGeometry></mxCell>')
        for texto, pos in ((ext_a, pos_ext[0]), (ext_b, pos_ext[1])):
            if texto:
                j = self._id()
                self.celdas.append(
                    f'<mxCell id="{j}" value="{esc(texto)}" style="{esc(FUENTE + "edgeLabel;html=1;fontSize=10;labelBackgroundColor=#ffffff;")}" '
                    f'vertex="1" connectable="0" parent="{i}"><mxGeometry x="{pos}" y="-10" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>')
        return i

    def flecha(self, x1, y1, x2, y2, etiqueta='', estilo='', puntos=None):
        """Arista libre entre dos puntos (para mensajes de secuencia)."""
        i = self._id()
        pts = ''
        if puntos:
            pts = '<Array as="points">' + ''.join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in puntos) + '</Array>'
        self.celdas.append(
            f'<mxCell id="{i}" value="{esc(etiqueta)}" style="{esc(FUENTE + "html=1;fontSize=10;verticalAlign=bottom;labelBackgroundColor=none;" + estilo)}" '
            f'edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
            f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>{pts}</mxGeometry></mxCell>')
        return i

    def redimensionar(self, i, w=None, h=None):
        """Cambia el tamaño de una caja ya creada (celda y registro de trazado)."""
        x, y, w0, h0, obst, forma = self.cajas[i]
        w, h = w or w0, h or h0
        self.cajas[i] = (x, y, w, h, obst, forma)
        for k, c in enumerate(self.celdas):
            if c.startswith(f'<mxCell id="{i}" '):
                self.celdas[k] = re.sub(r'width="[^"]*" height="[^"]*"', f'width="{w}" height="{h}"', c, count=1)
                break

    def _trazar_pendientes(self):
        if not self.pendientes:
            return
        from ruteo import Enrutador
        enr = Enrutador(self.ancho, self.alto, self.cajas)

        def largo(e):
            ax, ay, aw, ah = self.cajas[e[1]][:4]
            bx, by, bw, bh = self.cajas[e[2]][:4]
            return abs(ax + aw / 2 - bx - bw / 2) + abs(ay + ah / 2 - by - bh / 2)
        for i, a, b, etq, estilo, ext_a, ext_b, pos in sorted(self.pendientes, key=largo):
            ruta = enr.ruta(a, b)
            if not ruta:
                print(f'    sin ruta: {self.nombre} {a}->{b} {etq}')
                self._emitir_arista(i, a, b, etq, estilo, None, ext_a, ext_b, pos)
                continue
            (sx, sy), (tx, ty) = ruta[0], ruta[-1]
            ax, ay, aw, ah = self.cajas[a][:4]
            bx, by, bw, bh = self.cajas[b][:4]
            fijo = (f'edgeStyle=none;rounded=1;arcSize=6;exitX={(sx - ax) / aw:.4f};exitY={(sy - ay) / ah:.4f};exitDx=0;exitDy=0;'
                    f'exitPerimeter=0;entryX={(tx - bx) / bw:.4f};entryY={(ty - by) / bh:.4f};entryDx=0;entryDy=0;entryPerimeter=0;')
            limpio = ';'.join(s for s in estilo.split(';') if s and not s.startswith(('edgeStyle', 'rounded', 'exit', 'entry'))) + ';'
            # Etiqueta principal en el centro del tramo más largo; multiplicidades a ~24 px de cada extremo.
            tramos = [abs(x1 - x0) + abs(y1 - y0) for (x0, y0), (x1, y1) in zip(ruta, ruta[1:])]
            total = sum(tramos) or 1
            if not pos and etq:
                k = max(range(len(tramos)), key=lambda n: tramos[n])
                medio = sum(tramos[:k]) + tramos[k] / 2
                pos = round(2 * medio / total - 1, 3) or 0.001
            d = min(26, total * 0.3) / total * 2
            self._emitir_arista(i, a, b, etq, limpio + fijo, ruta[1:-1], ext_a, ext_b, pos, (round(-1 + d, 3), round(1 - d, 3)))
        self.pendientes = []

    def xml(self, idx):
        self._trazar_pendientes()
        cuerpo = ''.join(self.celdas)
        return (f'<diagram id="p{idx}" name="{esc(self.nombre)}"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" '
                f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.ancho}" '
                f'pageHeight="{self.alto}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{cuerpo}'
                f'</root></mxGraphModel></diagram>')

    # ---------- Formas comunes ----------
    def marco(self, titulo, x, y, w, h, tipo='req'):
        return self.vertice(f'<b>{tipo}</b> {html.escape(titulo)}', x, y, w, h,
                            f'shape=umlFrame;whiteSpace=wrap;html=1;width={min(560, 30 + 7 * len(titulo))};height=26;'
                            'boundedLbl=1;verticalAlign=middle;align=left;spacingLeft=6;fontSize=12;strokeColor=#333333;fillColor=none;', obst=False)

    def nota(self, texto, x, y, w, h=None):
        if h is None:
            lineas = sum(max(1, int(len(l) * 5.6 / (w - 20)) + 1) for l in texto.split('\n'))
            h = 22 + 14 * lineas
        return self.vertice(texto, x, y, w, h,
                            'shape=note;whiteSpace=wrap;html=1;size=14;align=left;verticalAlign=top;spacingLeft=6;'
                            'spacingTop=2;fontSize=10;fillColor=#FFF8E1;strokeColor=#B0A060;')

    def titulo(self, texto, x, y, w=1200, sub=''):
        etiqueta = f'<b style="font-size:20px;color:{GRANATE}">{html.escape(texto)}</b>'
        if sub:
            etiqueta += f'<br><span style="font-size:11px;color:#555">{html.escape(sub)}</span>'
        return self.vertice(etiqueta, x, y, w, 50, 'text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;')

    def requisito(self, ident, nombre, texto, x, y, w=330, h=None, color='#FFFFFF', estereotipo='requirement'):
        h = h or (70 + 13 * max(1, len(texto) // 52))
        etiqueta = (f'<div style="text-align:center">«{estereotipo}»<br><b>{html.escape(nombre)}</b></div>'
                    f'<hr size="1">Id: {html.escape(ident)}<br>Text: {html.escape(texto)}')
        return self.vertice(etiqueta, x, y, w, h,
                            f'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacingLeft=6;spacingRight=4;'
                            f'fontSize=10;fillColor={color};strokeColor=#333333;')

    def actor(self, nombre, x, y):
        return self.vertice(nombre, x, y, 34, 64,
                            'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;'
                            'fontStyle=1;fontSize=11;whiteSpace=nowrap;')

    def caso(self, nombre, x, y, w=190, h=62, color='#FFFFFF', punteado=False):
        return self.vertice(nombre, x, y, w, h,
                            f'ellipse;whiteSpace=wrap;html=1;fontStyle=1;fontSize=11;fillColor={color};strokeColor=#222222;'
                            + ('dashed=1;' if punteado else ''))

    def sistema(self, nombre, x, y, w, h):
        return self.vertice(nombre, x, y, w, h,
                            'rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;fontStyle=1;fontSize=13;fillColor=none;strokeColor=#222222;', obst=False)

    def clase(self, nombre, atributos, x, y, w=230, estereotipo='', metodos=(), color='#FFFFFF'):
        cab = (f'<p style="margin:0;margin-top:4px;text-align:center">' + (f'«{estereotipo}»<br>' if estereotipo else '') +
               f'<b>{html.escape(nombre)}</b></p><hr size="1">')
        cuerpo = '<p style="margin:0;margin-left:5px">' + '<br>'.join(html.escape(a) for a in atributos) + '</p>'
        if metodos:
            cuerpo += '<hr size="1"><p style="margin:0;margin-left:5px">' + '<br>'.join(html.escape(m) for m in metodos) + '</p>'
        extra = sum(max(0, int(len(a) * 5.7 / (w - 14)))  for a in atributos)
        h = 34 + 15 * (len(atributos) + extra) + (12 + 15 * len(metodos) if metodos else 0) + (14 if estereotipo else 0)
        return self.vertice(cab + cuerpo, x, y, w, h,
                            f'verticalAlign=top;align=left;overflow=fill;html=1;whiteSpace=wrap;fontSize=10;fillColor={color};strokeColor=#333333;'), h

    def paquete(self, nombre, x, y, w, h, color='#F7F7F7'):
        return self.vertice(nombre, x, y, w, h,
                            f'shape=folder;fontStyle=1;spacingTop=8;tabWidth={20 + 8 * len(nombre)};tabHeight=22;tabPosition=left;html=1;'
                            f'whiteSpace=wrap;verticalAlign=top;align=left;spacingLeft=8;fontSize=12;fillColor={color};strokeColor=#666666;', obst=False)

    def componente(self, nombre, detalle, x, y, w=220, h=80, color='#FFFFFF'):
        etiqueta = f'«component»<br><b>{html.escape(nombre)}</b>' + (f'<br><span style="font-size:9px">{html.escape(detalle)}</span>' if detalle else '')
        return self.vertice(etiqueta, x, y, w, h,
                            f'shape=component;align=center;spacingLeft=34;spacingRight=8;whiteSpace=wrap;html=1;fontSize=10;fillColor={color};strokeColor=#333333;')

    def nodo(self, nombre, x, y, w, h, color='#FFFFFF', estereotipo='device', contenedor=False):
        return self.vertice(f'«{estereotipo}»<br><b>{html.escape(nombre)}</b>', x, y, w, h,
                            f'shape=cube;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;darkOpacity=0.05;darkOpacity2=0.1;'
                            f'size=12;verticalAlign=top;fontSize=11;fillColor={color};strokeColor=#333333;', obst=not contenedor)

    def artefacto(self, nombre, x, y, w=180, h=46, color='#FFFFFF'):
        return self.vertice(f'«artifact»<br><b>{html.escape(nombre)}</b>', x, y, w, h,
                            f'shape=note;size=12;whiteSpace=wrap;html=1;fontSize=10;fillColor={color};strokeColor=#333333;')

    def bd(self, nombre, x, y, w=150, h=80, color='#FFFFFF'):
        return self.vertice(nombre, x, y, w, h,
                            f'shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fontSize=10;fillColor={color};strokeColor=#333333;',
                            forma='centro')

    # ---------- Clase UML estándar de draw.io (cabecera + filas editables) ----------
    @staticmethod
    def medida_clase(nombre, atributos, metodos=(), estereotipo=''):
        largo = max([len(nombre) + 4] + [len(a) for a in atributos] + [len(m) for m in metodos])
        w = max(190, int(largo * 6.2) + 26)
        cab = 40 if estereotipo else 26
        h = cab + 18 * len(atributos) + (8 + 18 * len(metodos) if metodos else 8)
        return w, h, cab

    def clase_uml(self, nombre, atributos, x, y, metodos=(), color='#DAE8FC', borde='#6C8EBF', estereotipo='', w=None):
        w0, h, cab = self.medida_clase(nombre, atributos, metodos, estereotipo)
        w = w or w0
        titulo = (f'«{estereotipo}»<br>' if estereotipo else '') + f'<b>{html.escape(nombre)}</b>'
        i = self.vertice(titulo, x, y, w, h,
                         f'swimlane;fontStyle=0;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize={cab};'
                         f'horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;html=1;'
                         f'fontSize=11;fillColor={color};strokeColor={borde};swimlaneFillColor=#FFFFFF;rounded=0;')
        fila = ('text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;spacingRight=4;overflow=hidden;'
                'rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;html=1;fontSize=10;')
        yy = cab
        for a in atributos:
            self.vertice(html.escape(a), 0, yy, w, 18, fila, padre=i)
            yy += 18
        self.vertice('', 0, yy, w, 8, 'line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;'
                     'spacingRight=3;rotatable=0;labelPosition=right;points=[];portConstraint=eastwest;strokeColor=inherit;', padre=i)
        yy += 8
        for m in metodos:
            self.vertice(html.escape(m), 0, yy, w, 18, fila, padre=i)
            yy += 18
        return i, w, h

    def caja(self, texto, x, y, w, h, color='#FFFFFF', borde='#333333', extra=''):
        return self.vertice(texto, x, y, w, h,
                            f'rounded=1;arcSize=8;whiteSpace=wrap;html=1;fontSize=10;fillColor={color};strokeColor={borde};' + extra)


# ---------- Estilos de aristas ----------
DERIVE = 'endArrow=open;endSize=10;dashed=1;edgeStyle=orthogonalEdgeStyle;rounded=0;'
REFINE = 'endArrow=open;endSize=10;dashed=1;edgeStyle=orthogonalEdgeStyle;rounded=0;'
CONTIENE = 'endArrow=none;startArrow=circlePlus;startFill=0;startSize=12;edgeStyle=orthogonalEdgeStyle;rounded=0;'
INCLUDE = 'endArrow=open;endSize=10;dashed=1;'
EXTEND = 'endArrow=open;endSize=10;dashed=1;'
ASOC = 'endArrow=none;'
ASOC_NAV = 'endArrow=open;endSize=10;'
ASOC_ORTO = 'endArrow=none;edgeStyle=orthogonalEdgeStyle;rounded=0;'
GENERAL = 'endArrow=block;endFill=0;endSize=12;'
DEPENDE = 'endArrow=open;dashed=1;endSize=10;'
FLUJO = 'endArrow=block;endFill=1;endSize=8;edgeStyle=orthogonalEdgeStyle;rounded=0;'
COMPOSICION = 'endArrow=none;startArrow=diamondThin;startFill=1;startSize=14;'


def guardar(ruta, paginas):
    contenido = '<mxfile host="SIGED" agent="generador" version="24.7.17">' + ''.join(p.xml(i) for i, p in enumerate(paginas, 1)) + '</mxfile>'
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)
    return ruta
