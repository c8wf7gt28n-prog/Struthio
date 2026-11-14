import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

edit(W + 'shell2.py', [
('''        code.setStyleSheet('color:%s' % TEAL_TEXT);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse);code.setAccessibleName('staC: ' + line);card.box.addWidget(code)
        r = engineering(self.host.root).dispatch(operation, arguments, operator())
''', '''        code.setStyleSheet('color:%s' % TEAL_TEXT);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse);code.setAccessibleName('staC: ' + line)
        answer_first = bool(thing.get('whole'))       # when the rows are the whole answer (a doubt, a what-if, a brief), they are read first and the line that read them comes after
        if not answer_first:card.box.addWidget(code)
        r = engineering(self.host.root).dispatch(operation, arguments, operator())
'''),
('''        answer = QLabel(breakable(shown));answer.setTextFormat(Qt.PlainText);answer.setWordWrap(True)
        answer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);answer.setTextInteractionFlags(Qt.TextSelectableByMouse);card.box.addWidget(answer)
''', '''        answer = QLabel(breakable(shown));answer.setTextFormat(Qt.PlainText);answer.setWordWrap(True)
        answer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);answer.setTextInteractionFlags(Qt.TextSelectableByMouse);card.box.addWidget(answer)
        if answer_first:
            code.setFont(mono_font(13));card.box.addWidget(code)
'''),
('''            out.append(line + ('\\n   by ' + say(row['by']) if row.get('by') else ''))
''', '''            out.append(line + (' · ' + say(row['by']) if row.get('by') else ''))
'''),
("""                'intro': 'What if %s, on “%s”. Nothing is changed; the Field marks what would move (Esc clears):' % (said, chosen.title)}
""", """                'intro': 'What if %s on “%s”. Nothing is changed:' % (said, chosen.title if len(chosen.title) <= 44 else chosen.title[:43].rstrip() + '…')}
""")])

edit(W + 'field_page.py', [
('''    line = 'field.doubt %s | pick rows | select verdict,about,why' % js(id=obj.id)
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True, 'whole': True,
                        'intro': 'I doubted “%s”. What does not hold comes first, then what I cannot tell, then what holds:' % obj.title}
    shell.ask('What could be wrong with “%s”?' % obj.title)
    if getattr(host, '_field_active', False):host.field_page.view.setFocus(Qt.OtherFocusReason)
''', '''    line = 'field.doubt %s | pick rows | select verdict,about,why' % js(id=obj.id)
    name = obj.title if len(obj.title) <= 44 else obj.title[:43].rstrip() + '…'
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True, 'whole': True, 'intro': 'Doubting “%s”, worst first:' % name}
    shell.ask('What could be wrong with “%s”?' % obj.title)
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):
        show_doubt(host, obj, line);page.view.setFocus(Qt.OtherFocusReason)


def show_doubt(host, obj, line):
    """The doubt, where the eyes are: over the work, at reading size, grouped by what was found. It is a light page: it
    steps aside at the next key that is not a reading key (an arrow moves on, D offers what can be done), and Esc closes
    it. Talk keeps the same answer as a card."""
    from .engineering_kernel import operator
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:return
    answer = kernel.dispatch('field.doubt', {'id': obj.id}, operator())
    if not answer.get('ok'):return
    rows = answer['result'].get('rows', ());sheet = []
    for verdict, heading in (('doubt', 'Does not hold'), ('cannot tell', 'Cannot tell'), ('note', 'Worth knowing'), ('holds', 'Holds')):
        found = [row for row in rows if row.get('verdict') == verdict]
        if found:
            sheet.append(('h', heading))
            sheet.extend(('b', '%s — %s' % (row['about'][:1].upper() + row['about'][1:], row['why'])) for row in found)
    worst = sum(1 for row in rows if row.get('verdict') == 'doubt')
    name = obj.title if len(obj.title) <= 60 else obj.title[:59].rstrip() + '…'
    page.view.show_reading('Doubting “%s”' % name, sheet or [('q', 'There is nothing I know how to doubt about this yet.')],
                           ('D  what can be done about it      ' if worst else '') + 'Esc  close      any other key moves on', line, light=True)
''')])

