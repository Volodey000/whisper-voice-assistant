# -*- coding: utf-8 -*-
"""
contracts.py: Слой контрактов и типизированных структур данных (DTO).
Единый источник истины (Single Source of Truth) для Whisper Voice Assistant.

В соответствии с ARCHITECTURE.md (Contract-First):
- Содержит только типы, dataclasses, TypedDict и Protocol.
- Никакой бизнес-логики, обращений к диску или GUI.
- Все новые поля должны иметь значения по умолчанию (обратная совместимость).
"""

from typing import TypedDict, Optional, Literal, Protocol, runtime_checkable, Any
from dataclasses import dataclass, field


# =====================================================================
# 1. СХЕМА КОНФИГУРАЦИИ (Config Contract)
# =====================================================================

class ConfigDict(TypedDict, total=False):
    """Словарь параметров конфигурации config.json."""
    hotkey: str
    translate_hotkey: str
    hotkey_mode: Literal["toggle", "hold"]
    clean_fillers: bool
    custom_vocabulary_enabled: bool
    hotwords: str
    replacements: dict[str, str]
    model_name: str
    language: str
    device: str
    compute_type: str
    auto_paste: bool
    always_clipboard: bool
    play_sounds: bool
    sound_theme: Literal["hifi", "classic"]
    show_overlay: bool
    overlay_position: Literal["top_center", "bottom_center", "top_right", "bottom_right", "cursor", "custom"]
    overlay_custom_pos: Optional[list[int]]
    vad_filter: bool
    fast_lang_detect: bool
    noise_gate: bool
    noise_gate_level: Literal["soft", "medium", "aggressive"]
    input_device_index: Optional[int]
    start_minimized: bool
    show_console: bool


# =====================================================================
# 2. ИСТОРИЯ И ТРАНСКРИБАЦИЯ (Data Transfer Objects)
# =====================================================================

class HistoryEntryDict(TypedDict):
    """Структура записи в файле history.json."""
    id: int
    timestamp: str
    text: str
    language: str
    duration: float


@dataclass(frozen=True)
class HistoryEntry:
    """Неизменяемый DTO одной записи истории распознавания."""
    id: int
    timestamp: str
    text: str
    language: str
    duration: float

    def to_dict(self) -> HistoryEntryDict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "text": self.text,
            "language": self.language,
            "duration": self.duration
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HistoryEntry":
        return cls(
            id=int(data.get("id", 0)),
            timestamp=str(data.get("timestamp", "")),
            text=str(data.get("text", "")).strip(),
            language=str(data.get("language", "RU")).upper(),
            duration=float(data.get("duration", 0.0))
        )


@dataclass
class TranscriptionSegment:
    """Сегмент расшифровки аудиофайла с временными метками."""
    id: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    """Результат распознавания аудиофрагмента или файла."""
    text: str
    language: str
    duration: float
    task: Literal["transcribe", "translate"] = "transcribe"
    probability: float = 1.0
    segments: list[dict[str, Any]] = field(default_factory=list)


# =====================================================================
# 3. АППАРАТНЫЙ ПРОФИЛЬ (Hardware Profile DTO)
# =====================================================================

@dataclass(frozen=True)
class HardwareProfile:
    """Характеристики и рекомендации по оборудованию (GPU/CPU)."""
    has_cuda: bool
    gpu_name: str
    vram_gb: float
    cpu_threads: int
    recommended_device: Literal["cuda", "cpu"]
    recommended_compute_type: Literal["float16", "int8", "float32"]
    recommended_model: str
    badge_text: str
    mode_desc: str


# =====================================================================
# 4. АУДИО И СПЕКТР (Audio Contracts)
# =====================================================================

@dataclass
class AudioAnalysis:
    """Результаты спектрального и уровневого анализа микрофона."""
    rms: float
    spectrum_bands: list[float]
    is_speech: bool = True


# =====================================================================
# 5. ИНТЕРФЕЙСЫ И ПРОТОКОЛЫ (Protocols / Abstract Contracts)
# =====================================================================

@runtime_checkable
class TranscriberProtocol(Protocol):
    """Интерфейс движка распознавания речи."""
    def get_model(self) -> Any: ...
    def transcribe_audio(
        self,
        audio_data: Any,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> tuple[str, str, float]: ...
    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> tuple[str, list[dict[str, Any]], str]: ...


@runtime_checkable
class AudioRecorderProtocol(Protocol):
    """Интерфейс аудиорекордера микрофона."""
    def start(self) -> None: ...
    def stop(self) -> tuple[Any, float]: ...
    def cancel(self) -> None: ...
    def is_recording(self) -> bool: ...
    def get_spectrum_bands(self) -> list[float]: ...
    def get_current_rms(self) -> float: ...


@runtime_checkable
class PasteHelperProtocol(Protocol):
    """Интерфейс помощника вставки текста в активное окно ОС."""
    def paste_text(self, text: str) -> bool: ...
    def copy_to_clipboard(self, text: str) -> None: ...
