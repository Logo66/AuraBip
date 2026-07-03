// AuraBip — Konfiguration
// © 2026 KIE Engineering. Proprietär.
#pragma once

#define DEVICE_NAME       "AuraBip"

// --- I2C (⚠️ VERIFY Pins am V4-Schema; V3: SDA=17 SCL=18 fürs OLED-Bus) ---
#define PIN_I2C_SDA       41   // externer Sensorbus (getrennt vom OLED-Bus möglich)
#define PIN_I2C_SCL       42
#define I2C_ADDR_BMP581   0x47
#define I2C_ADDR_LSM6     0x6A
#define I2C_ADDR_SHT40    0x44

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
