"""AuraBip Maze-Router — A*-Wellenrouter auf 0.2-mm-Raster, 2 Lagen + Vias.

Findet garantiert jeden auf dem Raster existierenden Pfad (im Gegensatz
zu Kandidaten-Routern). Hindernis-Modell: Pad-Rechtecke, Tracks, Vias,
Boardrand, Fraes-Graben der Sensor-Insel, Antennen-Keepouts.

Usage: maze_router.py <in.kicad_pcb> <out.kicad_pcb>
"""
import heapq
import math
import os
import sys

import pcbnew

WD = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = sys.argv[1], sys.argv[2]
MM, T = pcbnew.FromMM, pcbnew.ToMM

RES = 0.1                 # Rasterweite mm (0.2 quantisiert 0.4er-Gassen weg!)
BW, BH = 52.0, 52.0
NX, NY = int(BW / RES) + 1, int(BH / RES) + 1
NARROW = "--narrow" in sys.argv
TW = 0.127 if NARROW else 0.15      # 5 mil fuer Engstellen (JLC-ok)
TRACK_W = MM(TW)
INFL = TW / 2 + 0.10          # Halbbreite + Clearance (DRC prueft nach)
VIA_OD, VIA_DR = 0.5, 0.3
VIA_COST = 14                 # Rasterschritte "Strafe" pro Via

log = open(os.path.join(WD, "maze.log"), "w")


def L(*a):
    log.write(" ".join(str(x) for x in a) + "\n")
    log.flush()


b = pcbnew.LoadBoard(SRC)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
LAYERS = (F, B)
_fps = {fp.GetReference(): fp for fp in b.GetFootprints()}


def pad_of(ref, num):
    for p in _fps[ref].Pads():
        if p.GetNumber() == num:
            return p
    raise ValueError(f"{ref}.{num}")


# ---------------- Hindernis-Karten ----------------
# blocked[layer] = bytearray, 1 = fuer fremde Netze gesperrt
# net_of Karten brauchen wir nicht: wir bauen die Karte PRO NETZ neu aus
# vorgerechneten Listen (schnell genug fuer ~18 Netze).

pads_all = []   # (x1,y1,x2,y2, net, onF, onB)
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        pads_all.append((T(bb.GetLeft()), T(bb.GetTop()),
                         T(bb.GetRight()), T(bb.GetBottom()),
                         p.GetNetCode(),
                         p.IsOnLayer(F), p.IsOnLayer(B)))

segs_all = {F: [], B: []}   # (x1,y1,x2,y2,halfw,net)
vias_all = []               # (x,y,net)
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        vias_all.append((T(pos.x), T(pos.y), t.GetNetCode()))
    elif t.GetLayer() in LAYERS:
        s, e = t.GetStart(), t.GetEnd()
        segs_all[t.GetLayer()].append(
            (T(s.x), T(s.y), T(e.x), T(e.y),
             T(t.GetWidth()) / 2.0, t.GetNetCode()))

# --rip=NET1,NET2: diese Netze vor dem Routen komplett entfernen
# (Rip-up & Reroute bei Reihenfolge-Konflikten)
_rip = set()
for a in sys.argv:
    if a.startswith("--rip="):
        _rip = set(a[6:].split(","))
if _rip:
    _names = {}
    doomed = []
    for t in b.GetTracks():
        if t.GetNetname() in _rip:
            doomed.append(t)
    for t in doomed:
        b.Remove(t)
    L("Rip-up:", len(doomed), "Elemente aus", ",".join(sorted(_rip)))
    # Listen neu aufbauen
    segs_all = {F: [], B: []}
    vias_all = []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            vias_all.append((T(pos.x), T(pos.y), t.GetNetCode()))
        elif t.GetLayer() in LAYERS:
            s_, e_ = t.GetStart(), t.GetEnd()
            segs_all[t.GetLayer()].append(
                (T(s_.x), T(s_.y), T(e_.x), T(e_.y),
                 T(t.GetWidth()) / 2.0, t.GetNetCode()))

# statische Sperrzonen (beide Lagen): Rand, Keepouts, Moat
STATIC = bytearray(NX * NY)


