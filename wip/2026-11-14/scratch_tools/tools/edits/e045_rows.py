import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_qt.py', [
('''    KEY_OF = {'Enter': (Qt.Key_Return, ''), 'Esc': (Qt.Key_Escape, ''), '⌫': (Qt.Key_Backspace, ''), '?': (Qt.Key_Question, '?'), 'Menu': (Qt.Key_Menu, '')}
''', '''    KEY_OF = {'Enter': (Qt.Key_Return, ''), 'Esc': (Qt.Key_Escape, ''), '⌫': (Qt.Key_Backspace, ''), 'Backspace': (Qt.Key_Backspace, ''), '?': (Qt.Key_Question, '?'),
              'Menu': (Qt.Key_Menu, ''), 'Menu key': (Qt.Key_Menu, '')}
'''),
('''        self._hot = []
        self._hover = ''                    # the sheet under the pointer: its wires show, and its whole name
''', '''        self._hot = []
        self._through = []                  # places on a page for reading whose click first closes the page, then does what the key does
        self._hover = ''                    # the sheet under the pointer: its wires show, and its whole name
'''),
('''            hot = self._hot_at(pos)
            if hot is not None:
                self.press_key(hot[1], hot[2]);return
''', '''            hot = self._hot_at(pos)
            if hot is not None:
                if any(hot[0] is box for box in self._through):self.close_reading()      # a row of the key card: the card steps aside, then the key acts
                self.press_key(hot[1], hot[2]);return
'''),
('''        self._hot = []                        # while a page is read, only its own controls are places to click
''', '''        self._hot = [];self._through = []     # while a page is read, only its own controls are places to click
'''),
('''        rows = [];at = 0.0                     # (y from the top of the writing, x, font, colour, text)
''', '''        rows = [];at = 0.0                     # (y from the top of the writing, x, font, colour, text)
        spots = []                             # a key and its words are a place to click: (top, bottom, the key's label, its words)
'''),
('''                keys, _, words = str(text).partition('\\t');lines = self._flow(words, fm_text, inner.width() - key_w)
                rows.append((at + fm_text.ascent(), 0.0, key_font, t.AMBER_TEXT, keys))
                for line in lines:
                    rows.append((at + fm_text.ascent(), key_w, text_font, t.TEXT, line));at += fm_text.height()
                at += 5 * s
''', '''                keys, _, words = str(text).partition('\\t');lines = self._flow(words, fm_text, inner.width() - key_w);began = at
                rows.append((at + fm_text.ascent(), 0.0, key_font, t.AMBER_TEXT, keys))
                for line in lines:
                    rows.append((at + fm_text.ascent(), key_w, text_font, t.TEXT, line));at += fm_text.height()
                spots.append((began, at, keys, words));at += 5 * s
'''),
('''        p.setClipRect(whole)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
''', '''        for began, ended, keys, words in spots:      # each key's row does what the key does; on a page for reading, the page closes first
            found = self._key_of(keys);top_seen = inner.top() + began - self._read_at;bottom_seen = inner.top() + ended - self._read_at
            if found is None or bottom_seen < inner.top() + 4 or top_seen > inner.bottom() - 4:continue
            box = QRectF(inner.left() - 6 * s, max(inner.top(), top_seen), inner.width() + 12 * s, min(inner.bottom(), bottom_seen) - max(inner.top(), top_seen))
            self._hot.append((box, found[0], found[1], words[:1].upper() + words[1:]))
            if not read.get('light'):self._through.append(box)
        p.setClipRect(whole)
        base = r.bottom() - pad / 2 - fm_foot.descent();p.setFont(self.mono(12))
''')])
edit(W + 'field_page.py', [('''    face = _talk(host)
    if face is not None and steps:face.say_steps(obj.title, steps, lambda n, obj=obj:take(host, obj, n))
    if not steps:host.statusBar().showMessage('Field · the records offer nothing to do about %s' % obj.title, 6000)
    return page.steps
''', '''    face = _talk(host)
    if face is not None and steps:face.say_steps(obj.title, steps, lambda n, obj=obj:take(host, obj, n))
    if not steps:host.statusBar().showMessage('Field · the records offer nothing to do about %s' % obj.title, 6000)
    if steps:
        # The steps, where the eyes are and where the pointer can reach them: a light page whose rows are the steps. A click on
        # a row, or its digit, takes it; the page steps aside at any other key. A step that changes something says it waits.
        name = obj.title if len(obj.title) <= 56 else obj.title[:55].rstrip() + '…'
        rows = [('k', '%d\\t%s%s%s' % (n + 1, step.words, ' · waits for your Approve' if step.kind == 'write' else '', (' — ' + step.why) if step.why else '')) for n, step in enumerate(steps)]
        page.view.show_reading('What can be done about “%s”' % name, rows, '1 – %d  take a step      Esc  close      any other key moves on' % len(steps) if len(steps) > 1 else '1  take the step      Esc  close',
                               light=True)
        page.view.steps = tuple((step.words, step.kind) for step in steps)       # showing the page does not withdraw what was just offered
        page.view.setFocus(Qt.OtherFocusReason)
    return page.steps
''')])
print('ok')
