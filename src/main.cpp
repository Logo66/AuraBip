// AuraBip — Hauptprogramm
// © 2026 KIE Engineering. Proprietär.
//
// Tasks:
//   Core 1: Sensorik (IMU 200 Hz predict, Baro 50 Hz update) — harte Latenz
//   Core 0: BLE (5 Hz LK8EX1 + NMEA), Display (5 Hz), Audio-Render
//
// Sensortreiber: v0.1 nutzt die im Aura-Projekt bewährten Register-Zugriffe
// (BMP581/LSM6DSO32/SHT40 sind Ivos Standard-Trio, gleiche I2C-Map wie Vario v3).
// T2 portiert die Treiber aus dem Aura-Monorepo hierher (eigener Code = ok).

#include <Arduino.h>
#include <Wire.h>
#include <esp_task_wdt.h>
#include <esp_idf_version.h>
#include "config.h"
#include "vario.h"
#include "ble_link.h"
#include "display.h"
#ifdef VARIANT_AUDIO
#include "audio.h"
AudioEngine audio;
#endif

VarioKF  kf;
BleLink  ble;
Display  disp;
HardwareSerial GnssSerial(1);

// --- Platzhalter-Sensor-API bis T2 die echten Treiber portiert ---
namespace sensors {
  bool  init();                 // I2C-Scan + Konfiguration
  float readPressurePa();       // BMP581
  void  readAccel(float&, float&, float&);  // LSM6DSO32, m/s²
  float readTempC();            // SHT40
}

volatile float g_vario = 0, g_alt = 0;
static float g_gsKmh = 0; static bool g_fix = false;
static float g_lastTemp = 15.0f;

// --- Sensor-Task: Kern des Varios ---
void sensorTask(void*) {
  esp_task_wdt_add(NULL);
  kf.reset(pressureToAlt(sensors::readPressurePa()));
  uint32_t lastBaro = 0;
  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    esp_task_wdt_reset();
    float ax, ay, az;
    sensors::readAccel(ax, ay, az);
    kf.predict(verticalAccelApprox(ax, ay, az), 1.0f / IMU_RATE_HZ);

    if (millis() - lastBaro >= 1000 / BARO_RATE_HZ) {
      lastBaro = millis();
      kf.update(pressureToAlt(sensors::readPressurePa()));
    }
    g_vario = kf.vario();
    g_alt   = kf.altitude();
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(1000 / IMU_RATE_HZ));
  }
}

// --- GNSS: NMEA durchreichen + Speed/Fix extrahieren (RMC) ---
static void pumpGnss() {
  static char line[100]; static size_t pos = 0;
  while (GnssSerial.available()) {
    char c = GnssSerial.read();
    if (c == '\n') {
      line[pos] = 0; pos = 0;
      if (strncmp(line, "$G", 2) == 0 &&
          (strstr(line, "RMC") || strstr(line, "GGA"))) {
        ble.sendLine(line); ble.sendLine("\r\n");
        if (strstr(line, "RMC")) {
          // Feld 7 = Speed in Knoten, Feld 2 = Status A/V  (simpel, T2 härten)
          char* f = line; int idx = 0; float kn = 0; char stat = 'V';
          while ((f = strchr(f, ',')) != nullptr) {
            f++; idx++;
            if (idx == 2) stat = *f;
            if (idx == 7) kn = strtof(f, nullptr);
          }
          g_fix = (stat == 'A');
          g_gsKmh = kn * 1.852f;
        }
      }
    } else if (pos < sizeof(line) - 1 && c != '\r') line[pos++] = c;
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, 400000);

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
  esp_task_wdt_config_t wdt = { .timeout_ms = 10000, .idle_core_mask = 0, .trigger_panic = true };
  esp_task_wdt_init(&wdt);
#else
  esp_task_wdt_init(10, true);  // IDF 4.x (Arduino-Core 2.x): Sekunden-API
#endif
  esp_task_wdt_add(NULL);

  disp.begin();
  if (!sensors::init()) Serial.println("[ERR] Sensor-Init — I2C-Map prüfen");
  ble.begin(DEVICE_NAME);
  GnssSerial.begin(GNSS_BAUD, SERIAL_8N1, PIN_GNSS_RX, PIN_GNSS_TX);
#ifdef VARIANT_AUDIO
  audio.begin();
#endif

  xTaskCreatePinnedToCore(sensorTask, "sensor", 4096, nullptr, 10, nullptr, 1);
}

void loop() {
  esp_task_wdt_reset();
  pumpGnss();

  static uint32_t lastTx = 0, lastDisp = 0, lastTemp = 0;
  uint32_t now = millis();

  if (now - lastTemp > 5000) { lastTemp = now; g_lastTemp = sensors::readTempC(); }

  if (now - lastTx >= 1000 / LK8EX1_RATE_HZ) {
    lastTx = now;
    ble.sendLK8EX1(sensors::readPressurePa(), g_alt, g_vario, g_lastTemp, -1);
  }
  if (now - lastDisp >= 200) {
    lastDisp = now;
    disp.flight(g_vario, g_alt, g_gsKmh, ble.connected(), g_fix);
  }
#ifdef VARIANT_AUDIO
  audio.render(g_vario);
#endif
  delay(2);
}
