import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/shell2.py', [
("""        line = thing['stac'];operation, arguments = route_program(line)
        card = self.say(intro)""", """        from .field_do import call as line_call
        line = thing['stac'];operation, arguments = line_call(line)
        card = self.say(intro)"""),
("""        else:
            said = (readable_result(r['result']) if isinstance(r['result'], dict) else str(r['result'])[:2000]) if r.get('ok') \\
                else 'The records did not answer: ' + r['error']['message']""",
"""        else:
            said = (readable_result(r['result']) if isinstance(r['result'], dict) else str(r['result'])[:2000]) if r.get('ok') \\
                else 'The records did not answer: ' + r['error']['message']
            if r.get('ok') and said == 'Done.' and isinstance(r['result'], dict):      # a read whose answer is a record, not rows: the record itself, in short
                said = json.dumps(r['result'], indent=1, ensure_ascii=False, default=str)[:1500]"""),
("""    def ask(self, text, about=None):
        thing = self.thing_asked_about(text)""", '''    # ---- doing: the steps the records offer for a thing (workbench/field_do.py), said and carried out here ---------------------
    def say_steps(self, title, steps, take):
        """What can be done about a thing: each step a word to choose, numbered as the Field numbers them. `take(n)` takes one."""
        card = self.say('What can be done about “%s”. A number in the Field takes a step, or choose it here. One that changes something asks first.' % title)
        for n, step in enumerate(steps[:9]):
            words = '%d  %s' % (n + 1, step.words) + ('  ·  asks first' if step.kind == 'write' else '')
            card.box.addWidget(sentence('{go}', {'go': (words, lambda n=n:take(n))}))
        card.steps = steps
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def stage(self, title, step, done=None):
        """A step that changes something waits here for the owner: what it does, what it leaves behind, the exact line, and
        Run. Run is the owner's go: the line goes through the Kernel with the owner's own authority, once. `done(ok, result)`
        is told how it went, so the Field can read the records again."""
        from .context_menu import inspect_in_line
        card = self.say('For “%s”: %s. This changes something, so it waits for you.' % (title, step.words[:1].lower() + step.words[1:]))
        if step.why:
            why = QLabel(breakable(step.why[:1].upper() + step.why[1:] + '.'));why.setWordWrap(True);why.setStyleSheet('color:%s' % QUIET)
            why.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(why)
        code = QLabel(breakable(step.line));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(15))
        code.setStyleSheet('color:%s' % TEAL_TEXT);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse);code.setAccessibleName('The line: ' + step.line);card.box.addWidget(code)
        row = QHBoxLayout();run = button('Run', 'stac');run.setObjectName('StagedRun');row.addWidget(run)
        row.addWidget(sentence('{line}', {'line': ('in the line', lambda:inspect_in_line(self.host, step.line))}));row.addStretch(1);card.box.addLayout(row)
        card.step = step;card.run = run;card.ran = None
        run.clicked.connect(lambda:self.run_staged(card, done))
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def run_staged(self, card, done=None):
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_do import call as line_call
        if card.ran is not None:return           # one go, one run
        operation, arguments = line_call(card.step.line)
        r = engineering(self.host.root).dispatch(operation, arguments, operator())
        card.ran = bool(r.get('ok'));card.run.setEnabled(False);card.run.setText('Ran' if card.ran else 'Refused')
        if card.ran:
            result = r['result'] if isinstance(r['result'], dict) else {}
            if isinstance(result.get('document'), dict) and result['document'].get('title'):said = 'Done: “%s”.' % result['document']['title']
            elif isinstance(result.get('words'), str) and result['words']:said = 'Done. ' + result['words']
            elif isinstance(result.get('changed'), list):said = 'Done: %s.' % ('nothing had changed' if not result['changed'] else '%d changed' % len(result['changed']))
            elif isinstance(result.get('ran'), list):said = 'Done: %d check%s ran%s.' % (len(result['ran']), '' if len(result['ran']) == 1 else 's', (': ' + ', '.join(str(x.get('outcome')) for x in result['ran'][:6])) if result['ran'] else '')
            else:said = 'Done.'
        else:
            said = 'It was refused, and nothing was changed: ' + str((r.get('error') or {}).get('message'))[:400]
        note = QLabel(breakable(said));note.setWordWrap(True);note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(note)
        if done is not None:done(card.ran, r.get('result') if card.ran else None)

    def say_desk(self, count, waiting, lines, go):
        """The desk, checked: how many things were read, which wait for the owner and why, and the reads that were made.
        `go(object)` goes to one of them in the Field and says what can be done about it."""
        if not waiting:
            card = self.say('I read the desk: %d thing%s. Nothing waits for you.' % (count, '' if count == 1 else 's'))
        else:
            card = self.say('I read the desk: %d thing%s. %d wait%s for you:' % (count, '' if count == 1 else 's', len(waiting), 's' if len(waiting) == 1 else ''))
            for n, (obj, why, steps) in enumerate(waiting[:12]):
                card.box.addWidget(sentence('{go}', {'go': ('“%s”' % obj.title, lambda obj=obj:go(obj))}))
                first = next((step for step in steps if step.kind == 'write'), None)
                said = QLabel(breakable(why + ((' · next: ' + first.words[:1].lower() + first.words[1:]) if first else '')));said.setWordWrap(True)
                said.setStyleSheet('color:%s' % QUIET);said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            if len(waiting) > 12:card.box.addWidget(QLabel('… and %d more' % (len(waiting) - 12)))
        if lines:program_detail(card.box, 'The %d reads I made' % len(lines), '\\n'.join(lines))
        card.waiting = waiting
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def ask(self, text, about=None):
        thing = self.thing_asked_about(text)'''),
])

