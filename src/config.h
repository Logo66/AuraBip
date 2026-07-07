// AuraBip — Konfiguration
// © 2026 KIE Engineering. Proprietär.
#pragma once

#define DEVICE_NAME       "AuraBip"

// I2C-Adressen (beide Boards gleich)
#define I2C_ADDR_BMP581   0x47
#define I2C_ADDR_LSM6     0x6A
#define I2C_ADDR_SHT40    0x44

#ifdef BOARD_SERIES
// ============================================================================
// Serienboard v0.1 — ESP32-S3-MINI-1 (Referenz: hardware/PINMAP.md)
// ============================================================================

// --- I2C (ein Bus: BMP581 + LSM6DSO32 + SHT40) ---
#define PIN_I2C_SDA       8
#define PIN_I2C_SCL       9
#define PIN_IMU_INT       10   // LSM6DSO32 INT1 (Tap/Data-Ready, v0.1 ungenutzt)

// --- Audio: I2S -> MAX98357A ---
#define PIN_I2S_BCLK      4
#define PIN_I2S_LRCK      5
#define PIN_I2S_DOUT      47   // Routing-Umzug 2026-07-06: IO6 -> IO47 (s. PINMAP.md)
#define PIN_AMP_SD        7    // high = Amp an (100k-Pullup an 3V3)

// --- GNSS: Quectel L96 an UART1 ---
#define PIN_GNSS_RX       17   // <- L96 TXD
#define PIN_GNSS_TX       18   // -> L96 RXD
#define GNSS_BAUD         9600

// --- LoRa: E22-900M22S (SX1262) an SPI2, geteilt mit OLED ---
#define PIN_SPI_SCK       12
#define PIN_SPI_MOSI      11
#define PIN_SPI_MISO      13
#define PIN_LORA_NSS      21
#define PIN_LORA_DIO1     3
#define PIN_LORA_BUSY     14
#define PIN_LORA_RST      15
#define PIN_LORA_TXEN     16
#define PIN_LORA_RXEN     37

// --- OLED SSD1327 (Variante vision, geteilter SPI2-Bus) ---
#define PIN_OLED_CS       33
#define PIN_OLED_DC       34
#define PIN_OLED_RST      35

// --- Sonstiges ---
#define PIN_VBAT_ADC      1    // Teiler 1M/1M -> VBAT/2
#define PIN_LED           2    // Status-LED, aktiv high
#define PIN_BTN           0    // BOOT/USER-Taster (aktiv low)

#else
// ============================================================================
// Heltec V3/V4 Prototyp — Sensorik simuliert (sensors_stub.cpp)
// ============================================================================

// --- I2C (⚠️ VERIFY Pins am V4-Schema; V3: SDA=17 SCL=18 fürs OLED-Bus) ---
#define PIN_I2C_SDA       41   // externer Sensorbus (getrennt vom OLED-Bus möglich)
#define PIN_I2C_SCL       42

// --- OLED (onboard, eigener Bus beim Heltec) ---
#define PIN_OLED_SDA      17
#define PIN_OLED_SCL      18
#define PIN_OLED_RST      21
#define PIN_VEXT          36   // OLED/Peripherie-Versorgung (LOW = an) ⚠️ VERIFY V4

// --- GNSS (SH1.25-8P) ⚠️ VERIFY Pinout aus V4-Doku (T2) ---
#define PIN_GNSS_RX       33
#define PIN_GNSS_TX       34
#define GNSS_BAUD         9600

// --- Audio-Variante (nur bei -D VARIANT_AUDIO) ---
#define PIN_I2S_BCLK      6
#define PIN_I2S_LRCK      5
#define PIN_I2S_DOUT      7

#endif // BOARD_SERIES

#define AUDIO_SAMPLE_RATE 16000

// --- Vario-Filter ---
#define BARO_RATE_HZ      50
#define IMU_RATE_HZ       200
#define KF_ACCEL_NOISE    0.3f    // m/s² Prozessrauschen (tunen im Flug)
#define KF_BARO_NOISE     0.35f   // m Messrauschen BMP581 (tunen)

// --- Ton-Engine (audio) ---
#define TONE_CLIMB_ON_MS_BASE   350
#define TONE_BASE_FREQ_HZ       600
#define TONE_FREQ_PER_MS        120   // Hz pro m/s Steigen
#define SINK_ALARM_MS           -3.5f // Dauerton unterhalb

// --- BLE ---
#define LK8EX1_RATE_HZ    5

// --- FANET (nur Serienboard, nur TX) ---
#define FANET_TX_ENABLED        1
#define FANET_TX_INTERVAL_MS    5000
#define FANET_TX_DBM            14
#define FANET_TCXO_VOLT         1.8f  // E22-900M22S: TCXO an DIO3, 1.8 V
#define FANET_FREQ_MHZ          868.2f
#define FANET_AIRCRAFT_TYPE     1     // 1 = Paraglider
// Flugerkennung: GPS-Fix + Speed-Schwelle mit Hysterese
#define FLIGHT_START_KMH        10.0f
#define FLIGHT_STOP_KMH         5.0f
#define FLIGHT_STOP_HOLD_MS     60000