def idx(ix, iy):
    return iy * NX + ix


def block_rect(arr, x1, y1, x2, y2):
    # Zellmittelpunkt-Sampling: Zelle gesperrt, wenn ihr Zentrum im
    # Rechteck liegt (knappe Rasterung — grosszuegiges Runden frisst
    # sonst die schmalen Gassen zwischen Pad-Reihen)
    ix1 = max(0, int(math.ceil(x1 / RES - 1e-9)))
    iy1 = max(0, int(math.ceil(y1 / RES - 1e-9)))
    ix2 = min(NX - 1, int(math.floor(x2 / RES + 1e-9)))
    iy2 = min(NY - 1, int(math.floor(y2 / RES + 1e-9)))
    for iy in range(iy1, iy2 + 1):
        base = iy * NX
        for ix in range(ix1, ix2 + 1):
            arr[base + ix] = 1


# Boardrand
m = 0.35
block_rect(STATIC, 0, 0, BW, m)
block_rect(STATIC, 0, BH - m, BW, BH)
block_rect(STATIC, 0, 0, m, BH)
block_rect(STATIC, BW - m, 0, BW, BH)
# Antennen-Keepouts (Tracks verboten)
block_rect(STATIC, 0, 17.7, 6.0, 34.3)
block_rect(STATIC, 15.6, 0, 20.4, 8.4)
# Sensor-Insel-Graben (C-Form, 1mm Schlitz + 0.25 Rand)
for (x1, y1, x2, y2) in [(43.5, 18.6, 50.0, 19.6),
                          (43.5, 27.0, 50.0, 28.0),
                          (43.5, 18.6, 44.5, 28.0)]:
    block_rect(STATIC, x1 - 0.25, y1 - 0.25, x2 + 0.25, y2 + 0.25)


def build_maps(net):
    """Gesperrt-Karten je Lage + Via-Karte fuer dieses Netz."""
    blocked = {F: bytearray(STATIC), B: bytearray(STATIC)}
    via_ok = bytearray(NX * NY)  # 0 = ok (invertiert am Ende)

    for (x1, y1, x2, y2, n, onF, onB) in pads_all:
        if n == net and n != 0:
            continue
        # netzlose Pads (NPTH/Schirm): Bohr-Clearance 0.2 einrechnen
        extra = 0.12 if n == 0 else 0.0
        for layer, on in ((F, onF), (B, onB)):
            if on:
                block_rect(blocked[layer], x1 - INFL - extra, y1 - INFL - extra,
                           x2 + INFL + extra, y2 + INFL + extra)
        # Via-Verbot um jedes fremde Pad (Via-Radius + Clearance)
        vi = VIA_OD / 2 + 0.12
        block_rect(via_ok, x1 - vi, y1 - vi, x2 + vi, y2 + vi)

    for layer in LAYERS:
        for (x1, y1, x2, y2, hw, n) in segs_all[layer]:
            if n == net:
                continue
            g = hw + INFL
            # Segment als Kette von Rechtecken rastern
            length = math.hypot(x2 - x1, y2 - y1)
            steps = max(1, int(length / RES))
            for k in range(steps + 1):
                px = x1 + (x2 - x1) * k / steps
                py = y1 + (y2 - y1) * k / steps
                block_rect(blocked[layer], px - g, py - g, px + g, py + g)

    for (x, y, n) in vias_all:
        r = VIA_OD / 2
        if n != net:
            g = r + INFL + (0.02 if "--ortho" in sys.argv else 0.08)
            for layer in LAYERS:
                block_rect(blocked[layer], x - g, y - g, x + g, y + g)
        # Bohrabstand fuer neue Vias (auch gleiche Netze!)
        hb = VIA_DR + 0.3
        block_rect(via_ok, x - hb, y - hb, x + hb, y + hb)

    # Fremd-Tracks blockieren Vias ebenfalls
    for layer in LAYERS:
        for (x1, y1, x2, y2, hw, n) in segs_all[layer]:
            if n == net:
                continue
            g = hw + VIA_OD / 2 + 0.12
            length = math.hypot(x2 - x1, y2 - y1)
            steps = max(1, int(length / RES))
            for k in range(steps + 1):
                px = x1 + (x2 - x1) * k / steps
                py = y1 + (y2 - y1) * k / steps
                block_rect(via_ok, px - g, py - g, px + g, py + g)

    return blocked, via_ok


