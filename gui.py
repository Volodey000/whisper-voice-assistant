import os
import sys
import ctypes
import sounddevice as sd
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QProgressBar, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QRadioButton, QButtonGroup,
    QFrame, QScrollArea, QApplication, QListView
)
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette

from config import config
from icons import (
    get_app_icon, get_tray_minimize_icon, get_play_icon, get_stop_icon,
    CHECK_TICK_PATH, RADIO_DOT_PATH, COMBO_ARROW_PATH, ensure_ui_icons
)
from waveform import WaveformVisualizer
from vocabulary import DEFAULT_HOTWORDS, DEFAULT_REPLACEMENTS
from console_manager import set_console_visible, is_console_visible
from history_manager import history
from paste_helper import copy_to_clipboard
from workers import FileTranscriptionWorker
from transcriber import export_to_srt
from hotkey_recorder import HotkeyRecorderWidget, format_hotkey_display
from hardware import detect_hardware, resolve_settings
import autostart

# Гарантируем наличие векторных UI иконок
ensure_ui_icons()

# Чистая светлая тема в строгом стиле shadcn/ui (Zinc light)
SHADCN_STYLESHEET = f"""
QMainWindow {{
    background-color: #fafafa;
    color: #09090b;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
}}
QWidget {{
    color: #09090b;
    font-size: 13px;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
}}
/* Сегментированные вкладки shadcn */
QTabWidget::pane {{
    border: 1px solid #e4e4e7;
    background-color: #ffffff;
    border-radius: 8px;
    top: 4px;
}}
QTabBar {{
    background-color: #f4f4f5;
    border: 1px solid #e4e4e7;
    border-radius: 6px;
    padding: 3px;
}}
QTabBar::tab {{
    background: transparent;
    color: #71717a;
    padding: 6px 18px;
    border-radius: 4px;
    border: none;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    color: #09090b;
    border: 1px solid #e4e4e7;
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: #18181b;
}}

/* Карточки */
QGroupBox {{
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px;
    padding-top: 24px;
    font-weight: 600;
    color: #09090b;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    top: 2px;
    color: #52525b;
    font-size: 12px;
    font-weight: 600;
}}

/* Кнопки shadcn */
QPushButton {{
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 6px;
    padding: 7px 14px;
    color: #09090b;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #f4f4f5;
    border-color: #d4d4d8;
}}
QPushButton:pressed {{
    background-color: #e4e4e7;
}}
QPushButton:disabled {{
    background-color: #fafafa;
    color: #a1a1aa;
    border-color: #e4e4e7;
}}

/* Кнопка быстрой записи в режиме ожидания (белая кнопка с контрастным текстом) */
QPushButton#primaryBtn {{
    background-color: #ffffff;
    border: 1.5px solid #d4d4d8;
    color: #09090b;
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{
    background-color: #f4f4f5;
    border-color: #a1a1aa;
}}
QPushButton#primaryBtn:pressed {{
    background-color: #e4e4e7;
}}

/* Кнопка записи в активном состоянии (shadcn destructive red) */
QPushButton#recordBtnActive {{
    background-color: #ef4444;
    border: 1.5px solid #dc2626;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#recordBtnActive:hover {{
    background-color: #dc2626;
}}
QPushButton#recordBtnActive:pressed {{
    background-color: #b91c1c;
}}

/* Текстовые поля, строки ввода и таблицы */
QLineEdit, QTextEdit, QTableWidget {{
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 6px;
    color: #09090b;
    padding: 8px;
    selection-background-color: #f4f4f5;
    selection-color: #09090b;
    line-height: 1.5;
}}
QLineEdit:focus, QTextEdit:focus, QTableWidget:focus {{
    border-color: #71717a;
}}

/* Выпадающие списки (QComboBox) - гарантированно светлый фон и темный текст */
QComboBox {{
    background-color: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 6px;
    padding: 6px 12px;
    color: #09090b;
    font-size: 13px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: #a1a1aa;
}}
QComboBox:focus {{
    border-color: #71717a;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url({COMBO_ARROW_PATH});
    width: 12px;
    height: 12px;
}}
QComboBox QAbstractItemView,
QComboBox QListView,
QListView {{
    background-color: #ffffff;
    background: #ffffff;
    border: 1px solid #e4e4e7;
    border-radius: 6px;
    padding: 4px;
    color: #09090b;
    selection-background-color: #f4f4f5;
    selection-color: #09090b;
    outline: none;
}}
QComboBox QAbstractItemView::item,
QComboBox QListView::item,
QListView::item {{
    background-color: #ffffff;
    color: #09090b;
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 22px;
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QListView::item:hover,
QListView::item:hover {{
    background-color: #f4f4f5;
    color: #09090b;
}}
QComboBox QAbstractItemView::item:selected,
QComboBox QListView::item:selected,
QListView::item:selected {{
    background-color: #e4e4e7;
    color: #09090b;
    font-weight: 500;
}}

/* Полоса прогресса */
QProgressBar {{
    background-color: #f4f4f5;
    border-radius: 4px;
    border: none;
    text-align: center;
    color: #71717a;
    height: 6px;
}}
QProgressBar::chunk {{
    background-color: #18181b;
    border-radius: 4px;
}}

/* Чекбоксы: настоящие галочки shadcn/ui */
QCheckBox {{
    spacing: 8px;
    color: #18181b;
    font-weight: 400;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
}}
QCheckBox::indicator:unchecked {{
    background-color: #ffffff;
    border: 1.5px solid #d4d4d8;
    image: none;
}}
QCheckBox::indicator:unchecked:hover {{
    border-color: #71717a;
    background-color: #f4f4f5;
}}
QCheckBox::indicator:checked {{
    background-color: #09090b;
    border: 1.5px solid #09090b;
    image: url({CHECK_TICK_PATH});
}}
QCheckBox::indicator:checked:hover {{
    background-color: #27272a;
    border-color: #27272a;
    image: url({CHECK_TICK_PATH});
}}

/* Радио-кнопки */
QRadioButton {{
    spacing: 8px;
    color: #18181b;
    font-weight: 400;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 9px;
}}
QRadioButton::indicator:unchecked {{
    background-color: #ffffff;
    border: 1.5px solid #d4d4d8;
    image: none;
}}
QRadioButton::indicator:unchecked:hover {{
    border-color: #71717a;
    background-color: #f4f4f5;
}}
QRadioButton::indicator:checked {{
    background-color: #ffffff;
    border: 2px solid #09090b;
    image: url({RADIO_DOT_PATH});
}}
QRadioButton::indicator:checked:hover {{
    border-color: #27272a;
    image: url({RADIO_DOT_PATH});
}}

/* Заголовки таблиц */
QHeaderView::section {{
    background-color: #f4f4f5;
    color: #71717a;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #e4e4e7;
    font-weight: 600;
    font-size: 12px;
}}
QTableWidget {{
    gridline-color: #f4f4f5;
}}

/* Элегантный тонкий скроллбар в стиле shadcn */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 1px 4px 1px;
}}
QScrollBar::handle:vertical {{
    background: #e4e4e7;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #d4d4d8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
"""

