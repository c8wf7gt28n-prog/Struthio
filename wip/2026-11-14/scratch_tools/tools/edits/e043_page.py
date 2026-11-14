import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:70])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_page.py', [('''def show_would(host, ident, setting, said):''', '''def brief(host):
    """B: the desk written up as one page, from the records. Stacy reads it (field.brief, a staC line like any other) and shows
    every line; keeping it as a page is a change, so that waits for the owner's go. No model writes any of it."""
    from .field_do import Step, op
    page = host.field_page
    if page.face != 'work' or not page.view.field.objects:return None
    face = _talk(host)
    if face is None:return None
    title = str(page.view.field.title or host.root.name).split('  ·  ')[0]
    face.answer_in_stac({'title': title, 'stac': 'field.brief | pick lines | select text', 'kind': 'desk', 'whole': True},
                        'The desk, written up from the records. This is what the page would say:')
    step = Step('Keep the brief as a page', 'write', op('field.brief.keep'),
                'a page in Documents and on the Field, to edit, export or print; when the desk changes it says so, and a later brief takes its place', 'execute')
    def done(ok, result):
        page.steps = ();page.steps_of = '';page.pending = None
        if not ok:return
        page.refresh(force=True)
        made = (result or {}).get('document') if isinstance(result, dict) else None
        ident = 'document:' + str(made.get('id')) if isinstance(made, dict) and made.get('id') else ''
        if ident and page.view.field.get(ident) is not None:
            page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe()
        page.view.update()
    card = face.stage(title, step, done=done)
    _await_go(host, 'keep the brief as a page', lambda:face.run_staged(card, done))
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def show_would(host, ident, setting, said):''')])
edit(W + 'shell2.py', [('''        shown = said
        if r.get('ok') and len(rows) > 1 and all(isinstance(row, dict) and len(row) >= 3 for row in rows):''', '''        shown = said
        if r.get('ok') and rows and all(isinstance(row, dict) and len(row) == 1 for row in rows):
            # Rows of one field are lines of writing (a page's words, a brief): each on its own line, with nothing in front of it.
            shown = '\\n'.join(str(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))[:600] for row in rows[:120] for value in row.values())
            if len(rows) > 120:shown += '\\n… %d more lines' % (len(rows) - 120)
        elif r.get('ok') and len(rows) > 1 and all(isinstance(row, dict) and len(row) >= 3 for row in rows):''')])
print('ok')
