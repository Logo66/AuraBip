# -*- coding: utf-8 -*-
"""Lokales Rip-and-Reroute mit dem bewaehrten A*-Wellenrouter (IN-PLACE).

Kernidee (WindBuddy 0/0):
  * Nur LOKAL rippen: die harte Via + ihre lokalen Tracks UND die lokalen
    Segmente der Flanker-Netze (Fenster RIPWIN um die Via) werden entfernt.
  * Reroute mit dem GLEICHEN A* wie maze_router (0.1-mm-Raster, 2 Lagen,
    Vias, echte Clearance) — aber zwischen KOORDINATEN-Terminals statt Pads.
  * Reihenfolge: zuerst das harte Netz (dessen Via faellt off-pad in die
    freigeraeumte Luecke), danach die Flanker rundherum.
  * Terminals = Enden der geripten Segmente, die noch ueberlebendes
    Kupfer des Netzes beruehren  ->  Topologie bleibt exakt erhalten.
Endkontrolle: echte kicad-cli DRC im Aufrufer.

local_maze.py X Y --padlayer F|B --rip NET,NET [--ripwin 1.7] [--tw 0.15]
"""
import sys, math, heapq, pcbnew

MM = pcbnew.FromMM
T = pcbnew.ToMM
NM = 1_000_000
PATH = r"project/aurabip_routed.kicad_pcb"

X, Y = float(sys.argv[1]), float(sys.argv[2])
PADLAYER = pcbnew.F_Cu
RIPNETS = set(); RIPWIN = 1.7; TW = 0.15; HARDWIN = 0.6
for i, a in enumerate(sys.argv):
    if a == "--padlayer": PADLAYER = pcbnew.F_Cu if sys.argv[i+1] == "F" else pcbnew.B_Cu
    if a == "--rip": RIPNETS = set(sys.argv[i+1].split(","))
    if a == "--ripwin": RIPWIN = float(sys.argv[i+1])
    if a == "--hardwin": HARDWIN = float(sys.argv[i+1])
    if a == "--tw": TW = float(sys.argv[i+1])

RES = 0.1
BW, BH = 52.0, 52.0
NX, NY = int(BW/RES)+1, int(BH/RES)+1
TRACK_W = MM(TW)
INFL = TW/2 + 0.10
VIA_OD, VIA_DR = 0.5, 0.3
VIA_COST = 14

b = pcbnew.LoadBoard(PATH)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
LAYERS = (F, B)
li = {F: 0, B: 1}
LMAP = (F, B)


