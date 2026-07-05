# AuraBip audio — BOM v0.1 (Serienprodukt)

© 2026 KIE Engineering. Proprietär.

Ziel: kompaktes BLE-Vario mit Sprach-/Tonausgabe, ~35×48 mm, 4-Lagen-PCB,
JLCPCB-Fertigung (SMT-Bestückung ab Rolle wo möglich).
Alle LCSC-Nummern sind ⚠️ **vor Bestellung zu verifizieren** (Verfügbarkeit dreht schnell).

## Kern

| Ref | Bauteil | Package | Funktion | LCSC (⚠️ prüfen) | ~Preis (1 Stk) |
|---|---|---|---|---|---|
| U1 | **ESP32-S3-MINI-1-N8** | Modul 15.4×15.4 | MCU, BLE 5, natives USB (kein UART-Bridge-Chip nötig), FCC/CE-zertifiziert | C2913204 | 3.20 CHF |
| U2 | **BMP581** | LGA-10 2×2 | Barometer 50 Hz (Kalman-Update), Adr 0x47 | TBD | 2.50 CHF |
| U3 | **LSM6DSO32XTR** | LGA-14 2.5×3 | IMU ±32 g, 200 Hz Prädiktion + Tap-Detection, Adr 0x6A | TBD | 2.80 CHF |
| U4 | **SHT40-AD1B** | DFN-4 1.5×1.5 | Temp/Feuchte, Adr 0x44 | TBD | 1.80 CHF |
| U5 | **Quectel L96-M33** | LCC 14×15 | GNSS MT3333, **integrierte Patch-Antenne** (kein RF-Design-Risiko), 1 Hz NMEA | TBD | 6.50 CHF |
| U6 | **MAX98357AETE+T** | TQFN-16-EP 3×3 | I2S-DAC+3.2W-Class-D-Amp, läuft direkt an VBAT | TBD | 2.20 CHF |

## Power

