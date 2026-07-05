"""Deterministischer Rest-Router v2 — schliesst alles, was FreeRouting
liegen laesst: LoRa-Bus (F->Via->B), Testpads, USB, I2S, EN, Insel-I2C.

Exakte Rechteck-Kollisionspruefung (Pad-Boundingboxen), Via-Suche mit
Bohrabstand, L/Z-Kandidaten mit Kanal-Sweep je Lage.

Usage: handroute2.py <routed.kicad_pcb> <out.kicad_pcb>
"""
import math
import os
import sys

import pcbnew

WD = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = sys.argv[1], sys.argv[2]
MM, T = pcbnew.FromMM, pcbnew.ToMM

TRACK_W = MM(0.15)
CLR = MM(0.12)
VIA_OD, VIA_DR = MM(0.5), MM(0.3)
HOLE_CLR = MM(0.25)

log = open(os.path.join(WD, "handroute4.log"), "w")


def L(*a):
    log.write(" ".join(str(x) for x in a) + "\n")
    log.flush()


b = pcbnew.LoadBoard(SRC)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
_fps = {fp.GetReference(): fp for fp in b.GetFootprints()}

# NICHT-DESTRUKTIV: FreeRoutings Zuege bleiben stehen, wir ergaenzen nur
# die offenen Netze. Nur echte Null-Segmente raus.
to_remove = []
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T and t.GetStart() == t.GetEnd():
        to_remove.append(t)
_remove_ids = {t.m_Uuid.AsString() for t in to_remove}

# ---------- Hindernis-Listen (exakte AABBs) ----------
# pad_rects[layer] = [(x1,y1,x2,y2,net)]
pad_rects = {F: [], B: []}
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        r = (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom(),
             p.GetNetCode())
        for layer in (F, B):
            if p.IsOnLayer(layer):
                pad_rects[layer].append(r)

seg_obst = {F: [], B: []}   # (x1,y1,x2,y2,halfw,net)
via_obst = []               # (x,y,r,net)
for t in b.GetTracks():
    if t.m_Uuid.AsString() in _remove_ids:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        try:
            w = t.GetWidth(F)
        except TypeError:
            w = t.GetWidth()
        via_obst.append((pos.x, pos.y, w / 2.0, t.GetNetCode()))
    elif t.GetLayer() in (F, B):
        s, e = t.GetStart(), t.GetEnd()
        seg_obst[t.GetLayer()].append(
            (s.x, s.y, e.x, e.y, t.GetWidth() / 2.0, t.GetNetCode()))


# jetzt (nach allen Iterationen) wirklich loeschen
for t in to_remove:
    b.Remove(t)
L("entfernt:", len(to_remove))


def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _intersect(a1, a2, b1, b2):
    d1, d2 = _orient(b1, b2, a1), _orient(b1, b2, a2)
    d3, d4 = _orient(a1, a2, b1), _orient(a1, a2, b2)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return False


def seg_seg_dist(a1, a2, b1, b2):
    if _intersect(a1, a2, b1, b2):
        return 0.0
    def d(p, q1, q2):
        dx, dy = q2[0] - q1[0], q2[1] - q1[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - q1[0], p[1] - q1[1])
        t_ = max(0.0, min(1.0, ((p[0] - q1[0]) * dx + (p[1] - q1[1]) * dy) /
                          float(dx * dx + dy * dy)))
        return math.hypot(p[0] - (q1[0] + t_ * dx), p[1] - (q1[1] + t_ * dy))
    return min(d(a1, b1, b2), d(a2, b1, b2), d(b1, a1, a2), d(b2, a1, a2))


def seg_rect_clear(x1, y1, x2, y2, rect, margin):
    rx1, ry1, rx2, ry2 = rect[0] - margin, rect[1] - margin, rect[2] + margin, rect[3] + margin
    # Segment-AABB-Test (Slab)
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx1), (dx, rx2 - x1), (-dy, y1 - ry1), (dy, ry2 - y1)):
        if p == 0:
            if q < 0:
                return True   # parallel ausserhalb
        else:
            r = q / float(p)
            if p < 0:
                if r > t1:
                    return True
                t0 = max(t0, r)
            else:
                if r < t0:
                    return True
                t1 = min(t1, r)
    return t0 > t1


