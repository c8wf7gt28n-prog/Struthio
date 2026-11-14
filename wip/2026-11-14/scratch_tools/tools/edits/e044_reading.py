import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_qt.py', [
('''LONGEST = 240                               # a title is cut to this many characters before it is measured: paint time must not follow its length
''', '''LONGEST = 240                               # a title is cut to this many characters before it is measured: paint time must not follow its length

# Every key of the Field, for the card that ? shows. ('h', heading) or ('k', 'the keys<TAB>what they do').
KEYS = (('h', 'Move'),
        ('k', '← ↑ ↓ →\\tfollow the wires from sheet to sheet'),
        ('k', 'Home  End\\tthe first sheet, the last sheet'),
        ('k', 'PgUp  PgDn\\tscroll the surface'),
        ('k', 'A\\tthe next thing that waits for you (Shift+A the one before)'),
        ('k', 'Backspace\\tback to the sheet you were on before'),
        ('k', 'W  P  N\\tthe faces: the work, every program as a shelf, this computer’s network'),
        ('h', 'Open'),
        ('k', 'Enter\\topen the real page for this sheet; Esc there comes back here'),
        ('k', 'R\\tread the records again'),
        ('k', 'Esc\\tclose what is open here (this card, the steps, a what-if’s marks), then leave the Field'),
        ('h', 'Ask · these only read, nothing is changed'),
        ('k', 'X\\tdoubt it: what does not hold, what cannot be told, what holds'),
        ('k', 'T\\ttrace it: where it comes from and what rests on it'),
        ('k', 'C\\tcheck the whole desk: what waits, and what Stacy doubts'),
        ('k', 'B\\tthe brief: the desk written up as one page, from the records'),
        ('k', 'S\\tthis sheet’s staC line, into the writing strip'),
        ('k', 'Shift+Enter\\trun that line; the answer opens in the working area'),
        ('k', 'what if …\\tin the writing strip, with a sheet selected: “what if B4 were 100?” marks everything that would move'),
        ('h', 'Do'),
        ('k', 'D\\twhat can be done about this sheet, as numbered steps'),
        ('k', '1 – 9\\tchoose a step. A read runs at once; a change is put up in Talk and waits'),
        ('k', 'G\\tyour go for the change that waits. Only G approves; a digit never does'),
        ('k', 'F\\ton the shelf: this program in its own full window'),
        ('h', 'Also'),
        ('k', 'Menu  or right-click\\tthe same things as a cascading menu, on the sheet under the pointer'),
        ('k', 'F9\\tthe Field, from anywhere in Graphite'),
        ('k', 'this\\tin the writing strip: the selected sheet (this | count, then Ctrl+Enter)'),
        ('k', 'word NAME = LINE\\tin the writing strip: keep a staC line under a word of your own'))
'''),
('''    brief_asked = Signal()             # B: the desk written up as one page, from the records
''', '''    brief_asked = Signal()             # B: the desk written up as one page, from the records
    reading_closed = Signal()          # the reading sheet was closed by the owner (Esc, or a click beside it)
'''),
('''        self._trail = [];self._last = ''    # the sheets the owner was on before this one, for Backspace
''', '''        self._trail = [];self._last = ''    # the sheets the owner was on before this one, for Backspace
        self.reading = None                 # a page to read, shown over the work: {'title', 'lines': [(style, text)], 'foot', 'code'}
        self._read_at = 0.0;self._read_room = 0.0      # how far it is scrolled, and how far it can be
'''),
('''        self.would = {};self.would_said = ''      # a what-if is about the records as they were read: a new reading ends it
''', '''        self.would = {};self.would_said = ''      # a what-if is about the records as they were read: a new reading ends it
        self.reading = None                       # and so is a page shown over them
'''),
('''    # ---- input -----------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key();before = self.field.selected;plain = not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
''', '''    # ---- a page to read, over the work -----------------------------------------------------------------------------
    def show_reading(self, title, lines, foot='', code=''):
        """Show writing over the work, to be read: a title, lines of ('h' heading | 'p' paragraph | 'q' quiet | 'b' bullet |
        'k' a key and its words, tab between), a foot that says the keys, and the staC line that reads it. The arrow keys
        scroll it; Esc closes it. The sheets stay as they were underneath."""
        self.reading = {'title': str(title), 'lines': tuple(lines), 'foot': str(foot), 'code': str(code)}
        self._read_at = 0.0
        self.setAccessibleDescription(str(title) + '. ' + ' '.join(str(text).replace('\\t', ': ') for _, text in lines)[:4000])
        self.update()

    def close_reading(self):
        if self.reading is not None:
            self.reading = None;self._describe_quietly();self.update()

    def _describe_quietly(self):
        steps, go = self.steps, self.go;self._describe();self.steps, self.go = steps, go      # the description follows the sheet again; what waits is not withdrawn

    def show_keys(self):
        self.show_reading('The keys of the Field', KEYS, 'Esc  close      ↑ ↓  read on      ?  close')

    def _reading_key(self, event):
        """The keys while a page is being read: reading keys only, so a letter meant for the page cannot act on a sheet."""
        key = event.key();step = 3 * QFontMetricsF(self.sans(15)).height()
        if key == Qt.Key_Escape or event.text() == '?':
            self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
        elif key == Qt.Key_G and self.go:self.go_asked.emit()
        elif key in (Qt.Key_Down, Qt.Key_Up):self._read_at += step if key == Qt.Key_Down else -step
        elif key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space):self._read_at += self.body().height() * 0.8 * (-1 if key == Qt.Key_PageUp else 1)
        elif key == Qt.Key_Home:self._read_at = 0.0
        elif key == Qt.Key_End:self._read_at = self._read_room
        self._read_at = max(0.0, min(self._read_room, self._read_at));self.update()

    # ---- input -----------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key();before = self.field.selected;plain = not (event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
        if self.reading is not None and plain:
            return self._reading_key(event)
        if plain and event.text() == '?':     # ?: every key of the Field, on a card
            self.show_keys();return
'''),
('''    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
''', '''    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        if self.reading is not None:          # a click beside the page closes it; a click on it is for reading
            if not self._reading_rect(self.body()).contains(event.position()):
                self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
            return
'''),
('''    def wheelEvent(self, event):
        body = self._layout();room_x = max(0.0, self._surface[0] - body.width());room_y = max(0.0, self._surface[1] - body.height())
''', '''    def wheelEvent(self, event):
        if self.reading is not None:
            self._read_at = max(0.0, min(self._read_room, self._read_at - event.angleDelta().y() / 2.0));self.update();return
        body = self._layout();room_x = max(0.0, self._surface[0] - body.width());room_y = max(0.0, self._surface[1] - body.height())
'''),
('''                p.restore()
                self._more(p, body)
            self._foot(p)
''', '''                p.restore()
                self._more(p, body)
            if self.reading is not None:self._reading(p, body)
            self._foot(p)
'''),
('''    def _art(self, p, body):
        """The desk's artwork in its own place.''', '''    def _reading_rect(self, body):
        s = self.scale();wide = min(body.width() - 2 * 20 * s, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + 14 * s, wide, body.height() - 28 * s)

    @staticmethod
    def _flow(text, fm, width):
        """Whole words on as many lines as they need; a word wider than the line is cut where it stops fitting."""
        out = [];line = ''
        for word in str(text).split():
            while fm.horizontalAdvance(word) > width and len(word) > 2:
                low, high = 1, len(word) - 1
                while low < high:
                    mid = (low + high + 1) // 2
                    if fm.horizontalAdvance(word[:mid]) <= width:low = mid
                    else:high = mid - 1
                if line:out.append(line);line = ''
                out.append(word[:low]);word = word[low:]
            trial = (line + ' ' + word).strip()
            if not line or fm.horizontalAdvance(trial) <= width:line = trial
            else:
                out.append(line);line = word
        if line:out.append(line)
        return out or ['']

    def _reading(self, p, body):
        """A page to read, over the work: the brief, the keys. Opaque ground, an amber edge, type at the owner's reading size;
        what does not fit scrolls, and the foot says the keys that act here."""
        s = self.scale();r = self._reading_rect(body);pad = 26 * s;read = self.reading
        p.save();p.setClipRect(body)
        p.fillRect(body, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
        p.setPen(QPen(ink(t.AMBER_EDGE, 0.9), 1.4));p.setBrush(QColor(t.GROUND));p.drawRect(r)
        title_font = self.sans(19);fm_title = QFontMetricsF(title_font);y = r.top() + pad + fm_title.ascent()
        p.setFont(title_font);p.setPen(QColor(t.TEXT));p.drawText(QPointF(r.left() + pad, y), fm_title.elidedText(read['title'], Qt.ElideRight, r.width() - 2 * pad))
        top = y + fm_title.descent() + 12 * s
        p.setPen(QPen(QColor(t.LINE_STRONG), 1));p.drawLine(QPointF(r.left() + pad, top), QPointF(r.right() - pad, top))
        fm_foot = QFontMetricsF(self.mono(12));foot_h = (fm_foot.height() + 10 * s) * (2 if read['code'] else 1) + 8 * s
        inner = QRectF(r.left() + pad, top + 10 * s, r.width() - 2 * pad, r.bottom() - foot_h - pad / 2 - top - 10 * s)
        text_font = self.sans(15);fm_text = QFontMetricsF(text_font);head_font = self.mono(12.5, QFont.Medium);fm_head = QFontMetricsF(head_font)
        quiet_font = self.sans(14);fm_quiet = QFontMetricsF(quiet_font);key_font = self.mono(13, QFont.Medium);fm_key = QFontMetricsF(key_font)
        key_w = min(inner.width() * 0.32, max([fm_key.horizontalAdvance(text.split('\\t', 1)[0]) for style, text in read['lines'] if style == 'k'] or [0.0]) + 22 * s)
        rows = [];at = 0.0                     # (y from the top of the writing, x, font, colour, text)
        for style, text in read['lines']:
            if style == 'h':
                at += (16 * s if rows else 2 * s)
                rows.append((at + fm_head.ascent(), 0.0, head_font, t.AMBER_TEXT, str(text).upper()));at += fm_head.height() + 6 * s
            elif style == 'k':
                keys, _, words = str(text).partition('\\t');lines = self._flow(words, fm_text, inner.width() - key_w)
                rows.append((at + fm_text.ascent(), 0.0, key_font, t.AMBER_TEXT, keys))
                for line in lines:
                    rows.append((at + fm_text.ascent(), key_w, text_font, t.TEXT, line));at += fm_text.height()
                at += 5 * s
            else:
                font, fm, colour = (quiet_font, fm_quiet, t.QUIET) if style == 'q' else (text_font, fm_text, t.TEXT)
                hang = fm.horizontalAdvance('·  ') if style == 'b' else 0.0
                for index, line in enumerate(self._flow(text, fm, inner.width() - hang)):
                    if style == 'b' and index == 0:rows.append((at + fm.ascent(), 0.0, font, t.AMBER_EDGE, '·'))
                    rows.append((at + fm.ascent(), hang, font, colour, line));at += fm.height()
                at += 7 * s
        self._read_room = max(0.0, at - inner.height());self._read_at = max(0.0, min(self._read_room, self._read_at))
        p.setClipRect(inner.adjusted(0, -2, 0, 2))
        for y_at, x, font, colour, text in rows:
            y_seen = inner.top() + y_at - self._read_at
            if y_seen < inner.top() - 30 * s or y_seen > inner.bottom() + 30 * s:continue
            p.setFont(font);p.setPen(QColor(colour));p.drawText(QPointF(inner.left() + x, y_seen), text)
        p.setClipRect(body)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
        more = ('↑ more   ' if self._read_at > 1 else '') + ('more ↓' if self._read_room - self._read_at > 1 else '')
        if more:
            p.setPen(QColor(t.AMBER_TEXT));p.drawText(QPointF(r.right() - pad - fm_foot.horizontalAdvance(more), base), more)
        p.setPen(QColor(t.QUIET));p.drawText(QPointF(r.left() + pad, base), fm_foot.elidedText(read['foot'], Qt.ElideRight, r.width() - 2 * pad - fm_foot.horizontalAdvance(more) - 16 * s))
        if read['code']:
            p.setPen(QColor(t.FAINT));p.drawText(QPointF(r.left() + pad, base - fm_foot.height() - 6 * s), fm_foot.elidedText('staC  ' + read['code'], Qt.ElideRight, r.width() - 2 * pad))
        p.restore()

    def _art(self, p, body):
        """The desk's artwork in its own place.'''),