| Ref | Bauteil | Package | Funktion | LCSC (⚠️ prüfen) | ~Preis |
|---|---|---|---|---|---|
| U10 | **Ebyte E22-900M22S** | Modul 16×26 | SX1262 + TCXO + PA, FANET-TX (Typ 1) → OGN-Sichtbarkeit (Pflicht ab 2027). TX-Leistung in FW hart auf 14 dBm ERP begrenzt | TBD | 5.50 CHF |
| J5 | **u.FL / IPEX** Buchse | SMD | 868-MHz-Antenne (Flexantenne intern im Gehäuse, ~1 CHF) | TBD | 0.40 CHF |
| U7 | **MCP73831T-2ACI/OT** | SOT-23-5 | LiPo-Lader 1 Zelle, 500 mA (R_PROG 2 kΩ) | C424093 | 0.60 CHF |
| U8 | **ME6217C33M5G** | SOT-23-5 | LDO 3.3 V / **800 mA** (ESP32-BLE-Peak + LoRa-TX + GNSS gleichzeitig; Amp hängt an VBAT). Pinkompatibel zu AP2112K | C82942 (⚠️) | 0.20 CHF |
| U9 | **USBLC6-2SC6** | SOT-23-6 | USB-ESD-Schutz | C7519 | 0.20 CHF |
| J1 | **TYPE-C-31-M-12** (HRO) | USB-C 16P | Laden + Flashen (USB-CDC/DFU) | C165948 | 0.25 CHF |
| J2 | **JST PH 2P** (S2B-PH-K-S) | THT gewinkelt | Akku-Anschluss | TBD | 0.10 CHF |
| BAT | **EEMB LP603450** LiPo 3.7 V 1000–1100 mAh, 34.5×52×6.3 mm, **mit Schutzschaltung** + JST-PH-2.0-Stecker | extern, unter dem 52×52-Board | ~7 h Laufzeit bei ~140 mA Mix; ⚠️ **POLARITÄT am Stecker prüfen** — bei LiPo-Herstellern nicht genormt! | Amazon/EEMB ~8 CHF | 8.00 CHF |
| SW1 | **MSK-12C02** | Schiebeschalter | Ein/Aus (schaltet nur LDO-EN, nicht VBAT — Laden geht auch „aus") | TBD | 0.15 CHF |

## Audio & UI

| Ref | Bauteil | Package | Funktion | LCSC (⚠️ prüfen) | ~Preis |
|---|---|---|---|---|---|
| LS1/J3 | **Visaton K 28 WP** (28 mm, 8 Ω, 1 W, spritzwassergeschützte Kunststoffmembran) an JST-PH-Pigtail | — | Varioton + Sprache; WP-Variante wegen Outdoor-Einsatz | Voelkner/RS/Reichelt ~4 CHF | 4.00 CHF |
| J4 | **JST-PH 8-Pin vertikal** (B8B-PH-K-S) + **Waveshare 1.32" OLED** 128×96, 16 Graustufen, SSD1327, SPI | Kabel (liegt Modul bei) | Kein Header — Modul hat **PH2.0-Buchse**, Kabel im Lieferumfang → Display frei im Gehäusedeckel platzierbar. Teilt SPI2 mit E22 (eigener CS); −20…70 °C. T-H9: Kabel-Pinreihenfolge bei Lieferung prüfen | Waveshare/Amazon ~12 CHF | 12.00 CHF |
| SW2 | Taster **RESET** (EN) | SMD 3.9×2.9 | Neustart | TBD | 0.05 CHF |
| SW3 | Taster **BOOT/USER** (GPIO0) | SMD 3.9×2.9 | Strapping + Nutzertaste im Betrieb (Doppeltipp macht die IMU) | TBD | 0.05 CHF |
| D1 | LED grün + R 1 kΩ | 0603 | Lade-Status (MCP73831 STAT) | — | 0.03 CHF |
| D2 | LED blau + R 1 kΩ | 0603 | Status (GPIO2) | — | 0.03 CHF |

## Passiv (0402, JLC Basic Parts)

| Menge | Wert | Funktion |
|---|---|---|
| 2× | 5.1 kΩ | USB-C CC1/CC2 |
| 2× | 4.7 kΩ | I2C-Pullups SDA/SCL |
| 1× | 2 kΩ | MCP73831 PROG (500 mA) |
| 2× | 1 MΩ | VBAT-ADC-Teiler (GPIO1) |
| 1× | 100 kΩ | Amp SD_MODE-Pullup auf 3V3 (aus, wenn 3V3 aus) |
| 1× | 10 kΩ | EN-Pullup (RESET) |
| 8× | 100 nF | Abblock je IC |
| 2× | 10 µF | LDO in/out |
| 1× | 22 µF (0805) | Amp-VBAT-Puffer |
| 1× | 100 nF | ADC-Teiler-Filter |

**Summe Elektronik: ~31 CHF/Stk** (Kleinserie 50 Stk, ohne PCB/Bestückung/Akku/Gehäuse).
PCB+SMT bei JLC (50 Stk, 4-Lagen): ~9 CHF/Board. Akku 802030: ~3 CHF. Antenne 868: ~1 CHF. → **~44 CHF Material.**

## Bewusste Entscheidungen

- **FANET-TX drin** (Änderung 2026-07-03): Elektronische Sichtbarkeits-Pflicht (FLARM/FANET/OGN) ab 2027 → SX1262-Modul E22-900M22S. **Nur TX** (Tracking Typ 1, FANET→OGN), keine Warnlogik — Warnquellen-Philosophie bleibt. FANET-Encoder aus WindBuddy `lib/fanet` (eigener Clean-Room-Code) wiederverwenden. Modul statt nacktem SX1262: TCXO (Frequenzstabilität bei Kälte!) + fertiges RF-Frontend.
- **Kein USB-UART-Chip**: ESP32-S3 natives USB (GPIO19/20) für Flashen + CDC-Logs.
- **Kein Fuel-Gauge** (v1): VBAT-Teiler an ADC reicht für %-Anzeige. v2-Option: MAX17048.
- **Kein Power-Path** (v1): MCP73831 lädt, System zieht parallel an VBAT. Bekannte Schwäche: Terminierung bei Last ungenau. v2-Option: BQ24074.
- **L96 mit integrierter Antenne** statt ATGM336H+Antenne: teurer, aber null RF-Layout-Risiko und kleiner als Patch+Pigtail.
- **Amp an VBAT**: Audio-Peaks (~1 A kurz) gehen nicht durch den 600-mA-LDO. SD_MODE-Pullup an 3V3 schaltet den Amp mit aus.

## ⚠️ VERIFY vor Fertigungsfreigabe

1. Alle LCSC-Nummern + Lagerbestand (T-H1)
2. L96-Padout gegen Quectel-Hardware-Design-Guide (T-H2)
3. MAX98357A Exposed-Pad-Maß auf TQFN-Footprint (T-H3)
4. LSM6DSO32-Pinout gegen ST-Datenblatt (T-H4)
5. Antennen-Keepouts: ESP32-MINI-Antenne über Boardkante, L96-Patch braucht GND-Fläche darunter lt. Quectel (T-H5)
6. USB-C-Orientierung: Steckeröffnung muss über die Boardkante ragen (T-H6)
7. **E22-900M22S-Padout** (Pinnummern + Rastermass) gegen Ebyte-Datenblatt; RXEN/TXEN mit RadioLib setRfSwitchPins (T-H7)
8. Regulatorik FANET-TX: 14 dBm ERP inkl. Antennengewinn, Duty Cycle fürs Tracking-Intervall (T-H8)
