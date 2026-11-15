# -*- coding: utf-8 -*-
"""
hotkey_manager.py: Двухуровневая система глобальных горячих клавиш Windows с наивысшим
системным приоритетом над всеми открытыми приложениями (Win32 RegisterHotKey + low-level hook).
"""

import time
import threading
import ctypes
from ctypes import wintypes
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal
from config import config

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_MAP = {
    '`': 0xC0, '~': 0xC0, 'ё': 0xC0, 'grave': 0xC0,
    'space': 0x20, 'tab': 0x09, 'enter': 0x0D, 'return': 0x0D, 'esc': 0x1B, 'escape': 0x1B,
    'backspace': 0x08, 'capslock': 0x14,
    'pageup': 0x21, 'page_up': 0x21, 'pagedown': 0x22, 'page_down': 0x22,
    'end': 0x23, 'home': 0x24, 'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    'printscreen': 0x2C, 'insert': 0x2D, 'delete': 0x2E,
    '-': 0xBD, 'minus': 0xBD, '=': 0xBB, 'equal': 0xBB,
    '[': 0xDB, ']': 0xDD, '\\': 0xDC, ';': 0xBA, "'": 0xDE,
    ',': 0xBC, '.': 0xBE, '/': 0xBF
}
for i in range(1, 25):
    VK_MAP[f'f{i}'] = 0x70 + (i - 1)

def parse_hotkey_to_win32(hotkey_str: str) -> tuple[int, int] | None:
    """Преобразует строку горячей клавиши (напр. 'ctrl+`', 'alt+`', 'f8') в кортеж (modifiers, vk)."""
    if not hotkey_str:
        return None
    parts = [p.strip().lower() for p in hotkey_str.replace('+', ' ').split() if p.strip()]
    if not parts:
        return None

    mods = 0
    key = None
    for p in parts:
        if p in ('ctrl', 'control'):
            mods |= MOD_CONTROL
        elif p in ('alt', 'menu'):
            mods |= MOD_ALT
        elif p in ('shift',):
            mods |= MOD_SHIFT
        elif p in ('win', 'windows', 'super'):
            mods |= MOD_WIN
        else:
            key = p

    if not key:
        return None

    if key in VK_MAP:
        vk = VK_MAP[key]
    elif len(key) == 1:
        ch = key.upper()
        if 'A' <= ch <= 'Z' or '0' <= ch <= '9':
            vk = ord(ch)
        else:
            vk = user32.VkKeyScanW(ord(key)) & 0xFF
    else:
        return None

    return mods, vk

class Win32HotkeyThread(threading.Thread):
    """
    Поток системного перехвата с наивысшим приоритетом через Win32 RegisterHotKey.
    Гарантирует перехват горячей клавиши даже если другое приложение находится в фокусе.
    """
    def __init__(self, hotkeys: dict[int, tuple[int, int]], on_hotkey_callback):
        super().__init__(daemon=True)
        self.hotkeys = hotkeys  # id -> (mods, vk)
        self.callback = on_hotkey_callback
        self.thread_id = None
        self._running = True
        self.registered_ids = []

    def run(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        for hk_id, (mods, vk) in self.hotkeys.items():
            # Регистрация с флагом MOD_NOREPEAT (наивысший приоритет ОС Windows, без дребезга)
            if user32.RegisterHotKey(None, hk_id, mods | MOD_NOREPEAT, vk):
                self.registered_ids.append(hk_id)
            else:
                if user32.RegisterHotKey(None, hk_id, mods, vk):
                    self.registered_ids.append(hk_id)

        msg = wintypes.MSG()
        while self._running:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
            if msg.message == 0x0312:  # WM_HOTKEY
                hk_id = msg.wParam
                if self.callback:
                    self.callback(hk_id)
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        for hk_id in self.registered_ids:
            user32.UnregisterHotKey(None, hk_id)

    def stop(self):
        self._running = False
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)  # WM_QUIT

def _patch_winkeyboard():
    """Исправляет хуки клавиатуры в окружениях Python на Windows."""
    try:
        import keyboard._winkeyboard as w
        if getattr(w, '_whisper_patched', False):
            return

        if hasattr(w, 'SetWindowsHookEx'):
            orig_SetWindowsHookEx = w.SetWindowsHookEx

            def safe_SetWindowsHookEx(idHook, lpfn, hMod, dwThreadId):
                res = orig_SetWindowsHookEx(idHook, lpfn, 0, dwThreadId)
                if not res:
                    res = orig_SetWindowsHookEx(idHook, lpfn, hMod, dwThreadId)
                return res

            w.SetWindowsHookEx = safe_SetWindowsHookEx

        if hasattr(w, '_setup_name_tables'):
            orig_setup = w._setup_name_tables

            def patched_setup():
                orig_setup()
                entry_oem3 = [(0, (41, 192, 0, ())), (0, (41, 192, 1, ()))]
                for alias in [chr(96), "`", "grave", "~", "ё"]:
                    if not w.from_name.get(alias):
                        w.from_name[alias].extend(entry_oem3)

                qwerty_scan_codes = {
                    'q': 16, 'w': 17, 'e': 18, 'r': 19, 't': 20, 'y': 21, 'u': 22, 'i': 23, 'o': 24, 'p': 25,
                    'a': 30, 's': 31, 'd': 32, 'f': 33, 'g': 34, 'h': 35, 'j': 36, 'k': 37, 'l': 38,
                    'z': 44, 'x': 45, 'c': 46, 'v': 47, 'b': 48, 'n': 49, 'm': 50
                }
                for letter, sc in qwerty_scan_codes.items():
                    if not w.from_name.get(letter):
                        vk = ord(letter.upper())
                        w.from_name[letter].extend([(0, (sc, vk, 0, ())), (0, (sc, vk, 1, ()))])

            w._setup_name_tables = patched_setup
            patched_setup()

        w._whisper_patched = True
    except Exception as e:
        print(f"[Hotkey] Замечание по патчу хука: {e}")

