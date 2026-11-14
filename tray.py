import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon
from icons import get_app_icon
from config import config
from hotkey_recorder import format_hotkey_display

class TrayIcon(QSystemTrayIcon):
    def __init__(self, main_window=None):
        # В Windows QSystemTrayIcon не должен иметь QWidget в качестве родителя,
        # чтобы его жизненный цикл и видимость не зависели от состояния главного окна
        super().__init__(None)
        self.main_window = main_window
        self.is_recording = False

        # Устанавливаем официальную иконку приложения с микрофоном
        self.setIcon(self._get_icon(False))
        self.update_tooltip()

        if self.main_window:
            self._build_menu()
            self.activated.connect(self._on_tray_activated)

        # Обязательно форсируем видимость иконки в Windows трее
        self.setVisible(True)
        self.show()

    def set_main_window(self, main_window):
        self.main_window = main_window
        self._build_menu()
        self.activated.connect(self._on_tray_activated)

    def _get_icon(self, is_recording: bool) -> QIcon:
        """
        Возвращает иконку приложения. Если не идет запись и файл app_icon.ico доступен на диске,
        используем его для максимально чистого нативного рендеринга Windows Explorer.
        """
        if not is_recording:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
            if os.path.exists(ico_path):
                return QIcon(ico_path)
        return get_app_icon(is_recording)

    def update_icon_for_window_state(self):
        """Гарантирует отображение иконки приложения с микрофоном при открытом окне."""
        self.setIcon(self._get_icon(self.is_recording))
        self.update_tooltip()
        self.setVisible(True)
        self.show()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #09090b;
                border: 1px solid #e4e4e7;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f4f4f5;
                color: #09090b;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e4e4e7;
                margin: 4px 6px;
            }
        """)

        self.action_record = QAction("Начать запись", self)
        if self.main_window:
            self.action_record.triggered.connect(self.main_window.toggle_recording)
        menu.addAction(self.action_record)

        menu.addSeparator()

        action_show = QAction("Открыть окно", self)
        if self.main_window:
            action_show.triggered.connect(self.main_window.show_and_activate)
        menu.addAction(action_show)

        # Подменю языков
        lang_menu = menu.addMenu("Язык распознавания")
        for code, label in [("auto", "Авто (RU / EN)"), ("ru", "Русский"), ("en", "English")]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(config.get("language", "auto") == code)
            act.triggered.connect(lambda checked, c=code: self._set_language(c))
            lang_menu.addAction(act)

        menu.addSeparator()

        action_quit = QAction("Выход", self)
        if self.main_window:
            action_quit.triggered.connect(self.main_window.quit_application)
        menu.addAction(action_quit)

        self.setContextMenu(menu)

    def _set_language(self, code: str):
        config.set("language", code)
        if self.main_window:
            self.main_window.sync_settings_ui()
        self._build_menu()

    def set_recording_state(self, is_recording: bool, task: str = "transcribe"):
        self.is_recording = is_recording
        self.setIcon(self._get_icon(is_recording))
        if is_recording:
            if task == "translate":
                self.action_record.setText("Остановить перевод")
                self.setToolTip("Whisper: идет запись для перевода (RU -> EN)...")
            else:
                self.action_record.setText("Остановить запись")
                self.setToolTip("Whisper: идет запись речи...")
        else:
            self.action_record.setText("Начать запись")
            self.update_tooltip()
        self.setVisible(True)
        self.show()

    def update_tooltip(self):
        hotkey = format_hotkey_display(config.get("hotkey", "ctrl+`"))
        trans_hk = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
        self.setToolTip(f"Whisper Voice Assistant\nДиктовка: {hotkey} • Перевод: {trans_hk}\nКликните для открытия окна")

    def show_minimized_notification(self):
        """Показывает всплывающее системное уведомление Windows, указывающее на значок в трее."""
        if not QSystemTrayIcon.supportsMessages():
            return
        hotkey = format_hotkey_display(config.get("hotkey", "ctrl+`"))
        trans_hk = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
        self.showMessage(
            "Whisper Voice Assistant",
            f"Приложение свернуто в трей.\nДиктовка: [{hotkey}] • Перевод: [{trans_hk}]\nКликните по иконке, чтобы открыть окно.",
            self.icon(),
            2500
        )

    def _on_tray_activated(self, reason):
        # Открытие окна по одиночному или двойному клику левой кнопкой мыши
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick
        ):
            if self.main_window:
                self.main_window.show_and_activate()
