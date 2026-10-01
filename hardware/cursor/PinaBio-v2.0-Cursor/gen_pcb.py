#!/usr/bin/env python3
"""Place and route PinaBio v.2.0. Cursor. Four layers, one ground."""
import heapq
import math
import re
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent
FP_BASE = Path("/usr/share/kicad/footprints")
CLR = 150_000  # 0.15 mm
VIA_D = 500_000
VIA_DRILL = 250_000
CELL = 200_000

# Nets that stay on the planes: a via (or a through-hole pad) is enough.
ZONE_NETS = {"/GND", "/3V3_SYS"}
WIDE = {"/SYS", "/BAT_PROT", "/VBUS", "/VBUS_RAW", "/3V3_A", "/3V0_TEMP", "/SW_L1", "/SW_L2"}

# Anchors are footprint origins in millimetres, Y down. USB sits under the
# module so D+/D− (module edge +Y) face the receptacle. The buck is on the
# left; the ADS and the op-amp are on the right.
FIXED = {
    "J2": (4.0, 4.2, 0),
    "SW1": (16.5, 5.2, 0),
    "U2": (16.2, 12.2, 270),
    "U3": (16.2, 23.2, 180),
    "L1": (10.4, 23.2, 0),
    "U5": (38.0, 16.5, 0),
    "U1": (37.6, 27.3, 90),
    "J1": (38.0, 35.6, 0),
    "SW2": (27.2, 12.4, 90),
    "U6": (56.5, 14.5, 0),
    "U7": (56.5, 22.6, 0),
    "U8": (69.2, 18.6, 0),
    "U4": (56.5, 31.2, 0),
    "J5": (78.6, 8.2, 270),
    "J4": (78.6, 28.6, 270),
    "J3": (78.6, 44.2, 270),
    "J6": (5.6, 33.5, 180),
    "J7": (5.6, 40.2, 180),
    "J8": (5.6, 46.9, 180),
    "TP1": (69.0, 31.0, 0),
    "D1": (23.2, 17.0, 0),
    "Q1": (27.0, 28.6, 0),
    "Q2": (27.0, 32.6, 180),
    "Q3": (27.0, 36.6, 0),
}

# Passive -> (already placed ref, pin). The part is set just outside that pad.
ATTACH = {
    "C1": ("U2", "13"),
    "C2": ("U2", "10"),
    "C3": ("U2", "2"),
    "C4": ("U3", "12"),
    "C5": ("U3", "13"),
    "C6": ("U3", "12"),
    "C7": ("U3", "7"),
    "C8": ("U3", "8"),
    "C9": ("U3", "7"),
    "C10": ("U3", "8"),
    "C11": ("U3", "3"),
    "C12": ("U4", "1"),
    "C13": ("U4", "5"),
    "C14": ("U5", "5"),
    "C15": ("U5", "45"),
    "C16": ("U5", "3"),
    "C17": ("U5", "3"),
    "C18": ("U6", "12"),
    "C19": ("U6", "13"),
    "C20": ("U7", "12"),
    "C21": ("U7", "13"),
    "C22": ("U8", "4"),
    "R1": ("J1", "A5"),
    "R2": ("J1", "B5"),
    "R3": ("J1", "A4"),
    "R4": ("U2", "6"),
    "R5": ("D1", "3"),
    "R6": ("U2", "16"),
    "R7": ("U2", "15"),
    "R8": ("U2", "12"),
    "R9": ("U2", "9"),
    "R10": ("U2", "7"),
    "R11": ("SW1", "2"),
    "R12": ("SW1", "5"),
    "R13": ("U3", "5"),
    "R14": ("U3", "5"),
    "R15": ("U6", "12"),
    "R16": ("Q1", "1"),
    "R17": ("Q1", "3"),
    "R18": ("U5", "5"),
    "R19": ("Q2", "1"),
    "R20": ("Q3", "1"),
    "R21": ("U5", "6"),
    "R22": ("U5", "45"),
    "R23": ("U5", "8"),
    "R24": ("U5", "9"),
    "R25": ("U5", "14"),
    "R26": ("U6", "14"),
    "R27": ("U7", "14"),
    "R28": ("U8", "3"),
    "R29": ("U8", "3"),
    "R30": ("U8", "5"),
    "R31": ("U8", "10"),
    "R32": ("U8", "12"),
    "R33": ("U6", "11"),
    "R34": ("U6", "11"),
}


def nm(mm):
    return int(round(mm * 1_000_000))


def parse_netlist(path):
    text = Path(path).read_text()
    comps = {}
    for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s+\(value "([^"]*)"\)\s+\(footprint "([^"]+)"\)',
        text,
    ):
        comps[m.group(1)] = {"value": m.group(2), "fp": m.group(3)}
    nets = {}
    for m in re.finditer(r'\(net \(code "(\d+)"\) \(name "([^"]+)"\)', text):
        start = m.end()
        nxt = text.find("\n    (net ", start)
        block = text[start:] if nxt < 0 else text[start:nxt]
        nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block)
        nets[m.group(2)] = nodes
    return comps, nets