def pad_cells(pad):
    """Rasterzellen im Pad (leicht geschrumpft)."""
    bb = pad.GetBoundingBox()
    x1, y1 = T(bb.GetLeft()) + 0.02, T(bb.GetTop()) + 0.02
    x2, y2 = T(bb.GetRight()) - 0.02, T(bb.GetBottom()) - 0.02
    out = []
    ix1, iy1 = int(math.ceil(x1 / RES)), int(math.ceil(y1 / RES))
    ix2, iy2 = int(x2 / RES), int(y2 / RES)
    for iy in range(iy1, iy2 + 1):
        for ix in range(ix1, ix2 + 1):
            if 0 <= ix < NX and 0 <= iy < NY:
                out.append((ix, iy))
    if not out:  # sehr kleines Pad: Mittelpunkt
        p = pad.GetPosition()
        out = [(int(round(T(p.x) / RES)), int(round(T(p.y) / RES)))]
    return out


def astar(net, src_pad, dst_pad):
    blocked, via_ok = build_maps(net)
    la = F if src_pad.IsOnLayer(F) else B
    lb = F if dst_pad.IsOnLayer(F) else B
    li = {F: 0, B: 1}
    src = [(ix, iy, li[la]) for (ix, iy) in pad_cells(src_pad)]
    dst = set((ix, iy, li[lb]) for (ix, iy) in pad_cells(dst_pad))
    # Eigene Pad-Zellen sind IMMER begehbar (Nachbar-Inflation kann
    # sie sonst zudecken — z.B. 0.4/0.8-Pitch-Sensoren). Zusaetzlich:
    # Via-in-Pad am Start/Ziel erlauben — Rettungsanker, wenn die
    # Lage vollstaendig zugebaut ist (Modul-Pads: 0.5er-Via passt).
    def via_fit_exact(x_mm, y_mm):
        # praezise Pruefung fuer Rettungs-Vias in Pad-Zellen:
        # Fremd-Tracks beider Lagen, alle Via-Bohrungen, Fremd-Pads
        vr = VIA_OD / 2
        for layer in LAYERS:
            for (x1, y1, x2, y2, hw, n) in segs_all[layer]:
                if n == net:
                    continue
                dx, dy = x2 - x1, y2 - y1
                ll = dx * dx + dy * dy
                t_ = 0 if ll == 0 else max(0.0, min(1.0,
                    ((x_mm - x1) * dx + (y_mm - y1) * dy) / ll))
                d = math.hypot(x_mm - (x1 + t_ * dx), y_mm - (y1 + t_ * dy))
                if d < vr + hw + 0.09:
                    return False
        for (vx, vy, n) in vias_all:
            if math.hypot(x_mm - vx, y_mm - vy) < VIA_DR + 0.28:
                return False
        for (x1, y1, x2, y2, n, onF, onB) in pads_all:
            if n == net and n != 0:
                continue
            if x1 - vr - 0.09 < x_mm < x2 + vr + 0.09 and                     y1 - vr - 0.09 < y_mm < y2 + vr + 0.09:
                return False
        return True

    for (ix, iy, l) in list(src) + list(dst):
        blocked[F if l == 0 else B][iy * NX + ix] = 0
        if via_fit_exact(ix * RES, iy * RES):
            via_ok[iy * NX + ix] = 0
    if not src or not dst:
        return None
    dp = dst_pad.GetPosition()
    tx, ty = T(dp.x) / RES, T(dp.y) / RES

    NL = NX * NY
    best = {}
    prev = {}
    pq = []
    for (ix, iy, l) in src:
        n = l * NL + iy * NX + ix
        best[n] = 0.0
        heapq.heappush(pq, (0.0, 0.0, n))

    layer_arr = [blocked[F], blocked[B]]
    if "--ortho" in sys.argv:   # keine Diagonalen -> keine Eckenschnitte
        DIRS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0))
    else:
        DIRS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42))
    goal = None
    while pq:
        f, g0, n = heapq.heappop(pq)
        if g0 > best.get(n, 1e18) + 1e-9:
            continue
        l, rest = divmod(n, NL)
        iy, ix = divmod(rest, NX)
        if (ix, iy, l) in dst:
            goal = n
            break
        arr = layer_arr[l]
        for (dx, dy, c) in DIRS:
            jx, jy = ix + dx, iy + dy
            if not (0 <= jx < NX and 0 <= jy < NY):
                continue
            if arr[jy * NX + jx]:
                continue
            if dx and dy:  # Diagonale: Eckdurchschlupf verbieten
                if arr[iy * NX + jx] or arr[jy * NX + ix]:
                    continue
            m_ = l * NL + jy * NX + jx
            nd = g0 + c
            if nd < best.get(m_, 1e18):
                best[m_] = nd
                prev[m_] = n
                h = math.hypot(jx - tx, jy - ty) * 0.99
                heapq.heappush(pq, (nd + h, nd, m_))
        # Via-Wechsel
        if not via_ok[iy * NX + ix]:
            ol = 1 - l
            if not layer_arr[ol][iy * NX + ix]:
                m_ = ol * NL + iy * NX + ix
                nd = g0 + VIA_COST
                if nd < best.get(m_, 1e18):
                    best[m_] = nd
                    prev[m_] = n
                    h = math.hypot(ix - tx, iy - ty) * 0.99
                    heapq.heappush(pq, (nd + h, nd, m_))
    if goal is None:
        # Diagnose: wie weit kam die Welle?
        src_blocked = sum(1 for (ix, iy, l) in src
                          if layer_arr[l][iy * NX + ix])
        dst_blocked = sum(1 for (ix, iy, l) in dst
                          if layer_arr[l][iy * NX + ix])
        onB = sum(1 for n in best if n >= NL)
        via_free_src = sum(1 for (ix, iy, l) in src
                           if not via_ok[iy * NX + ix])
        L(f"    Diagnose: besucht={len(best)} (davon B: {onB}),"
          f" srcZellen={len(src)} (blockiert {src_blocked},"
          f" via-frei {via_free_src}), dstZellen={len(dst)}"
          f" (blockiert {dst_blocked})")
        return None
    # Pfad rekonstruieren
    path = []
    n = goal
    while True:
        l, rest = divmod(n, NL)
        iy, ix = divmod(rest, NX)
        path.append((ix, iy, l))
        if n not in prev:
            break
        n = prev[n]
    path.reverse()
    return path


