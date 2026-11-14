import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_qt.py', [
('''from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget
''', '''from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QKeyEvent, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget
'''),
('''    reading_closed = Signal()          # the reading sheet was closed by the owner (Esc, or a click beside it)
''', '''    reading_closed = Signal()          # the reading sheet was closed by the owner (Esc, or a click beside it)
    menu_asked = Signal()              # a click on "Menu": the selected sheet's own menu
'''),
('''        self.reading = None                 # a page to read, shown over the work: {'title', 'lines': [(style, text)], 'foot', 'code'}
        self._read_at = 0.0;self._read_room = 0.0      # how far it is scrolled, and how far it can be
''', '''        self.reading = None                 # a page to read, shown over the work: {'title', 'lines': [(style, text)], 'foot', 'code'}
        self._read_at = 0.0;self._read_room = 0.0      # how far it is scrolled, and how far it can be
        # The mouse does what the keys do: every key the surface shows is also a place to click. Each painting leaves the
        # places here as (rectangle, key, the text that key types, what it does in words).
        self._hot = []
        self._hover = ''                    # the sheet under the pointer: its wires show, and its whole name
        self._press = None                  # where a press began: (position, the sheet there, the scroll then)
        self._panned = False
        self.setMouseTracking(True)
'''),
('''    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        if self.reading is not None:          # a click beside the page closes it; a click on it is for reading
            if not self._reading_rect(self.body()).contains(event.position()):
                self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
            return
        for box, name in self._face_boxes:
            if box.contains(event.position()):
                self.face_chosen.emit(name);return
        ident = self._hit(event.position())
        if ident and ident != self.field.selected:
            self.field.select(ident);self._describe();self.update()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        ident = self._hit(event.position())
        if ident:
            self.field.select(ident);self._describe();self.update();self.opened.emit(self.selected())
''', '''    KEY_OF = {'Enter': (Qt.Key_Return, ''), 'Esc': (Qt.Key_Escape, ''), '⌫': (Qt.Key_Backspace, ''), '?': (Qt.Key_Question, '?'), 'Menu': (Qt.Key_Menu, '')}

    def _key_of(self, label):
        """The key a shown label stands for ('D', '1', 'Esc', '?'): (key, the text it types), or None for a label that names no one key."""
        label = str(label).strip()
        if label in self.KEY_OF:return self.KEY_OF[label]
        if len(label) == 1 and label.isdigit() and label != '0':return Qt.Key_0 + int(label), label
        if len(label) == 1 and label.isascii() and label.isalpha():return getattr(Qt, 'Key_' + label.upper()), label.lower()
        return None

    def press_key(self, key, text=''):
        """Do what a key does, for a click: the same event the keyboard sends, so the mouse can never do something else."""
        if key == Qt.Key_Menu:
            self.menu_asked.emit();return
        self.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, text))

    def _hot_at(self, pos):
        return next(((box, key, text, words) for box, key, text, words in reversed(self._hot) if box.contains(pos)), None)

    def _keys_line(self, p, x, base, items, colour, room, target=''):
        """Draw 'KEY  what it does' items along one line, each a place to click that does what its key does. An item whose key
        is G is the owner's go, so it is drawn as an Approve button and says what it would apply, and to what. Items that do
        not fit are left out from the end. Returns the x after the last one drawn."""
        s = self.scale();fm = QFontMetricsF(p.font());gap = fm.horizontalAdvance('      ');end = x + room
        for item in items:
            label, _, words = str(item).partition('  ');words = words.strip();found = self._key_of(label)
            if label.strip() == 'G':
                wide = fm.horizontalAdvance('Approve') + 16 * s;said = fm.elidedText(words, Qt.ElideRight, max(40.0, end - x - wide - 8 * s))
                total = wide + 8 * s + fm.horizontalAdvance(said)
                if x + wide > end:break
                box = QRectF(x, base - fm.ascent() - 3 * s, wide, fm.height() + 6 * s)
                p.save();p.setPen(Qt.NoPen);p.setBrush(QColor(t.AMBER_EDGE));p.drawRect(box)
                p.setPen(QColor(t.GROUND));p.drawText(box, Qt.AlignCenter, 'Approve');p.restore()
                p.setPen(QColor(colour));p.drawText(QPointF(x + wide + 8 * s, base), said)
                self._hot.append((QRectF(x, box.top(), total, box.height()), Qt.Key_G, 'g',
                                  'Approve: %s%s. Nothing is changed until you do (G does the same)' % (words, (' · for “%s”' % str(target)[:80]) if target else '')))
            else:
                total = fm.horizontalAdvance(str(item))
                if x + total > end:break
                p.setPen(QColor(colour));p.drawText(QPointF(x, base), str(item))
                if found is not None:
                    self._hot.append((QRectF(x - 4 * s, base - fm.ascent() - 4 * s, total + 8 * s, fm.height() + 8 * s), found[0], found[1], words[:1].upper() + words[1:] + ' (%s)' % label.strip()))
            x += total + gap
        return x

    def mousePressEvent(self, event):
        """A click on something the surface shows as a key does what that key does. A click on a sheet opens it (on release,
        so that a drag can move the surface instead); the right button selects the sheet for its menu and opens nothing."""
        self.setFocus(Qt.MouseFocusReason);pos = event.position()
        if event.button() == Qt.LeftButton:
            hot = self._hot_at(pos)
            if hot is not None:
                self.press_key(hot[1], hot[2]);return
        if self.reading is not None:          # a click beside the page closes it; a click on it is for reading
            if not self._reading_rect(self.body()).contains(pos):
                self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
            return
        for box, name in self._face_boxes:
            if box.contains(pos):
                self.face_chosen.emit(name);return
        ident = self._hit(pos)
        if event.button() == Qt.LeftButton:
            self._press = (QPointF(pos), ident, (self.scroll_x, self.scroll_y));self._panned = False
            return
        if ident and ident != self.field.selected:
            self.field.select(ident);self._describe();self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._press is not None and event.buttons() & Qt.LeftButton:      # a drag moves the surface
            start, _, (x, y) = self._press;delta = pos - start
            if self._panned or abs(delta.x()) + abs(delta.y()) > 6:
                self._panned = True;body = self._layout()
                self.scroll_x = max(0.0, min(max(0.0, self._surface[0] - body.width()), x - delta.x()))
                self.scroll_y = max(0.0, min(max(0.0, self._surface[1] - body.height()), y - delta.y()))
                self.setCursor(Qt.ClosedHandCursor);self.update()
            return
        hot = self._hot_at(pos);ident = '' if hot or self.reading is not None else (self._hit(pos) or '')
        self.setCursor(Qt.PointingHandCursor if hot or ident else Qt.ArrowCursor)
        if ident != self._hover:
            self._hover = ident;self.update()
        obj = self.field.get(ident) if ident else None
        tip = hot[3] if hot else ('%s%s\\nClick opens it · right-click for what can be done' % (obj.title, (' · ' + STATE_WORD.get(obj.state, obj.state)) if obj.state else '')) if obj is not None else ''
        if tip:QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:QToolTip.hideText()

    def mouseReleaseEvent(self, event):
        press, self._press = self._press, None
        if press is None or event.button() != Qt.LeftButton:return super().mouseReleaseEvent(event)
        if self._panned:
            self._panned = False;self.setCursor(Qt.ArrowCursor);return
        ident = press[1]
        if ident and self._hit(event.position()) == ident:      # a click on a sheet: it is the selected one, and it opens
            if ident != self.field.selected:
                self.field.select(ident);self._describe()
            self.update();self.opened.emit(self.selected())

    def leaveEvent(self, event):
        if self._hover:
            self._hover = '';self.update()
        super().leaveEvent(event)
'''),
('''            touching = self.field.selected in (link.source, link.target)
''', '''            touching = self.field.selected in (link.source, link.target) or (bool(self._hover) and self._hover in (link.source, link.target))
'''),
('''            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            import time
            self._now = time.time()
''', '''            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            import time
            self._now = time.time();self._hot = []
'''),
# ---- the foot: every key shown is a place to click ------------------------------------------------------------------------
('''            p.setPen(QColor(t.QUIET));p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2), 'R  look again      ?  keys      Esc  back');return
''', '''            self._keys_line(p, x, top + h / 2 + fm.ascent() / 2, ['R  look again', '?  keys', 'Esc  back'], t.QUIET, self.width() - 2 * x);return
'''),
('''            p.drawText(QPointF(left, top + h / 2 + fm2.ascent() / 2 - 1), fm2.elidedText(str(obj.title)[:LONGEST], Qt.ElideRight, max(40.0, self.width() - x - left)))
            return
''', '''            p.drawText(QPointF(left, top + h / 2 + fm2.ascent() / 2 - 1), fm2.elidedText(str(obj.title)[:LONGEST], Qt.ElideRight, max(40.0, self.width() - x - left)))
            p.setFont(self.mono(12))
            if self.go:                      # even on one line, what waits can be approved with a click
                p.fillRect(QRectF(self.width() * 0.5, top + 2, self.width() * 0.5, h - 4), QColor(t.GROUND))
                self._keys_line(p, self.width() * 0.5 + 8 * s, top + h / 2 + fm.ascent() / 2 - 1, ['G  ' + self.go], t.AMBER_TEXT, self.width() * 0.5 - x - 8 * s, obj.title)
            return
'''),
('''        if legend:
            keys = '      '.join(word for _, word in legend);keys_w = fm.horizontalAdvance(keys)
            p.setFont(self.mono(12));p.setPen(QColor(t.QUIET));p.drawText(QPointF(self.width() - x - keys_w, top + 24 * s), keys)
''', '''        if legend:
            keys = '      '.join(word for _, word in legend);keys_w = fm.horizontalAdvance(keys)
            p.setFont(self.mono(12));self._keys_line(p, self.width() - x - keys_w, top + 24 * s, [word for _, word in legend], t.QUIET, keys_w + 2)
'''),
('''        if self.steps or self.go:            # the owner asked what can be done: the foot says the steps and the go, wherever the rail is
            said = 'DO      ' + '      '.join(['%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9])]
                                              + (['G  ' + self.go] if self.go else []))
            code = '';p.setPen(QColor(t.AMBER_TEXT))
''', '''        if self.steps or self.go:            # the owner asked what can be done: the foot says the steps and the go, wherever the rail is
            # The go comes first, as a button: it is never the item that does not fit. Each step is a place to click, as a digit is a key.
            items = (['G  ' + self.go] if self.go else []) + ['%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9])]
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(x, top + h - 14 * s), 'DO')
            self._keys_line(p, x + fm3.horizontalAdvance('DO      '), top + h - 14 * s, items, t.AMBER_TEXT, wide - fm3.horizontalAdvance('DO      '), obj.title)
            return
'''),
# ---- the steps box in the rail: a step is a place to click, and so is the go --------------------------------------------------
('''                rows.append((line if at == 0 else '   ' + line, write and at == 0))
''', '''                rows.append((line if at == 0 else '   ' + line, write and at == 0, n))
'''),
('''        for line, write in rows:
            y += fm.height();p.setPen(QColor(t.TEXT));p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w - (asks_w if write else 0)))
            if write:
''', '''        for line, write, n in rows:
            y += fm.height();p.setPen(QColor(t.TEXT));p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line, Qt.ElideRight, inner_w - (asks_w if write else 0)))
            self._hot.append((QRectF(x - 4 * s, y - fm.height(), inner_w + 8 * s, fm.height()), Qt.Key_1 + n, str(n + 1),
                              'Take this step: %s' % ('it is put up for you to approve; nothing is changed yet' if self.steps[n][1] == 'write' else 'a read, it runs at once')))
            if write:
'''),
('''            for at, line in enumerate(going):
                y += fm.height();p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line if at == 0 else '   ' + line, Qt.ElideRight, inner_w))
''', '''            for at, line in enumerate(going):
                y += fm.height();p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line if at == 0 else '   ' + line, Qt.ElideRight, inner_w))
                self._hot.append((QRectF(x - 4 * s, y - fm.height(), inner_w + 8 * s, fm.height()), Qt.Key_G, 'g', 'Approve: %s. Nothing is changed until you do' % self.go))
'''),
# ---- the reading page: a visible Close, and its foot's keys are places to click -------------------------------------------------
('''        s = self.scale();r = self._reading_rect(body);tight = self._tight(body);pad = (14 if tight else 26) * s;read = self.reading
''', '''        s = self.scale();r = self._reading_rect(body);tight = self._tight(body);pad = (14 if tight else 26) * s;read = self.reading
        self._hot = []                        # while a page is read, only its own controls are places to click
'''),
('''        p.setFont(title_font);p.setPen(QColor(t.TEXT))
        heading = self._flow(read['title'], fm_title, r.width() - 2 * pad)       # a long name takes a second line before it is cut
        if len(heading) > 2:heading = [heading[0], fm_title.elidedText(' '.join(heading[1:]), Qt.ElideRight, r.width() - 2 * pad)]
''', '''        close_font = self.mono(12);fm_close = QFontMetricsF(close_font);close = '✕  Close';close_w = fm_close.horizontalAdvance(close)
        p.setFont(close_font);p.setPen(QColor(t.QUIET));p.drawText(QPointF(r.right() - pad - close_w, y), close)
        self._hot.append((QRectF(r.right() - pad - close_w - 8 * s, y - fm_close.ascent() - 6 * s, close_w + 16 * s, fm_close.height() + 12 * s), Qt.Key_Escape, '', 'Close this page (Esc)'))
        p.setFont(title_font);p.setPen(QColor(t.TEXT))
        heading = self._flow(read['title'], fm_title, r.width() - 2 * pad - close_w - 16 * s)       # a long name takes a second line before it is cut
        if len(heading) > 2:heading = [heading[0], fm_title.elidedText(' '.join(heading[1:]), Qt.ElideRight, r.width() - 2 * pad - close_w - 16 * s)]
'''),
('''        p.setPen(QColor(t.QUIET));p.drawText(QPointF(r.left() + pad, base), fm_foot.elidedText(read['foot'], Qt.ElideRight, r.width() - 2 * pad - fm_foot.horizontalAdvance(more) - 16 * s))
''', '''        self._keys_line(p, r.left() + pad, base, [item for item in read['foot'].split('      ') if item.strip()], t.QUIET, r.width() - 2 * pad - fm_foot.horizontalAdvance(more) - 16 * s)
''')])
print('ok')
