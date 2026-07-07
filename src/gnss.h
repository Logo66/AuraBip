// AuraBip — Minimaler NMEA-Parser (RMC + GGA), eigener Code
// © 2026 KIE Engineering. Proprietär.
//
// Zeilenweise füttern (feed gibt true zurück, wenn eine komplette Zeile im
// Puffer liegt — z.B. für BLE-Passthrough). Checksumme wird geprüft, nur
// gültige RMC/GGA-Sätze aktualisieren den Zustand.
// Quectel L96: Standard-NMEA 0183, 9600 Bd.

#pragma once
#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

struct GnssData {
  bool     fix = false;       // RMC-Status 'A'
  double   lat = 0, lon = 0;  // Grad, +N/+E
  float    alt_m = 0;         // GGA MSL-Höhe
  float    speed_kmh = 0;     // RMC Ground Speed
  float    course_deg = 0;    // RMC Kurs über Grund
  uint8_t  sats = 0;          // GGA Satelliten in Benutzung
  uint32_t lastFixMs = 0;     // millis() des letzten gültigen RMC-'A'
};

class NmeaParser {
public:
  GnssData data;

  // Ein Zeichen einlesen; true = komplette Zeile fertig, in line() abrufbar.
  bool feed(char c) {
    if (c == '\n') {
      _buf[_pos] = 0; _pos = 0;
      if (_buf[0] == '$') { parse(_buf); return true; }
      return false;
    }
    if (c != '\r' && _pos < sizeof(_buf) - 1) _buf[_pos++] = c;
    return false;
  }

  const char* line() const { return _buf; }

private:
  char _buf[120]; size_t _pos = 0;

  static bool checksumOk(const char* s) {
    const char* star = strrchr(s, '*');
    if (!star || strlen(star) < 3) return false;
    uint8_t cs = 0;
    for (const char* p = s + 1; p < star; ++p) cs ^= (uint8_t)*p;
    return cs == (uint8_t)strtol(star + 1, nullptr, 16);
  }

  // Felder (kommagetrennt) in Zeiger-Array zerlegen. Leere Felder -> "".
  static int split(char* s, const char* f[], int maxf) {
    int n = 0; f[n++] = s;
    for (char* p = s; *p && n < maxf; ++p)
      if (*p == ',' || *p == '*') { *p = 0; f[n++] = p + 1; }
    return n;
  }

  // ddmm.mmmm -> Grad (NMEA-Koordinatenformat)
  static double coordToDeg(const char* v, const char* hemi) {
    if (!*v) return 0;
    double raw = atof(v);
    double deg = floor(raw / 100.0);
    deg += (raw - deg * 100.0) / 60.0;
    if (*hemi == 'S' || *hemi == 'W') deg = -deg;
    return deg;
  }

  void parse(const char* rawline) {
    if (!checksumOk(rawline)) return;
    char work[120];
    strncpy(work, rawline, sizeof(work) - 1); work[sizeof(work) - 1] = 0;
    const char* f[20];
    int n = split(work, f, 20);
    if (n < 2) return;
    // Talker-ID ignorieren ($GPRMC/$GNRMC/...): Satztyp = Zeichen 3..5
    const char* type = f[0] + 3;

    if (strncmp(type, "RMC", 3) == 0 && n >= 9) {
      // 1 Zeit, 2 Status A/V, 3/4 Lat, 5/6 Lon, 7 Speed kn, 8 Kurs
      bool valid = (f[2][0] == 'A');
      data.fix = valid;
      if (valid) {
        data.lat = coordToDeg(f[3], f[4]);
        data.lon = coordToDeg(f[5], f[6]);
        data.speed_kmh  = atof(f[7]) * 1.852f;
        if (*f[8]) data.course_deg = atof(f[8]);
        data.lastFixMs = millis();
      }
    } else if (strncmp(type, "GGA", 3) == 0 && n >= 10) {
      // 6 Fix-Qualität, 7 Sats, 9 MSL-Höhe
      data.sats = (uint8_t)atoi(f[7]);
      if (atoi(f[6]) > 0 && *f[9]) data.alt_m = atof(f[9]);
    }
  }
};
