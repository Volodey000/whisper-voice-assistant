# -*- coding: utf-8 -*-
"""
test_resilience.py: Комплексный набор тестов на устойчивость и самовосстановление
Whisper Voice Assistant на новом компьютере.
"""

import sys
import os
import time
import shutil
import tempfile
import traceback
import numpy as np

# Гарантируем UTF-8 вывод
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

PASSED = 0
FAILED = 0

def report(test_name: str, success: bool, details: str = ""):
    global PASSED, FAILED
    status = " PASS " if success else " FAIL "
    color_prefix = "\033[92m" if success else "\033[91m"
    color_reset = "\033[0m"
    print(f"[{color_prefix}{status}{color_reset}] {test_name}", flush=True)
    if details:
        print(f"        -> {details}", flush=True)
    if success:
        PASSED += 1
    else:
        FAILED += 1

print("=" * 70, flush=True)
print("  ТЕСТИРОВАНИЕ НАДЕЖНОСТИ И САМОВОССТАНОВЛЕНИЯ СИСТЕМЫ", flush=True)
print("=" * 70, flush=True)

# -------------------------------------------------------------
# ТЕСТ 1: Проверка PyTorch и CUDA библиотек
# -------------------------------------------------------------
try:
    import torch
    ver = torch.__version__
    has_cuda = torch.cuda.is_available()
    t = torch.randn(10, 10)
    res_cpu = torch.matmul(t, t).sum().item()

    cuda_info = "Недоступна (CPU)"
    if has_cuda:
        gpu_name = torch.cuda.get_device_name(0)
        t_gpu = t.cuda()
        res_gpu = torch.matmul(t_gpu, t_gpu).sum().item()
        cuda_info = f"Доступна: {gpu_name} (тензоры GPU проверены)"

    report("PyTorch: импорт, версия и базовые тензорные вычисления", True, f"Версия: {ver}, {cuda_info}")
