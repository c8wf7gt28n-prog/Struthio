import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:70])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)

edit('/home/user/Struthio/workbench/shell2.py', [('''    def what_if(self, text):
        """“What if B3 were 320?”, asked while a calculation is selected in the Field: the calculation's own recipe worked with
        that value, exactly, changing nothing (field.whatif, a read). The inputs are named by their cell, their symbol or
        their words; several go together with "and". Returns the thing to answer about, a dict with 'refusal' when the
        question is a what-if but names no input of this calculation, or None when it is not a what-if about a calculation."""
        asked = re.match(r'^\\s*what\\s+if\\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind != 'calculation' or not isinstance(chosen.target, dict):return None
        got = call(self.host, 'documents.get', {'id': chosen.target.get('id')}) or {}
        inputs = ((got.get('document') or {}).get('derivation') or {}).get('inputs') or []
        if not inputs:return None
        names = {}
        for item in inputs:
            for name in (str(item['cell']), str(item['symbol']), str(item['symbol']).replace('_', ' '), str(item.get('parameter') or '')):
                if name.strip():names[name.strip().lower()] = item['cell']
''', '''    def what_if(self, text):
        """“What if B3 were 320?”, asked while a sheet or a calculation is selected in the Field: that cell set to that value
        and followed along the wires, changing nothing (field.ripple, a read). Every calculation that reads the cell is worked
        again exactly with its own recipe; every finding, page and check that would move is named, and the Field marks them
        until Esc. A cell is named by its address, by its row's words, or (for a calculation) by its symbol; several go
        together with "and". Returns the thing to answer about, a dict with 'refusal' when the question is a what-if but
        names no number of this sheet, or None when it is not a what-if about a sheet or a calculation."""
        asked = re.match(r'^\\s*what\\s+if\\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind not in ('calculation', 'sheet') or not isinstance(chosen.target, dict):return None
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_ripple import cells_named
        _, names = cells_named(engineering(self.host.root), operator(), chosen)
        if not names:return None
        inputs = []
        if chosen.kind == 'calculation':
            got = call(self.host, 'documents.get', {'id': chosen.target.get('id')}) or {}
            inputs = ((got.get('document') or {}).get('derivation') or {}).get('inputs') or []
'''), ('''        said = ', '.join('%s (%s, in %s)' % (i['cell'], i.get('parameter') or i['symbol'], i['unit']) for i in inputs)
        if not setting:
            return {'refusal': 'Say which input and its new value, for example “what if %s were” and a number. This calculation reads %s.' % (inputs[-1]['cell'], said)}
        from .field_do import js
        from .field_page import thing_of
        return {**thing_of(self.host, chosen), 'stac': 'field.whatif %s | select says_now,would_be,exact,set,changed' % js(id=chosen.id, set=setting),
                'explicit': True, 'intro': 'What if, for “%s”. Worked exactly with its own recipe; nothing is changed:' % chosen.title}
''', '''        if not setting:
            if inputs:
                said = ', '.join('%s (%s, in %s)' % (i['cell'], i.get('parameter') or i['symbol'], i['unit']) for i in inputs)
                return {'refusal': 'Say which input and its new value, for example “what if %s were” and a number. This calculation reads %s.' % (inputs[-1]['cell'], said)}
            cells = sorted({cell for cell in names.values()}, key=lambda cell: (len(cell), cell))
            return {'refusal': 'Say which cell and its new value, for example “what if %s were” and a number. The numbers of this sheet are in %s.' % (cells[-1], ', '.join(cells[:12]))}
        from .field_do import js
        from .field_page import show_would, thing_of
        said = ', '.join('%s = %s' % pair for pair in setting.items())
        show_would(self.host, chosen.id, setting, said)
        return {**thing_of(self.host, chosen), 'stac': 'field.ripple %s | pick rows | select way,kind,title,says_now,would_be,why' % js(id=chosen.id, set=setting),
                'explicit': True, 'whole': True,
                'intro': 'What if %s, on “%s”. Followed along the wires and worked exactly; nothing is changed. The Field marks what would move until Esc:' % (said, chosen.title)}
''')])

edit('/home/user/Struthio/workbench/field_page.py', [('''        self.view.doubt_asked.connect(lambda obj: doubt(self.host, obj))
''', '''        self.view.doubt_asked.connect(lambda obj: doubt(self.host, obj))
        self.view.brief_asked.connect(lambda: brief(self.host))
'''), ('''def full_window(host, obj):
    """F on the shelf: this program in its full window.''', '''def show_would(host, ident, setting, said):
    """A what-if, shown on the Field: the sheets that would move carry what they would say, in amber, until Esc or the next
    reading. The same read Stacy shows in Talk (field.ripple); a refusal marks nothing."""
    from .engineering_kernel import operator
    from .field_ripple import marks
    page = getattr(host, 'field_page', None);kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if page is None or kernel is None:return {}
    answer = kernel.dispatch('field.ripple', {'id': ident, 'set': setting}, operator())
    page.view.would = marks(answer['result']) if answer.get('ok') else {}
    page.view.would_said = ('what if ' + said) if page.view.would else ''
    page.view.update()
    return page.view.would


def full_window(host, obj):
    """F on the shelf: this program in its full window.''')])
print('ok')
