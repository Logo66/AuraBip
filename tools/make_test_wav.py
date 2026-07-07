#!/usr/bin/env python3
# AuraBip — Testsample für das Sprach-Framework erzeugen
# © 2026 KIE Engineering. Proprietär.
#
# Erzeugt data/voice/test.wav: 16 kHz mono 16-bit PCM, 1.5 s Sinus-Sweep
# 400->1200 Hz mit Fade-in/out. Aufs Gerät bringen:
#   python tools/make_test_wav.py
#   pio run -e series -t uploadfs
# Abspielen in der Firmware: audio.speakInfo("test")

import math
import struct
import wave
from pathlib import Path

RATE = 16000
DUR_S = 1.5
F_START, F_END = 400.0, 1200.0
AMP = 0.6

out = Path(__file__).resolve().parent.parent / "data" / "voice" / "test.wav"
out.parent.mkdir(parents=True, exist_ok=True)

n = int(RATE * DUR_S)
fade = int(RATE * 0.02)  # 20 ms Fade gegen Klicken
samples = bytearray()
phase = 0.0
for i in range(n):
    t = i / n
    freq = F_START + (F_END - F_START) * t
    phase += 2.0 * math.pi * freq / RATE
    env = min(1.0, i / fade, (n - 1 - i) / fade)
    s = int(AMP * env * 32767.0 * math.sin(phase))
    samples += struct.pack("<h", s)

with wave.open(str(out), "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(bytes(samples))

print(f"OK: {out} ({out.stat().st_size} Bytes, {DUR_S}s Sweep {F_START:.0f}-{F_END:.0f} Hz)")