edit(W + 'field_qt.py', [
('''        ('k', 'Menu  or right-click\\tthe same things as a cascading menu, on the sheet under the pointer'),
        ('k', 'F9\\tthe Field, from anywhere in Graphite'),
        ('k', 'this\\tin the writing strip: the selected sheet (this | count, then Ctrl+Enter)'),
        ('k', 'word NAME = LINE\\tin the writing strip: keep a staC line under a word of your own'))
''', '''        ('k', 'Menu key\\tor right-click: the same things as a cascading menu, on the sheet under the pointer'),
        ('k', 'F9\\tthe Field, from anywhere in Graphite'),
        ('k', 'this\\tin the writing strip: the selected sheet (this | count, then Ctrl+Enter)'),
        ('k', 'word\\tin the writing strip: word NAME = LINE keeps a staC line under a word of your own'))
'''),
('''    def show_reading(self, title, lines, foot='', code=''):
        """Show writing over the work, to be read: a title, lines of ('h' heading | 'p' paragraph | 'q' quiet | 'b' bullet |
        'k' a key and its words, tab between), a foot that says the keys, and the staC line that reads it. The arrow keys
        scroll it; Esc closes it. The sheets stay as they were underneath."""
        self.reading = {'title': str(title), 'lines': tuple(lines), 'foot': str(foot), 'code': str(code)}
''', '''    def show_reading(self, title, lines, foot='', code='', light=False):
        """Show writing over the work, to be read: a title, lines of ('h' heading | 'p' paragraph | 'q' quiet | 'b' bullet |
        'k' a key and its words, tab between), a foot that says the keys, and the staC line that reads it. The arrow keys
        scroll it; Esc closes it. The sheets stay as they were underneath. A light page (an answer about one sheet) also
        steps aside at any key that is not a reading key, and that key then does what it always does."""
        self.reading = {'title': str(title), 'lines': tuple(lines), 'foot': str(foot), 'code': str(code), 'light': bool(light)}
'''),
('''    def _reading_key(self, event):
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
''', '''    def _reading_key(self, event):
        """The keys while a page is being read. A page (the brief, the keys) takes reading keys only, so a letter meant for
        it cannot act on a sheet. A light page scrolls when it has more to show, and otherwise steps aside: False is
        returned and the key does what it always does."""
        key = event.key();step = 3 * QFontMetricsF(self.sans(15)).height();light = self.reading.get('light');more = self._read_room > 1
        if key == Qt.Key_Escape or (event.text() == '?' and not light):
            self.steps = ();self.go = '';self.close_reading();self.reading_closed.emit()
        elif key == Qt.Key_G and self.go:self.go_asked.emit()
        elif key in (Qt.Key_Down, Qt.Key_Up) and (more or not light):self._read_at += step if key == Qt.Key_Down else -step
        elif key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space) and (more or not light):self._read_at += self.body().height() * 0.8 * (-1 if key == Qt.Key_PageUp else 1)
        elif key == Qt.Key_Home and (more or not light):self._read_at = 0.0
        elif key == Qt.Key_End and (more or not light):self._read_at = self._read_room
        elif light:
            self.close_reading();return False
        self._read_at = max(0.0, min(self._read_room, self._read_at));self.update()
        return True
'''),
('''        if self.reading is not None and plain:
            return self._reading_key(event)
''', '''        if self.reading is not None and plain and self._reading_key(event):
            return
'''),
# the page takes the foot's room too: its own foot says the keys that act while it is read
('''    def _reading_rect(self, body):
        s = self.scale();wide = min(body.width() - 2 * 20 * s, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + 14 * s, wide, body.height() - 28 * s)
''', '''    def _reading_rect(self, body):
        s = self.scale();wide = min(body.width() - 2 * 20 * s, 940 * s)
        return QRectF(body.left() + (body.width() - wide) / 2, body.top() + 14 * s, wide, self.height() - body.top() - 28 * s)
'''),
('''            if self.reading is not None:self._reading(p, body)
            self._foot(p)
''', '''            self._foot(p)
            if self.reading is not None:self._reading(p, body)
'''),
('''        s = self.scale();r = self._reading_rect(body);pad = 26 * s;read = self.reading
        p.save();p.setClipRect(body)
        p.fillRect(body, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
''', '''        s = self.scale();r = self._reading_rect(body);pad = 26 * s;read = self.reading
        whole = QRectF(body.left(), body.top(), body.width(), self.height() - body.top())      # the work and its foot: the page's own foot says the keys now
        p.save();p.setClipRect(whole)
        p.fillRect(whole, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
'''),
('''        p.setClipRect(inner.adjusted(0, -2, 0, 2))
        for y_at, x, font, colour, text in rows:''', '''        p.setClipRect(inner.adjusted(0, -2, 0, 2))
        for y_at, x, font, colour, text in rows:'''),
('''        p.setClipRect(body)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
''', '''        p.setClipRect(whole)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
'''),
('''        elif key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space) and (more or not light):self._read_at += self.body().height() * 0.8 * (-1 if key == Qt.Key_PageUp else 1)
''', '''        elif key in (Qt.Key_PageDown, Qt.Key_PageUp, Qt.Key_Space) and (more or not light):self._read_at += self._reading_rect(self.body()).height() * 0.7 * (-1 if key == Qt.Key_PageUp else 1)
'''),
# the strip under the sheets: what is being said is said whole; where the surface goes on takes what is left
('''            note = fm.elidedText(note, Qt.ElideRight, room if not said else max(room * 0.5, room - fm.horizontalAdvance('   '.join(said)) - 28 * s))
            left = room - fm.horizontalAdvance(note) - 28 * s
''', '''            note = fm.elidedText(note, Qt.ElideRight, room)
            left = room - fm.horizontalAdvance(note) - 28 * s
''')])
print('ok')