def seg_pt(ax, ay, bx, by, px, py):
    dx, dy = bx-ax, by-ay
    if dx == 0 and dy == 0: return math.hypot(px-ax, py-ay)
    t = max(0, min(1, ((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-(ax+t*dx), py-(ay+t*dy))


# --- Zielvia + Pad ---
best, bd = None, 1e18
for v in b.GetTracks():
    if isinstance(v, pcbnew.PCB_VIA):
        p = v.GetPosition(); d = math.hypot(T(p.x)-X, T(p.y)-Y)
        if d < bd: bd, best = d, v
hardvia = best
O = hardvia.GetPosition()
Ox, Oy = T(O.x), T(O.y)
mynet = hardvia.GetNetCode()
mynetname = hardvia.GetNetname()
pad = None
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and p.HitTest(O):
            pad = p; ref = "%s.%s" % (fp.GetReference(), p.GetNumber())
print("harte Via %s net=%s @(%.2f,%.2f) padlayer=%s" % (
    ref, mynetname, Ox, Oy, "F" if PADLAYER == F else "B"))

# Ist das harte Netz ein Flaechen-/Plane-Netz (hat gefuellte Zone)? Dann darf
# nur DIE harte Via weg (nicht anderes GND-Kupfer); Wiederanbindung = Via off-
# pad + F-Stub (Durchkontaktierung trifft die In-Lagen-GND-Plane).
PLANE_HARD = any(z.GetNetCode() == mynet for z in b.Zones())
RIP_TRACK_NETS = set(RIPNETS)   # Flanker per Naehe (geclippt) rippen
if not PLANE_HARD:
    RIP_TRACK_NETS |= {mynetname}   # Signal-Hartnetz ebenso lokal auftrennen
print("PLANE_HARD=%s  rip=%s" % (PLANE_HARD, ",".join(sorted(RIP_TRACK_NETS))))


def touches_surviving(px, py, netname, exclude):
    """Beruehrt Punkt ueberlebendes Kupfer des Netzes (Pad/Via/Track-Ende)?"""
    P = pcbnew.VECTOR2I(int(px), int(py))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == netname and p.HitTest(P): return True
    for t in b.GetTracks():
        if id(t) in exclude: continue
        if t.GetNetname() != netname: continue
        if isinstance(t, pcbnew.PCB_VIA):
            if math.hypot(t.GetPosition().x-px, t.GetPosition().y-py) < MM(0.05): return True
        else:
            for e in (t.GetStart(), t.GetEnd()):
                if math.hypot(e.x-px, e.y-py) < MM(0.02): return True
    return False


# --- LOKAL rippen ---
RW = MM(RIPWIN)
RWmm = RIPWIN
HEPS = MM(0.02)
net_terminals = {}   # netname -> list of (x_nm, y_nm, layer)
net_width = {}


def circ_interval(ax, ay, bx, by, rad):
    """t-Intervall [t0,t1] in [0,1], wo Segment naeher als rad an O ist."""
    dx, dy = bx-ax, by-ay
    A = dx*dx+dy*dy
    if A == 0:
        return (0.0, 1.0) if math.hypot(ax-O.x, ay-O.y) < rad else None
    Bc = 2*((ax-O.x)*dx+(ay-O.y)*dy)
    C = (ax-O.x)**2+(ay-O.y)**2-rad*rad
    disc = Bc*Bc-4*A*C
    if disc <= 0: return None
    sq = math.sqrt(disc)
    r0 = (-Bc-sq)/(2*A); r1 = (-Bc+sq)/(2*A)
    lo, hi = max(0.0, min(r0, r1)), min(1.0, max(r0, r1))
    if lo >= hi: return None
    return (lo, hi)


doomed = [hardvia]           # ganz entfernen
new_stubs = []               # (sx,sy,ex,ey,w,layer,net) ueberlebende Aussenstuecke
clip_terms = {}              # net -> list of (x,y,layer) Schnittpunkte
bcheck = []                  # (x,y,layer,net) Endpunkte, per touches_surviving pruefen

for t in list(b.GetTracks()):
    if isinstance(t, pcbnew.PCB_VIA):
        if t is hardvia: continue
        pp = t.GetPosition()
        if t.GetNetname() in RIP_TRACK_NETS and math.hypot(pp.x-O.x, pp.y-O.y) < RW:
            doomed.append(t)
        continue
    nm = t.GetNetname()
    s, e = t.GetStart(), t.GetEnd()
    if nm in RIP_TRACK_NETS:
        rad = MM(HARDWIN) if nm == mynetname else RW
        iv = circ_interval(s.x, s.y, e.x, e.y, rad)
        if iv is None: continue
        t0, t1 = iv
        w = t.GetWidth(); ly = t.GetLayer()
        net_width[nm] = max(net_width.get(nm, TRACK_W), w)
        dx, dy = e.x-s.x, e.y-s.y
        p0 = (int(s.x+dx*t0), int(s.y+dy*t0))
        p1 = (int(s.x+dx*t1), int(s.y+dy*t1))
        clipped = False
        if t0 > 1e-6:                 # Aussenstueck s..p0 behalten
            new_stubs.append((s.x, s.y, p0[0], p0[1], w, ly, nm))
            clip_terms.setdefault(nm, []).append((p0[0], p0[1], ly)); clipped = True
        if t1 < 1-1e-6:               # Aussenstueck p1..e behalten
            new_stubs.append((p1[0], p1[1], e.x, e.y, w, ly, nm))
            clip_terms.setdefault(nm, []).append((p1[0], p1[1], ly)); clipped = True
        if not clipped:               # ganz innen: Endpunkte spaeter pruefen
            bcheck.append((s.x, s.y, ly, nm)); bcheck.append((e.x, e.y, ly, nm))
        doomed.append(t)

doomset = set(id(t) for t in doomed)
# Terminals: (a) Schnittpunkte an der Fenstergrenze (Aussenstuecke) je Flanker
for nm, pts in clip_terms.items():
    net_terminals.setdefault(nm, [])
    for (x, y, ly) in pts:
        if all(math.hypot(x-q[0], y-q[1]) > MM(0.05) for q in net_terminals[nm]):
            net_terminals[nm].append((x, y, ly))
# (b) markierte Endpunkte, die ueberlebendes Kupfer beruehren
for (x, y, ly, nm) in bcheck:
    if touches_surviving(x, y, nm, doomset):
        net_terminals.setdefault(nm, [])
        if all(math.hypot(x-q[0], y-q[1]) > MM(0.05) for q in net_terminals[nm]):
            net_terminals[nm].append((x, y, ly))

# Hartes Netz (nur Signal): Terminals INNERHALB des Pads verwerfen (die
# wuerden nur wieder in-pad verbunden); Pad selbst als einziges In-Pad-
# Terminal setzen -> A* muss off-pad zu den externen Terminals routen.
pc = pad.GetPosition()
pbb0 = pad.GetBoundingBox()
if not PLANE_HARD:
    kept = []
    for (x, y, l) in net_terminals.get(mynetname, []):
        inside = (pbb0.GetLeft() < x < pbb0.GetRight() and
                  pbb0.GetTop() < y < pbb0.GetBottom())
        if not inside:
            kept.append((x, y, l))
    kept.append((pc.x, pc.y, PADLAYER))
    net_terminals[mynetname] = kept
    net_width.setdefault(mynetname, TRACK_W)

for t in doomed:
    b.Remove(t)
# ueberlebende Aussenstuecke der geclippten Flanker wieder einsetzen
for (sx, sy, ex, ey, w, ly, nm) in new_stubs:
    if math.hypot(ex-sx, ey-sy) < MM(0.01): continue
    tr = pcbnew.PCB_TRACK(b)
    tr.SetStart(pcbnew.VECTOR2I(int(sx), int(sy)))
    tr.SetEnd(pcbnew.VECTOR2I(int(ex), int(ey)))
    tr.SetWidth(w); tr.SetLayer(ly)
    tr.SetNet(b.GetNetsByName()[nm]); b.Add(tr)
print("lokal gerippt: %d Elemente (+harte Via), %d Aussenstuecke behalten" % (
    len(doomed), len(new_stubs)))
for nm, terms in net_terminals.items():
    print("  %s: %d Terminals %s" % (nm, len(terms),
          " ".join("(%.2f,%.2f,%s)" % (T(x), T(y), "F" if l == F else "B") for x, y, l in terms)))

# ================= A* (portiert aus maze_router) =================
STATIC = bytearray(NX*NY)


def idx(ix, iy): return iy*NX+ix


def block_rect(arr, x1, y1, x2, y2):
    ix1 = max(0, int(math.ceil(x1/RES-1e-9))); iy1 = max(0, int(math.ceil(y1/RES-1e-9)))
    ix2 = min(NX-1, int(math.floor(x2/RES+1e-9))); iy2 = min(NY-1, int(math.floor(y2/RES+1e-9)))
    for iy in range(iy1, iy2+1):
        base = iy*NX
        for ix in range(ix1, ix2+1):
            arr[base+ix] = 1


m = 0.35
block_rect(STATIC, 0, 0, BW, m); block_rect(STATIC, 0, BH-m, BW, BH)
block_rect(STATIC, 0, 0, m, BH); block_rect(STATIC, BW-m, 0, BW, BH)
block_rect(STATIC, 0, 17.7, 6.0, 34.3); block_rect(STATIC, 15.6, 0, 20.4, 8.4)
for (x1, y1, x2, y2) in [(43.5, 18.6, 50.0, 19.6), (43.5, 27.0, 50.0, 28.0), (43.5, 18.6, 44.5, 28.0)]:
    block_rect(STATIC, x1-0.25, y1-0.25, x2+0.25, y2+0.25)


def snapshot():
    pads_all = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads_all.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom()),
                             p.GetNetCode(), p.IsOnLayer(F), p.IsOnLayer(B)))
    segs = {F: [], B: []}; vias = []
    for t in b.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            pp = t.GetPosition(); vias.append((T(pp.x), T(pp.y), t.GetNetCode()))
        elif t.GetLayer() in LAYERS:
            s, e = t.GetStart(), t.GetEnd()
            segs[t.GetLayer()].append((T(s.x), T(s.y), T(e.x), T(e.y), T(t.GetWidth())/2.0, t.GetNetCode()))
    return pads_all, segs, vias


