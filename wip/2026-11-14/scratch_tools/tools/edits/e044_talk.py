import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

# ---- B: the brief is a page, so it is read as one, in the centre -------------------------------------------------------------
t = io.open(W + 'field_page.py', encoding='utf8').read()
start = t.index('def brief(host):');end = t.index('def show_would(host, ident, setting, said):')
t = t[:start] + '''def brief(host):
    """B: the desk written up as one page, from the records. It is a page, so it is shown as one: over the work, at reading
    size, to scroll. Keeping it as a page is a change, so that waits for the owner's go (G here, or Run in Talk), and the
    go keeps exactly the desk that was shown. No model writes any of it; the staC line that reads it is under the page."""
    from .engineering_kernel import operator
    from .field_do import Step, op
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work' or not page.view.field.objects:return None
    answer = kernel.dispatch('field.brief', {}, operator())
    if not answer.get('ok'):
        host.statusBar().showMessage('Field · the brief could not be read: %s' % str((answer.get('error') or {}).get('message'))[:160], 9000);return None
    made = answer['result'];lines = made['lines'];title = lines[0]['text'] if lines else 'The brief'
    style = {'head': 'q', 'title': 'h', 'foot': 'q'}
    page.view.show_reading(title, [(style.get(line['part'], 'b'), line['text']) for line in lines[1:]],
                           'G  keep it as a page      ↑ ↓  read on      Esc  close', 'field.brief | pick lines | select text')
    step = Step('Keep the brief as a page', 'write', op('field.brief.keep', shown=made['fingerprint']),
                'a page in Documents and on the Field, to edit, export or print; when the desk changes it says so, and a later brief takes its place', 'execute')

    def done(ok, result):
        page.steps = ();page.steps_of = '';page.pending = None
        page.view.close_reading()
        if not ok:
            host.statusBar().showMessage('Field · the brief was not kept; B reads the desk again', 9000);page.view.update();return
        page.refresh(force=True)
        kept = (result or {}).get('document') if isinstance(result, dict) else None
        ident = 'document:' + str(kept.get('id')) if isinstance(kept, dict) and kept.get('id') else ''
        if ident and page.view.field.get(ident) is not None:
            page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe()
        page.view.update()

    face = _talk(host)
    if face is not None:                       # Talk holds the change itself, with its line and its Run; the page is read in the Field
        card = face.stage(title, step, done=done)
        run = lambda: face.run_staged(card, done)
    else:
        card = None
        def run():
            r = kernel.dispatch('field.brief.keep', {'shown': made['fingerprint']}, operator())
            done(bool(r.get('ok')), r.get('result') if r.get('ok') else None)
    _await_go(host, 'keep the brief as a page', run)
    page.view.setFocus(Qt.OtherFocusReason)
    return card


''' + t[end:]
old = '''        self.view.brief_asked.connect(lambda: brief(self.host))
'''
assert t.count(old) == 1
t = t.replace(old, old + '''        self.view.reading_closed.connect(self._reading_closed)
''')
old = '''    def _keyboard_moved(self, old, now):'''
assert t.count(old) == 1
t = t.replace(old, '''    def _reading_closed(self):
        """The owner closed the page being read (Esc): what waited on it for a go is withdrawn from the keyboard too."""
        self.pending = None

    def _keyboard_moved(self, old, now):''')
io.open(W + 'field_page.py', 'w', encoding='utf8').write(t)

# ---- Talk: an answer read at a glance in a narrow column ---------------------------------------------------------------------
edit(W + 'shell2.py', [
('''def to_console(host, page, text):''', '''def shaped_rows(rows):
    """Rows of the shapes Stacy answers in most, written for a narrow column: a line that names the thing, then what the
    records say of it, a blank line between rows. A doubt leads with its verdict; a what-if with what it says now and what it
    would say; a trace with which way and how far. None for any other shape (the caller's own layout then stands)."""
    if not rows or not all(isinstance(row, dict) for row in rows):return None
    keys = set(rows[0])
    if any(set(row) != keys for row in rows):return None
    say = lambda value: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    out = []
    if {'verdict', 'about', 'why'} <= keys:
        for row in rows[:50]:
            head = '%s · %s' % (say(row['verdict']).upper(), say(row['about']))
            out.append((head + '\\n“%s”' % say(row['title']) if row.get('title') else head) + '\\n' + say(row['why']))
    elif {'title', 'says_now', 'would_be', 'why'} <= keys:
        for row in rows[:50]:
            now = say(row['says_now']).strip();then = say(row['would_be']).strip()
            change = ('%s  →  %s' % (now, then)) if now and then and now != then else (('%s, as now' % now) if now else then)
            out.append('%s\\n%s\\n%s' % (say(row['title']), change, say(row['why'])))
    elif {'way', 'steps', 'kind', 'title'} <= keys:
        for row in rows[:50]:
            way = say(row['way']);far = row.get('steps') if isinstance(row.get('steps'), int) else 0
            lead = '•' if way == 'this' else ('←' if way == 'from' else '→') * max(1, min(3, far))
            line = '%s %s · %s%s' % (lead, say(row['kind']), say(row['title']), (' (%s)' % say(row['state'])) if row.get('state') else '')
            out.append(line + ('\\n   by ' + say(row['by']) if row.get('by') else ''))
        return '\\n'.join(out) + ('\\n… %d more rows' % (len(rows) - 50) if len(rows) > 50 else '')
    else:
        return None
    return '\\n\\n'.join(out) + ('\\n\\n… %d more rows' % (len(rows) - 50) if len(rows) > 50 else '')


def to_console(host, page, text):'''),
('''        code = QLabel(breakable(line.replace(' | ', '\\n| ')));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(15))      # a stage a line, as her rail in the Field shows it
''', '''        # A stage a line, as her rail in the Field shows it, with long record numbers shortened for the eye as the rail does.
        # The line itself stays exact: it is what runs, what "in the line" gives, and the label's tooltip.
        code = QLabel(breakable(re.sub(r'([0-9a-f]{6})[0-9a-f]{20,}', '\\\\1…', line).replace(' | ', '\\n| ')));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(15))
        code.setToolTip(line)
'''),
('''        shown = said
        if r.get('ok') and rows and all(isinstance(row, dict) and len(row) == 1 for row in rows):''', '''        shown = said;shaped = shaped_rows(rows) if r.get('ok') else None
        if shaped is not None:                # a doubt, a what-if, a trace: each row a few short lines, made for this column
            shown = shaped
        elif r.get('ok') and rows and all(isinstance(row, dict) and len(row) == 1 for row in rows):'''),
("""                'intro': 'What if %s, on “%s”. Followed along the wires and worked exactly; nothing is changed. The Field marks what would move until Esc:' % (said, chosen.title)}
""", """                'intro': 'What if %s, on “%s”. Nothing is changed; the Field marks what would move (Esc clears):' % (said, chosen.title)}
""")])
print('ok')
