// AuraBip — Sensor-API (Implementierung: sensors_series.cpp bzw. sensors_stub.cpp)
// © 2026 KIE Engineering. Proprietär.
//
// BOARD_SERIES: echte Treiber (BMP581 50 Hz, LSM6DSO32 208 Hz, SHT40).
// Heltec:       sensors_stub.cpp — SIMULIERTE Werte.

#pragma once

namespace sensors {

// I2C-Geräte proben + konfigurieren. false = mind. ein Chip fehlt.
bool  init();

// BMP581: statischer Druck in Pa (<0 bei Lesefehler)
float readPressurePa();

// LSM6DSO32: Beschleunigung in m/s² (Board-Frame)
void  readAccel(float& ax, float& ay, float& az);

// SHT40: Temperatur °C / rel. Feuchte % (gecacht, Messung ~10 ms — nicht
// aus dem Sensor-Task aufrufen, nur aus loop())
float readTempC();
float readHumidity();

} // namespace sensors