NO_VIA_RECT = None   # (x1,y1,x2,y2) mm: hier keine neue Via (Pad-Schutz)


def build_maps(net, pads_all, segs_all, vias_all):
    blocked = {F: bytearray(STATIC), B: bytearray(STATIC)}
    via_ok = bytearray(NX*NY)
    for (x1, y1, x2, y2, n, onF, onB) in pads_all:
        if n == net and n != 0: continue
        extra = 0.12 if n == 0 else 0.0
        for layer, on in ((F, onF), (B, onB)):
            if on:
                block_rect(blocked[layer], x1-INFL-extra, y1-INFL-extra, x2+INFL+extra, y2+INFL+extra)
        vi = VIA_OD/2 + 0.12
        block_rect(via_ok, x1-vi, y1-vi, x2+vi, y2+vi)
    for layer in LAYERS:
        for (x1, y1, x2, y2, hw, n) in segs_all[layer]:
            if n == net: continue
            g = hw+INFL
            length = math.hypot(x2-x1, y2-y1); steps = max(1, int(length/RES))
            for k in range(steps+1):
                px = x1+(x2-x1)*k/steps; py = y1+(y2-y1)*k/steps
                block_rect(blocked[layer], px-g, py-g, px+g, py+g)
    for (x, y, n) in vias_all:
        r = VIA_OD/2
        if n != net:
            g = r+INFL+0.08
            for layer in LAYERS:
                block_rect(blocked[layer], x-g, y-g, x+g, y+g)
        hb = VIA_DR+0.3
        block_rect(via_ok, x-hb, y-hb, x+hb, y+hb)
    if NO_VIA_RECT is not None:
        x1, y1, x2, y2 = NO_VIA_RECT
        block_rect(via_ok, x1, y1, x2, y2)
    for layer in LAYERS:
        for (x1, y1, x2, y2, hw, n) in segs_all[layer]:
            if n == net: continue
            g = hw+VIA_OD/2+0.12
            length = math.hypot(x2-x1, y2-y1); steps = max(1, int(length/RES))
            for k in range(steps+1):
                px = x1+(x2-x1)*k/steps; py = y1+(y2-y1)*k/steps
                block_rect(via_ok, px-g, py-g, px+g, py+g)
    return blocked, via_ok