# the legend: ? is the way to every other key, so it is among the last to give way
('''        legend = [(3, '← ↑ ↓ →  move'), (1, 'Enter  open'), (2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (6.5, 'B  brief'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'),
                  (10, 'R  look again'), (12, '⌫  where I was'), (0, 'Esc  back')]
''', '''        legend = [(3, '← ↑ ↓ →  move'), (1, 'Enter  open'), (2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (6.5, 'B  brief'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'),
                  (10, 'R  look again'), (12, '⌫  where I was'), (0.5, '?  keys'), (0, 'Esc  back')]
'''),
('''            p.setPen(QColor(t.QUIET));p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2), 'R  look again      Esc  back');return
''', '''            p.setPen(QColor(t.QUIET));p.drawText(QPointF(x, top + h / 2 + fm.ascent() / 2), 'R  look again      ?  keys      Esc  back');return
'''),
('''            p.setPen(QColor(t.QUIET));lines = ('// nothing in the field yet', '', '   bring material in through Ingress, or open a file;',
                                               '   what you work on appears here with what it came from.')
''', '''            p.setPen(QColor(t.QUIET));lines = ('// nothing in the field yet', '', '   bring material in through Ingress, or open a file;',
                                               '   what you work on appears here with what it came from.', '', '   ?  shows every key of the Field.')
'''),
# the strip under the sheets: what it says on the left and where the surface goes on, on the right, never over each other
('''        if said:
            p.setPen(QColor(t.QUIET))
            p.drawText(QRectF(body.left(), body.bottom() - 22 * s, body.width() - 28 * s, 18 * s), Qt.AlignRight | Qt.AlignVCenter, '   '.join(said))
        if note:
            p.setPen(QColor(t.AMBER_TEXT))
            p.drawText(QRectF(body.left() + 28 * s, body.bottom() - 22 * s, body.width() * 0.62, 18 * s), Qt.AlignLeft | Qt.AlignVCenter, note)
''', '''        fm = QFontMetricsF(p.font());room = body.width() - 56 * s
        if note:                           # what is being said comes first; where the surface goes on takes what is left, the sideways words giving way first
            note = fm.elidedText(note, Qt.ElideRight, room if not said else max(room * 0.5, room - fm.horizontalAdvance('   '.join(said)) - 28 * s))
            left = room - fm.horizontalAdvance(note) - 28 * s
            while said and fm.horizontalAdvance('   '.join(said)) > left:said.pop()
            p.setPen(QColor(t.AMBER_TEXT))
            p.drawText(QRectF(body.left() + 28 * s, body.bottom() - 22 * s, room, 18 * s), Qt.AlignLeft | Qt.AlignVCenter, note)
        if said:
            p.setPen(QColor(t.QUIET))
            p.drawText(QRectF(body.left(), body.bottom() - 22 * s, body.width() - 28 * s, 18 * s), Qt.AlignRight | Qt.AlignVCenter, '   '.join(said))
'''),
('''        if self.would.get(obj.id):           # a what-if marks this sheet: the foot says it whole
            said = 'WHAT IF      ' + self.would_said.replace('what if ', '', 1) + '      ' + self.would[obj.id];p.setPen(QColor(t.AMBER_TEXT))
''', '''        marked = bool(self.would.get(obj.id))
        if marked:                           # a what-if marks this sheet: the foot says it whole, and has the line to itself
            said = 'WHAT IF      ' + self.would_said.replace('what if ', '', 1) + '      ' + self.would[obj.id];p.setPen(QColor(t.AMBER_TEXT))
'''),
('''        code = '' if self.rail() or not obj.stac else 'staC  ' + '  '.join(self.stac_lines(obj.stac))      # no rail: the line is said here
''', '''        code = '' if self.rail() or not obj.stac or marked else 'staC  ' + '  '.join(self.stac_lines(obj.stac))      # no rail: the line is said here
''')])
print('ok')
