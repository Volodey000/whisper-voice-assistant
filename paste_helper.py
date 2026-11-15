# -*- coding: utf-8 -*-
"""
paste_helper.py: Надежная работа с буфером обмена Windows и автоматическая вставка (Ctrl+V)
с многоуровневым каскадом (Qt Clipboard -> 64-bit Win32 API -> Pyperclip),
восстановлением фокуса целевого окна и поддержкой SendInput.
"""

import time
import ctypes
from ctypes import wintypes
import pyperclip
from config import config

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12       # Alt
VK_V = 0x56
VK_LWIN = 0x5B
VK_RWIN = 0x5C

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13
INPUT_KEYBOARD = 1

# -------------------------------------------------------------
# Структуры для Windows SendInput
# -------------------------------------------------------------
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION)
    ]

# -------------------------------------------------------------
# Точная типизация Win32 API для 64-битных дескрипторов (HGLOBAL, HWND)
# -------------------------------------------------------------
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL

user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

_last_paste_time = 0.0
_last_pasted_text = ""

def _win32_set_clipboard_text(text: str) -> bool:
    """Прямая запись текста в буфер обмена Windows через 64-битный Win32 API с повторными попытками."""
    opened = False
    for _ in range(8):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.02)
    if not opened:
        return False

    try:
        user32.EmptyClipboard()
        text_bytes = (text + '\0').encode('utf-16le')
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
        if not h_mem:
            return False
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            kernel32.GlobalFree(h_mem)
            return False
        ctypes.memmove(ptr, text_bytes, len(text_bytes))
        kernel32.GlobalUnlock(h_mem)
        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
            kernel32.GlobalFree(h_mem)
            return False
        return True
    finally:
        user32.CloseClipboard()

def copy_to_clipboard(text: str) -> bool:
    """
    Многоуровневый каскад копирования текста в буфер обмена Windows:
    1. Прямой вызов 64-битного Win32 API (OpenClipboard + CF_UNICODETEXT) для гарантированной записи в буфер ОС.
    2. Нативный Qt Clipboard для синхронизации с внутренними компонентами интерфейса.
    3. Резервный вызов pyperclip.copy().
    """
    if not text:
        return False

    success = False

    # Уровень 1: Прямой 64-битный Win32 API (системный уровень Windows, доступен всем приложениям)
    try:
        if _win32_set_clipboard_text(text):
            success = True
    except Exception as e_win32:
        print(f"[Clipboard] Win32 Clipboard info: {e_win32}")

    # Уровень 2: Синхронизация с Qt Clipboard
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QClipboard
        app = QApplication.instance()
        if app is not None and getattr(app, "platformName", lambda: "")() != "offscreen":
            cb = app.clipboard()
            cb.setText(text, QClipboard.Mode.Clipboard)
            success = True
    except Exception as e_qt:
        print(f"[Clipboard] Qt Clipboard info: {e_qt}")

    # Уровень 3: Резервный вызов pyperclip
    if not success:
        try:
            pyperclip.copy(text)
            success = True
        except Exception as e_pyperclip:
            print(f"[Clipboard] Ошибка pyperclip: {e_pyperclip}")

    return success

def wait_for_physical_modifiers_released(timeout: float = 0.35):
    """
    Ожидает, пока пользователь физически отпустит клавиши-модификаторы
    (Ctrl, Alt, Shift, Win), нажатые при использовании горячей клавиши.
    """
    start = time.time()
    while time.time() - start < timeout:
        ctrl_held = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
        alt_held = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
        shift_held = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        win_held = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))
        if not (ctrl_held or alt_held or shift_held or win_held):
            break
        time.sleep(0.015)

def release_all_modifiers():
    """
    Принудительно отправляет событие KEYEVENTF_KEYUP для всех модификаторов,
    чтобы Windows не удерживала виртуальный Ctrl, Alt или Shift перед отправкой Ctrl+V.
    """
    for vk in (VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN, VK_CONTROL):
        sc = user32.MapVirtualKeyW(vk, 0)
        user32.keybd_event(vk, sc, KEYEVENTF_KEYUP, 0)

