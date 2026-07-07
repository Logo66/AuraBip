// AuraBip — FANET-Sender (Tracking Typ 1, NUR TX) fürs Serienboard
// © 2026 KIE Engineering. Proprietär.
//
// Funkmodul: EBYTE E22-900M22S (SX1262) an SPI2. Besonderheiten E22:
//   - TCXO an DIO3 mit 1.8 V (nicht 2.4 V wie Heltec!)
//   - externer RF-Schalter über TXEN/RXEN -> RadioLib setRfSwitchPins
// PHY: 868.2 MHz, SF7, BW 250 kHz, CR 4/8, SyncWord 0xF1, CRC an —
// Parameter identisch zum in aura_kruecke live verifizierten Setup.
// Frame-Encoding: lib/fanet (Clean-Room, aus WindBuddy übernommen).
//
// Sende-Politik: alle FANET_TX_INTERVAL_MS, aber nur im Flug (Flugerkennung
// mit Hysterese in main.cpp). Kein RX — Empfang macht die Krücke/App.

#pragma once
#ifdef BOARD_SERIES
#include <Arduino.h>
#include <SPI.h>
#include <RadioLib.h>
#include <esp_mac.h>
#include <fanet.h>
#include "config.h"

class FanetTx {
public:
  bool ok = false;

  // Voraussetzung: SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI) lief schon.
  bool begin() {
    _radio = new SX1262(new Module(PIN_LORA_NSS, PIN_LORA_DIO1,
                                   PIN_LORA_RST, PIN_LORA_BUSY));
    int st = _radio->begin(FANET_FREQ_MHZ, 250.0, 7, 8,
                           0xF1, FANET_TX_DBM, 12, FANET_TCXO_VOLT);
    Serial.printf("[SX1262] begin = %d\n", st);
    if (st != RADIOLIB_ERR_NONE) return false;

    _radio->setRfSwitchPins(PIN_LORA_RXEN, PIN_LORA_TXEN);
    _radio->setCRC(true);
    _radio->setCurrentLimit(140);
    _radio->standby();

    // Eigene FANET-Adresse: 0xFC (Experimental/Unregistriert, wie Krücke),
    // Device-ID aus den letzten 2 Bytes der eFuse-MAC.
    uint8_t mac[6] = {0};
    esp_read_mac(mac, ESP_MAC_WIFI_STA);
    _addr.manufacturer = 0xFC;
    _addr.device = (uint16_t)mac[4] << 8 | mac[5];
    Serial.printf("[FANET] Adresse FC:%04X, TX %d dBm — NUR TX\n",
                  _addr.device, FANET_TX_DBM);
    ok = true;
    return true;
  }

  // Tracking-Frame blockierend senden (~30 ms Airtime bei SF7/BW250).
  bool sendTracking(double lat, double lon, float alt_m, float speed_kmh,
                    float climb_ms, float heading_deg) {
    if (!ok || !FANET_TX_ENABLED) return false;
    fanet::TrackingData t;
    t.lat_deg = lat; t.lon_deg = lon; t.alt_m = alt_m;
    t.speed_kmh = speed_kmh; t.climb_ms = climb_ms; t.heading_deg = heading_deg;
    t.aircraft_type = FANET_AIRCRAFT_TYPE;
    t.online_tracking = true;
    uint8_t buf[fanet::MAX_FRAME];
    size_t n = fanet::buildTrackingFrame(_addr, t, buf, sizeof(buf));
    if (!n) return false;
    int st = _radio->transmit(buf, n);
    _radio->standby();
    if (st != RADIOLIB_ERR_NONE) Serial.printf("[FANET] TX-Fehler %d\n", st);
    return st == RADIOLIB_ERR_NONE;
  }

private:
  SX1262* _radio = nullptr;
  fanet::Address _addr {0xFC, 0};
};
#endif // BOARD_SERIES
