"""Small clearance-aware grid router used by rework_tps63070.py.

It reads the copper that is already on a pcbnew board, blocks every cell that
would break the 0.15 mm clearance for the net being routed, and runs an A*
search on F.Cu and B.Cu with through vias. Output is plain pcbnew tracks.
"""
import heapq
import math

import numpy as np
import pcbnew

CLR = 0.15
VIA_D = 0.50
VIA_DRILL = 0.25
MARGIN = 0.02
PITCH = 0.05
F, B = 0, 1
LAYER = {F: pcbnew.F_Cu, B: pcbnew.B_Cu}


def mm(v):
    return v / 1e6


def nm(v):
    return int(round(v * 1e6))


class Prim:
    __slots__ = ("kind", "net", "layers", "d", "w")

    def __init__(self, kind, net, layers, d, w=0.0):
        self.kind, self.net, self.layers, self.d, self.w = kind, net, layers, d, w

    def bbox(self):
        if self.kind == "rect":
            return self.d
        if self.kind == "circ":
            x, y, r = self.d
            return (x - r, y - r, x + r, y + r)
        x1, y1, x2, y2 = self.d
        h = self.w / 2
        return (min(x1, x2) - h, min(y1, y2) - h, max(x1, x2) + h, max(y1, y2) + h)

    def dist(self, X, Y):
        """Distance from points to the copper edge (negative inside)."""
        if self.kind == "rect":
            x0, y0, x1, y1 = self.d
            dx = np.maximum(np.maximum(x0 - X, X - x1), 0)
            dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
            return np.hypot(dx, dy)
        if self.kind == "circ":
            x, y, r = self.d
            return np.hypot(X - x, Y - y) - r
        x1, y1, x2, y2 = self.d
        vx, vy = x2 - x1, y2 - y1
        l2 = vx * vx + vy * vy
        if l2 == 0:
            return np.hypot(X - x1, Y - y1) - self.w / 2
        t = np.clip(((X - x1) * vx + (Y - y1) * vy) / l2, 0, 1)
        return np.hypot(X - (x1 + t * vx), Y - (y1 + t * vy)) - self.w / 2


def prims_of(items):
    prims = []
    for t in items:
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            prims.append(Prim("circ", t.GetNetname(), {F, B}, (mm(p.x), mm(p.y), mm(t.GetWidth(pcbnew.F_Cu)) / 2)))
        else:
            a, c = t.GetStart(), t.GetEnd()
            layer = F if t.GetLayer() == pcbnew.F_Cu else B
            prims.append(
                Prim("seg", t.GetNetname(), {layer}, (mm(a.x), mm(a.y), mm(c.x), mm(c.y)), mm(t.GetWidth()))
            )
    return prims


def collect(board, skip_items=()):
    prims = []
    skip = {id(i) for i in skip_items}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            rect = (mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom()))
            layers = set()
            if pad.IsOnLayer(pcbnew.F_Cu):
                layers.add(F)
            if pad.IsOnLayer(pcbnew.B_Cu):
                layers.add(B)
            if layers:
                prims.append(Prim("rect", pad.GetNetname(), layers, rect))
    for t in board.GetTracks():
        if id(t) in skip:
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            prims.append(Prim("circ", t.GetNetname(), {F, B}, (mm(p.x), mm(p.y), mm(t.GetWidth(pcbnew.F_Cu)) / 2)))
        else:
            a, c = t.GetStart(), t.GetEnd()
            layer = F if t.GetLayer() == pcbnew.F_Cu else B
            prims.append(
                Prim("seg", t.GetNetname(), {layer}, (mm(a.x), mm(a.y), mm(c.x), mm(c.y)), mm(t.GetWidth()))
            )
    return prims