def window_lists(x1, y1, x2, y2, net, skip_pts, margin_mm=4.5):
    """Hindernisse auf das Routen-Fenster vorfiltern (grosser Speedup)."""
    m = MM(margin_mm)
    wx1, wy1 = min(x1, x2) - m, min(y1, y2) - m
    wx2, wy2 = max(x1, x2) + m, max(y1, y2) + m
    pads = {F: [], B: []}
    for layer in (F, B):
        for rect in pad_rects[layer]:
            if rect[4] == net:
                continue
            if rect[2] < wx1 or rect[0] > wx2 or rect[3] < wy1 or rect[1] > wy2:
                continue
            cx, cy = (rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0
            if any(math.hypot(cx - sx, cy - sy) < MM(0.01) for sx, sy in skip_pts):
                continue
            pads[layer].append(rect)
    segs = {F: [], B: []}
    for layer in (F, B):
        for s in seg_obst[layer]:
            if s[5] == net:
                continue
            if max(s[0], s[2]) < wx1 or min(s[0], s[2]) > wx2:
                continue
            if max(s[1], s[3]) < wy1 or min(s[1], s[3]) > wy2:
                continue
            segs[layer].append(s)
    vias = [v for v in via_obst
            if v[3] != net and wx1 - m < v[0] < wx2 + m and wy1 - m < v[1] < wy2 + m]
    return pads, segs, vias


_ctx = {"pads": None, "segs": None, "vias": None}


def seg_free(layer, x1, y1, x2, y2, net, skip_pts=()):
    hw = TRACK_W / 2.0
    for rect in _ctx["pads"][layer]:
        if not seg_rect_clear(x1, y1, x2, y2, rect, hw + CLR):
            return False
    for (ax, ay, bx, by, ohw, onet) in _ctx["segs"][layer]:
        if seg_seg_dist((x1, y1), (x2, y2), (ax, ay), (bx, by)) < hw + ohw + CLR:
            return False
    for (vx, vy, vr, onet) in _ctx["vias"]:
        if seg_seg_dist((x1, y1), (x2, y2), (vx, vy), (vx, vy)) < hw + vr + CLR:
            return False
    return True


def via_free(x, y, net):
    rv = VIA_OD / 2.0
    for layer in (F, B):
        for rect in pad_rects[layer]:
            if rect[4] == net and rect[4] != 0:
                continue
            m = rv + CLR
            if rect[0] - m < x < rect[2] + m and rect[1] - m < y < rect[3] + m:
                return False
    for (ax, ay, bx, by, ohw, onet) in seg_obst[F] + seg_obst[B]:
        if onet == net:
            continue
        if seg_seg_dist((x, y), (x, y), (ax, ay), (bx, by)) < rv + ohw + CLR:
            return False
    for (vx, vy, vr, onet) in via_obst:
        if math.hypot(x - vx, y - vy) < VIA_DR + HOLE_CLR + vr * 0 + MM(0.3):
            return False
    # Board-Rand + Insel-Graben + Antennen-Keepouts
    xm, ym = T(x), T(y)
    if not (0.8 < xm < 51.2 and 0.8 < ym < 51.2):
        return False
    if 42.9 < xm < 50.6 and 18.0 < ym < 28.6 and not (45.1 < xm < 49.4 and 20.2 < ym < 26.4):
        return False
    if xm < 6.3 and 17.4 < ym < 34.6:
        return False
    if 15.3 < xm < 20.7 and ym < 8.7:
        return False
    return True


def add_seg(layer, x1, y1, x2, y2, net):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetWidth(TRACK_W)
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)
    seg_obst[layer].append((int(x1), int(y1), int(x2), int(y2),
                            TRACK_W / 2.0, net.GetNetCode()))


