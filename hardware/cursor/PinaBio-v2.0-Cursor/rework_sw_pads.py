#!/usr/bin/env python3
"""Replace onboard SW1 with six wire pads and move only the copper that the holes cut.

The DPDT stays in the enclosure. Pad nets stay 1=VLOG, 2=EN2_CE, 3=GND,
4=BAT_PROT, 5=TPS_EN, 6=VLOG. U3, L1, the planes, NT1, J5 and the antenna
keep-out are not moved. Zones are refilled at the end.

usage: rework_sw_pads.py SRC.kicad_pcb DST.kicad_pcb
"""
import math
import sys
from pathlib import Path

import pcbnew

import rw_router as rr
from rework_tps63070 import group_mask, islands

ROOT = Path(__file__).resolve().parent
FP_DIR = ROOT / "lib.pretty"
FP_NAME = "SW_ext_6pad"
PAD_R = 0.75
DRILL_R = 0.50
CLR = 0.15
KEEP = []

# Local pad centers, same places as the C&K JS202011 pads.
LOCAL = {
    "1": (-2.5, -1.2),
    "2": (0.0, -1.2),
    "3": (2.5, -1.2),
    "4": (-2.5, 1.2),
    "5": (0.0, 1.2),
    "6": (2.5, 1.2),
}


def nm(v):
    return int(round(v * 1e6))


def mm(v):
    return v / 1e6


def V(x, y):
    return pcbnew.VECTOR2I(nm(x), nm(y))


def find(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    raise SystemExit(f"no {ref}")


def dist_seg(px, py, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    l2 = vx * vx + vy * vy
    if l2 < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / l2))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def seg_gap(x1, y1, x2, y2, x3, y3, x4, y4):
    """Minimum distance between two segments. Crossing segments return 0."""
    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)

    o1 = orient(x1, y1, x2, y2, x3, y3)
    o2 = orient(x1, y1, x2, y2, x4, y4)
    o3 = orient(x3, y3, x4, y4, x1, y1)
    o4 = orient(x3, y3, x4, y4, x2, y2)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return 0.0
    return min(
        dist_seg(x1, y1, x3, y3, x4, y4),
        dist_seg(x2, y2, x3, y3, x4, y4),
        dist_seg(x3, y3, x1, y1, x2, y2),
        dist_seg(x4, y4, x1, y1, x2, y2),
    )


def pad_centers(origin):
    ox, oy = origin
    return {n: (ox + x, oy + y) for n, (x, y) in LOCAL.items()}


def swap_sw(board):
    old = find(board, "SW1")
    pos = old.GetPosition()
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    lib = pcbnew.FootprintLoad(str(FP_DIR), FP_NAME)
    if lib is None:
        raise SystemExit(f"missing {FP_NAME}")
    KEEP.append(lib)
    gone = list(old.Pads()) + list(old.GraphicalItems())
    for it in gone:
        old.Remove(it)
    KEEP.extend(gone)
    old.SetPosition(V(0, 0))
    for p in lib.Pads():
        d = p.Duplicate()
        old.Add(d)
        d.SetNet(nets[d.GetNumber()])
    for g in lib.GraphicalItems():
        old.Add(g.Duplicate())
    old.SetFPID(pcbnew.LIB_ID("PinaCursor", FP_NAME))
    old.Models().clear()
    old.SetLibDescription(lib.GetLibDescription())
    old.SetKeywords(lib.GetKeywords())
    old.SetAttributes(lib.GetAttributes())
    old.SetValue("DPDT caja")
    old.Value().SetLayer(pcbnew.F_Fab)
    old.Value().SetTextSize(V(0.5, 0.5))
    old.Value().SetTextThickness(nm(0.08))
    old.Reference().SetLayer(pcbnew.F_Fab)
    old.Reference().SetTextSize(V(0.5, 0.5))
    old.Reference().SetTextThickness(nm(0.08))
    old.SetPosition(pos)
    ox, oy = mm(pos.x), mm(pos.y)
    old.Reference().SetPosition(V(ox - 6.3, oy))
    old.Value().SetPosition(V(ox, oy + 3.9))
    print("SW1 pads", {n: nets[n].GetNetname() for n in nets})
    return old, (ox, oy)


def tracks_of(board):
    out = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            continue
        a, c = t.GetStart(), t.GetEnd()
        out.append((t, mm(a.x), mm(a.y), mm(c.x), mm(c.y)))
    return out


