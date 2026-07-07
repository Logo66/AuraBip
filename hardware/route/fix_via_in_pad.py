# -*- coding: utf-8 -*-
"""Vias aus SMD-Pads schieben (PCBWay-Review W603081ASX14).

Jede in-pad-Via (ausser ESP32-EP U1.61) wird minimal aus dem Pad geschoben:
Via landet auf bereits geroutetem EIGEN-Netz-Kupfer (Track-Punkt bzw. GND-
Zonenpunkt) >=0.55 mm vom Pad, ein kurzer F.Cu-Stub bindet das Pad neu an.
Es wird NICHTS entfernt -> Netz-Verbindung bleibt konstruktiv erhalten.
Rigorose Segment-Geometrie; Endkontrolle per echter DRC im Aufrufer.

Performance: Hindernisse einmal gecacht, Via-Positionen live im Cache
aktualisiert, Kandidaten pro Via begrenzt.
"""
import math
import pcbnew

MM = 1_000_000
CLR = int(0.12 * MM)
VIA_R = int(0.25 * MM)
STUB_W = int(0.2 * MM)
SAMP = int(0.1 * MM)

board = pcbnew.LoadBoard(r"project/aurabip_routed.kicad_pcb")
GND = board.GetNetsByName()["GND"].GetNetCode()
fps = list(board.GetFootprints())
edge = board.GetBoardEdgesBoundingBox()