class Router:
    def __init__(self, board, window, extra_blocks=()):
        self.board = board
        self.x0, self.y0, self.x1, self.y1 = window
        self.nx = int((self.x1 - self.x0) / PITCH) + 1
        self.ny = int((self.y1 - self.y0) / PITCH) + 1
        xs = self.x0 + np.arange(self.nx) * PITCH
        ys = self.y0 + np.arange(self.ny) * PITCH
        self.X, self.Y = np.meshgrid(xs, ys, indexing="ij")
        self.extra = list(extra_blocks)
        self.refresh()

    def refresh(self):
        self.prims = collect(self.board)
        self._cache = {}

    def cell(self, x, y):
        return int(round((x - self.x0) / PITCH)), int(round((y - self.y0) / PITCH))

    def pos(self, i, j):
        return self.x0 + i * PITCH, self.y0 + j * PITCH

    def _mark(self, mask, prim, need, layer_ok=True):
        bx0, by0, bx1, by1 = prim.bbox()
        i0 = max(0, int((bx0 - need - self.x0) / PITCH) - 1)
        i1 = min(self.nx, int((bx1 + need - self.x0) / PITCH) + 2)
        j0 = max(0, int((by0 - need - self.y0) / PITCH) - 1)
        j1 = min(self.ny, int((by1 + need - self.y0) / PITCH) + 2)
        if i0 >= i1 or j0 >= j1:
            return
        d = prim.dist(self.X[i0:i1, j0:j1], self.Y[i0:i1, j0:j1])
        mask[i0:i1, j0:j1] |= d < need

    def track_mask(self, net, width, layer):
        key = ("t", net, round(width, 3), layer)
        if key in self._cache:
            return self._cache[key]
        mask = np.zeros((self.nx, self.ny), dtype=bool)
        edge = 0.30 + width / 2
        mask[self.X < self.x0 + 0.0] = True
        for p in self.prims:
            if p.net == net and net != "":
                continue
            if layer not in p.layers:
                continue
            self._mark(mask, p, width / 2 + CLR + MARGIN)
        for rect in self.extra:
            self._mark(mask, Prim("rect", "", {F, B}, rect), width / 2 + CLR + MARGIN)
        self._cache[key] = mask
        return mask

    def via_mask(self, net):
        key = ("v", net)
        if key in self._cache:
            return self._cache[key]
        mask = np.zeros((self.nx, self.ny), dtype=bool)
        r = VIA_D / 2
        for p in self.prims:
            if p.net == net and net != "":
                if p.kind == "rect":
                    self._mark(mask, p, r + 0.10)
                elif p.kind == "circ":
                    self._mark(mask, p, 0.55 - r)
                continue
            self._mark(mask, p, r + CLR + MARGIN)
        for rect in self.extra:
            self._mark(mask, Prim("rect", "", {F, B}, rect), r + CLR + MARGIN)
        self._cache[key] = mask
        return mask

    def cells_of_prim(self, prim, layer, grow=0.0):
        mask = np.zeros((self.nx, self.ny), dtype=bool)
        if layer in prim.layers:
            self._mark(mask, prim, grow + 1e-9)
        return mask

    def route(self, net, width, sources, targets, via_cost=2.0, bend=0.15, allow_via=True, layers=(F, B), max_nodes=400000):
        """sources/targets: boolean masks (nx, ny) per layer dict {F: mask, B: mask}."""
        masks = {L: self.track_mask(net, width, L) for L in layers}
        vmask = self.via_mask(net) if allow_via else None
        for L in layers:
            masks[L] = masks[L].copy()
            masks[L] |= False
        # sources and targets are always enterable
        free = {L: (~masks[L]) | sources.get(L, False) | targets.get(L, False) for L in layers}
        tgt_any = np.zeros((self.nx, self.ny), dtype=bool)
        for L in layers:
            if L in targets:
                tgt_any |= targets[L]
        tl = np.argwhere(tgt_any)
        if len(tl) == 0:
            return None
        tcx, tcy = tl[:, 0].mean(), tl[:, 1].mean()
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        heap = []
        best = {}
        parent = {}
        for L in layers:
            if L in sources:
                for i, j in np.argwhere(sources[L] & free[L]):
                    k = (L, int(i), int(j), -1)
                    best[k] = 0.0
                    heapq.heappush(heap, (self._h(i, j, tcx, tcy), 0.0, k))
        n = 0
        goal = None
        while heap:
            f, g, k = heapq.heappop(heap)
            if best.get(k, 1e18) < g - 1e-12:
                continue
            L, i, j, d = k
            if targets.get(L) is not None and targets[L][i, j]:
                goal = k
                break
            n += 1
            if n > max_nodes:
                break
            for di, dj in dirs:
                ni, nj = i + di, j + dj
                if not (0 <= ni < self.nx and 0 <= nj < self.ny):
                    continue
                if not free[L][ni, nj]:
                    continue
                if di and dj and not (free[L][i + di, j] and free[L][i, j + dj]):
                    continue
                step = PITCH * (1.41421356 if di and dj else 1.0)
                nd = dirs.index((di, dj))
                cost = g + step + (bend if d >= 0 and nd != d else 0.0)
                if L == B:
                    cost += step * 0.15
                nk = (L, ni, nj, nd)
                if cost < best.get(nk, 1e18) - 1e-12:
                    best[nk] = cost
                    parent[nk] = k
                    heapq.heappush(heap, (cost + self._h(ni, nj, tcx, tcy), cost, nk))
            if allow_via and len(layers) == 2:
                if not vmask[i, j]:
                    O = B if L == F else F
                    if free[O][i, j]:
                        nk = (O, i, j, -1)
                        cost = g + via_cost
                        if cost < best.get(nk, 1e18) - 1e-12:
                            best[nk] = cost
                            parent[nk] = k
                            heapq.heappush(heap, (cost + self._h(i, j, tcx, tcy), cost, nk))
        if goal is None:
            return None
        path = [goal]
        while path[-1] in parent:
            path.append(parent[path[-1]])
        path.reverse()
        return [(L, i, j) for (L, i, j, _d) in path]

    @staticmethod
    def _h(i, j, tcx, tcy):
        return max(0.0, math.hypot(i - tcx, j - tcy) - 6) * PITCH * 0.8

    def to_segments(self, path):
        """Collapse the cell path to (layer, [points]) polylines plus via list."""
        polys = []
        vias = []
        cur = None
        for idx, (L, i, j) in enumerate(path):
            x, y = self.pos(i, j)
            if cur is None or cur[0] != L:
                if cur is not None:
                    vias.append((x, y))
                cur = [L, [(x, y)]]
                polys.append(cur)
            else:
                cur[1].append((x, y))
        out = []
        for L, pts in polys:
            red = [pts[0]]
            for k in range(1, len(pts) - 1):
                a, b, c = red[-1], pts[k], pts[k + 1]
                if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-9:
                    red.append(b)
            if len(pts) > 1:
                red.append(pts[-1])
            out.append((L, red))
        return out, vias

    def commit(self, net_name, width, polys, vias, snap=None):
        board = self.board
        net = board.FindNet(net_name)
        added = []
        for L, pts in polys:
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(nm(x1), nm(y1)))
                t.SetEnd(pcbnew.VECTOR2I(nm(x2), nm(y2)))
                t.SetWidth(nm(width))
                t.SetLayer(LAYER[L])
                t.SetNet(net)
                board.Add(t)
                added.append(t)
        for x, y in vias:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
            v.SetWidth(nm(VIA_D))
            v.SetDrill(nm(VIA_DRILL))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetNet(net)
            board.Add(v)
            added.append(v)
        self.refresh()
        return added

    def mask_of(self, prims_or_points, layer, grow=0.0):
        mask = np.zeros((self.nx, self.ny), dtype=bool)
        for p in prims_or_points:
            if layer in p.layers:
                self._mark(mask, p, grow + 1e-9)
        return mask
