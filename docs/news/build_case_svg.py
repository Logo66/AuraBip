# -*- coding: utf-8 -*-
"""Massstaebliche Explosions-Schnittzeichnung des Gehaeuses — generiert
DIREKT aus dem P-Parameterblock von hardware/fusion/aurabip_case.py
(eine Quelle der Wahrheit, keine Freihand-Proportionen).

Schnittebene: durch die Lautsprecherachse (x-Richtung), Explosion vertikal.
"""
import os
import re

D = os.path.dirname(os.path.abspath(__file__))
FUSION = os.path.join(D, "..", "..", "hardware", "fusion", "aurabip_case.py")

src = open(FUSION, encoding="utf-8").read()
m = re.search(r"^P = \{(.*?)^\}", src, re.S | re.M)
ns = {}
exec("P = {" + m.group(1) + "}", ns)
P = ns["P"]

# ---- abgeleitete Masse (identisch zur Fusion-Logik) ----
in_w = P["pcb_w"] + 2 * P["pcb_clear"]
out_w = in_w + 2 * P["wall"]
z_bat = P["bat_t"] + 2 * P["bat_clear"]
base_h = P["floor"] + z_bat + P["bot_clear"] + P["pcb_t"] + 2.0
lid_h = P["lid_cavity"] + P["lid_plate"]
boss_od = P["spk_d"] + 2 * P["boss_wall"]
boss_h = P["spk_depth"] + P["spk_flange_t"] + P["chamber_h"] + 1.2
scx = out_w / 2.0          # Schnitt durch Lautsprecher-Mitte (x)

S = 9.0                    # Skala px/mm
GAP = 11                   # Explosionsabstand mm


def x(v):
    return round(60 + v * S, 1)


rows = []
y_cursor = 12.0

def block(h):
    global y_cursor
    y0 = y_cursor
    y_cursor += h + GAP
    return y0

def Y(y0, v):
    return round(20 + (y0 + v) * S, 1)

svg = []
svg.append(f'<svg viewBox="0 0 {round(120 + out_w * S + 330)} '
           f'{round(60 + (lid_h + 4 + P["spk_depth"] + 3 + P["pcb_t"] + 4 + P["bat_t"] + base_h + 6 * GAP + 24) * S / 1 + 40)}"'
           ' xmlns="http://www.w3.org/2000/svg" role="img"'
           ' aria-label="Explosions-Schnitt AuraBip-Gehaeuse (massstaeblich)">')
svg.append('<style>.p{fill:#1d3a43;stroke:#3d5a64;stroke-width:1.2}'
           '.c{fill:#10242b;stroke:#3d5a64;stroke-width:1}'
           '.pcb{fill:#173d2a;stroke:#3d5a64;stroke-width:1.2}'
           '.bat{fill:#203038;stroke:#3d5a64;stroke-width:1.2}'
           '.spk{fill:#142b32;stroke:#3d5a64;stroke-width:1.2}'
           '.acc{stroke:#ff7a3d;stroke-width:1.4;fill:none}'
           '.lbl{font:13px Segoe UI,sans-serif;fill:#e8e4d8}'
           '.sub{font:11px Segoe UI,sans-serif;fill:#8fa3a6}'
           '.dim{font:10px Segoe UI,sans-serif;fill:#8fa3a6}'
           '.lead{stroke:#8fa3a6;stroke-width:1;stroke-dasharray:3 4}</style>')

LX = x(out_w) + 26   # Label-Spalte

# ================= DECKEL (Schnitt) =================
y0 = block(lid_h + boss_h - P["lid_cavity"] + 2)
# Deckelplatte
svg.append(f'<rect class="p" x="{x(0)}" y="{Y(y0,0)}" width="{out_w*S:.0f}" height="{P["lid_plate"]*S:.0f}"/>')
# Trichter (Ausschnitt in der Platte, konisch angedeutet)
h1, h2 = P["horn_d1"], P["horn_d2"]
svg.append(f'<polygon points="{x(scx-h2/2)},{Y(y0,0)} {x(scx+h2/2)},{Y(y0,0)} '
           f'{x(scx+h1/2)},{Y(y0,P["lid_plate"])} {x(scx-h1/2)},{Y(y0,P["lid_plate"])}" '
           f'fill="#0f1d21" stroke="#3d5a64"/>')
# Gitterstege
for k in (-1, 0, 1):
    gx = scx + k * 6.0
    svg.append(f'<rect class="c" x="{x(gx-P["grill_bar"]/2)}" y="{Y(y0,0)}" width="{P["grill_bar"]*S:.1f}" height="{P["lid_plate"]*S:.0f}"/>')
# Deckelwaende
for wx in (0, out_w - P["wall"]):
    svg.append(f'<rect class="p" x="{x(wx)}" y="{Y(y0,P["lid_plate"])}" width="{P["wall"]*S:.0f}" height="{P["lid_cavity"]*S:.0f}"/>')
