// AuraBip — Audio-Engine (Variante AUDIO): I2S -> MAX98357A -> Lautsprecher
// © 2026 KIE Engineering. Proprietär.
//
// Zwei Ebenen:
//  1) Varioton: Sinus-Synthese in Echtzeit. Tonhöhe/Piep-Rate aus Vz.
//     Klangqualität kommt aus sauberem Sinus + Hüllkurve (kein Klicken) —
//     genau das unterscheidet die Franzosen vom Piezo-Gefiepe.
//  2) Sprache: 16 kHz mono 16-bit-PCM-WAV aus LittleFS (/voice/<id>.wav),
//     über den Varioton gemischt (Ton während Ansage um -12 dB abgesenkt).
//     Prioritäts-Queue: Warnung verdrängt Info, beide verdrängen nie den
//     laufenden Piep abrupt (Mischung, kein Stopp).
//
// API: speakWarning("sink") -> spielt /voice/sink.wav mit PRIO_WARN.
//      Testsample erzeugen: tools/make_test_wav.py -> data/voice/test.wav,
//      dann `pio run -t uploadfs`.

#pragma once
#ifdef VARIANT_AUDIO
#include <Arduino.h>
#include <driver/i2s.h>
#include <math.h>
#include <FS.h>
#include <LittleFS.h>
#include "config.h"

class AudioEngine {
public:
  enum Prio : uint8_t { PRIO_BEEP = 0, PRIO_INFO = 1, PRIO_WARN = 2 };

  void begin() {
#ifdef PIN_AMP_SD
    pinMode(PIN_AMP_SD, OUTPUT);
    digitalWrite(PIN_AMP_SD, HIGH);       // MAX98357A aus Shutdown holen
#endif
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

    _fsOk = LittleFS.begin(true);
    Serial.printf("[AUDIO] LittleFS %s\n", _fsOk ? "OK" : "FEHLT (keine Ansagen)");
  }

  // --- Sprach-API -------------------------------------------------------------
  // id -> /voice/<id>.wav. Warnungen verdrängen wartende Infos.
  bool speakWarning(const char* id) { return enqueue(id, PRIO_WARN); }
  bool speakInfo(const char* id)    { return enqueue(id, PRIO_INFO); }

  bool enqueue(const char* id, Prio prio) {
    if (!_fsOk) return false;
    char path[48];
    snprintf(path, sizeof(path), "/voice/%s.wav", id);
    if (!LittleFS.exists(path)) {
      Serial.printf("[AUDIO] fehlt: %s\n", path);
      return false;
    }
    // Einfache Prioritäts-Queue (klein & deterministisch): Slot suchen,
    // bei vollem Puffer fliegt der niederprioste Eintrag raus.
    if (_qLen < QUEUE_MAX) {
      insert(path, prio);
      return true;
    }
    int lowest = 0;
    for (int i = 1; i < _qLen; i++)
      if (_queue[i].prio < _queue[lowest].prio) lowest = i;
    if (_queue[lowest].prio >= prio) return false;   // alles wichtiger
    for (int i = lowest; i < _qLen - 1; i++) _queue[i] = _queue[i + 1];
    _qLen--;
    insert(path, prio);
    return true;
  }

  bool speaking() const { return _wav; }

