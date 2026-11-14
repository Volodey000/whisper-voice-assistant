import os
import sys
import winreg

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WhisperVoiceAssistant"

def is_autostart_enabled() -> bool:
    try:
        proj_dir = os.path.dirname(os.path.abspath(__file__))
        target_vbs = os.path.join(proj_dir, "run_silent.vbs")

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            if not val:
                return False
            # Проверяем, что в автозапуске зарегистрирован именно текущий каталог приложения
            return target_vbs.lower() in str(val).lower()
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"[Autostart] Ошибка чтения реестра: {e}")
        return False

def enable_autostart() -> bool:
    try:
        proj_dir = os.path.dirname(os.path.abspath(__file__))
        target_vbs = os.path.join(proj_dir, "run_silent.vbs")

        if not os.path.exists(target_vbs):
            return False

        # wscript.exe "C:\...\run_silent.vbs" --minimized
        cmd = f'wscript.exe "{target_vbs}" --minimized'

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Autostart] Ошибка добавления в автозапуск: {e}")
        return False

def disable_autostart() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[Autostart] Ошибка удаления из автозапуска: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("enable", "on", "1"):
            res = enable_autostart()
            print("Автозапуск включен!" if res else "Ошибка включения автозапуска.")
        elif arg in ("disable", "off", "0"):
            res = disable_autostart()
            print("Автозапуск отключен!" if res else "Ошибка отключения автозапуска.")
        elif arg == "status":
            print(f"Статус автозапуска: {'Включен' if is_autostart_enabled() else 'Отключен'}")
    else:
        print(f"Текущий статус автозапуска: {'Включен' if is_autostart_enabled() else 'Отключен'}")
