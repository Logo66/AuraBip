// AuraBip — Echte Sensortreiber fürs Serienboard (raw I2C, keine Fremdlibs)
// © 2026 KIE Engineering. Proprietär.
//
// BMP581-Zugriff portiert aus dem Aura-Krücke-Projekt (eigener Code,
// C:\Users\Ivo\aura_kruecke\src\main.cpp rawBMP581Pressure); Registerwerte
// gegen das Bosch-Datenblatt bzw. bmp5_defs.h verifiziert.
// SHT40: Sensirion-Kommando 0xFD (High Precision), Formeln lt. Datenblatt.
// LSM6DSO32: ST-Registersatz (WHO_AM_I 0x6C), 208 Hz / ±8 g.

#ifdef BOARD_SERIES
#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "sensors.h"

namespace sensors {

// --- I2C-Helfer --------------------------------------------------------------
// Mutex: Sensor-Task (200 Hz, Core 1) und loop() (LK8EX1/SHT40) teilen sich
// den Bus — jede Transaktion ist gelockt, die SHT40-Messwartezeit NICHT.
static SemaphoreHandle_t s_busMtx = nullptr;

struct BusLock {
  BusLock()  { if (s_busMtx) xSemaphoreTake(s_busMtx, portMAX_DELAY); }
  ~BusLock() { if (s_busMtx) xSemaphoreGive(s_busMtx); }
};

static bool writeReg(uint8_t addr, uint8_t reg, uint8_t val) {
  BusLock lock;
  Wire.beginTransmission(addr);
  Wire.write(reg); Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool readRegs(uint8_t addr, uint8_t reg, uint8_t* buf, size_t len) {
  BusLock lock;
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, (uint8_t)len) != len) return false;
  for (size_t i = 0; i < len; i++) buf[i] = Wire.read();
  return true;
}

// --- BMP581 (0x47) ------------------------------------------------------------
// Register: CHIP_ID 0x01 (=0x50), OSR_CONFIG 0x36, ODR_CONFIG 0x37,
//           Druck 0x20..0x22 (24 bit LE, /64 = Pa)
static bool bmpInit() {
  uint8_t id = 0;
  if (!readRegs(I2C_ADDR_BMP581, 0x01, &id, 1) || id != 0x50) return false;
  // OSR_CONFIG: press_en (bit6) | osr_p 16x (0x04<<3) | osr_t 4x (0x02)
  if (!writeReg(I2C_ADDR_BMP581, 0x36, 0x40 | (0x04 << 3) | 0x02)) return false;
  // ODR_CONFIG: odr 50 Hz (0x0F<<2) | pwr_mode NORMAL (0x01)
  if (!writeReg(I2C_ADDR_BMP581, 0x37, (0x0F << 2) | 0x01)) return false;
  delay(20);  // erste Messung
  return true;
}

float readPressurePa() {
  uint8_t d[3];
  if (!readRegs(I2C_ADDR_BMP581, 0x20, d, 3)) return -1.0f;
  int32_t raw = (int32_t)d[0] | ((int32_t)d[1] << 8) | ((int32_t)d[2] << 16);
  if (raw & 0x800000) raw |= 0xFF000000;
  return (float)raw / 64.0f;  // Pa
}

// --- LSM6DSO32 (0x6A) ----------------------------------------------------------
// WHO_AM_I 0x0F (=0x6C), CTRL1_XL 0x10, CTRL3_C 0x12, OUTX_L_A 0x28
// DSO32-FS_XL-Codierung (bits 3:2): 00=±4g 01=±32g 10=±8g 11=±16g
static bool imuInit() {
  uint8_t id = 0;
  if (!readRegs(I2C_ADDR_LSM6, 0x0F, &id, 1) || id != 0x6C) return false;
  writeReg(I2C_ADDR_LSM6, 0x12, 0x44);            // CTRL3_C: BDU | IF_INC
  // CTRL1_XL: ODR 208 Hz (0101<<4) | FS ±8g (10<<2)
  return writeReg(I2C_ADDR_LSM6, 0x10, (0x05 << 4) | (0x02 << 2));
}

void readAccel(float& ax, float& ay, float& az) {
  uint8_t d[6];
  if (!readRegs(I2C_ADDR_LSM6, 0x28, d, 6)) { ax = ay = 0; az = 9.81f; return; }
  int16_t x = (int16_t)(d[0] | (d[1] << 8));
  int16_t y = (int16_t)(d[2] | (d[3] << 8));
  int16_t z = (int16_t)(d[4] | (d[5] << 8));
  const float k = 0.244e-3f * 9.80665f;  // ±8g: 0.244 mg/LSB -> m/s²
  ax = x * k; ay = y * k; az = z * k;
}

// --- SHT40 (0x44) ---------------------------------------------------------------
static float g_temp = 15.0f, g_rh = 50.0f;

static bool shtMeasure() {
  {
    BusLock lock;
    Wire.beginTransmission(I2C_ADDR_SHT40);
    Wire.write(0xFD);                     // Measure High Precision
    if (Wire.endTransmission() != 0) return false;
  }
  delay(10);                              // Messzeit lt. Datenblatt (max 8.3 ms)
  uint8_t d[6];
  {
    BusLock lock;
    if (Wire.requestFrom((uint8_t)I2C_ADDR_SHT40, (uint8_t)6) != 6) return false;
    for (int i = 0; i < 6; i++) d[i] = Wire.read();
  }
  uint16_t t_raw = (d[0] << 8) | d[1];
  uint16_t h_raw = (d[3] << 8) | d[4];
  g_temp = -45.0f + 175.0f * (float)t_raw / 65535.0f;
  g_rh   =  -6.0f + 125.0f * (float)h_raw / 65535.0f;
  if (g_rh > 100) g_rh = 100; if (g_rh < 0) g_rh = 0;
  return true;
}

float readTempC()    { shtMeasure(); return g_temp; }
float readHumidity() { return g_rh; }   // aus letzter readTempC()-Messung

// --- Init ------------------------------------------------------------------------
bool init() {
  if (!s_busMtx) s_busMtx = xSemaphoreCreateMutex();
  bool bmp = bmpInit();
  bool imu = imuInit();
  bool sht = shtMeasure();
  Serial.printf("[I2C] BMP581  0x%02X: %s\n", I2C_ADDR_BMP581, bmp ? "OK" : "FEHLT");
  Serial.printf("[I2C] LSM6DSO32 0x%02X: %s\n", I2C_ADDR_LSM6, imu ? "OK" : "FEHLT");
  Serial.printf("[I2C] SHT40   0x%02X: %s\n", I2C_ADDR_SHT40, sht ? "OK" : "FEHLT");
  return bmp && imu && sht;
}

} // namespace sensors
#endif // BOARD_SERIES
