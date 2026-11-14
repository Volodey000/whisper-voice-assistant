import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "hotkey": "ctrl+`",
    "translate_hotkey": "alt+`",      # Горячая клавиша мгновенного перевода на английский (RU -> EN)
    "hotkey_mode": "toggle",          # "toggle" (нажать для старта/стопа) или "hold" (удерживать при речи)
    "clean_fillers": True,            # Очистка слов-паразитов, междометий и заиканий (э-э, ну, повторы)
    "model_name": "auto",             # "auto" (автовыбор: GPU -> large-v3-turbo, CPU/ноутбук -> small), "large-v3-turbo", "medium", "small", "base"
    "language": "auto",               # "auto", "ru", "en"
    "device": "auto",                 # "auto" (автовыбор: cuda или cpu), "cuda", "cpu"
    "compute_type": "auto",           # "auto" (float16 для GPU, int8 для CPU), "float16", "int8"
    "auto_paste": True,               # Пытаться вставить в активное окно (Ctrl+V)
    "always_clipboard": True,         # ВСЕГДА копировать распознанный текст в буфер
    "play_sounds": True,              # Звуковой отклик при старте и завершении записи
    "sound_theme": "hifi",            # "hifi" (студийные мягкие перезвоны), "classic" (beep)
    "show_overlay": True,             # Плавающий индикатор записи/распознавания
    "overlay_position": "top_center", # "top_center", "bottom_center", "top_right", "bottom_right", "cursor", "custom"
    "overlay_custom_pos": None,       # [x, y] при ручном перетаскивании
    "vad_filter": True,               # Фильтр пауз и тишины (Silero VAD)
    "fast_lang_detect": True,         # Быстрое определение языка без задержки
    "noise_gate": True,               # Шумоподавление фонового шума
    "noise_gate_level": "medium",     # "soft" (0.005), "medium" (0.009), "aggressive" (0.016)
    "input_device_index": None,       # None - микрофон по умолчанию Windows
    "start_minimized": False,         # Запускаться свернутым в трей
    "show_console": False             # Показать/скрыть окно консоли Windows
}

class AppConfig:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Config] Ошибка чтения {CONFIG_FILE}: {e}. Восстановление настроек по умолчанию.")
                # Если файл поврежден (0 байт от внезапного выключения), создаем резервную копию и перезаписываем
                try:
                    corrupt_path = CONFIG_FILE + ".corrupt"
                    if os.path.exists(CONFIG_FILE):
                        os.replace(CONFIG_FILE, corrupt_path)
                except Exception:
                    pass
                self.save()
        else:
            self.save()

    def save(self):
        try:
            tmp_file = CONFIG_FILE + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, CONFIG_FILE)
        except Exception as e:
            print(f"[Config] Ошибка сохранения {CONFIG_FILE}: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

# Глобальный экземпляр настроек
config = AppConfig()