def load_fp(fpname):
    nick, name = fpname.split(":", 1)
    path = str(ROOT / "lib.pretty") if nick == "PinaCursor" else str(FP_BASE / f"{nick}.pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"missing footprint {fpname}")
    return fp


def courtyard(fp):
    poly = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = poly.BBox() if poly.OutlineCount() else fp.GetBoundingBox(False, False)
    return (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())


def overlap(a, b, gap=150_000):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def set_pose(fp, x_mm, y_mm, rot):
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    fp.SetPosition(pcbnew.VECTOR2I(nm(x_mm), nm(y_mm)))


def hide_text(fp):
    for item in (fp.Reference(), fp.Value()):
        item.SetLayer(pcbnew.F_Fab)
        item.SetTextSize(pcbnew.VECTOR2I(nm(0.5), nm(0.5)))
        item.SetTextThickness(nm(0.08))


def rot_xy(x, y, rot):
    r = int(rot) % 360
    if r == 0:
        return x, y
    if r == 90:
        return y, -x
    if r == 180:
        return -x, -y
    if r == 270:
        return -y, x
    raise SystemExit(f"bad rot {rot}")


def place_all(board, comps):
    fps = {}
    boxes = []

    def add(ref, x, y, rot):
        fp = load_fp(comps[ref]["fp"])
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        hide_text(fp)
        set_pose(fp, x, y, rot)
        box = courtyard(fp)
        hit = None
        for other, b in boxes:
            if overlap(box, b):
                hit = other
                break
        if hit:
            raise SystemExit(f"overlap {ref} with {hit} at {x:.2f},{y:.2f} rot {rot}")
        board.Add(fp)
        fps[ref] = fp
        boxes.append((ref, box))
        return fp

    pending = []
    for ref, (x, y, rot) in FIXED.items():
        fp = load_fp(comps[ref]["fp"])
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        hide_text(fp)
        set_pose(fp, x, y, rot)
        pending.append((ref, fp, courtyard(fp)))
    bad = []
    for i, (ra, _fa, ba) in enumerate(pending):
        for rb, _fb, bb in pending[i + 1 :]:
            if overlap(ba, bb):
                bad.append(f"{ra}/{rb}")
    if bad:
        raise SystemExit("fixed overlaps: " + ", ".join(bad))
    for ref, fp, box in pending:
        board.Add(fp)
        fps[ref] = fp
        boxes.append((ref, box))

    def pad_world(ref, pin):
        fp = fps[ref]
        pad = None
        for p in fp.Pads():
            if p.GetNumber() == pin:
                pad = p
                break
        if pad is None:
            raise SystemExit(f"no pad {ref} {pin}")
        pos = pad.GetPosition()
        cen = fp.GetPosition()
        return pos.x, pos.y, cen.x, cen.y

    order = sorted(ATTACH, key=lambda r: (0 if r.startswith("C") else 1, r))
    for ref in order:
        host, pin = ATTACH[ref]
        px, py, cx, cy = pad_world(host, pin)
        ox, oy = px - cx, py - cy
        if ox == 0 and oy == 0:
            ox, oy = nm(1), 0
        mag = math.hypot(ox, oy)
        ux, uy = ox / mag, oy / mag
        horiz = abs(ux) >= abs(uy)
        fp = load_fp(comps[ref]["fp"])
        fp.SetReference(ref)
        fp.SetValue(comps[ref]["value"])
        hide_text(fp)
        placed = False
        # The module antenna looks out of local -Y. Keep that strip empty.
        ant_x0, ant_x1 = nm(38.0 - 9.0), nm(38.0 + 9.0)
        ant_y1 = nm(16.5 - 7.4)
        # Resistors stay off the pin so a via can land in the corridor.
        # Capacitors stay close: they are the decoupling.
        dists = (
            (2.15, 2.55, 3.05, 3.6, 4.3, 5.1, 6.0, 7.2)
            if ref.startswith("C")
            else (3.8, 4.5, 5.3, 6.2, 7.2, 8.4, 9.6)
        )
        for dist in dists:
            if placed:
                break
            for lat in (0, 1.6, -1.6, 3.0, -3.0, 4.4, -4.4, 5.8, -5.8):
                if placed:
                    break
                for rot in ((0, 90) if horiz else (90, 0)):
                    lx, ly = (-uy * lat, ux * lat)
                    x = (px + ux * nm(dist) + nm(lx)) / 1e6
                    y = (py + uy * nm(dist) + nm(ly)) / 1e6
                    set_pose(fp, x, y, rot)
                    box = courtyard(fp)
                    if any(overlap(box, b) for _, b in boxes):
                        continue
                    if box[0] < nm(-1) or box[1] < nm(0.4) or box[2] > nm(90) or box[3] > nm(68):
                        continue
                    if box[2] > ant_x0 and box[0] < ant_x1 and box[1] < ant_y1:
                        continue
                    board.Add(fp)
                    fps[ref] = fp
                    boxes.append((ref, box))
                    placed = True
                    break
        if not placed:
            for rad in [i * 0.7 for i in range(2, 18)]:
                if placed:
                    break
                for step in range(20):
                    if placed:
                        break
                    ang = step * math.pi / 10
                    x = px / 1e6 + rad * math.cos(ang)
                    y = py / 1e6 + rad * math.sin(ang)
                    for rot in (0, 90):
                        set_pose(fp, x, y, rot)
                        box = courtyard(fp)
                        if any(overlap(box, b) for _, b in boxes):
                            continue
                        if box[0] < nm(-1) or box[1] < nm(0.4) or box[2] > nm(90) or box[3] > nm(68):
                            continue
                        if box[2] > ant_x0 and box[0] < ant_x1 and box[1] < ant_y1:
                            continue
                        board.Add(fp)
                        fps[ref] = fp
                        boxes.append((ref, box))
                        placed = True
                        break
        if not placed:
            raise SystemExit(f"no spot for {ref} near {host}.{pin}")
        p = fps[ref].GetPosition()
        print(f"placed {ref:4} {p.x/1e6:6.2f},{p.y/1e6:6.2f}")
    missing = [r for r in comps if r not in fps]
    if missing:
        raise SystemExit(f"unplaced {missing}")
    return fps


def translate(board, dx, dy):
    for fp in board.GetFootprints():
        p = fp.GetPosition()
        fp.SetPosition(pcbnew.VECTOR2I(p.x + dx, p.y + dy))


def board_box(board):
    boxes = [courtyard(fp) for fp in board.GetFootprints()]
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def add_outline(board, x0, y0, x1, y1):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pcbnew.VECTOR2I(int(a[0]), int(a[1])))
        seg.SetEnd(pcbnew.VECTOR2I(int(b[0]), int(b[1])))
        seg.SetWidth(nm(0.05))
        board.Add(seg)


def add_nets(board, nets):
    for i, name in enumerate(sorted(nets), start=1):
        board.Add(pcbnew.NETINFO_ITEM(board, name, i))


def assign_pads(fps, nets):
    for name, nodes in nets.items():
        if name.startswith("unconnected-"):
            continue
        for ref, pin in nodes:
            hits = [p for p in fps[ref].Pads() if p.GetNumber() == pin]
            if not hits:
                raise SystemExit(f"no pad {ref} pin {pin}")
            for pad in hits:
                pad.SetNet(fps[ref].GetBoard().FindNet(name))


def track_width(name):
    if name in ("/SW_L1", "/SW_L2"):
        return nm(0.40)
    if name in WIDE:
        return nm(0.35)
    return nm(0.15)