def emit(path, net, src_pad, dst_pad):
    """Pfad -> Tracks/Vias; kollineare Läufe zusammenfassen."""
    def pt(ix, iy):
        return pcbnew.VECTOR2I(MM(ix * RES), MM(iy * RES))

    LMAP = (F, B)
    # Anker: exakte Pad-Zentren an den Enden anspleissen
    segpts = [(src_pad.GetPosition(), path[0][2])]
    i = 0
    while i < len(path) - 1:
        j = i + 1
        if path[j][2] != path[i][2]:      # Via
            segpts.append((pt(path[i][0], path[i][1]), path[i][2]))
            segpts.append(("VIA", None))
            segpts.append((pt(path[j][0], path[j][1]), path[j][2]))
            i = j
            continue
        dx = path[j][0] - path[i][0]
        dy = path[j][1] - path[i][1]
        while j + 1 < len(path) and path[j + 1][2] == path[i][2] and \
                (path[j + 1][0] - path[j][0], path[j + 1][1] - path[j][1]) == (dx, dy):
            j += 1
        segpts.append((pt(path[j][0], path[j][1]), path[j][2]))
        i = j
    segpts.append((dst_pad.GetPosition(), path[-1][2]))

    last = None
    nvias = 0
    for item in segpts:
        if isinstance(item[0], str):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(last[0])
            v.SetWidth(MM(VIA_OD))
            v.SetDrill(MM(VIA_DR))
            v.SetNet(net)
            b.Add(v)
            vias_all.append((T(last[0].x), T(last[0].y), net.GetNetCode()))
            nvias += 1
            continue
        if last is not None and last[1] == item[1] and (last[0].x != item[0].x or last[0].y != item[0].y):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(last[0])
            t.SetEnd(item[0])
            t.SetWidth(TRACK_W)
            t.SetLayer(LMAP[item[1]] if item[1] is not None else F)
            t.SetNet(net)
            b.Add(t)
            segs_all[LMAP[item[1]]].append(
                (T(last[0].x), T(last[0].y), T(item[0].x), T(item[0].y),
                 T(TRACK_W) / 2.0, net.GetNetCode()))
        last = item
    return nvias


