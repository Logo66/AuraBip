"""PCBWay-Bestueckungs-BOM (CSV) aus der Schema-Netzliste erzeugen.

MPN-Zuordnung pro Referenz — ⚠️ Positionen mit VERIFY-Vermerk vor der
Bestellung gegen Datenblatt/Verfuegbarkeit pruefen (T-H1..T-H9)!
"""

import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from symlib import parse

HW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
SCH = os.path.join(HW, "project", "aurabip.kicad_sch")
OUT = os.path.join(HW, "production", "aurabip-bom.csv")

# Ref -> (MPN, Hersteller, Beschreibung) — englisch, PCBWay liest das
MPN = {
    "U1":  ("ESP32-S3-MINI-1-N8", "Espressif", "WiFi/BLE module, 8MB flash"),
    "U2":  ("BMP581", "Bosch", "Barometric pressure sensor LGA-10 - open port, do NOT wash"),
    "U3":  ("LSM6DSO32XTR", "ST", "IMU +/-32g LGA-14"),
    "U4":  ("SHT40-AD1B-R2", "Sensirion", "Temp/humidity sensor DFN-4"),
    "U5":  ("L96-M33", "Quectel", "GNSS module with integrated antenna"),
    "U6":  ("MAX98357AETE+T", "Analog Devices", "I2S Class-D amplifier TQFN-16"),
    "U7":  ("MCP73831T-2ACI/OT", "Microchip", "LiPo charger SOT-23-5"),
    "U8":  ("ME6217C33M5G", "MicrOne", "LDO 3.3V 800mA SOT-23-5"),
    "U9":  ("USBLC6-2SC6", "ST", "USB ESD protection SOT-23-6"),
    "U10": ("E22-900M22S", "Ebyte", "SX1262 LoRa module, stamp holes, bottom side"),
    "J1":  ("TYPE-C-31-M-12", "HRO", "USB-C receptacle 16P"),
    "J2":  ("S2B-PH-K-S", "JST", "Battery connector PH 2.0 2P, THT"),
    "J3":  ("S2B-PH-K-S", "JST", "Speaker connector PH 2.0 2P, THT"),
    "J4":  ("B8B-PH-K-S", "JST", "OLED connector PH 2.0 8P vertical, THT"),
    "SW1": ("MSK-12C02", "Shouhan", "Slide switch"),
    "SW2": ("KMR221GLFS", "C&K", "Tactile switch RESET"),
    "SW3": ("KMR221GLFS", "C&K", "Tactile switch BOOT"),
    "D1":  ("19-217/GHC-YR1S2/3T", "Everlight", "LED green 0603"),
    "D2":  ("19-217/BHC-ZL1M2RY/3T", "Everlight", "LED blue 0603"),
}

# Wert-basierte Zuordnung fuer Passiva (alle 0402/0603/0805 Basic Parts)
# Englische Spec-Beschreibungen — PCBWay matcht Passive darueber
PASSIVE_DESC = {
    "R": "Chip Resistor 1%", "C": "MLCC Capacitor X7R 16V",
}


def load_components():
    net_file = os.path.join(HW, "project", "aurabip_bom.net")
    subprocess.run([KICAD_CLI, "sch", "export", "netlist", "--format",
                    "kicadsexpr", "-o", net_file, SCH],
                   check=True, capture_output=True)
    tree = parse(open(net_file, encoding="utf-8").read())

    def atom(x):
        return x[1:] if isinstance(x, str) and x.startswith('"') else x

    comps = []

    def walk(node):
        if isinstance(node, list) and node and node[0] == "comp":
            ref = val = fp = None
            for sub in node:
                if isinstance(sub, list):
                    if sub[0] == "ref":
                        ref = atom(sub[1])
                    elif sub[0] == "value":
                        val = atom(sub[1])
                    elif sub[0] == "footprint":
                        fp = atom(sub[1])
            if ref and not ref.startswith("#"):
                comps.append((ref, val, fp or ""))
        elif isinstance(node, list):
            for sub in node:
                walk(sub)

    walk(tree)
    return comps


def main():
    comps = load_components()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    # Gruppieren: gleiche (Wert, Footprint, MPN) -> eine Zeile
    BACK_REFS = {"U10", "J5", "C14", "C15"}
    groups = {}
    for ref, val, fp in comps:
        mpn, mfr, desc = MPN.get(ref, ("", "", ""))
        if not mpn:
            pkg = fp.split(":")[-1]
            desc = f"{PASSIVE_DESC.get(ref[0], val)} {val} {pkg}"
        side = "Bottom" if ref in BACK_REFS else "Top"
        key = (val, fp, mpn, side)
        groups.setdefault(key, {"refs": [], "mfr": mfr, "desc": desc, "side": side})
        groups[key]["refs"].append(ref)

    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Qty", "MPN", "Manufacturer",
                    "Description", "Footprint", "Side"])
        for (val, fp, mpn, side), g in sorted(groups.items(), key=lambda kv: kv[1]["refs"][0]):
            w.writerow([",".join(sorted(g["refs"])), len(g["refs"]), mpn,
                        g["mfr"], g["desc"], fp.split(":")[-1], side])
    print(f"BOM geschrieben: {OUT} ({len(groups)} Positionen)")


if __name__ == "__main__":
    main()
