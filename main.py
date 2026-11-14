import sys
import os
import subprocess
import ctypes

# Гарантируем поддержку UTF-8 в консоли Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# -------------------------------------------------------------
# 0. Автоматическая проверка и самоинициализация виртуального окружения (.venv)
# -------------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_DIR, ".venv")
VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe")

def _bootstrap_environment():
    in_local_venv = os.path.abspath(sys.prefix).lower() == os.path.abspath(VENV_DIR).lower()

    if not in_local_venv and os.environ.get("WHISPER_NO_VENV") != "1":
        venv_ready = False
        if os.path.exists(VENV_PY):
            try:
                res = subprocess.run([VENV_PY, "-c", "import sys"], capture_output=True)
                if res.returncode == 0:
                    venv_ready = True
            except Exception:
                venv_ready = False

        if not venv_ready:
            print("=" * 60)
            print(" [Whisper Voice Assistant] Первоначальная настройка на новом ПК")
            print("=" * 60)
            print("[Инфо] Создание изолированного виртуального окружения .venv...")
            try:
                import venv
                venv.create(VENV_DIR, with_pip=True)
                venv_ready = True
            except Exception as e:
                print(f"[Предупреждение] Ошибка venv.create: {e}. Попытка через subprocess...")
                try:
                    subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
                    venv_ready = True
                except Exception as e2:
                    print(f"[Ошибка] Не удалось создать .venv: {e2}")

        if venv_ready and os.path.exists(VENV_PY):
            cmd = [VENV_PY, os.path.abspath(__file__)] + sys.argv[1:]
            sys.exit(subprocess.call(cmd))

    # Внутри .venv проверяем обязательные пакеты (включая torch) ДО импорта PyQt6
    try:
        from check_environment import check_missing_packages, install_packages, check_and_fix_audio_devices, ensure_app_icons_and_shortcut
        missing = check_missing_packages()
        if missing:
            print("[Whisper Voice Assistant] Обнаружены недостающие компоненты. Автоматическая установка...")
            ok = install_packages(missing)
            if not ok:
                print("[Whisper Voice Assistant] Ошибка: Не удалось установить зависимости.")
                sys.exit(1)
        check_and_fix_audio_devices()
        ensure_app_icons_and_shortcut()
    except Exception as e_check:
        print(f"[Whisper Voice Assistant] Замечание предстартовой проверки: {e_check}")

_bootstrap_environment()

import traceback
def _global_excepthook(exc_type, exc_value, exc_tb):
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=== UNHANDLED EXCEPTION ===\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
sys.excepthook = _global_excepthook

# 1. Настройка CUDA окружения перед остальными импортами
import cuda_setup

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from config import config
from audio_recorder import AudioRecorder
from transcriber import whisper_engine
from sound_effects import play_start_sound, play_stop_sound, play_success_sound, play_cancel_sound
from paste_helper import handle_recognized_text
from history_manager import history
from overlay import RecordingOverlay
from hotkey_manager import HotkeyManager
from workers import LiveTranscriptionWorker
from gui import MainWindow
from tray import TrayIcon
from console_manager import apply_console_preference
from hotkey_recorder import format_hotkey_display
from icons import get_app_icon

