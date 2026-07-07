// AuraBip — FANET Frame Encoder/Decoder (Implementierung)
// © 2026 KIE Engineering. Proprietär.
// Herkunft: WindBuddy-KI lib/fanet (eigener Clean-Room-Code) + Typ-1-Tracking.
//
// Clean-Room nach FANET-Protokoll-Spezifikation (protocol.txt, 3s1d/fanet-stm32).
// Alle ⚠️ VERIFY-Marker: gegen Spez + realen Empfänger prüfen (Ticket T1).

#include "fanet.h"
#include <math.h>
#include <string.h>

namespace fanet {

// --- MAC-Header -------------------------------------------------------------
// Byte 0: bit7 Extended Header, bit6 Forward, bits 5..0 Typ
// Byte 1: Manufacturer, Byte 2..3: Device-ID little endian
static size_t writeMacHeader(const Address& src, uint8_t type, bool forward,
                             uint8_t* buf) {
  buf[0] = (type & 0x3F) | (forward ? 0x40 : 0x00);
  buf[1] = src.manufacturer;
  buf[2] = (uint8_t)(src.device & 0xFF);
  buf[3] = (uint8_t)(src.device >> 8);
  return 4;
}

// --- Absolute Koordinaten ----------------------------------------------------
// 3 Byte signed little endian. ⚠️ VERIFY Skalierung gegen protocol.txt:
// lat_i = round(lat * 93206), lon_i = round(lon * 46603)
static void writeCoord3(int32_t v, uint8_t* p) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
  p[2] = (uint8_t)((v >> 16) & 0xFF);
}

static size_t writePosition(double lat_deg, double lon_deg, uint8_t* p) {
  writeCoord3((int32_t)lround(lat_deg * 93206.0), p);
  writeCoord3((int32_t)lround(lon_deg * 46603.0), p + 3);
  return 6;
}

// Wind-/Böengeschwindigkeit: 1 Byte, bits 0..6 in 0.2 km/h,
// bit 7 = Skalierung 5x (für Werte über 25.4 km/h).
static uint8_t encodeSpeed(float kmh) {
  if (kmh < 0) kmh = 0;
  long units = lround(kmh * 5.0);        // Einheiten à 0.2 km/h
  if (units <= 127) return (uint8_t)units;
  units = lround(kmh);                   // 5x-Skala: Einheiten à 1.0 km/h
  if (units > 127) units = 127;          // Kappe bei 127 km/h
  return (uint8_t)(0x80 | units);
}

// --- Typ 1: Tracking ----------------------------------------------------------
// Payload-Layout lt. protocol.txt (gleiche Struktur wie der im Aura-Krücke-
// Projekt gegen Live-Empfänger verifizierte Encoder):
//   0-5  Position (24-bit LE 2er-Komplement, lat*93206 / lon*46603)
//   6-7  16-bit LE: Online(15) | Aircraft(14-12) | AltScaling(11, 1=4x) | Alt(10-0)
//   8    Speed: bits 0-6 in 0.5 km/h, bit 7 = 5x-Skala
//   9    Climb: bits 0-6 7-bit-2er-Komplement in 0.1 m/s, bit 7 = 5x-Skala
//   10   Heading in 360/256 Grad
size_t buildTrackingFrame(const Address& src, const TrackingData& t,
                          uint8_t* buf, size_t buflen) {
  if (buflen < 15) return 0;
  size_t n = writeMacHeader(src, TYPE_TRACKING, false, buf);
  n += writePosition(t.lat_deg, t.lon_deg, buf + n);

  // Höhe + Status-Wort
  long alt = lroundf(t.alt_m);
  if (alt < 0) alt = 0;
  uint16_t alt_scale = 0;
  if (alt > 2047) { alt = (alt + 2) / 4; if (alt > 2047) alt = 2047; alt_scale = 1; }
  uint16_t w = ((uint16_t)alt & 0x07FF)
             | (uint16_t)(alt_scale << 11)
             | (uint16_t)((t.aircraft_type & 0x07) << 12)
             | (uint16_t)((t.online_tracking ? 1 : 0) << 15);
  buf[n++] = (uint8_t)(w & 0xFF);
  buf[n++] = (uint8_t)(w >> 8);

  // Speed
  long sp = lroundf(t.speed_kmh * 2.0f); if (sp < 0) sp = 0;
  uint8_t sp_scale = 0;
  if (sp > 127) { sp = lroundf(t.speed_kmh * 0.4f); if (sp > 127) sp = 127; sp_scale = 1; }
  buf[n++] = (uint8_t)((sp & 0x7F) | (sp_scale << 7));

  // Climb
  long cl = lroundf(t.climb_ms * 10.0f);
  uint8_t cl_scale = 0;
  if (cl > 63 || cl < -64) { cl = lroundf(t.climb_ms * 2.0f); cl_scale = 1; }
  if (cl > 63) cl = 63; if (cl < -64) cl = -64;
  buf[n++] = (uint8_t)((cl & 0x7F) | (cl_scale << 7));

  // Heading
  float h = t.heading_deg;
  while (h < 0) h += 360.0f;
  while (h >= 360.0f) h -= 360.0f;
  buf[n++] = (uint8_t)(lroundf(h * 256.0f / 360.0f) & 0xFF);

  return n;  // 15
}