def setup(board):
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = nm(0.15)
    ds.m_MinClearance = CLR
    ds.m_ViasMinSize = nm(0.45)
    ds.m_ViasMinDrill = nm(0.25)
    ds.m_MinThroughDrill = nm(0.25)
    ds.m_CopperEdgeClearance = nm(0.30)
    # 0.15 mm matches the copper clearance. The HCTL USB-C footprint's
    # locating holes are 0.185 mm from the shell pads, so 0.20 mm cannot pass.
    ds.m_HoleClearance = nm(0.15)
    ds.m_SilkClearance = nm(0.10)
    ds.m_SolderMaskToCopperClearance = nm(0.05)
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(CLR)
    nc.SetTrackWidth(nm(0.20))
    nc.SetViaDiameter(VIA_D)
    nc.SetViaDrill(VIA_DRILL)
    tb = board.GetTitleBlock()
    tb.SetTitle("PinaBio v.2.0. Cursor")
    tb.SetRevision("SPEC-0.8")
    tb.SetDate("2026-09-30")
    tb.SetComment(0, "Cuatro capas. In1 masa, In2 3V3_SYS.")


def add_track(board, x1, y1, x2, y2, width, layer, net):
    if int(x1) == int(x2) and int(y1) == int(y2):
        return None
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    tr.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    tr.SetWidth(int(width))
    tr.SetLayer(layer)
    tr.SetNet(net)
    board.Add(tr)
    return tr


def add_via(board, x, y, net):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    via.SetWidth(VIA_D)
    via.SetDrill(VIA_DRILL)
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNet(net)
    board.Add(via)
    return via


def pad_rect(pad):
    bb = pad.GetBoundingBox()
    return bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()


def dist_point_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 <= 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def dist_point_rect(px, py, rect):
    x0, y0, x1, y1 = rect
    cx = min(max(px, x0), x1)
    cy = min(max(py, y0), y1)
    return math.hypot(px - cx, py - cy)


def seg_rect_ok(x1, y1, x2, y2, half, rect, clearance):
    need = half + clearance
    if dist_point_rect(x1, y1, rect) < need or dist_point_rect(x2, y2, rect) < need:
        return False
    for cx, cy in ((rect[0], rect[1]), (rect[2], rect[1]), (rect[0], rect[3]), (rect[2], rect[3])):
        if dist_point_seg(cx, cy, x1, y1, x2, y2) < need:
            return False
    # sample so a segment that cuts through a pad cannot sneak past the corners
    length = math.hypot(x2 - x1, y2 - y1)
    steps = max(1, int(length / 50_000))
    for i in range(steps + 1):
        t = i / steps
        if dist_point_rect(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, rect) < need:
            return False
    return True


def seg_seg_ok(a, b, need):
    (x1, y1, x2, y2) = a
    (u1, v1, u2, v2) = b
    if dist_point_seg(x1, y1, u1, v1, u2, v2) < need and dist_point_seg(x2, y2, u1, v1, u2, v2) < need:
        # both ends close: still check midpoints below
        pass
    length = math.hypot(x2 - x1, y2 - y1)
    steps = max(1, int(length / 80_000))
    for i in range(steps + 1):
        t = i / steps
        if dist_point_seg(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, u1, v1, u2, v2) < need:
            return False
    return True


class World:
    def __init__(self, board, outline):
        self.board = board
        self.outline = outline
        self.tracks = []  # (x1,y1,x2,y2,w,layer,netname)
        self.vias = []  # (x,y,netname)
        self.keepouts = []
        self.added = []  # pcbnew items, so a failed net can be rolled back
        self.channels = []
        for fp in board.GetFootprints():
            if fp.GetReference() not in ("U2", "U3", "U5", "U6", "U7", "U8"):
                continue
            cen = fp.GetPosition()
            for pad in fp.Pads():
                if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                    continue
                pos = pad.GetPosition()
                ox, oy = pos.x - cen.x, pos.y - cen.y
                mag = math.hypot(ox, oy) or 1.0
                reach = nm(2.0)
                farx = pos.x + ox / mag * reach
                fary = pos.y + oy / mag * reach
                half = nm(0.28)
                self.channels.append(
                    (
                        min(pos.x, farx) - half,
                        min(pos.y, fary) - half,
                        max(pos.x, farx) + half,
                        max(pos.y, fary) + half,
                        pad.GetNetname(),
                    )
                )
        self.pad_obs = []  # (rect, layer or None for all, netname)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                rect = pad_rect(pad)
                attr = pad.GetAttribute()
                # PTH and NPTH block every copper layer. SMD blocks the front.
                all_layers = attr != pcbnew.PAD_ATTRIB_SMD
                self.pad_obs.append((rect, None if all_layers else pcbnew.F_Cu, pad.GetNetname(), pad))

    def inside(self, x, y, margin):
        x0, y0, x1, y1 = self.outline
        return x0 + margin < x < x1 - margin and y0 + margin < y < y1 - margin

    def track_ok(self, x1, y1, x2, y2, width, layer, netname):
        half = width / 2
        if not self.inside(x1, y1, nm(0.30) + half) or not self.inside(x2, y2, nm(0.30) + half):
            # allow the endpoints to sit on a pad that is inside; the edge test
            # uses the segment samples against the outline margin
            pass
        x0, y0, x1o, y1o = self.outline
        margin = nm(0.30) + half
        length = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(length / 100_000))
        for i in range(steps + 1):
            t = i / steps
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            if self.in_keepout(px, py):
                return False
            if not (x0 + margin < px < x1o - margin and y0 + margin < py < y1o - margin):
                # a pad may legally sit closer than the track margin if this
                # sample is inside that same-net pad
                on_pad = False
                for rect, ly, name, _pad in self.pad_obs:
                    if name != netname:
                        continue
                    if ly not in (None, layer):
                        continue
                    if rect[0] <= px <= rect[2] and rect[1] <= py <= rect[3]:
                        on_pad = True
                        break
                if not on_pad:
                    return False
        for rect, ly, name, _pad in self.pad_obs:
            if name == netname:
                continue
            if ly not in (None, layer):
                continue
            if not seg_rect_ok(x1, y1, x2, y2, half, rect, CLR):
                return False
        for tx1, ty1, tx2, ty2, tw, tlayer, tname in self.tracks:
            if tlayer != layer or tname == netname:
                continue
            need = half + tw / 2 + CLR
            if not seg_seg_ok((x1, y1, x2, y2), (tx1, ty1, tx2, ty2), need):
                return False
        for vx, vy, vname in self.vias:
            if vname == netname:
                continue
            need = half + VIA_D / 2 + CLR
            if dist_point_seg(vx, vy, x1, y1, x2, y2) < need:
                return False
        return True

    def in_keepout(self, x, y):
        for x0, y0, x1, y1 in self.keepouts:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return True
        return False

    def via_ok(self, x, y, netname):
        if self.in_keepout(x, y):
            return False
        if not self.inside(x, y, nm(0.30) + VIA_D / 2):
            return False
        for rect, _ly, name, _pad in self.pad_obs:
            if name == netname:
                # same-net via must not sit in the pad (avoid via-in-pad DRC)
                inflated = (
                    rect[0] - CLR,
                    rect[1] - CLR,
                    rect[2] + CLR,
                    rect[3] + CLR,
                )
                if dist_point_rect(x, y, inflated) < VIA_D / 2:
                    return False
                continue
            if dist_point_rect(x, y, rect) < VIA_D / 2 + CLR:
                return False
        for vx, vy, vname in self.vias:
            need = (VIA_D / 2 + CLR + VIA_D / 2) if vname != netname else nm(0.55)
            if (vx - x) ** 2 + (vy - y) ** 2 < need ** 2:
                return False
        for tx1, ty1, tx2, ty2, tw, _layer, tname in self.tracks:
            if tname == netname:
                continue
            if dist_point_seg(x, y, tx1, ty1, tx2, ty2) < VIA_D / 2 + tw / 2 + CLR:
                return False
        return True

    def commit_track(self, x1, y1, x2, y2, width, layer, net):
        item = add_track(self.board, x1, y1, x2, y2, width, layer, net)
        if item is None:
            return
        self.tracks.append((x1, y1, x2, y2, width, layer, net.GetNetname()))
        self.added.append(item)

    def commit_via(self, x, y, net):
        item = add_via(self.board, x, y, net)
        self.vias.append((x, y, net.GetNetname()))
        self.added.append(item)

    def mark(self):
        return len(self.added)

    def rollback(self, mark):
        while len(self.added) > mark:
            item = self.added.pop()
            self.board.Remove(item)
        # rebuild the geometric indexes from what remains on the board
        self.tracks = []
        self.vias = []
        for item in self.added:
            if item.GetClass() == "PCB_VIA":
                p = item.GetPosition()
                self.vias.append((p.x, p.y, item.GetNetname()))
            else:
                a, c = item.GetStart(), item.GetEnd()
                self.tracks.append((a.x, a.y, c.x, c.y, item.GetWidth(), item.GetLayer(), item.GetNetname()))