def setup_light_combobox(combo: QComboBox):
    """
    Гарантирует белоснежный фон, четкий темный текст и красивое выпадающее меню
    для QComboBox независимо от темы Windows (светлая/темная).
    """
    view = QListView(combo)
    view.setStyleSheet("""
        QListView {
            background-color: #ffffff;
            background: #ffffff;
            color: #09090b;
            border: 1px solid #e4e4e7;
            border-radius: 6px;
            padding: 4px;
            outline: none;
            selection-background-color: #f4f4f5;
            selection-color: #09090b;
        }
        QListView::item {
            background-color: #ffffff;
            color: #09090b;
            padding: 6px 10px;
            border-radius: 4px;
            min-height: 22px;
        }
        QListView::item:hover {
            background-color: #f4f4f5;
            color: #09090b;
        }
        QListView::item:selected {
            background-color: #e4e4e7;
            color: #09090b;
            font-weight: 500;
        }
    """)
    pal = view.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#09090b"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#09090b"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#e4e4e7"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#09090b"))
    view.setPalette(pal)
    if view.viewport():
        view.viewport().setPalette(pal)
        view.viewport().setStyleSheet("background-color: #ffffff; color: #09090b;")
    combo.setView(view)

class LightComboBox(QComboBox):
    """
    Выпадающий список с гарантированно светлым фоном и темным текстом меню,
    устойчивый к темной теме Windows 10/11.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        setup_light_combobox(self)

    def showPopup(self):
        super().showPopup()
        container = self.view().window()
        if container:
            container.setStyleSheet("""
                QFrame {
                    background-color: #ffffff;
                    background: #ffffff;
                    color: #09090b;
                    border: 1px solid #e4e4e7;
                    border-radius: 6px;
                }
            """)
            c_pal = container.palette()
            c_pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
            c_pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            c_pal.setColor(QPalette.ColorRole.Text, QColor("#09090b"))
            c_pal.setColor(QPalette.ColorRole.WindowText, QColor("#09090b"))
            container.setPalette(c_pal)

class MainWindow(QMainWindow):
    request_toggle_recording = pyqtSignal()
    request_quit = pyqtSignal()
    settings_saved = pyqtSignal()

    def __init__(self, recorder, transcriber):
        super().__init__()
        self.recorder = recorder
        self.transcriber = transcriber
        self.file_worker = None
        self.last_file_segments = []

        self.setWindowTitle("Whisper Voice Assistant")
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))
        else:
            self.setWindowIcon(get_app_icon(False))
        self.setStyleSheet(SHADCN_STYLESHEET)

        # Автоматическая адаптация размера под экран (учитывает панель задач Windows)
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            # Окно гарантированно помещается в рабочую область экрана с безопасным отступом
            init_w = min(820, max(520, avail.width() - 40))
            init_h = min(580, max(380, avail.height() - 70))
        else:
            init_w, init_h = 780, 540

        self.resize(init_w, init_h)
        # Разрешаем свободно масштабировать окно (уменьшать/увеличивать) по высоте и ширине
        self.setMinimumSize(640, 380)

        # Центрируем окно на экране
        if screen:
            avail = screen.availableGeometry()
            self.move(
                avail.x() + max(0, (avail.width() - init_w) // 2),
                avail.y() + max(0, (avail.height() - init_h) // 2)
            )

        self.vol_timer = QTimer(self)
        self.vol_timer.timeout.connect(self._update_volume_meter)

        self._init_ui()
        self.sync_settings_ui()
        self.load_history_table()

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # Верхняя плашка в стиле shadcn (заголовок + бейдж оборудования)
        header_layout = QHBoxLayout()
        title_label = QLabel("Whisper Voice Assistant", self)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #09090b;")

        hw = detect_hardware()
        self.gpu_badge = QLabel(hw["badge_text"], self)
        self.gpu_badge.setStyleSheet("""
            background-color: #f4f4f5;
            color: #18181b;
            border: 1px solid #e4e4e7;
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 500;
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.gpu_badge)
        main_layout.addLayout(header_layout)

        # Вкладки (Tabs)
        self.tabs = QTabWidget(self)
        self.tab_dictation = self._wrap_in_scroll_area(self._create_dictation_tab())
        self.tab_vocabulary = self._wrap_in_scroll_area(self._create_vocabulary_tab())
        self.tab_files = self._wrap_in_scroll_area(self._create_files_tab())
        self.tab_settings = self._wrap_in_scroll_area(self._create_settings_tab())

        self.tabs.addTab(self.tab_dictation, "Диктовка")
        self.tabs.addTab(self.tab_vocabulary, "Словарь")
        self.tabs.addTab(self.tab_files, "Файлы")
        self.tabs.addTab(self.tab_settings, "Настройки")

        # Верхняя панель управления треем (чекбокс + кнопка в правом углу вкладок под плашкой оборудования)
        corner_widget = QWidget(self.tabs)
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 4, 2)
        corner_layout.setSpacing(10)

        self.chk_start_minimized = QCheckBox("Запускать свернутым в трей", corner_widget)
        self.chk_start_minimized.setToolTip("Если включено, при запуске программа будет сразу сворачиваться в системный трей")
        self.chk_start_minimized.setStyleSheet("""
            QCheckBox {
                color: #52525b;
                font-size: 12px;
                font-weight: 500;
            }
            QCheckBox:hover {
                color: #18181b;
            }
        """)
        self.chk_start_minimized.toggled.connect(self._on_start_minimized_toggled)

        self.btn_minimize_tray = QPushButton(" Свернуть в трей", corner_widget)
        self.btn_minimize_tray.setIcon(get_tray_minimize_icon())
        self.btn_minimize_tray.setToolTip("Свернуть главное окно в область уведомлений (системный трей)")
        self.btn_minimize_tray.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #e4e4e7;
                border-radius: 6px;
                color: #18181b;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: #f4f4f5;
                border: 1px solid #d4d4d8;
                color: #09090b;
            }
            QPushButton:pressed {
                background-color: #e4e4e7;
                border: 1px solid #cbd5e1;
            }
        """)
        self.btn_minimize_tray.clicked.connect(self.minimize_to_tray)

        corner_layout.addWidget(self.chk_start_minimized)
        corner_layout.addWidget(self.btn_minimize_tray)
        self.tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)

        main_layout.addWidget(self.tabs)

        # Подвал
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(10)
        hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
        trans_hk_str = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
        self.hotkey_hint = QLabel(f"Диктовка: {hotkey_str} • Перевод (RU -> EN): {trans_hk_str}. Текст в буфере.", self)
        self.hotkey_hint.setWordWrap(True)
        self.hotkey_hint.setStyleSheet("color: #71717a; font-size: 12px;")
        footer_layout.addWidget(self.hotkey_hint, 1)

        main_layout.addLayout(footer_layout)

    def _wrap_in_scroll_area(self, widget: QWidget) -> QWidget:
        """Оборачивает содержимое вкладки в скролл-область для адаптации под компактные экраны."""
        container = QWidget(self)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        widget.setStyleSheet("background: transparent;")
        scroll.setWidget(widget)
        c_layout.addWidget(scroll)
        return container

    # ------------------ Вкладка 1: Диктовка ------------------
    def _create_dictation_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Блок управления записью
        hero_group = QGroupBox("Быстрая запись")
        hero_layout = QVBoxLayout(hero_group)
        hero_layout.setSpacing(10)

        ctrl_layout = QHBoxLayout()
        hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
        self.btn_record = QPushButton(f"Начать запись ({hotkey_str})", self)
        self.btn_record.setObjectName("primaryBtn")
        self.btn_record.setIcon(get_play_icon())
        self.btn_record.setIconSize(QSize(18, 18))
        self.btn_record.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_record.setFixedHeight(40)
        self.btn_record.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.btn_record.clicked.connect(self.toggle_recording)
        ctrl_layout.addWidget(self.btn_record, 3)

        self.lbl_record_time = QLabel("00:00", self)
        self.lbl_record_time.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        self.lbl_record_time.setStyleSheet("color: #71717a; padding: 0 10px; font-family: monospace;")
        ctrl_layout.addWidget(self.lbl_record_time, 1)
        hero_layout.addLayout(ctrl_layout)

        # Индикатор уровня звука (живая плавная форма волны)
        vol_layout = QHBoxLayout()
        vol_layout.setSpacing(10)
        vol_label = QLabel("Уровень сигнала:", self)
        vol_label.setStyleSheet("color: #71717a; font-size: 11px; font-weight: 500;")
        self.vol_bar = WaveformVisualizer(self, theme="light", fixed_height=34, num_nodes=25, gain=2.8)
        self.vol_bar.setToolTip("Живая форма звуковой волны микрофона")
        vol_layout.addWidget(vol_label)
        vol_layout.addWidget(self.vol_bar, 1)
        hero_layout.addLayout(vol_layout)

        layout.addWidget(hero_group)

        # Поле последнего распознанного текста
        result_group = QGroupBox("Текущий результат (в буфере обмена)")
        res_layout = QVBoxLayout(result_group)
        res_layout.setSpacing(8)

        self.txt_latest = QTextEdit(self)
        self.txt_latest.setPlaceholderText("Здесь появится надиктованный текст...")
        self.txt_latest.setMinimumHeight(55)
        self.txt_latest.setMaximumHeight(130)
        self.txt_latest.setFont(QFont("Segoe UI", 11))
        res_layout.addWidget(self.txt_latest)

        btn_res_layout = QHBoxLayout()
        self.btn_copy_latest = QPushButton("Копировать", self)
        self.btn_copy_latest.clicked.connect(self._copy_latest_text)
        self.lbl_copy_status = QLabel("", self)
        self.lbl_copy_status.setStyleSheet("color: #52525b; font-size: 12px;")

        btn_res_layout.addWidget(self.btn_copy_latest)
        btn_res_layout.addWidget(self.lbl_copy_status)
        btn_res_layout.addStretch()
        res_layout.addLayout(btn_res_layout)

        layout.addWidget(result_group)

        # Таблица истории
        hist_group = QGroupBox("История")
        hist_layout = QVBoxLayout(hist_group)
        hist_layout.setSpacing(8)

        self.table_history = QTableWidget(self)
        self.table_history.setMinimumHeight(80)
        self.table_history.setColumnCount(4)
        self.table_history.setHorizontalHeaderLabels(["Время", "Язык", "Длительность", "Текст"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_history.itemDoubleClicked.connect(self._on_history_row_double_clicked)
        hist_layout.addWidget(self.table_history)

        hist_btn_layout = QHBoxLayout()
        btn_copy_sel = QPushButton("Копировать выбранное", self)
        btn_copy_sel.clicked.connect(self._copy_selected_history)
        btn_clear_hist = QPushButton("Очистить историю", self)
        btn_clear_hist.clicked.connect(self._clear_history)

        hist_btn_layout.addWidget(btn_copy_sel)
        hist_btn_layout.addWidget(btn_clear_hist)
        hist_btn_layout.addStretch()
        hist_layout.addLayout(hist_btn_layout)

        layout.addWidget(hist_group, 2)
        return w

    # ------------------ Вкладка 2: Словарь ------------------
    def _create_vocabulary_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 1. Главный блок включения словаря
        top_group = QGroupBox("Пользовательский словарь терминов и подсказки для Whisper")
        top_layout = QVBoxLayout(top_group)
        top_layout.setSpacing(6)

        self.chk_vocab_enabled = QCheckBox("Использовать словарь горячих слов и автозамен", self)
        self.chk_vocab_enabled.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.chk_vocab_enabled.toggled.connect(self._on_vocab_toggle)
        top_layout.addWidget(self.chk_vocab_enabled)

        lbl_desc = QLabel(
            "Нейросеть Whisper предварительно обучается вашим терминам через контекстные механизмы hotwords и initial_prompt. "
            "Это обеспечивает 100% точность распознавания профессионального сленга, аббревиатур, брендов, кода и фамилий в правильном регистре букв.",
            self
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #71717a; font-size: 12px; line-height: 1.4;")
        top_layout.addWidget(lbl_desc)
        layout.addWidget(top_group)

        # 2. Блок горячих слов
        hw_group = QGroupBox("Горячие слова и ключевые термины (Hotwords)")
        hw_layout = QVBoxLayout(hw_group)
        hw_layout.setSpacing(6)

        hw_hint = QLabel(
            "Введите список терминов через запятую или с новой строки. Модель Whisper получит их как приоритетную контекстную подсказку перед началом декодирования речи:",
            self
        )
        hw_hint.setWordWrap(True)
        hw_hint.setStyleSheet("color: #52525b; font-size: 11px;")
        hw_layout.addWidget(hw_hint)

        self.txt_hotwords = QTextEdit(self)
        self.txt_hotwords.setPlaceholderText("Пример: Kubernetes, PostgreSQL, FastAPI, Docker, Python, PyQt6, Faster-Whisper, Antigravity, Figma, GitHub, Битрикс24")
        self.txt_hotwords.setMinimumHeight(65)
        self.txt_hotwords.setMaximumHeight(90)
        self.txt_hotwords.setFont(QFont("Segoe UI", 11))
        hw_layout.addWidget(self.txt_hotwords)
        layout.addWidget(hw_group)

        # 3. Блок автозамен и сокращений
        repl_group = QGroupBox("Словарь автозамен (как произносится → как писать)")
        repl_layout = QVBoxLayout(repl_group)
        repl_layout.setSpacing(8)

        repl_hint = QLabel(
            "Мгновенная замена созвучных слов, сокращений и разговорного сленга на правильные термины при вставке:",
            self
        )
        repl_hint.setStyleSheet("color: #52525b; font-size: 11px;")
        repl_layout.addWidget(repl_hint)

        # Строка быстрого поиска по обоим столбцам таблицы
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.txt_repl_search = QLineEdit(self)
        self.txt_repl_search.setPlaceholderText("Быстрый поиск по обоим столбцам (по сленгу или замене)...")
        self.txt_repl_search.setClearButtonEnabled(True)
        self.txt_repl_search.setFixedHeight(34)
        self.txt_repl_search.textChanged.connect(self._filter_replacements)
        search_row.addWidget(self.txt_repl_search, 1)

        self.lbl_search_count = QLabel("Всего записей: 0", self)
        self.lbl_search_count.setStyleSheet("color: #71717a; font-size: 12px; font-weight: 500; padding-right: 4px;")
        search_row.addWidget(self.lbl_search_count, 0)
        repl_layout.addLayout(search_row)

        self.table_replacements = QTableWidget(self)
        self.table_replacements.setColumnCount(2)
        self.table_replacements.setHorizontalHeaderLabels(["Что услышано / Сленг", "Правильное написание / Замена"])
        self.table_replacements.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_replacements.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_replacements.setMinimumHeight(130)
        self.table_replacements.setMaximumHeight(220)
        repl_layout.addWidget(self.table_replacements)

        btn_row = QHBoxLayout()
        self.btn_add_repl = QPushButton("+ Добавить слово", self)
        self.btn_add_repl.clicked.connect(lambda: self._add_replacement_row())
        self.btn_del_repl = QPushButton("Удалить выбранное", self)
        self.btn_del_repl.clicked.connect(self._delete_selected_replacement)
        self.btn_reset_repl = QPushButton("Сбросить к образцу", self)
        self.btn_reset_repl.clicked.connect(self._reset_vocabulary_to_defaults)

        btn_row.addWidget(self.btn_add_repl)
        btn_row.addWidget(self.btn_del_repl)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reset_repl)
        repl_layout.addLayout(btn_row)
        layout.addWidget(repl_group)

        # 4. Панель сохранения
        save_row = QHBoxLayout()
        self.btn_save_vocab = QPushButton("Сохранить словарь", self)
        self.btn_save_vocab.setObjectName("primaryBtn")
        self.btn_save_vocab.setFixedHeight(38)
        self.btn_save_vocab.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.btn_save_vocab.clicked.connect(self._save_vocabulary)
        save_row.addWidget(self.btn_save_vocab, 2)

        self.lbl_vocab_status = QLabel("", self)
        self.lbl_vocab_status.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500;")
        save_row.addWidget(self.lbl_vocab_status, 3)
        layout.addLayout(save_row)

        layout.addStretch()
        return w

    def _on_vocab_toggle(self, checked: bool):
        if hasattr(self, 'chk_vocab_in_settings') and self.chk_vocab_in_settings.isChecked() != checked:
            self.chk_vocab_in_settings.setChecked(checked)

    def _filter_replacements(self, query: str = ""):
        """Фильтрует строки таблицы автозамен по совпадению в любом из двух столбцов."""
        q = query.strip().lower()
        total_rows = self.table_replacements.rowCount()
        visible_rows = 0

        for r in range(total_rows):
            item_src = self.table_replacements.item(r, 0)
            item_tgt = self.table_replacements.item(r, 1)
            src_val = item_src.text().lower() if item_src else ""
            tgt_val = item_tgt.text().lower() if item_tgt else ""

            match = (not q) or (q in src_val) or (q in tgt_val)
            self.table_replacements.setRowHidden(r, not match)
            if match:
                visible_rows += 1

        if hasattr(self, 'lbl_search_count'):
            if q:
                self.lbl_search_count.setText(f"Найдено: {visible_rows} из {total_rows}")
            else:
                self.lbl_search_count.setText(f"Всего записей: {total_rows}")

    def _add_replacement_row(self, src: str = "", tgt: str = ""):
        if hasattr(self, 'txt_repl_search') and self.txt_repl_search.text():
            self.txt_repl_search.clear()

        row = self.table_replacements.rowCount()
        self.table_replacements.insertRow(row)
        self.table_replacements.setRowHidden(row, False)
        item_src = QTableWidgetItem(src)
        item_tgt = QTableWidgetItem(tgt)
        self.table_replacements.setItem(row, 0, item_src)
        self.table_replacements.setItem(row, 1, item_tgt)
        self.table_replacements.setCurrentItem(item_src)
        self.table_replacements.editItem(item_src)
        self._filter_replacements(self.txt_repl_search.text() if hasattr(self, 'txt_repl_search') else "")

    def _delete_selected_replacement(self):
        selected_rows = sorted(set(idx.row() for idx in self.table_replacements.selectedIndexes()), reverse=True)
        for r in selected_rows:
            self.table_replacements.removeRow(r)
        self._filter_replacements(self.txt_repl_search.text() if hasattr(self, 'txt_repl_search') else "")

    def _reset_vocabulary_to_defaults(self):
        reply = QMessageBox.question(
            self,
            "Сброс словаря",
            "Вернуть список горячих слов и словарь автозамен к рекомендуемым начальным значениям?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self, 'txt_repl_search'):
                self.txt_repl_search.clear()
            self.chk_vocab_enabled.setChecked(True)
            self.txt_hotwords.setPlainText(DEFAULT_HOTWORDS)
            self._populate_replacements_table(DEFAULT_REPLACEMENTS)
            self._save_vocabulary()

    def _populate_replacements_table(self, repl_dict: dict):
        self.table_replacements.setRowCount(0)
        for src, tgt in repl_dict.items():
            row = self.table_replacements.rowCount()
            self.table_replacements.insertRow(row)
            self.table_replacements.setItem(row, 0, QTableWidgetItem(str(src)))
            self.table_replacements.setItem(row, 1, QTableWidgetItem(str(tgt)))
        self._filter_replacements(self.txt_repl_search.text() if hasattr(self, 'txt_repl_search') else "")

    def _load_vocabulary_ui(self):
        enabled = config.get("custom_vocabulary_enabled", True)
        if hasattr(self, 'chk_vocab_enabled'):
            self.chk_vocab_enabled.setChecked(enabled)
        if hasattr(self, 'chk_vocab_in_settings'):
            self.chk_vocab_in_settings.setChecked(enabled)

        hw = config.get("hotwords", DEFAULT_HOTWORDS)
        if isinstance(hw, list):
            hw = ", ".join(hw)
        if hasattr(self, 'txt_hotwords'):
            self.txt_hotwords.setPlainText(str(hw))

        repl = config.get("replacements", DEFAULT_REPLACEMENTS)
        if not isinstance(repl, dict):
            repl = DEFAULT_REPLACEMENTS
        if hasattr(self, 'table_replacements'):
            self._populate_replacements_table(repl)

    def _save_vocabulary(self):
        enabled = self.chk_vocab_enabled.isChecked()
        config.set("custom_vocabulary_enabled", enabled)
        if hasattr(self, 'chk_vocab_in_settings'):
            self.chk_vocab_in_settings.setChecked(enabled)

        hw_text = self.txt_hotwords.toPlainText().strip()
        config.set("hotwords", hw_text)

        replacements = {}
        for r in range(self.table_replacements.rowCount()):
            item_src = self.table_replacements.item(r, 0)
            item_tgt = self.table_replacements.item(r, 1)
            if item_src and item_tgt:
                s = item_src.text().strip()
                t = item_tgt.text().strip()
                if s and t:
                    replacements[s] = t

        config.set("replacements", replacements)
        self.lbl_vocab_status.setText("Словарь сохранен и применен!")
        QTimer.singleShot(2500, lambda: self.lbl_vocab_status.setText(""))

    # ------------------ Вкладка 3: Файлы ------------------
    def _create_files_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        file_group = QGroupBox("Аудио или видео файл")
        f_layout = QVBoxLayout(file_group)
        f_layout.setSpacing(10)

        pick_layout = QHBoxLayout()
        self.lbl_selected_file = QLabel("Файл не выбран. Поддерживаются MP3, WAV, M4A, OGG, FLAC, MP4, MKV", self)
        self.lbl_selected_file.setStyleSheet("color: #71717a;")
        btn_browse = QPushButton("Обзор...", self)
        btn_browse.clicked.connect(self._browse_audio_file)

        pick_layout.addWidget(self.lbl_selected_file, 3)
        pick_layout.addWidget(btn_browse, 1)
        f_layout.addLayout(pick_layout)

        opts_layout = QHBoxLayout()
        opts_layout.addWidget(QLabel("Язык:"))
        self.cmb_file_lang = LightComboBox(self)
        self.cmb_file_lang.addItems(["Автоопределение", "Русский", "English"])
        opts_layout.addWidget(self.cmb_file_lang)
        opts_layout.addStretch()

        self.btn_transcribe_file = QPushButton("Распознать файл", self)
        self.btn_transcribe_file.setObjectName("primaryBtn")
        self.btn_transcribe_file.setEnabled(False)
        self.btn_transcribe_file.clicked.connect(self._start_file_transcription)
        opts_layout.addWidget(self.btn_transcribe_file)
        f_layout.addLayout(opts_layout)

        self.file_progress_bar = QProgressBar(self)
        self.file_progress_bar.setRange(0, 100)
        self.file_progress_bar.setValue(0)
        self.file_progress_bar.setVisible(False)
        self.lbl_file_status = QLabel("", self)
        self.lbl_file_status.setStyleSheet("color: #52525b; font-size: 11px;")
        f_layout.addWidget(self.file_progress_bar)
        f_layout.addWidget(self.lbl_file_status)

        layout.addWidget(file_group)

        # Результат
        res_group = QGroupBox("Результат")
        res_layout = QVBoxLayout(res_group)
        res_layout.setSpacing(8)

        self.txt_file_result = QTextEdit(self)
        self.txt_file_result.setPlaceholderText("Результат появится здесь...")
        self.txt_file_result.setMinimumHeight(70)
        self.txt_file_result.setFont(QFont("Segoe UI", 11))
        res_layout.addWidget(self.txt_file_result)

        btn_row = QHBoxLayout()
        btn_copy_file_res = QPushButton("Копировать текст", self)
        btn_copy_file_res.clicked.connect(lambda: copy_to_clipboard(self.txt_file_result.toPlainText()))
        btn_save_txt = QPushButton("Сохранить TXT", self)
        btn_save_txt.clicked.connect(self._save_file_txt)
        btn_save_srt = QPushButton("Экспорт SRT", self)
        btn_save_srt.clicked.connect(self._save_file_srt)

        btn_row.addWidget(btn_copy_file_res)
        btn_row.addWidget(btn_save_txt)
        btn_row.addWidget(btn_save_srt)
        btn_row.addStretch()
        res_layout.addLayout(btn_row)

        layout.addWidget(res_group, 2)
        return w

    # ------------------ Вкладка 3: Настройки ------------------
    def _create_settings_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Горячие клавиши
        hk_group = QGroupBox("Горячие клавиши")
        hk_layout = QVBoxLayout(hk_group)
        hk_layout.setSpacing(8)

        hk_row = QVBoxLayout()
        hk_row.addWidget(QLabel("Сочетание клавиш для диктовки:"))
        self.hotkey_recorder = HotkeyRecorderWidget(config.get("hotkey", "ctrl+`"), self)
        hk_row.addWidget(self.hotkey_recorder)
        hk_layout.addLayout(hk_row)

        trans_hk_row = QVBoxLayout()
        trans_hk_row.addWidget(QLabel("Сочетание клавиш для перевода на английский (RU -> EN):"))
        self.translate_hotkey_recorder = HotkeyRecorderWidget(config.get("translate_hotkey", "alt+`"), self)
        trans_hk_row.addWidget(self.translate_hotkey_recorder)
        hk_layout.addLayout(trans_hk_row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Режим:"))
        self.rad_toggle = QRadioButton("Переключение (нажать для старта, нажать для стопа)", self)
        self.rad_hold = QRadioButton("Удержание (Push-to-Talk)", self)
        self.bg_mode = QButtonGroup(self)
        self.bg_mode.addButton(self.rad_toggle)
        self.bg_mode.addButton(self.rad_hold)
        row2.addWidget(self.rad_toggle)
        row2.addWidget(self.rad_hold)
        row2.addStretch()
        hk_layout.addLayout(row2)

        layout.addWidget(hk_group)

        # Железо и модель
        model_group = QGroupBox("Модель и оборудование")
        m_layout = QVBoxLayout(model_group)
        m_layout.setSpacing(8)

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Устройство:"))
        self.cmb_device = LightComboBox(self)
        self.cmb_device.addItem("Автовыбор по оборудованию", "auto")
        self.cmb_device.addItem("NVIDIA GPU (CUDA, float16)", "cuda")
        self.cmb_device.addItem("Процессор (CPU, int8 режим)", "cpu")
        dev_row.addWidget(self.cmb_device, 2)
        m_layout.addLayout(dev_row)

        m_row1 = QHBoxLayout()
        m_row1.addWidget(QLabel("Модель Whisper:"))
        self.cmb_model = LightComboBox(self)
        self.cmb_model.addItem("Автовыбор (GPU: large-v3-turbo / Ноутбук: small)", "auto")
        self.cmb_model.addItem("large-v3-turbo (Максимальная точность)", "large-v3-turbo")
        self.cmb_model.addItem("medium (Высокая точность)", "medium")
        self.cmb_model.addItem("small (Оптимально для ноутбуков и CPU)", "small")
        self.cmb_model.addItem("base (Базовая, быстрая)", "base")
        m_row1.addWidget(self.cmb_model, 2)
        m_layout.addLayout(m_row1)

        m_row2 = QHBoxLayout()
        m_row2.addWidget(QLabel("Язык по умолчанию:"))
        self.cmb_lang = LightComboBox(self)
        self.cmb_lang.addItem("Автоопределение (RU / EN)", "auto")
        self.cmb_lang.addItem("Русский", "ru")
        self.cmb_lang.addItem("English", "en")
        m_row2.addWidget(self.cmb_lang, 2)
        m_layout.addLayout(m_row2)

        self.chk_fast_lang = QCheckBox("Быстрое автоопределение языка (без задержки)", self)
        m_layout.addWidget(self.chk_fast_lang)

        self.chk_vad = QCheckBox("Фильтрация пауз и тишины (Silero VAD, ускоряет работу)", self)
        m_layout.addWidget(self.chk_vad)

        hw = detect_hardware()
        self.lbl_hw_info = QLabel(f"{hw['mode_desc']}. При переносе на ноутбук без GPU система автоматически переключится на оптимизированный режим CPU INT8.", self)
        self.lbl_hw_info.setWordWrap(True)
        self.lbl_hw_info.setStyleSheet("color: #71717a; font-size: 11px;")
        m_layout.addWidget(self.lbl_hw_info)

        layout.addWidget(model_group)

        # Буфер и поведение
        beh_group = QGroupBox("Поведение")
        b_layout = QVBoxLayout(beh_group)
        b_layout.setSpacing(6)

        self.chk_always_clip = QCheckBox("Копировать результат в буфер обмена Windows (всегда включено)", self)
        self.chk_always_clip.setChecked(True)
        self.chk_always_clip.setEnabled(False)
        b_layout.addWidget(self.chk_always_clip)

        self.chk_auto_paste = QCheckBox("Автоматически вставлять в активное окно (Ctrl + V)", self)
        b_layout.addWidget(self.chk_auto_paste)

        self.chk_clean_fillers = QCheckBox("Очищать слова-паразиты, междометия и заикания (э-э, ну, повторы)", self)
        b_layout.addWidget(self.chk_clean_fillers)

        self.chk_vocab_in_settings = QCheckBox("Пользовательский словарь и горячие слова (вкладка «Словарь»)", self)
        self.chk_vocab_in_settings.toggled.connect(self._on_settings_vocab_toggle)
        b_layout.addWidget(self.chk_vocab_in_settings)

        sound_row = QHBoxLayout()
        sound_row.addWidget(QLabel("Звуковые эффекты:"))
        self.cmb_sound_theme = LightComboBox(self)
        self.cmb_sound_theme.addItem("Hi-Fi студийные перезвоны", "hifi")
        self.cmb_sound_theme.addItem("Классические тоновые сигналы", "classic")
        self.cmb_sound_theme.addItem("Звуки отключены", "off")
        sound_row.addWidget(self.cmb_sound_theme, 2)
        b_layout.addLayout(sound_row)

        self.chk_overlay = QCheckBox("Плавающий оверлей на экране (с матричным VU-метром)", self)
        b_layout.addWidget(self.chk_overlay)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Расположение оверлея:"))
        self.cmb_overlay_pos = LightComboBox(self)
        self.cmb_overlay_pos.addItem("Вверху по центру (по умолчанию)", "top_center")
        self.cmb_overlay_pos.addItem("Внизу по центру", "bottom_center")
        self.cmb_overlay_pos.addItem("Вверху справа", "top_right")
        self.cmb_overlay_pos.addItem("Внизу справа", "bottom_right")
        self.cmb_overlay_pos.addItem("Рядом с курсором мыши", "cursor")
        self.cmb_overlay_pos.addItem("Своя позиция (перетаскивание мышью)", "custom")
        pos_row.addWidget(self.cmb_overlay_pos, 2)
        b_layout.addLayout(pos_row)

        lbl_drag_hint = QLabel("💡 Оверлей можно свободно перетаскивать мышью в любое место экрана.", self)
        lbl_drag_hint.setStyleSheet("color: #71717a; font-size: 11px;")
        b_layout.addWidget(lbl_drag_hint)

        self.chk_autostart = QCheckBox("Запускать автоматически при входе в Windows (автозапуск)", self)
        b_layout.addWidget(self.chk_autostart)

        self.chk_start_minimized_settings = QCheckBox("Запускать свернутым в системный трей", self)
        self.chk_start_minimized_settings.setToolTip("Если включено, при запуске программа будет сразу сворачиваться в системный трей")
        self.chk_start_minimized_settings.toggled.connect(self._on_start_minimized_toggled)
        b_layout.addWidget(self.chk_start_minimized_settings)

        self.chk_console = QCheckBox("Показывать окно консоли Windows", self)
        self.chk_console.setToolTip("Если отключено, окно консоли будет скрыто")
        self.chk_console.toggled.connect(self._on_console_toggled)
        b_layout.addWidget(self.chk_console)

        layout.addWidget(beh_group)

        # Микрофон и шумоподавление
        mic_group = QGroupBox("Аудиоустройство и шумоподавление")
        mic_vlayout = QVBoxLayout(mic_group)
        mic_vlayout.setSpacing(8)

        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Микрофон:"))
        self.cmb_devices = LightComboBox(self)
        self._populate_audio_devices()
        mic_row.addWidget(self.cmb_devices, 2)
        mic_vlayout.addLayout(mic_row)

        self.chk_noise_gate = QCheckBox("Шумоподавление фона и кулеров (Noise Gate)", self)
        mic_vlayout.addWidget(self.chk_noise_gate)

        ng_row = QHBoxLayout()
        ng_row.addWidget(QLabel("Чувствительность шумоподавления:"))
        self.cmb_noise_level = LightComboBox(self)
        self.cmb_noise_level.addItem("Средняя (рекомендуется)", "medium")
        self.cmb_noise_level.addItem("Мягкая (только тихое шипение)", "soft")
        self.cmb_noise_level.addItem("Агрессивная (для шумных помещений)", "aggressive")
        ng_row.addWidget(self.cmb_noise_level, 2)
        mic_vlayout.addLayout(ng_row)

        layout.addWidget(mic_group)

        layout.addStretch()

        btn_save = QPushButton("Сохранить настройки", self)
        btn_save.setFixedHeight(38)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #f4f4f5;
                border: 1px solid #d4d4d8;
                border-radius: 6px;
                color: #000000;
                font-weight: 600;
                font-size: 13px;
                padding: 7px 16px;
            }
            QPushButton:hover {
                background-color: #e4e4e7;
                border: 1px solid #a1a1aa;
                color: #000000;
            }
            QPushButton:pressed {
                background-color: #d4d4d8;
                border: 1px solid #71717a;
                color: #000000;
            }
        """)
        btn_save.clicked.connect(self._save_settings)
        layout.addWidget(btn_save)

        return w

    def _populate_audio_devices(self):
        self.cmb_devices.clear()
        self.cmb_devices.addItem("По умолчанию Windows", None)
        try:
            devs = sd.query_devices()
            for idx, d in enumerate(devs):
                if d.get('max_input_channels', 0) > 0:
                    name = d.get('name', f"Device {idx}")
                    self.cmb_devices.addItem(f"{name} (ID: {idx})", idx)
        except Exception as e:
            print(f"[GUI] Ошибка списка аудиоустройств: {e}")

    def sync_settings_ui(self):
        cur_hk = config.get("hotkey", "ctrl+`")
        self.hotkey_recorder.set_hotkey(cur_hk)
        disp_hk = format_hotkey_display(cur_hk)

        cur_trans_hk = config.get("translate_hotkey", "alt+`")
        self.translate_hotkey_recorder.set_hotkey(cur_trans_hk)
        disp_trans_hk = format_hotkey_display(cur_trans_hk)

        if config.get("hotkey_mode", "toggle") == "hold":
            self.rad_hold.setChecked(True)
        else:
            self.rad_toggle.setChecked(True)

        cur_dev = config.get("device", "auto")
        for i in range(self.cmb_device.count()):
            if self.cmb_device.itemData(i) == cur_dev:
                self.cmb_device.setCurrentIndex(i)
                break

        cur_model = config.get("model_name", "auto")
        for i in range(self.cmb_model.count()):
            if self.cmb_model.itemData(i) == cur_model:
                self.cmb_model.setCurrentIndex(i)
                break

        cur_lang = config.get("language", "auto")
        for i in range(self.cmb_lang.count()):
            if self.cmb_lang.itemData(i) == cur_lang:
                self.cmb_lang.setCurrentIndex(i)
                break

        self.chk_fast_lang.setChecked(config.get("fast_lang_detect", True))
        self.chk_vad.setChecked(config.get("vad_filter", True))

        self.chk_auto_paste.setChecked(config.get("auto_paste", True))
        self.chk_clean_fillers.setChecked(config.get("clean_fillers", True))
        voc_enabled = config.get("custom_vocabulary_enabled", True)
        self.chk_vocab_in_settings.setChecked(voc_enabled)
        self._load_vocabulary_ui()

        cur_sound = config.get("sound_theme", "hifi")
        if not config.get("play_sounds", True):
            cur_sound = "off"
        for i in range(self.cmb_sound_theme.count()):
            if self.cmb_sound_theme.itemData(i) == cur_sound:
                self.cmb_sound_theme.setCurrentIndex(i)
                break

        self.chk_overlay.setChecked(config.get("show_overlay", True))
        cur_pos = config.get("overlay_position", "top_center")
        for i in range(self.cmb_overlay_pos.count()):
            if self.cmb_overlay_pos.itemData(i) == cur_pos:
                self.cmb_overlay_pos.setCurrentIndex(i)
                break

        self.chk_autostart.setChecked(autostart.is_autostart_enabled())
        is_start_min = config.get("start_minimized", False)
        if hasattr(self, 'chk_start_minimized'):
            self.chk_start_minimized.blockSignals(True)
            self.chk_start_minimized.setChecked(is_start_min)
            self.chk_start_minimized.blockSignals(False)
        if hasattr(self, 'chk_start_minimized_settings'):
            self.chk_start_minimized_settings.blockSignals(True)
            self.chk_start_minimized_settings.setChecked(is_start_min)
            self.chk_start_minimized_settings.blockSignals(False)
        self.chk_console.blockSignals(True)
        self.chk_console.setChecked(config.get("show_console", False))
        self.chk_console.blockSignals(False)

        dev_idx = config.get("input_device_index", None)
        for i in range(self.cmb_devices.count()):
            if self.cmb_devices.itemData(i) == dev_idx:
                self.cmb_devices.setCurrentIndex(i)
                break

        self.chk_noise_gate.setChecked(config.get("noise_gate", True))
        cur_ng_lvl = config.get("noise_gate_level", "medium")
        for i in range(self.cmb_noise_level.count()):
            if self.cmb_noise_level.itemData(i) == cur_ng_lvl:
                self.cmb_noise_level.setCurrentIndex(i)
                break

        self.hotkey_hint.setText(f"Диктовка: {disp_hk} • Перевод (RU -> EN): {disp_trans_hk}. Текст в буфере.")
        if not (self.recorder and getattr(self.recorder, 'is_recording', False)):
            self.btn_record.setText(f"Начать запись ({disp_hk})")
            self.btn_record.setIcon(get_play_icon())

    def _save_settings(self):
        new_hk = self.hotkey_recorder.get_hotkey().strip()
        new_trans_hk = self.translate_hotkey_recorder.get_hotkey().strip()
        new_mode = "hold" if self.rad_hold.isChecked() else "toggle"
        new_device = self.cmb_device.currentData()
        new_model = self.cmb_model.currentData()
        new_lang = self.cmb_lang.currentData()
        new_fast_lang = self.chk_fast_lang.isChecked()
        new_vad = self.chk_vad.isChecked()
        new_clean_fillers = self.chk_clean_fillers.isChecked()
        new_vocab_enabled = self.chk_vocab_in_settings.isChecked()
        new_paste = self.chk_auto_paste.isChecked()
        new_sound_theme = self.cmb_sound_theme.currentData()
        new_sounds = (new_sound_theme != "off")
        new_overlay = self.chk_overlay.isChecked()
        new_overlay_pos = self.cmb_overlay_pos.currentData()
        new_console = self.chk_console.isChecked()
        new_dev = self.cmb_devices.currentData()
        new_ng = self.chk_noise_gate.isChecked()
        new_ng_lvl = self.cmb_noise_level.currentData()

        config.set("hotkey", new_hk)
        config.set("translate_hotkey", new_trans_hk)
        config.set("hotkey_mode", new_mode)
        config.set("device", new_device)
        config.set("model_name", new_model)
        config.set("language", new_lang)
        config.set("fast_lang_detect", new_fast_lang)
        config.set("vad_filter", new_vad)
        config.set("clean_fillers", new_clean_fillers)
        config.set("custom_vocabulary_enabled", new_vocab_enabled)
        if hasattr(self, 'chk_vocab_enabled'):
            self.chk_vocab_enabled.setChecked(new_vocab_enabled)
        config.set("auto_paste", new_paste)
        config.set("sound_theme", new_sound_theme)
        config.set("play_sounds", new_sounds)
        config.set("show_overlay", new_overlay)
        config.set("overlay_position", new_overlay_pos)
        config.set("show_console", new_console)
        set_console_visible(new_console)
        config.set("input_device_index", new_dev)
        config.set("noise_gate", new_ng)
        config.set("noise_gate_level", new_ng_lvl)

        if self.chk_autostart.isChecked():
            autostart.enable_autostart()
        else:
            autostart.disable_autostart()

        if hasattr(self, 'chk_start_minimized'):
            config.set("start_minimized", self.chk_start_minimized.isChecked())

        self.sync_settings_ui()
        self.settings_saved.emit()
        QMessageBox.information(self, "Настройки", "Параметры сохранены.")

    def _on_start_minimized_toggled(self, checked: bool):
        if hasattr(self, 'chk_start_minimized'):
            self.chk_start_minimized.blockSignals(True)
            self.chk_start_minimized.setChecked(checked)
            self.chk_start_minimized.blockSignals(False)
        if hasattr(self, 'chk_start_minimized_settings'):
            self.chk_start_minimized_settings.blockSignals(True)
            self.chk_start_minimized_settings.setChecked(checked)
            self.chk_start_minimized_settings.blockSignals(False)
        config.set("start_minimized", checked)

    def _on_console_toggled(self, checked: bool):
        set_console_visible(checked)
        config.set("show_console", checked)

    def _on_settings_vocab_toggle(self, checked: bool):
        if hasattr(self, 'chk_vocab_enabled') and self.chk_vocab_enabled.isChecked() != checked:
            self.chk_vocab_enabled.setChecked(checked)

    def set_recording_state(self, is_recording: bool, task: str = "transcribe"):
        if is_recording:
            if task == "translate":
                hotkey_str = format_hotkey_display(config.get("translate_hotkey", "alt+`"))
                self.btn_record.setText(f"Остановить перевод ({hotkey_str})")
            else:
                hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
                self.btn_record.setText(f"Остановить запись ({hotkey_str})")
            self.btn_record.setIcon(get_stop_icon())
            self.btn_record.setObjectName("recordBtnActive")
            self.btn_record.setStyle(self.btn_record.style())
            self.vol_timer.start(33)
        else:
            hotkey_str = format_hotkey_display(config.get("hotkey", "ctrl+`"))
            self.btn_record.setText(f"Начать запись ({hotkey_str})")
            self.btn_record.setIcon(get_play_icon())
            self.btn_record.setObjectName("primaryBtn")
            self.btn_record.setStyle(self.btn_record.style())
            self.vol_timer.stop()
            self.vol_bar.reset()
            self.lbl_record_time.setText("00:00")

    def update_record_duration(self, seconds: float):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        self.lbl_record_time.setText(f"{mins:02d}:{secs:02d}")

    def _update_volume_meter(self):
        if hasattr(self.recorder, 'get_audio_bands'):
            bands = self.recorder.get_audio_bands()
            self.vol_bar.update_from_bands(bands)
        else:
            vol = self.recorder.get_volume()
            self.vol_bar.update_from_volume(vol)
        dur = self.recorder.get_duration()
        self.update_record_duration(dur)

    def display_latest_text(self, text: str):
        self.txt_latest.setPlainText(text)
        self.lbl_copy_status.setText("Скопировано в буфер")
        QTimer.singleShot(2500, lambda: self.lbl_copy_status.setText(""))
        self.load_history_table()

    def _copy_latest_text(self):
        text = self.txt_latest.toPlainText()
        if text:
            copy_to_clipboard(text)
            self.lbl_copy_status.setText("Скопировано в буфер")
            QTimer.singleShot(2500, lambda: self.lbl_copy_status.setText(""))

    def load_history_table(self):
        entries = history.get_all()
        self.table_history.setRowCount(len(entries))
        for row, item in enumerate(entries):
            self.table_history.setItem(row, 0, QTableWidgetItem(item.get("timestamp", "")))
            self.table_history.setItem(row, 1, QTableWidgetItem(item.get("language", "")))
            self.table_history.setItem(row, 2, QTableWidgetItem(f"{item.get('duration', 0)} с"))
            self.table_history.setItem(row, 3, QTableWidgetItem(item.get("text", "")))

    def _on_history_row_double_clicked(self, item):
        row = item.row()
        text_item = self.table_history.item(row, 3)
        if text_item:
            text = text_item.text()
            copy_to_clipboard(text)
            self.txt_latest.setPlainText(text)
            self.lbl_copy_status.setText("Скопировано из истории")
            QTimer.singleShot(2500, lambda: self.lbl_copy_status.setText(""))

    def _copy_selected_history(self):
        selected_rows = set(index.row() for index in self.table_history.selectedIndexes())
        texts = []
        for row in sorted(selected_rows):
            item = self.table_history.item(row, 3)
            if item:
                texts.append(item.text())
        if texts:
            combined = "\n".join(texts)
            copy_to_clipboard(combined)
            self.lbl_copy_status.setText("Выбранные строки скопированы")
            QTimer.singleShot(2500, lambda: self.lbl_copy_status.setText(""))

    def _clear_history(self):
        reply = QMessageBox.question(self, "Очистка истории", "Удалить историю записей?")
        if reply == QMessageBox.StandardButton.Yes:
            history.clear()
            self.load_history_table()

    # Файловая транскрибация
    def _browse_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла",
            "",
            "Медиа файлы (*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.mov *.webm *.aac);;Все файлы (*.*)"
        )
        if path:
            self.selected_file_path = path
            size_mb = os.path.getsize(path) / (1024 * 1024)
            self.lbl_selected_file.setText(f"{os.path.basename(path)} ({size_mb:.1f} МБ)")
            self.btn_transcribe_file.setEnabled(True)

    def _start_file_transcription(self):
        if not hasattr(self, 'selected_file_path') or not self.selected_file_path:
            return

        lang_idx = self.cmb_file_lang.currentIndex()
        lang = "auto" if lang_idx == 0 else ("ru" if lang_idx == 1 else "en")

        self.btn_transcribe_file.setEnabled(False)
        self.file_progress_bar.setVisible(True)
        self.file_progress_bar.setValue(0)
        self.lbl_file_status.setText("Идет обработка...")

        self.file_worker = FileTranscriptionWorker(self.selected_file_path, language=lang)
        self.file_worker.progress_signal.connect(self._on_file_progress)
        self.file_worker.finished_signal.connect(self._on_file_finished)
        self.file_worker.error_signal.connect(self._on_file_error)
        self.file_worker.start()

    def _on_file_progress(self, percent, text):
        self.file_progress_bar.setValue(percent)
        self.lbl_file_status.setText(f"{percent}%: {text[:60]}")

    def _on_file_finished(self, full_text, segments, lang):
        self.last_file_segments = segments
        self.txt_file_result.setPlainText(full_text)
        self.file_progress_bar.setValue(100)
        self.lbl_file_status.setText(f"Завершено ({lang.upper()}). Текст скопирован в буфер.")
        self.btn_transcribe_file.setEnabled(True)
        copy_to_clipboard(full_text)

    def _on_file_error(self, err_msg):
        self.lbl_file_status.setText(f"Ошибка: {err_msg}")
        self.btn_transcribe_file.setEnabled(True)
        QMessageBox.critical(self, "Ошибка транскрибации", f"Не удалось распознать файл:\n{err_msg}")

    def _save_file_txt(self):
        text = self.txt_file_result.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", "transcript.txt", "Текстовые файлы (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def _save_file_srt(self):
        if not self.last_file_segments:
            QMessageBox.warning(self, "Субтитры", "Сначала распознайте файл для создания субтитров.")
            return
        srt_content = export_to_srt(self.last_file_segments)
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт субтитров", "subtitles.srt", "Субтитры SRT (*.srt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(srt_content)

    def toggle_recording(self):
        self.request_toggle_recording.emit()

    def show_and_activate(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()
        if hasattr(self, "tray") and self.tray:
            self.tray.update_icon_for_window_state()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.ico")
                if os.path.exists(ico_path):
                    user32 = ctypes.windll.user32
                    h_sm = user32.LoadImageW(None, ico_path, 1, 16, 16, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
                    h_big = user32.LoadImageW(None, ico_path, 1, 32, 32, 0x10)
                    if h_sm:
                        user32.SendMessageW(hwnd, 0x007F, 0, h_sm)  # WM_SETICON, ICON_SMALL
                    if h_big:
                        user32.SendMessageW(hwnd, 0x007F, 1, h_big)  # WM_SETICON, ICON_BIG
            except Exception:
                pass

        if hasattr(self, "tray") and self.tray:
            self.tray.update_icon_for_window_state()

    def minimize_to_tray(self):
        self.hide()
        if hasattr(self, "tray") and self.tray:
            self.tray.show_minimized_notification()

    def quit_application(self):
        self.request_quit.emit()

    def closeEvent(self, event):
        event.ignore()
        self.minimize_to_tray()
