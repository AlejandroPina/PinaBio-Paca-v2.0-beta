#!/usr/bin/env python3
"""Move the TPS63070 corner of the committed board to the TI pin order.

The first board carried U3 as a vertical mirror of the TI land pattern. This
script swaps the footprint, turns U3 so that pins 12-15 (VIN, EN, VSEL) look
at the SYS rail and pins 5-8 (FB, FB2, VOUT) at the 3V3 caps, puts the
inductor east of pins 9-11, and re-routes only what moved. The rest of the
board, the planes, the antenna keep-out and the silkscreen are left as they
were.

usage: rework_tps63070.py SRC.kicad_pcb DST.kicad_pcb
"""
import math
import sys
from pathlib import Path

import pcbnew

import rw_router as rr
from rw_router import F, B

ROOT = Path(__file__).resolve().parent

U3_POS = (15.545, 22.995)
L1_POS = (19.80, 23.295)
CLR_MM = 0.15
# plane vias that lost their stub when the neighbouring parts moved
ORPHAN_VIAS = [(15.119, 25.379), (11.452, 29.584), (24.703, 22.493)]
ZONE = {"/GND", "/AGND", "/3V3_SYS"}


def nm(v):
    return int(round(v * 1e6))


def V(x, y):
    return pcbnew.VECTOR2I(nm(x), nm(y))


def court(fp):
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False, False)
    return (bb.GetX() / 1e6, bb.GetY() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6)


def boxes_overlap(a, b, gap=0.0):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def pose(fp, x, y, rot):
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    fp.SetPosition(V(x, y))


_KEEP = []


def find(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    raise SystemExit(f"no {ref}")


def swap_u3(board):
    old = find(board, "U3")
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    lib = pcbnew.FootprintLoad(str(ROOT / "lib.pretty"), "TPS63070RNM")
    if lib is None:
        raise SystemExit("TPS63070RNM missing from lib.pretty")
    old.SetOrientation(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    _KEEP.append(lib)
    old_pads = list(old.Pads())
    old_gfx = list(old.GraphicalItems())
    for p in old_pads:
        old.Remove(p)
    for g in old_gfx:
        old.Remove(g)
    _KEEP.extend(old_pads + old_gfx)
    old.SetPosition(V(0, 0))
    for p in lib.Pads():
        d = p.Duplicate()
        old.Add(d)
        d.SetNet(nets[d.GetNumber()])
    for g in lib.GraphicalItems():
        old.Add(g.Duplicate())
    # Keep the library nickname. The pad geometry above is the corrected RNM.
    old.SetFPID(pcbnew.LIB_ID("PinaCursor", "TPS63070RNM"))
    old.SetLibDescription(lib.GetLibDescription())
    old.SetKeywords(lib.GetKeywords())
    old.SetPosition(V(*U3_POS))
    old.Reference().SetPosition(V(U3_POS[0], U3_POS[1] - 2.3))
    old.Value().SetPosition(V(U3_POS[0], U3_POS[1] + 2.3))
    for t in (old.Reference(), old.Value()):
        t.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    return old


def free_spot(board, fp, near, rots=(0, 90, 180, 270), radius=7.0, step=0.1, gap=0.05, avoid=()):
    """Closest legal courtyard position to near, same footprint pose list."""
    others = [(f.GetReference(), court(f)) for f in board.GetFootprints() if f is not fp]
    others += [("keep", b) for b in avoid]
    best = None
    n = int(radius / step)
    for di in range(-n, n + 1):
        for dj in range(-n, n + 1):
            x, y = near[0] + di * step, near[1] + dj * step
            d = math.hypot(x - near[0], y - near[1])
            if d > radius or (best and d >= best[0]):
                continue
            for rot in rots:
                pose(fp, x, y, rot)
                bx = court(fp)
                if any(boxes_overlap(bx, o, gap) for _r, o in others):
                    continue
                best = (d, x, y, rot)
                break
    if best is None:
        raise SystemExit(f"no spot for {fp.GetReference()}")
    pose(fp, best[1], best[2], best[3])
    return best



def ref_of(item):
    return item.GetParentFootprint().GetReference()


def pad_prims(fps):
    out = []
    for f in fps:
        for p in f.Pads():
            bb = p.GetBoundingBox()
            out.append(rr.Prim("rect", p.GetNetname(), {F}, (bb.GetX() / 1e6, bb.GetY() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6)))
    return out


def violates(item, prims, margin=0.0):
    """True if a track or via of the board breaks clearance against any foreign prim."""
    import numpy as np

    if item.GetClass() == "PCB_VIA":
        p = item.GetPosition()
        pts = [(p.x / 1e6, p.y / 1e6)]
        half = item.GetWidth(pcbnew.F_Cu) / 2e6
        layers = {F, B}
    else:
        a, c = item.GetStart(), item.GetEnd()
        x1, y1, x2, y2 = a.x / 1e6, a.y / 1e6, c.x / 1e6, c.y / 1e6
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / 0.02))
        pts = [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n) for k in range(n + 1)]
        half = item.GetWidth() / 2e6
        layers = {F if item.GetLayer() == pcbnew.F_Cu else B}
    X = np.array([q[0] for q in pts])
    Y = np.array([q[1] for q in pts])
    for pr in prims:
        if pr.net == item.GetNetname() and pr.net != "":
            continue
        if not (pr.layers & layers):
            continue
        if (pr.dist(X, Y) - half < CLR_MM - 1e-6 + margin).any():
            return True
    return False