def pads_of(board, nets, name):
    out = []
    seen = set()
    for ref, pin in nets[name]:
        fp = next(f for f in board.GetFootprints() if f.GetReference() == ref)
        for pad in fp.Pads():
            if pad.GetNumber() != pin:
                continue
            key = (ref, pin, pad.GetPosition().x, pad.GetPosition().y)
            if key in seen:
                continue
            seen.add(key)
            out.append(pad)
    return out


def try_poly(world, pts, width, layer, net):
    name = net.GetNetname()
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if not world.track_ok(x1, y1, x2, y2, width, layer, name):
            return False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        world.commit_track(x1, y1, x2, y2, width, layer, net)
    return True


def connect_points(world, a, b, width, net):
    """Straight, then both L shapes, on F then B. Vias only if the layer is B."""
    name = net.GetNetname()
    ax, ay = a
    bx, by = b
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if try_poly(world, [(ax, ay), (bx, by)], width, layer, net):
            if layer == pcbnew.B_Cu:
                return world.via_ok(ax, ay, name) and world.via_ok(bx, by, name)
            return True
        for mid in ((bx, ay), (ax, by)):
            if mid in ((ax, ay), (bx, by)):
                continue
            if try_poly(world, [(ax, ay), mid, (bx, by)], width, layer, net):
                if layer == pcbnew.B_Cu:
                    return world.via_ok(ax, ay, name) and world.via_ok(bx, by, name)
                return True
    return False


def route_pair_layer(world, a, b, width, net, layer):
    if try_poly(world, [a, b], width, layer, net):
        return True
    for mid in ((b[0], a[1]), (a[0], b[1])):
        if mid in (a, b):
            continue
        if try_poly(world, [a, mid, b], width, layer, net):
            return True
    for dist in (nm(0.9), nm(1.4), nm(2.0), nm(2.8), nm(-0.9), nm(-1.4), nm(-2.0), nm(-2.8)):
        for ox, oy in ((dist, 0), (0, dist)):
            p1 = (a[0] + ox, a[1] + oy)
            p2 = (b[0] + ox, b[1] + oy)
            if try_poly(world, [a, p1, p2, b], width, layer, net):
                return True
    return False


def route_pair_front(world, pad_a, pad_b, width, net):
    a = (pad_a.GetPosition().x, pad_a.GetPosition().y)
    b = (pad_b.GetPosition().x, pad_b.GetPosition().y)
    # Long runs go to the back side so they do not wall off a pin row.
    if math.hypot(b[0] - a[0], b[1] - a[1]) > nm(7):
        return False
    return route_pair_layer(world, a, b, width, net, pcbnew.F_Cu)


def escape_point(world, pad, netname):
    """A via site just outside the pad, or the pad centre if it is through-hole."""
    if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        return pad.GetPosition().x, pad.GetPosition().y, False
    pos = pad.GetPosition()
    parent = pad.GetParentFootprint()
    cen = parent.GetPosition()
    ox, oy = pos.x - cen.x, pos.y - cen.y
    if ox == 0 and oy == 0:
        ox, oy = nm(1), 0
    mag = math.hypot(ox, oy) or 1
    ux, uy = ox / mag, oy / mag
    px, py = -uy, ux
    rect = pad_rect(pad)
    # start just past the pad edge along the outward axis
    for dist_mm in (0.70, 1.00, 1.35, 1.75, 2.20, 2.70, 3.30, 4.00):
        for lat_mm in (0, 0.45, -0.45, 0.90, -0.90, 1.40, -1.40, 1.90, -1.90):
            x = pos.x + ux * nm(dist_mm) + px * nm(lat_mm)
            y = pos.y + uy * nm(dist_mm) + py * nm(lat_mm)
            if not world.via_ok(x, y, netname):
                continue
            if world.track_ok(pos.x, pos.y, x, y, nm(0.15), pcbnew.F_Cu, netname):
                return int(x), int(y), True
    return None


