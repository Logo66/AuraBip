"""AuraBip audio — Schema-Generator v0.1.

Erzeugt hardware/project/aurabip.kicad_sch komplett aus Code:
- offizielle KiCad-10-Symbole werden aus den System-Libs extrahiert
- eigene Symbole (MAX98357A, MCP73831, L96, LSM6DSO32) werden als
  Box-Symbole generiert; BMP581 kommt aus Ivos aura_sensors-Lib
- Verbindungen ausschliesslich über Netz-Labels direkt am Pin
  (Label-Anker == Pin-Anschlusspunkt -> elektrisch verbunden)
- ungenutzte Pins bekommen no_connect-Flags

Pinnummern der eigenen Symbole: ⚠️ VERIFY-Tickets T-H2..T-H4 (BOM.md).

Ausfuehren mit KiCads Python:
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" generate_schematic.py
"""

import os
import uuid

from symlib import KICAD_SYM_DIR, extract_symbol_text, symbol_pins

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HW_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.path.join(HW_DIR, "project")
AURA_LIB = r"C:\Users\Ivo\aura_kruecke\hardware\sensor_board\lib\aura_sensors.kicad_sym"
OUTPUT = os.path.join(PROJECT_DIR, "aurabip.kicad_sch")


def uid():
    return str(uuid.uuid4())


# ============================================================
# Eigene Symbole als Box generieren
# side: "L"/"R"/"T"/"B", slot: Rasterposition entlang der Seite
# ============================================================

def make_box_symbol(name, pins, half_w=10.16, pin_len=2.54, row_pitch=2.54):
    """Erzeugt kicad_sym-Text fuer ein Rechteck-Symbol.

    pins: Liste (number, name, etype, side, slot)
      side L: Pin links, zeigt nach rechts (rot 0),  Anschluss bei x=-half_w-pin_len
      side R: Pin rechts, zeigt nach links (rot 180), Anschluss bei x=+half_w+pin_len
      slot: 0,1,2,... von oben (y = top - slot*row_pitch)
    """
    n_left = max([p[4] for p in pins if p[3] == "L"] + [0])
    n_right = max([p[4] for p in pins if p[3] == "R"] + [0])
    rows = max(n_left, n_right) + 1
    half_h = (rows + 1) * row_pitch / 2
    top = half_h - row_pitch

    pin_texts = []
    for number, pname, etype, side, slot in pins:
        y = top - slot * row_pitch
        if side == "L":
            x, rot = -half_w - pin_len, 0
        else:
            x, rot = half_w + pin_len, 180
        pin_texts.append(f"""      (pin {etype} line
        (at {x:g} {y:g} {rot})
        (length {pin_len:g})
        (name "{pname}" (effects (font (size 1.27 1.27))))
        (number "{number}" (effects (font (size 1.27 1.27))))
      )""")

    pins_block = "\n".join(pin_texts)
    return f"""(symbol "aurabip:{name}"
    (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at 0 {half_h + 1.27:g} 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{name}" (at 0 {-half_h - 1.27:g} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Description" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "{name}_0_1"
      (rectangle (start {-half_w:g} {half_h:g}) (end {half_w:g} {-half_h:g})
        (stroke (width 0.254) (type default)) (fill (type background)))
{pins_block}
    )
  )"""


