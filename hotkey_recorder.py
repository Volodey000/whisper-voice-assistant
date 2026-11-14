from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
)
from PyQt6.QtGui import QKeyEvent, QFont

def format_hotkey_display(hotkey: str) -> str:
    """Форматирует комбинацию клавиш в лаконичном стиле shadcn <kbd>."""
    if not hotkey:
        return "Не задано"
    parts = hotkey.split("+")
    formatted = []
    for p in parts:
        p_clean = p.strip()
        p_lower = p_clean.lower()
        if p_lower == "ctrl":
            formatted.append("Ctrl")
        elif p_lower == "shift":
            formatted.append("Shift")
        elif p_lower == "alt":
            formatted.append("Alt")
        elif p_lower == "win":
            formatted.append("Win")
        elif p_lower == "space":
            formatted.append("Space")
        elif p_lower == "tab":
            formatted.append("Tab")
        elif p_lower == "enter":
            formatted.append("Enter")
        elif p_lower in ("`", "grave", "~"):
            formatted.append("`")
        elif p_lower.startswith("f") and p_lower[1:].isdigit():
            formatted.append(p_lower.upper())
        else:
            formatted.append(p_clean.upper() if len(p_clean) == 1 else p_clean.title())
    return " + ".join(formatted)

class HotkeyCaptureBox(QFrame):
    """
    Поле ввода горячей клавиши в стиле shadcn input/kbd.
    """
    key_combination_captured = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.is_recording = False
        self.current_hotkey = "ctrl+`"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.lbl_text = QLabel("ctrl+`", self)
        self.lbl_text.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_text)

        self._apply_normal_style()

    def _apply_normal_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e4e4e7;
                border-radius: 6px;
                min-height: 28px;
            }
            QFrame:hover {
                border-color: #a1a1aa;
            }
        """)
        self.lbl_text.setStyleSheet("color: #09090b; font-family: 'Segoe UI', monospace;")
        self.lbl_text.setText(format_hotkey_display(self.current_hotkey))

    def _apply_recording_style(self, text="Нажмите клавиши на клавиатуре..."):
        self.setStyleSheet("""
            QFrame {
                background-color: #f4f4f5;
                border: 1px solid #18181b;
                border-radius: 6px;
                min-height: 28px;
            }
        """)
        self.lbl_text.setStyleSheet("color: #09090b; font-weight: 500;")
        self.lbl_text.setText(text)

    def start_recording(self):
        self.is_recording = True
        self.setFocus()
        self.grabKeyboard()
        self._apply_recording_style("Нажмите комбинацию (например Ctrl + `)...")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.releaseKeyboard()
            self._apply_normal_style()

    def set_hotkey(self, hotkey: str):
        self.current_hotkey = hotkey.strip()
        self._apply_normal_style()

    def get_hotkey(self) -> str:
        return self.current_hotkey

    def mousePressEvent(self, event):
        if not self.is_recording:
            self.start_recording()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Отмена по Escape
        if key == Qt.Key.Key_Escape and not modifiers:
            self.stop_recording()
            self.cancelled.emit()
            event.accept()
            return

        # Нажат только модификатор — предпросмотр
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            preview = []
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                preview.append("Ctrl")
            if modifiers & Qt.KeyboardModifier.AltModifier:
                preview.append("Alt")
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                preview.append("Shift")
            if modifiers & Qt.KeyboardModifier.MetaModifier:
                preview.append("Win")
            if preview:
                self._apply_recording_style(" + ".join(preview) + " + ...")
            event.accept()
            return

        # Сбор модификаторов
        mods = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mods.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mods.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mods.append("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mods.append("win")

        scan_code = event.nativeScanCode()
        vk = event.nativeVirtualKey()

        if scan_code == 41 or vk in (0xC0, 192) or key in (Qt.Key.Key_QuoteLeft, Qt.Key.Key_AsciiTilde, 96):
            main_key = "`"
        elif key == Qt.Key.Key_Space:
            main_key = "space"
        elif key == Qt.Key.Key_Tab:
            main_key = "tab"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            main_key = "enter"
        elif key == Qt.Key.Key_Backspace:
            main_key = "backspace"
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            main_key = f"f{key - Qt.Key.Key_F1 + 1}"
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            main_key = chr(key)
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            main_key = chr(key).lower()
        else:
            txt = event.text()
            if txt and txt.isprintable() and txt != " ":
                main_key = txt.lower()
            else:
                main_key = f"f{key}" if key < 100 else "key"

        parts = list(mods)
        if main_key not in parts:
            parts.append(main_key)

        hotkey_str = "+".join(parts)
        self.current_hotkey = hotkey_str
        self.stop_recording()
        self.key_combination_captured.emit(hotkey_str)
        event.accept()

class HotkeyRecorderWidget(QWidget):
    hotkey_changed = pyqtSignal(str)

    def __init__(self, initial_hotkey="ctrl+`", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(8)

        # Поле захвата
        self.capture_box = HotkeyCaptureBox(self)
        self.capture_box.set_hotkey(initial_hotkey)
        self.capture_box.key_combination_captured.connect(self._on_captured)
        self.capture_box.cancelled.connect(self._on_cancelled)
        row.addWidget(self.capture_box, 3)

        # Кнопка записи
        self.btn_record = QPushButton("Изменить", self)
        self.btn_record.clicked.connect(self._toggle_recording)
        self.btn_record.setFixedHeight(34)
        row.addWidget(self.btn_record, 1)

        # Кнопка сброса
        self.btn_reset = QPushButton("Сброс", self)
        self.btn_reset.setToolTip("Вернуть сочетание по умолчанию (Ctrl + `)")
        self.btn_reset.clicked.connect(lambda: self.set_hotkey("ctrl+`"))
        self.btn_reset.setFixedHeight(34)
        row.addWidget(self.btn_reset, 1)

        layout.addLayout(row)

        self.lbl_hint = QLabel("Нажмите «Изменить» или кликните по полю и нажмите нужное сочетание на клавиатуре.", self)
        self.lbl_hint.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(self.lbl_hint)

    def _toggle_recording(self):
        if self.capture_box.is_recording:
            self.capture_box.stop_recording()
            self.btn_record.setText("Изменить")
        else:
            self.capture_box.start_recording()
            self.btn_record.setText("Отмена")

    def _on_captured(self, hotkey_str: str):
        self.btn_record.setText("Изменить")
        self.hotkey_changed.emit(hotkey_str)

    def _on_cancelled(self):
        self.btn_record.setText("Изменить")

    def set_hotkey(self, hotkey: str):
        self.capture_box.set_hotkey(hotkey)
        self.btn_record.setText("Изменить")
        self.hotkey_changed.emit(hotkey)

    def get_hotkey(self) -> str:
        return self.capture_box.get_hotkey()
