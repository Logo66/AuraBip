// AuraBip — Vario-Kern: beschleunigungsgestützter Kalman-Filter
// © 2026 KIE Engineering. Proprietär.
//
// Zustand x = [Höhe h, Vertikalgeschwindigkeit v]
// Prädiktion mit vertikaler Beschleunigung a_z (IMU, gravitationskompensiert),
// Korrektur mit barometrischer Höhe (BMP581).
// Das ist das "Instant Vario"-Prinzip: der Beschleuniger liefert die schnelle
// Dynamik, das Barometer die Drift-Referenz.

#pragma once
#include <math.h>

class VarioKF {
public:
  void reset(float alt0) {
    h = alt0; v = 0;
    P00 = 10; P01 = 0; P10 = 0; P11 = 10;
  }

  // IMU-Schritt (hohe Rate). az_mss: Vertikalbeschleunigung Erde-Frame, g-frei.
  void predict(float az_mss, float dt) {
    h += v * dt + 0.5f * az_mss * dt * dt;
    v += az_mss * dt;
    // P = F P F' + Q  (F = [[1,dt],[0,1]])
    float q = KF_ACCEL_NOISE * KF_ACCEL_NOISE;
    float P00n = P00 + dt*(P10 + P01) + dt*dt*P11 + 0.25f*q*dt*dt*dt*dt;
    float P01n = P01 + dt*P11 + 0.5f*q*dt*dt*dt;
    float P10n = P10 + dt*P11 + 0.5f*q*dt*dt*dt;
    float P11n = P11 + q*dt*dt;
    P00=P00n; P01=P01n; P10=P10n; P11=P11n;
  }

  // Baro-Schritt (mittlere Rate). z: barometrische Höhe in m.
  void update(float z) {
    float r = KF_BARO_NOISE * KF_BARO_NOISE;
    float y = z - h;
    float S = P00 + r;
    float K0 = P00 / S, K1 = P10 / S;
    h += K0 * y;
    v += K1 * y;
    float P00n = (1 - K0) * P00;
    float P01n = (1 - K0) * P01;
    float P10n = P10 - K1 * P00;
    float P11n = P11 - K1 * P01;
    P00=P00n; P01=P01n; P10=P10n; P11=P11n;
  }

  float altitude() const { return h; }
  float vario()    const { return v; }

private:
  float h = 0, v = 0;
  float P00, P01, P10, P11;
};

// Barometrische Höhe aus Druck (ISA, QNH konfigurierbar)
inline float pressureToAlt(float p_pa, float qnh_pa = 101325.0f) {
  return 44330.0f * (1.0f - powf(p_pa / qnh_pa, 0.1902949f));
}

// Vertikalbeschleunigung Erde-Frame aus Roh-Accel + Orientierung.
// v0.1-Vereinfachung: |a| - g als Näherung der Vertikalkomponente.
// Gut genug im ruhigen Geradeausflug; T3 ersetzt das durch echte
// Orientierungsschätzung (Mahony/Madgwick mit Gyro).
inline float verticalAccelApprox(float ax, float ay, float az) {
  float mag = sqrtf(ax*ax + ay*ay + az*az);
  return mag - 9.81f;   // ⚠️ Vorzeichenkonvention beim Einbau prüfen
}