def add_via(x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetWidth(VIA_OD)
    v.SetDrill(VIA_DR)
    v.SetNet(net)
    b.Add(v)
    via_obst.append((int(x), int(y), VIA_OD / 2.0, net.GetNetCode()))


def pad_of(ref, num):
    for p in _fps[ref].Pads():
        if p.GetNumber() == num:
            return p
    raise ValueError(f"{ref}.{num}")


def pad_layer(p):
    return B if (p.IsOnLayer(B) and not p.IsOnLayer(F)) else F


def auto_exit(pad, dist=1.0):
    fp = pad.GetParentFootprint()
    fc, pp = fp.GetPosition(), pad.GetPosition()
    dx, dy = pp.x - fc.x, pp.y - fc.y
    d = math.hypot(dx, dy) or 1.0
    return (pp.x + dx / d * MM(dist), pp.y + dy / d * MM(dist))


def path_candidates(ax, ay, bx, by):
    yield [(bx, ay)]
    yield [(ax, by)]
    yield []                                   # direkte Diagonale
    for f in (0.3, 0.5, 0.7):                  # Diagonal-Doglegs
        yield [(ax + (bx - ax) * f, ay + (by - ay) * f)]
        yield [(ax + (bx - ax) * f, ay), (ax + (bx - ax) * f, by)]
    lo, hi = min(ax, bx) - MM(3), max(ax, bx) + MM(3)
    c = lo
    while c <= hi:
        yield [(c, ay), (c, by)]
        c += MM(0.4)
    lo, hi = min(ay, by) - MM(3), max(ay, by) + MM(3)
    c = lo
    while c <= hi:
        yield [(ax, c), (bx, c)]
        c += MM(0.4)


def chain_ok(layer, pts, net, skip):
    for i in range(len(pts) - 1):
        if pts[i] == pts[i + 1]:
            continue
        if not seg_free(layer, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                        net, skip):
            return False
    return True


def lay_chain(layer, pts, net):
    for i in range(len(pts) - 1):
        if pts[i] != pts[i + 1]:
            add_seg(layer, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], net)


def route_same_layer(refA, numA, refB, numB, exit_a=None):
    pa, pb = pad_of(refA, numA), pad_of(refB, numB)
    layer = pad_layer(pa)
    net = pa.GetNet()
    nc = net.GetNetCode()
    A, Bp = pa.GetPosition(), pb.GetPosition()
    skip = [(A.x, A.y), (Bp.x, Bp.y)]
    _ctx["pads"], _ctx["segs"], _ctx["vias"] = window_lists(
        A.x, A.y, Bp.x, Bp.y, nc, skip)
    starts = [(A.x, A.y)]
    if exit_a:
        ex = (A.x + MM(exit_a[0]), A.y + MM(exit_a[1]))
        if seg_free(layer, A.x, A.y, ex[0], ex[1], nc, skip):
            starts = [(A.x, A.y), ex]
    ax, ay = starts[-1]
    for mids in path_candidates(ax, ay, Bp.x, Bp.y):
        pts = starts + mids + [(Bp.x, Bp.y)]
        if chain_ok(layer, pts, nc, skip):
            lay_chain(layer, pts, net)
            L(f"OK  {refA}.{numA}->{refB}.{numB} [{net.GetNetname()}] {len(pts)-1} Seg")
            return True
    L(f"FAIL {refA}.{numA}->{refB}.{numB} [{net.GetNetname()}]")
    return False


def find_via_spots(near_x, near_y, net, want=5):
    out = []
    for rad in (0.0, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5):
        steps = 1 if rad == 0 else 12
        for k in range(steps):
            a = 2 * math.pi * k / steps
            x = near_x + MM(rad) * math.cos(a)
            y = near_y + MM(rad) * math.sin(a)
            if via_free(x, y, net):
                out.append((int(x), int(y)))
                if len(out) >= want:
                    return out
    return out