def cell(x_nm, y_nm):
    return (int(round(T(x_nm)/RES)), int(round(T(y_nm)/RES)))


def astar(net, src_pt, dst_cells, pads_all, segs_all, vias_all, via_at_ends=True):
    blocked, via_ok = build_maps(net, pads_all, segs_all, vias_all)
    sx, sy = cell(src_pt[0], src_pt[1]); sl = li[src_pt[2]]
    # Start/Ziel-Zellen immer begehbar machen
    for (cx, cy, cl) in [(sx, sy, sl)] + list(dst_cells):
        blocked[F if cl == 0 else B][cy*NX+cx] = 0
        if via_at_ends:
            via_ok[cy*NX+cx] = 0
    dst = set(dst_cells)
    NL = NX*NY
    best = {}; prev = {}; pq = []
    sn = sl*NL+sy*NX+sx
    best[sn] = 0.0; heapq.heappush(pq, (0.0, 0.0, sn))
    # Heuristik-Ziel = erstes dst
    tx, ty = next(iter(dst))[0], next(iter(dst))[1]
    layer_arr = [blocked[F], blocked[B]]
    DIRS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42))
    goal = None
    while pq:
        f, g0, n = heapq.heappop(pq)
        if g0 > best.get(n, 1e18)+1e-9: continue
        l, rest = divmod(n, NL); iy, ix = divmod(rest, NX)
        if (ix, iy, l) in dst: goal = n; break
        arr = layer_arr[l]
        for (dx, dy, c) in DIRS:
            jx, jy = ix+dx, iy+dy
            if not (0 <= jx < NX and 0 <= jy < NY): continue
            if arr[jy*NX+jx]: continue
            if dx and dy and (arr[iy*NX+jx] or arr[jy*NX+ix]): continue
            mm = l*NL+jy*NX+jx; nd = g0+c
            if nd < best.get(mm, 1e18):
                best[mm] = nd; prev[mm] = n
                h = math.hypot(jx-tx, jy-ty)*0.99
                heapq.heappush(pq, (nd+h, nd, mm))
        if not via_ok[iy*NX+ix]:
            ol = 1-l
            if not layer_arr[ol][iy*NX+ix]:
                mm = ol*NL+iy*NX+ix; nd = g0+VIA_COST
                if nd < best.get(mm, 1e18):
                    best[mm] = nd; prev[mm] = n
                    h = math.hypot(ix-tx, iy-ty)*0.99
                    heapq.heappush(pq, (nd+h, nd, mm))
    if goal is None:
        return None
    path = []; n = goal
    while True:
        l, rest = divmod(n, NL); iy, ix = divmod(rest, NX)
        path.append((ix, iy, l))
        if n not in prev: break
        n = prev[n]
    path.reverse()
    return path


