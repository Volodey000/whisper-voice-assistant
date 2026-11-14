import sys
import os
import subprocess
import importlib
import shutil

# Гарантируем корректный вывод UTF-8 в консоли Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe")

# Список обязательных пакетов для работы Whisper Voice Assistant
REQUIRED_PACKAGES = [
    ("PyQt6", "PyQt6>=6.5.0"),
    ("torch", "torch>=2.0.0"),
    ("faster_whisper", "faster-whisper>=1.0.0"),
    ("sounddevice", "sounddevice>=0.5.0"),
    ("soundfile", "soundfile>=0.12.0"),
    ("keyboard", "keyboard>=0.13.5"),
    ("pyperclip", "pyperclip>=1.8.0"),
    ("numpy", "numpy>=1.24.0")
]

def has_nvidia_gpu() -> bool:
    """Проверяет наличие видеокарты NVIDIA и установленных драйверов CUDA в Windows."""
    # 1. Проверка системной библиотеки драйвера NVIDIA CUDA
    if os.path.exists(r"C:\Windows\System32\nvcuda.dll"):
        return True
    # 2. Проверка утилиты nvidia-smi
    if shutil.which("nvidia-smi") is not None:
        return True
    return False

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
    """
    Устанавливает недостающие пакеты через pip текущего Python.
    Для PyTorch автоматически выбирает оптимальную сборку:
    - с аппаратным ускорением CUDA для ПК с видеокартами NVIDIA
    - легковесную сборку CPU для ноутбуков и офисных ПК
    """
    print("=" * 60)
    print(" [Whisper Voice Assistant] Автоматическая установка компонентов")
    print("=" * 60)
    print(f"Обнаружены недостающие библиотеки: {len(packages)} шт.")
    for p in packages:
        print(f"  -> {p}")
    print("\nПожалуйста, подождите, идет скачивание и установка...")
    print("Это требуется только один раз при первом запуске на новом устройстве.\n")

    # Обновляем pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], capture_output=True)
    except Exception:
        pass

    # Отдельно обрабатываем PyTorch, если он в списке недостающих
    torch_pkgs = [p for p in packages if p.startswith("torch")]
    other_pkgs = [p for p in packages if not p.startswith("torch")]

    if torch_pkgs:
        is_nvidia = has_nvidia_gpu()
        if is_nvidia:
            print("[Установка] Обнаружена видеокарта NVIDIA. Загрузка PyTorch с аппаратным ускорением CUDA 12.1...")
            torch_cmd = [
                sys.executable, "-m", "pip", "install",
                "torch>=2.0.0",
                "--index-url", "https://download.pytorch.org/whl/cu121"
            ]
        else:
            print("[Установка] Дискретная видеокарта NVIDIA не найдена. Загрузка легковесной сборки PyTorch (CPU)...")
            torch_cmd = [
                sys.executable, "-m", "pip", "install",
                "torch>=2.0.0",
                "--index-url", "https://download.pytorch.org/whl/cpu"
            ]

        try:
            print(f"  Выполняется: {' '.join(torch_cmd)}")
            res = subprocess.run(torch_cmd, check=True)
        except Exception as e:
            print(f"[Установка] Специализированная установка не удалась ({e}). Пробуем стандартный pip install torch...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "torch>=2.0.0"], check=True)
            except Exception as e_std:
                print(f"[Ошибка] Не удалось установить PyTorch: {e_std}")
                return False

    if other_pkgs:
        print(f"[Установка] Установка остальных компонентов ({len(other_pkgs)} шт.)...")
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + other_pkgs
        try:
            res = subprocess.run(cmd, check=True)
            if res.returncode != 0:
                return False
        except Exception as e:
            print(f"[Ошибка] Не удалось установить пакеты через pip: {e}")
            return False

    print("\n[Успех] Все необходимые библиотеки успешно установлены!")
    return True

def check_torch_status():
    """Проверяет состояние PyTorch и доступность CUDA/CPU."""
    try:
        import torch
        ver = torch.__version__
        cuda_avail = torch.cuda.is_available()
        if cuda_avail:
            gpu_name = torch.cuda.get_device_name(0)
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = vram_bytes / (1024 ** 3)
            print(f"[PyTorch] Версия: {ver} | CUDA ускорение: ВКЛЮЧЕНО (GPU: {gpu_name}, {vram_gb:.1f} ГБ VRAM)")
        else:
            print(f"[PyTorch] Версия: {ver} | Режим CPU: Готов (квантование INT8 оптимизировано)")
        return True
    except Exception as e:
        print(f"[PyTorch] Предупреждение инициализации torch: {e}")
        return False

def check_and_fix_audio_devices():
    """Проверяет звуковые устройства и предотвращает сбои при несовпадающих ID."""
    try:
        import sounddevice as sd
        from config import config

        devs = sd.query_devices()
        input_devs = [idx for idx, d in enumerate(devs) if d.get('max_input_channels', 0) > 0]

        if not input_devs:
            print("[Аудио] Внимание: на этом ПК не найден подключенный микрофон.")
            print("[Аудио] Подключите микрофон или проверьте параметры конфиденциальности Windows.")
        else:
            default_in = sd.default.device[0]
            print(f"[Аудио] Микрофоны обнаружены (всего {len(input_devs)} шт.). Устройство по умолчанию: ID {default_in}")

        cur_idx = config.get("input_device_index", None)
        if cur_idx is not None and cur_idx not in input_devs:
            print(f"[Настройка аудио] Предыдущий микрофон (ID {cur_idx}) не найден на этом компьютере.")
            print("[Настройка аудио] Сброс на 'Микрофон по умолчанию Windows'.")
            config.set("input_device_index", None)
    except Exception as e:
        print(f"[Аудио] Замечание при проверке микрофона: {e}")

def check_models_availability():
    """Проверяет наличие локальных моделей в папке models/."""
    models_dir = os.path.join(PROJECT_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)

    available = []
    try:
        for item in os.listdir(models_dir):
            p = os.path.join(models_dir, item)
            if os.path.isdir(p):
                bin_f = os.path.join(p, "model.bin")
                if os.path.exists(bin_f) and os.path.getsize(bin_f) > 1000000:
                    available.append(item)
    except Exception:
        pass

    if available:
        print(f"[Модели] Готовы локально в папке models/: {', '.join(available)}")
    else:
        print("[Модели] Локальная папка models/ готова. Модель Whisper скачается автоматически при первом распознавании.")

def ensure_app_icons_and_shortcut():
    """Создает файлы app_icon.ico, app_icon.png и ярлык Start Whisper.lnk при их отсутствии или переезде."""
    try:
        ico_path = os.path.join(PROJECT_DIR, "app_icon.ico")
        png_path = os.path.join(PROJECT_DIR, "app_icon.png")

        if not os.path.exists(ico_path) or not os.path.exists(png_path):
            from icons import save_app_icons
            save_app_icons(PROJECT_DIR)

        # Создание / обновление ярлыка Start Whisper.lnk
        target_bat = os.path.join(PROJECT_DIR, "start_whisper.bat")
        lnk_path = os.path.join(PROJECT_DIR, "Start Whisper.lnk")

        shortcut_created = False
        try:
            import win32com.client
            wsh = win32com.client.Dispatch("WScript.Shell")
            sc = wsh.CreateShortcut(lnk_path)
            sc.TargetPath = target_bat
            sc.WorkingDirectory = PROJECT_DIR
            sc.IconLocation = f"{ico_path}, 0"
            sc.Description = "Whisper Voice Assistant"
            sc.Save()
            shortcut_created = True
        except Exception:
            pass

        # Fallback через системный PowerShell
        if not shortcut_created and not os.path.exists(lnk_path):
            try:
                ps_cmd = (
                    f"$ws = New-Object -ComObject WScript.Shell; "
                    f"$s = $ws.CreateShortcut('{lnk_path}'); "
                    f"$s.TargetPath = '{target_bat}'; "
                    f"$s.WorkingDirectory = '{PROJECT_DIR}'; "
                    f"$s.IconLocation = '{ico_path}, 0'; "
                    f"$s.Description = 'Whisper Voice Assistant'; "
                    f"$s.Save()"
                )
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            except Exception:
                pass
    except Exception as e:
        print(f"[Ярлык] Замечание: {e}")

def ensure_venv() -> bool:
    """
    Проверяет существование .venv. Если отсутствует или поврежден, создает новый.
    Возвращает True, если окружение готово.
    """
    if os.path.exists(VENV_PY):
        try:
            res = subprocess.run([VENV_PY, "-c", "import sys"], capture_output=True)
            if res.returncode == 0:
                return True
        except Exception:
            pass
        # Если поврежден, удаляем
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    print("[Окружение] Создание изолированного виртуального окружения .venv...")
    try:
        import venv
        venv.create(VENV_DIR, with_pip=True)
        return True
    except Exception as e:
        print(f"[Окружение] Ошибка venv.create: {e}. Попытка через sys.executable...")
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
            return True
        except Exception as e2:
            print(f"[Окружение] Не удалось создать .venv: {e2}")
            return False

def main():
    print("=" * 60)
    print(" [Whisper Voice Assistant] Диагностика и проверка компонентов")
    print("=" * 60)
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

    # Проверка PyTorch и CUDA
    check_torch_status()

    # Проверка аудио, моделей, иконок и ярлыка
    check_and_fix_audio_devices()
    check_models_availability()
    ensure_app_icons_and_shortcut()
    print("\n[Проверка] Все компоненты и зависимости готовы к работе!\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