def custom_symbols():
    """Definitionen der eigenen Symbole. Rueckgabe: {name: (text, pins, half_w)}."""
    defs = {}

    # MAX98357A TQFN-16-EP — ⚠️ VERIFY T-H3 (Pinnummern gegen Datenblatt)
    max_pins = [
        ("2",  "BCLK",    "input",     "L", 0),
        ("1",  "LRCLK",   "input",     "L", 1),
        ("3",  "DIN",     "input",     "L", 2),
        ("5",  "SD_MODE", "input",     "L", 3),
        ("4",  "GAIN",    "input",     "L", 4),
        ("13", "VDD",     "power_in",  "R", 0),
        ("9",  "OUTP",    "output",    "R", 2),
        ("11", "OUTN",    "output",    "R", 3),
        ("8",  "GND",     "power_in",  "R", 5),
        ("17", "EP",      "power_in",  "R", 6),
    ]
    defs["MAX98357A"] = (make_box_symbol("MAX98357A", max_pins), max_pins, 10.16)

    # MCP73831 SOT-23-5 (Pinout sicher: 1 STAT, 2 VSS, 3 VBAT, 4 VDD, 5 PROG)
    mcp_pins = [
        ("4", "VDD",  "power_in",  "L", 0),
        ("5", "PROG", "passive",   "L", 2),
        ("3", "VBAT", "power_out", "R", 0),
        ("1", "STAT", "open_collector", "R", 2),
        ("2", "VSS",  "power_in",  "R", 4),
    ]
    defs["MCP73831"] = (make_box_symbol("MCP73831", mcp_pins, half_w=7.62), mcp_pins, 7.62)

    # Quectel L96 (GNSS, integrierte Antenne) — ⚠️ VERIFY T-H2 (Padout!)
    l96_pins = [
        ("8",  "VCC",      "power_in", "L", 0),
        ("6",  "V_BCKP",   "power_in", "L", 1),
        ("4",  "RESET_N",  "input",    "L", 3),
        ("2",  "FORCE_ON", "input",    "L", 4),
        ("9",  "TXD",      "output",   "R", 0),
        ("10", "RXD",      "input",    "R", 1),
        ("5",  "1PPS",     "output",   "R", 3),
        ("11", "EX_ANT",   "passive",  "R", 4),
        ("1",  "GND",      "power_in", "R", 6),
        ("3",  "GND2",     "power_in", "R", 7),
        ("7",  "GND3",     "power_in", "R", 8),
        ("12", "GND4",     "power_in", "R", 9),
    ]
    defs["L96"] = (make_box_symbol("L96", l96_pins), l96_pins, 10.16)

    # Ebyte E22-900M22S (SX1262+TCXO+PA) — ⚠️ VERIFY T-H7 (Pinnummern!)
    # Annahme: 22 Pads, Nummerierung nach Ebyte-Datenblatt-Konvention.
    e22_pins = [
        ("11", "VCC",  "power_in", "L", 0),
        ("10", "NRST", "input",    "L", 2),
        ("19", "NSS",  "input",    "L", 4),
        ("18", "SCK",  "input",    "L", 5),
        ("17", "MOSI", "input",    "L", 6),
        ("16", "MISO", "output",   "L", 7),
        ("15", "BUSY", "output",   "L", 9),
        ("14", "DIO1", "output",   "L", 10),
        ("6",  "TXEN", "input",    "R", 4),
        ("7",  "RXEN", "input",    "R", 5),
        ("1",  "GND",  "power_in", "R", 8),
        ("12", "GND2", "power_in", "R", 9),
        ("20", "GND3", "power_in", "R", 10),
        ("3",  "ANT",  "passive",  "R", 0),
        ("2",  "GND4", "power_in", "R", 1),
    ]
    defs["E22_900M22S"] = (make_box_symbol("E22_900M22S", e22_pins), e22_pins, 10.16)

    # LSM6DSO32 LGA-14 — Nummern konsistent zur verifizierten Kruecke-Map,
    # INT1=4 ⚠️ VERIFY T-H4
    lsm_pins = [
        ("8",  "VDD",   "power_in",     "L", 0),
        ("5",  "VDDIO", "power_in",     "L", 1),
        ("12", "CS",    "input",        "L", 3),
        ("1",  "SA0",   "input",        "L", 4),
        ("13", "SCL",   "input",        "R", 0),
        ("14", "SDA",   "bidirectional","R", 1),
        ("4",  "INT1",  "output",       "R", 3),
        ("9",  "INT2",  "output",       "R", 4),
        ("2",  "SDX",   "passive",      "L", 6),
        ("3",  "SCX",   "passive",      "L", 7),
        ("10", "NC1",   "no_connect",   "R", 6),
        ("11", "NC2",   "no_connect",   "R", 7),
        ("6",  "GND",   "power_in",     "R", 9),
        ("7",  "GND2",  "power_in",     "R", 10),
    ]
    defs["LSM6DSO32"] = (make_box_symbol("LSM6DSO32", lsm_pins), lsm_pins, 10.16)

    return defs


def box_pin_points(pins, half_w=10.16, pin_len=2.54, row_pitch=2.54):
    """Anschlusspunkte eines Box-Symbols relativ zum Zentrum (Lib-Koordinaten)."""
    n_left = max([p[4] for p in pins if p[3] == "L"] + [0])
    n_right = max([p[4] for p in pins if p[3] == "R"] + [0])
    rows = max(n_left, n_right) + 1
    half_h = (rows + 1) * row_pitch / 2
    top = half_h - row_pitch
    pts = {}
    for number, pname, etype, side, slot in pins:
        y = top - slot * row_pitch
        x = (-half_w - pin_len) if side == "L" else (half_w + pin_len)
        pts[number] = (x, y)
    return pts


