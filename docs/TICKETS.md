# AuraBip — Tickets (Claude Code)

Clean-Room-Regel wie WindBuddy gilt. Kein GXAirCom/SoftRF-Code anschauen.

## T1 — LK8EX1 & BLE-Kompatibilität (BLOCKER)
- LK8EX1-Spez beschaffen, Feldkonventionen verifizieren (Batteriefeld!)
- Test gegen XCTrack auf Ivos Handy: verbindet, zeigt Baro-Alt + Vario + GPS?
- BLE-Name/Advertising so, dass XCTrack das Gerät als "BLE Sensor" findet
- DoD: XCTrack fliegt komplett mit AuraBip-Daten (interner Sensor aus)

## T2 — Sensortreiber & GNSS
- BMP581/LSM6DSO32/SHT40-Treiber aus Aura-Monorepo portieren (eigener Code)
- BMP581: OSR/ODR für 50 Hz rauscharm konfigurieren
- V4 GNSS-Connector-Pinout aus Heltec-Doku verifizieren, MAX-M10S anbinden
- RMC-Parser härten (kein strstr-Gefrickel)
- DoD: sensors::init() erkennt alle drei, Live-Werte plausibel

## T3 — Orientierungsschätzung
- verticalAccelApprox() durch Mahony-Filter (Gyro+Accel) ersetzen,
  echte Erd-Frame-Vertikalbeschleunigung
- Kalman-Tuning im Auto-/Treppenhaus-Test, dann Flug
- DoD: Ansprechzeit < 150 ms, kein Zappeln im Geradeausflug

## T4 — Audio-Ausbau (Variante audio)
- WAV-Player aus LittleFS, Mixer (Ansage über gedämpftem Varioton)
- Tap-Detection LSM6DSO32 (Doppeltipp = Ansage Höhe/Speed)
- Sprachsamples de/en/es generieren (TTS), 16 kHz mono
- Lautstärke-Profil: Start laut, konfigurierbar via BLE
- DoD: Doppeltipp -> saubere Sprachansage ohne Knacken, Ton läuft weiter

## T5 — BLE-Konfigurationskanal
- Zweite NUS-Charakteristik (RX): einfache Key=Value-Kommandos
  (QNH, Lautstärke, Klimm-/Sinkschwellen, Sprachwahl)
- Persistenz in NVS
- DoD: Einstellung überlebt Reboot

## T6 — Strom & Gehäuse
- Light-Sleep-Strategie am Boden (kein Steigen 10 min -> Display dim, IMU-Wakeup)
- Verbrauchsmessung beide Varianten; Ziel: >20 h mit 3000er Zelle
- Ivo: Gehäuse-Design (Druck), Lautsprecheröffnung akustisch (Bassreflex-Schlitz)

## Später / v2
- FANET über den onboard SX1262 (lib/fanet aus WindBuddy wiederverwenden!)
- IGC-Logging in Flash
