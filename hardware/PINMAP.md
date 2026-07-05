# AuraBip audio — Pin-Map & Netzliste v0.1

© 2026 KIE Engineering. Proprietär.

## ESP32-S3-MINI-1 GPIO-Zuordnung

| GPIO | Netz | Funktion | Anmerkung |
|---|---|---|---|
| 0 | BTN_BOOT | Taster BOOT/USER | Strapping; im Betrieb Nutzertaste |
| 1 | VBAT_SENSE | ADC1_CH0, Teiler 1M/1M + 100n | VBAT/2, max 2.15 V ✓ |
| 2 | LED_STATUS | Status-LED (blau) | aktiv high |
| 4 | I2S_BCLK | MAX98357A BCLK | |
| 5 | I2S_LRCK | MAX98357A LRC | |
| 6 | I2S_DOUT | MAX98357A DIN | |
| 7 | AMP_SD | MAX98357A SD_MODE | high = an (mono L+R/2); 100k-Pullup an 3V3 |
| 8 | I2C_SDA | Sensorbus + OLED | 4.7k-Pullup |
| 9 | I2C_SCL | Sensorbus + OLED | 4.7k-Pullup |
| 10 | IMU_INT1 | LSM6DSO32 INT1 | Tap-Detection / Data-Ready |
| 17 | GNSS_RX | ← L96 TXD | UART1 RX |
| 18 | GNSS_TX | → L96 RXD | UART1 TX |
| 19 | USB_DN | USB D− | über USBLC6 |
| 20 | USB_DP | USB D+ | über USBLC6 |
| 3 | LORA_DIO1 | E22 DIO1 (IRQ) | |
| 11 | SPI2_MOSI | E22 MOSI + OLED DIN | geteilter SPI2-Bus |
| 12 | SPI2_SCK | E22 SCK + OLED CLK | geteilter SPI2-Bus |
| 13 | SPI2_MISO | E22 MISO | OLED hat kein MISO |
| 14 | LORA_BUSY | E22 BUSY | |
| 15 | LORA_RST | E22 NRST | |
| 16 | LORA_TXEN | E22 TXEN | RadioLib setRfSwitchPins |
| 21 | LORA_NSS | E22 NSS | SPI CS LoRa |
| 33 | OLED_CS | Display Chip-Select | |
| 34 | OLED_DC | Display Data/Command | |
| 35 | OLED_RST | Display Reset | |
| 37 | LORA_RXEN | E22 RXEN | RadioLib setRfSwitchPins (IO26 ist Flash-reserviert) |
| EN | ESP_EN | RESET-Taster + 10k-Pullup + 1µF | |

Display: 1.5" 128×128 SSD1327 über SPI (U8g2: `U8G2_SSD1327_WS_128X128` o. ä.,
Controller nach Lieferung verifizieren, T-H9). I2C-Bus bleibt nur für Sensorik.

Frei/Reserve: 38–48 → 4 Testpads (TP1–TP4: 38, 40, 41, 42).

**config.h-Änderungen für Serien-Board** (gegenüber Heltec-Prototyp):
`PIN_I2C_SDA 8, PIN_I2C_SCL 9, PIN_GNSS_RX 17, PIN_GNSS_TX 18,
PIN_I2S_BCLK 4, PIN_I2S_LRCK 5, PIN_I2S_DOUT 6` + neu `PIN_AMP_SD 7,
PIN_VBAT_ADC 1, PIN_LED 2, PIN_BTN 0`. OLED auf demselben Bus (0x3C),
kein Vext, kein separater OLED-Bus.

## Stromversorgung

```
USB-C 5V ──┬── MCP73831 ──── VBAT ──┬── JST-PH Akku (802030, 500 mAh)
           │   (500 mA, STAT→LED)   ├── MAX98357A VDD (22µF Puffer)
           └── USBLC6 ── D+/D−      └── SW1 ─→ AP2112K EN
                                            AP2112K: VBAT → 3V3
3V3 ── ESP32-S3, L96 (VCC+V_BCKP), BMP581, LSM6DSO32, SHT40, OLED,
       Pullups (I2C, AMP_SD, EN)
```

- SW1 schaltet nur das LDO-EN gegen VBAT/GND → Laden funktioniert im Aus-Zustand, kein Laststrom über den Schalter.
- Amp ist bei 3V3=aus über SD_MODE (Pullup an 3V3 → low) im Shutdown (<1 µA).
- L96 V_BCKP an 3V3: kein Warmstart nach „Aus" (bewusst — Backup-Zelle gespart; Kaltstart ~35 s).

## I2C-Bus (400 kHz, ein Bus)

| Gerät | Adresse |
|---|---|
| BMP581 | 0x47 (SDO→3V3) |
| LSM6DSO32 | 0x6A (SA0→GND) |
| SHT40 | 0x44 |
| OLED SSD1306 | 0x3C |

## Vollständige Netzliste (Referenz für Generatoren)

| Netz | Pins |
|---|---|
| GND | alle GND-Pads, USB-Shield, EP U6, CC-Rs low-side n/a |
| VBUS | J1.VBUS, U9.VBUS, U7.IN(4), 100n |
| VBAT | U7.OUT(3), J2.1, U6.VDD, SW1-Mitte n/a → U8.IN(1)+EN-Kette, R-Teiler oben |
| +3V3 | U8.OUT(5), U1.3V3, U2, U3, U4, U5.VCC+V_BCKP, J4.VCC, Pullups |
| USB_DP/USB_DN | J1.D±(A6/B6, A7/B7) ↔ U9 ↔ U1.IO20/IO19 |
| CC1/CC2 | J1.CC1/CC2 → je 5.1k → GND |
| CHG_STAT | U7.STAT(1) → LED grün → 3V3 (aktiv low) |
| PROG | U7.PROG(5) → 2k → GND |
| LDO_EN | U8.EN(3) ← SW1 (VBAT / GND) |
| ESP_EN | U1.EN ← 10k→3V3, 1µF→GND, SW2→GND |
| BTN_BOOT | U1.IO0 ← SW3→GND (interner Pullup) |
| I2C_SDA/SCL | s. oben, 4.7k→3V3 |
| I2S_BCLK/LRCK/DOUT | U1.IO4/5/6 → U6.BCLK/LRC/DIN |
| AMP_SD | U1.IO7 → U6.SD_MODE, 100k→3V3 |
| AMP_OUTP/OUTN | U6.OUT+/OUT− → J3 (Lautsprecher) |
| IMU_INT1 | U3.INT1 → U1.IO10 |
| GNSS_TX_NET | U5.TXD → U1.IO17 |
| GNSS_RX_NET | U5.RXD ← U1.IO18 |
| VBAT_SENSE | Teiler-Mitte → U1.IO1 |
| LED_STATUS | U1.IO2 → 1k → LED blau → GND |
| LORA_NSS/SCK/MOSI/MISO | U1.IO21/12/11/13 → U10 (E22-900M22S) |
| LORA_BUSY/DIO1/RST | U10 → U1.IO14/IO3/IO15 |
| LORA_TXEN/RXEN | U1.IO16/IO37 → U10 |
| LORA_ANT | U10.ANT → J5 (u.FL); E22 an +3V3 (TX 14 dBm ≈ 120 mA ok) |

⚠️ VERIFY: MAX98357A-GAIN-Pin offen lassen = 9 dB (Default). Bei Bedarf
GAIN-Netz auf Lötjumper führen — v0.1: offen.