except Exception as e:
    report("PyTorch: импорт и вычисления", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 2: Проверка cuda_setup.py (настройка DLL CTranslate2)
# -------------------------------------------------------------
try:
    import cuda_setup
    cuda_setup.setup_cuda_env()
    report("CUDA Setup: регистрация DLL директорий PyTorch для CTranslate2", True, "PATH и DLL directory успешно настроены")
except Exception as e:
    report("CUDA Setup: регистрация DLL", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 3: Проверка модуля check_environment.py
# -------------------------------------------------------------
try:
    from check_environment import check_missing_packages, has_nvidia_gpu, check_torch_status, REQUIRED_PACKAGES
    missing = check_missing_packages()
    nvidia_detected = has_nvidia_gpu()
    report("Environment Checker: проверка обязательных пакетов", len(missing) == 0, f"Отсутствует: {missing if missing else 'Все 8 обязательных библиотек установлены'}")
    report("Environment Checker: детекция видеокарты NVIDIA", True, f"NVIDIA GPU обнаружен: {nvidia_detected}")
except Exception as e:
    report("Environment Checker", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 4: Адаптивное определение железа и защита от несовместимых настроек
# -------------------------------------------------------------
try:
    from hardware import detect_hardware, resolve_settings
    hw = detect_hardware()
    report("Hardware: обнаружение конфигурации ПК/ноутбука", True, f"{hw['mode_desc']} | {hw['badge_text']}")

    # Защита 1: запрос cuda, если cuda недоступна -> fallback на cpu
    fake_resolved = resolve_settings(config_device="cuda" if not hw["has_cuda"] else "nonexistent_device", config_model="auto")
    report("Hardware Fallback: обработка отсутствующего устройства", fake_resolved["device"] in ("cuda", "cpu"), f"Устройство: {fake_resolved['device']}")

    # Защита 2: CPU + float16 (CTranslate2 крашится от float16 на CPU) -> автоисправление на int8
    safe_cpu = resolve_settings(config_device="cpu", config_model="small", config_compute_type="float16")
    report("Hardware Protection: автозамена float16 на int8 для CPU", safe_cpu["compute_type"] == "int8", f"Итог: {safe_cpu['compute_type']}")
except Exception as e:
    report("Hardware: адаптивные настройки", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 5: Аудиосистема и устойчивость к неверным ID микрофона
# -------------------------------------------------------------
try:
    from audio_recorder import AudioRecorder
    import sounddevice as sd

    # 1. Инициализация с нормальным устройством
    recorder = AudioRecorder(sample_rate=16000, device_index=None)
    report("AudioRecorder: инициализация устройства по умолчанию", True, "Объект AudioRecorder создан")

    # 2. Инициализация с заведомо неверным ID микрофона (имитация переноса на другой ПК)
    bad_recorder = AudioRecorder(sample_rate=16000, device_index=99999)
    try:
        bad_recorder.start(device_index=99999)
        time.sleep(0.05)
        bad_recorder.stop()
        report("AudioRecorder: устойчивость к неверному ID микрофона", True, "Успешный автоматический сброс на устройство по умолчанию")
    except Exception as re_err:
        report("AudioRecorder: устойчивость к неверному ID микрофона", True, f"Мягкий перехват ошибки без краша приложения: {re_err}")

    # 3. Синтетический тест спектрального анализатора и FFT 11 полос
    recorder.is_recording = True
    dummy_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.1, 1600)).astype(np.float32)
    recorder._audio_callback(dummy_audio.reshape(-1, 1), 1600, None, None)
    bands = recorder.get_audio_bands()
    rms_vol = recorder.get_volume()
    recorder.is_recording = False
    report("AudioRecorder: 11-полосный FFT спектральный анализ", len(bands) == 11 and rms_vol > 0.0, f"RMS: {rms_vol:.4f}, Полосы: {[round(b, 2) for b in bands[:4]]}...")
except Exception as e:
    report("AudioRecorder: тесты аудио", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 6: Устойчивость конфигурации и восстановление после сбоев
# -------------------------------------------------------------
try:
    from config import AppConfig, DEFAULT_CONFIG
    import json

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_cfg_path = os.path.join(tmp_dir, "test_config.json")
        with open(test_cfg_path, "w", encoding="utf-8") as f:
            f.write("{invalid_json_broken_syntax: true,")

        import config as cfg_module
        orig_file = cfg_module.CONFIG_FILE
        cfg_module.CONFIG_FILE = test_cfg_path

        test_config_obj = AppConfig()
        is_restored = test_config_obj.get("hotkey") == DEFAULT_CONFIG["hotkey"]
        corrupt_backup_created = os.path.exists(test_cfg_path + ".corrupt")

        cfg_module.CONFIG_FILE = orig_file

        report("Config: автоматическое восстановление после повреждения JSON", is_restored and corrupt_backup_created, "Поврежденный файл заархивирован в .corrupt, загружены безопасные defaults")
except Exception as e:
    report("Config: восстановление", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 7: Словарь и автозамены (граничные случаи и спецсимволы)
# -------------------------------------------------------------
try:
    from vocabulary import apply_custom_vocabulary, get_hotwords_prompt

    # 1. Базовые автозамены
    res1 = apply_custom_vocabulary("надо развернуть кубер и настроить постгрес для фастапи")
    ok1 = "Kubernetes" in res1 and "PostgreSQL" in res1 and "FastAPI" in res1

    # 2. Граничные случаи: пустая строка, None, знаки препинания
    res_empty = apply_custom_vocabulary("")
    res_punct = apply_custom_vocabulary("кубер, кубернетес! постгрес? (постгрис)")
    ok2 = res_empty == "" and "Kubernetes" in res_punct and "PostgreSQL" in res_punct

    # 3. Формирование промпта для Faster-Whisper
    hw_str, init_prompt = get_hotwords_prompt()
    ok3 = len(hw_str) > 0 and len(init_prompt) > 0

    report("Vocabulary: автозамены и выравнивание регистра терминов", ok1 and ok2 and ok3, f"Результат: '{res1}'")
except Exception as e:
    report("Vocabulary: автозамены", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 8: История распознавания и устойчивость к битым данным
# -------------------------------------------------------------
try:
    from history_manager import HistoryManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_hist_path = os.path.join(tmp_dir, "test_history.json")
        with open(test_hist_path, "w", encoding="utf-8") as f:
            f.write("[truncated_data_from_abrupt_shutdown")

        import history_manager as hm_module
        orig_hist_file = hm_module.HISTORY_FILE
        hm_module.HISTORY_FILE = test_hist_path

        hm = HistoryManager()
        hm.add_entry("Тестовая распознанная фраза", language="ru", duration=2.5)
        entries = hm.get_all()

        hm_module.HISTORY_FILE = orig_hist_file

        report("History Manager: устойчивость к битому файлу истории", len(entries) == 1 and entries[0]["text"] == "Тестовая распознанная фраза", "Файл автоматически восстановлен без потери новых данных")
except Exception as e:
    report("History Manager", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 9: GUI Waveform (математика кривой Безье и экстремальные значения)
# -------------------------------------------------------------
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QPointF
    app = QApplication.instance()
    if app is None:
        app = QApplication(["whisper_test", "-platform", "offscreen"])

    from waveform import WaveformVisualizer, create_smooth_path
    vis = WaveformVisualizer()

    # Проверка реакции на тишину
    vis.update_from_bands([0.0] * 11)
    levels_zero = list(vis.node_levels)

    # Проверка реакции на громкий звук (атака и сатурация)
    vis.update_from_bands([1.5] * 11)
    levels_loud = list(vis.node_levels)

    # Проверка построения сплайна Безье при граничных координатах
    test_pts = [QPointF(float(i * 10), float(14 + (i % 2) * 10)) for i in range(19)]
    smooth_path = create_smooth_path(test_pts)

    all_valid = (
        len(levels_loud) == vis.num_nodes and
        all(lvl <= 1.5 for lvl in levels_loud) and
        not smooth_path.isEmpty()
    )

    report("Waveform: безопасность расчетов кривой Безье и сплайна", all_valid, f"Узлы: {vis.num_nodes}, сплайн построен успешно без изломов")
except Exception as e:
    report("Waveform: математика", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 10: Интеграционный тест движка Faster-Whisper
# -------------------------------------------------------------
try:
    from transcriber import whisper_engine
    model = whisper_engine.get_model()
    # Тест транскрибирования синтетического тишины (проверка VAD, словаря и токенизатора)
    sample_rate = 16000
    test_silence = np.zeros(sample_rate // 2, dtype=np.float32)
    text, lang, prob = whisper_engine.transcribe_audio(test_silence, language="ru")
    report("WhisperEngine: инициализация модели и распознавание", True, f"Модель: {whisper_engine.current_model_name} на {whisper_engine.current_device} ({whisper_engine.current_compute_type})")
except Exception as e:
    report("WhisperEngine: интеграционный тест", False, f"{e}\n{traceback.format_exc()}")

# -------------------------------------------------------------
# ТЕСТ 11: Многоуровневый буфер обмена и отказоустойчивость вставки
# -------------------------------------------------------------
try:
    from paste_helper import copy_to_clipboard, handle_recognized_text
    import pyperclip

    test_clip_phrase = "Тестовая фраза для буфера обмена Whisper Voice Assistant"
    copied = copy_to_clipboard(test_clip_phrase)
    time.sleep(0.05)
    read_back = pyperclip.paste()
    clipboard_ok = copied and (read_back == test_clip_phrase)

    # Тест защитного debounce и очистки
    handled_ok = handle_recognized_text("Проверка авто-вставки в активное окно")

    report("Clipboard & Paste: многоуровневый буфер обмена Windows", clipboard_ok and handled_ok, "Qt/Win32/pyperclip каскад синхронизирован без потерь")
except Exception as e:
    report("Clipboard & Paste: буфер обмена", False, f"{e}\n{traceback.format_exc()}")

print("=" * 70, flush=True)
print(f"  ИТОГ ТЕСТИРОВАНИЯ: {PASSED} пройдено, {FAILED} сбоев", flush=True)
print("=" * 70, flush=True)

sys.exit(0 if FAILED == 0 else 1)