# Feder (Dichtlippe) unten an den Waenden
tc = P["tongue_clear"]
for wx in (P["groove_off"] + tc, out_w - P["groove_off"] - P["groove_w"] + tc):
    svg.append(f'<rect class="acc" x="{x(wx)}" y="{Y(y0,P["lid_plate"]+P["lid_cavity"])}" '
               f'width="{(P["groove_w"]-2*tc)*S:.1f}" height="{(P["groove_d"]-tc)*S:.1f}" fill="#ff7a3d" fill-opacity="0.25"/>')
# Boss-Ring + Kammer
bl, br = scx - boss_od / 2, scx + boss_od / 2
svg.append(f'<rect class="p" x="{x(bl)}" y="{Y(y0,P["lid_plate"])}" width="{P["boss_wall"]*S:.0f}" height="{boss_h*S:.0f}"/>')
svg.append(f'<rect class="p" x="{x(br-P["boss_wall"])}" y="{Y(y0,P["lid_plate"])}" width="{P["boss_wall"]*S:.0f}" height="{boss_h*S:.0f}"/>')
# Reflexkanal: Decke laeuft vom Boss zur rechten Wand (im Schnitt sichtbar)
pz = P["lid_plate"] + P["lid_cavity"] - P["port_h"]
svg.append(f'<rect class="c" x="{x(br-0.4)}" y="{Y(y0,pz)}" width="{(out_w-P["wall"]-br+0.4)*S:.0f}" height="{P["port_h"]*S:.0f}" fill="#0f1d21"/>')
svg.append(f'<rect class="p" x="{x(br-0.4)}" y="{Y(y0,pz+P["port_h"])}" width="{(out_w-P["wall"]-br+0.4)*S:.0f}" height="{1.2*S:.0f}"/>')
# Austritt durch die Wand
svg.append(f'<rect x="{x(out_w-P["wall"])}" y="{Y(y0,pz)}" width="{P["wall"]*S:.0f}" height="{P["port_h"]*S:.0f}" fill="#0f1d21" stroke="#ff7a3d"/>')
# Schraubensenkung angedeutet (links)
svg.append(f'<rect class="c" x="{x(P["scr_pos"]-P["scr_head_d"]/2)}" y="{Y(y0,0)}" width="{P["scr_head_d"]*S:.1f}" height="{P["scr_head_h"]*S:.1f}"/>')
svg.append(f'<line class="lead" x1="{x(out_w)+4}" y1="{Y(y0,pz+1.5)}" x2="{LX-6}" y2="{Y(y0,pz+1.5)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,1.2)}">Deckel (Schnitt)</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,3.0)}">Trichter {h1:g}&#8594;{h2:g} mm, Gitter, M2-Senkungen</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,pz+2.2)}">Reflexkanal {P["port_w"]:g}&#215;{P["port_h"]:g} &#8594; durch die Wand</text>')

# ================= LAUTSPRECHER =================
y0 = block(P["spk_depth"])
svg.append(f'<rect class="spk" rx="4" x="{x(scx-P["spk_d"]/2)}" y="{Y(y0,0)}" width="{P["spk_d"]*S:.0f}" height="{P["spk_depth"]*S:.0f}"/>')
svg.append(f'<circle class="c" cx="{x(scx)}" cy="{Y(y0,P["spk_depth"]/2)}" r="{P["spk_d"]/5*S:.0f}"/>')
svg.append(f'<line class="lead" x1="{x(scx+P["spk_d"]/2)+4}" y1="{Y(y0,P["spk_depth"]/2)}" x2="{LX-6}" y2="{Y(y0,P["spk_depth"]/2)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,1.5)}">Lautsprecher K 28 WP</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,3.3)}">&#216;{P["spk_d"]:g}, sitzt im Boss-Ring, Membran zum Trichter</text>')

# ================= KAMMERDECKEL =================
y0 = block(2.4)
svg.append(f'<rect class="p" x="{x(scx-boss_od/2)}" y="{Y(y0,1.0)}" width="{boss_od*S:.0f}" height="{1.2*S:.0f}"/>')
svg.append(f'<rect class="p" x="{x(scx-(P["spk_d"]-0.5)/2)}" y="{Y(y0,0)}" width="{(P["spk_d"]-0.5)*S:.0f}" height="{1.0*S:.0f}"/>')
svg.append(f'<line class="lead" x1="{x(scx+boss_od/2)+4}" y1="{Y(y0,1.4)}" x2="{LX-6}" y2="{Y(y0,1.4)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,1.2)}">Kammerdeckel (3. Druckteil)</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,3.0)}">mit Zentrierbund, dicht einkleben = geschlossene Kammer</text>')