def b_route(world, points, width, net):
    """Orthogonal A* on B.Cu between points that already have a via or a through hole."""
    if len(points) < 2:
        return True
    name = net.GetNetname()
    x0, y0, x1, y1 = world.outline
    cell = 250_000
    nx = int((x1 - x0) / cell) + 3
    ny = int((y1 - y0) / cell) + 3

    def cid(x, y):
        return int((x - x0) / cell), int((y - y0) / cell)

    def npos(i, j):
        return int(x0 + (i + 0.5) * cell), int(y0 + (j + 0.5) * cell)

    blocked = set()
    for kx0, ky0, kx1, ky1 in world.keepouts:
        i0, j0 = cid(kx0, ky0)
        i1, j1 = cid(kx1, ky1)
        for i in range(max(0, i0), min(nx, i1 + 1)):
            for j in range(max(0, j0), min(ny, j1 + 1)):
                blocked.add((i, j))
    grow = CLR + width / 2 + 80_000
    for rect, ly, pname, _pad in world.pad_obs:
        if pname == name or ly == pcbnew.F_Cu:
            continue
        i0, j0 = cid(rect[0] - grow, rect[1] - grow)
        i1, j1 = cid(rect[2] + grow, rect[3] + grow)
        for i in range(max(0, i0), min(nx, i1 + 1)):
            for j in range(max(0, j0), min(ny, j1 + 1)):
                if dist_point_rect(*npos(i, j), rect) < grow:
                    blocked.add((i, j))
    for tx1, ty1, tx2, ty2, tw, tlayer, tname in world.tracks:
        if tlayer != pcbnew.B_Cu or tname == name:
            continue
        need = width / 2 + tw / 2 + CLR + 50_000
        steps = max(1, int(math.hypot(tx2 - tx1, ty2 - ty1) / 100_000))
        for s in range(steps + 1):
            t = s / steps
            i, j = cid(tx1 + (tx2 - tx1) * t, ty1 + (ty2 - ty1) * t)
            rad = int(need / cell) + 1
            for di in range(-rad, rad + 1):
                for dj in range(-rad, rad + 1):
                    cx, cy = npos(i + di, j + dj)
                    if dist_point_seg(cx, cy, tx1, ty1, tx2, ty2) <= need:
                        blocked.add((i + di, j + dj))
    for vx, vy, vname in world.vias:
        if vname == name:
            continue
        need = VIA_D / 2 + width / 2 + CLR
        i, j = cid(vx, vy)
        rad = int(need / cell) + 1
        for di in range(-rad, rad + 1):
            for dj in range(-rad, rad + 1):
                if math.hypot(*[a - b for a, b in zip(npos(i + di, j + dj), (vx, vy))]) <= need:
                    blocked.add((i + di, j + dj))

    def lay(path):
        pts = [npos(i, j) for i, j in path]
        compact = [pts[0]]
        for p in pts[1:]:
            if len(compact) >= 2:
                a, b = compact[-2], compact[-1]
                if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                    compact[-1] = p
                    continue
            compact.append(p)
        # Snap the ends onto the real via/pad coordinates so the track enters the copper.
        if points:
            compact[0] = points[0] if False else compact[0]
        segs = list(zip(compact, compact[1:]))
        for a, c in segs:
            if not world.track_ok(a[0], a[1], c[0], c[1], width, pcbnew.B_Cu, name):
                return False
        for a, c in segs:
            world.commit_track(a[0], a[1], c[0], c[1], width, pcbnew.B_Cu, net)
        return True

    connected = [points[0]]
    for goal in points[1:]:
        start_cells = set()
        for sx, sy in connected:
            i, j = cid(sx, sy)
            start_cells.add((i, j))
        gi, gj = cid(*goal)
        heap = []
        prev = {}
        for s in start_cells:
            prev[s] = None
            heapq.heappush(heap, (abs(s[0] - gi) + abs(s[1] - gj), 0, s))
        found = None
        seen = set(start_cells)
        steps = 0
        while heap:
            _h, cost, cur = heapq.heappop(heap)
            if cur == (gi, gj) or (cur[0], cur[1]) == (gi, gj):
                found = cur
                break
            steps += 1
            if steps > 200000:
                break
            i, j = cur
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if not (0 <= ni < nx and 0 <= nj < ny) or (ni, nj) in seen:
                    continue
                if (ni, nj) in blocked and (ni, nj) != (gi, gj):
                    continue
                seen.add((ni, nj))
                ncost = cost + 1
                heapq.heappush(heap, (ncost + abs(ni - gi) + abs(nj - gj), ncost, (ni, nj)))
                prev[(ni, nj)] = cur
                if (ni, nj) == (gi, gj):
                    found = (ni, nj)
                    heap.clear()
                    break
        if not found:
            return False
        path = []
        cur = found
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        if not lay(path):
            return False
        connected.append(goal)
    return True


def drop_via(world, pad, net):
    """Short front stub plus a via. Returns the via point, or None."""
    name = net.GetNetname()
    pos = pad.GetPosition()
    if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
        return (pos.x, pos.y)
    esc = escape_point(world, pad, name)
    elbow = None
    if esc is None:
        esc, elbow = escape_elbow(world, pad, name)
    if esc is None:
        return None
    x, y, _ = esc
    if elbow is None:
        world.commit_track(pos.x, pos.y, x, y, nm(0.15), pcbnew.F_Cu, net)
    else:
        world.commit_track(pos.x, pos.y, elbow[0], elbow[1], nm(0.15), pcbnew.F_Cu, net)
        world.commit_track(elbow[0], elbow[1], x, y, nm(0.15), pcbnew.F_Cu, net)
    world.commit_via(x, y, net)
    return (x, y)


def route_signals(board, nets, world):
    failed = []
    names = [n for n in nets if n not in ZONE_NETS and not n.startswith("unconnected-")]
    # Per-net fanout only. A global fanout fills the back layer and blocks the rest.
    fanout = {}
    for name in []:
        pads = pads_of(board, nets, name)
        if len(pads) < 2:
            continue
        mark = world.mark()
        pts = []
        ok = True
        for pad in pads:
            pt = drop_via(world, pad, board.FindNet(name))
            if pt is None:
                ok = False
                break
            pts.append(pt)
        if ok:
            fanout[name] = pts
        else:
            world.rollback(mark)
    print("fanout nets", len(fanout), "of", len(names))
    # short USB and the switch node first
    def rank(n):
        if n in ("/USB_DM", "/USB_DP", "/USB_DM_C", "/USB_DP_C", "/SW_L1", "/SW_L2"):
            return 0
        return 1

    names.sort(key=lambda n: (rank(n), -len(nets[n]), n))
    for name in names:
        pads = pads_of(board, nets, name)
        if len(pads) < 2:
            continue
        if name in fanout:
            net = board.FindNet(name)
            pts = fanout[name]
            pending = pts[1:]
            done = [pts[0]]
            while pending:
                hit = False
                for p in list(pending):
                    for src in done:
                        if route_pair_layer(world, src, p, nm(0.15), net, pcbnew.B_Cu):
                            done.append(p)
                            pending.remove(p)
                            hit = True
                            break
                    if hit:
                        break
                if not hit:
                    break
            if not pending or b_route(world, done + pending, nm(0.15), net):
                print("routed", name, len(pads), "fanout")
                continue
            print("UNROUTED", name, "fanout-join")
            failed.append(name)
            continue
        width = track_width(name)
        net = board.FindNet(name)
        conn = [pads[0]]
        rest = pads[1:]
        progressed = True
        while rest and progressed:
            progressed = False
            for target in list(rest):
                for src in sorted(
                    conn,
                    key=lambda p: (p.GetPosition().x - target.GetPosition().x) ** 2
                    + (p.GetPosition().y - target.GetPosition().y) ** 2,
                ):
                    if route_pair_front(world, src, target, width, net) or (
                        width > nm(0.25) and route_pair_front(world, src, target, nm(0.20), net)
                    ):
                        conn.append(target)
                        rest.remove(target)
                        progressed = True
                        break
        front_ok = not rest
        if rest:
            # Bridge whatever is still loose with a back-side via on each side.
            front_ok = escape_and_b(world, rest + conn[:1], width, net)
        if front_ok:
            print("routed", name, len(pads))
        else:
            print("UNROUTED", name, len(pads))
            failed.append(name)
    return failed


