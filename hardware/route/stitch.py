"""GND-Stitch-Vias NACH dem Routing setzen (kollisionsbewusst gegen alles).
Usage: stitch.py <routed.kicad_pcb> <out.kicad_pcb>
"""
import math
import os
import sys

import pcbnew

WD = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = sys.argv[1], sys.argv[2]
MM = pcbnew.FromMM

VIA_OD, VIA_DR = MM(0.5), MM(0.3)
CLR = MM(0.25)
# Antennen-Keepout ESP32
KO = (MM(-1), MM(17.4), MM(6.3), MM(34.6))

log = open(os.path.join(WD, "stitch.log"), "w")


def L(*a):
    log.write(" ".join(str(x) for x in a) + "\n")
    log.flush()


def seg_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


b = pcbnew.LoadBoard(SRC)
gnd = None
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() == "GND":
            gnd = pad.GetNet()
            break
    if gnd:
        break

# Hindernisse: alle Pads (fremde Netze), alle Tracks/Vias (fremde Netze),
# GND-Vias nur auf Bohrabstand
pads = []
for fp in b.GetFootprints():
    for pad in fp.Pads():
        p = pad.GetPosition()
        sz = pad.GetSize()
        pads.append((p.x, p.y, max(sz.x, sz.y) / 2.0, pad.GetNetCode()))
tracks = []
vias = []
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        vias.append((p.x, p.y, t.GetWidth() / 2.0, t.GetNetCode()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        tracks.append((s.x, s.y, e.x, e.y, t.GetWidth() / 2.0, t.GetNetCode()))

gc = gnd.GetNetCode()
rv = VIA_OD / 2.0
added = 0
gx = MM(3.0)
while gx <= MM(48.0):     # Board 52x52
    gy = MM(3.0)
    while gy <= MM(48.0):
        ok = True
        if KO[0] <= gx <= KO[2] and KO[1] <= gy <= KO[3]:
            ok = False
        # runde Ecken (r=1.5) meiden: Via >= 2mm von jeder Ecke
        for (ex, ey) in ((3.0, 3.0), (49.0, 3.0), (3.0, 49.0), (49.0, 49.0)):
            if math.hypot(gx - MM(ex), gy - MM(ey)) < MM(2.5):
                ok = False
                break
        if ok:
            for (px, py, r, net) in pads:
                lim = rv + r + (CLR if net != gc else MM(0.15))
                if math.hypot(gx - px, gy - py) < lim:
                    ok = False
                    break
        if ok:
            for (x1, y1, x2, y2, r, net) in tracks:
                lim = rv + r + (CLR if net != gc else MM(0.05))
                if seg_dist(x1, y1, x2, y2, gx, gy) < lim:
                    ok = False
                    break
        if ok:
            for (px, py, r, net) in vias:
                if math.hypot(gx - px, gy - py) < rv + r + MM(0.3):
                    ok = False
                    break
        if ok:
            via = pcbnew.PCB_VIA(b)
            via.SetPosition(pcbnew.VECTOR2I(int(gx), int(gy)))
            via.SetWidth(VIA_OD)
            via.SetDrill(VIA_DR)
            via.SetNet(gnd)
            b.Add(via)
            vias.append((gx, gy, rv, gc))
            added += 1
        gy += MM(5.0)
    gx += MM(5.0)

L("stitch vias:", added)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
L("zones filled")
b.Save(OUT)
L("saved", os.path.getsize(OUT), "bytes")
