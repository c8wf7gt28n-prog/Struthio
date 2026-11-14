import io
p = '/home/user/Struthio/workbench/field_qt.py'
t = io.open(p, encoding='utf8').read()
def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (t.count(old), old[:70])
    t = t.replace(old, new)

rep('''    doubt_asked = Signal(object)       # X: cross-examine the selected object for what a plausible result may hide
''', '''    doubt_asked = Signal(object)       # X: cross-examine the selected object for what a plausible result may hide
    brief_asked = Signal()             # B: the desk written up as one page, from the records
''')
rep('''        self.go = ''                        # what G would run now, in words, while something waits in Talk for the owner's go
''', '''        self.go = ''                        # what G would run now, in words, while something waits in Talk for the owner's go
        self.would = {}                     # a what-if followed along the wires: {object id: the few words of what it would say}
        self.would_said = ''                # the what-if itself, in words, for as long as its marks show
        self._trail = [];self._last = ''    # the sheets the owner was on before this one, for Backspace
''')
rep('''        if kept:self.field.select(keep)
        else:self.scroll_x = self.scroll_y = 0.0
        self._reveal_pending = True
''', '''        if kept:self.field.select(keep)
        else:self.scroll_x = self.scroll_y = 0.0
        self.would = {};self.would_said = ''      # a what-if is about the records as they were read: a new reading ends it
        self._reveal_pending = True
''')
rep('''        obj = self.selected();self.steps = ();self.go = ''      # the steps and the go belong to the sheet they were asked for: another sheet, or a new reading, closes them
''', '''        obj = self.selected();self.steps = ();self.go = ''      # the steps and the go belong to the sheet they were asked for: another sheet, or a new reading, closes them
        now = self.field.selected
        if self._last and now and now != self._last and (not self._trail or self._trail[-1] != self._last):
            self._trail.append(self._last);del self._trail[:-40]       # where the owner was: Backspace goes back along it
        if now:self._last = now
''')
rep('''        elif key == Qt.Key_Escape:
            if self.steps or self.go:        # the first Esc closes the steps and withdraws the go from the keyboard; the next one leaves
                self.steps = ();self.go = '';self.update();return
            self.left.emit();return
''', '''        elif key == Qt.Key_Escape:
            if self.steps or self.go:        # the first Esc closes the steps and withdraws the go from the keyboard; the next one leaves
                self.steps = ();self.go = '';self.update();return
            if self.would:                   # then a what-if's marks are cleared: the desk shows what is, again
                self.would = {};self.would_said = '';self.update();return
            self.left.emit();return
        elif key == Qt.Key_Backspace and plain:      # back to the sheet the owner was on before this one, and the one before that
            while self._trail:
                ident = self._trail.pop()
                if ident != self.field.selected and self.field.get(ident) is not None:
                    self._last = '';self.field.select(ident);break      # going back is not a step forward: it leaves no trail of its own
            else:
                return
        elif key == Qt.Key_B and plain:      # B: the brief
            self.brief_asked.emit();return
''')
# the sheet: a what-if's words, in amber, where the first fact stands
rep('''        y += 4 * s
        for fact in (() if self.field.compact else obj.lines[:FACT_LINES]):
            if y + fm.height() > inner.bottom() - where_h + 1:break
            y += fm.height();p.setPen(ink(t.QUIET, keep));p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(fact)[:LONGEST], Qt.ElideRight, inner.width()))
''', '''        y += 4 * s
        would = self.would.get(obj.id)
        facts = () if self.field.compact else (((would,) + tuple(obj.lines[:FACT_LINES - 1])) if would else obj.lines[:FACT_LINES])
        for at, fact in enumerate(facts):
            if y + fm.height() > inner.bottom() - where_h + 1:break
            y += fm.height();p.setPen(ink(t.AMBER_TEXT, 1.0) if would and at == 0 else ink(t.QUIET, keep))
            p.drawText(QPointF(inner.left(), y - fm.descent()), fm.elidedText(str(fact)[:LONGEST], Qt.ElideRight, inner.width()))
        if would:                            # and a broken amber edge: it reads as "would", without colour too
            pen = QPen(ink(t.AMBER_EDGE, 0.95), 1.6);pen.setStyle(Qt.CustomDashLine);pen.setDashPattern([4, 4])
            p.setPen(pen);p.setBrush(Qt.NoBrush);p.drawRect(r.adjusted(-3 * s, -3 * s, 3 * s, 3 * s))
''')
rep('''        note = ' · '.join(part for part in (self.field.note, self.problem) if part)
''', '''        note = ' · '.join(part for part in ((self.would_said + ' · nothing is changed · Esc clears') if self.would_said else '', self.field.note, self.problem) if part)
''')
rep('''        legend = [(3, '← ↑ ↓ →  move'), (1, 'Enter  open'), (2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'), (10, 'R  look again'), (0, 'Esc  back')]
''', '''        legend = [(3, '← ↑ ↓ →  move'), (1, 'Enter  open'), (2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (6.5, 'B  brief'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'),
                  (10, 'R  look again'), (12, '⌫  where I was'), (0, 'Esc  back')]
''')
# the foot says the what-if for the selected sheet
rep('''        if not said:said = obj.where
        p.setFont(self.mono(12.5));fm3 = QFontMetricsF(p.font());p.setPen(QColor(t.QUIET))
''', '''        if not said:said = obj.where
        p.setFont(self.mono(12.5));fm3 = QFontMetricsF(p.font());p.setPen(QColor(t.QUIET))
        if self.would.get(obj.id):           # a what-if marks this sheet: the foot says it whole
            said = 'WHAT IF      ' + self.would_said + '      ' + self.would[obj.id];p.setPen(QColor(t.AMBER_TEXT))
''')
io.open(p, 'w', encoding='utf8').write(t)
print('ok')