def violating(board, centers, nets_by_pad):
    bad = []
    for t, x1, y1, x2, y2 in tracks_of(board):
        w = mm(t.GetWidth())
        net = t.GetNetname()
        for num, (px, py) in centers.items():
            if nets_by_pad[num] == net:
                continue
            gap = dist_seg(px, py, x1, y1, x2, y2) - w / 2 - PAD_R
            if gap < CLR - 1e-4:
                bad.append(t)
                break
    return bad


def move_end(board, net, layer, a, b, new_a=None, new_b=None):
    hits = []
    for t, x1, y1, x2, y2 in tracks_of(board):
        if t.GetNetname() != net or t.GetLayer() != layer:
            continue
        if math.hypot(x1 - a[0], y1 - a[1]) < 0.03 and math.hypot(x2 - b[0], y2 - b[1]) < 0.03:
            hits.append((t, False))
        elif math.hypot(x1 - b[0], y1 - b[1]) < 0.03 and math.hypot(x2 - a[0], y2 - a[1]) < 0.03:
            hits.append((t, True))
    if not hits:
        raise SystemExit(f"track not found {net} {a} {b}")
    for t, rev in hits:
        s = t.GetStart()
        e = t.GetEnd()
        if new_a and not rev:
            s = V(*new_a)
        if new_b and not rev:
            e = V(*new_b)
        if new_a and rev:
            e = V(*new_a)
        if new_b and rev:
            s = V(*new_b)
        t.SetStart(s)
        t.SetEnd(e)
    print(f"moved {len(hits)} {net} {a}->{b}")


def move_via(board, net, old, new):
    n = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA" or t.GetNetname() != net:
            continue
        p = t.GetPosition()
        if math.hypot(mm(p.x) - old[0], mm(p.y) - old[1]) < 0.03:
            t.SetPosition(V(*new))
            n += 1
    if n != 1:
        raise SystemExit(f"via {net} {old} count {n}")
    print("moved via", net, old, new)


def add_poly(board, net_name, width, layer, pts):
    net = board.FindNet(net_name)
    added = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(x1, y1))
        t.SetEnd(V(x2, y2))
        t.SetWidth(nm(width))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)
        added.append(t)
    return added


def copper_conflict(board, net, width, layer, pts, pads):
    """Return a description if this polyline breaks 0.15 mm clearance."""
    problems = []
    half = width / 2
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for num, px, py, pnet in pads:
            if pnet == net:
                continue
            gap = dist_seg(px, py, x1, y1, x2, y2) - half - PAD_R
            if gap < CLR - 1e-3:
                problems.append(f"pad {num} gap {gap:.3f} on ({x1:.3f},{y1:.3f})-({x2:.3f},{y2:.3f})")
            # Hole of a different net.
            hgap = dist_seg(px, py, x1, y1, x2, y2) - half - DRILL_R
            if hgap < CLR - 1e-3 and gap >= CLR:
                problems.append(f"hole {num} gap {hgap:.3f}")
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                if t.GetNetname() == net:
                    continue
                p = t.GetPosition()
                vr = mm(t.GetWidth(layer if layer in (pcbnew.F_Cu, pcbnew.B_Cu) else pcbnew.F_Cu)) / 2
                d = dist_seg(mm(p.x), mm(p.y), x1, y1, x2, y2)
                if d - half - vr < CLR - 1e-3:
                    problems.append(
                        f"via {t.GetNetname()} {mm(p.x):.3f},{mm(p.y):.3f} gap {d - half - vr:.3f}"
                    )
                continue
            if t.GetLayer() != layer or t.GetNetname() == net:
                continue
            a, c = t.GetStart(), t.GetEnd()
            tw = mm(t.GetWidth())
            d = seg_gap(x1, y1, x2, y2, mm(a.x), mm(a.y), mm(c.x), mm(c.y))
            if d - half - tw / 2 < CLR - 1e-3:
                problems.append(
                    f"track {t.GetNetname()} ({mm(a.x):.2f},{mm(a.y):.2f})-({mm(c.x):.2f},{mm(c.y):.2f}) gap {d - half - tw / 2:.3f}"
                )
        # Board edge. Outline is x 0..80.99, y 0.395..57.29.
        for x, y in ((x1, y1), (x2, y2)):
            if x - half < 0.30 or 80.99 - (x + half) < 0.30 or y - half < 0.395 + 0.30:
                problems.append(f"edge ({x:.2f},{y:.2f})")
    return problems


