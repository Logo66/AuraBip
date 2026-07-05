"""AuraBip audio — PCB-Generator v0.1.

Baut hardware/project/aurabip.kicad_pcb:
- Netzliste kommt aus dem Schema (kicad-cli sch export netlist), keine Duplikation
- Quectel-L96-Footprint wird generiert (⚠️ VERIFY T-H2 gegen Quectel-Doku)
- Platzierung nach Floorplan, 36×52 mm, 4 Lagen (Sig/GND/3V3/Sig)
- Antennen-Keepout fuer ESP32-MINI, Zonen, Board-Outline
- KEINE Tracks — Routing macht die FreeRouting-Pipeline (route/)

Ausfuehren mit KiCads Python:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generate_pcb.py
"""

import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from symlib import parse  # S-Expression-Parser fuer die Netzliste

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HW_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.path.join(HW_DIR, "project")
LIB_FP = os.path.join(HW_DIR, "lib", "aurabip.pretty")
KICAD_FP = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

SCH = os.path.join(PROJECT_DIR, "aurabip.kicad_sch")
NETLIST = os.path.join(PROJECT_DIR, "aurabip.net")
OUTPUT = os.path.join(PROJECT_DIR, "aurabip.kicad_pcb")

MM = pcbnew.FromMM


def vec(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def fp_lib(name):
    return os.path.join(KICAD_FP, f"{name}.pretty")


# ============================================================
# Quectel-L96-Footprint (LCC-12, 14×15 mm, Patch-Antenne oben)
# ⚠️ VERIFY T-H2: Padgeometrie/-nummerierung gegen Quectel L96
# Hardware Design Guide pruefen, bevor irgendwas bestellt wird!
# Annahme: 6 Pads je Seite in der unteren Haelfte, Pitch 1.9 mm,
# Pad 1.1×0.9, Pin 1 links oben, gegen den Uhrzeigersinn.
# ============================================================

def create_l96_footprint():
    """Quectel L96 GNSS, LCC-31, 14.0×9.6 mm, Chip-Antenne.

    VERIFIZIERT 2026-07-05 gegen Quectel L96 Hardware Design V1.4, Fig. 21/22
    (quectel.com/content/uploads/2024/02/Quectel_L96_Hardware_Design_V1.4-4.pdf):
    - Seiten-Landpads 2.15×0.70, 13 je Laengsseite, Pitch 1.00 (Eck 1.15),
      Reihenmitte-zu-Reihenmitte 12.15
    - Stirnpads 27-31: 0.70×2.15, Pitch 1.00, mittig
    - Lokal: Antenne oben (-y, padfrei), Stirnpads unten (Datenblatt 180°
      gedreht) -> Pin 1 unten rechts, 1..13 rechts aufwaerts,
      14..26 links abwaerts, 27..31 unten von rechts nach links
    """
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("aurabip", "Quectel_L96"))
    fp.SetLibDescription("Quectel L96 GNSS LCC-31 (HW Design V1.4 Fig.22)")
    fp.SetKeywords("GNSS L96 Quectel MT3333")
    fp.SetAttributes(pcbnew.FP_SMD)

    half_row = 12.15 / 2.0
    # rechte Seite: Pin 1 unten (y +6.20), 1..12 Pitch 1.00, 12->13 Pitch 1.15
    ys_right = [6.20 - i * 1.00 for i in range(12)] + [6.20 - 11.0 - 1.15]
    for i, yy in enumerate(ys_right):
        _l96_pad(fp, str(i + 1), half_row, yy, 2.15, 0.70)
    # linke Seite: Pin 14 oben (y -5.95), 14->15 Pitch 1.15, dann 1.00
    ys_left = [-5.95] + [-4.80 + i * 1.00 for i in range(12)]
    for i, yy in enumerate(ys_left):
        _l96_pad(fp, str(i + 14), -half_row, yy, 2.15, 0.70)
    # Stirnseite unten: 27..31 von rechts (x+2.0) nach links
    for i, xx in enumerate([2.0, 1.0, 0.0, -1.0, -2.0]):
        _l96_pad(fp, str(i + 27), xx, 6.925, 0.70, 2.15)

    for (x1, y1, x2, y2, layer, w) in [
        (-4.8, -7.0, 4.8, 7.0, pcbnew.F_Fab, 0.1),
        (-7.4, -7.3, 7.4, 8.3, pcbnew.F_CrtYd, 0.05),
    ]:
        r = pcbnew.PCB_SHAPE(fp)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(vec(x1, y1)); r.SetEnd(vec(x2, y2))
        r.SetLayer(layer); r.SetWidth(MM(w))
        fp.Add(r)

    # Antennenzone markieren (Silk, oben, padfreies Ende)
    ant = pcbnew.PCB_SHAPE(fp)
    ant.SetShape(pcbnew.SHAPE_T_RECT)
    ant.SetStart(vec(-2.4, -7.0)); ant.SetEnd(vec(2.4, -2.5))
    ant.SetLayer(pcbnew.F_SilkS); ant.SetWidth(MM(0.12))
    fp.Add(ant)

    marker = pcbnew.PCB_SHAPE(fp)  # Pin 1 unten rechts
    marker.SetShape(pcbnew.SHAPE_T_CIRCLE)
    marker.SetStart(vec(8.0, 6.2)); marker.SetEnd(vec(8.15, 6.2))
    marker.SetLayer(pcbnew.F_SilkS); marker.SetWidth(MM(0.15))
    fp.Add(marker)

    fp.Reference().SetPosition(vec(0, -8.1))
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    fp.Value().SetPosition(vec(0, 9.3))
    fp.Value().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))

    os.makedirs(LIB_FP, exist_ok=True)
    pcbnew.FootprintSave(LIB_FP, fp)
    print("L96-Footprint gespeichert (HW Design V1.4 verifiziert)")


