from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPoint
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QCursor, QLinearGradient
from config import config
from hotkey_recorder import format_hotkey_display
from waveform import WaveformVisualizer

class StatusDot(QWidget):
    """Минималистичная индикаторная точка в стиле shadcn."""
    def __init__(self, color="#ef4444", parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.dot_color = QColor(color)

    def set_color(self, hex_color: str):
        self.dot_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(self.dot_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 8, 8)
        p.end()

class MatrixVuMeter(WaveformVisualizer):
    """
    Аутентичный спектральный индикатор звука (Waveform VU-метр) в стиле матрицы.
    Плавная непрерывная звуковая волна (Catmull-Rom кубический сплайн Безье)
    с симметричным отклонением вверх и вниз от средней линии
    и натуральной плавной огибающей живой речи (vocal curve).
    """
    def __init__(self, parent=None):
        # Ширина 88px, высота 28px (увеличена для большей амплитуды), 19 узлов, усиление 2.8x
        super().__init__(parent=parent, theme="matrix", fixed_width=88, fixed_height=28, num_nodes=19, gain=2.8)

    def set_levels(self, levels):
        self.update_from_bands(levels)

    def update_bands(self, new_bands: list[float]):
        self.update_from_bands(new_bands)

    def update_volume(self, raw_volume: float):
        super().update_from_volume(raw_volume)

class RecordingOverlay(QWidget):
    """
    Плавающая минималистичная капсула в стиле shadcn/ui.
    Не перехватывает фокус ввода. Поддерживает свободное перетаскивание мышью.
    """
    cancel_requested = pyqtSignal()

    def __init__(self, recorder=None):
        super().__init__()
        self.recorder = recorder

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.state = "idle"
        self.timer_seconds = 0

        self.rec_timer = QTimer(self)
        self.rec_timer.timeout.connect(self._on_rec_tick)

        # 30 FPS таймер для плавного матричного VU-метра
        self.vu_timer = QTimer(self)
        self.vu_timer.timeout.connect(self._on_vu_tick)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_overlay)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.container = QWidget(self)
        self.container.setObjectName("capsule")
        self.container.setToolTip("Перетащите мышью, чтобы переместить плашку в любое место")
        self.container.setStyleSheet("""
            QWidget#capsule {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 20px;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 9px;
                font-size: 11px;
                font-family: -apple-system, 'Segoe UI', BlinkMacSystemFont, sans-serif;
                font-weight: 700;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                padding: 0px;
                margin-left: 4px;
            }
            QPushButton#cancelBtn:hover {
                background-color: #27272a;
                color: #ef4444;
            }
            QPushButton#cancelBtn:pressed {
                background-color: #3f3f46;
                color: #f87171;
            }
        """)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(14, 6, 14, 6)
        container_layout.setSpacing(10)

        # 1. Цветная индикаторная точка (для состояний: ожидание, обработка, успех, ошибка)
        self.dot = StatusDot("#ef4444", self.container)

        # 2. Матричный VU-метр (показывается только во время активной записи)
        self.matrix_meter = MatrixVuMeter(self.container)
        self.matrix_meter.setVisible(False)

        # 3. Основной текст
        self.text_label = QLabel("Запись", self.container)
        self.text_label.setStyleSheet("color: #fafafa; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 13px; font-weight: 500;")

        # 4. Вторичный текст / таймер
        self.sub_label = QLabel("00:00", self.container)
        self.sub_label.setStyleSheet("color: #a1a1aa; font-family: 'Segoe UI', 'Consolas', monospace; font-size: 12px;")

        # 5. Кнопка крестика отмены записи
        self.btn_cancel = QPushButton("✕", self.container)
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setToolTip("Отменить запись (без сохранения и вставки)")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_cancel.setVisible(False)

        container_layout.addWidget(self.dot)
        container_layout.addWidget(self.matrix_meter)
        container_layout.addWidget(self.text_label)
        container_layout.addWidget(self.sub_label)
        container_layout.addWidget(self.btn_cancel)

        layout.addWidget(self.container)
        self.adjustSize()

    # ------------------ Перетаскивание мышью (Drag & Drop) ------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if hasattr(self, '_drag_pos') and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_pos') and event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Запоминаем пользовательские координаты
            config.set("overlay_position", "custom")
            config.set("overlay_custom_pos", [self.x(), self.y()])
            del self._drag_pos
            event.accept()

    # ------------------ Вычисление позиции оверлея ------------------
    def _apply_position(self):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return

        geom = screen.availableGeometry()
        self.adjustSize()
        w = self.width()
        h = self.height()

        pos_mode = config.get("overlay_position", "top_center")

        if pos_mode == "custom":
            saved_pos = config.get("overlay_custom_pos", None)
            if saved_pos and len(saved_pos) == 2:
                x = max(geom.x(), min(geom.x() + geom.width() - w, saved_pos[0]))
                y = max(geom.y(), min(geom.y() + geom.height() - h, saved_pos[1]))
                self.move(x, y)
                return

        if pos_mode == "bottom_center":
            x = geom.x() + (geom.width() - w) // 2
            y = geom.y() + geom.height() - h - 36
        elif pos_mode == "top_right":
            x = geom.x() + geom.width() - w - 32
            y = geom.y() + 32
        elif pos_mode == "bottom_right":
            x = geom.x() + geom.width() - w - 32
            y = geom.y() + geom.height() - h - 36
        elif pos_mode == "cursor":
            cur_pos = QCursor.pos()
            x = max(geom.x(), min(geom.x() + geom.width() - w, cur_pos.x() - w // 2))
            y = max(geom.y(), min(geom.y() + geom.height() - h, cur_pos.y() - h - 25))
        else:  # "top_center"
            x = geom.x() + (geom.width() - w) // 2
            y = geom.y() + 32

        self.move(x, y)

    def _on_vu_tick(self):
        if self.recorder and self.recorder.is_recording:
            if hasattr(self.recorder, 'get_audio_bands'):
                bands = self.recorder.get_audio_bands()
                self.matrix_meter.update_bands(bands)
            else:
                vol = self.recorder.get_volume()
                self.matrix_meter.update_volume(vol)

    def show_recording(self, task: str = "transcribe"):
        if not config.get("show_overlay", True):
            return
        self.state = "recording"
        self.current_task = task
        self.timer_seconds = 0
        self.hide_timer.stop()

        # Во время записи активируем матричный VU-метр вместо точки
        self.dot.setVisible(False)
        self.matrix_meter.setVisible(True)
        self.matrix_meter.reset()
        self.vu_timer.start(33)

        if task == "translate":
            self.text_label.setText("Перевод (EN)")
            hotkey_str = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
            self.sub_label.setText(f"00:00 • RU → EN • {hotkey_str}")
        else:
            self.text_label.setText("Запись")
            hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
            self.sub_label.setText(f"00:00 • {hotkey_str}")

        self.btn_cancel.setVisible(True)
        self._apply_position()
        self.show()
        self.rec_timer.start(1000)

    def _on_rec_tick(self):
        self.timer_seconds += 1
        mins = self.timer_seconds // 60
        secs = self.timer_seconds % 60
        if getattr(self, 'current_task', 'transcribe') == "translate":
            hotkey_str = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
            self.sub_label.setText(f"{mins:02d}:{secs:02d} • RU → EN • {hotkey_str}")
        else:
            hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
            self.sub_label.setText(f"{mins:02d}:{secs:02d} • {hotkey_str}")
        self._apply_position()

    def show_processing(self, task: str = "transcribe"):
        if not config.get("show_overlay", True):
            return
        self.rec_timer.stop()
        self.vu_timer.stop()
        self.state = "processing"

        self.matrix_meter.setVisible(False)
        self.dot.setVisible(True)
        self.dot.set_color("#3b82f6")
        self.btn_cancel.setVisible(False)

        from transcriber import whisper_engine, get_local_model_target
        cfg_model = config.get("model_name", "auto")
        target_name = "large-v3-turbo" if cfg_model == "auto" else cfg_model
        _, is_local = get_local_model_target(target_name)

        if whisper_engine.model is None and not is_local:
            self.text_label.setText("Загрузка модели ИИ")
            self.sub_label.setText("Скачивание весов (~1.5 ГБ)...")
        elif whisper_engine.model is None:
            self.text_label.setText("Инициализация")
            self.sub_label.setText("Загрузка модели в память...")
        elif task == "translate":
            self.text_label.setText("Перевод")
            self.sub_label.setText("Whisper → English")
        else:
            self.text_label.setText("Распознавание")
            self.sub_label.setText("Whisper")

        self._apply_position()
        self.show()

    def show_success(self, text: str, is_translation: bool = False):
        if not config.get("show_overlay", True):
            return
        self.rec_timer.stop()
        self.vu_timer.stop()
        self.state = "success"

        self.matrix_meter.setVisible(False)
        self.dot.setVisible(True)
        self.dot.set_color("#22c55e")
        self.btn_cancel.setVisible(False)

        if is_translation:
            if config.get("auto_paste", True):
                self.text_label.setText("Перевод вставлен")
            else:
                self.text_label.setText("Перевод в буфере")
        else:
            if config.get("auto_paste", True):
                self.text_label.setText("Вставлено в окно")
            else:
                self.text_label.setText("Скопировано в буфер")

        preview = text.strip().replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        if not preview:
            preview = ""
        self.sub_label.setText(preview)

        self._apply_position()
        self.show()
        self.hide_timer.start(2400)

    def show_error(self, title: str = "Ошибка", message: str = ""):
        self.rec_timer.stop()
        self.vu_timer.stop()
        self.state = "error"

        self.matrix_meter.setVisible(False)
        self.dot.setVisible(True)
        self.dot.set_color("#f59e0b")
        self.btn_cancel.setVisible(False)

        self.text_label.setText(title)
        preview = message.strip().replace("\n", " ")
        if len(preview) > 45:
            preview = preview[:42] + "..."
        self.sub_label.setText(preview)

        self._apply_position()
        self.show()
        self.hide_timer.start(3500)

    def show_cancelled(self):
        self.rec_timer.stop()
        self.vu_timer.stop()
        self.state = "cancelled"

        self.matrix_meter.setVisible(False)
        self.dot.setVisible(True)
        self.dot.set_color("#71717a")
        self.btn_cancel.setVisible(False)

        self.text_label.setText("Запись отменена")
        self.sub_label.setText("")
        self._apply_position()
        self.show()
        self.hide_timer.start(750)

    def hide_overlay(self):
        self.rec_timer.stop()
        self.vu_timer.stop()
        self.hide_timer.stop()
        self.btn_cancel.setVisible(False)
        self.hide()