def remove_items(board, items):
    for it in items:
        board.Remove(it)
    _KEEP.extend(items)


def rip(board):
    """Take out the copper that belonged to the old pin order."""
    gone = []
    for t in list(board.GetTracks()):
        net = t.GetNetname()
        a, c = t.GetStart(), t.GetEnd()
        via = t.GetClass() == "PCB_VIA"
        top = t.GetLayer() == pcbnew.F_Cu
        if net in ("/SW_L1", "/SW_L2", "/VAUX", "/FB"):
            gone.append(t)
        elif net == "/ILIM":
            gone.append(t)
        elif net == "/TPS_EN" and top and not via and a.y / 1e6 > 19.0:
            gone.append(t)
    remove_items(board, gone)
    print("ripped", len(gone))


def conflicts(board, prims, keep_ids=()):
    bad = [t for t in board.GetTracks() if id(t) not in keep_ids and violates(t, prims)]
    for t in bad:
        a = t.GetStart()
        print("  conflict", t.GetClass(), t.GetNetname(), a.x / 1e6, a.y / 1e6)
    remove_items(board, bad)
    return len(bad)


def islands(board, net):
    return islands_of([p for p in rr.collect(board) if p.net == net])


def touching(a, b):
    import numpy as np

    if not (a.layers & b.layers):
        return False
    if a.kind == "rect" and b.kind == "rect":
        ax0, ay0, ax1, ay1 = a.d
        bx0, by0, bx1, by1 = b.d
        return not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)
    for src, dst in ((a, b), (b, a)):
        if src.kind == "rect":
            x0, y0, x1, y1 = src.d
            pts = [((x0 + x1) / 2, (y0 + y1) / 2), (x0, y0), (x1, y0), (x0, y1), (x1, y1)]
            if dst.kind == "rect":
                continue
        elif src.kind == "circ":
            pts = [(src.d[0], src.d[1])]
        else:
            pts = [(src.d[0], src.d[1]), (src.d[2], src.d[3])]
        for px, py in pts:
            if dst.dist(np.array([px]), np.array([py]))[0] <= 0.002:
                return True
    return False


def prune_dangling(board, window):
    x0, y0, x1, y1 = window
    removed = 0
    for _ in range(8):
        items = [t for t in board.GetTracks()]
        prims = rr.prims_of(items)
        pads = [p for p in rr.collect(board) if p.kind == "rect"]
        bad = []
        for it, pr in zip(items, prims):
            cx = (pr.bbox()[0] + pr.bbox()[2]) / 2
            cy = (pr.bbox()[1] + pr.bbox()[3]) / 2
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                continue
            others = [q for q in prims if q is not pr and q.net == pr.net] + [q for q in pads if q.net == pr.net]
            if pr.kind == "circ":
                if pr.net in ZONE:
                    continue
                if not any(touching(pr, q) for q in others if q.kind != "circ"):
                    bad.append(it)
            else:
                ends = []
                for ex, ey in ((pr.d[0], pr.d[1]), (pr.d[2], pr.d[3])):
                    ends.append(rr.Prim("circ", pr.net, pr.layers, (ex, ey, 0.001)))
                if not all(any(touching(e, q) for q in others) for e in ends):
                    bad.append(it)
        if not bad:
            break
        for it in bad:
            a = it.GetStart()
            print("  prune", it.GetClass(), it.GetNetname(), round(a.x / 1e6, 3), round(a.y / 1e6, 3))
        remove_items(board, bad)
        removed += len(bad)
    return removed


