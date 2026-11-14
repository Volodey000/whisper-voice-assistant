import math
import struct
import winsound
import threading
from config import config

def _synthesize_pcm_wav(tones, duration, sample_rate=44100):
    """
    Синтезирует 16-битный PCM WAV буфер высокого разрешения (Hi-Fi)
    с мягкими огибающими (Attack/Decay) и теплыми обертонами.
    """
    num_samples = int(sample_rate * duration)
    samples = [0.0] * num_samples

    for (freq, start_t, tone_dur, amp) in tones:
        start_idx = int(start_t * sample_rate)
        tone_len = int(tone_dur * sample_rate)
        for i in range(tone_len):
            idx = start_idx + i
            if idx >= num_samples:
                break
            t = i / sample_rate
            # Плавная атака 6 мс и мягкое экспоненциальное затухание
            att = min(1.0, i / (0.006 * sample_rate))
            rel = math.exp(-t * 9.5)
            # Основной чистый тон + 20% мягкой второй гармоники
            val = (math.sin(2 * math.pi * freq * t) + 0.2 * math.sin(4 * math.pi * freq * t)) * att * rel * amp
            samples[idx] += val

    max_v = max(abs(s) for s in samples) or 1.0
    pcm = bytearray()
    for s in samples:
        v = int(max(-32767, min(32767, (s / max_v * 0.72) * 32767)))
        pcm += struct.pack('<h', v)

    data_size = len(pcm)
    hdr = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVEfmt '
    hdr += struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
    hdr += b'data' + struct.pack('<I', data_size)
    return hdr + pcm

# 1. Сигнал старта: мягкий восходящий теплый перезвон C5 (523Hz) -> G5 (784Hz)
_START_WAV = _synthesize_pcm_wav([
    (523.25, 0.00, 0.12, 0.8),
    (783.99, 0.04, 0.14, 0.95)
], duration=0.18)

# 2. Сигнал остановки: деликатный нисходящий тон G5 (784Hz) -> E5 (659Hz)
_STOP_WAV = _synthesize_pcm_wav([
    (783.99, 0.00, 0.09, 0.85),
    (659.25, 0.03, 0.12, 0.75)
], duration=0.15)

# 3. Сигнал успешной вставки: благородный аккорд F5 -> A5 -> C6
_SUCCESS_WAV = _synthesize_pcm_wav([
    (698.46, 0.00, 0.11, 0.7),
    (880.00, 0.03, 0.13, 0.8),
    (1046.50, 0.06, 0.15, 0.9)
], duration=0.22)

# 4. Сигнал отмены: глухой мягкий клик D4 (293Hz) -> A3 (220Hz)
_CANCEL_WAV = _synthesize_pcm_wav([
    (293.66, 0.00, 0.08, 0.8),
    (220.00, 0.02, 0.10, 0.7)
], duration=0.12)

def _play_hifi(wav_bytes):
    try:
        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
    except Exception:
        pass

def play_start_sound():
    if not config.get("play_sounds", True):
        return
    theme = config.get("sound_theme", "hifi")
    if theme == "classic":
        threading.Thread(target=lambda: [winsound.Beep(900, 50), winsound.Beep(1200, 60)], daemon=True).start()
    elif theme == "hifi":
        threading.Thread(target=_play_hifi, args=(_START_WAV,), daemon=True).start()

def play_stop_sound():
    if not config.get("play_sounds", True):
        return
    theme = config.get("sound_theme", "hifi")
    if theme == "classic":
        threading.Thread(target=lambda: [winsound.Beep(1200, 50), winsound.Beep(850, 60)], daemon=True).start()
    elif theme == "hifi":
        threading.Thread(target=_play_hifi, args=(_STOP_WAV,), daemon=True).start()

def play_success_sound():
    if not config.get("play_sounds", True):
        return
    theme = config.get("sound_theme", "hifi")
    if theme == "classic":
        threading.Thread(target=lambda: [winsound.Beep(1400, 40), winsound.Beep(1800, 70)], daemon=True).start()
    elif theme == "hifi":
        threading.Thread(target=_play_hifi, args=(_SUCCESS_WAV,), daemon=True).start()

def play_cancel_sound():
    if not config.get("play_sounds", True):
        return
    theme = config.get("sound_theme", "hifi")
    if theme == "classic":
        threading.Thread(target=lambda: winsound.Beep(650, 70), daemon=True).start()
    elif theme == "hifi":
        threading.Thread(target=_play_hifi, args=(_CANCEL_WAV,), daemon=True).start()
