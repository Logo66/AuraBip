// AuraBip — Display (SSD1306 128x64, U8g2 BSD-Lizenz)
// © 2026 KIE Engineering. Proprietär.
//
// Eine Ansicht. Vario riesig, Rest klein. Kein Menü im Flug.

#pragma once
#include <U8g2lib.h>
#include "config.h"

class Display {
public:
  void begin() {
    pinMode(PIN_VEXT, OUTPUT);
    digitalWrite(PIN_VEXT, LOW);          // Peripherie an ⚠️ VERIFY V4
    delay(50);
    _oled.begin();
    _oled.setBusClock(400000);
  }

  void flight(float vario_ms, float alt_m, float gs_kmh, bool bleOk, bool gpsFix) {
    _oled.clearBuffer();

    // Vario: Vorzeichen + eine Nachkommastelle, grösste verfügbare Ziffern
    char v[8];
    snprintf(v, sizeof(v), "%+.1f", vario_ms);
    _oled.setFont(u8g2_font_logisoso32_tf);      // 32 px — füllt die obere Hälfte
    int w = _oled.getStrWidth(v);
    _oled.drawStr((128 - w) / 2, 40, v);

    // Untere Zeile: Höhe + Groundspeed
    char l[24];
    snprintf(l, sizeof(l), "%4dm  %3dkmh", (int)lroundf(alt_m), (int)lroundf(gs_kmh));
    _oled.setFont(u8g2_font_helvB12_tf);
    _oled.drawStr(0, 62, l);

    // Statuspunkte oben rechts: BLE / GPS
    if (bleOk)  _oled.drawDisc(118, 4, 2);
    if (gpsFix) _oled.drawDisc(126, 4, 2);
    else        _oled.drawCircle(126, 4, 2);

    _oled.sendBuffer();
  }

private:
  U8G2_SSD1306_128X64_NONAME_F_HW_I2C _oled{U8G2_R0, PIN_OLED_RST, PIN_OLED_SCL, PIN_OLED_SDA};
};