# ================= PLATINE =================
y0 = block(P["pcb_t"] + 3.2)
px0 = P["wall"] + P["pcb_clear"]
svg.append(f'<rect class="pcb" x="{x(px0)}" y="{Y(y0,0)}" width="{P["pcb_w"]*S:.0f}" height="{P["pcb_t"]*S:.0f}"/>')
# E22 auf der Unterseite (14 breit im Schnitt ~ zentriert), USB oben rechts angedeutet
svg.append(f'<rect class="c" x="{x(px0+11)}" y="{Y(y0,P["pcb_t"])}" width="{14*S:.0f}" height="{3.0*S:.0f}"/>')
svg.append(f'<rect class="c" x="{x(px0+38)}" y="{Y(y0,-2.0)}" width="{9*S:.0f}" height="{2.0*S:.0f}"/>')
svg.append(f'<line class="lead" x1="{x(px0+P["pcb_w"])+4}" y1="{Y(y0,0.8)}" x2="{LX-6}" y2="{Y(y0,0.8)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,0.6)}">Platine {P["pcb_w"]:g}&#215;{P["pcb_h"]:g}&#215;{P["pcb_t"]:g}</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,2.4)}">liegt auf dem Steg; FANET-Modul (E22) unten</text>')

# ================= AKKU =================
y0 = block(P["bat_t"])
bx0 = (out_w - 52.0) / 2
svg.append(f'<rect class="bat" rx="3" x="{x(bx0)}" y="{Y(y0,0)}" width="{52.0*S:.0f}" height="{P["bat_t"]*S:.0f}"/>')
svg.append(f'<text class="dim" x="{x(bx0+2)}" y="{Y(y0,P["bat_t"]-1.2)}">LiPo 504050 &#183; 1500 mAh</text>')
svg.append(f'<line class="lead" x1="{x(bx0+52)+4}" y1="{Y(y0,P["bat_t"]/2)}" x2="{LX-6}" y2="{Y(y0,P["bat_t"]/2)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,1.4)}">Akku 52&#215;42&#215;{P["bat_t"]:g}</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,3.2)}">im Schacht der Basis, {P["bat_clear"]:g} mm Luft</text>')

# ================= BASIS (Schnitt) =================
y0 = block(base_h)
# Waende
for wx in (0, out_w - P["wall"]):
    svg.append(f'<rect class="p" x="{x(wx)}" y="{Y(y0,0)}" width="{P["wall"]*S:.0f}" height="{base_h*S:.0f}"/>')
# Boden
svg.append(f'<rect class="p" x="{x(0)}" y="{Y(y0,base_h-P["floor"])}" width="{out_w*S:.0f}" height="{P["floor"]*S:.0f}"/>')
# Nut in der Stirnflaeche
for wx in (P["groove_off"], out_w - P["groove_off"] - P["groove_w"]):
    svg.append(f'<rect x="{x(wx)}" y="{Y(y0,0)}" width="{P["groove_w"]*S:.1f}" height="{P["groove_d"]*S:.1f}" fill="#0f1d21" stroke="#ff7a3d"/>')
# Insert-Bohrung links
svg.append(f'<rect class="c" x="{x(P["scr_pos"]-P["ins_d"]/2)}" y="{Y(y0,0)}" width="{P["ins_d"]*S:.1f}" height="{P["ins_depth"]*S:.1f}"/>')
# Auflagesteg
ledge_z = base_h - P["floor"] - z_bat - P["bot_clear"] - 1.2 + P["floor"]
for wx in (P["wall"], out_w - P["wall"] - P["ledge"]):
    svg.append(f'<rect class="p" x="{x(wx)}" y="{Y(y0, P["lid_plate"] + 4.4)}" width="{P["ledge"]*S:.0f}" height="{1.2*S:.0f}"/>')
# Antennen-Nische (rechte Wand innen, symbolisch)
svg.append(f'<rect x="{x(out_w-P["wall"])}" y="{Y(y0,base_h-P["floor"]-P["ant_h"])}" width="{P["ant_d"]*S:.1f}" height="{P["ant_h"]*S:.0f}" fill="#0f1d21" stroke="#ff7a3d"/>')
svg.append(f'<line class="lead" x1="{x(out_w)+4}" y1="{Y(y0,2)}" x2="{LX-6}" y2="{Y(y0,2)}"/>')
svg.append(f'<text class="lbl" x="{LX}" y="{Y(y0,1.6)}">Basis (Schnitt)</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,3.4)}">Nut-Dichtsitz (orange), Insert {P["ins_d"]:g}&#215;{P["ins_depth"]:g},</text>')
svg.append(f'<text class="sub" x="{LX}" y="{Y(y0,5.2)}">Akkuschacht, Antennen-Nische (orange, Wand)</text>')

# Massstab
svg.append(f'<line x1="{x(0)}" y1="{Y(y0,base_h+4)}" x2="{x(20)}" y2="{Y(y0,base_h+4)}" stroke="#8fa3a6" stroke-width="2"/>')
svg.append(f'<text class="dim" x="{x(0)}" y="{Y(y0,base_h+7)}">20 mm &#183; Aussen {out_w:g} mm breit &#183; massstaeblich aus aurabip_case.py</text>')
svg.append('</svg>')

out = os.path.join(D, "case_section.svg.frag")
open(out, "w", encoding="utf-8").write("\n".join(svg))
print(f"SVG generiert: {out} ({len(''.join(svg))//1024} KB), out_w={out_w:g}, lid_h={lid_h:g}, base_h={base_h:g}")
