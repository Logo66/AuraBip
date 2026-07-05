"""Platzierungs-Check: Courtyard-Ueberlappungen + Bauteile ausserhalb des Boards.
Usage: python check_place.py [board.kicad_pcb]
"""
import os
import sys

import pcbnew

BOARD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "project", "aurabip.kicad_pcb")
BW, BH = 52.0, 52.0
# Steckverbinder/Taster duerfen ueber die Kante ragen
EDGE_OK = {"J1", "J2", "J3", "SW1"}

T = pcbnew.ToMM
b = pcbnew.LoadBoard(BOARD)

boxes = {}   # ref -> (x1, y1, x2, y2, seite)
for fp in b.GetFootprints():
    side = "B" if fp.IsFlipped() else "F"
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    cy = fp.GetCourtyard(layer)
    if cy.OutlineCount() == 0:
        print(f"WARN {fp.GetReference()}: kein Courtyard")
        continue
    bb = cy.BBox()
    boxes[fp.GetReference()] = (T(bb.GetLeft()), T(bb.GetTop()),
                                T(bb.GetRight()), T(bb.GetBottom()), side)

refs = sorted(boxes)
overlaps = []
for i, a in enumerate(refs):
    ax1, ay1, ax2, ay2, aside = boxes[a]
    for bref in refs[i + 1:]:
        bx1, by1, bx2, by2, bside = boxes[bref]
        if aside != bside:
            continue
        ox = min(ax2, bx2) - max(ax1, bx1)
        oy = min(ay2, by2) - max(ay1, by1)
        if ox > 0.01 and oy > 0.01:
            overlaps.append((a, bref, round(min(ox, oy), 2)))

off = []
for r in refs:
    x1, y1, x2, y2, _side = boxes[r]
    if r in EDGE_OK:
        continue
    if x1 < 0.15 or y1 < 0.15 or x2 > BW - 0.15 or y2 > BH - 0.15:
        off.append((r, round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)))

print(f"Ueberlappungen: {len(overlaps)}")
for a, bref, d in overlaps:
    print(f"  {a} <-> {bref}  ({d} mm)")
print(f"Ausserhalb/zu nah an Kante: {len(off)}")
for r, x1, y1, x2, y2 in off:
    print(f"  {r}: x {x1}..{x2}  y {y1}..{y2}")
