import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_qt.py', [
("""    check_asked = Signal()             # C: check the desk (everything read again, what waits said with its next step)
""", """    check_asked = Signal()             # C: check the desk (everything read again, what waits said with its next step)
    go_asked = Signal()                # G: the owner's go for what waits in Talk. Never a digit: digits only choose
"""),
("""        self._now = 0.0                     # the time of this painting, for "changed lately"
""", """        self._now = 0.0                     # the time of this painting, for "changed lately"
        self.go = ''                        # what G would run now, in words, while something waits in Talk for the owner's go
"""),
("""        obj = self.selected();self.steps = ()          # the steps belong to the sheet they were asked for: another sheet, or a new reading, closes them""",
 """        obj = self.selected();self.steps = ();self.go = ''      # the steps and the go belong to the sheet they were asked for: another sheet, or a new reading, closes them"""),
("""            if self.steps:                   # the first Esc closes the steps; the next one leaves
                self.steps = ();self.update();return""", """            if self.steps or self.go:        # the first Esc closes the steps and withdraws the go from the keyboard; the next one leaves
                self.steps = ();self.go = '';self.update();return"""),
("""        elif key == Qt.Key_C and plain:      # C: check the desk""", """        elif key == Qt.Key_G and plain:      # G: go. Only while something waits in Talk and says so here
            if self.go:self.go_asked.emit()
            return
        elif key == Qt.Key_C and plain:      # C: check the desk"""),
("""        if self.steps:return self._do(p, body, w)""", """        if self.steps or self.go:return self._do(p, body, w)"""),
("""        tall = pad * 2 + head.height() + 4 * s + len(rows) * fm.height() + 6 * s + head.height()
        if tall > body.height() - 24 * s:return           # no room under her: the foot still says them""",
 """        going = self._wrap('G  ' + self.go, fm, inner_w, 3) if self.go else []
        tall = pad * 2 + head.height() + 4 * s + (len(rows) + len(going)) * fm.height() + (4 * s if rows and going else 0) + 6 * s + head.height()
        if tall > body.height() - 24 * s:return           # no room under her: the foot still says them"""),
("""        y += 6 * s + head.ascent();p.setPen(QColor(t.QUIET))
        p.drawText(QPointF(x, y), fm.elidedText('1-%d  take  ·  Esc  close' % min(9, len(self.steps)) if len(self.steps) > 1 else '1  take  ·  Esc  close', Qt.ElideRight, inner_w))""",
 """        if going:                            # what waits in Talk for the owner's go, and the key that gives it
            if rows:y += 4 * s
            p.setPen(QColor(t.AMBER_TEXT))
            for at, line in enumerate(going):
                y += fm.height();p.drawText(QPointF(x, y - fm.descent()), fm.elidedText(line if at == 0 else '   ' + line, Qt.ElideRight, inner_w))
        y += 6 * s + head.ascent();p.setPen(QColor(t.QUIET))
        keys = [('1-%d  take' % min(9, len(self.steps)) if len(self.steps) > 1 else '1  take')] if self.steps else []
        if self.go:keys.append('G  go')
        p.drawText(QPointF(x, y), fm.elidedText('  ·  '.join(keys + ['Esc  close']), Qt.ElideRight, inner_w))"""),
("""        if self.steps:                       # the owner asked what can be done: the foot says the steps, wherever the rail is
            said = 'DO      ' + '      '.join('%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9]))
            code = '';p.setPen(QColor(t.AMBER_TEXT))""",
 """        if self.steps or self.go:            # the owner asked what can be done: the foot says the steps and the go, wherever the rail is
            said = 'DO      ' + '      '.join(['%d  %s%s' % (n + 1, words, ' (asks first)' if kind == 'write' else '') for n, (words, kind) in enumerate(self.steps[:9])]
                                              + (['G  ' + self.go] if self.go else []))
            code = '';p.setPen(QColor(t.AMBER_TEXT))"""),
])

edit('workbench/field_page.py', [
("""        self.view.check_asked.connect(lambda: check_desk(self.host))""", """        self.view.check_asked.connect(lambda: check_desk(self.host))
        self.view.go_asked.connect(lambda: go(self.host))"""),
("""        self.pending = None                     # what the single offered step runs, when it is a step of the desk or the Run of what waits in Talk""",
 """        self.pending = None                     # what G runs: the Run of what waits in Talk for the owner's go
        self.star = None                        # what step 1 does when the steps are the desk's own (settle what can be settled)"""),
("""def _offer(host, words, run, kind='run'):
    \"\"\"One step offered from the keyboard that is not a step of a sheet: settling the desk, or the Run of what waits in Talk.
    It shows where the steps show, as 1; taking it runs `run`. The mouse has the same thing in Talk.\"\"\"
    page = host.field_page
    page.steps = (words,);page.steps_of = '*';page.pending = run
    page.view.steps = ((words, kind),);page.view.update()      # 'run': taking it is the owner's go itself; 'write': it shows what it would do first""",
 """def _await_go(host, words, run):
    \"\"\"Something waits in Talk for the owner's go. From the keyboard the go is G, and only G: a digit chooses a step and never
    approves one. The Field says what G would run for as long as it would; moving to another sheet, or Esc, withdraws it from
    the keyboard (the Run in Talk stays).\"\"\"
    page = host.field_page
    page.pending = run;page.view.go = words;page.view.update()


def go(host):
    \"\"\"G: the owner's go for what waits.\"\"\"
    page = host.field_page
    run, page.pending = page.pending, None
    page.view.go = '';page.view.update()
    if run is not None:run()
    if getattr(host, '_field_active', False):page.view.setFocus(Qt.OtherFocusReason)"""),
("""    if page.steps_of == '*':                   # the one step of the desk, or the Run of what waits in Talk
        run, page.pending = page.pending, None
        page.steps = ();page.steps_of = '';page.view.steps = ();page.view.update()
        if n == 0 and run is not None:run()
        page.view.setFocus(Qt.OtherFocusReason)
        return None""", """    if page.steps_of == '*':                   # the desk's own step: it shows what it would change and asks; it runs nothing
        star, page.star = page.star, None
        page.steps = ();page.steps_of = '';page.view.steps = ();page.view.update()
        if n == 0 and star is not None:star()
        page.view.setFocus(Qt.OtherFocusReason)
        return None"""),
("""        card = face.stage(obj.title, step, done=done)
        _offer(host, 'Run it, as written in Talk', lambda:face.run_staged(card, done))      # the keyboard's Run: 1""",
 """        card = face.stage(obj.title, step, done=done)
        _await_go(host, step.words[:1].lower() + step.words[1:], lambda:face.run_staged(card, done))"""),
("""        _offer(host, 'Run all %d, as listed in Talk' % len(plan) if len(plan) > 1 else 'Run it, as listed in Talk', lambda:face.run_plan(card, done))""",
 """        _await_go(host, 'all %d changes, as listed in Talk' % len(plan) if len(plan) > 1 else 'the change, as listed in Talk', lambda:face.run_plan(card, done))"""),
("""    page.steps = ();page.steps_of = '';page.pending = None
    if plan:_offer(host, 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's'), settle, 'write')
    return card""", """    page.steps = ();page.steps_of = '';page.pending = None;page.star = None
    if plan:                                   # the desk's own step, numbered 1: it puts the changes up; G then gives the go
        words = 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's')
        page.steps = (words,);page.steps_of = '*';page.star = settle
        page.view.steps = ((words, 'write'),);page.view.update()
    return card"""),
])
print('edits applied')