class VoiceAssistantApp:
    def __init__(self, q_app):
        self.app = q_app
        self.recorder = AudioRecorder(device_index=config.get("input_device_index"))
        self.transcriber = whisper_engine
        self.worker = None

        # Создаем компоненты интерфейса
        self.overlay = RecordingOverlay(recorder=self.recorder)
        self.main_window = MainWindow(self.recorder, self.transcriber)
        self.tray = TrayIcon(self.main_window)
        self.main_window.tray = self.tray
        self.tray.show()
        self.hotkey_mgr = HotkeyManager()
        self.current_task = "transcribe"

        self._setup_ipc_server()
        self._connect_signals()

        # Регистрация глобальных горячих клавиш
        self.hotkey_mgr.setup()

        # Показ окна при старте
        start_min = config.get("start_minimized", False) or ("--minimized" in sys.argv)
        if not start_min:
            self.main_window.show_and_activate()
        else:
            hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
            self.tray.showMessage(
                "Whisper Voice Assistant",
                f"Приложение запущено в трее. Нажмите [{hotkey_str}] для диктовки!",
                self.tray.icon(),
                3000
            )

    def _setup_ipc_server(self):
        self.local_server = QLocalServer(self.app)
        server_name = "WhisperVoiceAssistant_IPC"
        QLocalServer.removeServer(server_name)
        self.local_server.listen(server_name)
        self.local_server.newConnection.connect(self._on_ipc_connection)

    def _on_ipc_connection(self):
        client = self.local_server.nextPendingConnection()
        if client:
            client.readyRead.connect(lambda: self._handle_ipc_message(client))
            self.main_window.show_and_activate()

    def _handle_ipc_message(self, client):
        try:
            _ = bytes(client.readAll()).decode('utf-8', errors='ignore')
        except Exception:
            pass
        self.main_window.show_and_activate()

    def _connect_signals(self):
        # Сигналы от горячей клавиши
        self.hotkey_mgr.toggle_recording.connect(self.toggle_recording)
        self.hotkey_mgr.start_recording.connect(self.start_recording)
        self.hotkey_mgr.stop_recording.connect(self.stop_recording)

        # Сигнал от оверлея (кнопка крестика отмены записи)
        self.overlay.cancel_requested.connect(self.cancel_recording)

        # Сигналы от GUI
        self.main_window.request_toggle_recording.connect(self.toggle_recording)
        self.main_window.request_quit.connect(self.quit_app)
        self.main_window.settings_saved.connect(self._on_settings_saved)

    def _on_settings_saved(self):
        print("[App] Настройки обновлены. Перезапуск горячей клавиши...")
        self.hotkey_mgr.setup()
        self.tray.update_tooltip()
        self.recorder.device_index = config.get("input_device_index", None)
        self.overlay._apply_position()

    def toggle_recording(self, task: str = "transcribe"):
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording(task=task)

    def start_recording(self, task: str = "transcribe"):
        if self.recorder.is_recording:
            return

        self.current_task = task
        dev_idx = config.get("input_device_index", None)
        try:
            self.recorder.start(device_index=dev_idx)
        except Exception as e:
            err_msg = str(e)
            print(f"[App] Ошибка старта записи: {err_msg}")
            self.overlay.show_error("Микрофон недоступен", "Проверьте микрофон или доступ в Windows")
            return

        play_start_sound()
        self.overlay.show_recording(task=task)
        self.tray.set_recording_state(True, task=task)
        self.main_window.set_recording_state(True, task=task)

    def stop_recording(self):
        if not self.recorder.is_recording:
            return

        dur = self.recorder.get_duration()
        audio_data = self.recorder.stop()

        play_stop_sound()
        self.tray.set_recording_state(False)
        self.main_window.set_recording_state(False)

        if audio_data is None or len(audio_data) < 1600:
            self.overlay.hide_overlay()
            return

        self.overlay.show_processing(task=self.current_task)

        # Запускаем распознавание или перевод в отдельном потоке
        lang = config.get("language", "auto")
        self.worker = LiveTranscriptionWorker(
            audio_data,
            duration=dur,
            language=lang,
            task=self.current_task
        )
        self.worker.finished_signal.connect(self._on_transcription_finished)
        self.worker.error_signal.connect(self._on_transcription_error)
        self.worker.start()

    def cancel_recording(self):
        """
        Отменяет текущую запись: сбрасывает аудиопоток без сохранения,
        без распознавания и без вставки в активное окно.
        """
        if not self.recorder.is_recording:
            return

        print("[App] Запись отменена пользователем (звук сброшен).")
        # 1. Сбрасываем запись без сохранения аудио
        _ = self.recorder.stop()

        # 2. Звуковой сигнал отмены
        play_cancel_sound()

        # 3. Сбрасываем визуальные индикаторы в обычное состояние
        self.tray.set_recording_state(False)
        self.main_window.set_recording_state(False)

        # 4. Отображаем статус отмены в оверлее
        self.overlay.show_cancelled()

    def _on_transcription_finished(self, text: str, detected_lang: str, duration: float, task: str = "transcribe"):
        clean_text = text.strip()
        is_trans = (task == "translate")

        if is_trans:
            print(f"[App] Переведено ({detected_lang} -> EN): {clean_text}")
        else:
            print(f"[App] Распознано ({detected_lang}): {clean_text}")

        if clean_text:
            # 1. Всегда помещаем в буфер обмена Windows и (если разрешено) делаем Ctrl+V
            handle_recognized_text(clean_text)

            # 2. Звук успешного завершения
            play_success_sound()

            # 3. Визуальный оверлей успеха
            self.overlay.show_success(clean_text, is_translation=is_trans)

            # 4. Добавляем в историю и обновляем UI
            hist_lang = "EN (Перевод)" if is_trans else detected_lang
            history.add_entry(clean_text, language=hist_lang, duration=duration)
            self.main_window.display_latest_text(clean_text)
        else:
            self.overlay.hide_overlay()

    def _on_transcription_error(self, err_msg: str):
        print(f"[App] Ошибка распознавания: {err_msg}")
        self.overlay.show_error("Ошибка распознавания", err_msg)

    def quit_app(self):
        self.hotkey_mgr.unregister()
        if self.recorder.is_recording:
            self.recorder.stop()
        self.app.quit()

_instance_mutex = None

def acquire_single_instance_mutex():
    """
    Создает именованный мьютекс Windows для предотвращения запуска двух копий программы.
    """
    global _instance_mutex
    mutex_name = "WhisperVoiceAssistant_SingleInstance_Mutex"
    _instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return False
    return True

def activate_existing_window():
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "Whisper Voice Assistant")
    if hwnd:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    return False

def main():
    # 0. Явная регистрация AppUserModelID в Windows 10/11 для корректной группировки на панели задач
    # и отображения официальной иконки приложения с микрофоном вместо стандартной иконки Python
    if sys.platform == "win32":
        try:
            myappid = "whisper.voice.assistant.app.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Отключаем масштабирование размытия для экранов с высоким DPI
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)

    # 1. Попытка связаться с уже работающим экземпляром через QLocalSocket
    server_name = "WhisperVoiceAssistant_IPC"
    sock = QLocalSocket()
    sock.connectToServer(server_name)
    if sock.waitForConnected(300):
        sock.write(b"SHOW\n")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        print("[App] Приложение уже работает. Окно активировано.")
        sys.exit(0)

    # Защита от повторного запуска (Single Instance Mutex fallback)
    if not acquire_single_instance_mutex():
        print("[App] Приложение уже работает в фоновом режиме или в трее.")
        activate_existing_window()
        sys.exit(0)

    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))
    else:
        app.setWindowIcon(get_app_icon(False))
    app.setQuitOnLastWindowClosed(False)

    try:
        assistant = VoiceAssistantApp(app)
        # Применяем скрытие консоли только после успешной загрузки интерфейса и трея
        apply_console_preference()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        from console_manager import set_console_visible
        set_console_visible(True)
        print("\n" + "=" * 60)
        print(" [ОШИБКА ЗАПУСКА WHISPER VOICE ASSISTANT]")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        input("\nНажмите клавишу Enter для выхода...")
        sys.exit(1)

if __name__ == "__main__":
    main()