def outside_parts(x1, y1, x2, y2, box):
    """Pieces of the segment that sit outside the box. Empty if it is fully inside."""
    x0, y0, x1b, y1b = box
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - x0), (dx, x1b - x1), (-dy, y1 - y0), (dy, y1b - y1)):
        if abs(p) < 1e-12:
            if q < 0:
                return [((x1, y1), (x2, y2))]
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return [((x1, y1), (x2, y2))]
            t0 = max(t0, r)
        else:
            if r < t0:
                return [((x1, y1), (x2, y2))]
            t1 = min(t1, r)
    if t0 > t1:
        return [((x1, y1), (x2, y2))]
    parts = []
    if t0 > 1e-4:
        parts.append(((x1, y1), (x1 + t0 * dx, y1 + t0 * dy)))
    if t1 < 1 - 1e-4:
        parts.append(((x1 + t1 * dx, y1 + t1 * dy), (x2, y2)))
    return parts


def rip_box(board, nets, box):
    """Delete B.Cu of these nets inside the box. Keep the copper outside it."""
    doomed = []
    replacements = []
    for t, x1, y1, x2, y2 in tracks_of(board):
        if t.GetLayer() != pcbnew.B_Cu or t.GetNetname() not in nets:
            continue
        parts = outside_parts(x1, y1, x2, y2, box)
        fully_out = len(parts) == 1 and parts[0][0] == (x1, y1) and parts[0][1] == (x2, y2)
        if fully_out:
            continue
        doomed.append(t)
        w = mm(t.GetWidth())
        net = t.GetNetname()
        for a, b in parts:
            replacements.append((net, w, a, b))
    for t in doomed:
        board.Remove(t)
    for net, w, a, b in replacements:
        add_poly(board, net, w, pcbnew.B_Cu, [a, b])
    return doomed


def route_b(board, rt, net, widths):
    """Reconnect a net on B.Cu only, without new vias."""
    for _ in range(16):
        groups = islands(board, net)
        if len(groups) <= 1:
            return True
        groups.sort(key=lambda g: -sum(1 for p in g if p.kind == "rect"))
        src = groups[0]
        done = False
        rest = groups[1:]

        def far(g):
            return min(
                math.hypot(
                    (a.bbox()[0] + a.bbox()[2]) / 2 - (b.bbox()[0] + b.bbox()[2]) / 2,
                    (a.bbox()[1] + a.bbox()[3]) / 2 - (b.bbox()[1] + b.bbox()[3]) / 2,
                )
                for a in g
                for b in src
            )

        for tgt in sorted(rest, key=far):
            for w in widths:
                sm = group_mask(rt, src)
                tm = group_mask(rt, tgt)
                path = None
                for layers, vias_ok in (((rr.B,), False), ((rr.F, rr.B), True)):
                    path = rt.route(
                        net, w, sm, tm, allow_via=vias_ok, layers=layers, via_cost=3.0, max_nodes=800000
                    )
                    if path is not None:
                        break
                if path is None:
                    continue
                polys, vias = rt.to_segments(path)
                rt.commit(net, w, polys, vias)
                length = sum(
                    math.hypot(b[0] - a[0], b[1] - a[1])
                    for _L, pts in polys
                    for a, b in zip(pts, pts[1:])
                )
                print(f"  routed {net} w={w} len={length:.2f} vias={len(vias)}")
                done = True
                break
            if done:
                break
        if not done:
            print("  FAILED", net, "islands", len(groups))
            for i, g in enumerate(groups):
                xs, ys = [], []
                kinds = {}
                for p in g:
                    bb = p.bbox()
                    xs += [bb[0], bb[2]]
                    ys += [bb[1], bb[3]]
                    kinds[p.kind] = kinds.get(p.kind, 0) + 1
                mb = group_mask(rt, g).get(rr.B)
                nb = int(mb.sum()) if mb is not None else -1
                print(
                    f"    isle {i} n={len(g)} {kinds} "
                    f"x {min(xs):.2f}-{max(xs):.2f} y {min(ys):.2f}-{max(ys):.2f} Bcells {nb}"
                )
            return False
    return len(islands(board, net)) <= 1