def restore_target_focus(hwnd):
    """
    Восстанавливает фокус ввода в целевое окно, где находился курсор пользователя
    в момент запуска записи.
    """
    if not hwnd or not user32.IsWindow(hwnd):
        return
    try:
        cur_fg = user32.GetForegroundWindow()
        if cur_fg == hwnd:
            return

        cur_thread = kernel32.GetCurrentThreadId()
        fg_thread = user32.GetWindowThreadProcessId(cur_fg, None)
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        if fg_thread and target_thread and fg_thread != target_thread:
            user32.AttachThreadInput(cur_thread, target_thread, True)
            user32.AttachThreadInput(fg_thread, target_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(cur_thread, target_thread, False)
            user32.AttachThreadInput(fg_thread, target_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
        time.sleep(0.025)
    except Exception as e:
        print(f"[Focus] Восстановление фокуса окна: {e}")

def _send_ctrl_v_sendinput() -> tuple[bool, int]:
    """
    Атомарная отправка Ctrl+V через SendInput.
    Возвращает (success: bool, count_sent: int).
    """
    try:
        sc_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0) or 29
        sc_v = user32.MapVirtualKeyW(VK_V, 0) or 47

        events = (INPUT * 4)()

        # 1. Ctrl Down
        events[0].type = INPUT_KEYBOARD
        events[0].u.ki.wVk = VK_CONTROL
        events[0].u.ki.wScan = sc_ctrl
        events[0].u.ki.dwFlags = 0

        # 2. V Down
        events[1].type = INPUT_KEYBOARD
        events[1].u.ki.wVk = VK_V
        events[1].u.ki.wScan = sc_v
        events[1].u.ki.dwFlags = 0

        # 3. V Up
        events[2].type = INPUT_KEYBOARD
        events[2].u.ki.wVk = VK_V
        events[2].u.ki.wScan = sc_v
        events[2].u.ki.dwFlags = KEYEVENTF_KEYUP

        # 4. Ctrl Up
        events[3].type = INPUT_KEYBOARD
        events[3].u.ki.wVk = VK_CONTROL
        events[3].u.ki.wScan = sc_ctrl
        events[3].u.ki.dwFlags = KEYEVENTF_KEYUP

        sent = user32.SendInput(4, events, ctypes.sizeof(INPUT))
        return (sent == 4), sent
    except Exception:
        return False, 0

def _send_ctrl_v_keybd_event():
    """Резервная отправка Ctrl+V через keybd_event."""
    sc_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0) or 29
    sc_v = user32.MapVirtualKeyW(VK_V, 0) or 47

    # Гарантируем, что клавиши отпущены
    user32.keybd_event(VK_CONTROL, sc_ctrl, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_V, sc_v, KEYEVENTF_KEYUP, 0)
    time.sleep(0.015)

    # Нажатие Ctrl+V
    user32.keybd_event(VK_CONTROL, sc_ctrl, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, sc_v, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, sc_v, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, sc_ctrl, KEYEVENTF_KEYUP, 0)

def simulate_paste(target_hwnd=None):
    """
    Чистая эмуляция вставки Ctrl+V в целевое окно:
    1. Восстанавливает фокус в окне, где стоял курсор.
    2. Ожидает физического отпускания пользователем клавиш горячей клавиши.
    3. Снимает любое виртуальное зажатие модификаторов (Alt, Shift, Ctrl).
    4. Отправляет атомарную связку Ctrl+V (SendInput с безопасным fallback).
    """
    try:
        # 1. Восстанавливаем фокус в окно пользователя (если окно потеряло фокус)
        if target_hwnd:
            restore_target_focus(target_hwnd)

        # 2. Ждем физического отпускания клавиш после остановки записи
        wait_for_physical_modifiers_released(0.35)

        # 3. Принудительно отпускаем все модификаторы
        release_all_modifiers()
        time.sleep(0.025)

        # 4. Пробуем современный атомарный SendInput
        success_sendinput, count_sent = _send_ctrl_v_sendinput()
        if not success_sendinput and count_sent == 0:
            # Fallback на keybd_event запускается СТРОГО если SendInput не отправил ни одного события (0).
            # Это на 100% исключает двойную вставку текста!
            _send_ctrl_v_keybd_event()

        # 5. Финальное подтверждение снятия зажатия
        release_all_modifiers()
    except Exception as e:
        print(f"[Paste] Ошибка отправки клавиш Ctrl+V: {e}")

def handle_recognized_text(text: str, target_hwnd=None) -> bool:
    """
    1. Защита от случайного повторного вызова (debounce).
    2. Всегда помещает текст в буфер обмена Windows через многоуровневый каскад.
    3. Если включена авто-вставка — отправляет чистый Ctrl+V в окно с курсором.
    """
    global _last_paste_time, _last_pasted_text

    if not text or not text.strip():
        return False

    cleaned_text = text.strip()
    now = time.time()

    # Защита от дублей: если тот же текст вызывается быстрее чем за 0.8 сек
    if cleaned_text == _last_pasted_text and (now - _last_paste_time < 0.8):
        print("[Paste] Повторный вызов вставки дублирующего текста пропущен (debounce).")
        return False

    _last_paste_time = now
    _last_pasted_text = cleaned_text

    # Шаг 1: ВСЕГДА сохраняем в буфер обмена Windows
    copied = copy_to_clipboard(cleaned_text)

    # Шаг 2: При необходимости отправляем Ctrl+V в окно курсора
    if config.get("auto_paste", True):
        simulate_paste(target_hwnd=target_hwnd)

    return copied