def islands_of(prims):
    # pads of one footprint with the same number are one copper island
    n = len(prims)
    par = list(range(n))

    def find_(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def key_points(p):
        if p.kind == "rect":
            x0, y0, x1, y1 = p.d
            return [((x0 + x1) / 2, (y0 + y1) / 2)]
        if p.kind == "circ":
            return [(p.d[0], p.d[1])]
        return [(p.d[0], p.d[1]), (p.d[2], p.d[3])]

    import numpy as np

    for i in range(n):
        for j in range(i + 1, n):
            a, b = prims[i], prims[j]
            if not (a.layers & b.layers):
                continue
            hit = False
            for src, dst in ((a, b), (b, a)):
                pts = key_points(src)
                if src.kind == "rect":
                    x0, y0, x1, y1 = src.d
                    pts = pts + [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
                    if dst.kind == "rect":
                        continue
                for px, py in pts:
                    if dst.dist(np.array([px]), np.array([py]))[0] <= 0.002:
                        hit = True
                        break
                if hit:
                    break
            if a.kind == "rect" and b.kind == "rect":
                ax0, ay0, ax1, ay1 = a.d
                bx0, by0, bx1, by1 = b.d
                hit = not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0)
            if hit:
                par[find_(i)] = find_(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find_(i), []).append(prims[i])
    return list(groups.values())


def group_mask(rt, group, grow=0.0):
    return {L: rt.mask_of([p for p in group], L, grow) for L in (F, B)}


def route_islands(board, rt, net, widths, via_cost=2.0, window_pad=None):
    ok = True
    for _ in range(12):
        gs = islands(board, net)
        if len(gs) <= 1:
            return True
        gs.sort(key=lambda g: -sum(1 for p in g if p.kind == "rect"))
        src = gs[0]
        done = False
        for tgt in sorted(gs[1:], key=lambda g: min(
            math.hypot((a.bbox()[0] + a.bbox()[2]) / 2 - (b.bbox()[0] + b.bbox()[2]) / 2,
                       (a.bbox()[1] + a.bbox()[3]) / 2 - (b.bbox()[1] + b.bbox()[3]) / 2)
            for a in g for b in src)):
            for w in widths:
                sm = group_mask(rt, src)
                tm = group_mask(rt, tgt)
                path = rt.route(net, w, sm, tm, via_cost=via_cost)
                if path is None:
                    continue
                polys, vias = rt.to_segments(path)
                rt.commit(net, w, polys, vias)
                print(f"  routed {net} w={w} len={sum(math.hypot(b[0]-a[0], b[1]-a[1]) for _L, pts in polys for a, b in zip(pts, pts[1:])):.2f} vias={len(vias)}")
                done = True
                break
            if done:
                break
        if not done:
            print("  FAILED", net, len(gs), "islands")
            return False
    return ok


def add_poly(board, net, width, layer, pts):
    t_net = board.FindNet(net)
    items = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(x1, y1))
        t.SetEnd(V(x2, y2))
        t.SetWidth(nm(width))
        t.SetLayer(layer)
        t.SetNet(t_net)
        board.Add(t)
        items.append(t)
    return items


def add_via(board, net, x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(x, y))
    v.SetWidth(nm(0.5))
    v.SetDrill(nm(0.25))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetNet(board.FindNet(net))
    board.Add(v)
    return v


def window_islands(board, net, window):
    x0, y0, x1, y1 = window
    prims = [p for p in rr.collect(board) if p.net == net]
    prims = [p for p in prims if x0 <= (p.bbox()[0] + p.bbox()[2]) / 2 <= x1 and y0 <= (p.bbox()[1] + p.bbox()[3]) / 2 <= y1]
    return prims


