# AuraBip — BLE-Vario auf Heltec V4 (Arbeitstitel)

Minimalistisches BLE-Vario im Stodeus-Stil: Heltec WiFi LoRa 32 V4 + GNSS +
BMP581 + LSM6DSO32 + SHT40. OLED zeigt nur das Nötigste, maximal gross.
Zwei Varianten: **silent** (BLE+Display) und **audio** (I2S-Verstärker,
Vario-Ton + Sprachansagen).

© 2026 KIE Engineering. Proprietär. Clean-Room-Regel wie WindBuddy:
kein Code aus GPL/CC-BY-NC-Projekten (GXAirCom, SoftRF, etc.).
Erlaubt: RadioLib/NimBLE/U8g2 als Bibliotheken (MIT/BSD), öffentliche
Protokoll-Spezifikationen (LK8EX1, NMEA).

## Kernidee "Instant Vario"

Reines Baro-Vario ist träge und böenempfindlich. Die Franzosen (Stodeus)
koppeln deshalb Beschleunigungssensor + Barometer. Wir machen dasselbe:
Kalman-Filter mit BMP581 (Messung, ~50 Hz) + LSM6DSO32 Vertikal-
beschleunigung (Prädiktion, ~200 Hz). Ergebnis: Ansprechzeit <100 ms statt
~1 s, ohne Zappeln.

## BLE-Protokoll (Kompatibilität zu XCTrack / XCSoar / SkyDrop-Apps)

Nordic UART Service (NUS), Notify-Stream mit:
- `$LK8EX1,<press_Pa>,<alt_m>,<vario_cm_s>,<temp_C>,<batt>*CS` — 5 Hz
- NMEA `$GPGGA` / `$GPRMC` Passthrough vom GNSS — 1 Hz
⚠️ VERIFY: LK8EX1-Feldreihenfolge/Checksumme gegen offizielle Doku (T1).

## Display-Philosophie

128×64 OLED, eine einzige Ansicht im Flug:
```
+----------------------+
|  +2.4          ← Vario, riesig (32 px Ziffern)
|  1847 m   34 km/h    ← Alt + GPS-Speed, klein
+----------------------+
```
Kein Menü im Flug. Konfiguration über BLE (BipLink-Prinzip) — Ticket T5.

## Audio-Variante — Realitätscheck

"High Quality Sprach- und Varioton" geht NICHT über den nackten Piezo.
Stodeus-Qualität heisst: richtiger Lautsprecher + Verstärker.
Unser Weg: **MAX98357A I2S-Amp (~3 CHF) + 1 W / 8 Ω Lautsprecher 20–28 mm**.
- Varioton: Synthese direkt auf dem S3 (Sinus/Rechteck, Tonhöhe+Rate aus Vz)
- Sprache: WAV-Samples (16 kHz mono) im 16-MB-Flash — Ansagen Höhe/Speed/
  Steigen auf Doppeltipp (IMU-Tap-Detection des LSM6DSO32, kein Taster nötig!)
Samples: selbst mit TTS generieren (de/en/es — es für Kolumbien 😉).

## Hardware-Verkabelung (v0.1 Prototyp)

| Signal | Heltec V4 Pin | Anmerkung |
|---|---|---|
| I2C SDA/SCL | 17 / 18 (⚠️ VERIFY am V4-Schema) | BMP581 0x47, LSM6DSO32 0x6A, SHT40 0x44 — Ivos Standard-Map |
| GNSS | SH1.25-8P Connector | ⚠️ VERIFY Pinout/UART lt. V4-Doku (T2) |
| OLED | onboard | SSD1306 128×64 |
| I2S (audio) | BCLK/LRCK/DIN frei wählen | in config.h |

## Strategie-Notiz

Hardware-Kosten ~35–45 CHF (Board+Sensoren+GNSS). Als Bausatz das perfekte
Einstiegsprodukt unterhalb der Aura Krücke — und der SX1262 ist ja onboard:
FANET-Upgrade per Firmware-Update ist der eingebaute Upsell (v2).
