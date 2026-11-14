import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)
edit('workbench/field_page.py', [
("""        self.steps = ();self.steps_of = ''      # the steps last offered, and the object they were offered for""",
 """        self.steps = ();self.steps_of = ''      # the steps last offered, and the object they were offered for
        self.pending = None                     # what the single offered step runs, when it is a step of the desk or the Run of what waits in Talk"""),
("""def do(host, obj):""", """def _offer(host, words, run):
    \"\"\"One step offered from the keyboard that is not a step of a sheet: settling the desk, or the Run of what waits in Talk.
    It shows where the steps show, as 1; taking it runs `run`. The mouse has the same thing in Talk.\"\"\"
    page = host.field_page
    page.steps = (words,);page.steps_of = '*';page.pending = run
    page.view.steps = ((words, 'write'),);page.view.update()


def do(host, obj):"""),
("""    page = host.field_page
    if obj is None or page.steps_of != obj.id or not 0 <= n < len(page.steps):return None
    step = page.steps[n];face = _talk(host)
    if face is None:return None
    if step.kind == 'read':
        card = face.answer_in_stac({'title': obj.title, 'stac': step.line, 'kind': obj.kind}, '%s, for “%s”:' % (step.words, obj.title))
    else:
        card = face.stage(obj.title, step, done=lambda ok, result, obj=obj:_after(host, obj, ok, result))
    page.view.setFocus(Qt.OtherFocusReason)
    return card""",
 """    page = host.field_page
    if page.steps_of == '*':                   # the one step of the desk, or the Run of what waits in Talk
        run, page.pending = page.pending, None
        page.steps = ();page.steps_of = '';page.view.steps = ();page.view.update()
        if n == 0 and run is not None:run()
        page.view.setFocus(Qt.OtherFocusReason)
        return None
    if obj is None or page.steps_of != obj.id or not 0 <= n < len(page.steps):return None
    step = page.steps[n];face = _talk(host)
    if face is None:return None
    if step.kind == 'read':
        card = face.answer_in_stac({'title': obj.title, 'stac': step.line, 'kind': obj.kind}, '%s, for “%s”:' % (step.words, obj.title))
    else:
        done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
        card = face.stage(obj.title, step, done=done)
        _offer(host, 'Run it, as written in Talk', lambda:face.run_staged(card, done))      # the keyboard's Run: 1
    page.view.setFocus(Qt.OtherFocusReason)
    return card"""),
("""    if not ok:return
    page = host.field_page;page.refresh(force=True)""", """    page = host.field_page;page.steps = ();page.steps_of = '';page.pending = None
    if not ok:
        page.view.steps = ();page.view.update();return
    page.refresh(force=True)"""),
("""    def settle():
        # The changes go up together for one Run; when they have run the desk is checked again, and that check is the answer.
        face.say_plan(plan, done=lambda results:check_desk(host))
        page.view.setFocus(Qt.OtherFocusReason)
    return face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle)""",
 """    def settle():
        # The changes go up together for one Run; when they have run the desk is checked again, and that check is the answer.
        done = lambda results:check_desk(host)
        card = face.say_plan(plan, done=done)
        _offer(host, 'Run all %d, as listed in Talk' % len(plan) if len(plan) > 1 else 'Run it, as listed in Talk', lambda:face.run_plan(card, done))
        page.view.setFocus(Qt.OtherFocusReason)
    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle)
    page.steps = ();page.steps_of = '';page.pending = None
    if plan:_offer(host, 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's'), settle)
    return card"""),
])
print('edits applied')
