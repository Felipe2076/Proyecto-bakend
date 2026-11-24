"""Trazado ortogonal de conectores que esquiva las cajas (A* sobre una grilla de 10 px).

Cada conector sale perpendicular a un lado de su caja de origen y entra perpendicular a un lado de la caja destino.
Penaliza los quiebres y los puntos ya usados por otros conectores, para que las líneas no se monten.
"""
import heapq
import math

G = 10
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))
QUIEBRE = 6
USO = 5
MARGEN = 14   # distancia mínima entre una línea y una caja ajena
SEP = 20      # largo del tramo recto al salir/entrar de una caja


def _contiene(c, a):
    return c[0] <= a[0] and c[1] <= a[1] and c[0] + c[2] >= a[0] + a[2] and c[1] + c[3] >= a[1] + a[3]


class Enrutador:
    def __init__(self, ancho, alto, cajas):
        self.W, self.H = int(ancho / G) + 1, int(alto / G) + 1
        self.cajas = cajas          # id -> (x, y, w, h, obstaculo, forma)
        self.uso = {}
        self.puertos = {}   # caja -> [punto de anillo usado]
        self._bloq = {}
        for k, (x, y, w, h, obst, _) in cajas.items():
            if obst:
                i0, i1 = int((x - MARGEN) // G), int((x + w + MARGEN) // G) + 1
                j0, j1 = int((y - MARGEN) // G), int((y + h + MARGEN) // G) + 1
                self._bloq[k] = {(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)
                                 if x - MARGEN <= i * G <= x + w + MARGEN and y - MARGEN <= j * G <= y + h + MARGEN}

    def _bloqueados(self, a, b):
        ca, cb = self.cajas[a], self.cajas[b]
        bloq = set()
        for k, pts in self._bloq.items():
            c = self.cajas[k]
            if k in (a, b) or _contiene(c, ca) or _contiene(c, cb) or _contiene(ca, c) or _contiene(cb, c):
                continue
            bloq |= pts
        return bloq

    def _anillo(self, k, bloq):
        """Puntos de salida alrededor de la caja: (punto_grilla, dirección_hacia_afuera, puerto_px)."""
        x, y, w, h, _, forma = self.cajas[k]
        res = []
        lados = []
        if forma == 'centro':
            cx, cy = round((x + w / 2) / G), round((y + h / 2) / G)
            lados = [((cx,), 'arriba'), ((cx,), 'abajo'), ((cy,), 'izq'), ((cy,), 'der')]
        else:
            xs = list(range(int((x + 12) // G) + 1, int((x + w - 12) // G) + 1))
            ys = list(range(int((y + 10) // G) + 1, int((y + h - 10) // G) + 1))
            lados = [(xs, 'arriba'), (xs, 'abajo'), (ys, 'izq'), (ys, 'der')]
        for valores, lado in lados:
            for v in valores:
                if lado == 'arriba':
                    p, d, puerto = (v, math.floor((y - SEP) / G)), (0, -1), (v * G, y)
                elif lado == 'abajo':
                    p, d, puerto = (v, math.ceil((y + h + SEP) / G)), (0, 1), (v * G, y + h)
                elif lado == 'izq':
                    p, d, puerto = (math.floor((x - SEP) / G), v), (-1, 0), (x, v * G)
                else:
                    p, d, puerto = (math.ceil((x + w + SEP) / G), v), (1, 0), (x + w, v * G)
                if p not in bloq and 0 <= p[0] < self.W and 0 <= p[1] < self.H:
                    res.append((p, d, puerto))
        return res

    def ruta(self, a, b):
        bloq = self._bloqueados(a, b)
        inicios, metas = self._anillo(a, bloq), self._anillo(b, bloq)
        if not inicios or not metas:
            return None
        meta = {p: (d, puerto) for p, d, puerto in metas}
        bx, by, bw, bh = self.cajas[b][:4]
        bx0, bx1, by0, by1 = (bx - SEP) / G, (bx + bw + SEP) / G, (by - SEP) / G, (by + bh + SEP) / G

        def heur(p):
            dx = max(bx0 - p[0], 0, p[0] - bx1)
            dy = max(by0 - p[1], 0, p[1] - by1)
            return dx + dy

        abiertos, mejor_g, padre = [], {}, {}
        def castigo_puerto(caja, p):
            return sum(25 for q in self.puertos.get(caja, []) if abs(q[0] - p[0]) + abs(q[1] - p[1]) <= 3)

        for p, d, puerto in inicios:
            g = self.uso.get(p, 0) * USO + castigo_puerto(a, p)
            estado = (p, d)
            if g < mejor_g.get(estado, 1e9):
                mejor_g[estado] = g
                padre[estado] = ('inicio', puerto)
                heapq.heappush(abiertos, (g + heur(p), g, p, d))
        mejor, fin = 1e18, None
        while abiertos:
            f, g, p, d = heapq.heappop(abiertos)
            if f >= mejor:
                break
            if g > mejor_g.get((p, d), 1e9):
                continue
            if p in meta:
                dentro = (-meta[p][0][0], -meta[p][0][1])
                total = g + castigo_puerto(b, p) + (0 if d == dentro else QUIEBRE * (2 if d == (-dentro[0], -dentro[1]) else 1))
                if total < mejor:
                    mejor, fin = total, (p, d)
            for nd in DIRS:
                if nd == (-d[0], -d[1]):
                    continue
                q = (p[0] + nd[0], p[1] + nd[1])
                if q in bloq or not (0 <= q[0] < self.W and 0 <= q[1] < self.H):
                    continue
                ng = g + 1 + (QUIEBRE if nd != d else 0) + self.uso.get(q, 0) * USO
                if ng < mejor_g.get((q, nd), 1e9):
                    mejor_g[(q, nd)] = ng
                    padre[(q, nd)] = (p, d)
                    heapq.heappush(abiertos, (ng + heur(q), ng, q, nd))
        if fin is None:
            return None
        camino, estado = [], fin
        while True:
            camino.append(estado[0])
            ant = padre[estado]
            if ant[0] == 'inicio':
                puerto_a = ant[1]
                break
            estado = ant
        camino.reverse()
        self.puertos.setdefault(a, []).append(camino[0])
        self.puertos.setdefault(b, []).append(camino[-1])
        for q in camino:
            self.uso[q] = self.uso.get(q, 0) + 1
        puerto_b = meta[fin[0]][1]
        pts = [puerto_a] + [(i * G, j * G) for i, j in camino] + [puerto_b]
        limpio = [pts[0]]
        for k in range(1, len(pts) - 1):
            (x0, y0), (x1, y1), (x2, y2) = limpio[-1], pts[k], pts[k + 1]
            if (x0 == x1 == x2) or (y0 == y1 == y2):
                continue
            limpio.append(pts[k])
        limpio.append(pts[-1])
        return limpio
