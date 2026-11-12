"""The Field, drawn: real work objects as sheets in the dark, with the wires that say what feeds what.

Master specification, sections 70 to 72: "Let me move between an overview of an assignment and close work on an artifact."
The selected sheet is the brightest; what touches it stays near; the rest recedes. Enter opens the real editor for the
selected object; the host brings the Field back with the same selection. Nothing is edited or run from here.

Presentation follows the BOSS desk: charcoal ground, cream reading ink, amber for the selection and what waits for the
owner, small green marks for what is current. The surface is static: no timers, no animation. Artwork never enters it.
"""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import boss_theme as t
from .field_model import ATTENTION, KIND_TAG, STATE_CURRENT, STATE_HELD, STATE_OPEN, STATE_RECHECK, Field

DEPTH_INK = (1.0, 0.9, 0.56, 0.36)          # how much of its ink a sheet keeps at each step from the selection
STATE_WORD = {STATE_CURRENT: 'current', STATE_RECHECK: 'recheck', STATE_OPEN: 'open', STATE_HELD: 'held'}


def ink(colour, alpha=1.0):
    c = QColor(colour);c.setAlphaF(max(0.0, min(1.0, alpha)));return c


class FieldView(QWidget):
    """One Field on one surface. `opened` carries the FieldObject the owner asked to open; `left` asks the host to go back."""
    opened = Signal(object)
    left = Signal()
    selection_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.field = Field()
        self.texture = True                 # the quiet scan texture behind the sheets; the Clean desk turns it off
        self.scroll = 0.0
        self._placed = {};self._surface = 0.0;self._gap = 34.0;self._labels = []
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(420, 300)
        self.setAccessibleName('Field: the work in this workspace and what feeds what')
        self.setObjectName('GraphiteField')

    # ---- content ---------------------------------------------------------------------------------------------------
    def set_field(self, field):
        keep = self.field.selected if self.field else ''
        self.field = field or Field()
        if keep and self.field.get(keep):
            self.field.select(keep)
        self.scroll = 0.0
        self._describe();self.update()

    def selected(self):
        return self.field.get(self.field.selected)

    def _describe(self):
        obj = self.selected()
        if obj is None:
            self.setAccessibleDescription('Nothing is here yet.')
        else:
            feeds = [self.field.get(l.target).title for l in self.field.feeds(obj.id)]
            fed = [self.field.get(l.source).title for l in self.field.fed_by(obj.id)]
            words = '%s: %s. State: %s.' % (KIND_TAG.get(obj.kind, obj.kind).capitalize(), obj.title, STATE_WORD.get(obj.state, obj.state))
            if fed:words += ' Fed by ' + ', '.join(fed) + '.'
            if feeds:words += ' Feeds ' + ', '.join(feeds) + '.'
            self.setAccessibleDescription(words)
        self.selection_changed.emit(obj)

    # ---- measures --------------------------------------------------------------------------------------------------
    def scale(self):
        return max(0.85, min(2.0, self.fontInfo().pixelSize() / 16.0))

    def mono(self, px, weight=QFont.Normal):
        f = QFont('IBM Plex Mono');f.setStyleHint(QFont.Monospace);f.setPixelSize(max(9, round(px * self.scale())));f.setWeight(weight);return f

    def sans(self, px, weight=QFont.Medium):
        f = QFont('IBM Plex Sans');f.setPixelSize(max(10, round(px * self.scale())));f.setWeight(weight);return f

    def head_height(self):
        return round(58 * self.scale())

    def foot_height(self):
        return round(92 * self.scale())

    def body(self):
        return QRectF(0, self.head_height(), self.width(), max(1, self.height() - self.head_height() - self.foot_height()))

    def _layout(self):
        body = self.body()
        self._placed, self._surface = self.field.place(body.width(), body.height(), self.scale())
        self.scroll = max(0.0, min(self.scroll, max(0.0, self._surface - body.height())))
        lefts = sorted({round(place.x, 1) for place in self._placed.values()})
        widths = [place.w for place in self._placed.values()]
        self._gap = (lefts[1] - lefts[0] - widths[0]) if len(lefts) > 1 else 34.0
        return body

    def sheet_rect(self, ident, body=None):
        body = body or self.body();p = self._placed.get(ident)
        return None if p is None else QRectF(body.left() + p.x, body.top() + p.y - self.scroll, p.w, p.h)

    def _reveal(self):
        body = self.body();p = self._placed.get(self.field.selected)
        if p is None:return
        if p.y - 12 < self.scroll:self.scroll = max(0.0, p.y - 12)
        elif p.y + p.h + 12 > self.scroll + body.height():self.scroll = p.y + p.h + 12 - body.height()

    # ---- input -----------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key();before = self.field.selected
        moves = {Qt.Key_Left: 'left', Qt.Key_Right: 'right', Qt.Key_Up: 'up', Qt.Key_Down: 'down'}
        if key in moves:self.field.move(moves[key])
        elif key == Qt.Key_Home:self.field.select(self.field.first())
        elif key in (Qt.Key_Tab, Qt.Key_Backtab) and any(o.needs_attention() for o in self.field.objects):
            self.field.next_attention(backwards=key == Qt.Key_Backtab)
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            if self.selected() is not None:self.opened.emit(self.selected())
            return
        elif key == Qt.Key_Escape:
            self.left.emit();return
        else:
            return super().keyPressEvent(event)
        if self.field.selected != before:
            self._layout();self._reveal();self._describe();self.update()

    def focusNextPrevChild(self, forward):
        # Tab walks what needs the owner while there is any; otherwise it leaves the Field as Tab does everywhere.
        if any(o.needs_attention() for o in self.field.objects):return False
        return super().focusNextPrevChild(forward)

    def _hit(self, pos):
        body = self._layout()
        if not body.contains(pos):return None
        depth = self.field.depth()
        for ident in sorted(self._placed, key=lambda i: depth.get(i, 3)):       # the nearest sheet wins where two overlap
            if self.sheet_rect(ident, body).contains(pos):return ident
        return None

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        ident = self._hit(event.position())
        if ident and ident != self.field.selected:
            self.field.select(ident);self._describe();self.update()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        ident = self._hit(event.position())
        if ident:
            self.field.select(ident);self._describe();self.update();self.opened.emit(self.selected())

    def wheelEvent(self, event):
        body = self._layout();room = max(0.0, self._surface - body.height())
        if room <= 0:return super().wheelEvent(event)
        self.scroll = max(0.0, min(room, self.scroll - event.angleDelta().y() / 2.0));self.update()

    # ---- drawing ---------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))
        body = self._layout()
        if self.texture:self._texture(p, body)
        self._head(p)
        if not self.field.objects:
            self._empty(p, body)
        else:
            p.save();p.setClipRect(body)
            depth = self.field.depth()
            self._columns(p, body)
            order = sorted(self._placed, key=lambda i: -depth.get(i, 3))          # far sheets first, the selected one last
            for ident in order:self._ghosts(p, self.sheet_rect(ident, body), depth.get(ident, 3))
            self._labels = []
            self._wires(p, body, depth)
            for ident in order:self._sheet(p, self.field.get(ident), self.sheet_rect(ident, body), depth.get(ident, 3))
            self._wire_words(p)
            p.restore()
            if self._surface > body.height() + 1:self._more(p, body)
        self._foot(p)
        p.end()

    def _texture(self, p, body):
        """A still scan texture and a darker rim: depth without movement."""
        p.save();p.setClipRect(body);p.setPen(Qt.NoPen)
        line = ink('#ffffff', 0.016);step = 3
        y = int(body.top())
        while y < body.bottom():
            p.fillRect(QRectF(body.left(), y, body.width(), 1), line);y += step
        rim = QRadialGradient(body.center(), max(body.width(), body.height()) * 0.72)      # a darker rim: depth that does not move
        rim.setColorAt(0.0, ink('#000000', 0.0));rim.setColorAt(0.6, ink('#000000', 0.0));rim.setColorAt(1.0, ink('#000000', 0.6))
        p.fillRect(body, rim)
        p.restore()

    def _head(self, p):
        s = self.scale();h = self.head_height();x = 28 * s
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, h - 0.5), QPointF(self.width(), h - 0.5))
        p.setFont(self.mono(12, QFont.Medium));p.setPen(QColor(t.AMBER_EDGE))
        label = 'FIELD';fm = QFontMetricsF(p.font());base = h / 2 + fm.ascent() / 2 - 2
        p.drawText(QPointF(x, base), label);x += fm.horizontalAdvance(label) + 14 * s
        p.setFont(self.sans(17));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        words = self.field.title or 'This workspace';parts = self.field.census()
        p.setFont(self.mono(11.5));fm3 = QFontMetricsF(p.font());room = self.width() - x - 28 * s
        waiting = [part for part in parts if 'recheck' in part or 'open question' in part]
        while parts and fm3.horizontalAdvance('  ·  '.join(parts)) + 24 * s + fm2.horizontalAdvance(words) > room:
            parts = waiting if parts != waiting and waiting else []        # the title keeps its room; the counts give way, what waits last
            waiting = []
        census = '  ·  '.join(parts);census_w = fm3.horizontalAdvance(census)
        p.setFont(self.sans(17))
        p.drawText(QPointF(x, h / 2 + fm2.ascent() / 2 - 2), fm2.elidedText(words, Qt.ElideRight, max(60.0, room - (census_w + 24 * s if census else 0))))
        if census:
            p.setFont(self.mono(11.5));p.setPen(QColor(t.QUIET))
            p.drawText(QPointF(self.width() - 28 * s - census_w, base), census)

    def _columns(self, p, body):
        s = self.scale();p.setFont(self.mono(10.5, QFont.Medium));fm = QFontMetricsF(p.font())
        for rank in self.field.ranks():
            ids = self.field.column(rank)
            if not ids or ids[0] not in self._placed:continue
            first = self._placed[ids[0]]
            x = body.left() + first.x;y = body.top() + 22 * s - self.scroll
            p.setPen(ink(t.FAINT, 0.9))
            p.drawText(QPointF(x, y), self.field.rank_title(rank))
            p.setPen(QPen(ink(t.LINE, 0.9), 1))
            start = x + fm.horizontalAdvance(self.field.rank_title(rank)) + 10 * s
            if start < x + first.w:p.drawLine(QPointF(start, y - fm.ascent() / 2 + 1), QPointF(x + first.w, y - fm.ascent() / 2 + 1))

    def _wires(self, p, body, depth):
        s = self.scale()
        for link in self.field.links:
            a = self.sheet_rect(link.source, body);b = self.sheet_rect(link.target, body)
            if a is None or b is None:continue
            near = min(depth.get(link.source, 3), depth.get(link.target, 3))
            touching = self.field.selected in (link.source, link.target)
            strength = 1.0 if touching else (0.5 if near <= 1 else 0.26)
            start = QPointF(a.right(), a.center().y());end = QPointF(b.left(), b.center().y())
            if end.x() < start.x():      # a wire that would run backwards leaves from the left and arrives at the right
                start = QPointF(a.left(), a.center().y());end = QPointF(b.right(), b.center().y())
            reach = max(24.0 * s, abs(end.x() - start.x()) * 0.5) * (1 if end.x() >= start.x() else -1)
            path = QPainterPath(start);path.cubicTo(QPointF(start.x() + reach, start.y()), QPointF(end.x() - reach, end.y()), end)
            colour = t.AMBER_EDGE if link.stale else (t.TEXT if touching else t.TEAL_EDGE)
            pen = QPen(ink(colour, strength * (0.95 if link.stale or touching else 0.8)), 1.6 if touching else 1.0)
            if link.stale:pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([5, 4])
            p.setBrush(Qt.NoBrush);p.setPen(pen);p.drawPath(path)
            p.setPen(Qt.NoPen);p.setBrush(ink(colour, strength))
            for point in (start, end):p.drawEllipse(point, 2.6 * s, 2.6 * s)
            word = 'recheck' if link.stale and not link.label else link.label
            if word and (touching or link.stale) and abs(end.x() - start.x()) > 56 * s:
                # The word sits in the open gap beside the sheet the wire leaves, never under a sheet further along.
                gap = min(abs(end.x() - start.x()), max(34.0 * s, self._gap)) / 2
                want = start.x() + (gap if end.x() >= start.x() else -gap)
                at = min((n / 40.0 for n in range(1, 40)), key=lambda f: abs(path.pointAtPercent(f).x() - want))
                self._labels.append((path.pointAtPercent(at), word, link.stale, max(0.7, strength)))

    def _sheet(self, p, obj, r, depth):
        s = self.scale();keep = DEPTH_INK[min(depth, 3)];selected = depth == 0;focus = self.hasFocus()
        p.setBrush(ink(t.CARD if depth <= 1 else t.PANEL, 1.0))
        edge = t.AMBER_EDGE if selected and focus else (t.LINE_STRONG if depth <= 1 else t.LINE)
        p.setPen(QPen(ink(edge, 1.0 if selected else 0.75 * keep + 0.1), 2 if selected else 1));p.drawRect(r)
        if selected:                         # corner ticks: the selection reads without colour too
            p.setPen(QPen(ink(t.AMBER_EDGE if focus else t.LINE_STRONG, 1.0), 2));k = 9 * s;o = 5 * s
            for cx, cy, dx, dy in ((r.left() - o, r.top() - o, 1, 1), (r.right() + o, r.top() - o, -1, 1),
                                   (r.left() - o, r.bottom() + o, 1, -1), (r.right() + o, r.bottom() + o, -1, -1)):
                p.drawLine(QPointF(cx, cy), QPointF(cx + dx * k, cy));p.drawLine(QPointF(cx, cy), QPointF(cx, cy + dy * k))
        pad = 12 * s;inner = r.adjusted(pad, pad - 2 * s, -pad, -pad + 2 * s)
        # Kind at the left, state at the right.
        p.setFont(self.mono(10.5, QFont.Medium));fm = QFontMetricsF(p.font());y = inner.top() + fm.ascent()
        state = STATE_WORD.get(obj.state, obj.state or '')
        state_colour = t.READY if obj.state == STATE_CURRENT else (t.AMBER_EDGE if obj.state in ATTENTION else t.QUIET)
        mark = 7 * s;state_w = fm.horizontalAdvance(state.upper()) + mark + 6 * s
        tag = fm.elidedText(KIND_TAG.get(obj.kind, obj.kind.upper()), Qt.ElideRight, max(10.0, inner.width() - state_w - 8 * s))
        p.setPen(ink(t.AMBER_TEXT if obj.kind == 'question' else t.QUIET, keep));p.drawText(QPointF(inner.left(), y), tag)
        if state and inner.width() > state_w + fm.horizontalAdvance(tag) + 6 * s:
            sx = inner.right() - state_w;box = QRectF(sx, y - fm.ascent() / 2 - mark / 2 + 1, mark, mark)
            if obj.state == STATE_CURRENT:
                p.setPen(Qt.NoPen);p.setBrush(ink(state_colour, keep));p.drawRect(box)
            else:
                p.setBrush(Qt.NoBrush);p.setPen(QPen(ink(state_colour, max(keep, 0.75)), 1.5));p.drawRect(box)
            p.setPen(ink(state_colour, max(keep, 0.75) if obj.state in ATTENTION else keep))
            p.drawText(QPointF(sx + mark + 6 * s, y), state.upper())
        y += 7 * s
        # Title, up to two lines.
        p.setFont(self.sans(14.5));fm = QFontMetricsF(p.font());p.setPen(ink(t.TEXT, keep))
        lines = self._wrap(obj.title, fm, inner.width(), 2 if r.height() > 96 * s else 1)
        for line in lines:
            y += fm.height();p.drawText(QPointF(inner.left(), y - fm.descent()), line)
        # Facts, while they fit above the identity line.
        p.setFont(self.mono(11));fm = QFontMetricsF(p.font());where_h = fm.height() if obj.where else 0
        y += 4 * s
        for fact in obj.lines:
            if y + fm.height() > inner.bottom() - where_h:break
            y += fm.height();p.setPen(ink(t.QUIET, keep));p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(fact), Qt.ElideRight, inner.width()))
        if obj.where and inner.bottom() - fm.descent() > y + 2:
            p.setFont(self.mono(10));fm = QFontMetricsF(p.font());p.setPen(ink(t.FAINT, keep))
            p.drawText(QPointF(inner.left(), inner.bottom() - fm.descent()), fm.elidedText(obj.where, Qt.ElideMiddle, inner.width()))

    def _wire_words(self, p):
        s = self.scale();p.setFont(self.mono(10));fm = QFontMetricsF(p.font())
        for point, word, stale, strength in self._labels:
            w = fm.horizontalAdvance(word) + 10 * s;box = QRectF(point.x() - w / 2, point.y() - fm.height() / 2 - 1, w, fm.height() + 2)
            p.setPen(Qt.NoPen);p.setBrush(QColor(t.TERMINAL_GROUND));p.drawRect(box)
            p.setPen(ink(t.AMBER_TEXT if stale else t.QUIET, strength));p.drawText(box, Qt.AlignCenter, word)

    def _ghosts(self, p, r, depth):
        """The sheets behind a sheet: two outlines stepping back into the dark. Drawn before the wires so no wire starts under one."""
        s = self.scale();keep = DEPTH_INK[min(depth, 3)];selected = depth == 0
        for step, alpha in ((2, 0.16), (1, 0.3)):
            ghost = r.translated(step * 5 * s, step * 5 * s)
            p.setBrush(ink(t.TERMINAL_GROUND, 1.0));p.setPen(QPen(ink(t.LINE_STRONG if selected else t.LINE, alpha * keep * (1.6 if selected else 1.0)), 1))
            p.drawRect(ghost)

    @staticmethod
    def _wrap(text, fm, width, limit):
        words = str(text).split();lines = [];line = '';used = 0
        for word in words:
            trial = (line + ' ' + word).strip()
            if fm.horizontalAdvance(trial) <= width or not line:line = trial;used += 1
            elif len(lines) + 1 == limit:break
            else:
                lines.append(line);line = word;used += 1
        if line:lines.append(line)
        if used < len(words) and lines:lines[-1] = lines[-1] + ' ' + ' '.join(words[used:])   # the last line carries the rest, cut once
        return [fm.elidedText(l, Qt.ElideRight, width) for l in lines]

    def _more(self, p, body):
        s = self.scale();p.setFont(self.mono(10.5));p.setPen(QColor(t.QUIET))
        below = self._surface - body.height() - self.scroll > 1
        words = ('more below ↓' if below else '') + ('   ↑ more above' if self.scroll > 1 else '')
        p.drawText(QRectF(body.left(), body.bottom() - 20 * s, body.width() - 28 * s, 16 * s), Qt.AlignRight | Qt.AlignVCenter, words.strip())

    def _empty(self, p, body):
        s = self.scale();p.setFont(self.mono(13));p.setPen(QColor(t.QUIET));fm = QFontMetricsF(p.font())
        lines = ('// nothing in the field yet', '', '   bring material in through Ingress, or open a file;',
                 '   what you work on appears here with what it came from.')
        y = body.center().y() - len(lines) * fm.height() / 2;x = max(28 * s, body.center().x() - 240 * s)
        for line in lines:
            y += fm.height();p.drawText(QPointF(x, y), line)

    def _foot(self, p):
        s = self.scale();h = self.foot_height();top = self.height() - h;x = 28 * s
        p.fillRect(QRectF(0, top, self.width(), h), QColor(t.GROUND))
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(QPointF(0, top + 0.5), QPointF(self.width(), top + 0.5))
        obj = self.selected()
        keys = '← ↑ ↓ →  move      Enter  open      Tab  next waiting      Esc  back'
        p.setFont(self.mono(10.5));fm = QFontMetricsF(p.font());keys_w = fm.horizontalAdvance(keys)
        if obj is None:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2), 'Esc  back');return
        wide = self.width() - 2 * x
        p.setFont(self.mono(10.5, QFont.Medium));p.setPen(QColor(t.AMBER_TEXT))
        tag = KIND_TAG.get(obj.kind, obj.kind.upper()) + '  ·  ' + STATE_WORD.get(obj.state, obj.state).upper()
        p.drawText(QPointF(x, top + 22 * s), tag)
        if wide > keys_w + fm.horizontalAdvance(tag) + 40 * s:
            p.setFont(self.mono(10.5));p.setPen(QColor(t.FAINT));p.drawText(QPointF(self.width() - x - keys_w, top + 22 * s), keys)
        p.setFont(self.sans(16));fm2 = QFontMetricsF(p.font());p.setPen(QColor(t.TEXT))
        p.drawText(QPointF(x, top + 22 * s + fm2.height() + 2 * s), fm2.elidedText(obj.title, Qt.ElideRight, wide))
        fed = [self.field.get(l.source).title for l in self.field.fed_by(obj.id)];feeds = [self.field.get(l.target).title for l in self.field.feeds(obj.id)]
        words = obj.role or ''
        if fed:words += ('   ·   ' if words else '') + 'from ' + ', '.join(fed)
        if feeds:words += ('   ·   ' if words else '') + 'feeds ' + ', '.join(feeds)
        if not words:words = obj.where
        p.setFont(self.mono(11));fm3 = QFontMetricsF(p.font());p.setPen(QColor(t.QUIET))
        p.drawText(QPointF(x, top + h - 14 * s), fm3.elidedText(words, Qt.ElideRight, wide))