def create_e22_footprint():
    """Ebyte E22-900M22S (SX1262+TCXO+PA), 14×20 mm, 22 Stamp-Hole-Pads.

    VERIFIZIERT 2026-07-05 gegen Ebyte User Manual v1.3 (2022-10-26,
    https://www.cdebyte.com/pdf-down.aspx?id=1822) und Referenz-Footprint
    github.com/candykingdom/homebrew.pretty/E22-900M22S.kicad_mod:
    - Modul 14.0×20.0×3.0 mm, 11 Pads je 20-mm-Laengsseite
    - Pitch 1.27 mm, zwischen Pin 3<->4 bzw. 19<->20 Luecke 5.588 mm
    - PCB-Pad 1.68×0.81, Reihenmitte-zu-Reihenmitte 13.97 mm
    - Top-View: Pin 1 unten RECHTS, 1..11 rechts aufsteigend,
      12 oben links, 12..22 links absteigend; IPX-Buchse unten links
    """
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID("aurabip", "E22_900M22S"))
    fp.SetLibDescription("Ebyte E22-900M22S SX1262, 14x20, Manual v1.3 verifiziert")
    fp.SetKeywords("LoRa SX1262 E22 FANET")
    fp.SetAttributes(pcbnew.FP_SMD)

    # Y-Kette ab Moduloberkante (y=-10): 2.00, dann 7x1.27, Luecke 5.588,
    # 2x1.27, Rest 1.00 zur Unterkante. Pin 12 oben links ... Pin 22 unten links.
    y_top = -10.0
    ys = []
    y = y_top + 2.0
    for i in range(8):            # 8 Pads im oberen Block (12..19 links)
        ys.append(y); y += 1.27
    y = y - 1.27 + 5.588          # Luecke
    for i in range(3):            # 3 Pads im unteren Block (20..22 links)
        ys.append(y); y += 1.27
    xr, xl = 13.97 / 2.0, -13.97 / 2.0

    # links: 12 (oben) .. 22 (unten)
    for i, yy in enumerate(ys):
        _smd_pad(fp, str(12 + i), xl, yy, 1.68, 0.81)
    # rechts: 11 (oben) .. 1 (unten)
    for i, yy in enumerate(ys):
        _smd_pad(fp, str(11 - i), xr, yy, 1.68, 0.81)

    for (x1, y1, x2, y2, layer, w) in [
        (-7.0, -10.0, 7.0, 10.0, pcbnew.F_Fab, 0.1),
        (-7.7, -10.3, 7.7, 10.3, pcbnew.F_CrtYd, 0.05),
    ]:
        r = pcbnew.PCB_SHAPE(fp)
        r.SetShape(pcbnew.SHAPE_T_RECT)
        r.SetStart(vec(x1, y1)); r.SetEnd(vec(x2, y2))
        r.SetLayer(layer); r.SetWidth(MM(w))
        fp.Add(r)

    # Pin-1-Marker unten rechts
    marker = pcbnew.PCB_SHAPE(fp)
    marker.SetShape(pcbnew.SHAPE_T_CIRCLE)
    marker.SetStart(vec(8.3, ys[-1])); marker.SetEnd(vec(8.45, ys[-1]))
    marker.SetLayer(pcbnew.F_SilkS); marker.SetWidth(MM(0.15))
    fp.Add(marker)

    fp.Reference().SetPosition(vec(0, -11.1))
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    fp.Value().SetPosition(vec(0, 11.1))
    fp.Value().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
    pcbnew.FootprintSave(LIB_FP, fp)
    print("E22-Footprint gespeichert (Manual v1.3 verifiziert)")


