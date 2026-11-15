# -*- coding: utf-8 -*-
"""
test_priority_and_double_paste.py:
1. Проверка приоритетного перехвата горячей клавиши (подавление для других приложений).
2. Защита от случайного двойного вызова (debounce/mutex).
3. Проверка того, что текст вставляется ровно один раз за вызов (без дублей).
4. Проверка последовательной двухкратной вставки (фраза 1, затем фраза 2 в одно поле).
"""

import sys
import os
import time
import ctypes
import pyperclip

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import cuda_setup

user32 = ctypes.windll.user32
h_default = user32.OpenDesktopW('Default', 0, False, 0x01FF)
if h_default:
    user32.SetThreadDesktop(h_default)

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout
from hotkey_manager import HotkeyManager
from paste_helper import handle_recognized_text
from main import VoiceAssistantApp

def test_hotkey_priority_and_debounce():
    print("--- 1. ТЕСТ ПРИОРИТЕТА И ЗАЩИТЫ ОТ ДВОЙНОГО СРАБАТЫВАНИЯ ---")
    app = QApplication.instance() or QApplication(['test', '--minimized'])

    hm = HotkeyManager()
    triggered = []
    hm.toggle_recording.connect(lambda task: triggered.append((task, time.time())))

    # Симулируем одновременный приход событий от Win32 RegisterHotKey и Low-level Hook (с интервалом 5 мс)
    hm._safe_dispatch_toggle("transcribe")
    hm._safe_dispatch_toggle("transcribe")  # должен быть отсечен debounce

    time.sleep(0.05)
    print(f"Срабатываний при одновременном вызове: {len(triggered)} (ожидается 1)")
    assert len(triggered) == 1, f"Двойное срабатывание не заблокировано! Число сигналов: {len(triggered)}"

    # Вызов спустя 0.5с (новое нажатие пользователя)
    time.sleep(0.5)
    hm._safe_dispatch_toggle("transcribe")
    time.sleep(0.05)
    print(f"Срабатываний после паузы: {len(triggered)} (ожидается 2)")
    assert len(triggered) == 2, f"Повторное нажатие не сработало! Число сигналов: {len(triggered)}"

    hm.unregister()
    print("[PASS] Защита от дребезга и двойного срабатывания работает идеально!\n")

def test_two_sequential_pastes():
    print("--- 2. ТЕСТ ДВУКРАТНОЙ ПОСЛЕДОВАТЕЛЬНОЙ ВСТАВКИ В ТЕКСТОВОЕ ПОЛЕ ---")
    app = QApplication.instance() or QApplication(['test', '--minimized'])

    # Создаем тестовое окно с полем ввода
    w = QWidget()
    w.setWindowTitle("Two Pastes Test")
    layout = QVBoxLayout(w)
    edit = QLineEdit(w)
    layout.addWidget(edit)
    w.show()
    w.raise_()
    w.activateWindow()
    edit.setFocus()

    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    hwnd = int(w.winId())
    user32.SetForegroundWindow(hwnd)

    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    assistant = VoiceAssistantApp(app)

    # ---------------- Вставка 1 ----------------
    phrase1 = "Первая фраза."
    print(f"Вставка 1: '{phrase1}'")
    assistant.target_window_hwnd = hwnd
    assistant._on_transcription_finished(phrase1, "ru", 1.5, task="transcribe")

    for _ in range(20):
        app.processEvents()
        time.sleep(0.04)

    val1 = edit.text()
    print(f"Текст в поле после 1-й вставки: '{val1}'")
    assert val1 == phrase1, f"Ошибка 1-й вставки: '{val1}' != '{phrase1}' (возможно двойная вставка!)"

    # Пауза между диктовками (как у реального пользователя)
    time.sleep(0.3)
    edit.setFocus()
    user32.SetForegroundWindow(hwnd)

    # ---------------- Вставка 2 ----------------
    phrase2 = " Вторая фраза."
    print(f"Вставка 2: '{phrase2}'")
    assistant.target_window_hwnd = hwnd
    assistant._on_transcription_finished(phrase2, "ru", 1.2, task="transcribe")

    for _ in range(20):
        app.processEvents()
        time.sleep(0.04)

    val2 = edit.text()
    expected = phrase1 + phrase2.strip()
    print(f"Текст в поле после 2-й вставки: '{val2}'")
    assert val2 == expected, f"Ошибка 2-й вставки: '{val2}' != '{expected}'"

    w.close()
    assistant.quit_app()
    print("[PASS] Обе фразы успешно и строго по одному разу вставились в поле ввода!\n")

def test_instant_duplicate_prevention():
    print("--- 3. ТЕСТ ПРЕДОТВРАЩЕНИЯ СЛУЧАЙНОЙ ДВОЙНОЙ ВСТАВКИ ОДНОГО ТЕКСТА ---")
    app = QApplication.instance() or QApplication(['test', '--minimized'])

    w = QWidget()
    w.setWindowTitle("Duplicate Prevention Test")
    layout = QVBoxLayout(w)
    edit = QLineEdit(w)
    layout.addWidget(edit)
    w.show()
    w.raise_()
    w.activateWindow()
    edit.setFocus()

    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)

    hwnd = int(w.winId())
    user32.SetForegroundWindow(hwnd)

    for _ in range(5):
        app.processEvents()
        time.sleep(0.02)

    test_word = "ОдиночнаяВставка"
    # Мгновенно вызываем вставку одного и того же текста 2 раза подряд
    res1 = handle_recognized_text(test_word, target_hwnd=hwnd)
    res2 = handle_recognized_text(test_word, target_hwnd=hwnd)

    for _ in range(20):
        app.processEvents()
        time.sleep(0.04)

    val = edit.text()
    w.close()

    print(f"Результат вызова 1: {res1}, вызова 2 (дубль): {res2}")
    print(f"Текст в поле: '{val}'")
    assert res1 is True and res2 is False, "Второй вызов должен быть отсечен дебаунсом!"
    assert val == test_word, f"Текст продублировался в поле: '{val}' != '{test_word}'"
    print("[PASS] Защита от дублирования предотвратила вторую вставку одного текста!\n")

if __name__ == "__main__":
    test_hotkey_priority_and_debounce()
    test_two_sequential_pastes()
    test_instant_duplicate_prevention()
    print("=" * 60)
    print(" ВСЕ ТЕСТЫ ПРИОРИТЕТА И ВСТАВКИ ПРОЙДЕНЫ! ")
    print("=" * 60)
