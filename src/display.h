// AuraBip — Display
// © 2026 KIE Engineering. Proprietär.
//
// Drei Ausbaustufen:
//   Heltec-Prototyp:        SSD1306 128x64 onboard (I2C, eigener Bus)
//   Serie (VARIANT_VISION): SSD1327 128x96 Graustufen-OLED am geteilten SPI2
//                           (⚠️ T-H9: Controller/Geometrie nach Lieferung
//                            verifizieren — U8g2-Konstruktor ggf. tauschen!)
//   Serie ohne vision:      kein Display (No-Op-Stub)
//
// Eine Ansicht. Vario riesig, Rest klein. Kein Menü im Flug.

#pragma once
#include "config.h"

#if defined(BOARD_SERIES) && !defined(VARIANT_VISION)

// --- Serie ohne Display: Stub -------------------------------------------------
class Display {
public:
  void begin() {}
  void splash() {}
  void flight(float, float, float, bool, bool) {}
  void status(uint8_t, bool) {}
};

#else
#include <U8g2lib.h>
#include <SPI.h>

class Display {
public:
  void begin() {
#ifndef BOARD_SERIES
    pinMode(PIN_VEXT, OUTPUT);
    digitalWrite(PIN_VEXT, LOW);          // Peripherie an ⚠️ VERIFY V4
    delay(50);
#endif
    _oled.begin();
#ifndef BOARD_SERIES
    _oled.setBusClock(400000);
#endif
    splash();
  }

  // Startbild
  void splash() {
    _oled.clearBuffer();
    _oled.setFont(u8g2_font_logisoso22_tf);
    int w = _oled.getStrWidth("AuraBip");
    _oled.drawStr((W - w) / 2, H / 2, "AuraBip");
    _oled.setFont(u8g2_font_helvR08_tf);
    const char* sub = "Aura PIP";
    w = _oled.getStrWidth(sub);
    _oled.drawStr((W - w) / 2, H / 2 + 16, sub);
    _oled.sendBuffer();
  }

  // Zusatzinfos für den Basisscreen (Serie): FANET-TX + Satellitenzahl
  void status(uint8_t sats, bool fanetTx) { _sats = sats; _fanetTx = fanetTx; }

  void flight(float vario_ms, float alt_m, float gs_kmh, bool bleOk, bool gpsFix) {
    _oled.clearBuffer();

    // Vario: Vorzeichen + eine Nachkommastelle, grösste verfügbare Ziffern
    char v[8];
    snprintf(v, sizeof(v), "%+.1f", vario_ms);
    _oled.setFont(u8g2_font_logisoso32_tf);      // 32 px — füllt die obere Hälfte
    int w = _oled.getStrWidth(v);
    _oled.drawStr((W - w) / 2, 40, v);

    // Untere Zeile(n): Höhe + Groundspeed
    char l[24];
    snprintf(l, sizeof(l), "%4dm  %3dkmh", (int)lroundf(alt_m), (int)lroundf(gs_kmh));
    _oled.setFont(u8g2_font_helvB12_tf);
    _oled.drawStr(0, H - 2, l);

#ifdef BOARD_SERIES
    // Statuszeile Serie: BLE / GNSS-Sats / FANET
    char s[32];
    snprintf(s, sizeof(s), "BLE%c GPS%d %s",
             bleOk ? '*' : '-', _sats, _fanetTx ? "FANET*" : "fanet-");
    _oled.setFont(u8g2_font_helvR08_tf);
    _oled.drawStr(0, 52, s);
#endif

    // Statuspunkte oben rechts: BLE / GPS
    if (bleOk)  _oled.drawDisc(W - 10, 4, 2);
    if (gpsFix) _oled.drawDisc(W - 2, 4, 2);
    else        _oled.drawCircle(W - 2, 4, 2);

    _oled.sendBuffer();
  }

private:
#ifdef BOARD_SERIES
  static const int W = 128, H = 96;
  // SSD1327 128x96 am geteilten SPI2 (SCK/MOSI via SPI.begin in main.cpp).
  // ⚠️ T-H9: Konstruktor nach Lieferung verifizieren (evtl. WS_128X128 o.ä.)
  U8G2_SSD1327_VISIONOX_128X96_F_4W_HW_SPI _oled{U8G2_R0, PIN_OLED_CS, PIN_OLED_DC, PIN_OLED_RST};
#else
  static const int W = 128, H = 64;
  U8G2_SSD1306_128X64_NONAME_F_HW_I2C _oled{U8G2_R0, PIN_OLED_RST, PIN_OLED_SCL, PIN_OLED_SDA};
#endif
  uint8_t _sats = 0;
  bool _fanetTx = false;
};
#endif
