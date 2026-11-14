import os
import sys
import ctypes
from config import config

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

SW_HIDE = 0
SW_SHOW = 5
SW_RESTORE = 9

_console_allocated = False

def set_console_visible(visible: bool):
    """
    Показывает или полностью скрывает окно консоли Windows на лету.
    """
    hwnd = kernel32.GetConsoleWindow()

    if visible:
        if hwnd == 0:
            global _console_allocated
            if not _console_allocated:
                kernel32.AllocConsole()
                _console_allocated = True
                try:
                    sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                    sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                except Exception:
                    pass
            hwnd = kernel32.GetConsoleWindow()

        if hwnd != 0:
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.ShowWindow(hwnd, SW_RESTORE)
    else:
        if hwnd != 0:
            user32.ShowWindow(hwnd, SW_HIDE)

def is_console_visible() -> bool:
    hwnd = kernel32.GetConsoleWindow()
    if hwnd == 0:
        return False
    return bool(user32.IsWindowVisible(hwnd))

def apply_console_preference():
    """Применяет сохраненное состояние консоли при старте приложения."""
    show = config.get("show_console", False)
    set_console_visible(show)
