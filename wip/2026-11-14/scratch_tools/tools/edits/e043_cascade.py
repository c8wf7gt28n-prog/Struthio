import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

# ---- two faults of my own, found reading it again -----------------------------------------------------------------------
edit(W + 'field_doubt.py', [('''            named = any(word in label(run[u]).lower() for word in ('total', 'sum', 'subtotal'))
''', '''            named = re.search(r'\\b(sub-?total|total|sum)\\b', label(run[u]), re.IGNORECASE) is not None      # the word itself: "Consumption" is not a sum
''')])
edit(W + 'field_ripple.py', [('''        if _decimal(value) is None:
            raise ValueError('%s needs a plain number%s' % (cell, (', in ' + unit_of(cells, cell)) if unit_of(cells, cell) else ''))
''', '''        if str((cells.get(cell) or {}).get('type') or '') == 'text' or _decimal((cells.get(cell) or {}).get('value')) is None:
            raise ValueError('%s holds words, not a number: a what-if sets a number' % cell)
        if _decimal(value) is None:
            raise ValueError('%s needs a plain number%s' % (cell, (', in ' + unit_of(cells, cell)) if unit_of(cells, cell) else ''))
''')])

# ---- the right-click cascade for the Field ---------------------------------------------------------------------------------
edit(W + 'context_menu.py', [('''def field_entries(host, t):
    """The Field (workbench/field_page.py): the instruments for the selected sheet,''', '''def _plain_number(value):
    text = format(value.normalize(), 'f') if value == value.to_integral_value() else format(value, 'f').rstrip('0').rstrip('.')
    return text if text not in ('', '-0') else '0'


def field_whatif_rows(host, obj):
    """What if ▸: one row for each number of the sheet (or each input of the calculation), with its cell, its words and its
    value; under each, the values worth trying. Choosing one asks Stacy the what-if (a read: nothing is changed), and the
    Field marks what would move. "Another value…" puts the question in the writing line to finish."""
    from decimal import Decimal, InvalidOperation
    from .engine import engineering
    from .engineering_kernel import operator
    from .field_doubt import unit_of
    from .field_ripple import _label, cells_named
    kernel = engineering(host.root);sheet, names = cells_named(kernel, operator(), obj)
    got = kernel.dispatch('office.get', {'id': sheet}, operator()) if sheet else {}
    if not got.get('ok') or not names:
        return [Entry('field:whatif:none', 'It has no number to set', 'capability', enabled=False, reason='A what-if sets a number of a sheet, or an input of a calculation')]
    cells = ((got['result'].get('document') or {}).get('sheets') or [{}])[0].get('cells') or {};out = []
    for cell in sorted(set(names.values()), key=lambda name: (len(name), name))[:24]:
        value = str((cells.get(cell) or {}).get('value') or '').strip();unit = unit_of(cells, cell);said = _label(cells, cell)
        try:
            number = Decimal(value)
        except (InvalidOperation, ValueError):
            continue
        def tries(cell=cell, number=number, unit=unit):
            rows = []
            for key, words, factor in (('more', '10 % more', Decimal('1.1')), ('less', '10 % less', Decimal('0.9')), ('twice', 'Twice', Decimal(2)), ('half', 'Half', Decimal('0.5'))):
                new = _plain_number(number * factor)
                rows.append(Entry('field:whatif:%s:%s' % (cell, key), ('%s · %s %s' % (words, new, unit)).strip(), 'command',
                                  lambda new=new: host.shell2.ask('what if %s were %s' % (cell, new)), icon='line', operation='field.ripple',
                                  tip='A read: nothing is changed. Stacy follows the wires and the Field marks what would move, until Esc'))
            rows.append(Entry('field:whatif:%s:other' % cell, 'Another value…', 'command', lambda: ask_graphite(host, 'what if %s were ' % cell), icon='ask',
                              tip='The question in the writing line for you to finish; Enter asks'))
            return rows
        out.append(Entry('field:whatif:' + cell, short(' · '.join(part for part in (cell, said, ('%s %s' % (value, unit)).strip()) if part), 58), 'command', icon='line', submenu=tries))
    return out or [Entry('field:whatif:none', 'It has no number to set', 'capability', enabled=False, reason='A what-if sets a number of a sheet, or an input of a calculation')]


def field_step_rows(host, view, obj):
    """What can be done ▸: the steps the records offer for this sheet, as D shows them. A read runs at once and Stacy shows
    its line and the answer; a step that changes something is put up in Talk and waits for G. Choosing here never approves."""
    from . import field_page
    from .engine import engineering
    from .engineering_kernel import operator
    from .field_do import steps_for
    steps = steps_for(engineering(host.root), operator(), obj, view.field)
    def take(line):
        offered = field_page.do(host, obj)         # the same steps D shows, read now; the one chosen is found by its exact line
        at = next((n for n, step in enumerate(offered) if step.line == line), None)
        if at is not None:field_page.take(host, obj, at)
    return [Entry('field:do:%d' % n, short(step.words, 56), 'command', lambda line=step.line: take(line), icon='line', caption='asks' if step.kind == 'write' else '',
                  tip=((step.why[:1].upper() + step.why[1:] + '.\\n') if step.why else '') + ('It changes something: it is put up in Talk and waits for your go (G).' if step.kind == 'write' else 'A read: it runs at once.') + '\\n' + step.line[:300])
            for n, step in enumerate(steps)] or [Entry('field:do:none', 'The records offer nothing to do about this', 'capability', enabled=False)]


def field_doubt_rows(host, view, obj):
    """Doubt it ▸: what Stacy finds when she cross-examines this, right in the menu, worst first. A row's reason is its tooltip;
    choosing a row shows the read that is its evidence, in Talk. The first row is the whole of it in Talk (X)."""
    from .engine import engineering
    from .engineering_kernel import operator
    answer = engineering(host.root).dispatch('field.doubt', {'id': obj.id}, operator())
    out = [Entry('field:doubt:all', 'All of it, in Talk', 'command', lambda: view.doubt_asked.emit(obj), icon='ask', caption='X')]
    if not answer.get('ok'):
        return out + [Entry('field:doubt:problem', 'It could not be looked at', 'capability', enabled=False, reason=str((answer.get('error') or {}).get('message'))[:200])]
    def show(row):
        face = getattr(getattr(host, 'shell2', None), 'show_slate_face', lambda: None)()
        if face is not None and row.get('see'):
            face.answer_in_stac({'title': obj.title, 'stac': row['see'], 'kind': obj.kind}, '%s: %s. The read that shows it:' % (row['about'][:1].upper() + row['about'][1:], row['why']))
        view.setFocus(Qt.OtherFocusReason)
    for n, row in enumerate(answer['result'].get('rows', ())[:16]):
        out.append(Entry('field:doubt:%d' % n, short('%s · %s' % (row['verdict'], row['about']), 58), 'state', (lambda row=row: show(row)) if row.get('see') else None,
                         icon='line', enabled=bool(row.get('see')), reason='' if row.get('see') else row['why'], tip=row['why'] + ('\\nChoose it to see the read that shows this.' if row.get('see') else '')))
    return out


def field_trace_rows(host, view, obj, select):
    """Trace it ▸: where this comes from, farthest first, then what rests on it; choosing a row goes to that sheet. The first
    row tells the whole trace in Talk (T)."""
    from .engine import engineering
    from .engineering_kernel import operator
    answer = engineering(host.root).dispatch('field.trace', {'id': obj.id}, operator())
    out = [Entry('field:trace:all', 'The whole trace, in Talk', 'command', lambda: view.trace_asked.emit(obj), icon='ask', caption='T')]
    for row in (answer['result'].get('rows', ()) if answer.get('ok') else ()):
        if row['way'] == 'this':continue
        out.append(Entry('field:trace:' + row['id'], short(('← ' if row['way'] == 'from' else '→ ') + str(row['title']), 56), 'state', lambda ident=row['id']: select(ident),
                         caption=str(row['kind']), tip='%s, %d step%s %s%s' % (row['kind'], row['steps'], '' if row['steps'] == 1 else 's', 'back' if row['way'] == 'from' else 'on',
                                                                             (' · by ' + row['by']) if row.get('by') else '')))
    if len(out) == 1:
        out.append(Entry('field:trace:none', 'Nothing is wired to it', 'capability', enabled=False))
    return out


def word_rows(host, manage=False):
    """Your words ▸: the owner's own staC words (workbench/stac_words.py). On a sheet, choosing one runs it in Talk, and a word
    whose line starts with `this` reads the selected sheet. On the Field's own menu each word also goes to the line or is
    forgotten, and a new one can be started."""
    from .stac_words import known_to
    words = known_to(host, fresh=True);out = []
    for name, line in sorted(words.items()):
        run = lambda name=name: host.shell2.ask(name)
        if manage:
            out.append(Entry('words:' + name, name, 'command', icon='line', tip=line, submenu=lambda name=name, line=line, run=run: [
                Entry('words:%s:run' % name, 'Run it', 'command', run, icon='line', operation='language.run', tip=line),
                Entry('words:%s:line' % name, 'In the line', 'command', lambda: inspect_in_line(host, name), icon='line', tip='The word in the writing line, to go on from: ' + name + ' | …'),
                Entry('words:%s:forget' % name, 'Forget it', 'edit', lambda: inspect_in_line(host, 'forget ' + name), icon='line', tip='Puts “forget %s” in the line; Ctrl+Enter lets the word go' % name)]))
        else:
            out.append(Entry('words:' + name, name, 'command', run, icon='line', operation='language.run', tip=line))
    if manage or not out:
        out.append(Entry('words:new', 'Keep a new word…', 'edit', lambda: inspect_in_line(host, 'word '), icon='line',
                         tip='In the line: word NAME = a staC line. Ctrl+Enter keeps it; then the word is the line'))
    return out


def field_entries(host, t):
    """The Field (workbench/field_page.py): the instruments for the selected sheet,'''),
('''        out.append(Entry('field:stac', 'This face in staC', 'command', icon='line', tip='Read-only staC lines for what the Field shows; each goes to the writing strip',
                         submenu=lambda:[Entry('field:stac:%d' % n, label, 'command', lambda code=code:inspect_in_line(host, code), icon='line', tip=code)
                                         for n, (label, code) in enumerate(lines)]))
        return out
''', '''        out.append(Entry('field:stac', 'This face in staC', 'command', icon='line', tip='Read-only staC lines for what the Field shows; each goes to the writing strip',
                         submenu=lambda:[Entry('field:stac:%d' % n, label, 'command', lambda code=code:inspect_in_line(host, code), icon='line', tip=code)
                                         for n, (label, code) in enumerate(lines)]))
        out.append(Entry('field:words', 'Your words', 'command', icon='line', submenu=lambda:word_rows(host, manage=True),
                         tip='staC lines you keep under words of your own: run one, put it in the line, forget it, or keep a new one'))
        return out
'''),
('''    out.append(Entry('field:doubt', 'Doubt it', 'command', lambda:view.doubt_asked.emit(obj), icon='line', caption='X',
                     tip='Cross-examine it for what a plausible result may hide: what does not hold, what cannot be told, what holds'))
    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',
                     tip='Where it comes from and what rests on it, hop by hop along the wires'))
    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     tip='The steps the records offer for this. A read runs at once; one that changes something asks first'))
''', '''    work = view.face == 'work'
    if work and obj.kind in ('sheet', 'calculation'):      # the cascade for looking ahead: a number, then a value to try
        out.append(Entry('field:whatif', 'What if', 'command', icon='line', submenu=lambda:field_whatif_rows(host, obj),
                         tip='Set one of its numbers to another value without changing anything: the wires are followed and the Field marks what would move'))
    out.append(Entry('field:doubt', 'Doubt it', 'command', lambda:view.doubt_asked.emit(obj), icon='line', caption='X',
                     submenu=(lambda:field_doubt_rows(host, view, obj)) if work else None,
                     tip='Cross-examine it for what a plausible result may hide: what does not hold, what cannot be told, what holds (X shows all of it in Talk)'))
    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',
                     submenu=(lambda:field_trace_rows(host, view, obj, select)) if work else None,
                     tip='Where it comes from and what rests on it, hop by hop along the wires; choose one to go there (T tells it in Talk)'))
    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     submenu=lambda:field_step_rows(host, view, obj),
                     tip='The steps the records offer for this. A read runs at once; one that changes something is put up and waits for your go (D shows them in the Field)'))
    if work and obj.stac:
        out.append(Entry('field:words', 'Your words', 'command', icon='line', submenu=lambda:word_rows(host),
                         tip='Run one of your own staC words here; a word whose line starts with `this` reads this sheet'))
''')])
print('ok')