# ============================================================
# Schaltplan-Elemente
# ============================================================

SHEET_UUID = uid()

def comp(ref, lib_id, value, footprint, x, y, in_bom=True):
    bom = "yes" if in_bom else "no"
    return f"""  (symbol
    (lib_id "{lib_id}")
    (at {x:g} {y:g} 0)
    (unit 1)
    (exclude_from_sim no) (in_bom {bom}) (on_board yes) (dnp no)
    (uuid "{uid()}")
    (property "Reference" "{ref}" (at 0 -2.54 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{value}" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "{footprint}" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (instances
      (project "aurabip"
        (path "/{SHEET_UUID}" (reference "{ref}") (unit 1))
      )
    )
  )"""


def label(name, x, y, angle=0):
    return f"""  (label "{name}"
    (at {x:g} {y:g} {angle})
    (effects (font (size 1.27 1.27)))
    (uuid "{uid()}")
  )"""


def wire(x1, y1, x2, y2):
    return f"""  (wire
    (pts (xy {x1:g} {y1:g}) (xy {x2:g} {y2:g}))
    (uuid "{uid()}")
  )"""


def no_connect(x, y):
    return f"""  (no_connect (at {x:g} {y:g}) (uuid "{uid()}"))"""


# Label-Winkel nach Pin-Richtung (Pin rot 0 = zeigt vom Anschluss nach rechts
# in den Body -> Label soll nach links raus: angle 180)
def label_angle(pin_rot):
    return {0: 180, 90: 270, 180: 0, 270: 90}.get(int(pin_rot) % 360, 0)


# ============================================================
# Hauptgenerator
# ============================================================

