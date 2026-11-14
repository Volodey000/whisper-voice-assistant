import os
import sys
import numpy as np
from config import config
from hardware import resolve_settings, detect_hardware

# Инициализируем пути к библиотекам CUDA
import cuda_setup

# Папка для локального хранения моделей внутри самого проекта
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")

def get_local_model_target(model_name: str) -> tuple[str, bool]:
    """
    Проверяет, есть ли модель в локальной папке проекта: whisper-voice-assistant/models/<name>.
    Если модель распакована локально — возвращает абсолютный путь к папке и True.
    Если нет — возвращает имя модели и False.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    local_path = os.path.join(MODELS_DIR, model_name)
    bin_file = os.path.join(local_path, "model.bin")
    
    # Модель считается локальной, если в папке есть файл весов model.bin размером > 1 МБ
    if os.path.isdir(local_path) and os.path.exists(bin_file) and os.path.getsize(bin_file) > 1000000:
        return local_path, True
    return model_name, False

class WhisperEngine:
    def __init__(self):
        self.model = None
        self.current_model_name = None
        self.current_device = None
        self.current_compute_type = None

    def get_model(self):
        cfg_model = config.get("model_name", "auto")
        cfg_device = config.get("device", "auto")
        cfg_compute = config.get("compute_type", "auto")

        resolved = resolve_settings(cfg_device, cfg_model, cfg_compute)
        model_name = resolved["model_name"]
        device = resolved["device"]
        compute_type = resolved["compute_type"]

        # Если уже загружена нужная модель — возвращаем её
        if (self.model is not None and 
            self.current_model_name == model_name and 
            self.current_device == device and 
            self.current_compute_type == compute_type):
            return self.model

        from faster_whisper import WhisperModel

        target_path_or_name, is_local = get_local_model_target(model_name)
        download_dest = os.path.join(MODELS_DIR, model_name)

        if is_local:
            print(f"[WhisperEngine] Загрузка ЛОКАЛЬНОЙ модели '{model_name}' из папки проекта: {target_path_or_name}")
        else:
            print(f"[WhisperEngine] Модель '{model_name}' скачивается в папку проекта: {download_dest}")

        try:
            self.model = WhisperModel(
                target_path_or_name,
                device=device,
                compute_type=compute_type,
                download_root=download_dest,
                local_files_only=is_local
            )
            self.current_model_name = model_name
            self.current_device = device
            self.current_compute_type = compute_type
            print(f"[WhisperEngine] Модель '{model_name}' успешно загружена на {device} ({compute_type})!")
        except Exception as e:
            print(f"[WhisperEngine] Не удалось запустить на {device} ({compute_type}): {e}.")
            print(f"[WhisperEngine] Включение отказоустойчивого режима CPU...")

            # Подбираем безопасную модель для CPU
            # Если целевая модель уже скачана локально, используем её, чтобы не требовать интернет
            fallback_name = "small" if model_name in ("large-v3-turbo", "medium", "large-v3") else model_name
            fb_path, fb_is_local = get_local_model_target(fallback_name)

            if not fb_is_local and is_local:
                # Если fallback нет на диске, но запрошенная модель локальна — работаем автономно с ней
                fb_path, fb_is_local = target_path_or_name, is_local
                fallback_name = model_name

            fb_dest = os.path.join(MODELS_DIR, fallback_name)

            # Шаг 1: Пробуем CPU INT8 (быстрое квантование)
            try:
                self.model = WhisperModel(
                    fb_path,
                    device="cpu",
                    compute_type="int8",
                    download_root=fb_dest,
                    local_files_only=fb_is_local
                )
                self.current_model_name = fallback_name
                self.current_device = "cpu"
                self.current_compute_type = "int8"
                print(f"[WhisperEngine] Резервный запуск: CPU INT8 ('{fallback_name}') успешен.")
            except Exception as e_int8:
                print(f"[WhisperEngine] INT8 не поддерживается данным процессором: {e_int8}. Переход на CPU default (float32)...")
                # Шаг 2: Пробуем CPU default/float32 (совместимо со всеми процессорами x86/x64)
                try:
                    self.model = WhisperModel(
                        fb_path,
                        device="cpu",
                        compute_type="default",
                        download_root=fb_dest,
                        local_files_only=fb_is_local
                    )
                    self.current_model_name = fallback_name
                    self.current_device = "cpu"
                    self.current_compute_type = "default"
                    print(f"[WhisperEngine] Универсальный запуск: CPU default ('{fallback_name}') успешен.")
                except Exception as e_cpu_all:
                    print(f"[WhisperEngine] Критическая ошибка загрузки модели Whisper: {e_cpu_all}")
                    raise RuntimeError(f"Не удалось инициализировать модель Whisper: {e_cpu_all}")

        return self.model

    def transcribe_audio(self, audio_data: np.ndarray, language: str = None, task: str = "transcribe") -> tuple[str, str, float]:
        """
        Транскрибирует или переводит numpy массив (16kHz float32 mono).
        task="transcribe" — распознавание исходной речи
        task="translate" — мгновенный перевод на английский язык
        Возвращает: (полный текст, определенный язык, вероятность языка)
        """
        if audio_data is None or len(audio_data) < 1600:  # меньше 0.1 сек
            return "", "unknown", 0.0

        model = self.get_model()

        if language is None or language == "auto":
            lang_param = None
        else:
            lang_param = language

        # beam_size 5 для высокой точности
        vad_enabled = config.get("vad_filter", True)
        vad_params = dict(min_silence_duration_ms=400, speech_pad_ms=200) if vad_enabled else None

        # Быстрое определение языка без задержки: 1 сегмент вместо мульти-прохода
        extra_kwargs = {}
        if lang_param is None and config.get("fast_lang_detect", True):
            extra_kwargs["language_detection_segments"] = 1
            extra_kwargs["language_detection_threshold"] = 0.45

        segments, info = model.transcribe(
            audio_data,
            language=lang_param,
            task=task,
            beam_size=5,
            vad_filter=vad_enabled,
            vad_parameters=vad_params,
            **extra_kwargs
        )

        texts = []
        for segment in segments:
            texts.append(segment.text.strip())

        full_text = " ".join(texts).strip()
        detected_lang = info.language
        lang_prob = info.language_probability

        return full_text, detected_lang, lang_prob

    def transcribe_file(self, file_path: str, language: str = None, progress_callback=None) -> tuple[str, list[dict], str]:
        """
        Транскрибирует аудио или видео файл.
        Возвращает: (полный текст, список сегментов с таймкодами, язык)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        model = self.get_model()

        if language is None or language == "auto":
            lang_param = None
        else:
            lang_param = language

        vad_enabled = config.get("vad_filter", True)
        vad_params = dict(min_silence_duration_ms=450, speech_pad_ms=250) if vad_enabled else None

        segments, info = model.transcribe(
            file_path,
            language=lang_param,
            beam_size=5,
            vad_filter=vad_enabled,
            vad_parameters=vad_params
        )

        result_segments = []
        texts = []

        total_duration = info.duration if hasattr(info, 'duration') and info.duration > 0 else 1.0

        for segment in segments:
            texts.append(segment.text.strip())
            result_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
            if progress_callback:
                progress = min(100, int((segment.end / total_duration) * 100))
                progress_callback(progress, segment.text.strip())

        full_text = "\n".join(texts).strip()
        return full_text, result_segments, info.language

def format_timestamp_srt(seconds: float) -> str:
    """Форматирует секунды в формат субтитров SRT: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

def export_to_srt(segments: list[dict]) -> str:
    """Генерирует содержимое SRT файла из сегментов."""
    lines = []
    for idx, seg in enumerate(segments, 1):
        start = format_timestamp_srt(seg["start"])
        end = format_timestamp_srt(seg["end"])
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)

# Глобальный инстанс движка
whisper_engine = WhisperEngine()
