// AuraBip — Sensor-Stub (Platzhalter bis T2 die echten Treiber portiert)
// © 2026 KIE Engineering. Proprietär.
//
// init() probt die erwarteten I2C-Adressen real (zeigt also echte
// Verkabelungsfehler). Die Messwerte sind SIMULIERT: Normaldruck mit
// leichter Sinus-Welle (~±0.5 m/s Vario zum Testen von Display/BLE/Ton),
// Accel = 1 g ruhend, Temp = 15 °C. T2 ersetzt diese Datei komplett.

#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include "config.h"

namespace sensors {

static bool probe(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

bool init() {
  struct { uint8_t addr; const char* name; } chips[] = {
    { I2C_ADDR_BMP581, "BMP581" },
    { I2C_ADDR_LSM6,   "LSM6DSO32" },
    { I2C_ADDR_SHT40,  "SHT40" },
  };
  bool all = true;
  for (auto& c : chips) {
    bool ok = probe(c.addr);
    Serial.printf("[I2C] %-10s 0x%02X: %s\n", c.name, c.addr, ok ? "OK" : "FEHLT");
    all &= ok;
  }
  if (!all) Serial.println("[I2C] STUB aktiv — Messwerte sind simuliert!");
  return all;
}

float readPressurePa() {
  // Normaldruck + langsame Welle: ~±4 m Hub, Periode 30 s -> sichtbares Vario
  return 101325.0f + 50.0f * sinf(millis() * (2.0f * PI / 30000.0f));
}

void readAccel(float& ax, float& ay, float& az) {
  ax = 0.0f; ay = 0.0f; az = 9.81f;   // ruhend, z nach oben
}

float readTempC() {
  return 15.0f;
}

} // namespace sensors
