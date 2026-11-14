import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_do.py', [
("""    scope: str = 'read'     # the Kernel's scope for it: read, execute, approve
""", """    scope: str = 'read'     # the Kernel's scope for it: read, execute, approve
    settles: bool = False   # taking it is what brings the thing back to current (so "settle the desk" may include it)
"""),
("""                        'the same calculation, worked again from the sheet as it is now; the new page takes its place and this one is kept in Documents', 'approve'))""",
 """                        'the same calculation, worked again from the sheet as it is now; the new page takes its place and this one is kept in Documents', 'approve', True))"""),
("""                        'the page is read again, the numbers added, and the result paragraph rewritten', 'execute'))""",
 """                        'the page is read again, the numbers added, and the result paragraph rewritten', 'execute', True))"""),
("""                        'each check is a read with an expectation; what passes counts as support', 'execute'))""",
 """                        'each check is a read with an expectation; what passes counts as support', 'execute', True))"""),
("""def sweep(kernel, principal, field):""", '''def settling(waiting):
    """From a checked desk, the changes that would bring things back to current, one for each thing that has one, in the
    order the desk lists them: [(object, step)]. What only the owner can decide (a review, an open question) is not here."""
    plan = [];seen = set()
    for obj, _, steps in waiting:
        step = next((step for step in steps if step.kind == 'write' and step.settles), None)
        if step is not None and step.line not in seen:
            plan.append((obj, step));seen.add(step.line)
    return plan


def sweep(kernel, principal, field):'''),
])

edit('workbench/shell2.py', [
("""    def say_desk(self, count, waiting, lines, go):
        \"\"\"The desk, checked: how many things were read, which wait for the owner and why, and the reads that were made.
        `go(object)` goes to one of them in the Field and says what can be done about it.\"\"\"""",
 """    def say_desk(self, count, waiting, lines, go, plan=(), settle=None):
        \"\"\"The desk, checked: how many things were read, which wait for the owner and why, and the reads that were made.
        `go(object)` goes to one of them in the Field and says what can be done about it. `plan` is the changes that would
        settle what can be settled without a decision of the owner's; `settle()` puts them up for one Run.\"\"\""""),
("""        if lines:program_detail(card.box, 'The %d reads I made' % len(lines), '\\n'.join(lines))
        card.waiting = waiting""", """        if plan and settle is not None:
            card.box.addWidget(sentence('{settle}', {'settle': ('Settle what I can: %d change%s, one Run' % (len(plan), '' if len(plan) == 1 else 's'), settle)}))
        if lines:program_detail(card.box, 'The %d reads I made' % len(lines), '\\n'.join(lines))
        card.waiting = waiting;card.plan = plan"""),
("""    def ask(self, text, about=None):
        thing = self.thing_asked_about(text)""", '''    def say_plan(self, plan, done=None):
        """Several changes put up together: each named, with its exact line, and one Run. Run is the owner's go for the whole
        list as written. They run in order through the Kernel and stop at the first that is refused; each says how it went.
        `done(results)` is told, so the desk can be checked again: finished means the check finds nothing waiting."""
        card = self.say('To settle the desk I would make %d change%s. One Run does them in order, as written here, and stops at the first that is refused.' % (len(plan), '' if len(plan) == 1 else 's'))
        card.rows = []
        for n, (obj, step) in enumerate(plan):
            said = QLabel(breakable('%d  “%s”: %s' % (n + 1, obj.title, step.words[:1].lower() + step.words[1:])));said.setWordWrap(True)
            said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            code = QLabel(breakable(step.line));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(14))
            code.setStyleSheet('color:%s' % TEAL_TEXT);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);code.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card.box.addWidget(code);card.rows.append(said)
        row = QHBoxLayout();run = button('Run all %d' % len(plan) if len(plan) > 1 else 'Run', 'stac');run.setObjectName('PlanRun');row.addWidget(run);row.addStretch(1);card.box.addLayout(row)
        card.plan = plan;card.run = run;card.results = None
        run.clicked.connect(lambda:self.run_plan(card, done))
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def run_plan(self, card, done=None):
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_do import call as line_call
        if card.results is not None:return        # one go, one run
        card.results = [];card.run.setEnabled(False)
        for n, (obj, step) in enumerate(card.plan):
            operation, arguments = line_call(step.line)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
            ok = bool(r.get('ok'));card.results.append((step.line, ok, r.get('result') if ok else (r.get('error') or {}).get('message')))
            result = r.get('result') if ok and isinstance(r.get('result'), dict) else {}
            title = (result.get('document') or {}).get('title') if isinstance(result.get('document'), dict) else None
            card.rows[n].setText(breakable(card.rows[n].text() + ('  ·  done' + (': “%s”' % title if title else '') if ok else '  ·  REFUSED: ' + str((r.get('error') or {}).get('message'))[:200])))
            if not ok:break
        went = sum(1 for _, ok, _ in card.results if ok)
        card.run.setText('Ran %d of %d' % (went, len(card.plan)))
        if done is not None:done(card.results)

    def ask(self, text, about=None):
        thing = self.thing_asked_about(text)'''),
])

edit('workbench/field_page.py', [
("""    from .field_do import sweep
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work':return None
    page.refresh(force=True)
    waiting, lines = sweep(kernel, operator(), page.view.field)
    face = _talk(host)
    if face is None:return None
    def go(obj):
        if page.view.field.get(obj.id) is None:return
        page.view.field.select(obj.id);page.view._reveal_pending = True;page.view._describe();page.view.update();do(host, obj)
    return face.say_desk(len(page.view.field.objects), waiting, lines, go)""",
 """    from .field_do import settling, sweep
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work':return None
    page.refresh(force=True)
    waiting, lines = sweep(kernel, operator(), page.view.field)
    face = _talk(host)
    if face is None:return None
    def go(obj):
        if page.view.field.get(obj.id) is None:return
        page.view.field.select(obj.id);page.view._reveal_pending = True;page.view._describe();page.view.update();do(host, obj)
    plan = settling(waiting)
    def settle():
        # The changes go up together for one Run; when they have run the desk is checked again, and that check is the answer.
        face.say_plan(plan, done=lambda results:check_desk(host))
        page.view.setFocus(Qt.OtherFocusReason)
    return face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle)"""),
])
print('edits applied')
