"""Paint Graphite's fictional idle display from its elapsed display time."""

from math import sin

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF

from . import boss_theme as theme
from .boss_qt import charcoal_workshop, draw_plate, midnight_plate


_WIDTH, _HEIGHT = 1440, 900
_INK = QColor(theme.TERMINAL_GROUND)
_FACE = QColor(theme.PANEL)
_RULE = QColor(theme.LINE)
_PAPER = QColor(theme.TEXT)
_MUTED = QColor(theme.QUIET)
_AMBER = QColor(theme.AMBER_EDGE)
_GREEN = QColor(theme.READY)
_FAINT_GREEN = QColor(theme.TEAL_EDGE)
_GRID = QColor('#242923')
_LED_SHADE = QColor('#26321b')

# These invented operations and their operands are display material only.
_OPERATIONS = (
    ('VEC.FOLD', 'lattice/03', '01'), ('PAGE.MAP', 'spool/21', '06'),
    ('BUS.ROUTE', 'crossbar/12', '02'), ('TAPE.SEEK', 'reel/07', '09'),
    ('MASK.XOR', 'plane/04', '03'), ('CELL.SORT', 'grid/18', '08'),
    ('PHASE.LOCK', 'signal/16', '04'), ('BLOCK.SUM', 'vault/09', '07'),
    ('BITS.PACK', 'strand/02', '00'), ('LOOP.CHECK', 'relay/11', '05'),
)
_SCOPE = tuple(0.58 * sin(i / 5) + 0.18 * sin(i / 1.8) for i in range(70))


def _font(size, weight=QFont.Weight.Normal):
    font = QFont(theme.MONO)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size)
    font.setWeight(weight)
    return font


def _line(painter, x1, y1, x2, y2, ink):
    painter.setPen(ink)
    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _text(painter, x, y, text, ink):
    painter.setPen(ink)
    painter.drawText(QPointF(x, y), text)


def _panel(painter, x, y, width, height):
    rect = QRectF(x, y, width, height)
    painter.fillRect(rect, _FACE)
    painter.setPen(_RULE)
    painter.drawRect(rect)


def _word(sequence):
    return (sequence * 0x9E3779B1 + 0x3DA77000) & 0xFFFFFFFF