PAIRS = [
    ("U4", "2", "U2", "2"),      # SCL lokal auf der Insel
    ("U2", "2", "R4", "2"),      # SCL ueber die Bruecke zum Bus
    ("U1", "12", "R3", "2"),     # SDA Hauptbus
    ("U1", "4", "SW3", "1"),     # BTN_BOOT
    ("SW2", "1", "R5", "2"),     # ESP_EN
    ("U1", "10", "U6", "1"),     # I2S_DOUT
    ("U1", "11", "R8", "2"),     # AMP_SD
    ("U1", "23", "U9", "6"),     # USB_DN
    ("U1", "24", "U9", "4"),     # USB_DP
    ("U1", "7", "U10", "13"),    # LORA_DIO1
    ("U1", "17", "U10", "16"),   # SPI2_MISO
    ("U1", "25", "U10", "19"),   # LORA_NSS
    ("U1", "20", "U10", "7"),    # LORA_TXEN
    ("U1", "33", "U10", "6"),    # LORA_RXEN
    ("U1", "34", "TP1", "1"),
    ("U1", "36", "TP2", "1"),
    ("U1", "37", "TP3", "1"),
    ("U1", "38", "TP4", "1"),
]

# --pairs U4.2:U2.2,U2.2:R4.2 ueberschreibt die Standardliste
for a in sys.argv:
    if a.startswith("--pairs="):
        PAIRS = []
        for item in a[8:].split(","):
            lhs, rhs = item.split(":")
            ra, na = lhs.rsplit(".", 1)
            rb, nb = rhs.rsplit(".", 1)
            PAIRS.append((ra, na, rb, nb))


ok = 0
for (ra, na, rb, nb) in PAIRS:
    try:
        pa, pb = pad_of(ra, na), pad_of(rb, nb)
        if pa.GetNetCode() != pb.GetNetCode():
            L(f"SKIP {ra}.{na}->{rb}.{nb}: Netz-Mismatch!")
            continue
        path = astar(pa.GetNetCode(), pa, pb)
        if path is None:
            L(f"FAIL {ra}.{na}->{rb}.{nb} [{pa.GetNetname()}]")
            continue
        nv = emit(path, pa.GetNet(), pa, pb)
        ok += 1
        L(f"OK  {ra}.{na}->{rb}.{nb} [{pa.GetNetname()}] {len(path)} Zellen, {nv} Vias")
    except Exception:
        import traceback as tb
        L(f"CRASH {ra}.{na}->{rb}.{nb}:")
        L(tb.format_exc())

# GND-Nachzuegler: Via in U2.3 (Insel) — im --pairs-Modus ueberspringen
try:
    if any(a.startswith("--pairs=") for a in sys.argv):
        raise StopIteration("uebersprungen")
    pad = pad_of("U2", "3")
    pos = pad.GetPosition()
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pos)
    v.SetWidth(MM(VIA_OD))
    v.SetDrill(MM(VIA_DR))
    v.SetNet(pad.GetNet())
    b.Add(v)
    L("OK  Via-in-Pad U2.3 [GND]")
    ok += 1
except Exception as e:
    L("FAIL U2.3:", e)

L(f"=== {ok}/{len(PAIRS) + 1} geschafft ===")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(OUT)
print(f"maze_router: {ok}/{len(PAIRS) + 1}")