size_t buildWeatherFrame(const Address& src, const WeatherData& wx,
                         uint8_t* buf, size_t buflen) {
  if (buflen < MAX_FRAME) return 0;

  size_t n = writeMacHeader(src, TYPE_SERVICE, false, buf);

  // Service-Sub-Header (⚠️ VERIFY Bitbelegung gegen protocol.txt):
  // bit7 Internet-Gateway, bit6 Temperatur, bit5 Wind, bit4 Feuchte,
  // bit3 Luftdruck, bit2 Remote-Config, bit1 State of Charge, bit0 Ext.Header
  uint8_t sub = 0;
  if (wx.has_temp)     sub |= 1 << 6;
  if (wx.has_wind)     sub |= 1 << 5;
  if (wx.has_humidity) sub |= 1 << 4;
  if (wx.has_pressure) sub |= 1 << 3;
  if (wx.has_soc)      sub |= 1 << 1;
  buf[n++] = sub;

  // Position ist Pflicht, sobald Messdaten folgen — wir senden sie immer,
  // damit die Station auch im Fehlerpfad (nur Header) auf Karten sichtbar
  // bleibt.
  n += writePosition(wx.lat_deg, wx.lon_deg, buf + n);

  // Datenfelder in Sub-Header-Reihenfolge (bit 6 abwärts):
  if (wx.has_temp) {
    // 1 Byte, 0.5 °C, Zweierkomplement
    long t = lround(wx.temp_c * 2.0f);
    if (t > 127) t = 127; if (t < -128) t = -128;
    buf[n++] = (uint8_t)(int8_t)t;
  }
  if (wx.has_wind) {
    // Heading: 1 Byte in 360/256 Grad
    float dir = wx.wind_dir_deg;
    while (dir < 0) dir += 360.0f;
    while (dir >= 360.0f) dir -= 360.0f;
    buf[n++] = (uint8_t)lround(dir * 256.0 / 360.0) & 0xFF;
    buf[n++] = encodeSpeed(wx.wind_speed_kmh);
    buf[n++] = encodeSpeed(wx.wind_gust_kmh);
  }
  if (wx.has_humidity) {
    // 1 Byte in 0.4 %rh
    long h = lround(wx.humidity_rh / 0.4f);
    if (h < 0) h = 0; if (h > 255) h = 255;
    buf[n++] = (uint8_t)h;
  }
  if (wx.has_pressure) {
    // 2 Byte little endian, (hPa - 430) * 10
    long p = lround((wx.pressure_hpa - 430.0f) * 10.0f);
    if (p < 0) p = 0; if (p > 65535) p = 65535;
    buf[n++] = (uint8_t)(p & 0xFF);
    buf[n++] = (uint8_t)(p >> 8);
  }
  if (wx.has_soc) {
    // Untere 4 Bits: 0x0 = 0 %, 0xF = 100 % (Schritte 100/15 %)
    float s = wx.soc_percent;
    if (s < 0) s = 0; if (s > 100) s = 100;
    buf[n++] = (uint8_t)lround(s * 15.0f / 100.0f) & 0x0F;
  }

  return n;
}

size_t buildNameFrame(const Address& src, const char* name,
                      uint8_t* buf, size_t buflen) {
  size_t namelen = strlen(name);
  if (4 + namelen > buflen) namelen = buflen - 4;
  size_t n = writeMacHeader(src, TYPE_NAME, false, buf);
  memcpy(buf + n, name, namelen);  // ohne Nullterminator
  return n + namelen;
}

bool parseHeader(const uint8_t* buf, size_t len, DecodedFrame& out) {
  if (len < 4) return false;

  out.type    = buf[0] & 0x3F;
  out.forward = (buf[0] & 0x40) != 0;
  out.src.manufacturer = buf[1];
  out.src.device = (uint16_t)buf[2] | ((uint16_t)buf[3] << 8);

  size_t pos = 4;

  // Extended Header (bit 7): 1 Byte — bits 7..6 ACK, bit 5 Unicast
  // (+3 Byte Zieladresse), bit 4 Signatur (+4 Byte). ⚠️ VERIFY
  if (buf[0] & 0x80) {
    if (len < pos + 1) return false;
    uint8_t ext = buf[pos++];
    if (ext & 0x20) pos += 3;  // Unicast: Zieladresse überspringen
    if (ext & 0x10) pos += 4;  // Signatur überspringen
    if (pos > len) return false;
  }

  out.payload_len = len - pos;
  if (out.payload_len > MAX_FRAME) out.payload_len = MAX_FRAME;
  memcpy(out.payload, buf + pos, out.payload_len);
  return true;
}

} // namespace fanet
