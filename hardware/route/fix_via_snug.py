# -*- coding: utf-8 -*-
"""Via-in-Pad SNUG-Loeser (PCBWay-Review W603081ASX14).

Wie fix_via_in_pad.py, aber minimaler Austritt: die Via wird nur so weit
aus IHREM Pad geschoben, dass das Via-Body/Bohrloch das Pad-Polygon
verlaesst (Eigen-Netz -> keine Clearance zum eigenen Pad noetig, nur die
Kupfer-Geometrie muss raus). Reconnect per kurzem Stub auf der PAD-Lage.
Alle Fremdnetz-Kollisionschecks bleiben rigoros. Endkontrolle per echter
DRC im Aufrufer.
"""
import math
import pcbnew

MM = 1_000_000
CLR = int(0.12 * MM)
VIA_R = int(0.25 * MM)          # Via-Body Halbmesser (0.5 mm OD)
HOLE_R = int(0.15 * MM)         # Via-Bohrung Halbmesser (0.3 mm)
STUB_W = int(0.2 * MM)
SAMP = int(0.1 * MM)
# Wie weit das Bohrloch/Body ueber die Pad-Kante hinaus muss (mm):
TARGETS = [0.30, 0.26, 0.22, 0.18]     # >=0.15 -> Bohrung frei vom Pad

board = pcbnew.LoadBoard(r"project/aurabip_routed.kicad_pcb")
GND = board.GetNetsByName()["GND"].GetNetCode()
fps = list(board.GetFootprints())
edge = board.GetBoardEdgesBoundingBox()

