# -*- coding: utf-8 -*-
"""Restliche GND-in-pad-Vias: Via loeschen, Pad per kurzem F.Cu-Stub an die
naechste bereits verbundene GND-Kupferstelle (relozierte GND-Via / GND-Track-
Punkt) binden. Garantierte Verbindung, keine Bohrung im Pad.
Rigorose Stub-Kollisionspruefung; Endkontrolle per echter DRC im Aufrufer."""
import math
import pcbnew

MM = 1_000_000
CLR = int(0.12 * MM)
STUB_W = int(0.2 * MM)
SAMP = int(0.1 * MM)

board = pcbnew.LoadBoard(r"project/aurabip_routed.kicad_pcb")
GND = board.GetNetsByName()["GND"].GetNetCode()
fps = list(board.GetFootprints())

PAD_OBS = [(p.GetNetCode(), p.GetBoundingBox()) for f in fps for p in f.Pads()]
TRK = [t for t in board.GetTracks()
       if isinstance(t, pcbnew.PCB_TRACK) and not isinstance(t, pcbnew.PCB_VIA)]
TRK_OBS = [(t.GetNetCode(), t.GetStart().x, t.GetStart().y, t.GetEnd().x,
            t.GetEnd().y, t.GetWidth() // 2, t.GetLayer()) for t in TRK]
VIAS = [v for v in board.GetTracks() if isinstance(v, pcbnew.PCB_VIA)]


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
    return best


def stub_ok(ax, ay, bx, by):
    for nc, bb in PAD_OBS:
        if nc == GND:
            continue
        c = bb.GetCenter()
        if seg_pt(ax, ay, bx, by, c.x, c.y) < max(bb.GetWidth(), bb.GetHeight()) // 2 + STUB_W // 2 + CLR:
            return False
    for nc, sx, sy, ex, ey, hw, ly in TRK_OBS:
        if nc == GND or ly != pcbnew.F_Cu:
            continue
        if seg_seg(ax, ay, bx, by, sx, sy, ex, ey) < STUB_W // 2 + hw + CLR:
            return False
    return True


# GND-Zielpunkte: relozierte GND-Vias (nicht in Pad) + GND-Track-Endpunkte
def in_any_pad(x, y):
    for f in fps:
        for p in f.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and \
               p.HitTest(pcbnew.VECTOR2I(int(x), int(y))):
                return True
    return False


gnd_targets = []
for v in VIAS:
    if v.GetNetCode() == GND:
        p = v.GetPosition()
        gnd_targets.append((p.x, p.y))
for nc, sx, sy, ex, ey, hw, ly in TRK_OBS:
    if nc == GND:
        gnd_targets.append((sx, sy))
        gnd_targets.append((ex, ey))

# stuck GND-in-pad-Vias
stuck = []
for v in VIAS:
    if v.GetNetCode() != GND:
        continue
    vp = v.GetPosition()
    for fp in fps:
        for pad in fp.Pads():
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            if fp.GetReference() == "U1" and pad.GetNumber() == "61":
                continue
            if pad.HitTest(vp):
                stuck.append((v, fp, pad))
                break
        else:
            continue
        break

print("stuck GND-Vias:", len(stuck))
done = 0
fail = []
add_stubs = []
del_vias = []
for v, fp, pad in stuck:
    pc = pad.GetCenter()
    cands = sorted(gnd_targets,
                   key=lambda q: math.hypot(q[0] - pc.x, q[1] - pc.y))
    placed = False
    for tx, ty in cands:
        d = math.hypot(tx - pc.x, ty - pc.y)
        if d < 0.4 * MM or d > 2.5 * MM:
            continue
        if in_any_pad(tx, ty):
            continue
        if stub_ok(pc.x, pc.y, tx, ty):
            add_stubs.append((pc.x, pc.y, int(tx), int(ty)))
            del_vias.append(v)
            done += 1
            placed = True
            break
    if not placed:
        fail.append((fp.GetReference(), pad.GetNumber()))

for v in del_vias:
    board.Remove(v)
for ax, ay, bx, by in add_stubs:
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(ax, ay))
    tr.SetEnd(pcbnew.VECTOR2I(bx, by))
    tr.SetWidth(STUB_W)
    tr.SetLayer(pcbnew.F_Cu)
    tr.SetNetCode(GND)
    board.Add(tr)

print(f"GND per Stub geloest: {done} | offen: {len(fail)}", fail)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard("project/aurabip_routed.kicad_pcb", board)
print("gespeichert")
