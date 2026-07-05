"""ASCII-Dump der Hindernis-Karte um einen Punkt. Usage: maze_debug.py"""
import importlib.util
import os
import sys

WD = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["maze_debug", os.path.join(WD, "../project/aurabip_routed.kicad_pcb"),
            os.path.join(WD, "_dbg_out.kicad_pcb")]

# maze_router laden, aber Hauptteil abklemmen: wir patchen PAIRS leer,
# indem wir das Modul bis vor "PAIRS =" ausfuehren
src = open(os.path.join(WD, "maze_router.py"), encoding="utf-8").read()
head = src[:src.index("PAIRS = [")]
ns = {"__file__": os.path.join(WD, "maze_router.py")}
exec(compile(head, "maze_router_head", "exec"), ns)

F, B = ns["F"], ns["B"]
NX, RES = ns["NX"], ns["RES"]
pad_of = ns["pad_of"]
build_maps = ns["build_maps"]

import os as _os
pa = pad_of(_os.environ.get("DBG_REF","U1"), _os.environ.get("DBG_PAD","34"))
net = pa.GetNetCode()
blocked, via_ok = build_maps(net)
pp = pa.GetPosition(); cx, cy = ns["T"](pp.x), ns["T"](pp.y)
ix0, iy0 = int(cx / RES), int(cy / RES)
R = 22
for layer, name in ((F, "F.Cu"), (B, "B.Cu")):
    print(f"--- {name} um U1.34 ({cx},{cy}), {2*R+1}x{2*R+1} Zellen a {RES}mm ---")
    arr = blocked[layer]
    for iy in range(iy0 - R, iy0 + R + 1):
        row = ""
        for ix in range(ix0 - R, ix0 + R + 1):
            if ix == ix0 and iy == iy0:
                row += "S"
            elif arr[iy * NX + ix]:
                row += "#"
            else:
                row += "."
        print(row)
