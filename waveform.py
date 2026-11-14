import numpy as np
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QPainterPath
from PyQt6.QtWidgets import QWidget

def create_smooth_path(points: list[QPointF]) -> QPainterPath:
    """
    Строит гладкую кривую (Catmull-Rom к кубическому сплайну Безье),
    проходящую точно через все заданные опорные точки без изломов и острых углов.
    """
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(points[0])
    if len(points) == 1:
        return path
    if len(points) == 2:
        path.lineTo(points[1])
        return path

    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2

        ctrl1_x = p1.x() + (p2.x() - p0.x()) / 6.0
        ctrl1_y = p1.y() + (p2.y() - p0.y()) / 6.0
        ctrl2_x = p2.x() - (p3.x() - p1.x()) / 6.0
        ctrl2_y = p2.y() - (p3.y() - p1.y()) / 6.0

        path.cubicTo(QPointF(ctrl1_x, ctrl1_y), QPointF(ctrl2_x, ctrl2_y), p2)
    return path


class WaveformVisualizer(QWidget):
    """
    Плавный симметричный спектральный визуализатор звуковой волны (Continuous Waveform VU).
    Полностью заменяет дискретные столбики непрерывной плавной акустической огибающей.
    
    Поддерживает темы:
      - 'matrix': неоновый фосфорный стиль матрицы для темного плавающего оверлея
      - 'light': изумрудный стиль shadcn Zinc для светлого интерфейса программы
    """
    def __init__(
        self,
        parent=None,
        theme: str = "matrix",
        fixed_width: int = None,
        fixed_height: int = 28,
        num_nodes: int = 19,
        gain: float = 2.8
    ):
        super().__init__(parent)
        self.theme = theme
        self.num_nodes = max(9, num_nodes)
        self.node_levels = [0.0] * self.num_nodes
        self.gain = gain

        if fixed_width is not None and fixed_height is not None:
            self.setFixedSize(fixed_width, fixed_height)
        elif fixed_height is not None:
            self.setFixedHeight(fixed_height)

        # Веса гармонического распределения речевых частот (форманты гласных)
        self._speech_weights = [0.15, 0.35, 0.65, 0.90, 0.98, 0.88, 0.70, 0.52, 0.38, 0.22, 0.12]

    def update_from_bands(self, bands: list[float]):
        """
        Обновляет огибающую волны на основе спектральных частот (например, 11 полос FFT).
        Интерполирует спектр в num_nodes с естественной баллистикой атаки и спада.
        """
        if not bands:
            self.reset()
            return

        nb = len(bands)
        # Интерполяция полос в узлы гладкой кривой
        src_xs = np.linspace(0.0, 1.0, nb)
        dst_xs = np.linspace(0.0, 1.0, self.num_nodes)
        interp = np.interp(dst_xs, src_xs, bands)

        for i in range(self.num_nodes):
            # Дополнительное пространственное сглаживание соседних узлов
            left = interp[i - 1] if i > 0 else interp[i]
            right = interp[i + 1] if i < self.num_nodes - 1 else interp[i]
            target = float(0.68 * interp[i] + 0.16 * left + 0.16 * right)

            if target > self.node_levels[i]:
                # Мгновенная атака на голос (fast attack)
                self.node_levels[i] = target
            else:
                # Плавный сход для устранения дрожания (smooth decay)
                self.node_levels[i] = max(0.0, self.node_levels[i] * 0.80 - 0.012)

        self.update()

    def update_from_volume(self, raw_volume: float):
        """
        Fallback-обновление по единому RMS-уровню громкости:
        синтезирует спектральную форму голосовой форманты с увеличенной чувствительностью.
        """
        norm_vol = min(1.0, (raw_volume * 45.0) ** 0.60)
        bands = [min(1.0, norm_vol * w) for w in self._speech_weights]
        self.update_from_bands(bands)

    def setValue(self, val: int):
        """Совместимость с интерфейсом QProgressBar (0..100)."""
        self.update_from_volume(float(val) / 100.0)

    def reset(self):
        """Сброс волны в покой (тишина)."""
        self.node_levels = [0.0] * self.num_nodes
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        total_w = float(self.width())
        total_h = float(self.height())
        cy = total_h / 2.0
        max_amp = max(2.0, (total_h - 4.0) / 2.0)

        # 1. Тонкая осевая линия покоя
        if self.theme == "matrix":
            zero_pen = QPen(QColor(0, 255, 102, 40), 1.0, Qt.PenStyle.DotLine)
        else:
            zero_pen = QPen(QColor(16, 185, 129, 50), 1.0, Qt.PenStyle.DotLine)
        p.setPen(zero_pen)
        p.drawLine(3, int(cy), int(total_w - 3), int(cy))

        # 2. Вычисление симметричных верхних и нижних координат кривой
        xs = np.linspace(3.0, total_w - 3.0, self.num_nodes)
        upper_pts = []
        lower_pts = []

        for i, x in enumerate(xs):
            lvl = self.node_levels[i]
            # Умножение амплитуды колебаний на ~2.5x - 3.0x с мягким компрессионным насыщением
            amplified_lvl = min(1.0, (lvl * self.gain) ** 0.85)

            # Широкое раскрытие волны по всей ширине с плавным сужением только у самых концов
            edge_factor = np.sin((i / max(1, self.num_nodes - 1)) * np.pi) ** 0.55
            amp = 0.8 + amplified_lvl * (max_amp - 0.8) * edge_factor
            upper_pts.append(QPointF(x, cy - amp))
            lower_pts.append(QPointF(x, cy + amp))

        # 3. Построение замкнутого пути для заливки градиентом
        wave_path = create_smooth_path(upper_pts)
        lower_rev = create_smooth_path(list(reversed(lower_pts)))
        wave_path.lineTo(lower_pts[-1])
        wave_path.connectPath(lower_rev)
        wave_path.lineTo(upper_pts[0])
        wave_path.closeSubpath()

        # 4. Градиентная заливка волны
        grad = QLinearGradient(0, cy - max_amp, 0, cy + max_amp)
        if self.theme == "matrix":
            grad.setColorAt(0.0, QColor(0, 255, 102, 35))
            grad.setColorAt(0.35, QColor(52, 211, 153, 140))
            grad.setColorAt(0.5, QColor(0, 255, 102, 230))
            grad.setColorAt(0.65, QColor(52, 211, 153, 140))
            grad.setColorAt(1.0, QColor(0, 255, 102, 35))
            stroke_color = QColor(0, 255, 102, 240)
            center_color = QColor(167, 243, 208, 190)
        else:
            grad.setColorAt(0.0, QColor(16, 185, 129, 25))
            grad.setColorAt(0.35, QColor(16, 185, 129, 110))
            grad.setColorAt(0.5, QColor(5, 150, 105, 190))
            grad.setColorAt(0.65, QColor(16, 185, 129, 110))
            grad.setColorAt(1.0, QColor(16, 185, 129, 25))
            stroke_color = QColor(5, 150, 105, 230)
            center_color = QColor(16, 185, 129, 130)

        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(wave_path)

        # 5. Плавная контурная линия верхней и нижней кромки
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(stroke_color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(create_smooth_path(upper_pts))
        p.drawPath(create_smooth_path(lower_pts))

        # 6. Тонкая светящаяся центральная нить
        p.setPen(QPen(center_color, 1.0))
        p.drawLine(3, int(cy), int(total_w - 3), int(cy))

        p.end()
