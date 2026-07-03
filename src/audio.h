// AuraBip — Audio-Engine (Variante AUDIO): I2S -> MAX98357A -> Lautsprecher
// © 2026 KIE Engineering. Proprietär.
//
// Zwei Ebenen:
//  1) Varioton: Sinus-Synthese in Echtzeit. Tonhöhe/Piep-Rate aus Vz.
//     Klangqualität kommt aus sauberem Sinus + Hüllkurve (kein Klicken) —
//     genau das unterscheidet die Franzosen vom Piezo-Gefiepe.
//  2) Sprache: 16 kHz mono WAV aus LittleFS (16 MB Flash), gemischt über
//     den Varioton (Ton wird während Ansage um -12 dB abgesenkt).
//
// v0.1: Ton-Engine funktionsfähig, Sprach-Player als Gerüst (T4).

#pragma once
#ifdef VARIANT_AUDIO
#include <driver/i2s.h>
#include <math.h>
#include "config.h"

class AudioEngine {
public:
  void begin() {
    i2s_config_t cfg = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
      .sample_rate = AUDIO_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 4,
      .dma_buf_len = 256,
      .use_apll = false,
    };
    i2s_pin_config_t pins = {
      .bck_io_num = PIN_I2S_BCLK,
      .ws_io_num  = PIN_I2S_LRCK,
      .data_out_num = PIN_I2S_DOUT,
      .data_in_num = I2S_PIN_NO_CHANGE,
    };
    i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
    i2s_set_pin(I2S_NUM_0, &pins);
  }

  // Aus Vario-Wert Tonparameter ableiten und einen DMA-Block rendern.
  // Regelmässig aus eigener Task aufrufen (Task-Gerüst in main.cpp).
  void render(float vario_ms) {
    bool climb = vario_ms > 0.1f;
    bool sink  = vario_ms < SINK_ALARM_MS;
    float freq = TONE_BASE_FREQ_HZ + fmaxf(vario_ms, 0) * TONE_FREQ_PER_MS;
    if (sink) freq = 250;  // tiefer Dauerton

    // Piep-Kadenz: schneller bei mehr Steigen
    uint32_t period = climb ? (uint32_t)(TONE_CLIMB_ON_MS_BASE / (1.0f + vario_ms)) : 0;

    int16_t buf[256];
    uint32_t now = millis();
    uint32_t onMs = period < 40 ? 40u : period;
    bool on = sink || (climb && ((now % (2 * onMs)) < onMs));

    for (int i = 0; i < 256; i++) {
      if (on) {
        _phase += 2.0f * (float)M_PI * freq / AUDIO_SAMPLE_RATE;
        if (_phase > 2.0f * (float)M_PI) _phase -= 2.0f * (float)M_PI;
        // Hüllkurve gegen Klicken: 3 ms Attack/Release
        _env += (1.0f - _env) * 0.02f;
      } else {
        _env += (0.0f - _env) * 0.02f;
      }
      buf[i] = (int16_t)(sinf(_phase) * _env * 12000);
    }
    size_t written;
    i2s_write(I2S_NUM_0, buf, sizeof(buf), &written, portMAX_DELAY);
  }

  // T4: Sprach-Ansage abspielen (LittleFS-WAV, über Ton gemischt)
  void say(const char* /*wavPath*/) { /* Gerüst */ }

private:
  float _phase = 0, _env = 0;
};
#endif
