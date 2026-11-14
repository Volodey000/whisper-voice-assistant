from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF

def _render_mic_pixmap(size: int, is_recording: bool) -> QPixmap:
    """Рендерит пиксельно точную иконку микрофона для конкретного размера (16, 20, 24, 32, 48, 64)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Цветовая гамма shadcn Zinc Dark с высоким контрастом границ
    bg_color = QColor(24, 24, 27)  # zinc-900
    border_color = QColor(239, 68, 68) if is_recording else QColor(140, 140, 150)  # контрастный контур
    mic_color = QColor(239, 68, 68) if is_recording else QColor(255, 255, 255)  # чистый белый

    border_w = 1.0 if size <= 20 else (1.5 if size <= 32 else 2.0)
    pad = border_w / 2.0 + (0.5 if size <= 20 else 1.0)
    r = 3.0 if size <= 20 else (5.0 if size <= 32 else 8.0)

    # Фоновая плитка
    p.setBrush(QBrush(bg_color))
    p.setPen(QPen(border_color, border_w))
    p.drawRoundedRect(QRectF(pad, pad, size - pad * 2, size - pad * 2), r, r)

    # Капсюль микрофона
    s = size / 32.0
    cw = max(3.0, 7.0 * s)
    ch = max(5.0, 11.0 * s)
    cx = (size - cw) / 2.0
    cy = 5.5 * s
    cr = cw / 2.0

    p.setBrush(QBrush(mic_color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(cx, cy, cw, ch), cr, cr)

    # Дуга подставки
    aw = cw + 5.0 * s
    ah = ch * 0.75
    ax = (size - aw) / 2.0
    ay = cy + ch * 0.45
    arc_pen = max(1.2, 1.8 * s)
    p.setPen(QPen(mic_color, arc_pen, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(ax, ay, aw, ah), 0, -180 * 16)

    # Ножка и основание
    sy1 = ay + ah
    sy2 = min(float(size - 3), sy1 + max(2.5, 4.0 * s))
    p.drawLine(QPointF(size / 2.0, sy1), QPointF(size / 2.0, sy2))

    bw = cw + 3.0 * s
    p.drawLine(QPointF(size / 2.0 - bw / 2.0, sy2), QPointF(size / 2.0 + bw / 2.0, sy2))

    # Красный индикатор активности записи в правом верхнем углу
    if is_recording:
        dot_r = max(3.0, 5.0 * s)
        p.setBrush(QBrush(QColor(239, 68, 68)))
        p.setPen(QPen(QColor(255, 255, 255), 1.0) if size >= 24 else Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(size - pad - dot_r, pad, dot_r, dot_r))

    p.end()
    return pix

def get_tray_icon(is_recording=False) -> QIcon:
    """
    Возвращает многомасштабную иконку (16x16, 20x20, 24x24, 32x32, 48x48, 64x64)
    специально оптимизированную для системного трея Windows при любых масштабах DPI.
    """
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64):
        icon.addPixmap(_render_mic_pixmap(size, is_recording))
    return icon

def get_app_icon(is_recording=False) -> QIcon:
    """Иконка окна приложения и панели задач Windows."""
    return get_tray_icon(is_recording)

def get_tray_minimize_icon() -> QIcon:
    """Лаконичная векторная иконка 'Свернуть в трей' в стиле shadcn / Lucide."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    pen = QPen(
        QColor(24, 24, 27),
        2,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.RoundCap,
        Qt.PenJoinStyle.RoundJoin
    )
    p.setPen(pen)

    # Стрелка, направленная в лоток (трей)
    p.drawLine(16, 7, 16, 17)
    p.drawLine(11, 13, 16, 18)
    p.drawLine(21, 13, 16, 18)

    # Символ лотка трея
    p.drawLine(7, 19, 7, 24)
    p.drawLine(7, 24, 25, 24)
    p.drawLine(25, 24, 25, 19)

    p.end()
    return QIcon(pix)

def _render_play_pixmap(size: int, color_hex: str = "#10b981") -> QPixmap:
    """Рендерит векторную иконку Play (равносторонний треугольник со скругленными вершинами)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    pad_y = size * 0.22
    h = size - pad_y * 2
    w = h * 0.92
    x_offset = (size - w) / 2.0 + (size * 0.05)  # оптическое центрирование
    y_offset = pad_y

    path = QPainterPath()
    p1 = QPointF(x_offset, y_offset)
    p2 = QPointF(x_offset + w, y_offset + h / 2.0)
    p3 = QPointF(x_offset, y_offset + h)

    path.moveTo(p1)
    path.lineTo(p2)
    path.lineTo(p3)
    path.closeSubpath()

    c = QColor(color_hex)
    p.setBrush(QBrush(c))
    pen = QPen(c, max(1.0, size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawPath(path)
    p.end()
    return pix

def _render_stop_pixmap(size: int, color_hex: str = "#ffffff") -> QPixmap:
    """Рендерит векторную иконку Stop (квадрат со скругленными углами)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    pad = size * 0.24
    side = size - pad * 2
    r = max(1.5, side * 0.22)

    p.setBrush(QBrush(QColor(color_hex)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(pad, pad, side, side), r, r)
    p.end()
    return pix

def get_play_icon(size: int = 24, color_hex: str = "#10b981") -> QIcon:
    """Многомасштабная векторная иконка Play для кнопки быстрой записи."""
    icon = QIcon()
    for s in (16, 20, 24, 32, 48):
        icon.addPixmap(_render_play_pixmap(s, color_hex))
    return icon

def get_stop_icon(size: int = 24, color_hex: str = "#ffffff") -> QIcon:
    """Многомасштабная векторная иконка Stop для кнопки активной записи."""
    icon = QIcon()
    for s in (16, 20, 24, 32, 48):
        icon.addPixmap(_render_stop_pixmap(s, color_hex))
    return icon

def save_app_icons(target_dir: str = None):
    """
    Генерирует и сохраняет файлы app_icon.ico (мультимасштабный 16..256),
    icon.ico и app_icon.png в папку проекта.
    """
    import os, sys, struct
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QBuffer, QIODevice

    # Если QApplication еще не инициализирован, создаем offscreen-экземпляр
    app = QApplication.instance()
    app_created = False
    if app is None:
        app = QApplication([sys.argv[0], "-platform", "offscreen"])
        app_created = True

    if target_dir is None:
        target_dir = os.path.dirname(os.path.abspath(__file__))

    # PNG высокого разрешения (256x256)
    png_path = os.path.join(target_dir, "app_icon.png")
    pix256 = _render_mic_pixmap(256, False)
    pix256.save(png_path, "PNG")

    # Мультимасштабный ICO для Windows (16, 20, 24, 32, 48, 64, 128, 256)
    sizes = [16, 20, 24, 32, 48, 64, 128, 256]
    png_data_list = []
    for s in sizes:
        pix = _render_mic_pixmap(s, False)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        png_data_list.append((s, bytes(buf.data())))

    header = struct.pack('<HHH', 0, 1, len(png_data_list))
    offset = 6 + 16 * len(png_data_list)
    entry_bytes = bytearray()
    for s, data in png_data_list:
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        size_bytes = len(data)
        entry_bytes += struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, size_bytes, offset)
        offset += size_bytes

    ico_bytes = header + bytes(entry_bytes) + b''.join(d for _, d in png_data_list)
    for fname in ("app_icon.ico", "icon.ico"):
        p = os.path.join(target_dir, fname)
        with open(p, "wb") as f:
            f.write(ico_bytes)

    if app_created:
        app.quit()