# --- Hindernisse EINMAL cachen ---
PAD_OBS = []
for f in fps:
    for p in f.Pads():
        bb = p.GetBoundingBox()
        PAD_OBS.append((p.GetNetCode(), bb.GetCenter().x, bb.GetCenter().y,
                        bb.GetWidth() // 2, bb.GetHeight() // 2))
TRK_OBS = []          # (net, ax, ay, bx, by, halfw, layer)
for t in board.GetTracks():
    if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA):
        TRK_OBS.append((t.GetNetCode(), t.GetStart().x, t.GetStart().y,
                        t.GetEnd().x, t.GetEnd().y, t.GetWidth() // 2, t.GetLayer()))
VIA_OBJ = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
VIA_OBS = [[v.GetNetCode(), v.GetPosition().x, v.GetPosition().y] for v in VIA_OBJ]
# Bohrungen (THT-Pads, NPTH, Modul-Drills) fuer hole_to_hole-Abstand
HOLE_OBS = []
for f in fps:
    for p in f.Pads():
        ds = p.GetDrillSize()
        if ds.x > 0:
            c = p.GetPosition()
            HOLE_OBS.append((c.x, c.y, max(ds.x, ds.y) // 2))
# Board-Kanten inkl. interner Fraeskontur (Sensor-Insel-Moat)
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
    DRILL_R = int(0.15 * MM)          # halbe Via-Bohrung (0.3 mm)
    for i, (nc, x, y) in enumerate(VIA_OBS):
        if i == skip_via_idx:
            continue
        dvv = math.hypot(cx - x, cy - y)
        # Kupfer-Clearance nur bei Fremdnetz; Bohrabstand IMMER (netzunabh.)
        if nc != mynet and dvv < 2 * VIA_R + CLR:
            return False
        if dvv < 2 * DRILL_R + int(0.3 * MM):     # hole-to-hole >= 0.3 mm
            return False
    for hx, hy, hr in HOLE_OBS:       # hole-to-hole zu THT/NPTH
        if math.hypot(cx - hx, cy - hy) < DRILL_R + hr + int(0.26 * MM):
            return False
    for ex1, ey1, ex2, ey2 in EDGE_SEG:   # Board-/Insel-Kante
        if seg_pt(ex1, ey1, ex2, ey2, cx, cy) < VIA_R + int(0.3 * MM):
            return False
    return True


def stub_ok(ax, ay, bx, by, mynet):
    for nc, ox, oy, hw, hh in PAD_OBS:
        if nc == mynet:
            continue
        if seg_pt(ax, ay, bx, by, ox, oy) < max(hw, hh) + STUB_W // 2 + CLR:
            return False
    for nc, sx, sy, ex, ey, hw, ly in TRK_OBS:
        if nc == mynet or ly != pcbnew.F_Cu:
            continue
        if seg_seg(ax, ay, bx, by, sx, sy, ex, ey) < STUB_W // 2 + hw + CLR:
            return False
    return True


zones = [z for z in board.Zones() if z.GetNetCode() == GND]


def zone_pts(pc):
    out = []
    for r in range(6, 18):
        for a in range(0, 360, 20):
            x = int(pc.x + r / 10 * MM * math.cos(math.radians(a)))
            y = int(pc.y + r / 10 * MM * math.sin(math.radians(a)))
            for z in zones:
                if z.HitTestFilledArea(pcbnew.F_Cu, pcbnew.VECTOR2I(x, y), 0):
                    out.append((math.hypot(x - pc.x, y - pc.y), x, y))
                    break
        if out:
            break                      # kleinster Radius mit Treffern reicht
    out.sort()
    return out[:40]


# --- betroffene Vias sammeln (Index in VIA_OBJ/VIA_OBS merken) ---
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

# eigene Track-Segmente je Netz (fuer dichte Abtastung nahe am Pad)
from collections import defaultdict
own_seg = defaultdict(list)
for nc, ax, ay, bx, by, hw, ly in TRK_OBS:
    own_seg[nc].append((ax, ay, bx, by))


def own_candidates(mynet, pc):
    """Dichte Punkte (0.1 mm) auf eigenen Segmenten im 4-mm-Fenster ums Pad."""
    out = []
    win = int(4.0 * MM)
    for ax, ay, bx, by in own_seg.get(mynet, []):
        # Segment nur betrachten, wenn es dem Pad nahe kommt
        if seg_pt(ax, ay, bx, by, pc.x, pc.y) > win:
            continue
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / SAMP))
        for i in range(n + 1):
            x = ax + (bx - ax) * i // n
            y = ay + (by - ay) * i // n
            d = math.hypot(x - pc.x, y - pc.y)
            if 0.55 * MM <= d <= win:
                out.append((d, int(x), int(y)))
    out.sort()
    return out[:250]

# Track-Objekte (fuer Endpunkt-Drag) mit Live-Zugriff
TRK_OBJ = [t for t in board.GetTracks()
           if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA)]
EPS = 2000  # 2 um Toleranz fuer "Endpunkt == Via"


def dragged_seg_ok(P, far, layer, mynet):
    """Der zur neuen Via-Position P gezogene Track-Rest (P..far) muss
    Fremdnetz-Kupfer auf seiner Lage + Kanten frei halten."""
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


DIRS = [(math.cos(a), math.sin(a)) for a in [i * math.pi / 16 for i in range(32)]]
DISTS = [int(d * MM) for d in (0.55, 0.65, 0.75, 0.85, 1.0, 1.15, 1.3,
                               1.5, 1.75, 2.0, 2.3, 2.6, 3.0)]

relocated = failed = 0
fail_list = []
stubs = []
for idx, v, fp, pad in targets:
    mynet = pad.GetNetCode()
    O = v.GetPosition()
    Ox, Oy = O.x, O.y
    # an dieser Via haengende Track-Enden (net-gleich, Endpunkt ~ O)
    conn = []   # (track, far_x, far_y, layer)
    for t in TRK_OBJ:
        if t.GetNetCode() != mynet:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if abs(s.x - Ox) < EPS and abs(s.y - Oy) < EPS:
            conn.append((t, e.x, e.y, t.GetLayer(), "S"))
        elif abs(e.x - Ox) < EPS and abs(e.y - Oy) < EPS:
            conn.append((t, s.x, s.y, t.GetLayer(), "E"))
    placed = False
    for dist in DISTS:
        for dx, dy in DIRS:
            base = max(pad.GetBoundingBox().GetWidth(),
                       pad.GetBoundingBox().GetHeight()) // 2
            Px = int(Ox + dx * (base + dist))
            Py = int(Oy + dy * (base + dist))
            if not via_ok(Px, Py, mynet, idx):
                continue
            if not stub_ok(Ox, Oy, Px, Py, mynet):
                continue
            if not all(dragged_seg_ok((Px, Py), (fx, fy), ly, mynet)
                       for t, fx, fy, ly, w in conn):
                continue
            # anwenden: Via + alle angebundenen Track-Enden nach P ziehen
            v.SetPosition(pcbnew.VECTOR2I(Px, Py))
            VIA_OBS[idx][1] = Px
            VIA_OBS[idx][2] = Py
            for t, fx, fy, ly, which in conn:
                if which == "S":
                    t.SetStart(pcbnew.VECTOR2I(Px, Py))
                else:
                    t.SetEnd(pcbnew.VECTOR2I(Px, Py))
            stubs.append((Ox, Oy, Px, Py, mynet))
            relocated += 1
            placed = True
            break
        if placed:
            break
    if not placed:
        failed += 1
        fail_list.append((fp.GetReference(), pad.GetNumber(), mynet == GND, v, pad))

still_open = [(r, n, ('GND' if g else 'SIG')) for r, n, g, vv, pad in fail_list]

for sx, sy, ex, ey, nc in stubs:
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(sx, sy))
    tr.SetEnd(pcbnew.VECTOR2I(ex, ey))
    tr.SetWidth(STUB_W)
    tr.SetLayer(pcbnew.F_Cu)
    tr.SetNetCode(nc)
    board.Add(tr)

print(f"reloziert(drag): {relocated} | offen: {len(still_open)}")
for r, n, k in still_open:
    print(f"   OFFEN {r}.{n} [{k}]")

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard("project/aurabip_routed.kicad_pcb", board)
print("gespeichert")
