import time
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal
from config import config

def _patch_winkeyboard():
    """
    1. Исправляет ошибку SetWindowsHookEx (Error 126 / ERROR_MOD_NOT_FOUND)
       в виртуальных окружениях Python .venv, где GetModuleHandleW(None) указывает
       на stub-лаунчер. Для глобального хука WH_KEYBOARD_LL параметр hMod должен быть 0 (NULL).
    2. Обеспечивает корректную работу клавиш backtick (`), ё и латинских букв
       в Windows независимо от того, какая раскладка (русская/английская) активна.
    """
    try:
        import keyboard._winkeyboard as w
        if getattr(w, '_whisper_patched', False):
            return

        # Патч 1: SetWindowsHookEx c hMod=0 для WH_KEYBOARD_LL
        if hasattr(w, 'SetWindowsHookEx'):
            orig_SetWindowsHookEx = w.SetWindowsHookEx

            def safe_SetWindowsHookEx(idHook, lpfn, hMod, dwThreadId):
                # Для WH_KEYBOARD_LL (13) передаем hMod=0 (NULL), что гарантирует успешную регистрацию в .venv
                res = orig_SetWindowsHookEx(idHook, lpfn, 0, dwThreadId)
                if not res:
                    res = orig_SetWindowsHookEx(idHook, lpfn, hMod, dwThreadId)
                return res

            w.SetWindowsHookEx = safe_SetWindowsHookEx

        # Патч 2: Таблицы раскладки клавиш
        if hasattr(w, '_setup_name_tables'):
            orig_setup = w._setup_name_tables

            def patched_setup():
                orig_setup()
                # Scan code 41 = физическая клавиша ` / ~ / ё (VK 192 / 0xC0)
                entry_oem3 = [(0, (41, 192, 0, ())), (0, (41, 192, 1, ()))]
                for alias in [chr(96), "`", "grave", "~", "ё"]:
                    if not w.from_name.get(alias):
                        w.from_name[alias].extend(entry_oem3)

                # Добавляем стандартные сканкоды QWERTY клавиш a-z
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

    def setup(self):
        self.unregister()
        hotkey = config.get("hotkey", "ctrl+`").lower().strip()
        trans_hk = config.get("translate_hotkey", "alt+`").lower().strip()
        mode = config.get("hotkey_mode", "toggle")
        self._current_hotkey = hotkey
        self._current_translate_hotkey = trans_hk

        print(f"[Hotkey] Регистрация горячей клавиши диктовки: '{hotkey}' (режим: {mode})")

        # 1. Основная клавиша диктовки
        try:
            if mode == "hold":
                # Режим рации (Push-to-talk)
                def on_down(e):
                    if not self._is_holding:
                        self._is_holding = True
                        self.start_recording.emit("transcribe")

                def on_up(e):
                    if self._is_holding:
                        self._is_holding = False
                        self.stop_recording.emit()

                h1 = keyboard.on_press_key(hotkey, on_down, suppress=False)
                h2 = keyboard.on_release_key(hotkey, on_up, suppress=False)
                self._hook_refs.extend([h1, h2])
            else:
                # Режим переключения (Toggle: нажал - говорит, нажал - остановил)
                _last_toggle = 0.0

                def on_toggle():
                    nonlocal _last_toggle
                    now = time.time()
                    if now - _last_toggle < 0.35:
                        return
                    _last_toggle = now
                    self.toggle_recording.emit("transcribe")

                h = keyboard.add_hotkey(hotkey, on_toggle, suppress=False)
                self._hook_refs.append(h)
        except Exception as e:
            print(f"[Hotkey] Ошибка регистрации клавиши '{hotkey}': {e}")
            if hotkey != "f8":
                print("[Hotkey] Регистрация безопасной резервной клавиши F8...")
                try:
                    if mode == "hold":
                        h1 = keyboard.on_press_key("f8", on_down, suppress=False)
                        h2 = keyboard.on_release_key("f8", on_up, suppress=False)
                        self._hook_refs.extend([h1, h2])
                    else:
                        h = keyboard.add_hotkey("f8", on_toggle, suppress=False)
                        self._hook_refs.append(h)
                    self._current_hotkey = "f8"
                    print("[Hotkey] Резервная клавиша F8 успешно подключена.")
                except Exception as e_fallback:
                    print(f"[Hotkey] Критический сбой горячих клавиш: {e_fallback}")

        # 2. Горячая клавиша мгновенного перевода на английский (RU -> EN)
        if trans_hk and trans_hk != hotkey:
            print(f"[Hotkey] Регистрация горячей клавиши перевода: '{trans_hk}' (RU -> EN)")
            try:
                if mode == "hold":
                    def on_trans_down(e):
                        if not self._is_holding:
                            self._is_holding = True
                            self.start_recording.emit("translate")

                    def on_trans_up(e):
                        if self._is_holding:
                            self._is_holding = False
                            self.stop_recording.emit()

                    th1 = keyboard.on_press_key(trans_hk, on_trans_down, suppress=False)
                    th2 = keyboard.on_release_key(trans_hk, on_trans_up, suppress=False)
                    self._hook_refs.extend([th1, th2])
                else:
                    _last_trans_toggle = 0.0

                    def on_trans_toggle():
                        nonlocal _last_trans_toggle
                        now = time.time()
                        if now - _last_trans_toggle < 0.35:
                            return
                        _last_trans_toggle = now
                        self.toggle_recording.emit("translate")

                    th = keyboard.add_hotkey(trans_hk, on_trans_toggle, suppress=False)
                    self._hook_refs.append(th)
            except Exception as e_trans:
                print(f"[Hotkey] Замечание по клавише перевода '{trans_hk}': {e_trans}")

    def unregister(self):
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
