import sys
import os
import subprocess
import importlib

# Гарантируем корректный вывод UTF-8 в консоли Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Список обязательных пакетов для работы Whisper Voice Assistant
REQUIRED_PACKAGES = [
    ("PyQt6", "PyQt6>=6.5.0"),
    ("faster_whisper", "faster-whisper>=1.0.0"),
    ("sounddevice", "sounddevice>=0.5.0"),
    ("soundfile", "soundfile>=0.12.0"),
    ("keyboard", "keyboard>=0.13.5"),
    ("pyperclip", "pyperclip>=1.8.0"),
    ("numpy", "numpy>=1.24.0")
]

def check_missing_packages():
    """Проверяет, какие из обязательных библиотек отсутствуют."""
    missing = []
    for mod_name, pip_spec in REQUIRED_PACKAGES:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing.append(pip_spec)
        except Exception as e:
            # Например, сбой зависимых dll
            print(f"[Внимание] Ошибка при проверке модуля {mod_name}: {e}")
            missing.append(pip_spec)
    return missing

def install_packages(packages):
    """Устанавливает недостающие пакеты через pip текущего Python."""
    print("=" * 60)
    print(" [Whisper Voice Assistant] Автоматическая установка компонентов")
    print("=" * 60)
    print(f"Обнаружены недостающие библиотеки: {len(packages)} шт.")
    for p in packages:
        print(f"  -> {p}")
    print("\nПожалуйста, подождите, идет скачивание и установка...")
    print("Это требуется только один раз при первом запуске на новом устройстве.\n")

    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + packages
    try:
        res = subprocess.run(cmd, check=True)
        if res.returncode == 0:
            print("\n[Успех] Все необходимые библиотеки успешно установлены!")
            return True
    except Exception as e:
        print(f"\n[Ошибка] Не удалось установить пакеты через pip: {e}")
        return False
    return False

def check_and_fix_audio_devices():
    """Проверяет звуковые устройства и предотвращает сбои при несовпадающих ID."""
    try:
        import sounddevice as sd
        from config import config

        devs = sd.query_devices()
        input_devs = [idx for idx, d in enumerate(devs) if d.get('max_input_channels', 0) > 0]

        if not input_devs:
            print("[Аудио] Предупреждение: на этом ПК не найден подключенный микрофон.")

        cur_idx = config.get("input_device_index", None)
        if cur_idx is not None and cur_idx not in input_devs:
            print(f"[Настройка аудио] Предыдущий микрофон (ID {cur_idx}) не найден на этом компьютере.")
            print("[Настройка аудио] Сброс на 'Микрофон по умолчанию Windows'.")
            config.set("input_device_index", None)
    except Exception as e:
        print(f"[Аудио] Замечание при проверке микрофона: {e}")

def check_models_availability():
    """Проверяет наличие локальных моделей в папке models/."""
    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    if not os.path.exists(models_dir):
        os.makedirs(models_dir, exist_ok=True)

    available = []
    for item in os.listdir(models_dir):
        p = os.path.join(models_dir, item)
        if os.path.isdir(p):
            bin_f = os.path.join(p, "model.bin")
            if os.path.exists(bin_f) and os.path.getsize(bin_f) > 1000000:
                available.append(item)

    if available:
        print(f"[Модели] Готовы локально в папке models/: {', '.join(available)}")
    else:
        print("[Модели] Локальные модели не обнаружены в папке models/. При первом распознавании модель скачается автоматически.")

def ensure_app_icons_and_shortcut():
    """Создает файлы app_icon.ico, app_icon.png и ярлык Start Whisper.lnk при их отсутствии или переезде."""
    try:
        proj_dir = os.path.dirname(os.path.abspath(__file__))
        ico_path = os.path.join(proj_dir, "app_icon.ico")
        png_path = os.path.join(proj_dir, "app_icon.png")

        if not os.path.exists(ico_path) or not os.path.exists(png_path):
            from icons import save_app_icons
            save_app_icons(proj_dir)

        # Создание / обновление ярлыка Start Whisper.lnk
        target_bat = os.path.join(proj_dir, "start_whisper.bat")
        lnk_path = os.path.join(proj_dir, "Start Whisper.lnk")

        try:
            import win32com.client
            wsh = win32com.client.Dispatch("WScript.Shell")
            sc = wsh.CreateShortcut(lnk_path)
            sc.TargetPath = target_bat
            sc.WorkingDirectory = proj_dir
            sc.IconLocation = f"{ico_path}, 0"
            sc.Description = "Whisper Voice Assistant"
            sc.Save()
        except Exception:
            pass
    except Exception as e:
        print(f"[Ярлык] Замечание: {e}")

def main():
    print("[Проверка] Проверка установленных библиотек...")
    missing = check_missing_packages()

    if missing:
        success = install_packages(missing)
        if not success:
            sys.exit(1)

        # Повторная проверка
        still_missing = check_missing_packages()
        if still_missing:
            print(f"[Ошибка] Следующие пакеты не удалось загрузить: {still_missing}")
            sys.exit(1)

    # Проверка аудио, моделей, иконок и ярлыка
    check_and_fix_audio_devices()
    check_models_availability()
    ensure_app_icons_and_shortcut()
    print("[Проверка] Все компоненты готовы к работе!\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