def _smd_pad(fp, num, x, y, w, h):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(num)
    pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    pad.SetRoundRectRadiusRatio(0.2)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetLayerSet(pcbnew.PAD(fp).SMDMask())
    pad.SetPosition(vec(x, y))
    pad.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    fp.Add(pad)


def create_esp32_compact_footprint():
    """ESP32-S3-MINI-1 mit kompaktem Courtyard.

    Das offizielle KiCad-Footprint traegt Espressifs komplette
    Antennen-Freihaltezone (45×35 mm) als Courtyard — auf einem
    36-mm-Board unbrauchbar. Serienueblich (Heltec etc.): Body-Courtyard
    + expliziter Kupfer-Keepout unter der Antenne (macht generate()).
    HF-Kompromiss bewusst akzeptiert, siehe hardware/README.md.
    """
    fp = pcbnew.FootprintLoad(fp_lib("RF_Module"), "ESP32-S2-MINI-1")
    fp.SetFPID(pcbnew.LIB_ID("aurabip", "ESP32-S3-MINI-1_compact"))
    fp.SetLibDescription("ESP32-S3-MINI-1, Courtyard nur Body+Antenne (kompakt)")
    for g in list(fp.GraphicalItems()):
        if g.GetLayer() == pcbnew.F_CrtYd:
            fp.Remove(g)
    # Espressif bettet die komplette Antennen-Freihaltezone auch als
    # Keepout-ZONEN ein (±22.7×19.5!) — die fliegen mit raus; unser
    # eigener, kleinerer Keepout kommt in generate() aufs Board.
    # (FreeRouting wirft sonst alle Pins innerhalb stillschweigend raus.)
    for z in list(fp.Zones()):
        fp.Remove(z)
    r = pcbnew.PCB_SHAPE(fp)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(vec(-8.05, -10.75))   # Antenne oben (-y), Body bis y=10.55
    r.SetEnd(vec(8.05, 10.75))
    r.SetLayer(pcbnew.F_CrtYd)
    r.SetWidth(MM(0.05))
    fp.Add(r)
    pcbnew.FootprintSave(LIB_FP, fp)
    print("ESP32-Kompakt-Footprint gespeichert")


def _l96_pad(fp, num, x, y, w, h):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(num)
    pad.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    pad.SetRoundRectRadiusRatio(0.2)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetLayerSet(pcbnew.PAD(fp).SMDMask())
    pad.SetPosition(vec(x, y))
    pad.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    fp.Add(pad)


# ============================================================
# Netzliste aus dem Schema exportieren + parsen
# ============================================================

