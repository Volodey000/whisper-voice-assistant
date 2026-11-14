import time
import ctypes
import pyperclip
from config import config

user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_V = 0x56
VK_ALT = 0x12
VK_SHIFT = 0x10
KEYEVENTF_KEYUP = 0x0002

_last_paste_time = 0.0

def copy_to_clipboard(text: str) -> bool:
    """Всегда копирует текст в буфер обмена Windows."""
    if not text:
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        print(f"[Clipboard] Ошибка pyperclip: {e}")
        return False

def wait_for_physical_modifiers_released(timeout: float = 0.4):
    """
    Ожидает, пока пользователь физически отпустит клавишу Ctrl (и другие модификаторы),
    нажатые при использовании горячей клавиши (Ctrl + `).
    Если не подождать — Windows видит зажатый Ctrl от клавиатуры и эмулирует повторный ввод!
    """
    start = time.time()
    while time.time() - start < timeout:
        ctrl_held = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
        alt_held = bool(user32.GetAsyncKeyState(VK_ALT) & 0x8000)
        shift_held = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        if not (ctrl_held or alt_held or shift_held):
            break
        time.sleep(0.015)

def simulate_paste():
    """
    Чистая эмуляция нажатия Ctrl+V с защитой от двойной вставки:
    1. Ожидаем физического отпускания пользователем клавиши Ctrl.
    2. Используем точные сканкоды клавиш (Ctrl: 29, V: 47).
    3. Отправляем строго однократное нажатие с гарантированным снятием зажатия.
    """
    try:
        # 1. Ждем физического отпускания Ctrl после остановки записи
        wait_for_physical_modifiers_released(0.4)

        # Небольшая пауза для стабилизации фокуса в целевом окне
        time.sleep(0.05)

        sc_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0) or 29
        sc_v = user32.MapVirtualKeyW(VK_V, 0) or 47

        # Принудительно убеждаемся, что клавиши отпущены перед нажатием
        user32.keybd_event(VK_CONTROL, sc_ctrl, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_V, sc_v, KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)

        # Четкая связка: Ctrl Down -> V Down -> V Up -> Ctrl Up
        user32.keybd_event(VK_CONTROL, sc_ctrl, 0, 0)
        time.sleep(0.015)
        user32.keybd_event(VK_V, sc_v, 0, 0)
        time.sleep(0.015)
        user32.keybd_event(VK_V, sc_v, KEYEVENTF_KEYUP, 0)
        time.sleep(0.015)
        user32.keybd_event(VK_CONTROL, sc_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception as e:
        print(f"[Paste] Ошибка отправки клавиш Ctrl+V: {e}")

def handle_recognized_text(text: str) -> bool:
    """
    1. Защита от случайного повторного вызова (debounce).
    2. Всегда помещает текст в буфер обмена Windows.
    3. Если включена авто-вставка — отправляет одиночный чистый Ctrl+V в активное окно.
    """
    global _last_paste_time
    now = time.time()
    if now - _last_paste_time < 0.5:
        print("[Paste] Повторный вызов вставки пропущен (debounce).")
        return False

    if not text or not text.strip():
        return False

    _last_paste_time = now
    cleaned_text = text.strip()

    # Шаг 1: ВСЕГДА сохраняем в буфер обмена
    copied = copy_to_clipboard(cleaned_text)

    # Шаг 2: При необходимости отправляем Ctrl+V
    if config.get("auto_paste", True):
        simulate_paste()

    return copied