def emit(path, netcode, width, src_pt, dst_pt):
    def pt(ix, iy): return pcbnew.VECTOR2I(MM(ix*RES), MM(iy*RES))
    netobj = b.FindNet(netcode)
    segpts = [(pcbnew.VECTOR2I(int(src_pt[0]), int(src_pt[1])), path[0][2])]
    i = 0
    while i < len(path)-1:
        j = i+1
        if path[j][2] != path[i][2]:
            segpts.append((pt(path[i][0], path[i][1]), path[i][2]))
            segpts.append(("VIA", None))
            segpts.append((pt(path[j][0], path[j][1]), path[j][2]))
            i = j; continue
        dx = path[j][0]-path[i][0]; dy = path[j][1]-path[i][1]
        while j+1 < len(path) and path[j+1][2] == path[i][2] and \
                (path[j+1][0]-path[j][0], path[j+1][1]-path[j][1]) == (dx, dy):
            j += 1
        segpts.append((pt(path[j][0], path[j][1]), path[i][2])); i = j
    segpts.append((pcbnew.VECTOR2I(int(dst_pt[0]), int(dst_pt[1])), path[-1][2]))
    last = None
    for item in segpts:
        if isinstance(item[0], str):
            v = pcbnew.PCB_VIA(b); v.SetPosition(last[0])
            v.SetWidth(MM(VIA_OD)); v.SetDrill(MM(VIA_DR)); v.SetNet(netobj); b.Add(v)
            continue
        if last is not None and last[1] == item[1] and (last[0].x != item[0].x or last[0].y != item[0].y):
            tr = pcbnew.PCB_TRACK(b); tr.SetStart(last[0]); tr.SetEnd(item[0])
            tr.SetWidth(width); tr.SetLayer(LMAP[item[1]] if item[1] is not None else F)
            tr.SetNet(netobj); b.Add(tr)
        last = item


