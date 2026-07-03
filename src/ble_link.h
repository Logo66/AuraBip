// AuraBip — BLE-Link (Nordic UART Service, LK8EX1 + NMEA-Passthrough)
// © 2026 KIE Engineering. Proprietär.
// Bibliothek: NimBLE-Arduino (Apache-2.0)

#pragma once
#include <NimBLEDevice.h>
#include "config.h"

class BleLink {
public:
  void begin(const char* name) {
    NimBLEDevice::init(name);
    NimBLEDevice::setPower(ESP_PWR_LVL_P6);
    _server = NimBLEDevice::createServer();
    // Nordic UART Service UUIDs (öffentlicher De-facto-Standard)
    NimBLEService* svc = _server->createService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    _tx = svc->createCharacteristic("6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
                                    NIMBLE_PROPERTY::NOTIFY);
    svc->start();
    NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
    adv->addServiceUUID(svc->getUUID());
    adv->start();
  }

  bool connected() { return _server && _server->getConnectedCount() > 0; }

  void sendLine(const char* line) {
    if (!connected()) return;
    _tx->setValue((uint8_t*)line, strlen(line));
    _tx->notify();
  }

  // $LK8EX1,pressure(Pa),altitude(m),vario(cm/s),temp(°C),battery(%+1000 oder V*1000)*CS
  // ⚠️ VERIFY (T1): Feld 5 Konvention (999 wenn unbekannt; Batterie % = Wert+1000)
  void sendLK8EX1(float p_pa, float alt_m, float vario_ms, float temp_c, int batt_pct) {
    char body[96];
    snprintf(body, sizeof(body), "LK8EX1,%.0f,%.0f,%d,%.0f,%d",
             p_pa, alt_m, (int)lroundf(vario_ms * 100.0f), temp_c,
             batt_pct >= 0 ? batt_pct + 1000 : 999);
    uint8_t cs = 0;
    for (const char* c = body; *c; ++c) cs ^= (uint8_t)*c;
    char line[112];
    snprintf(line, sizeof(line), "$%s*%02X\r\n", body, cs);
    sendLine(line);
  }

private:
  NimBLEServer* _server = nullptr;
  NimBLECharacteristic* _tx = nullptr;
};
