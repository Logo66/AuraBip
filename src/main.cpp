// AuraBip — Hauptprogramm
// © 2026 KIE Engineering. Proprietär.
//
// Tasks:
//   Core 1: Sensorik (IMU 200 Hz predict, Baro 50 Hz update) — harte Latenz
//   Core 0: BLE (5 Hz LK8EX1 + NMEA), Display (5 Hz), Audio-Render, FANET-TX
//
// Boards:
//   Heltec V3/V4 (silent/audio): Sensorik SIMULIERT (sensors_stub.cpp)
//   Serienboard (series/series_vision): echte Treiber (sensors_series.cpp),
//     GNSS-Parser, FANET-Tracking (Typ 1, nur TX), I2S-Audio + Ansagen

#include <Arduino.h>
#include <Wire.h>
#include <esp_task_wdt.h>
#include <esp_idf_version.h>
#include "config.h"
#include "vario.h"
#include "sensors.h"
#include "gnss.h"
#include "ble_link.h"
#include "display.h"
#ifdef VARIANT_AUDIO
#include "audio.h"
AudioEngine audio;
#endif
#ifdef BOARD_SERIES
#include <SPI.h>
#include "fanet_tx.h"
FanetTx fanetTx;
#endif

VarioKF  kf;
BleLink  ble;
Display  disp;
NmeaParser gnss;
HardwareSerial GnssSerial(1);

volatile float g_vario = 0, g_alt = 0;
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
      float p = sensors::readPressurePa();
      if (p > 0) kf.update(pressureToAlt(p));
    }
    g_vario = kf.vario();
    g_alt   = kf.altitude();
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(1000 / IMU_RATE_HZ));
  }
}

// --- GNSS: Zeilen parsen (RMC+GGA) + roh per BLE durchreichen ---
static void pumpGnss() {
  while (GnssSerial.available()) {
    if (gnss.feed((char)GnssSerial.read())) {
      const char* l = gnss.line();
      if (strncmp(l, "$G", 2) == 0 && (strstr(l, "RMC") || strstr(l, "GGA"))) {
        ble.sendLine(l); ble.sendLine("\r\n");
      }
    }
  }
}

#ifdef BOARD_SERIES
// --- Batterie: Teiler 1M/1M -> VBAT/2 an ADC ---
static int batteryPct() {
  uint32_t mv = analogReadMilliVolts(PIN_VBAT_ADC) * 2;
  float pct = (mv - 3300) / (4200.0f - 3300.0f) * 100.0f;  // linear, grob
  if (pct < 0) pct = 0; if (pct > 100) pct = 100;
  return (int)pct;
}

// --- Flugerkennung (Hysterese): Fix + Speed ---
static bool flying() {
  static bool fly = false;
  static uint32_t slowSince = 0;
  bool fresh = gnss.data.fix && (millis() - gnss.data.lastFixMs < 5000);
  if (!fly) {
    if (fresh && gnss.data.speed_kmh > FLIGHT_START_KMH) fly = true;
  } else {
    if (fresh && gnss.data.speed_kmh > FLIGHT_STOP_KMH) slowSince = 0;
    else if (!slowSince) slowSince = millis();
    else if (millis() - slowSince > FLIGHT_STOP_HOLD_MS) { fly = false; slowSince = 0; }
  }
  return fly;
}
#endif

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

#ifdef BOARD_SERIES
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH);            // an bis Setup durch
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_LORA_NSS, OUTPUT); digitalWrite(PIN_LORA_NSS, HIGH);
  pinMode(PIN_OLED_CS, OUTPUT);  digitalWrite(PIN_OLED_CS, HIGH);
  SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI);   // geteilter SPI2-Bus
#endif

  disp.begin();
  if (!sensors::init()) Serial.println("[ERR] Sensor-Init — I2C-Map prüfen");
  ble.begin(DEVICE_NAME);
  GnssSerial.begin(GNSS_BAUD, SERIAL_8N1, PIN_GNSS_RX, PIN_GNSS_TX);
#ifdef VARIANT_AUDIO
  audio.begin();
#endif
#ifdef BOARD_SERIES
  if (!fanetTx.begin()) Serial.println("[ERR] FANET-Init — SX1262 prüfen");
  digitalWrite(PIN_LED, LOW);
#endif

  xTaskCreatePinnedToCore(sensorTask, "sensor", 4096, nullptr, 10, nullptr, 1);
}

void loop() {
  esp_task_wdt_reset();
  pumpGnss();

  static uint32_t lastTx = 0, lastDisp = 0, lastTemp = 0;
  uint32_t now = millis();

  if (now - lastTemp > 5000) { lastTemp = now; g_lastTemp = sensors::readTempC(); }

  int batt = -1;
#ifdef BOARD_SERIES
  batt = batteryPct();

  // FANET-Tracking: alle 5 s, nur im Flug (Doppel-Sicherung: Flag + Flug)
  static uint32_t lastFanet = 0;
  bool fanetActive = false;
  if (FANET_TX_ENABLED && fanetTx.ok && flying() &&
      now - lastFanet >= FANET_TX_INTERVAL_MS) {
    lastFanet = now;
    fanetActive = fanetTx.sendTracking(gnss.data.lat, gnss.data.lon,
                                     gnss.data.alt_m, gnss.data.speed_kmh,
                                     g_vario, gnss.data.course_deg);
  }
  disp.status(gnss.data.sats, fanetActive || (now - lastFanet < 2 * FANET_TX_INTERVAL_MS && lastFanet));
#endif

  if (now - lastTx >= 1000 / LK8EX1_RATE_HZ) {
    lastTx = now;
    ble.sendLK8EX1(sensors::readPressurePa(), g_alt, g_vario, g_lastTemp, batt);
  }
  if (now - lastDisp >= 200) {
    lastDisp = now;
    disp.flight(g_vario, g_alt, gnss.data.speed_kmh, ble.connected(), gnss.data.fix);
  }
#ifdef VARIANT_AUDIO
  audio.render(g_vario);
#endif
  delay(2);
}
