import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

# ---- field.set: one number of a sheet changed, as an operation that waits for the owner ------------------------------------
edit(W + 'field_service.py', [
('''  field.brief.keep  execute  {shown?}   the brief written as a page in Documents; a later one takes its place. `shown` is
                                        the fingerprint field.brief gave: with it, nothing is kept if the desk has changed since
''', '''  field.brief.keep  execute  {shown?}   the brief written as a page in Documents; a later one takes its place. `shown` is
                                        the fingerprint field.brief gave: with it, nothing is kept if the desk has changed since
  field.set         execute  {id, cell, value, expected_revision}
                                        one number of a sheet set to another value and the sheet saved. The what-if made real:
                                        field.ripple with the same cell and value says beforehand what it will move. Refused
                                        when the sheet has been saved since `expected_revision` was read.
'''),
('''    'field.brief.keep': ({'shown': {'type': 'string', 'minLength': 64, 'maxLength': 64}}, []),
}
WRITES = ('field.brief.keep',)
''', '''    'field.brief.keep': ({'shown': {'type': 'string', 'minLength': 64, 'maxLength': 64}}, []),
    'field.set': ({'id': TEXT, 'cell': {'type': 'string', 'minLength': 2, 'maxLength': 8}, 'value': {'type': 'string', 'minLength': 1, 'maxLength': 40},
                   'expected_revision': {'type': 'string', 'minLength': 64, 'maxLength': 64}}, ['id', 'cell', 'value', 'expected_revision']),
}
WRITES = ('field.brief.keep', 'field.set')
'''),
('''def dispatch(kernel, operation, args, principal):
    if operation == 'field.brief':return brief(kernel, principal)
''', '''def set_cell(kernel, principal, ident, cell, value, expected):
    """One number of a sheet set to another value, and the sheet saved through the Office's own save (its rules are the
    rules: the revision that was read must still be the sheet's). Only a number takes a number; the cell keeps its unit.
    Everything worked from the sheet then waits for a recheck, as after any saved change."""
    import re
    from decimal import Decimal, InvalidOperation
    record = ident[len('office:'):] if ident.startswith('office:') else ident;cell = str(cell).strip().upper()
    answer = kernel.dispatch('office.get', {'id': record}, principal)
    if not answer.get('ok'):
        raise ValueError('That sheet cannot be read: ' + str((answer.get('error') or {}).get('message'))[:160])
    got = answer['result'];document = got['document']
    if got.get('revision') != expected:
        raise ValueError('The sheet was saved again after this change was put up, so nothing was changed. Ask again to see it as it is now.')
    cells = (document.get('sheets') or [{}])[0].get('cells') or {};held = cells.get(cell)
    if not re.fullmatch(r'[A-Z]{1,3}[0-9]{1,5}', cell) or held is None:
        raise ValueError('%s is not a cell of “%s”' % (cell[:8], str(document.get('title'))[:60]))
    try:
        was = Decimal(str(held.get('value')).strip());now = Decimal(str(value).strip().replace(',', ''))
        if str(held.get('type')) == 'text' or not was.is_finite() or not now.is_finite():raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise ValueError('%s holds %s; only a number can be set to a number here' % (cell, 'words' if str((held or {}).get('type')) == 'text' else 'no plain number')) from None
    if was == now:
        raise ValueError('%s already says %s' % (cell, held.get('value')))
    cells[cell] = {**held, 'value': str(value).strip().replace(',', '')}
    saved = kernel.dispatch('office.save', {'id': record, 'expected_revision': expected, 'document': document}, principal)
    if not saved.get('ok'):
        raise ValueError('The sheet was not saved: ' + str((saved.get('error') or {}).get('message'))[:200])
    unit = str(held.get('unit') or '').strip()
    return {'schema': SCHEMA, 'id': 'office:' + record, 'cell': cell, 'was': str(held.get('value')), 'now': cells[cell]['value'], 'unit': unit,
            'revision': (saved['result'] or {}).get('revision'),
            'words': '%s of “%s” now says %s%s (it said %s). What was worked from this sheet waits for a recheck: C checks the desk.' % (
                cell, document.get('title'), cells[cell]['value'], ' ' + unit if unit else '', held.get('value'))}


def dispatch(kernel, operation, args, principal):
    if operation == 'field.set':return set_cell(kernel, principal, args['id'], args['cell'], args['value'], args['expected_revision'])
    if operation == 'field.brief':return brief(kernel, principal)
''')])