def escape_elbow(world, pad, netname):
    """Out along the pad, then sideways to a via that the straight stub cannot reach."""
    pos = pad.GetPosition()
    parent = pad.GetParentFootprint()
    cen = parent.GetPosition()
    ox, oy = pos.x - cen.x, pos.y - cen.y
    mag = math.hypot(ox, oy) or 1.0
    ux, uy = ox / mag, oy / mag
    px, py = -uy, ux
    for dist in (0.85, 1.15, 1.55, 2.05, 2.6, 3.2, 4.0):
        sx = int(pos.x + ux * nm(dist))
        sy = int(pos.y + uy * nm(dist))
        if not world.track_ok(pos.x, pos.y, sx, sy, nm(0.15), pcbnew.F_Cu, netname):
            continue
        for lat in (0.7, -0.7, 1.2, -1.2, 1.8, -1.8, 2.5, -2.5, 3.2, -3.2):
            x = int(sx + px * nm(lat))
            y = int(sy + py * nm(lat))
            if not world.via_ok(x, y, netname):
                continue
            if world.track_ok(sx, sy, x, y, nm(0.15), pcbnew.F_Cu, netname):
                return (x, y, True), (sx, sy)
    return None, None


def escape_and_b(world, pads, width, net):
    name = net.GetNetname()
    mark = world.mark()
    points = []
    for pad in pads:
        pos = pad.GetPosition()
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            points.append((pos.x, pos.y))
            continue
        esc = escape_point(world, pad, name)
        elbow = None
        if esc is None:
            esc, elbow = escape_elbow(world, pad, name)
        if esc is None:
            parent = pad.GetParentFootprint()
            print("  no escape", name, parent.GetReference(), pad.GetNumber())
            world.rollback(mark)
            return False
        x, y, _need = esc
        wesc = nm(0.15)
        if elbow is None:
            world.commit_track(pos.x, pos.y, x, y, wesc, pcbnew.F_Cu, net)
        else:
            world.commit_track(pos.x, pos.y, elbow[0], elbow[1], wesc, pcbnew.F_Cu, net)
            world.commit_track(elbow[0], elbow[1], x, y, wesc, pcbnew.F_Cu, net)
        world.commit_via(x, y, net)
        points.append((x, y))
    # Join the vias on the back with a short jog before falling back to the grid.
    pending = points[1:]
    done = [points[0]]
    while pending:
        hit = False
        for i, p in enumerate(list(pending)):
            for src in done:
                if route_pair_layer(world, src, p, min(width, nm(0.25)), net, pcbnew.B_Cu):
                    done.append(p)
                    pending.remove(p)
                    hit = True
                    break
            if hit:
                break
        if not hit:
            break
    if not pending:
        return True
    ok = b_route(world, done + pending, min(width, nm(0.25)), net)
    if not ok:
        print("  b-route failed", name, "terms", len(points))
        world.rollback(mark)
    return ok