def load_netlist():
    subprocess.run([KICAD_CLI, "sch", "export", "netlist",
                    "--format", "kicadsexpr", "-o", NETLIST, SCH],
                   check=True, capture_output=True)
    tree = parse(open(NETLIST, encoding="utf-8").read())

    def atom(x):
        return x[1:] if isinstance(x, str) and x.startswith('"') else x

    pad_nets = {}   # (ref, pin) -> netname
    netnames = set()

    def walk(node):
        if isinstance(node, list) and node and node[0] == "net":
            name = None
            nodes = []
            for sub in node:
                if isinstance(sub, list):
                    if sub[0] == "name":
                        name = atom(sub[1])
                    elif sub[0] == "node":
                        ref = pin = None
                        for s2 in sub:
                            if isinstance(s2, list):
                                if s2[0] == "ref":
                                    ref = atom(s2[1])
                                elif s2[0] == "pin":
                                    pin = atom(s2[1])
                        nodes.append((ref, pin))
            if name and len(nodes) > 1:  # Ein-Pin-Netze nicht routen
                # KiCad-Autonamen "/LABEL" -> "LABEL"
                clean = name.lstrip("/")
                netnames.add(clean)
                for ref, pin in nodes:
                    pad_nets[(ref, pin)] = clean
        elif isinstance(node, list):
            for sub in node:
                walk(sub)

    walk(tree)
    return pad_nets, netnames


# ============================================================
# Floorplan: (ref, lib_dir, footprint, x, y, rot, value)
# Board 36×52, Ursprung oben links, +y nach unten.
# ============================================================

BW, BH = 52.0, 52.0