def route_cross_layer(refA, numA, refB, numB):
    """A (F) -> Escape -> Via -> B.Cu -> B-Pad (oder zweites Via bei F-Ziel)."""
    pa, pb = pad_of(refA, numA), pad_of(refB, numB)
    net = pa.GetNet()
    nc = net.GetNetCode()
    la, lb = pad_layer(pa), pad_layer(pb)
    A, Bp = pa.GetPosition(), pb.GetPosition()
    skip = [(A.x, A.y), (Bp.x, Bp.y)]
    _ctx["pads"], _ctx["segs"], _ctx["vias"] = window_lists(
        A.x, A.y, Bp.x, Bp.y, nc, skip)

    ex = auto_exit(pa, 1.0)
    if not seg_free(la, A.x, A.y, ex[0], ex[1], nc, skip):
        ex = auto_exit(pa, 1.6)
        if not seg_free(la, A.x, A.y, ex[0], ex[1], nc, skip):
            ex = (A.x, A.y)

    v1s = [v for v in find_via_spots(ex[0], ex[1], nc)
           if seg_free(la, ex[0], ex[1], v[0], v[1], nc, skip)]
    if not v1s:
        L(f"FAIL {refA}.{numA}->{refB}.{numB}: kein Via-Platz bei Escape")
        return False

    if lb != la:
        for v1 in v1s:
            for mids in path_candidates(v1[0], v1[1], Bp.x, Bp.y):
                pts = [v1] + mids + [(Bp.x, Bp.y)]
                if chain_ok(lb, pts, nc, skip):
                    if ex != (A.x, A.y):
                        add_seg(la, A.x, A.y, ex[0], ex[1], net)
                    add_seg(la, ex[0], ex[1], v1[0], v1[1], net)
                    add_via(v1[0], v1[1], net)
                    lay_chain(lb, pts, net)
                    L(f"OK  {refA}.{numA}->{refB}.{numB} [{net.GetNetname()}] via")
                    return True
        L(f"FAIL {refA}.{numA}->{refB}.{numB}: B-Pfad blockiert")
        return False

    exb = auto_exit(pb, 1.0)
    if not seg_free(la, Bp.x, Bp.y, exb[0], exb[1], nc, skip):
        exb = (Bp.x, Bp.y)
    v2s = [v for v in find_via_spots(exb[0], exb[1], nc)
           if seg_free(la, v[0], v[1], Bp.x, Bp.y, nc, skip)]
    if not v2s:
        L(f"FAIL {refA}.{numA}->{refB}.{numB}: kein Via-Platz am Ziel")
        return False
    for v1 in v1s:
        for v2 in v2s:
            for mids in path_candidates(v1[0], v1[1], v2[0], v2[1]):
                pts = [v1] + mids + [v2]
                if chain_ok(B, pts, nc, skip):
                    if ex != (A.x, A.y):
                        add_seg(la, A.x, A.y, ex[0], ex[1], net)
                    add_seg(la, ex[0], ex[1], v1[0], v1[1], net)
                    add_via(v1[0], v1[1], net)
                    lay_chain(B, pts, net)
                    add_via(v2[0], v2[1], net)
                    add_seg(la, v2[0], v2[1], Bp.x, Bp.y, net)
                    L(f"OK  {refA}.{numA}->{refB}.{numB} [{net.GetNetname()}] 2 Vias")
                    return True
    L(f"FAIL {refA}.{numA}->{refB}.{numB}: B-Umweg blockiert")
    return False


def via_in_pad(ref, num):
    pad = pad_of(ref, num)
    pos = pad.GetPosition()
    nc = pad.GetNetCode()
    if not via_free(pos.x, pos.y, nc):
        L(f"FAIL Via-in-Pad {ref}.{num}")
        return False
    add_via(pos.x, pos.y, pad.GetNet())
    L(f"OK  Via-in-Pad {ref}.{num} [{pad.GetNetname()}]")
    return True


results = []


def route_pair(refA, numA, refB, numB, exit_a=None):
    if route_same_layer(refA, numA, refB, numB, exit_a=exit_a):
        return True
    return route_cross_layer(refA, numA, refB, numB)