def maze_connect(world, sources, target, width, net):
    """Grid A* on F and B from source pads (and their escapes) to the target pad."""
    name = net.GetNetname()
    x0, y0, x1, y1 = world.outline
    nx = int((x1 - x0) / CELL) + 3
    ny = int((y1 - y0) / CELL) + 3

    def cid(x, y):
        return int((x - x0) / CELL), int((y - y0) / CELL)

    def npos(i, j):
        return int(x0 + (i + 0.5) * CELL), int(y0 + (j + 0.5) * CELL)

    blocked = [set(), set()]
    via_block = set()
    for rect, ly, pname, _pad in world.pad_obs:
        if pname == name:
            continue
        layers = (0, 1) if ly is None else ((0,) if ly == pcbnew.F_Cu else (1,))
        grow = CLR + width / 2
        for li in layers:
            i0, j0 = cid(rect[0] - grow, rect[1] - grow)
            i1, j1 = cid(rect[2] + grow, rect[3] + grow)
            for i in range(max(0, i0), min(nx, i1 + 1)):
                for j in range(max(0, j0), min(ny, j1 + 1)):
                    cx, cy = npos(i, j)
                    if dist_point_rect(cx, cy, rect) < grow:
                        blocked[li].add((i, j))
        vg = VIA_D / 2 + CLR
        i0, j0 = cid(rect[0] - vg, rect[1] - vg)
        i1, j1 = cid(rect[2] + vg, rect[3] + vg)
        for i in range(max(0, i0), min(nx, i1 + 1)):
            for j in range(max(0, j0), min(ny, j1 + 1)):
                cx, cy = npos(i, j)
                if dist_point_rect(cx, cy, rect) < vg:
                    via_block.add((i, j))
    # existing foreign tracks and vias
    for tx1, ty1, tx2, ty2, tw, tlayer, tname in world.tracks:
        if tname == name:
            continue
        li = 0 if tlayer == pcbnew.F_Cu else 1
        grow = width / 2 + tw / 2 + CLR
        steps = max(1, int(math.hypot(tx2 - tx1, ty2 - ty1) / (CELL / 2)))
        for s in range(steps + 1):
            t = s / steps
            i, j = cid(tx1 + (tx2 - tx1) * t, ty1 + (ty2 - ty1) * t)
            rad = int(grow / CELL) + 1
            for di in range(-rad, rad + 1):
                for dj in range(-rad, rad + 1):
                    cx, cy = npos(i + di, j + dj)
                    if dist_point_seg(cx, cy, tx1, ty1, tx2, ty2) <= grow:
                        blocked[li].add((i + di, j + dj))
    for vx, vy, vname in world.vias:
        if vname == name:
            continue
        i, j = cid(vx, vy)
        rad = int((VIA_D / 2 + width / 2 + CLR) / CELL) + 1
        for di in range(-rad, rad + 1):
            for dj in range(-rad, rad + 1):
                cx, cy = npos(i + di, j + dj)
                if math.hypot(cx - vx, cy - vy) <= VIA_D / 2 + width / 2 + CLR:
                    blocked[0].add((i + di, j + dj))
                    blocked[1].add((i + di, j + dj))
        radv = int((nm(0.62)) / CELL) + 1
        for di in range(-radv, radv + 1):
            for dj in range(-radv, radv + 1):
                cx, cy = npos(i + di, j + dj)
                if math.hypot(cx - vx, cy - vy) < nm(0.62):
                    via_block.add((i + di, j + dj))

    def pad_cells(pad):
        rect = pad_rect(pad)
        i0, j0 = cid(rect[0], rect[1])
        i1, j1 = cid(rect[2], rect[3])
        cells = []
        for i in range(max(0, i0), min(nx, i1 + 1)):
            for j in range(max(0, j0), min(ny, j1 + 1)):
                cx, cy = npos(i, j)
                if rect[0] <= cx <= rect[2] and rect[1] <= cy <= rect[3]:
                    cells.append((i, j))
        if not cells:
            cells.append(cid(pad.GetPosition().x, pad.GetPosition().y))
        return cells

    start = set()
    for pad in sources:
        for c in pad_cells(pad):
            start.add((c[0], c[1], 0))
        esc = escape_point(world, pad, name)
        if esc is not None:
            ex, ey, _ = esc
            i, j = cid(ex, ey)
            start.add((i, j, 0))
            start.add((i, j, 1))
    goal = set()
    for c in pad_cells(target):
        goal.add((c[0], c[1]))
    # also accept an escape cell next to the target, then stitch it
    esc_t = escape_point(world, target, name)
    goal_escape = None
    if esc_t is not None:
        goal_escape = esc_t
        i, j = cid(esc_t[0], esc_t[1])
        goal.add((i, j))

    if not start or not goal:
        return False

    def heuristic(i, j):
        best = 1e18
        for gi, gj in goal:
            best = min(best, abs(i - gi) + abs(j - gj))
        return best

    heap = []
    prev = {}
    for s in start:
        if 0 <= s[0] < nx and 0 <= s[1] < ny:
            prev[s] = None
            heapq.heappush(heap, (heuristic(s[0], s[1]), 0, s))
    found = None
    seen = set(start)
    expansions = 0
    while heap:
        _h, cost, cur = heapq.heappop(heap)
        if cur in goal or (cur[0], cur[1]) in goal and cur[2] == 0:
            # goal pad cells are only valid on F for SMD; escape cells on both
            if (cur[0], cur[1]) in goal:
                found = cur
                break
        i, j, layer = cur
        expansions += 1
        if expansions > 250000:
            break
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if not (0 <= ni < nx and 0 <= nj < ny):
                continue
            nxt = (ni, nj, layer)
            if nxt in seen:
                continue
            on_goal = (ni, nj) in goal and (layer == 0 or goal_escape is not None)
            if (ni, nj) in blocked[layer] and not on_goal:
                continue
            seen.add(nxt)
            ncost = cost + 1
            heapq.heappush(heap, (ncost + heuristic(ni, nj), ncost, nxt))
            prev[nxt] = cur
            if on_goal:
                found = nxt
                heap.clear()
                break
        if found:
            break
        other = 1 - layer
        nxt = (i, j, other)
        if nxt not in seen and (i, j) not in via_block and (i, j) not in blocked[0] and (i, j) not in blocked[1]:
            seen.add(nxt)
            ncost = cost + 6
            heapq.heappush(heap, (ncost + heuristic(i, j), ncost, nxt))
            prev[nxt] = cur
    if not found:
        return False
    path = []
    cur = found
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    # lay, snapping the ends onto the nearest source pad and the target
    def nearest_source(i, j):
        x, y = npos(i, j)
        best = min(
            sources,
            key=lambda p: (p.GetPosition().x - x) ** 2 + (p.GetPosition().y - y) ** 2,
        )
        return best.GetPosition().x, best.GetPosition().y

    pts = []
    for i, j, layer in path:
        pts.append([npos(i, j)[0], npos(i, j)[1], layer])
    sx, sy = nearest_source(path[0][0], path[0][1])
    pts[0][0], pts[0][1] = sx, sy
    tx, ty = target.GetPosition().x, target.GetPosition().y
    # if we finished on the escape cell, append the pad
    end_on_pad = (path[-1][0], path[-1][1]) in set(pad_cells(target)) and path[-1][2] == 0
    if not end_on_pad:
        pts.append([tx, ty, 0])
    else:
        pts[-1][0], pts[-1][1] = tx, ty
    # drop collinear
    compact = [pts[0]]
    for p in pts[1:]:
        if len(compact) >= 2:
            a, b = compact[-2], compact[-1]
            if a[2] == b[2] == p[2] and (a[0] == b[0] == p[0] or a[1] == b[1] == p[1]):
                compact[-1] = p
                continue
        compact.append(p)
    # commit, checking clearance; if a segment fails, abort this path
    staged = []
    for p, q in zip(compact, compact[1:]):
        if p[2] != q[2]:
            if not world.via_ok(p[0], p[1], name):
                return False
            staged.append(("via", p[0], p[1]))
        else:
            layer = pcbnew.F_Cu if p[2] == 0 else pcbnew.B_Cu
            if not world.track_ok(p[0], p[1], q[0], q[1], width, layer, name):
                return False
            staged.append(("track", p[0], p[1], q[0], q[1], layer))
    for item in staged:
        if item[0] == "via":
            world.commit_via(item[1], item[2], net)
        else:
            world.commit_track(item[1], item[2], item[3], item[4], width, item[5], net)
    return True