PLACEMENT = [
    # GNSS oben, Chip-Antenne Richtung Oberkante (Quectel: mittig an
    # die Kante, GND-Flaeche seitlich weiterfuehren)
    ("U5", None, "Quectel_L96",                                     18.0,  8.1,   0, "L96"),
    ("C7", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            26.5,  6.3,  90, "100n"),
    ("C16", fp_lib("Capacitor_SMD"), "C_0603_1608Metric",           26.5,  9.5,  90, "10u"),
    # RF-Bruecke direkt neben RF_OUT/RF_IN (Pads bei x~11.9, y 4.3/5.3)
    ("R12", fp_lib("Resistor_SMD"), "R_0402_1005Metric",            10.0,  4.8,  90, "0R"),
    # RXD1-Pegelteiler unterhalb des Moduls
    ("R13", fp_lib("Resistor_SMD"), "R_0402_1005Metric",            13.5, 17.2,   0, "1k"),
    ("R14", fp_lib("Resistor_SMD"), "R_0402_1005Metric",            16.5, 17.2,   0, "2k"),

    # ESP32-Modul links, Antenne zur linken Kante (rot 90: Antenne -> -x)
    ("U1", None, "ESP32-S3-MINI-1_compact",                         11.0, 26.0,  90, "ESP32-S3-MINI-1"),
    ("C1", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            23.0, 20.0,  90, "100n"),
    ("R5", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             23.0, 23.5,  90, "10k"),
    ("C10", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",           23.0, 27.0,  90, "1u"),

    # Baro + Feuchte auf der thermisch entkoppelten Sensor-Insel
    # (rechte Kante, C-Fraes-Graben, Bruecke x 50..52)
    ("U2", None, "BMP581_LGA-10_2x2mm",                             47.5, 21.5,   0, "BMP581"),
    ("C4", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            45.5, 21.5,  90, "100n"),
    ("U4", fp_lib("Sensor_Humidity"),
           "Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",   47.5, 25.0,   0, "SHT40"),
    ("C6", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            45.5, 25.0,  90, "100n"),
    # IMU bleibt auf dem Hauptboard (starr, thermisch unkritisch)
    ("U3", fp_lib("Package_LGA"), "LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
                                                                     26.5, 27.5,   0, "LSM6DSO32"),
    ("C5", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            29.0, 27.5,  90, "100n"),
    ("R3", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             31.5, 26.0,  90, "4.7k"),
    ("R4", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             31.5, 29.5,  90, "4.7k"),

    # OLED-Anschluss: JST-PH 8-Pin vertikal, Waveshare-Kabel zum Display
    ("J4", fp_lib("Connector_JST"),
           "JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical",                 38.0, 17.5,  90, "OLED SPI"),

    # Akku-Anschluss rechts oben
    ("J2", fp_lib("Connector_JST"),
           "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",               47.0, 10.5, 180, "AKKU"),

    # RESET rechts unten (kleine Taste, versenkt im Gehaeuse)
    ("SW2", fp_lib("Button_Switch_SMD"), "SW_Push_1P1T_NO_CK_KMR2", 47.0, 34.0,   0, "RESET"),

    # Audio unten Mitte/rechts
    ("U6", fp_lib("Package_DFN_QFN"),
           "TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",                22.0, 38.0,   0, "MAX98357A"),
    ("R8", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             17.5, 36.5,  90, "100k"),
    ("C8", fp_lib("Capacitor_SMD"), "C_0805_2012Metric",            26.5, 36.0,  90, "22u"),
    # links vom Amp: rechts davon liegt das E22-Padfeld der Rueckseite
    # (Durchgangs-Vias fuer den GND-Anschluss waeren dort blockiert)
    ("C9", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            19.0, 36.9,  90, "100n"),
    # Oeffnung zur Board-MITTE (Ivo 2026-07-06: nie gegen die Wand,
    # nicht ueber SW2 — Kabel faehrt von innen ein)
    ("J3", fp_lib("Connector_JST"),
           "JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",               46.5, 43.5, 270, "SPEAKER"),

    # VBAT-Teiler
    ("R9", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             14.5, 36.5,  90, "1M"),
    ("R10", fp_lib("Resistor_SMD"), "R_0402_1005Metric",            12.0, 36.5,  90, "1M"),
    ("C11", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",            9.5, 36.5,  90, "100n"),

    # LDO + Schalter links unten
    ("U8", fp_lib("Package_TO_SOT_SMD"), "SOT-23-5",                 4.5, 36.5,   0, "AP2112K-3.3"),
    ("C3", fp_lib("Capacitor_SMD"), "C_0603_1608Metric",             8.0, 36.5,  90, "10u"),
    ("C2", fp_lib("Capacitor_SMD"), "C_0603_1608Metric",             4.5, 40.0,   0, "10u"),
    # rot 270: Signal-Pads nach rechts (bei 90 sind sie zwischen Kante
    # und NPTH-Justierloechern gefangen -> unroutbar)
    ("SW1", fp_lib("Button_Switch_SMD"), "SW_SPDT_PCM12",            3.2, 45.5, 270, "EIN/AUS"),

    # Lader + Lade-LED
    ("U7", fp_lib("Package_TO_SOT_SMD"), "SOT-23-5",                20.5, 44.5,   0, "MCP73831"),
    ("R11", fp_lib("Resistor_SMD"), "R_0402_1005Metric",            24.0, 44.5,  90, "2k"),
    ("C13", fp_lib("Capacitor_SMD"), "C_0603_1608Metric",           25.5, 44.5,  90, "4.7u"),
    ("C12", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",           18.5, 41.0,  90, "100n"),
    ("R6", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             21.0, 41.0,   0, "1k"),
    ("D1", fp_lib("LED_SMD"), "LED_0603_1608Metric",                24.5, 41.0,   0, "CHG"),

    # Status-LED (rechts vom ESP32)
    ("R7", fp_lib("Resistor_SMD"), "R_0402_1005Metric",             23.5, 30.0,   0, "1k"),
    ("D2", fp_lib("LED_SMD"), "LED_0603_1608Metric",                23.5, 32.0,   0, "STATUS"),

    # USB-C unten Mitte + ESD + CC-Widerstaende
    # rot 0: Oeffnung zur Unterkante, Nase ragt ~1.2 mm ueber (T-H6)
    ("J1", fp_lib("Connector_USB"),
           "USB_C_Receptacle_HRO_TYPE-C-31-M-12",                   12.0, 49.0,   0, "USB-C"),
    ("U9", fp_lib("Package_TO_SOT_SMD"), "SOT-23-6",                12.0, 41.5,   0, "USBLC6"),
    ("R1", fp_lib("Resistor_SMD"), "R_0402_1005Metric",              7.0, 41.5,  90, "5.1k"),
    ("R2", fp_lib("Resistor_SMD"), "R_0402_1005Metric",              9.0, 41.5,  90, "5.1k"),

    # BOOT/USER-Taste unten rechts vom USB
    ("SW3", fp_lib("Button_Switch_SMD"), "SW_Push_1P1T_NO_CK_KMR2", 20.5, 49.5,   0, "BOOT"),

    # Testpads unten rechts
    ("TP1", fp_lib("TestPoint"), "TestPoint_Pad_1.5x1.5mm",         25.2, 48.5,   0, "IO33"),
    ("TP2", fp_lib("TestPoint"), "TestPoint_Pad_1.5x1.5mm",         27.9, 48.5,   0, "IO34"),
    ("TP3", fp_lib("TestPoint"), "TestPoint_Pad_1.5x1.5mm",         30.6, 48.5,   0, "IO35"),
    ("TP4", fp_lib("TestPoint"), "TestPoint_Pad_1.5x1.5mm",         33.3, 48.5,   0, "IO36"),
]

# Rueckseite (Handbestueckung): FANET-Modul + Antennenbuchse + Abblock-Cs.
# Koordinaten in Vorderseiten-Sicht; Flip macht der Generator.
PLACEMENT_BACK = [
    ("U10", None, "E22_900M22S",                                    18.0, 30.0,   0, "E22-900M22S"),
    ("J5",  fp_lib("Connector_Coaxial"),
            "U.FL_Hirose_U.FL-R-SMT-1_Vertical",                    22.0, 47.5,   0, "u.FL 868"),
    ("C14", fp_lib("Capacitor_SMD"), "C_0402_1005Metric",           10.5, 46.0,  90, "100n"),
    ("C15", fp_lib("Capacitor_SMD"), "C_0603_1608Metric",           13.0, 46.0,  90, "10u"),
]


def generate():
    create_l96_footprint()
    create_esp32_compact_footprint()
    create_e22_footprint()

    pad_nets, netnames = load_netlist()
    print(f"Netzliste: {len(netnames)} Netze, {len(pad_nets)} Pad-Zuordnungen")

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.5)
    ds.m_ViasMinDrill = MM(0.3)
    ds.m_CopperEdgeClearance = MM(0.1)
    try:
        ds.m_MinClearance = MM(0.09)   # JLC 4-Lagen kann 0.09/0.09
        ds.m_HoleClearance = MM(0.20)  # JLC: Bohrloch->Kupfer min 0.2 (VERIFY T-H1)
    except Exception:
        pass
    # Default-Netzklasse: sonst gilt KiCads 0.2-mm-Clearance und
    # FreeRouting kommt nicht zwischen die 0.4-mm-Pitch-Pads (BMP581)
    try:
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetClearance(MM(0.10))
        nc.SetTrackWidth(MM(0.15))
        nc.SetViaDiameter(MM(0.5))
        nc.SetViaDrill(MM(0.3))
    except Exception as e:
        print(f"WARN Netzklasse: {e}")

    nets = {}
    for name in sorted(netnames):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # Outline mit 1.5-mm-Eckenradius
    r = 1.5
    lines = [((r, 0), (BW - r, 0)), ((BW, r), (BW, BH - r)),
             ((BW - r, BH), (r, BH)), ((0, BH - r), (0, r))]
    for (x1, y1), (x2, y2) in lines:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(vec(x1, y1)); seg.SetEnd(vec(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts); seg.SetWidth(MM(0.05))
        board.Add(seg)
    for (cx, cy), (sx, sy) in [((r, r), (0, r)), ((BW - r, r), (BW - r, 0)),
                                ((BW - r, BH - r), (BW, BH - r)), ((r, BH - r), (r, BH))]:
        arc = pcbnew.PCB_SHAPE(board)
        arc.SetShape(pcbnew.SHAPE_T_ARC)
        arc.SetCenter(vec(cx, cy))
        arc.SetStart(vec(sx, sy))
        arc.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), False)
        arc.SetLayer(pcbnew.Edge_Cuts); arc.SetWidth(MM(0.05))
        board.Add(arc)

    # Thermisch entkoppelte Sensor-Insel (BMP581 + SHT40, rechte Kante):
    # C-foermiger Fraes-Graben (1 mm), Insel x 44.5..52, y 19.6..27,
    # haengt nur an der 2-mm-Bruecke x 50..52. Ein geschlossener
    # Innen-Kontur-Zug (KiCad: Cutout).
    moat = [(43.5, 18.6), (50.0, 18.6), (50.0, 19.6), (44.5, 19.6),
            (44.5, 27.0), (50.0, 27.0), (50.0, 28.0), (43.5, 28.0)]
    for i in range(len(moat)):
        x1, y1 = moat[i]
        x2, y2 = moat[(i + 1) % len(moat)]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(vec(x1, y1)); seg.SetEnd(vec(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts); seg.SetWidth(MM(0.05))
        board.Add(seg)
    print("  Sensor-Insel: C-Graben um BMP581/SHT40, Bruecke x 50..52")

    # Bestuecken
    footprints = {}
    missing = []
    for entry, flip in [(e, False) for e in PLACEMENT] + [(e, True) for e in PLACEMENT_BACK]:
        ref, lib, fpname, cx, cy, rot, value = entry
        libdir = lib if lib else LIB_FP
        fp = pcbnew.FootprintLoad(libdir, fpname)
        if fp is None:
            missing.append((ref, fpname))
            continue
        fp.SetReference(ref)
        fp.Value().SetText(value)
        board.Add(fp)
        fp.SetPosition(vec(cx, cy))
        if flip:
            fp.Flip(vec(cx, cy), False)
        fp.SetOrientationDegrees(rot)
        footprints[ref] = fp
    if missing:
        print("FEHLENDE FOOTPRINTS:", missing)

    # Netze zuweisen
    unassigned = []
    for ref, fp in footprints.items():
        for pad in fp.Pads():
            num = pad.GetNumber()
            net = pad_nets.get((ref, num))
            if net and net in nets:
                pad.SetNet(nets[net])
            elif num:
                unassigned.append(f"{ref}.{num}")
    print(f"Pads ohne Netz (NC oder pruefen!): {', '.join(unassigned) if unassigned else 'keine'}")

    # Antennen-Keepout ESP32 (Antennenende des Moduls, linke Kante)
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowZoneFills(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ko.SetLayerSet(pcbnew.LSET.AllCuMask(4))
    ol = ko.Outline(); ol.NewOutline()
    for x, y in [(0.0, 17.7), (6.0, 17.7), (6.0, 34.3), (0.0, 34.3)]:
        ol.Append(MM(x), MM(y))
    board.Add(ko)
    print("Antennen-Keepout ESP32: x 0..6.0, y 17.7..34.3 (alle Cu-Lagen)")

    # L96-Antennen-Keepout (Quectel HW Design: 4.8×7.3 unter der
    # Chip-Antenne kupfer- und bauteilfrei)
    ko2 = pcbnew.ZONE(board)
    ko2.SetIsRuleArea(True)
    ko2.SetDoNotAllowZoneFills(True)
    ko2.SetDoNotAllowTracks(True)
    ko2.SetDoNotAllowVias(True)
    ko2.SetLayerSet(pcbnew.LSET.AllCuMask(4))
    ol2 = ko2.Outline(); ol2.NewOutline()
    for x, y in [(15.6, 0.0), (20.4, 0.0), (20.4, 8.4), (15.6, 8.4)]:
        ol2.Append(MM(x), MM(y))
    board.Add(ko2)
    print("Antennen-Keepout L96: x 15.6..20.4, y 0..8.4 (alle Cu-Lagen)")

    # Zonen: GND auf F/In1/B, +3V3 auf In2 — Zonen meiden das Antennenfeld
    def add_zone(layer, netname, prio):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets[netname])
        z.SetAssignedPriority(prio)
        z.SetMinThickness(MM(0.15))
        z.SetThermalReliefGap(MM(0.25))
        z.SetThermalReliefSpokeWidth(MM(0.3))
        # Voll angebunden (Reflow-Bestueckung): keine starved thermals
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        ol = z.Outline(); ol.NewOutline()
        for x, y in [(0.3, 0.3), (BW - 0.3, 0.3), (BW - 0.3, BH - 0.3), (0.3, BH - 0.3)]:
            ol.Append(MM(x), MM(y))
        board.Add(z)

    add_zone(pcbnew.F_Cu, "GND", 1)
    add_zone(pcbnew.In1_Cu, "GND", 0)
    add_zone(pcbnew.In2_Cu, "+3V3", 0)
    add_zone(pcbnew.B_Cu, "GND", 0)

    board.Save(OUTPUT)
    print(f"PCB gespeichert: {OUTPUT}")
    print(f"  {BW}x{BH} mm, 4 Lagen, {len(footprints)} Bauteile, {len(nets)} Netze")


if __name__ == "__main__":
    generate()
