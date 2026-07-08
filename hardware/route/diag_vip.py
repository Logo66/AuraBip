# -*- coding: utf-8 -*-
"""Diagnose: Via-in-SMD-Pad + Umgebung (Flanker-Netze)."""
import sys
import math
import pcbnew

T = pcbnew.ToMM
b = pcbnew.LoadBoard(r"project/aurabip_routed.kicad_pcb")
fps = list(b.GetFootprints())
vias = [v for v in b.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]
trks = [t for t in b.GetTracks()
        if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA)]

LMAP = {pcbnew.F_Cu: "F", pcbnew.B_Cu: "B",
        pcbnew.In1_Cu: "In1", pcbnew.In2_Cu: "In2"}

targets = []
for v in vias:
    vp = v.GetPosition()
    for fp in fps:
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if fp.GetReference() == "U1" and pad.GetNumber() == "61":
                continue
            if pad.HitTest(vp):
                targets.append((v, fp, pad))

print("=== Via-in-SMD-Pad (ohne U1.61):", len(targets), "===")
for v, fp, pad in targets:
    vp = v.GetPosition()
    ref = "%s.%s" % (fp.GetReference(), pad.GetNumber())
    net = pad.GetNetname()
    bb = pad.GetBoundingBox()
    print("\n-- %-10s [%s] @(%.2f,%.2f)  padW=%.2f padH=%.2f padLayers=%s" % (
        ref, net, T(vp.x), T(vp.y),
        T(bb.GetWidth()), T(bb.GetHeight()),
        "/".join(LMAP.get(l, str(l)) for l in pad.GetLayerSet().Seq() if l in LMAP)))
    # connected own-net tracks at this via
    own = []
    for t in trks:
        if t.GetNetCode() != pad.GetNetCode():
            continue
        for end in (t.GetStart(), t.GetEnd()):
            if math.hypot(T(end.x - vp.x), T(end.y - vp.y)) < 0.01:
                own.append(t)
                break
    print("   eigene Tracks an Via: %d" % len(own))
    for t in own:
        s, e = t.GetStart(), t.GetEnd()
        print("      %s  (%.2f,%.2f)->(%.2f,%.2f) w=%.3f" % (
            LMAP.get(t.GetLayer()), T(s.x), T(s.y), T(e.x), T(e.y), T(t.GetWidth())))
    # foreign copper within 1.2mm (flankers)
    flank = {}
    for t in trks:
        if t.GetNetCode() == pad.GetNetCode():
            continue
        s, e = t.GetStart(), t.GetEnd()
        # dist from via to segment
        ax, ay, bx, by = s.x, s.y, e.x, e.y
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            d = math.hypot(vp.x - ax, vp.y - ay)
        else:
            tt = max(0, min(1, ((vp.x-ax)*dx+(vp.y-ay)*dy)/(dx*dx+dy*dy)))
            d = math.hypot(vp.x-(ax+tt*dx), vp.y-(ay+tt*dy))
        if T(d) < 1.2:
            nm = t.GetNetname()
            flank[nm] = min(flank.get(nm, 9), T(d))
    print("   Flanker-Netze <1.2mm: %s" % (
        ", ".join("%s(%.2f)" % (k, v) for k, v in sorted(flank.items(), key=lambda x: x[1]))))