def jog_tps(board):
    """Bend the TPS_EN vertical left so BAT_PROT can cross on y=8.90."""
    found = None
    for t, x1, y1, x2, y2 in tracks_of(board):
        if t.GetNetname() != "/TPS_EN" or t.GetLayer() != pcbnew.B_Cu:
            continue
        if abs(x1 - 15.05) < 0.08 and abs(x2 - 15.05) < 0.08 and abs(y1 - y2) > 2:
            found = (t, y1, y2)
            break
    if found is None:
        raise SystemExit("TPS_EN vertical not found")
    t, y1, y2 = found
    lo, hi = min(y1, y2), max(y1, y2)
    board.Remove(t)
    KEEP.append(t)
    add_poly(
        board,
        "/TPS_EN",
        0.15,
        pcbnew.B_Cu,
        [
            (15.050, lo),
            (15.050, 7.450),
            (10.050, 7.450),
            (10.050, 9.200),
            (15.050, 9.200),
            (15.050, hi),
        ],
    )
    for seg, x1, y1, x2, y2 in tracks_of(board):
        if seg.GetNetname() != "/BAT_PROT" or seg.GetLayer() != pcbnew.B_Cu:
            continue
        if abs(y1 - 8.902) < 0.05 and abs(y2 - 8.902) < 0.05 and max(x1, x2) > 10.2:
            west = min(x1, x2)
            seg.SetStart(V(west, 8.902))
            seg.SetEnd(V(9.650, 8.902))
            print("shortened BAT_PROT spur to x=9.65")
            break
    drop = []
    for seg, x1, y1, x2, y2 in tracks_of(board):
        if seg.GetNetname() != "/BAT_PROT" or seg.GetLayer() != pcbnew.B_Cu:
            continue
        if abs(x1 - 14.05) < 0.05 and abs(x2 - 14.05) < 0.05 and abs(y1 - y2) > 1:
            drop.append(seg)
    for seg in drop:
        board.Remove(seg)
    KEEP.extend(drop)
    print("jogged TPS_EN, removed", len(drop), "BAT stubs")
    # U2 pads 2 and 3 are both BAT_PROT and overlap, so this via is only a
    # second stitch. Removing it avoids a long detour through the switch.
    gone = []
    for t in list(board.GetTracks()):
        if t.GetNetname() != "/BAT_PROT":
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            if abs(mm(p.x) - 16.443) < 0.05 and abs(mm(p.y) - 8.988) < 0.05:
                gone.append(t)
            continue
        a, c = t.GetStart(), t.GetEnd()
        xs = (mm(a.x), mm(c.x))
        ys = (mm(a.y), mm(c.y))
        if min(abs(xs[0] - 16.443), abs(xs[1] - 16.443)) < 0.05 and min(abs(ys[0] - 8.988), abs(ys[1] - 8.988)) < 0.05:
            gone.append(t)
    for t in gone:
        board.Remove(t)
    KEEP.extend(gone)
    print("removed BAT via", len(gone))
def drop_redundant_bat_via(board):
    """U2 pads 2 and 3 are both BAT_PROT and overlap, so this via is a second stitch."""
    gone = []
    for t in list(board.GetTracks()):
        if t.GetNetname() != "/BAT_PROT":
            continue
        if t.GetClass() == "PCB_VIA":
            pos = t.GetPosition()
            if abs(mm(pos.x) - 16.443) < 0.05 and abs(mm(pos.y) - 8.988) < 0.05:
                gone.append(t)
            continue
        a, c = t.GetStart(), t.GetEnd()
        xs, ys = (mm(a.x), mm(c.x)), (mm(a.y), mm(c.y))
        via = min(abs(xs[0] - 16.443), abs(xs[1] - 16.443)) < 0.05 and min(abs(ys[0] - 8.988), abs(ys[1] - 8.988)) < 0.05
        pad = min(abs(xs[0] - 15.295), abs(xs[1] - 15.295)) < 0.05 and min(abs(ys[0] - 10.557), abs(ys[1] - 10.557)) < 0.05
        if via and pad:
            gone.append(t)
    for t in gone:
        board.Remove(t)
    KEEP.extend(gone)
    print("removed redundant BAT stitch", len(gone))


def finish_links(board, centers, nets):
    """Pull the router stubs onto the vias and pads they stopped short of."""
    drop_redundant_bat_via(board)
    b = pcbnew.B_Cu
    f = pcbnew.F_Cu
    links = [
        ("/BAT_PROT", 0.25, b, [(10.600, 8.902), (14.154, 8.902)]),
        ("/TPS_EN", 0.15, b, [(15.100, 5.750), (14.400, 5.750), (14.400, 7.250), (14.945, 6.895)]),
        ("/TPS_EN", 0.15, b, [(14.945, 6.895), (15.050, 7.100)]),
        ("/VLOG", 0.15, f, [(17.250, 5.600), (17.424, 5.770)]),
        ("/VLOG", 0.15, b, [(19.050, 6.850), (19.050, 7.550), (17.424, 7.550), (17.424, 5.770)]),
        ("/VLOG", 0.15, b, [(14.300, 3.295), (14.750, 4.100)]),
    ]
    pads = [(n, centers[n][0], centers[n][1], nets[n]) for n in centers]
    for net, width, layer, pts in links:
        problems = copper_conflict(board, net, width, layer, pts, pads)
        if problems:
            print("LINK CONFLICT", net, pts[0], "->", pts[-1])
            for p in problems[:8]:
                print("  ", p)
            raise SystemExit("link conflict")
        add_poly(board, net, width, layer, pts)
        print("linked", net, pts[0], "->", pts[-1])


