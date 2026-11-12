"""Home backdrop: slow columns of hexadecimal code falling in ARC graphite and orange.

Decoration only; it reads no project data and implies no activity. The animation
stops whenever the backdrop is hidden and becomes one still frame when the reading
profile asks to reduce motion. Nothing flashes: glyph changes are dim and gradual.
"""
import random
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget

GLYPHS = '0123456789ABCDEF' * 3 + '<>=+*/:|'
BASE = QColor('#0b0d11')
TRAIL = QColor('#ff7a1a')
HEAD = QColor('#ffd9b8')


class CodeRain(QWidget):
    FRAME_MS = 50

    def __init__(self, parent=None, seed=1, reduce_motion=False):
        super().__init__(parent)
        self.setObjectName('CodeRain')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAccessibleName('Decorative falling code backdrop')
        self.random = random.Random(seed)
        self.font_ = QFont('DejaVu Sans Mono')
        self.font_.setStyleHint(QFont.Monospace)
        self.font_.setPixelSize(15)
        metrics = QFontMetrics(self.font_)
        self.cell_w, self.cell_h = max(9, metrics.horizontalAdvance('0') + 4), max(14, metrics.height())
        self.columns = []
        self.reduce_motion = reduce_motion
        self.timer = QTimer(self)
        self.timer.setInterval(self.FRAME_MS)
        self.timer.timeout.connect(self.advance)

    def _column(self, rows, start=None):
        r = self.random
        return {'y': r.uniform(-rows, rows) if start is None else start, 'speed': r.uniform(4.0, 11.0),
                'length': r.randint(6, max(7, min(26, rows))), 'glyphs': [r.choice(GLYPHS) for _ in range(rows + 30)],
                'bright': r.uniform(0.45, 1.0)}

    def _fit(self):
        count = self.width() // self.cell_w + 1
        rows = self.height() // self.cell_h + 1
        if len(self.columns) != count or (self.columns and len(self.columns[0]['glyphs']) < rows + 30):
            self.columns = [self._column(rows) for _ in range(count)]

    def set_reduce_motion(self, reduce):
        self.reduce_motion = bool(reduce)
        self._sync_timer()
        self.update()

    def _sync_timer(self):
        active = self.isVisible() and not self.reduce_motion and self.window() is not None \
            and not self.window().isMinimized()
        if active and not self.timer.isActive():self.timer.start()
        elif not active and self.timer.isActive():self.timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._sync_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def advance(self):
        if self.window() is not None and self.window().isMinimized():
            self.timer.stop();return
        rows = self.height() // self.cell_h + 1
        step = self.FRAME_MS / 1000.0
        for column in self.columns:
            column['y'] += column['speed'] * step
            if column['y'] - column['length'] > rows:
                column.update(self._column(rows, start=-self.random.uniform(0, rows * 0.6)))
            elif self.random.random() < 0.08:
                column['glyphs'][self.random.randrange(len(column['glyphs']))] = self.random.choice(GLYPHS)
        self.update()

    def paintEvent(self, event):
        self._fit()
        painter = QPainter(self)
        painter.fillRect(self.rect(), BASE)
        painter.setFont(self.font_)
        for index, column in enumerate(self.columns):
            head = int(column['y'])
            x = index * self.cell_w
            for offset in range(column['length']):
                row = head - offset
                if row < 0 or row * self.cell_h > self.height():continue
                fade = 1.0 - offset / column['length']
                color = QColor(HEAD if offset == 0 else TRAIL)
                color.setAlpha(int((150 if offset == 0 else 95) * fade * column['bright']))
                painter.setPen(color)
                painter.drawText(QRectF(x, row * self.cell_h, self.cell_w, self.cell_h), Qt.AlignCenter,
                                 column['glyphs'][row % len(column['glyphs'])])
        painter.end()