# ---- PLANE_HARD: Stitch-Via off-pad + F-Stub geometrisch platzieren ----
if PLANE_HARD:
    pads_all, segs_all, vias_all = snapshot()
    blocked, via_ok = build_maps(mynet, pads_all, segs_all, vias_all)
    bb = pad.GetBoundingBox()
    pl, pt_, pr, pbm = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
    pcx, pcy = T(pc.x), T(pc.y)
    VR = VIA_OD/2

    def fcell(x, y): return int(round(x/RES)), int(round(y/RES))

    # BFS auf der F-Lage (blocked[F]) vom Pad zur naechsten via-tauglichen,
    # off-pad Zelle. Pad-Zellen sind Startmenge (Eigen-Netz -> begehbar).
    from collections import deque
    Fb = blocked[F]
    pcell = fcell(pcx, pcy)
    start = []
    ixl, ixr = fcell(pl, pt_)[0], fcell(pr, pbm)[0]
    iyt, iyb = fcell(pl, pt_)[1], fcell(pr, pbm)[1]
    for iyy in range(min(iyt, iyb), max(iyt, iyb)+1):
        for ixx in range(min(ixl, ixr), max(ixl, ixr)+1):
            if 0 <= ixx < NX and 0 <= iyy < NY:
                start.append((ixx, iyy))
    if not start:
        start = [pcell]

    # Rechtecke ALLER Pads (auch Eigen-Netz) — eine Via darf in KEINEM Pad landen
    ALLPADR = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if fp.GetReference() == "U1" and p.GetNumber() == "61":
                continue
            bb2 = p.GetBoundingBox()
            ALLPADR.append((T(bb2.GetLeft()), T(bb2.GetTop()), T(bb2.GetRight()), T(bb2.GetBottom())))

    def offpad(gx, gy):
        for l2, t2, r2, b2 in ALLPADR:
            if l2-VR-0.02 < gx < r2+VR+0.02 and t2-VR-0.02 < gy < b2+VR+0.02:
                return False
        return True

    dist = {}
    prevc = {}
    dq = deque()
    for s in start:
        dist[s] = 0; dq.append(s)
    NB = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    goalc = None
    while dq:
        cx, cy = dq.popleft()
        gx, gy = cx*RES, cy*RES
        if offpad(gx, gy) and via_ok[cy*NX+cx] == 0 and math.hypot(gx-pcx, gy-pcy) >= 0.35:
            goalc = (cx, cy); break
        for dxx, dyy in NB:
            nxc, nyc = cx+dxx, cy+dyy
            if not (0 <= nxc < NX and 0 <= nyc < NY): continue
            if (nxc, nyc) in dist: continue
            if Fb[nyc*NX+nxc]: continue
            if dxx and dyy and (Fb[cy*NX+nxc] or Fb[nyc*NX+cx]): continue
            dist[(nxc, nyc)] = dist[(cx, cy)]+1
            prevc[(nxc, nyc)] = (cx, cy)
            dq.append((nxc, nyc))
    placed_stitch = None
    if goalc is not None:
        # Pfad rekonstruieren (Zellen -> mm), zu Polyline verdichten
        pathc = [goalc]
        while pathc[-1] in prevc:
            pathc.append(prevc[pathc[-1]])
        pathc.reverse()
        pts = [(pcx, pcy)] + [(c[0]*RES, c[1]*RES) for c in pathc]
        # kollineare verdichten
        sp = [pts[0]]
        for i in range(1, len(pts)-1):
            ax, ay = sp[-1]; bx, by = pts[i]; cx2, cy2 = pts[i+1]
            if (bx-ax)*(cy2-by) - (by-ay)*(cx2-bx) != 0:
                sp.append(pts[i])
        sp.append(pts[-1])
        gx, gy = pts[-1]
        placed_stitch = (gx, gy, sp)
    if not placed_stitch:
        print("BFS-erreichbare Zellen: %d, kein via-taugliches Ziel" % len(dist))
        print("KEIN Stitch-Via-Platz fuer %s" % mynetname); sys.exit(4)
    gx, gy, sp = placed_stitch
    netobj = b.FindNet(mynet)
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(gx), MM(gy)))
    v.SetWidth(MM(VIA_OD)); v.SetDrill(MM(VIA_DR)); v.SetNet(netobj); b.Add(v)
    for k in range(len(sp)-1):
        tr = pcbnew.PCB_TRACK(b)
        tr.SetStart(pcbnew.VECTOR2I(MM(sp[k][0]), MM(sp[k][1])))
        tr.SetEnd(pcbnew.VECTOR2I(MM(sp[k+1][0]), MM(sp[k+1][1])))
        tr.SetWidth(TRACK_W); tr.SetLayer(PADLAYER); tr.SetNet(netobj); b.Add(tr)
    print("Stitch-Via %s -> (%.3f,%.3f) off=%.3f Knick=%d" % (
        mynetname, gx, gy, math.hypot(gx-pcx, gy-pcy), len(sp)-2))

