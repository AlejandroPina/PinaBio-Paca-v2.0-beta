#!/usr/bin/env python3
"""Cut J5 (J_TEMP) down to 4 pins: 3V0_TEMP, GND, SDA_MOD, SCL_MOD.

J5 becomes JST_PH_B4B-PH-K_1x04, with pin 1 where it was, so pins 1-4 keep their
pads and their routing. The old pins 5-8 (OS and three GND), the OS test point
TP1 and the OS copper go away, and so do their silkscreen labels. The TEMP
label is centred on the shorter connector. The rest of the board, the planes,
the antenna keep-out, the logo and the other silkscreen are left as they were.
The zones are refilled at the end.

usage: rework_j5_4pin.py SRC.kicad_pcb DST.kicad_pcb
"""
import sys
from pathlib import Path

import pcbnew

FP_BASE = Path("/usr/share/kicad/footprints/Connector_JST.pretty")
NAME = "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical"
KEEP = []


def nm(v):
    return int(round(v * 1e6))


def V(x, y):
    return pcbnew.VECTOR2I(nm(x), nm(y))


def find(board, ref):
    for f in board.GetFootprints():
        if f.GetReference() == ref:
            return f
    raise SystemExit(f"no {ref}")


def swap_j5(board):
    old = find(board, "J5")
    pos = old.GetPosition()
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    lib = pcbnew.FootprintLoad(str(FP_BASE), NAME)
    if lib is None:
        raise SystemExit(f"{NAME} missing")
    KEEP.append(lib)
    items = list(old.Pads()) + list(old.GraphicalItems())
    for it in items:
        old.Remove(it)
    KEEP.extend(items)
    old.SetPosition(V(0, 0))
    for p in lib.Pads():
        d = p.Duplicate()
        old.Add(d)
        d.SetNet(nets[d.GetNumber()])
    for g in lib.GraphicalItems():
        old.Add(g.Duplicate())
    old.SetFPID(lib.GetFPID())
    old.Models().clear()
    for m in lib.Models():
        old.Add3DModel(m)
    old.SetLibDescription(lib.GetLibDescription())
    old.SetKeywords(lib.GetKeywords())
    old.SetPosition(pos)
    cx = pos.x / 1e6 + 3.0
    old.Reference().SetPosition(V(cx, pos.y / 1e6 - 2.9))
    old.Value().SetPosition(V(cx, pos.y / 1e6 + 4.0))
    return old


def drop_os(board):
    gone = [t for t in board.GetTracks() if t.GetNetname() == "/OS"]
    gone.append(find(board, "TP1"))
    for it in gone:
        board.Remove(it)
    KEEP.extend(gone)
    print("removed", len(gone), "items on OS / TP1")


def silk(board, j5):
    pos = j5.GetPosition()
    x0 = pos.x / 1e6
    lo, hi = x0 - 1.0, x0 + 8.0
    removed = []
    for d in list(board.GetDrawings()):
        if d.GetClass() != "PCB_TEXT" or d.GetLayer() != pcbnew.F_SilkS:
            continue
        p = d.GetPosition()
        px, py = p.x / 1e6, p.y / 1e6
        if not (lo < px < x0 + 16 and 46 < py < 51):
            continue
        txt = d.GetText()
        if txt in ("OS",) or (txt == "GND" and px > x0 + 8):
            board.Remove(d)
            removed.append(d)
        elif txt == "TEMP":
            d.SetPosition(V(x0 + 3.0, py))
    KEEP.extend(removed)
    print("removed silk labels", [r.GetText() for r in removed])


def main(src, dst):
    board = pcbnew.LoadBoard(src)
    j5 = swap_j5(board)
    drop_os(board)
    silk(board, j5)
    for n in ("/OS",):
        net = board.FindNet(n)
        if net is not None:
            board.RemoveNative(net)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