# ---- the page: the menu by a click; a change of one number put up for approval ------------------------------------------------
edit(W + 'field_page.py', [
('''        self.view.reading_closed.connect(self._reading_closed)
''', '''        self.view.reading_closed.connect(self._reading_closed)
        self.view.menu_asked.connect(self._menu)
'''),
('''    def _reading_closed(self):''', '''    def _menu(self):
        """A click on "Menu" at the foot: the selected sheet's own menu, as the Menu key and the right button open it."""
        from . import context_menu
        self.view.setFocus(Qt.OtherFocusReason)
        context_menu.open_at_focus(self.host)

    def _reading_closed(self):'''),
('''def show_would(host, ident, setting, said):''', '''def stage_set(host, obj, cell, value):
    """“Set B3 to 300”, asked of Stacy with a sheet (or a calculation, which stands for its sheet) selected: the change is
    put up with its exact line and waits for Approve, and meanwhile the Field marks what it would move, as a what-if does.
    Approving saves the sheet through the same operation the owner's own edit uses; then the records are read again."""
    from .engineering_kernel import operator
    from .field_do import Step, op
    from .field_ripple import cells_named
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None);face = _talk(host)
    if kernel is None or face is None:return None
    sheet, _ = cells_named(kernel, operator(), obj)
    got = kernel.dispatch('office.get', {'id': sheet}, operator()) if sheet else {'ok': False}
    if not got.get('ok'):
        face.say('I cannot read the sheet that number is on, so I have not put a change up.');return None
    held = ((got['result']['document'].get('sheets') or [{}])[0].get('cells') or {}).get(cell) or {}
    title = str(got['result']['document'].get('title') or 'the sheet');unit = str(held.get('unit') or '').strip()
    words = 'Set %s to %s%s' % (cell, value, ' ' + unit if unit else '')
    show_would(host, 'office:' + str(sheet), {cell: value}, '%s = %s' % (cell, value))
    step = Step(words, 'write', op('field.set', id='office:' + str(sheet), cell=cell, value=value, expected_revision=got['result']['revision']),
                '%s says %s%s now. The sheet is saved with the new value and everything worked from it waits for a recheck; the Field marks what would move' % (
                    cell, held.get('value'), ' ' + unit if unit else ''), 'execute')
    done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
    card = face.stage(title, step, done=done)
    _await_go(host, '%s on “%s”' % (words[:1].lower() + words[1:], title), lambda:face.run_staged(card, done))
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def show_would(host, ident, setting, said):''')])

# ---- Talk: "set B3 to 300", and the button that approves is called Approve ----------------------------------------------------
edit(W + 'shell2.py', [
('''        row = QHBoxLayout();run = button('Run', 'stac');run.setObjectName('StagedRun');row.addWidget(run)
''', '''        row = QHBoxLayout();run = button('Approve', 'stac');run.setObjectName('StagedRun');row.addWidget(run)
        run.setToolTip('Apply this change. Nothing is changed until you do; in the Field, G does the same')
'''),
('''        card.ran = bool(r.get('ok'));card.run.setEnabled(False);card.run.setText('Ran' if card.ran else 'Refused')
''', '''        card.ran = bool(r.get('ok'));card.run.setEnabled(False);card.run.setText('Approved' if card.ran else 'Refused')
'''),
('''        row = QHBoxLayout();run = button('Run all %d' % len(plan) if len(plan) > 1 else 'Run', 'stac');run.setObjectName('PlanRun');row.addWidget(run);row.addStretch(1);card.box.addLayout(row)
''', '''        row = QHBoxLayout();run = button('Approve all %d' % len(plan) if len(plan) > 1 else 'Approve', 'stac');run.setObjectName('PlanRun');row.addWidget(run);row.addStretch(1);card.box.addLayout(row)
        run.setToolTip('Apply these changes in the order listed, stopping at the first that is refused. Nothing is changed until you do; in the Field, G does the same')
'''),
('''    def ask(self, text, about=None):
        if self.own_word(text):return
''', '''    def set_asked(self, text):
        """“Set B3 to 300”, “change the settled current to 300”, “make B3 300”: asked with a sheet or a calculation selected
        in the Field. The change is put up for approval (workbench/field_page.py, stage_set); nothing is changed by asking.
        True when the line was such a request, whether or not a change could be put up."""
        asked = re.match(r'^\\s*(?:set|change|make)\\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind not in ('calculation', 'sheet') or not isinstance(chosen.target, dict):return False
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_ripple import cells_named
        _, names = cells_named(engineering(self.host.root), operator(), chosen)
        tokens = asked.group(1).replace('=', ' ').replace('?', ' ').split()
        at = next((i for i in range(len(tokens) - 1, -1, -1) if re.fullmatch(r'-?\\d+(?:\\.\\d+)?', tokens[i])), None)
        if not names or at is None:return False
        filler = {'the', 'a', 'an', 'is', 'to', 'be', 'at', 'of', 'cell', 'value', 'in', 'it', 'its', 'equal', 'equals'}
        name = ' '.join(t for t in tokens[:at] if t.lower() not in filler).lower()
        cell = names.get(name) or next((c for n, c in names.items() if name and all(word in n.split() for word in name.split())), None)
        self.thing = None;self.mine(text)
        if cell is None:
            cells = sorted({c for c in names.values()}, key=lambda c: (len(c), c))
            self.say('Say which number and its new value, for example “set %s to” and a number. The numbers here are in %s.' % (cells[-1], ', '.join(cells[:12])));return True
        from .field_page import stage_set
        stage_set(self.host, chosen, cell, tokens[at])
        return True

    def ask(self, text, about=None):
        if self.own_word(text):return
        if self.set_asked(text):return
''')])
edit(W + 'workspace_tabs.py', [('''        self.setCornerWidget(self.pin_button,Qt.TopRightCorner)
''', '''        self.setCornerWidget(self.pin_button,Qt.TopRightCorner)
        # Back to the Field, in the same place whatever is open: a click here is F9 (the Field keeps the tile and the view it was left with).
        self.field_button=QPushButton('‹ Field')
        self.field_button.setToolTip('Back to the Field: your work as tiles and wires, at the tile you opened this from (F9)')
        self.field_button.setAccessibleName('Back to the Field')
        self.field_button.clicked.connect(lambda:host.a_field.trigger() if hasattr(host,'a_field') else None)
        self.setCornerWidget(self.field_button,Qt.TopLeftCorner)
''')])
print('ok')