class IdleDisplayArt:
    """A native drawing with no work, network activity, or system counters."""

    def __init__(self, folder):
        self.folder = folder
        self._tape = None
        self._small = _font(13)
        self._code = _font(14)
        self._label = _font(15, QFont.Weight.DemiBold)
        self._title = _font(39, QFont.Weight.DemiBold)
        self._title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.6)

    def paint(self, painter, rect, seconds, reduced_motion=False):
        rect = QRectF(rect)
        if rect.isEmpty():
            return
        seconds = 0.0 if reduced_motion else max(0.0, seconds)
        painter.save()
        painter.fillRect(rect, _INK)
        scale = min(rect.width() / _WIDTH, rect.height() / _HEIGHT)
        painter.translate(rect.center())
        painter.scale(scale, scale)
        painter.translate(-_WIDTH / 2, -_HEIGHT / 2)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        self._header(painter, reduced_motion)
        self._trace(painter, seconds)
        self._crossbar(painter, seconds)
        self._workshop(painter, seconds)
        self._memory(painter, seconds)
        self._footer(painter)
        painter.restore()

    def _header(self, painter, reduced_motion):
        painter.setFont(self._small)
        _text(painter, 42, 41, 'STRUTHIO WORKSHOP  /  AFTER HOURS', _AMBER)
        painter.setFont(self._title)
        _text(painter, 40, 91, 'GRAPHITE', _PAPER)
        painter.setFont(self._small)
        _text(painter, 43, 117, 'FIELD DISPLAY 07   /   LOCAL ARTWORK', _MUTED)
        badge = QRectF(1180, 44, 218, 43)
        painter.fillRect(badge, _LED_SHADE)
        painter.setPen(_FAINT_GREEN)
        painter.drawRect(badge)
        painter.fillRect(QRectF(1196, 61, 8, 8), _GREEN)
        painter.setFont(self._label)
        _text(painter, 1220, 72, 'SIMULATION', _GREEN)
        painter.setFont(self._small)
        _text(painter, 1181, 113, 'STILL FRAME' if reduced_motion else 'FAST FORWARD   >>   12×', _AMBER)
        _line(painter, 42, 130, 1398, 130, _RULE)

    def _trace(self, painter, seconds):
        _panel(painter, 42, 150, 782, 475)
        painter.setFont(self._label)
        _text(painter, 58, 179, '01 / TRACE BUFFER', _PAPER)
        painter.setFont(self._small)
        _text(painter, 641, 178, 'REPLAY CHANNEL A', _FAINT_GREEN)
        _line(painter, 58, 193, 808, 193, _RULE)
        for x, name in ((59, 'STEP'), (134, 'ADDRESS'), (270, 'OPERATION'),
                        (424, 'OPERAND'), (552, 'DATA WORD'), (756, 'FLAG')):
            _text(painter, x, 218, name, _MUTED)

        step = seconds * 12.0
        index = int(step)
        offset = (step - index) * 21
        painter.save()
        painter.setClipRect(QRectF(57, 230, 751, 342))
        painter.setFont(self._code)
        for row in range(18):
            sequence = 183968 + index - 15 + row
            y = 244 + row * 21 - offset
            word = _word(sequence)
            op, operand, bank = _OPERATIONS[sequence % len(_OPERATIONS)]
            if row == 15:
                painter.fillRect(QRectF(58, y - 15, 748, 21), _LED_SHADE)
            if sequence % 4 == 0:
                _line(painter, 58, y + 5, 808, y + 5, _GRID)
            bright = _PAPER if row >= 12 else _MUTED
            _text(painter, 59, y, f'{sequence:06d}', bright)
            _text(painter, 134, y, f'0x{word:08X}', _FAINT_GREEN)
            _text(painter, 270, y, op, _AMBER)
            _text(painter, 424, y, operand, bright)
            _text(painter, 552, y, f'{word >> 16:04X}  {word & 0xFFFF:04X}  [{bank}]', bright)
            _text(painter, 756, y, 'PASS' if row >= 15 else '··', _GREEN if row >= 15 else _FAINT_GREEN)
        painter.restore()

        _line(painter, 58, 580, 808, 580, _RULE)
        painter.setFont(self._small)
        _text(painter, 58, 607, 'SPOOL / LOOP A', _AMBER)
        for block in range(20):
            color = _GREEN if block <= (index // 3) % 20 else _GRID
            painter.fillRect(QRectF(242 + block * 17, 596, 13, 9), color)
        _text(painter, 641, 607, 'FIXTURE DATA ONLY', _MUTED)

    def _crossbar(self, painter, seconds):
        _panel(painter, 42, 642, 782, 160)
        painter.setFont(self._label)
        _text(painter, 58, 670, '02 / CROSSBAR', _PAPER)
        painter.setFont(self._small)
        _text(painter, 602, 670, 'LOOPBACK WAVE', _FAINT_GREEN)
        _line(painter, 58, 682, 808, 682, _RULE)
        for branch in range(3):
            y = 708 + branch * 27
            _text(painter, 59, y + 4, f'B{branch + 1}', _AMBER)
            for x in (102, 201, 300, 399, 498):
                painter.fillRect(QRectF(x - 3, y - 3, 6, 6), _FAINT_GREEN)
            _line(painter, 102, y, 498, y, _RULE)
            _line(painter, 498, y, 544, 735, _FAINT_GREEN)
        pulse = seconds * 1.45
        x = 102 + (pulse % 1) * 396
        y = 708 + (int(pulse) % 3) * 27
        _line(painter, max(102, x - 44), y, x, y, _AMBER)
        painter.fillRect(QRectF(x - 2, y - 3, 5, 6), _GREEN)
        painter.fillRect(QRectF(541, 732, 7, 7), _GREEN)

        for y in (709, 735, 761):
            _line(painter, 602, y, 806, y, _GRID)
        shift = int(seconds * 13) % len(_SCOPE)
        signal = [QPointF(602 + index * 2.9, 735 + _SCOPE[(index + shift) % len(_SCOPE)] * 26)
                  for index in range(len(_SCOPE))]
        painter.setPen(QPen(_GREEN, 1.2))
        painter.drawPolyline(QPolygonF(signal))

    def _workshop(self, painter, seconds):
        _panel(painter, 844, 150, 554, 472)
        target = QRectF(855, 189, 532, 380)
        painter.setFont(self._label)
        tape = 24.0 <= seconds % 43.0 < 26.5
        from . import boss_theme
        if boss_theme.APPEARANCE == 'kasandra':      # 0.8.0: her office, dusk and rain in turn, in place of the workshop plate
            from . import kasandra_art
            base = self.folder.parent / 'kasandra';scene = kasandra_art.choose(base, 'office_banner', 'idle', int(seconds // 43.0))
            _text(painter, 857, 178, '03 / THE OFFICE', _PAPER);painter.fillRect(target, _INK)
            image = kasandra_art.picture(base, scene, round(target.width()), round(target.height())) if scene else QImage()
            if not image.isNull():painter.drawImage(target, image)
            _line(painter, 856, 585, 1386, 585, _RULE);painter.setFont(self._small)
            _text(painter, 856, 607, 'KASANDRA / ' + (scene['title'].upper() if scene else 'A QUIET ROOM'), _AMBER);_text(painter, 1222, 607, 'STRUTHIO MARK', _MUTED)
            return
        if tape and self._tape is None:
            self._tape = QImage(str(self.folder / 'plates' / 'Brain on Disk.png'))
        if tape and not self._tape.isNull():
            _text(painter, 857, 178, '03 / VHS INTERMISSION', _PAPER)
            self._intermission(painter, target)
            label, detail = 'REEL B / BRAIN ON DISK', '2.5 S / TAPED INSERT'
        else:
            _text(painter, 857, 178, '03 / THE WORKSHOP', _PAPER)
            frame = midnight_plate(self.folder)
            midnight = not frame.isNull()
            if not midnight:
                frame = charcoal_workshop(self.folder)
            painter.fillRect(target, _INK)
            if midnight:
                draw_plate(painter, target, frame, 0.17)
            elif not frame.isNull():
                # Keep the circuit-embroidered cap and the CRT's green lamp in frame.
                height = frame.height() * 0.82
                width = min(frame.width(), height * target.width() / target.height())
                left = min(frame.width() - width, frame.width() * 0.257)
                painter.drawImage(target, frame, QRectF(left, frame.height() * 0.018, width, height))
            label = 'PLATE 07 / AFTER MIDNIGHT' if midnight else 'PLATE 07 / CHARCOAL'
            detail = 'STRUTHIO MARK'
        _line(painter, 856, 585, 1386, 585, _RULE)
        painter.setFont(self._small)
        _text(painter, 856, 607, label, _AMBER)
        _text(painter, 1222, 607, detail, _MUTED)

    def _intermission(self, painter, rect):
        painter.fillRect(rect, _INK)
        ratio = min(rect.width() / self._tape.width(), rect.height() / self._tape.height())
        width = self._tape.width() * ratio
        height = self._tape.height() * ratio
        frame = QRectF(rect.center().x() - width / 2, rect.center().y() - height / 2, width, height)
        painter.drawImage(frame, self._tape)
        scan = QColor(6, 8, 6, 83)
        for y in range(int(frame.top()) + 2, int(frame.bottom()), 6):
            _line(painter, frame.left(), y, frame.right(), y, scan)

    def _memory(self, painter, seconds):
        _panel(painter, 844, 642, 554, 160)
        painter.setFont(self._label)
        _text(painter, 857, 670, '04 / HEX WINDOW', _PAPER)
        painter.setFont(self._small)
        _text(painter, 1256, 670, 'BUFFER 0x70', _FAINT_GREEN)
        _line(painter, 856, 682, 1386, 682, _RULE)
        tick = int(seconds * 3)
        for row in range(4):
            y = 707 + row * 24
            _text(painter, 856, y, f'{0x70 + row * 16:04X}', _AMBER)
            for column in range(10):
                byte = _word(tick + row * 37 + column * 13) >> 20 & 0xFF
                ink = _GREEN if column == (tick + row * 3) % 10 else _FAINT_GREEN
                _text(painter, 933 + column * 44, y, f'{byte:02X}', ink)

    def _footer(self, painter):
        _line(painter, 42, 827, 1398, 827, _RULE)
        painter.fillRect(QRectF(42, 850, 7, 7), _GREEN)
        painter.setFont(self._small)
        _text(painter, 59, 858, 'GRAPHITE   /   IDLE DISPLAY', _MUTED)
        _text(painter, 507, 858, 'Press a key or move the pointer to return', _PAPER)
        _text(painter, 1213, 858, 'REEL LOOP   [A–B]', _AMBER)
