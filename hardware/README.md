# AuraBip audio — Hardware v0.1 (Serienprodukt)

© 2026 KIE Engineering. Proprietär.

Kompaktes BLE-Vario mit Ton-/Sprachausgabe **und FANET-TX** (Sichtbarkeits-
pflicht ab 2027, FANET→OGN): **36×52 mm, 4 Lagen, doppelseitig bestückt**.
Vorderseite: MCU, Sensorik, GNSS, Audio, Power. Rückseite: E22-900M22S
(SX1262) + u.FL-Antennenbuchse. OLED-Modul gesteckt über der Vorderseite,
Akku (LiPo 802030) und Lautsprecher extern per JST-PH.

## Struktur

```
hardware/
  BOM.md          Stückliste + bewusste Design-Entscheide + VERIFY-Tickets
  PINMAP.md       GPIO-Zuordnung, Power-Topologie, komplette Netzliste
  lib/            aurabip.kicad_sym + aurabip.pretty (eigene Symbole/Footprints)
  project/        aurabip.kicad_sch / aurabip.kicad_pcb (generiert!)
  scripts/        generate_schematic.py / generate_pcb.py / symlib.py
  route/          FreeRouting-Pipeline (fanout -> DSN -> route -> import -> DRC)
```

**Alles generiert:** Schema und PCB entstehen aus den Python-Skripten —
Änderungen bitte dort machen und neu generieren, nicht im GUI editieren
(sonst divergiert die Quelle der Wahrheit). Workflow:

```powershell
# 1. Schema (schreibt auch lib/aurabip.kicad_sym + Lib-Tables)
& "C:\Program Files\KiCad\10.0\bin\python.exe" scripts\generate_schematic.py
# 2. ERC
& "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe" sch erc project\aurabip.kicad_sch
# 3. PCB (Platzierung + Zonen, ohne Tracks; zieht Netzliste aus dem Schema)
& "C:\Program Files\KiCad\10.0\bin\python.exe" scripts\generate_pcb.py
# 4. Routing + DRC
powershell -File route\run_autoroute.ps1   # -> project\aurabip_routed.kicad_pcb
```

## Floorplan (Blick von oben)

```
+--------------------------------+
|      L96 GNSS (Patch oben)     |  <- Antenne Richtung Himmel
|                        [AKKU]  |
| ESP32-S3    BMP581  SHT40      |
| (Antenne    LSM6DSO32   [OLED- |
|  -> links)  Pullups      Hdr]  |
| LDO  Teiler  MAX98357A         |
| SW1  USBLC6  Lader  [SPEAKER]  |
| [RST] USB-C [BOOT]  Testpads   |
+--------------------------------+
```

- **ESP32-Antenne**: linke Kante, Kupfer-Keepout auf allen Lagen (x 0–6.0, y 17.7–34.3)
- **L96-Patch**: obere Kante, GND-Lage bleibt darunter (Quectel-Empfehlung, VERIFY T-H5)
- **BMP581/SHT40**: nahe Boardkante; fürs Gehäuse Druckausgleichs-/Lüftungsöffnung vorsehen
- **Rückseite**: E22-900M22S mittig (Handbestückung), u.FL darunter — 868-Flexantenne
  im Gehäuse verlegen, weg von GNSS-Patch und BLE-Antenne (T-H8)
- Lagen: F=Signal+GND-Pour, In1=GND, In2=+3V3, B=Signal+GND-Pour

## Fertigung

- JLCPCB 4-Lagen, 1.6 mm, min. Track/Clearance 0.10 mm (Via 0.5/0.3),
  Bohrloch→Kupfer 0.2 mm — Standardprozess (T-H1 verifizieren)
- SMT-Bestückung (Vorderseite): alle Passiven 0402/0603 aus JLC-Basic-Sortiment
- Handbestückung: L96, JST-Stecker, OLED-Header, Rückseite (E22, u.FL, C14/C15)

## Firmware-Anpassung

Serien-Board ≠ Heltec-Prototyp — `src/config.h` braucht die Pin-Werte aus
[PINMAP.md](PINMAP.md) (I2C 8/9, GNSS 17/18, I2S 4/5/6, neu: AMP_SD 7,
VBAT_ADC 1, LED 2, BTN 0, LoRa-SPI 21/12/11/13 + BUSY 14/DIO1 3/RST 15/
TXEN 16/RXEN 37; OLED auf dem Sensorbus, kein Vext).

**FANET-TX**: Encoder aus WindBuddy `lib/fanet` übernehmen (eigener
Clean-Room-Code, Tracking Typ 1 statt Wetter Typ 4). RadioLib mit
`setRfSwitchPins(RXEN, TXEN)`. TX-Leistung hart ≤ 14 dBm ERP (T-H8),
nur im Flug senden, Adresse/Manufacturer wie WindBuddy-Konvention.

## Offene VERIFY-Tickets (vor Bestellung!)

| Ticket | Was |
|---|---|
| T-H1 | LCSC-Nummern + Lagerbestand aller Positionen |
| T-H2 | **L96-Padout** gegen Quectel Hardware Design Guide (Footprint ist Annahme!) |
| T-H3 | MAX98357A: TQFN-Pinnummern + Exposed-Pad-Maß gegen Maxim-Datenblatt |
| T-H4 | LSM6DSO32-Pinout (INT1=Pin 4?) gegen ST-Datenblatt |
| T-H5 | Antennen-Regeln: ESP32-Keepout-Maße + GND unter L96-Patch |
| T-H6 | USB-C-Footprint-Orientierung: Stecker muss über die Boardkante ragen |