# ---- Reihenfolge: hartes Netz (Signal) zuerst, dann Flanker ----
order = ([] if PLANE_HARD else [mynetname]) + [n for n in sorted(RIPNETS) if n != mynetname]
failed = []
for nm in order:
    NO_VIA_RECT = None
    if nm == mynetname:
        NO_VIA_RECT = (T(pbb0.GetLeft())-VIA_OD/2, T(pbb0.GetTop())-VIA_OD/2,
                       T(pbb0.GetRight())+VIA_OD/2, T(pbb0.GetBottom())+VIA_OD/2)
    terms = net_terminals.get(nm, [])
    if len(terms) < 2:
        print("  %s: <2 Terminals, nichts zu verbinden" % nm); continue
    nc = b.GetNetsByName()[nm].GetNetCode()
    w = net_width.get(nm, TRACK_W)
    # NN-Reihenfolge der Terminals, sukzessive verbinden
    remaining = terms[:]
    connected = [remaining.pop(0)]
    while remaining:
        # naechstes Terminal zum bereits verbundenen Satz
        bi, bj, bd2 = 0, 0, 1e18
        for ri, rt in enumerate(remaining):
            for ct in connected:
                d = math.hypot(rt[0]-ct[0], rt[1]-ct[1])
                if d < bd2: bd2, bi, ct_sel = d, ri, ct
        src = remaining.pop(bi)
        # dst-Zellen = alle bereits verbundenen Terminals (deren Zelle auf ihrer Lage)
        dst_cells = [(cell(ct[0], ct[1])[0], cell(ct[0], ct[1])[1], li[ct[2]]) for ct in connected]
        pads_all, segs_all, vias_all = snapshot()
        path = astar(nc, src, dst_cells, pads_all, segs_all, vias_all,
                     via_at_ends=(nm != mynetname))
        if path is None:
            print("  FAIL %s Terminal (%.2f,%.2f)" % (nm, T(src[0]), T(src[1])))
            failed.append((nm, T(src[0]), T(src[1]))); connected.append(src); continue
        # dst-Punkt = das getroffene Terminal (letzte Pfadzelle -> naechstes connected)
        endcell = path[-1]
        dpt = min(connected, key=lambda ct: math.hypot(cell(ct[0], ct[1])[0]-endcell[0], cell(ct[0], ct[1])[1]-endcell[1]))
        emit(path, nc, w, src, (dpt[0], dpt[1]))
        connected.append(src)
        print("  OK %s (%.2f,%.2f) %d Zellen" % (nm, T(src[0]), T(src[1]), len(path)))

print("Reroute fertig, Fehler:", len(failed))
if failed:
    print("NICHT gespeichert (unvollstaendig)"); sys.exit(3)
if "--dry" in sys.argv:
    print("dry-run (nichts gespeichert)"); sys.exit(0)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PATH)
print("saved")