def generate():
    parts = []      # Symbole, Labels, NCs
    lib_blocks = [] # lib_symbols-Eintraege

    # ---- Raster-Snap: alle Anschlusspunkte muessen auf 1.27 mm liegen ----
    def snap(v):
        return round(v / 1.27) * 1.27

    # ---- Offizielle Symbole extrahieren ----
    official = {
        "RF_Module:ESP32-S3-MINI-1": ("RF_Module", "ESP32-S3-MINI-1"),
        "Sensor_Humidity:SHT4x": ("Sensor_Humidity", "SHT4x"),
        "Regulator_Linear:AP2112K-3.3": ("Regulator_Linear", "AP2112K-3.3"),
        "Power_Protection:USBLC6-2SC6": ("Power_Protection", "USBLC6-2SC6"),
        "Connector:USB_C_Receptacle_USB2.0_16P": ("Connector", "USB_C_Receptacle_USB2.0_16P"),
        "Connector:Conn_Coaxial": ("Connector", "Conn_Coaxial"),
        "Connector_Generic:Conn_01x01": ("Connector_Generic", "Conn_01x01"),
        "Connector_Generic:Conn_01x02": ("Connector_Generic", "Conn_01x02"),
        "Connector_Generic:Conn_01x04": ("Connector_Generic", "Conn_01x04"),
        "Connector_Generic:Conn_01x07": ("Connector_Generic", "Conn_01x07"),
        "Connector_Generic:Conn_01x08": ("Connector_Generic", "Conn_01x08"),
        "Device:R": ("Device", "R"),
        "Device:C": ("Device", "C"),
        "Device:LED": ("Device", "LED"),
        "Switch:SW_Push": ("Switch", "SW_Push"),
        "Switch:SW_SPDT": ("Switch", "SW_SPDT"),
        "power:PWR_FLAG": ("power", "PWR_FLAG"),
    }
    pin_cache = {}
    import re as _re
    for full, (libname, symname) in official.items():
        path = os.path.join(KICAD_SYM_DIR, f"{libname}.kicad_sym")
        text = extract_symbol_text(path, symname)
        # extends-Symbole flach machen: Basisdefinition unter dem
        # abgeleiteten Namen einbetten (KiCad kann extends in lib_symbols
        # nicht zuverlaessig aufloesen)
        m = _re.search(r'\(extends\s+"([^"]+)"\)', text)
        if m:
            base = m.group(1)
            text = extract_symbol_text(path, base)
            text = text.replace(f'(symbol "{base}"', f'(symbol "{symname}"', 1)
            text = text.replace(f'(symbol "{base}_', f'(symbol "{symname}_')
            # Value-Property auf abgeleiteten Namen setzen
            text = _re.sub(r'\(property "Value" "[^"]*"',
                           f'(property "Value" "{symname}"', text, count=1)
        text = text.replace(f'(symbol "{symname}"', f'(symbol "{full}"', 1)
        lib_blocks.append("  " + text)
        pin_cache[full] = symbol_pins(path, symname)

    # BMP581 aus Ivos aura_sensors-Lib
    bmp_text = extract_symbol_text(AURA_LIB, "BMP581")
    bmp_text = bmp_text.replace('(symbol "BMP581"', '(symbol "aurabip:BMP581"', 1)
    lib_blocks.append("  " + bmp_text)
    pin_cache["aurabip:BMP581"] = symbol_pins(AURA_LIB, "BMP581")

    # Eigene Symbole (+ echte Lib-Datei fuer die GUI schreiben)
    customs = custom_symbols()
    lib_file_syms = []
    for name, (text, pins, hw) in customs.items():
        lib_blocks.append("  " + text)
        pts = box_pin_points(pins, half_w=hw)
        pin_cache[f"aurabip:{name}"] = [
            {"number": n, "name": pn, "etype": et,
             "x": pts[n][0], "y": pts[n][1],
             "rot": 0 if side == "L" else 180}
            for (n, pn, et, side, slot) in pins
        ]
        lib_file_syms.append(text.replace(f'(symbol "aurabip:{name}"',
                                          f'(symbol "{name}"', 1))
    # BMP581 auch in die Lib-Datei
    lib_file_syms.append(extract_symbol_text(AURA_LIB, "BMP581"))
    lib_dir = os.path.join(HW_DIR, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(lib_dir, "aurabip.kicad_sym"), "w", encoding="utf-8") as f:
        f.write('(kicad_symbol_lib (version 20231120) (generator "aurabip_gen")\n  '
                + "\n  ".join(lib_file_syms) + "\n)\n")

    # ---- Komponente platzieren + Pins verdrahten ----
    def place(ref, lib_id, value, footprint, x, y, nets, in_bom=True):
        """nets: {pinnummer: netzname | None(=NC) }; fehlende Pins -> NC."""
        x, y = snap(x), snap(y)
        parts.append(comp(ref, lib_id, value, footprint, x, y, in_bom))
        seen_pos = set()
        for p in pin_cache[lib_id]:
            px = x + p["x"]
            py = y - p["y"]          # Lib-Y ist mathematisch, Schema-Y nach unten
            pos_key = (round(px, 2), round(py, 2))
            net = nets.get(p["number"], "__NC__")
            if net == "__NC__" or net is None:
                if pos_key not in seen_pos:
                    parts.append(no_connect(px, py))
                    seen_pos.add(pos_key)
            else:
                if pos_key not in seen_pos:
                    parts.append(label(net, px, py, label_angle(p["rot"])))
                    seen_pos.add(pos_key)

    # --- Netz-Kuerzel fuer Wiederholungen ---
    V3, GND, VBAT, VBUS = "+3V3", "GND", "VBAT", "VBUS"

    # ================= Power-Block (links) =================
    place("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C",
          "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", 40, 70, {
              "A1": GND, "A12": GND, "B1": GND, "B12": GND, "SH": GND,
              "A4": VBUS, "A9": VBUS, "B4": VBUS, "B9": VBUS,
              "A5": "CC1", "B5": "CC2",
              "A6": "USB_DP", "B6": "USB_DP",
              "A7": "USB_DN", "B7": "USB_DN",
              "A8": None, "B8": None,
          })
    place("R1", "Device:R", "5.1k", "Resistor_SMD:R_0402_1005Metric", 70, 95,
          {"1": "CC1", "2": GND})
    place("R2", "Device:R", "5.1k", "Resistor_SMD:R_0402_1005Metric", 80, 95,
          {"1": "CC2", "2": GND})

    place("U9", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6",
          "Package_TO_SOT_SMD:SOT-23-6", 90, 60, {
              "1": "USB_DN", "6": "USB_DN",
              "3": "USB_DP", "4": "USB_DP",
              "5": VBUS, "2": GND,
          })

    place("U7", "aurabip:MCP73831", "MCP73831-2", "Package_TO_SOT_SMD:SOT-23-5",
          130, 45, {
              "4": VBUS, "3": VBAT, "2": GND, "5": "PROG", "1": "CHG_STAT",
          })
    place("R11", "Device:R", "2k", "Resistor_SMD:R_0402_1005Metric", 155, 60,
          {"1": "PROG", "2": GND})
    place("R6", "Device:R", "1k", "Resistor_SMD:R_0402_1005Metric", 165, 35,
          {"1": VBUS, "2": "CHG_LED_A"})
    place("D1", "Device:LED", "LED grn", "LED_SMD:LED_0603_1608Metric", 175, 45,
          {"2": "CHG_LED_A", "1": "CHG_STAT"})

    place("SW1", "Switch:SW_SPDT", "EIN/AUS", "Button_Switch_SMD:SW_SPDT_PCM12",
          130, 80, {"1": VBAT, "2": "LDO_EN", "3": GND})
    # ME6217C33M5G: pinkompatibel zu AP2112K (Symbol wiederverwendet)
    place("U8", "Regulator_Linear:AP2112K-3.3", "ME6217C33M5G",
          "Package_TO_SOT_SMD:SOT-23-5", 165, 80, {
              "1": VBAT, "3": "LDO_EN", "2": GND, "5": V3, "4": None,
          })
    place("C2", "Device:C", "10u", "Capacitor_SMD:C_0603_1608Metric", 150, 100,
          {"1": VBAT, "2": GND})
    place("C3", "Device:C", "10u", "Capacitor_SMD:C_0603_1608Metric", 185, 100,
          {"1": V3, "2": GND})
    place("C12", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 120, 100,
          {"1": VBUS, "2": GND})
    place("C13", "Device:C", "4.7u", "Capacitor_SMD:C_0603_1608Metric", 135, 100,
          {"1": VBAT, "2": GND})

    place("J2", "Connector_Generic:Conn_01x02", "AKKU LiPo",
          "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", 205, 60,
          {"1": VBAT, "2": GND})

    # VBAT-Teiler fuer ADC
    place("R9", "Device:R", "1M", "Resistor_SMD:R_0402_1005Metric", 225, 80,
          {"1": VBAT, "2": "VBAT_SENSE"})
    place("R10", "Device:R", "1M", "Resistor_SMD:R_0402_1005Metric", 225, 95,
          {"1": "VBAT_SENSE", "2": GND})
    place("C11", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 235, 95,
          {"1": "VBAT_SENSE", "2": GND})

    # ================= MCU (Mitte) =================
    place("U1", "RF_Module:ESP32-S3-MINI-1", "ESP32-S3-MINI-1-N8",
          "RF_Module:ESP32-S2-MINI-1", 90, 180, {
              "3": V3, "45": "ESP_EN",
              "4": "BTN_BOOT", "5": "VBAT_SENSE", "6": "LED_STATUS",
              "7": "LORA_DIO1",
              "8": "I2S_BCLK", "9": "I2S_LRCK", "10": "I2S_DOUT",
              "11": "AMP_SD", "12": "I2C_SDA", "13": "I2C_SCL",
              "14": "IMU_INT1",
              # SPI2 geteilt: LoRa (E22) + OLED (SSD1327), je eigener CS
              "15": "SPI2_MOSI", "16": "SPI2_SCK", "17": "SPI2_MISO",
              "18": "LORA_BUSY", "19": "LORA_RST", "20": "LORA_TXEN",
              "25": "LORA_NSS", "33": "LORA_RXEN",
              "28": "OLED_CS", "29": "OLED_DC", "31": "OLED_RST",
              "21": "GNSS_TXD", "22": "GNSS_RXD",
              "23": "USB_DN", "24": "USB_DP",
              "34": "TP_IO38", "36": "TP_IO40", "37": "TP_IO41", "38": "TP_IO42",
              "1": GND, "2": GND, "42": GND, "43": GND,
              **{str(n): GND for n in range(46, 66)},
          })

    place("C1", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 40, 130,
          {"1": V3, "2": GND})
    place("R5", "Device:R", "10k", "Resistor_SMD:R_0402_1005Metric", 40, 145,
          {"1": V3, "2": "ESP_EN"})
    place("C10", "Device:C", "1u", "Capacitor_SMD:C_0402_1005Metric", 50, 145,
          {"1": "ESP_EN", "2": GND})
    place("SW2", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
          30, 160, {"1": "ESP_EN", "2": GND})
    place("SW3", "Switch:SW_Push", "BOOT/USER", "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2",
          30, 175, {"1": "BTN_BOOT", "2": GND})
    place("R7", "Device:R", "1k", "Resistor_SMD:R_0402_1005Metric", 30, 195,
          {"1": "LED_STATUS", "2": "LED2_A"})
    place("D2", "Device:LED", "LED blau", "LED_SMD:LED_0603_1608Metric", 30, 210,
          {"2": "LED2_A", "1": GND})

    # Testpads
    for i, (tp, net) in enumerate([("TP1", "TP_IO38"), ("TP2", "TP_IO40"),
                                    ("TP3", "TP_IO41"), ("TP4", "TP_IO42")]):
        place(tp, "Connector_Generic:Conn_01x01", "TP",
              "TestPoint:TestPoint_Pad_1.5x1.5mm", 40 + i * 15, 240,
              {"1": net})

    # ================= Sensorik (rechts oben) =================
    place("U2", "aurabip:BMP581", "BMP581", "aurabip:BMP581_LGA-10_2x2mm",
          260, 130, {
              "10": V3, "1": V3, "5": V3, "6": V3,
              "2": "I2C_SCL", "4": "I2C_SDA",
              "3": GND, "8": GND, "9": GND, "7": None,
          })
    place("C4", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 285, 130,
          {"1": V3, "2": GND})

    place("U3", "aurabip:LSM6DSO32", "LSM6DSO32", "Package_LGA:Bosch_LGA-14_3x2.5mm_P0.5mm",
          260, 170, {
              "8": V3, "5": V3, "12": V3, "1": GND,
              "13": "I2C_SCL", "14": "I2C_SDA", "4": "IMU_INT1",
              "9": None, "2": None, "3": None, "10": None, "11": None,
              "6": GND, "7": GND,
          })
    place("C5", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 290, 170,
          {"1": V3, "2": GND})

    place("U4", "Sensor_Humidity:SHT4x", "SHT40-AD1B",
          "Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
          260, 205, {
              "3": V3, "4": GND, "1": "I2C_SDA", "2": "I2C_SCL",
          })
    place("C6", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 285, 205,
          {"1": V3, "2": GND})

    place("R3", "Device:R", "4.7k", "Resistor_SMD:R_0402_1005Metric", 310, 130,
          {"1": V3, "2": "I2C_SDA"})
    place("R4", "Device:R", "4.7k", "Resistor_SMD:R_0402_1005Metric", 320, 130,
          {"1": V3, "2": "I2C_SCL"})

    # OLED: Waveshare 1.32" 128x96 SSD1327 ueber SPI, Anschluss per
    # PH2.0-8-Pin-Kabel (liegt dem Modul bei). Display haengt am Kabel
    # -> frei im Gehaeusedeckel positionierbar.
    # ⚠️ T-H9: Pin-Reihenfolge des Waveshare-Kabels bei Lieferung pruefen!
    place("J4", "Connector_Generic:Conn_01x08", "OLED WS 1.32 SPI",
          "Connector_JST:JST_PH_B8B-PH-K_1x08_P2.00mm_Vertical", 310, 170, {
              "1": V3, "2": GND, "3": "SPI2_MOSI", "4": "SPI2_SCK",
              "5": "OLED_CS", "6": "OLED_DC", "7": "OLED_RST", "8": None,
          })

    # ================= GNSS (rechts unten) =================
    place("U5", "aurabip:L96", "Quectel L96", "aurabip:Quectel_L96",
          260, 250, {
              "8": V3, "6": V3,
              "9": "GNSS_TXD", "10": "GNSS_RXD",
              "4": None, "2": None, "5": None, "11": None,
              "1": GND, "3": GND, "7": GND, "12": GND,
          })
    place("C7", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 295, 250,
          {"1": V3, "2": GND})

    # ================= FANET/LoRa (E22-900M22S) =================
    place("U10", "aurabip:E22_900M22S", "E22-900M22S", "aurabip:E22_900M22S",
          335, 250, {
              "11": V3, "10": "LORA_RST",
              "19": "LORA_NSS", "18": "SPI2_SCK", "17": "SPI2_MOSI",
              "16": "SPI2_MISO", "15": "LORA_BUSY", "14": "LORA_DIO1",
              "6": "LORA_TXEN", "7": "LORA_RXEN",
              "3": "LORA_ANT",
              "1": GND, "2": GND, "12": GND, "20": GND,
          })
    place("C14", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 360, 235,
          {"1": V3, "2": GND})
    place("C15", "Device:C", "10u", "Capacitor_SMD:C_0603_1608Metric", 370, 235,
          {"1": V3, "2": GND})
    place("J5", "Connector:Conn_Coaxial", "u.FL 868",
          "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", 370, 250, {
              "1": "LORA_ANT", "2": GND,
          })

    # ================= Audio =================
    place("U6", "aurabip:MAX98357A", "MAX98357A",
          "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.75x1.75mm", 150, 250, {
              "2": "I2S_BCLK", "1": "I2S_LRCK", "3": "I2S_DOUT",
              "5": "AMP_SD", "4": None,
              "13": VBAT, "9": "SPK_P", "11": "SPK_N",
              "8": GND, "17": GND,
          })
    place("R8", "Device:R", "100k", "Resistor_SMD:R_0402_1005Metric", 120, 270,
          {"1": V3, "2": "AMP_SD"})
    place("C8", "Device:C", "22u", "Capacitor_SMD:C_0805_2012Metric", 180, 270,
          {"1": VBAT, "2": GND})
    place("C9", "Device:C", "100n", "Capacitor_SMD:C_0402_1005Metric", 190, 270,
          {"1": VBAT, "2": GND})
    place("J3", "Connector_Generic:Conn_01x02", "LAUTSPRECHER 8R 1W",
          "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", 200, 250,
          {"1": "SPK_P", "2": "SPK_N"})

    # ================= PWR_FLAGs =================
    flag_pins = pin_cache["power:PWR_FLAG"]
    fp0 = flag_pins[0]
    # VBAT/+3V3 haben schon power_out-Treiber (Lader/LDO) -> kein Flag noetig
    for i, net in enumerate([GND, VBUS]):
        fx = snap(40 + i * 25)
        fy = snap(275)
        parts.append(comp(f"#FLG0{i+1}", "power:PWR_FLAG", "PWR_FLAG", "", fx, fy,
                          in_bom=False))
        px = fx + fp0["x"]
        py = fy - fp0["y"]
        parts.append(label(net, px, py, 0))

    # ---- Datei zusammenbauen ----
    lib_symbols_block = "  (lib_symbols\n" + "\n".join(lib_blocks) + "\n  )"
    body = "\n".join(parts)
    sch = f"""(kicad_sch
  (version 20231120)
  (generator "aurabip_gen")
  (generator_version "1.0")
  (uuid "{SHEET_UUID}")
  (paper "A3")
  (title_block
    (title "AuraBip audio v0.1")
    (company "KIE Engineering")
    (comment 1 "BLE-Vario, Serienprodukt — proprietaer")
    (comment 2 "Pinnummern L96/MAX98357A/LSM6DSO32: siehe VERIFY-Tickets in BOM.md")
  )
{lib_symbols_block}
{body}
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""
    os.makedirs(PROJECT_DIR, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(sch)

    # Minimales Projektfile (kicad-cli liest Projekt-Lib-Tables nur damit)
    pro_path = os.path.join(PROJECT_DIR, "aurabip.kicad_pro")
    if not os.path.exists(pro_path):
        with open(pro_path, "w", encoding="utf-8") as f:
            f.write('{\n  "meta": { "filename": "aurabip.kicad_pro", "version": 3 },\n'
                    '  "schematic": { "legacy_lib_dir": "", "legacy_lib_list": [] }\n}\n')

    # Lib-Tables, damit KiCad die aurabip-Bibliotheken findet
    with open(os.path.join(PROJECT_DIR, "sym-lib-table"), "w", encoding="utf-8") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                '  (lib (name "aurabip")(type "KiCad")'
                '(uri "${KIPRJMOD}/../lib/aurabip.kicad_sym")(options "")(descr "AuraBip eigene Symbole"))\n)\n')
    with open(os.path.join(PROJECT_DIR, "fp-lib-table"), "w", encoding="utf-8") as f:
        f.write('(fp_lib_table\n  (version 7)\n'
                '  (lib (name "aurabip")(type "KiCad")'
                '(uri "${KIPRJMOD}/../lib/aurabip.pretty")(options "")(descr "AuraBip eigene Footprints"))\n)\n')
    print(f"Schema geschrieben: {OUTPUT}")
    print(f"  {len(parts)} Elemente, {len(lib_blocks)} Bibliothekssymbole")


if __name__ == "__main__":
    generate()
