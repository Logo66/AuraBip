"""Deterministische Rest-Verbindungen nach FreeRouting.

FreeRouting verwirft Pins in Footprint-Sperrzonen (SHT4x, u.FL) und
verliert gelegentlich einzelne Paare. Hier werden die bekannten Reste
mit kollisionsgeprueften L-Zuegen auf F.Cu geschlossen.

Usage: handroute.py <routed.kicad_pcb> <out.kicad_pcb>
"""
import math
import os
import sys

import pcbnew

WD = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = sys.argv[1], sys.argv[2]
MM, T = pcbnew.FromMM, pcbnew.ToMM

TRACK_W = MM(0.15)
CLR = MM(0.13)

log = open(os.path.join(WD, "handroute.log"), "w")


def L(*a):
    log.write(" ".join(str(x) for x in a) + "\n")
    log.flush()


b = pcbnew.LoadBoard(SRC)


def pad_of(ref, num):
    fp = b.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return p
    raise ValueError(f"{ref}.{num}?")


def seg_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


# Hindernisse auf F.Cu (fremdes Netz): Pads + Tracks + Via-Koerper
obst_pads, obst_tracks = [], []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if not p.IsOnLayer(pcbnew.F_Cu):
            continue
        pos = p.GetPosition()
        sz = p.GetSize()
        obst_pads.append((pos.x, pos.y, (sz.x + sz.y) / 4.0, p.GetNetCode()))
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        try:
            w = t.GetWidth(pcbnew.F_Cu)
        except TypeError:
            w = t.GetWidth()
        obst_pads.append((pos.x, pos.y, w / 2.0, t.GetNetCode()))
    elif t.GetLayer() == pcbnew.F_Cu:
        s, e = t.GetStart(), t.GetEnd()
        obst_tracks.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2.0, t.GetNetCode()))


def seg_free(x1, y1, x2, y2, net, skip_near=()):
    """Segment kollisionsfrei? skip_near: Punkte (Pads der Verbindung),
    Hindernisse in deren Naehe (< 0.65mm) werden ignoriert (Nachbarpads
    am eigenen Bauteil deckt die Pad-Clearance des Fills ab, nicht wir)."""
    hw = TRACK_W / 2.0
    for (px, py, r, onet) in obst_pads:
        if onet == net:
            continue
        if any(math.hypot(px - sx, py - sy) < MM(0.001) for sx, sy in skip_near):
            continue
        # r ist (min+max)/4 der Padmasse — Kreisnaeherung im Mittel;
        # Feinpruefung macht der finale DRC
        if seg_dist(x1, y1, x2, y2, px, py) < hw + r + CLR:
            return False
    for (ax, ay, bx, by, r, onet) in obst_tracks:
        if onet == net:
            continue
        # grober Segment-Segment-Test ueber beide Endpunkt-Distanzen + Mitte
        for (qx, qy) in ((ax, ay), (bx, by), ((ax + bx) / 2, (ay + by) / 2)):
            if seg_dist(x1, y1, x2, y2, qx, qy) < hw + r + CLR:
                return False
    return True


def add_track(x1, y1, x2, y2, net):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    t.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    t.SetWidth(TRACK_W)
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    b.Add(t)
    # neue Zuege sind Hindernisse fuer die folgenden Verbindungen
    obst_tracks.append((int(x1), int(y1), int(x2), int(y2), TRACK_W / 2.0, net.GetNetCode()))


def auto_exit(pad):
    """1-mm-Austritt radial weg vom Bauteilzentrum."""
    fp = pad.GetParentFootprint()
    fc = fp.GetPosition()
    pp = pad.GetPosition()
    dx, dy = pp.x - fc.x, pp.y - fc.y
    d = math.hypot(dx, dy) or 1.0
    return (T(dx / d * MM(1.0)), T(dy / d * MM(1.0)))