def hits(board, track, x, y):
    net = track.GetNetname()
    layer = track.GetLayer()
    half = mm(track.GetWidth()) / 2
    for o in board.GetTracks():
        if o == track or o.GetNetname() != net:
            continue
        if o.GetClass() == "PCB_VIA":
            p = o.GetPosition()
            if math.hypot(mm(p.x) - x, mm(p.y) - y) <= mm(o.GetWidth(pcbnew.F_Cu)) / 2 + half - 0.002:
                return True
            continue
        if o.GetLayer() != layer:
            continue
        a, c = o.GetStart(), o.GetEnd()
        if dist_seg(x, y, mm(a.x), mm(a.y), mm(c.x), mm(c.y)) <= mm(o.GetWidth()) / 2 + half - 0.002:
            return True
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net or not p.IsOnLayer(layer):
                continue
            pos = p.GetPosition()
            reach = max(mm(p.GetSize().x), mm(p.GetSize().y)) / 2 + half - 0.002
            if math.hypot(mm(pos.x) - x, mm(pos.y) - y) <= reach:
                return True
    return False


def prune_spurs(board):
    removed = 0
    for _ in range(12):
        bad = []
        for t, x1, y1, x2, y2 in tracks_of(board):
            if t.GetNetname() not in ("/BAT_PROT", "/TS", "/VLOG", "/TPS_EN"):
                continue
            a = hits(board, t, x1, y1)
            c = hits(board, t, x2, y2)
            if a != c:
                bad.append(t)
        if not bad:
            break
        for t in bad:
            board.Remove(t)
        KEEP.extend(bad)
        removed += len(bad)
    print("pruned", removed)
    return removed


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    sw, origin = swap_sw(board)
    centers = pad_centers(origin)
    nets = {n: sw.FindPadByNumber(n).GetNetname() for n in LOCAL}
    print("centers", {n: (round(p[0], 3), round(p[1], 3), nets[n]) for n, p in centers.items()})

    # The VLOG via sits on the EN2_CE pad. Slide it, and the track that ends there, left.
    move_via(board, "/VLOG", (14.900, 3.895), (14.650, 3.895))
    move_end(
        board,
        "/VLOG",
        pcbnew.F_Cu,
        (14.900, 3.895),
        (8.300, 3.895),
        new_a=(14.650, 3.895),
    )
    # EN2_CE vertical passes 0.13 mm from the BAT_PROT pad. Shift it to x=14.50.
    move_end(
        board,
        "/EN2_CE",
        pcbnew.F_Cu,
        (14.300, 4.495),
        (14.300, 7.295),
        new_a=(14.400, 4.495),
        new_b=(14.400, 7.295),
    )
    move_end(
        board,
        "/EN2_CE",
        pcbnew.F_Cu,
        (15.500, 4.495),
        (14.300, 4.495),
        new_b=(14.400, 4.495),
    )
    move_end(
        board,
        "/EN2_CE",
        pcbnew.F_Cu,
        (14.300, 7.295),
        (14.100, 7.295),
        new_a=(14.400, 7.295),
    )

    # Rip the B.Cu staircases that weave through the old switch. Tracks that
    # only cross the box are clipped so the copper outside stays put.
    rip = (10.6, 1.45, 21.0, 10.15)
    ripped = rip_box(board, ("/BAT_PROT", "/TS", "/VLOG", "/TPS_EN"), rip)
    print("ripped", len(ripped), "B.Cu segments")
    KEEP.extend(ripped)

    left = violating(board, centers, nets)
    if left:
        raise SystemExit(f"still {len(left)} violating tracks after the rip")

    window = (2.0, 0.90, 24.5, 12.5)
    rt = rr.Router(board, window)
    for net, widths in (
        ("/TPS_EN", (0.15,)),
        ("/TS", (0.15,)),
        ("/VLOG", (0.15,)),
        ("/BAT_PROT", (0.25, 0.15)),
    ):
        rt.refresh()
        print("islands", net, len(islands(board, net)))
        if not route_b(board, rt, net, widths):
            raise SystemExit(f"could not reconnect {net}")

    finish_links(board, centers, nets)
    prune_spurs(board)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(dst)
    print("saved", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