  // --- Renderer: regelmässig aufrufen (blockiert max. 1 DMA-Block, 16 ms) ------
  void render(float vario_ms) {
    // Nächste Ansage starten?
    if (!_wav && _qLen > 0) {
      _wav = new fs::File(LittleFS.open(_queue[0].path, "r"));
      for (int i = 0; i < _qLen - 1; i++) _queue[i] = _queue[i + 1];
      _qLen--;
      if (!*_wav || !seekToData(*_wav)) stopWav();
    }

    // Varioton-Parameter
    bool climb = vario_ms > 0.1f;
    bool sink  = vario_ms < SINK_ALARM_MS;
    float freq = TONE_BASE_FREQ_HZ + fmaxf(vario_ms, 0) * TONE_FREQ_PER_MS;
    if (sink) freq = 250;  // tiefer Dauerton

    uint32_t period = climb ? (uint32_t)(TONE_CLIMB_ON_MS_BASE / (1.0f + vario_ms)) : 0;
    uint32_t now = millis();
    uint32_t onMs = period < 40 ? 40u : period;
    bool on = sink || (climb && ((now % (2 * onMs)) < onMs));

    // WAV-Block lesen (falls Ansage läuft)
    int16_t wavBuf[256];
    size_t wavSamples = 0;
    if (_wav) {
      size_t got = _wav->read((uint8_t*)wavBuf, sizeof(wavBuf));
      wavSamples = got / 2;
      if (wavSamples == 0) stopWav();
    }

    // Mischen: Ansage voll, Varioton dabei um -12 dB (Faktor 0.25) abgesenkt
    float toneGain = wavSamples ? 0.25f : 1.0f;
    int16_t buf[256];
    for (int i = 0; i < 256; i++) {
      if (on) {
        _phase += 2.0f * (float)M_PI * freq / AUDIO_SAMPLE_RATE;
        if (_phase > 2.0f * (float)M_PI) _phase -= 2.0f * (float)M_PI;
        _env += (1.0f - _env) * 0.02f;   // 3 ms Attack/Release gegen Klicken
      } else {
        _env += (0.0f - _env) * 0.02f;
      }
      float s = sinf(_phase) * _env * 12000.0f * toneGain;
      if ((size_t)i < wavSamples) s += (float)wavBuf[i];
      if (s > 32000.0f) s = 32000.0f;
      if (s < -32000.0f) s = -32000.0f;
      buf[i] = (int16_t)s;
    }
    size_t written;
    i2s_write(I2S_NUM_0, buf, sizeof(buf), &written, portMAX_DELAY);
  }

private:
  static const int QUEUE_MAX = 4;
  struct QItem { char path[48]; Prio prio; };

  void insert(const char* path, Prio prio) {
    // Einsortieren: höhere Prio nach vorne (stabil innerhalb gleicher Prio)
    int pos = _qLen;
    while (pos > 0 && _queue[pos - 1].prio < prio) { _queue[pos] = _queue[pos - 1]; pos--; }
    snprintf(_queue[pos].path, sizeof(_queue[pos].path), "%s", path);
    _queue[pos].prio = prio;
    _qLen++;
  }

  void stopWav() {
    if (_wav) { _wav->close(); delete _wav; _wav = nullptr; }
  }

  // Minimaler RIFF-Parser: fmt prüfen (PCM16 mono 16 kHz), zu "data" springen.
  static bool seekToData(fs::File& f) {
    uint8_t hdr[12];
    if (f.read(hdr, 12) != 12 || memcmp(hdr, "RIFF", 4) || memcmp(hdr + 8, "WAVE", 4))
      return false;
    while (f.available()) {
      uint8_t ch[8];
      if (f.read(ch, 8) != 8) return false;
      uint32_t sz = (uint32_t)ch[4] | (ch[5] << 8) | (ch[6] << 16) | ((uint32_t)ch[7] << 24);
      if (!memcmp(ch, "fmt ", 4)) {
        uint8_t fmt[16];
        if (sz < 16 || f.read(fmt, 16) != 16) return false;
        uint16_t audioFmt  = fmt[0] | (fmt[1] << 8);
        uint16_t channels  = fmt[2] | (fmt[3] << 8);
        uint32_t rate      = (uint32_t)fmt[4] | (fmt[5] << 8) | (fmt[6] << 16) | ((uint32_t)fmt[7] << 24);
        uint16_t bits      = fmt[14] | (fmt[15] << 8);
        if (audioFmt != 1 || channels != 1 || bits != 16 || rate != AUDIO_SAMPLE_RATE) {
          Serial.printf("[AUDIO] WAV-Format falsch (PCM16 mono %d Hz noetig)\n", AUDIO_SAMPLE_RATE);
          return false;
        }
        if (sz > 16) f.seek(f.position() + (sz - 16));
      } else if (!memcmp(ch, "data", 4)) {
        return true;   // Dateizeiger steht auf den Samples
      } else {
        f.seek(f.position() + sz + (sz & 1));
      }
    }
    return false;
  }

  float _phase = 0, _env = 0;
  bool _fsOk = false;
  fs::File* _wav = nullptr;
  QItem _queue[QUEUE_MAX];
  int _qLen = 0;
};
#endif
