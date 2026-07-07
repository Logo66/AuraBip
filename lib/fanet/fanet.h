// AuraBip — FANET Frame Encoder/Decoder
// © 2026 KIE Engineering. Proprietär.
//
// Herkunft: übernommen aus dem WindBuddy-KI-Projekt
// (C:\Users\Ivo\WindBuddy-KI-1.0\lib\fanet, eigener Clean-Room-Code),
// erweitert um Typ-1-Tracking für das Vario.
//
// Clean-Room-Implementierung ausschliesslich nach der FANET-Protokoll-
// Spezifikation (protocol.txt aus github.com/3s1d/fanet-stm32 — Spez lesen
// ist ok, deren Code wurde NICHT angeschaut). Kein Code aus BreezeDude
// oder GXAirCom.
//
// ⚠️ VERIFY: Alle Byte-Layouts vor Produktivbetrieb gegen protocol.txt und
// einen echten FANET-Empfänger (z.B. Skytraxx am Boden) prüfen (Ticket T1).

#pragma once
#include <stdint.h>
#include <stddef.h>

namespace fanet {

// Maximale Framegrösse (MAC-Header + Payload). FANET-Frames sind klein;
// 64 Bytes decken Typ 2/4 grosszügig ab.
constexpr size_t MAX_FRAME = 64;

// Frame-Typen (Header Bits 5..0)
constexpr uint8_t TYPE_ACK      = 0;
constexpr uint8_t TYPE_TRACKING = 1;  // Luftfahrzeug-Tracking
constexpr uint8_t TYPE_NAME     = 2;
constexpr uint8_t TYPE_MESSAGE  = 3;
constexpr uint8_t TYPE_SERVICE  = 4;  // Wetterstation u.ä.

struct Address {
  uint8_t  manufacturer;
  uint16_t device;
};

// Eingabedaten für einen Typ-4-Wetterframe. has_*-Flags steuern, welche
// Felder in den Sub-Header aufgenommen werden.
struct WeatherData {
  double lat_deg = 0.0;
  double lon_deg = 0.0;

  bool  has_wind = false;
  float wind_dir_deg   = 0.0f;  // 0..360
  float wind_speed_kmh = 0.0f;
  float wind_gust_kmh  = 0.0f;

  bool  has_temp = false;
  float temp_c = 0.0f;

  bool  has_humidity = false;
  float humidity_rh = 0.0f;     // 0..100 %rh

  bool  has_pressure = false;
  float pressure_hpa = 0.0f;    // auf Meereshöhe normalisiert (QNH)

  bool  has_soc = false;
  float soc_percent = 0.0f;     // 0..100
};

// Dekodierter MAC-Header + Payload (Payload = Bytes NACH dem Header).
struct DecodedFrame {
  uint8_t  type = 0;
  Address  src {0, 0};
  bool     forward = false;
  uint8_t  payload[MAX_FRAME] = {0};
  size_t   payload_len = 0;
};

// Eingabedaten für einen Typ-1-Tracking-Frame (Luftfahrzeug).
struct TrackingData {
  double  lat_deg = 0.0;
  double  lon_deg = 0.0;
  float   alt_m = 0.0f;        // GPS-Höhe MSL
  float   speed_kmh = 0.0f;    // Ground Speed
  float   climb_ms = 0.0f;     // Vario
  float   heading_deg = 0.0f;  // Kurs über Grund
  uint8_t aircraft_type = 1;   // 0 Other, 1 Paraglider, 2 Hangglider, 4 Glider ...
  bool    online_tracking = true;  // false = "no-track"-Wunsch
};

// Baut einen Typ-1-Tracking-Frame (15 Bytes). Rückgabe: Framelänge, 0 bei Fehler.
size_t buildTrackingFrame(const Address& src, const TrackingData& t,
                          uint8_t* buf, size_t buflen);

// Baut einen Typ-4-Service-Frame (Wetter). Rückgabe: Framelänge in Bytes,
// 0 bei Fehler (Puffer zu klein).
size_t buildWeatherFrame(const Address& src, const WeatherData& wx,
                         uint8_t* buf, size_t buflen);

// Baut einen Typ-2-Namensframe. Name wird ohne Nullterminator gesendet.
size_t buildNameFrame(const Address& src, const char* name,
                      uint8_t* buf, size_t buflen);

// Parst den MAC-Header eines empfangenen Frames (inkl. Extended Header)
// und kopiert die Payload. false bei zu kurzem/ungültigem Frame.
bool parseHeader(const uint8_t* buf, size_t len, DecodedFrame& out);

} // namespace fanet