def stitch_group(rt, net, group, width=0.2, reach=3.0):
    """Short F.Cu stub from an island of plane copper to the nearest legal via."""
    import numpy as np

    vm = rt.via_mask(net)
    tm = rt.track_mask(net, width, F)
    near = rt.mask_of(group, F, grow=reach)
    tgt = (~vm) & (~tm) & near
    src = {F: rt.mask_of(group, F)}
    path = rt.route(net, width, src, {F: tgt}, allow_via=False, layers=(F,))
    if path is None:
        return False
    polys, _v = rt.to_segments(path)
    x, y = rt.pos(path[-1][1], path[-1][2])
    rt.commit(net, width, polys, [(x, y)])
    return True


def stitch_missing(board, rt, window, nets=("/GND", "/3V3_SYS"), width_for=None):
    x0, y0, x1, y1 = window
    for net in nets:
        for _ in range(40):
            rt.refresh()
            prims = window_islands(board, net, window)
            # union by touching, reusing islands() on the window subset
            groups = islands_of(prims)
            todo = [g for g in groups if any(p.kind == "rect" for p in g) and not any(p.kind == "circ" for p in g)]
            if not todo:
                break
            g = todo[0]
            w = 0.35 if any(abs((p.bbox()[2] - p.bbox()[0])) > 0.3 and abs(p.bbox()[3] - p.bbox()[1]) > 0.6 for p in g if p.kind == "rect") else 0.2
            if not stitch_group(rt, net, g, w) and not stitch_group(rt, net, g, 0.15):
                p = g[0]
                print("  stitch FAILED", net, [round(v, 2) for v in p.bbox()])
                break
            print("  stitched", net, [round(v, 2) for v in g[0].bbox()])


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    swap_u3(board)
    fp = {r: find(board, r) for r in ("L1", "C11", "R8", "R13", "R14", "U3")}
    pose(fp["U3"], *U3_POS, 0)
    pose(fp["L1"], *L1_POS, 270)
    pose(fp["C11"], 12.10, 23.245, 180)
    pose(fp["R14"], 12.10, 24.90, 180)
    pose(fp["R13"], 15.00, 27.10, 90)
    pose(fp["R8"], 18.30, 15.90, 0)
    rip(board)
    moved = pad_prims(fp.values())
    print("conflicts vs moved parts", conflicts(board, moved))

    # switch node: straight F.Cu, 0.40 mm, no vias, between the two PGND vias
    mine = []
    mine += add_poly(board, "/SW_L1", 0.40, pcbnew.F_Cu, [(16.30, 22.38), (18.60, 22.38)])
    mine += add_poly(board, "/SW_L2", 0.40, pcbnew.F_Cu, [(16.30, 23.62), (17.60, 23.62), (18.40, 24.42)])
    mine += add_poly(board, "/GND", 0.35, pcbnew.F_Cu, [(16.95, 22.995), (17.45, 22.995), (18.15, 23.10)])
    mine += [add_via(board, "/GND", 17.45, 22.995), add_via(board, "/GND", 18.15, 23.10)]
    print("conflicts vs manual", conflicts(board, rr.prims_of(mine), keep_ids={id(i) for i in mine}))
    rt = rr.Router(board, (4.0, 12.0, 30.0, 34.0))
    for net, widths in (
        ("/SYS", (0.35, 0.25, 0.20)),
        ("/TPS_EN", (0.15,)),
        ("/VAUX", (0.20, 0.15)),
        ("/FB", (0.15,)),
        ("/ILIM", (0.15,)),
        ("/SDA_MOD", (0.15,)),
        ("/PPG_INT", (0.15,)),
        ("/Q1G", (0.15,)),
        ("/VLOG", (0.15,)),
        ("/BAT_PROT", (0.25, 0.15)),
    ):
        rt.refresh()
        print(net)
        route_islands(board, rt, net, widths)
    prune_dangling(board, (4.0, 12.0, 30.0, 34.0))
    orphans = [
        v for v in board.GetTracks()
        if v.GetClass() == "PCB_VIA" and any(
            abs(v.GetPosition().x / 1e6 - x) < 0.01 and abs(v.GetPosition().y / 1e6 - y) < 0.01
            for x, y in ORPHAN_VIAS)
    ]
    remove_items(board, orphans)
    rt.refresh()
    stitch_missing(board, rt, (7.0, 14.0, 30.0, 33.0))
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