edit('workbench/field_page.py', [
("""        self.view.stac_run.connect(lambda obj: stac_run(self.host, obj))""", """        self.view.stac_run.connect(lambda obj: stac_run(self.host, obj))
        self.view.do_asked.connect(lambda obj: do(self.host, obj))
        self.view.step_chosen.connect(lambda obj, n: take(self.host, obj, n))
        self.view.check_asked.connect(lambda: check_desk(self.host))
        self.steps = ();self.steps_of = ''      # the steps last offered, and the object they were offered for"""),
("""def stac_in_line(host, obj):""", '''def _talk(host):
    """Stacy's pane, brought to the front of the right column; the keyboard stays in the Field."""
    shell = getattr(host, 'shell2', None)
    if shell is None:return None
    face = shell.show_slate_face()
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):page.view.setFocus(Qt.OtherFocusReason)
    return face


def do(host, obj):
    """D: ask the records what can be done about this sheet. The steps show in the Field, numbered, and Stacy says them in
    Talk. Nothing runs by being offered."""
    from .engineering_kernel import operator
    from .field_do import steps_for
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or obj is None:return ()
    steps = steps_for(kernel, operator(), obj, page.view.field)
    page.steps = tuple(steps);page.steps_of = obj.id
    page.view.steps = tuple((step.words, step.kind) for step in steps);page.view.update()
    face = _talk(host)
    if face is not None and steps:face.say_steps(obj.title, steps, lambda n, obj=obj:take(host, obj, n))
    if not steps:host.statusBar().showMessage('Field · the records offer nothing to do about %s' % obj.title, 6000)
    return page.steps


def take(host, obj, n):
    """Take one of the steps offered for this sheet. A read runs at once and Stacy shows its line and what the records
    answered. A step that changes something is put in Talk with its exact line and waits for the owner's Run; when it has
    run, the Field reads the records again."""
    page = host.field_page
    if obj is None or page.steps_of != obj.id or not 0 <= n < len(page.steps):return None
    step = page.steps[n];face = _talk(host)
    if face is None:return None
    if step.kind == 'read':
        card = face.answer_in_stac({'title': obj.title, 'stac': step.line, 'kind': obj.kind}, '%s, for “%s”:' % (step.words, obj.title))
    else:
        card = face.stage(obj.title, step, done=lambda ok, result, obj=obj:_after(host, obj, ok, result))
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def _after(host, obj, ok, result):
    """A step changed something: the Field reads the records again. A page that took the place of the selected one (a
    calculation brought up to date) is the one selected now."""
    if not ok:return
    page = host.field_page;page.refresh(force=True)
    made = (result or {}).get('document') if isinstance(result, dict) else None
    for ident in (('document:' + str(made.get('id'))) if isinstance(made, dict) and made.get('id') else '', obj.id):
        if ident and page.view.field.get(ident) is not None:
            page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe();break
    page.view.update()


def check_desk(host):
    """C: check the desk. Everything is read again; findings are checked against their sources without marking anything;
    Stacy says what waits and why, each with the step that would settle it, and lists the reads she made."""
    from .engineering_kernel import operator
    from .field_do import sweep
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work':return None
    page.refresh(force=True)
    waiting, lines = sweep(kernel, operator(), page.view.field)
    face = _talk(host)
    if face is None:return None
    def go(obj):
        if page.view.field.get(obj.id) is None:return
        page.view.field.select(obj.id);page.view._reveal_pending = True;page.view._describe();page.view.update();do(host, obj)
    return face.say_desk(len(page.view.field.objects), waiting, lines, go)


def stac_in_line(host, obj):'''),
])

edit('workbench/field_qt.py', [
("""    full_asked = Signal(object)        # F on the shelf: the selected program in its full window
""", """    full_asked = Signal(object)        # F on the shelf: the selected program in its full window
    check_asked = Signal()             # C: check the desk (everything read again, what waits said with its next step)
"""),
("""        elif key == Qt.Key_F and plain:      # F on the shelf: this program in its full window""", """        elif key == Qt.Key_C and plain:      # C: check the desk
            self.check_asked.emit();return
        elif key == Qt.Key_F and plain:      # F on the shelf: this program in its full window"""),
("""(2, 'D  do'), (4, 'S  staC'), (6, 'Menu  more'), (5, 'A  next waiting'), (7, 'R  look again'), (0, 'Esc  back')]""",
 """(2, 'D  do'), (4, 'C  check all'), (5, 'S  staC'), (7, 'Menu  more'), (6, 'A  next waiting'), (8, 'R  look again'), (0, 'Esc  back')]"""),
("""        legend = [(8, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend""",
 """        legend = [(9, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend"""),
])

edit('workbench/context_menu.py', [
("""        out.append(Entry('field:again', 'Look again', 'open', view.look_again.emit, icon='explore', caption='R', tip='Read the records again'))""",
 """        out.append(Entry('field:again', 'Look again', 'open', view.look_again.emit, icon='explore', caption='R', tip='Read the records again'))
        if view.face == 'work':
            out.append(Entry('field:check', 'Check the desk', 'command', view.check_asked.emit, icon='explore', caption='C',
                             tip='Everything is read again; Stacy says what waits for you and what would settle it'))"""),
("""    if not network:
        out.append(Entry('field:ask', 'Ask Stacy about this', 'command',""", """    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     tip='The steps the records offer for this. A read runs at once; one that changes something asks first'))
    if not network:
        out.append(Entry('field:ask', 'Ask Stacy about this', 'command',"""),
])
print('edits applied')