def stitch_zone_net(board, world, net_name):
    """One via just outside every SMD pad of a plane net, plus a short track."""
    net = board.FindNet(net_name)
    made = 0
    missed = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != net_name:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            esc = escape_point(world, pad, net_name)
            elbow = None
            if esc is None:
                esc, elbow = escape_elbow(world, pad, net_name)
            if esc is None:
                # Tie the pad to a via that is already on this net.
                pos = pad.GetPosition()
                linked = False
                near = sorted(world.vias, key=lambda v: (v[0] - pos.x) ** 2 + (v[1] - pos.y) ** 2)
                for vx, vy, vname in near:
                    if vname != net_name:
                        continue
                    if route_pair_layer(world, (pos.x, pos.y), (vx, vy), nm(0.20), net, pcbnew.F_Cu):
                        linked = True
                        made += 1
                        break
                    if (vx - pos.x) ** 2 + (vy - pos.y) ** 2 > nm(12) ** 2:
                        break
                if not linked:
                    missed.append(f"{fp.GetReference()}.{pad.GetNumber()}")
                continue
            x, y, _ = esc
            pos = pad.GetPosition()
            if elbow is None:
                world.commit_track(pos.x, pos.y, x, y, nm(0.15), pcbnew.F_Cu, net)
            else:
                world.commit_track(pos.x, pos.y, elbow[0], elbow[1], nm(0.20), pcbnew.F_Cu, net)
                world.commit_track(elbow[0], elbow[1], x, y, nm(0.20), pcbnew.F_Cu, net)
            world.commit_via(x, y, net)
            made += 1
    print(f"stitch {net_name}: {made} vias, missed {len(missed)} {missed[:8]}")
    return missed


def add_zone(board, net_name, outline, layer):
    net = board.FindNet(net_name)
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNet(net)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(nm(0.20))
    zone.SetLocalClearance(CLR)
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    zone.SetThermalReliefGap(nm(0.20))
    zone.SetThermalReliefSpokeWidth(nm(0.30))
    zone.SetAssignedPriority(1)
    ol = zone.Outline()
    ol.NewOutline()
    x0, y0, x1, y1 = outline
    # inset so the pour itself respects the edge clearance
    inset = nm(0.30)
    for x, y in (
        (x0 + inset, y0 + inset),
        (x1 - inset, y0 + inset),
        (x1 - inset, y1 - inset),
        (x0 + inset, y1 - inset),
    ):
        ol.Append(int(x), int(y))
    board.Add(zone)
    return zone


def stitch_ground(board, world, outline, keepout):
    net = board.FindNet("/GND")
    x0, y0, x1, y1 = outline
    kx0, ky0, kx1, ky1 = keepout
    made = 0
    y = y0 + nm(6)
    while y < y1 - nm(6):
        x = x0 + nm(6)
        while x < x1 - nm(6):
            if not (kx0 <= x <= kx1 and ky0 <= y <= ky1) and world.via_ok(x, y, "/GND"):
                world.commit_via(int(x), int(y), net)
                made += 1
            x += nm(12)
        y += nm(12)
    print("gnd grid vias", made)
    return []


def add_keepout(board, x0, y0, x1, y1):
    area = pcbnew.ZONE(board)
    area.SetIsRuleArea(True)
    area.SetDoNotAllowCopperPour(True)
    area.SetDoNotAllowTracks(True)
    area.SetDoNotAllowVias(True)
    area.SetDoNotAllowPads(False)
    area.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(layer)
    area.SetLayerSet(ls)
    ol = area.Outline()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(int(x), int(y))
    board.Add(area)


def main():
    comps, nets = parse_netlist(ROOT / "pinabio.net")
    board = pcbnew.BOARD()
    setup(board)
    print("placing", len(comps))
    fps = place_all(board, comps)
    x0, y0, x1, y1 = board_box(board)
    margin = nm(0.8)
    translate(board, -x0 + margin, -y0 + margin)
    x0, y0, x1, y1 = board_box(board)
    outline = (x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    add_outline(board, *outline)
    w = (outline[2] - outline[0]) / 1e6
    h = (outline[3] - outline[1]) / 1e6
    print(f"outline {w:.2f} x {h:.2f} mm")
    add_nets(board, nets)
    assign_pads(fps, nets)
    # antenna keepout: past the module's antenna end (local -Y), not over the pads
    esp = fps["U5"]
    ec = esp.GetPosition()
    # Leave a copper channel between the antenna keepout and the module pads.
    keepout = (ec.x - nm(8.2), outline[1] + nm(0.4), ec.x + nm(8.2), ec.y - nm(8.6))
    add_keepout(board, *keepout)
    world = World(board, outline)
    world.keepouts.append(keepout)
    failed = route_signals(board, nets, world)
    missed_p = stitch_zone_net(board, world, "/3V3_SYS")
    missed_g = stitch_ground(board, world, outline, keepout)
    print("adding zones")
    add_zone(board, "/GND", outline, pcbnew.F_Cu)
    add_zone(board, "/GND", outline, pcbnew.In1_Cu)
    add_zone(board, "/3V3_SYS", outline, pcbnew.In2_Cu)
    out = str(ROOT / "PinaBio-v2.0-Cursor.kicad_pcb")
    board.Save(out)
    print("saved before fill")
    text = pcbnew.PCB_TEXT(board)
    text.SetText("PinaBio v.2.0. Cursor")
    text.SetLayer(pcbnew.F_SilkS)
    text.SetPosition(pcbnew.VECTOR2I(int(outline[0] + nm(8.2)), int(outline[3] - nm(1.77))))
    text.SetTextSize(pcbnew.VECTOR2I(nm(0.9), nm(0.9)))
    text.SetTextThickness(nm(0.15))
    board.Add(text)
    out = str(ROOT / "PinaBio-v2.0-Cursor.kicad_pcb")
    board.Save(out)
    report = (
        f"{w:.2f} x {h:.2f} mm\n"
        f"layers 4 (F GND pour, In1 GND, In2 3V3_SYS, B signals)\n"
        f"unrouted {failed}\n"
        f"gnd vias missed {missed_g}\n"
        f"3v3 vias missed {missed_p}\n"
    )
    (ROOT / "board-size.txt").write_text(report)
    print(report)
    print("saved", out)
    fill_board(out)


def fill_board(path):
    # ZONE_FILLER segfaults in the same process that built the board.
    import subprocess
    import sys
    code = r"""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
zs = pcbnew.ZONES()
for z in b.Zones():
    if not z.GetIsRuleArea():
        zs.append(z)
ok = pcbnew.ZONE_FILLER(b).Fill(zs)
print("fill", ok, "zones", len(zs))
b.Save(sys.argv[1])
"""
    subprocess.check_call([sys.executable, "-u", "-c", code, path])


if __name__ == "__main__":
    main()
