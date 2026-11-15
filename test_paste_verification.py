# -*- coding: utf-8 -*-
"""
test_paste_verification.py: Комплексный тест устойчивости приложения,
копирования в буфер обмена и автоматической вставки в активное текстовое поле.
"""

import sys
import os
import time
import ctypes
import numpy as np
import pyperclip

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

# Переключаем поток на интерактивный рабочий стол Windows 'Default'
user32 = ctypes.windll.user32
h_default = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if h_default:
    user32.SetThreadDesktop(h_default)

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout
from paste_helper import copy_to_clipboard, handle_recognized_text
from main import VoiceAssistantApp
from history_manager import history

def run_tests():
    print("=" * 60)
    print("  ПРОВЕРКА СТАБИЛЬНОСТИ, БУФЕРА ОБМЕНА И АВТО-ВСТАВКИ")
    print("=" * 60)

    app = QApplication.instance()
    if app is None:
        app = QApplication(['whisper_test', '--minimized'])

    # -------------------------------------------------------------
    # 1. ТЕСТ: Инициализация и стабильность приложения (без вылетов)
    # -------------------------------------------------------------
    print("\n[ТЕСТ 1/3] Инициализация VoiceAssistantApp...")
    assistant = VoiceAssistantApp(app)

    assert assistant.recorder is not None, "AudioRecorder не инициализирован"
    assert assistant.transcriber is not None, "WhisperEngine не инициализирован"
    assert assistant.overlay is not None, "Overlay не создан"
    assert assistant.main_window is not None, "MainWindow не создано"
    assert assistant.tray is not None, "TrayIcon не создан"
    assert assistant.hotkey_mgr is not None, "HotkeyManager не создан"

    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    print(" -> Приложение успешно запущено без сбоев (Audio, Whisper, Tray, Overlay, Hotkeys готовы).")

    # -------------------------------------------------------------
    # 2. ТЕСТ: Копирование в буфер обмена Windows
    # -------------------------------------------------------------
    print("\n[ТЕСТ 2/3] Проверка многоуровневого буфера обмена Windows...")
    test_phrase = "Проверка буфера: Привет, мир! Hello World 123! #%&"
    copied = copy_to_clipboard(test_phrase)
    time.sleep(0.05)
    read_back = pyperclip.paste()

    assert copied is True, "copy_to_clipboard вернул False"
    assert read_back == test_phrase, f"Текст в буфере не совпал: '{read_back}' != '{test_phrase}'"
    print(f" -> Текст гарантированно записан в буфер Windows: '{read_back}'")

    # -------------------------------------------------------------
    # 3. ТЕСТ: Вставка в текущее активное текстовое поле (Ctrl+V)
    # -------------------------------------------------------------
    print("\n[ТЕСТ 3/3] Проверка автоматической вставки в активное поле ввода...")
    # Создаем окно с полем ввода
    w = QWidget()
    w.setWindowTitle("Target Field for Auto-Paste")
    layout = QVBoxLayout(w)
    edit = QLineEdit(w)
    edit.setPlaceholderText("Ожидание вставки текста...")
    layout.addWidget(edit)
    w.show()
    w.raise_()
    w.activateWindow()
    edit.setFocus()

    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    target_hwnd = int(w.winId())
    user32.SetForegroundWindow(target_hwnd)

    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    dictated_phrase = "Распознанный текст: мгновенная авто-вставка в активное поле работает отлично!"
    assistant.target_window_hwnd = target_hwnd

    # Симулируем успешное завершение распознавания
    assistant._on_transcription_finished(dictated_phrase, "ru", 2.0, task="transcribe")

    # Даем циклу событий ОС Windows и Qt обработать SendInput
    pasted = False
    start_time = time.time()
    while time.time() - start_time < 2.0:
        app.processEvents()
        time.sleep(0.04)
        if edit.text() == dictated_phrase:
            pasted = True
            break

    result_text = edit.text()
    w.close()

    assert pasted, f"Текст не вставился в текстовое поле! В поле: '{result_text}', ожидалось: '{dictated_phrase}'"
    print(f" -> Текст успешно вставлен в текстовое поле: '{result_text}'")

    # Проверяем, что в буфере обмена именно этот текст
    clip_after = pyperclip.paste()
    assert clip_after == dictated_phrase, f"Буфер обмена не обновился: '{clip_after}'"
    print(f" -> Буфер обмена также содержит актуальный текст.")

    # Проверяем запись в истории
    all_hist = history.get_all()
    assert len(all_hist) > 0 and all_hist[0]["text"] == dictated_phrase, "История не сохранила запись"
    print(f" -> Запись истории добавлена (всего записей: {len(all_hist)}).")

    # Завершаем приложение
    assistant.quit_app()

    print("\n" + "=" * 60)
    print("  РЕЗУЛЬТАТ: ВСЕ 3 ТРЕБОВАНИЯ ПОЛНОСТЬЮ ПОДТВЕРЖДЕНЫ! ")
    print("  1. Приложение стабильно инициализируется и не вываливается.")
    print("  2. Текст гарантированно копируется в системный буфер обмена.")
    print("  3. Текст автоматически вставляется в активное текстовое поле.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        run_tests()
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА] {e}")
        traceback.print_exc()
        sys.exit(1)