_patch_winkeyboard()

class HotkeyManager(QObject):
    toggle_recording = pyqtSignal(str)   # task: "transcribe" или "translate"
    start_recording = pyqtSignal(str)    # task: "transcribe" или "translate"
    stop_recording = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current_hotkey = None
        self._current_translate_hotkey = None
        self._hook_refs = []
        self._is_holding = False
        self._win32_thread = None
        self._last_toggle_time = 0.0
        self._lock = threading.Lock()

    def _safe_dispatch_toggle(self, task: str = "transcribe"):
        """Потокобезопасный диспетчер с защитой от двойного срабатывания."""
        with self._lock:
            now = time.time()
            if now - self._last_toggle_time < 0.40:
                return
            self._last_toggle_time = now
        self.toggle_recording.emit(task)

    def setup(self):
        self.unregister()
        hotkey = config.get("hotkey", "ctrl+`").lower().strip()
        trans_hk = config.get("translate_hotkey", "alt+`").lower().strip()
        mode = config.get("hotkey_mode", "toggle")
        self._current_hotkey = hotkey
        self._current_translate_hotkey = trans_hk

        print(f"[Hotkey] Регистрация горячей клавиши диктовки: '{hotkey}' (режим: {mode})")

        # -------------------------------------------------------------
        # УРОВЕНЬ 1: Win32 RegisterHotKey (Системный перехват ОС)
        # -------------------------------------------------------------
        if mode == "toggle":
            hk_parsed = parse_hotkey_to_win32(hotkey)
            trans_parsed = parse_hotkey_to_win32(trans_hk) if (trans_hk and trans_hk != hotkey) else None

            win32_dict = {}
            if hk_parsed:
                win32_dict[1] = hk_parsed
            if trans_parsed:
                win32_dict[2] = trans_parsed

            if win32_dict:
                def _on_win32_hotkey(hid):
                    task = "translate" if hid == 2 else "transcribe"
                    self._safe_dispatch_toggle(task)

                self._win32_thread = Win32HotkeyThread(win32_dict, _on_win32_hotkey)
                self._win32_thread.start()
                time.sleep(0.05)
                registered = self._win32_thread.registered_ids
                if 1 in registered:
                    print(f"[Hotkey] Приоритетный системный перехват RegisterHotKey для '{hotkey}' активен.")
                if 2 in registered:
                    print(f"[Hotkey] Приоритетный системный перехват RegisterHotKey для '{trans_hk}' активен.")

        # -------------------------------------------------------------
        # УРОВЕНЬ 2: Low-Level Hook с SUPPRESS=TRUE (Абсолютный приоритет над другими приложениями)
        # -------------------------------------------------------------
        # suppress=True блокирует передачу горячей клавиши другим приложениям (VS Code, браузеры, игры),
        # гарантируя, что даже если в другом окне настроена такая же клавиша,
        # событие перехватывается ИСКЛЮЧИТЕЛЬНО Whisper Voice Assistant!
        try:
            if mode == "hold":
                # Режим рации (Push-to-talk)
                def on_down(e):
                    with self._lock:
                        if not self._is_holding:
                            self._is_holding = True
                            self.start_recording.emit("transcribe")

                def on_up(e):
                    with self._lock:
                        if self._is_holding:
                            self._is_holding = False
                            self.stop_recording.emit()

                h1 = keyboard.on_press_key(hotkey, on_down, suppress=True)
                h2 = keyboard.on_release_key(hotkey, on_up, suppress=True)
                self._hook_refs.extend([h1, h2])
            else:
                # Перехват для toggle режима с подавлением для других приложений
                h = keyboard.add_hotkey(hotkey, lambda: self._safe_dispatch_toggle("transcribe"), suppress=True)
                self._hook_refs.append(h)
        except Exception as e:
            print(f"[Hotkey] Замечание по регистрации клавиши '{hotkey}': {e}")

        # Горячая клавиша перевода (RU -> EN)
        if trans_hk and trans_hk != hotkey:
            try:
                if mode == "hold":
                    def on_trans_down(e):
                        with self._lock:
                            if not self._is_holding:
                                self._is_holding = True
                                self.start_recording.emit("translate")

                    def on_trans_up(e):
                        with self._lock:
                            if self._is_holding:
                                self._is_holding = False
                                self.stop_recording.emit()

                    th1 = keyboard.on_press_key(trans_hk, on_trans_down, suppress=True)
                    th2 = keyboard.on_release_key(trans_hk, on_trans_up, suppress=True)
                    self._hook_refs.extend([th1, th2])
                else:
                    th = keyboard.add_hotkey(trans_hk, lambda: self._safe_dispatch_toggle("translate"), suppress=True)
                    self._hook_refs.append(th)
            except Exception as e_trans:
                print(f"[Hotkey] Замечание по клавише перевода '{trans_hk}': {e_trans}")

    def unregister(self):
        if self._win32_thread:
            try:
                self._win32_thread.stop()
                self._win32_thread.join(0.5)
            except Exception:
                pass
            self._win32_thread = None

        try:
            for h in self._hook_refs:
                try:
                    keyboard.remove_hotkey(h)
                except Exception:
                    try:
                        keyboard.unhook(h)
                    except Exception:
                        pass
            self._hook_refs.clear()
            self._is_holding = False
        except Exception as e:
            print(f"[Hotkey] Ошибка снятия перехвата: {e}")