def route(refA, numA, refB, numB, exitA=None, exitB=None, auto_a=False):
    """Verbindet zwei Pads; Kandidaten: direkt, L-Zuege, Z-Zuege mit
    Kanal-Suche. exitA/B: fester Austritt (dx,dy mm); auto_a: Austritt
    radial vom Bauteilzentrum weg."""
    pa, pb = pad_of(refA, numA), pad_of(refB, numB)
    net = pa.GetNet()
    A = pa.GetPosition()
    B = pb.GetPosition()
    ax, ay, bx, by = A.x, A.y, B.x, B.y
    if auto_a and not exitA:
        exitA = auto_exit(pa)
    pts_a = [(ax, ay)]
    pts_b = [(bx, by)]
    if exitA:
        ax2, ay2 = ax + MM(exitA[0]), ay + MM(exitA[1])
        pts_a.append((ax2, ay2))
        ax, ay = ax2, ay2
    if exitB:
        bx2, by2 = bx + MM(exitB[0]), by + MM(exitB[1])
        pts_b.append((bx2, by2))
        bx, by = bx2, by2

    skip = [(A.x, A.y), (B.x, B.y)]
    nc = net.GetNetCode()

    candidates = [[], [(bx, ay)], [(ax, by)]]
    # Z-Zuege: Kanal in x und y durchsuchen (±3 mm um die Endpunkte)
    lo_x, hi_x = min(ax, bx) - MM(3), max(ax, bx) + MM(3)
    step = MM(0.2)
    cx = lo_x
    while cx <= hi_x:
        candidates.append([(cx, ay), (cx, by)])
        cx += step
    lo_y, hi_y = min(ay, by) - MM(3), max(ay, by) + MM(3)
    cy = lo_y
    while cy <= hi_y:
        candidates.append([(ax, cy), (bx, cy)])
        cy += step

    for mids in candidates:
        chain = pts_a + mids + list(reversed(pts_b))
        ok = all(seg_free(chain[i][0], chain[i][1], chain[i + 1][0], chain[i + 1][1], nc, skip)
                 for i in range(len(chain) - 1))
        if ok:
            for i in range(len(chain) - 1):
                if chain[i] != chain[i + 1]:
                    add_track(chain[i][0], chain[i][1], chain[i + 1][0], chain[i + 1][1], net)
            L(f"{refA}.{numA} -> {refB}.{numB} [{net.GetNetname()}]: {len(chain)-1} Segmente")
            return True
    L(f"FEHLGESCHLAGEN: {refA}.{numA} -> {refB}.{numB} [{net.GetNetname()}]")
    return False


def via_in_pad(ref, num):
    """Via direkt im Pad — bindet ein einzelnes Plane-Netz-Pad an die
    Innenlage. Vorher pruefen: nichts Fremdes auf B-Seite/anderen Lagen
    im Weg (Durchgangs-Via!). JLC kann Via-in-Pad; Serie: plugged (T-H1)."""
    pad = pad_of(ref, num)
    pos = pad.GetPosition()
    nc = pad.GetNetCode()
    lim_pad = MM(0.25) + MM(0.08)  # Via-Radius + Minimal-Clearance
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p is pad or p.GetNetCode() == nc and p.GetNetCode() != 0:
                continue
            pp = p.GetPosition()
            sz = p.GetSize()
            # schmale Nachbarpads (QFN): halbe Schmalseite zaehlt
            if math.hypot(pp.x - pos.x, pp.y - pos.y) < lim_pad + min(sz.x, sz.y) / 2.0:
                L(f"Via-in-Pad {ref}.{num}: blockiert durch {fp.GetReference()}.{p.GetNumber()}")
                return False
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetNetCode() == nc:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if seg_dist(s.x, s.y, e.x, e.y, pos.x, pos.y) < lim_pad + t.GetWidth() / 2.0:
            L(f"Via-in-Pad {ref}.{num}: blockiert durch Track [{t.GetNetname()}]")
            return False
    via = pcbnew.PCB_VIA(b)
    via.SetPosition(pos)
    via.SetWidth(MM(0.5))
    via.SetDrill(MM(0.3))
    via.SetNet(pad.GetNet())
    b.Add(via)
    obst_pads.append((pos.x, pos.y, MM(0.25), nc))
    L(f"Via-in-Pad {ref}.{num} [{pad.GetNetname()}]")
    return True


results = []
# SHT40 (auf der Sensor-Insel): I2C zum BMP581 daneben — R3/R4 liegen
# auf dem Hauptboard, dorthin fuehrt nur die Bruecke (macht FreeRouting
# fuer den BMP581; SHT40 haengt sich hier lokal an dessen Pads)
results.append(route("U4", "1", "U2", "4", exitA=(-0.9, 0)))
results.append(route("U4", "2", "U2", "2", exitA=(-0.9, 0.6)))
# CC2: USB-Pad senkrecht nach oben raus
results.append(route("J1", "B5", "R2", "1", exitA=(0, -1.3)))
# AMP_SD: ESP-Pin zu Pullup, radial raus aus dem Modul-Padfeld
results.append(route("U1", "11", "R8", "2", auto_a=True))
# GND-Nachzuegler: Via-in-Pad direkt in die GND-Innenlage;
# wo blockiert (E22 auf der Rueckseite!) -> Track zum U6.8-Via
r_u68 = via_in_pad("U6", "8")
results.append(r_u68)
if not via_in_pad("C9", "2"):
    results.append(route("C9", "2", "U6", "8", exitA=(0, 0.9)))
else:
    results.append(True)

fails = results.count(False)
L(f"{len(results) - fails}/{len(results)} Verbindungen gelegt")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(OUT)
L("saved")
print(f"handroute: {len(results) - fails}/{len(results)} ok, {fails} offen")