PAD_OBS = []
for f in fps:
    for p in f.Pads():
        bb = p.GetBoundingBox()
        PAD_OBS.append((p.GetNetCode(), bb.GetCenter().x, bb.GetCenter().y,
                        bb.GetWidth() // 2, bb.GetHeight() // 2))
TRK_OBS = []
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA):
        TRK_OBS.append((t.GetNetCode(), t.GetStart().x, t.GetStart().y,
                        t.GetEnd().x, t.GetEnd().y, t.GetWidth() // 2, t.GetLayer()))
VIA_OBJ = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
VIA_OBS = [[v.GetNetCode(), v.GetPosition().x, v.GetPosition().y] for v in VIA_OBJ]
HOLE_OBS = []
for f in fps:
    for p in f.Pads():
        ds = p.GetDrillSize()
        if ds.x > 0:
            c = p.GetPosition()
            HOLE_OBS.append((c.x, c.y, max(ds.x, ds.y) // 2))
EDGE_SEG = []
for d in board.GetDrawings():
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    try:
        s, e = d.GetStart(), d.GetEnd()
        EDGE_SEG.append((s.x, s.y, e.x, e.y))
    except Exception:
        pass


def seg_pt(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg(ax, ay, bx, by, cx, cy, dx, dy):
    n = max(2, int(math.hypot(bx - ax, by - ay) / SAMP))
    best = 1e18
    for i in range(n + 1):
        px = ax + (bx - ax) * i / n
        py = ay + (by - ay) * i / n
        best = min(best, seg_pt(cx, cy, dx, dy, px, py))
        if best < 1:
            return 0
    return best


def via_ok(cx, cy, mynet, skip_via_idx):
    if not (edge.GetLeft() + VIA_R + CLR < cx < edge.GetRight() - VIA_R - CLR and
            edge.GetTop() + VIA_R + CLR < cy < edge.GetBottom() - VIA_R - CLR):
        return False
    kp = VIA_R + CLR
    for nc, ox, oy, hw, hh in PAD_OBS:
        if nc == mynet:
            continue
        if abs(cx - ox) < hw + kp and abs(cy - oy) < hh + kp:
            return False
    for nc, ax, ay, bx, by, hw, ly in TRK_OBS:
        if nc == mynet:
            continue
        if seg_pt(ax, ay, bx, by, cx, cy) < VIA_R + hw + CLR:
            return False
    DRILL_R = int(0.15 * MM)
    for i, (nc, x, y) in enumerate(VIA_OBS):
        if i == skip_via_idx:
            continue
        dvv = math.hypot(cx - x, cy - y)
        if nc != mynet and dvv < 2 * VIA_R + CLR:
            return False
        if dvv < 2 * DRILL_R + int(0.28 * MM):     # hole-to-hole >= 0.28 mm (>0.25 Regel)
            return False
    for hx, hy, hr in HOLE_OBS:
        if math.hypot(cx - hx, cy - hy) < DRILL_R + hr + int(0.24 * MM):
            return False
    for ex1, ey1, ex2, ey2 in EDGE_SEG:
        if seg_pt(ex1, ey1, ex2, ey2, cx, cy) < VIA_R + int(0.28 * MM):
            return False
    return True


def stub_ok(ax, ay, bx, by, mynet, layer):
    for nc, ox, oy, hw, hh in PAD_OBS:
        if nc == mynet:
            continue
        if seg_pt(ax, ay, bx, by, ox, oy) < max(hw, hh) + STUB_W // 2 + CLR:
            return False
    for nc, sx, sy, ex, ey, hw, ly in TRK_OBS:
        if nc == mynet or ly != layer:
            continue
        if seg_seg(ax, ay, bx, by, sx, sy, ex, ey) < STUB_W // 2 + hw + CLR:
            return False
    return True


def dragged_seg_ok(P, far, layer, mynet):
    for nc, sx, sy, ex, ey, hw, ly in TRK_OBS:
        if nc == mynet or ly != layer:
            continue
        if seg_seg(P[0], P[1], far[0], far[1], sx, sy, ex, ey) < STUB_W // 2 + hw + CLR:
            return False
    for nc, ox, oy, hw, hh in PAD_OBS:
        if nc == mynet:
            continue
        if seg_pt(P[0], P[1], far[0], far[1], ox, oy) < max(hw, hh) + CLR:
            return False
    for e1, e2, e3, e4 in EDGE_SEG:
        if seg_seg(P[0], P[1], far[0], far[1], e1, e2, e3, e4) < STUB_W // 2 + int(0.25 * MM):
            return False
    return True


# --- Zielvias sammeln ---
targets = []
for idx, v in enumerate(VIA_OBJ):
    vp = v.GetPosition()
    for fp in fps:
        hit = None
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if fp.GetReference() == "U1" and pad.GetNumber() == "61":
                continue
            if pad.HitTest(vp):
                hit = pad
                break
        if hit:
            targets.append((idx, v, fp, hit))
            break

print("in-pad-Vias (ohne EP):", len(targets))

TRK_OBJ = [t for t in board.GetTracks()
           if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA)]
EPS = 3000

DIRS = [(math.cos(a), math.sin(a)) for a in [i * math.pi / 24 for i in range(48)]]


def pad_clear(pad, cx, cy):
    """min. Abstand Punkt->Pad-Polygon (>0 wenn ausserhalb). Approx via HitTest
    + Kanten der Bounding-Shape; wir nutzen HitTest fuer 'drin' und die
    Rechteck-Kante fuer den Abstand (Pads hier sind Rechtecke/Rundrechtecke)."""
    if pad.HitTest(pcbnew.VECTOR2I(int(cx), int(cy))):
        return -1
    bb = pad.GetBoundingBox()
    l, t, r, b = bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()
    dx = max(l - cx, 0, cx - r)
    dy = max(t - cy, 0, cy - b)
    return math.hypot(dx, dy)


relocated = failed = 0
fail_list = []
stubs = []
for idx, v, fp, pad in targets:
    mynet = pad.GetNetCode()
    PL = pad.GetLayer()          # Pad-Lage fuer Stub
    O = v.GetPosition()
    Ox, Oy = O.x, O.y
    pc = pad.GetCenter()
    # angebundene Track-Enden an der Via
    conn = []
    for t in TRK_OBJ:
        if t.GetNetCode() != mynet:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if abs(s.x - Ox) < EPS and abs(s.y - Oy) < EPS:
            conn.append((t, e.x, e.y, t.GetLayer(), "S"))
        elif abs(e.x - Ox) < EPS and abs(e.y - Oy) < EPS:
            conn.append((t, s.x, s.y, t.GetLayer(), "E"))
    placed = False
    for target in TARGETS:
        if placed:
            break
        # Kandidaten: von der Via-Position aus in alle Richtungen marschieren,
        # bis (a) ausserhalb Pad mit >= target Abstand.
        cands = []
        for dx, dy in DIRS:
            for step in range(2, 40):     # 0.05 mm Schritte bis 2.0 mm
                r = step * int(0.05 * MM)
                Px = int(Ox + dx * r)
                Py = int(Oy + dy * r)
                clr = pad_clear(pad, Px, Py)
                if clr < 0:
                    continue
                if clr >= target * MM:
                    cands.append((r, Px, Py))
                    break
        cands.sort()   # kleinste Bewegung zuerst
        for r, Px, Py in cands:
            if not via_ok(Px, Py, mynet, idx):
                continue
            # Stub-Anker: Punkt im Pad Richtung P (garantiert auf Pad-Kupfer)
            ang = math.atan2(Py - pc.y, Px - pc.x)
            bb = pad.GetBoundingBox()
            inr = min(bb.GetWidth(), bb.GetHeight()) // 4
            Ax = int(pc.x + math.cos(ang) * inr)
            Ay = int(pc.y + math.sin(ang) * inr)
            if not stub_ok(Ax, Ay, Px, Py, mynet, PL):
                continue
            if not all(dragged_seg_ok((Px, Py), (fx, fy), ly, mynet)
                       for t, fx, fy, ly, w in conn):
                continue
            v.SetPosition(pcbnew.VECTOR2I(Px, Py))
            VIA_OBS[idx][1] = Px
            VIA_OBS[idx][2] = Py
            for t, fx, fy, ly, which in conn:
                if which == "S":
                    t.SetStart(pcbnew.VECTOR2I(Px, Py))
                else:
                    t.SetEnd(pcbnew.VECTOR2I(Px, Py))
            stubs.append((Ax, Ay, Px, Py, mynet, PL))
            relocated += 1
            placed = True
            break
    if not placed:
        failed += 1
        fail_list.append((fp.GetReference(), pad.GetNumber(), mynet == GND))

for sx, sy, ex, ey, nc, ly in stubs:
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(sx, sy))
    tr.SetEnd(pcbnew.VECTOR2I(ex, ey))
    tr.SetWidth(STUB_W)
    tr.SetLayer(ly)
    tr.SetNetCode(nc)
    board.Add(tr)

print(f"reloziert(snug): {relocated} | offen: {failed}")
for r, n, g in fail_list:
    print(f"   OFFEN {r}.{n} [{'GND' if g else 'SIG'}]")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard("project/aurabip_routed.kicad_pcb", board)
print("gespeichert")
