import queue
import time
import threading
import numpy as np
import sounddevice as sd
from config import config

SAMPLE_RATE = 16000

class AudioRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE, device_index=None):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.q = queue.Queue()
        self.is_recording = False
        self.stream = None
        self._lock = threading.Lock()
        self.current_volume = 0.0
        self.start_time = 0.0

        # Предварительный расчет для быстрого спектрального анализа 11 частотных полос
        self.num_bands = 11
        self.current_bands = [0.0] * self.num_bands
        self._fft_blocksize = 1024
        self._hanning_window = np.hanning(self._fft_blocksize).astype(np.float32)
        # Частотные диапазоны: охватывают спектр речи от 120 Гц до 6500 Гц
        band_edges = np.geomspace(120, 6500, self.num_bands + 1)
        freqs = np.fft.rfftfreq(self._fft_blocksize, 1.0 / self.sample_rate)
        self._band_masks = [(freqs >= band_edges[i]) & (freqs < band_edges[i+1]) for i in range(self.num_bands)]

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_recording:
            chunk = indata.copy()
            # 1. Расчет RMS громкости для визуализации и Noise Gate
            rms = float(np.sqrt(np.mean(chunk**2))) if chunk.size > 0 else 0.0
            self.current_volume = rms

            # 2. Быстрый спектральный анализ 11 частотных полос для живой волны
            if chunk.size >= self._fft_blocksize:
                sample = chunk[:self._fft_blocksize].flatten() * self._hanning_window
                spec = np.abs(np.fft.rfft(sample)) * (2.0 / self._fft_blocksize)
                raw_bands = [
                    float(np.sqrt(np.mean(spec[m]**2))) if np.any(m) else 0.0
                    for m in self._band_masks
                ]
                scaled_bands = []
                for b_val in raw_bands:
                    # Чувствительность увеличена в 2.5 раза для яркой и динамичной амплитуды волны
                    norm = min(1.0, (b_val * 50.0) ** 0.60)
                    scaled_bands.append(norm)
                self.current_bands = scaled_bands
            elif chunk.size > 0:
                self.current_bands = [min(1.0, (rms * 36.0) ** 0.65)] * self.num_bands

            # Шумоподавление (Noise Gate) с мягким щадящим порогом, чтобы не подавлять тихую речь
            if config.get("noise_gate", False):
                level = config.get("noise_gate_level", "soft")
                thresholds = {"soft": 0.0015, "medium": 0.003, "aggressive": 0.006}
                threshold = thresholds.get(level, 0.002)
                if rms < threshold:
                    # Мягкое плавное подавление фонового шума без подавления тихих согласных и гласных
                    factor = max(0.35, rms / threshold)
                    chunk = chunk * factor

            self.q.put(chunk)

    def get_volume(self) -> float:
        """Возвращает текущий RMS уровень громкости микрофона для живого VU-метра."""
        return self.current_volume

    def get_audio_bands(self) -> list[float]:
        """Возвращает текущие 11 частотных уровней (0.0 .. 1.0) для симметричного визуализатора."""
        return self.current_bands

    def start(self, device_index=None):
        with self._lock:
            if self.is_recording:
                return
            if device_index is not None:
                self.device_index = device_index

            # Защита: проверяем существование аудиоустройства
            if self.device_index is not None:
                try:
                    dev_info = sd.query_devices(self.device_index)
                    if dev_info.get('max_input_channels', 0) <= 0:
                        self.device_index = None
                except Exception:
                    print(f"[AudioRecorder] Микрофон ID {self.device_index} не найден на этом ПК. Переключение на устройство по умолчанию.")
                    self.device_index = None

            while not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    break

            self.is_recording = True
            self.start_time = time.time()
            self.current_volume = 0.0
            self.current_bands = [0.0] * self.num_bands

            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    device=self.device_index,
                    callback=self._audio_callback,
                    blocksize=1024
                )
                self.stream.start()
            except Exception as e:
                # Если сбой произошел на конкретном устройстве, пробуем дефолтный системный микрофон
                if self.device_index is not None:
                    print(f"[AudioRecorder] Сбой открытия микрофона ID {self.device_index}: {e}. Пробуем микрофон по умолчанию...")
                    self.device_index = None
                    try:
                        self.stream = sd.InputStream(
                            samplerate=self.sample_rate,
                            channels=1,
                            dtype='float32',
                            device=None,
                            callback=self._audio_callback,
                            blocksize=1024
                        )
                        self.stream.start()
                        return
                    except Exception as e_def:
                        self.is_recording = False
                        raise RuntimeError(f"Микрофон недоступен: {e_def}")
                self.is_recording = False
                raise RuntimeError(f"Микрофон недоступен: {e}")

    def stop(self) -> np.ndarray:
        with self._lock:
            if not self.is_recording:
                return np.array([], dtype=np.float32)

            self.is_recording = False
            if self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

            # Собираем все чанки аудио
            chunks = []
            while not self.q.empty():
                try:
                    chunks.append(self.q.get_nowait())
                except queue.Empty:
                    break

            if chunks:
                audio = np.concatenate(chunks, axis=0).flatten()
                return audio
            return np.array([], dtype=np.float32)

    def get_duration(self) -> float:
        if self.is_recording:
            return time.time() - self.start_time
        return 0.0

    def get_volume(self) -> float:
        return self.current_volume