def gnd_hookup(ref, num):
    if via_in_pad(ref, num):
        return True
    pad = pad_of(ref, num)
    pos = pad.GetPosition()
    net = pad.GetNet()
    nc = net.GetNetCode()
    layer = pad_layer(pad)
    skip = [(pos.x, pos.y)]
    _ctx["pads"], _ctx["segs"], _ctx["vias"] = window_lists(
        pos.x, pos.y, pos.x, pos.y, nc, skip)
    for rad in (0.6, 0.8, 1.0, 1.3, 1.6, 2.0):
        for k in range(16):
            a = 2 * math.pi * k / 16
            x = pos.x + MM(rad) * math.cos(a)
            y = pos.y + MM(rad) * math.sin(a)
            if via_free(x, y, nc) and seg_free(layer, pos.x, pos.y, x, y, nc, skip):
                add_seg(layer, pos.x, pos.y, x, y, net)
                add_via(x, y, net)
                L(f"OK  GND-Hookup {ref}.{num}")
                return True
    L(f"FAIL GND-Hookup {ref}.{num}")
    return False


# Feste, geometrisch sinnvolle Paarungen fuer bekannte Zwei-Pad-Verbindungen.
# Werden nur ausgefuehrt, wenn das Netz laut Connectivity noch offen ist.
b.BuildConnectivity()
conn = b.GetConnectivity()


def net_open(ref, num):
    """True, wenn dieser Pad noch unrouted (ungebundene Ratsnest-Kante)."""
    try:
        pad = pad_of(ref, num)
    except Exception:
        return False
    return conn.GetRatsnestForPad(pad).__len__() > 0 if hasattr(
        conn, "GetRatsnestForPad") else True


def try_pair(refA, numA, refB, numB, exit_a=None, cross=False):
    if not net_open(refA, numA):
        return None
    r = (route_cross_layer(refA, numA, refB, numB) if cross
         else route_pair(refA, numA, refB, numB, exit_a=exit_a))
    b.BuildConnectivity()
    return r


PAIRS = [
    ("U10", "21", "J5", "1", None, False),     # LORA_ANT
    ("U1", "25", "U10", "19", None, True),
    ("U1", "16", "U10", "18", None, True),
    ("U1", "15", "U10", "17", None, True),
    ("U1", "17", "U10", "16", None, True),
    ("U1", "18", "U10", "14", None, True),
    ("U1", "19", "U10", "15", None, True),
    ("U1", "7",  "U10", "13", None, True),
    ("U1", "20", "U10", "7",  None, True),
    ("U1", "33", "U10", "6",  None, True),
    ("U1", "34", "TP1", "1",  None, True),
    ("U1", "36", "TP2", "1",  None, True),
    ("U1", "37", "TP3", "1",  None, True),
    ("U1", "38", "TP4", "1",  None, True),
    ("U1", "23", "U9", "6",   None, False),
    ("U1", "24", "U9", "4",   None, False),
    ("U1", "45", "R5", "2",   None, False),
    ("U1", "10", "U6", "1",   None, False),
    ("U1", "9",  "U6", "14",  None, False),
    ("J1", "B5", "R2", "1",   (0, -1.3), False),
    ("U1", "11", "R8", "2",   None, False),
    ("U4", "1",  "U2", "4",   (-0.9, 0), False),
    ("U4", "2",  "U2", "2",   (-0.9, 0.6), False),
]
for (ra, na, rb, nb, ex, cr) in PAIRS:
    r = try_pair(ra, na, rb, nb, exit_a=ex, cross=cr)
    if r is not None:
        results.append(r)
for ref, num in [("U2", "3"), ("U6", "3"), ("U6", "11"), ("U6", "15"),
                 ("U5", "31")]:
    if net_open(ref, num):
        results.append(gnd_hookup(ref, num))
        b.BuildConnectivity()

ok = results.count(True)
L(f"{ok}/{len(results)} Verbindungen")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(OUT)
print(f"handroute4: {ok}/{len(results)}")
