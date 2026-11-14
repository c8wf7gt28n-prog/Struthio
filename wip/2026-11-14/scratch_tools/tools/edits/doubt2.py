import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_doubt.py', [
("""    # its checks: is there one, did it pass, and could it fail at all
    checks = [c for c in sheet.get('checked', ()) if c.get('claim') == claim]
    listed = 'investigation.sheet %s | pick checked | select claim_text,program,expect,value,last_outcome' % _js(id=inv)
    if not checks:
        out.append(Doubt('cannot tell', 'a check', 'no check says what would show it true; it is recorded, not checked', listed))
    for check in checks:
        program = str(check.get('program') or '');value = str(check.get('value') or '');expect = check.get('expect')
        whole = expect in ('CONTAINS', 'NOT_CONTAINS') and ' | ' not in program
        if whole or (expect == 'CONTAINS' and value and value.lower() in program.lower()):
            said = ('its check looks for “%s” in the whole record, which also keeps the words as they were first reviewed, so it passes even if the cell is changed' % value
                    if whole else 'its check looks for “%s”, and those words are in the check’s own line, so it passes by itself' % value)
            narrow = ''
            if program.startswith('@office:'):
                got = _read(kernel, principal, 'office.get', {'id': program[len('@office:'):]}) or {}
                cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
                cell = next((name for name, cell in cells.items() if str(cell.get('value') or '').strip() == value), None)
                if cell:
                    narrow = '%s | pick document.sheets | select cells.%s.value' % (program, cell);said += '. A check narrowed to cell %s could fail' % cell
            out.append(Doubt('doubt', 'a check that can fail', said, narrow or listed))
        elif check.get('last_outcome') == 'PASSED':""",
 """    # its checks: is there one, did it pass, and could it fail at all
    checks = [c for c in sheet.get('checked', ()) if c.get('claim') == claim]
    listed = 'investigation.sheet %s | pick checked | select claim_text,program,expect,value,last_outcome' % _js(id=inv)
    if not checks:
        out.append(Doubt('cannot tell', 'a check', 'no check says what would show it true; it is recorded, not checked', listed))
    sound = [c for c in checks if weak_check(kernel, principal, c) is None]
    for check in checks:
        program = str(check.get('program') or '');weak = weak_check(kernel, principal, check)
        if weak:
            said, narrow, cell = weak
            if sound:      # an older check that cannot fail does no harm beside one that can; it cannot be removed, so it is only named
                out.append(Doubt('note', 'a check that can fail', 'an older check of it cannot fail (%s); a narrower one stands beside it' % said.split(',')[0], listed))
            else:
                out.append(Doubt('doubt', 'a check that can fail', said + ('. A check narrowed to cell %s could fail' % cell if cell else ''), narrow or listed))
        elif check.get('last_outcome') == 'PASSED':"""),
("""def _condition(kernel, principal, obj, field):""", '''def weak_check(kernel, principal, check):
    """A check that cannot fail, or None. Two ways are known. It looks for words in a whole record: a reviewed sheet's record
    also keeps the words as they were first reviewed, so the words are found whatever the cell says now. Or the words it
    looks for are in its own line, and the answer it is matched against carries that line. Returns (why, a narrowed line or
    '', the cell that line reads or '')."""
    program = str(check.get('program') or '');value = str(check.get('value') or '');expect = check.get('expect')
    whole = expect in ('CONTAINS', 'NOT_CONTAINS') and ' | ' not in program
    if not whole and not (expect == 'CONTAINS' and value and value.lower() in program.lower()):
        return None
    said = ('its check looks for “%s” in the whole record, which also keeps the words as they were first reviewed, so it passes even if the cell is changed' % value
            if whole else 'its check looks for “%s”, and those words are in the check’s own line, so it passes by itself' % value)
    if program.startswith('@office:'):
        got = _read(kernel, principal, 'office.get', {'id': program[len('@office:'):]}) or {}
        cells = ((got.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        cell = next((name for name, held in cells.items() if str(held.get('value') or '').strip() == value), None)
        if cell:
            return said, '%s | pick document.sheets | select cells.%s.value' % (program, cell), cell
    return said, '', ''


def quoted_calculation(kernel, principal, obj, field):
    """The calculation on the desk whose result a finding's words carry: (the calculation's object, the decimal as written,
    the unit), or None. A match of the number and its unit, as _claim's own "its numbers" row is."""
    for value, unit in re.findall(r'(?<![\\w.])(-?\\d+(?:\\.\\d+)?)\\s*([A-Za-zµΩ°%]+)', str(obj.title)):
        for other in field.objects:
            if other.kind != 'calculation' or not isinstance(other.target, dict):continue
            got = _read(kernel, principal, 'documents.get', {'id': other.target.get('id')}) or {}
            result = (((((got.get('document') or {}).get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
            if result.get('unit') == unit and _same(_number(result.get('decimal')), _number(value)):
                return other, str(result['decimal']), unit
    return None


def _condition(kernel, principal, obj, field):'''),
])

edit('workbench/field_do.py', [
("""    settles: bool = False   # taking it is what brings the thing back to current (so "settle the desk" may include it)
""", """    settles: bool = False   # taking it is what brings the thing back to current (so "settle the desk" may include it)
    more: tuple = ()        # further (words, line) pairs that go with it: the step is the whole list, put up together for one go
"""),
("""    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if was in obj.title and now not in obj.title), None) if finding else None""",
 """    if finding and claim and field is not None:      # what Stacy's doubt finds wrong with its checking, as steps that put it right
        from .field_doubt import quoted_calculation, weak_check
        checks = [c for c in sheet.get('checked', ()) if c.get('claim') == claim]
        registered = {row.get('address') for row in sheet.get('read', ())}
        weak = next((found for found in (weak_check(kernel, principal, c) for c in checks) if found and found[1]), None)
        if weak and all(weak_check(kernel, principal, c) is not None for c in checks):
            said, narrow, cell = weak;address = narrow.split(' | ', 1)[0].lstrip('@');value = next(str(c.get('value')) for c in checks if weak_check(kernel, principal, c))
            lines = ([('have it watch the sheet', op('investigation.add_source', id=inv, address=address))] if address not in registered else []) + [
                ('bind a check on cell %s' % cell, op('investigation.check', claim=claim, program=narrow, oracle='Cell %s still says “%s”.' % (cell, value),
                                                    expect='CONTAINS', value='"cells.%s.value": %s' % (cell, json.dumps(value, ensure_ascii=False)), refutes_on_fail=True)),
                ('run the checks that are due', op('investigation.continue', id=inv))]
            out.append(Step('Give it a check that can fail', 'write', lines[0][1], 'the check it has passes whatever the cell says; this one reads cell %s itself' % cell, 'execute', more=tuple(lines[1:])))
            out[-1].words_first = lines[0][0]
        elif not checks:
            quoted = quoted_calculation(kernel, principal, obj, field)
            if quoted:
                calc, decimal, unit = quoted;address = calc.id;record = calc.target['id']
                lines = ([('have it watch “%s”' % calc.title, op('investigation.add_source', id=inv, address=address))] if address not in registered else []) + [
                    ('bind a check on its result', op('investigation.check', claim=claim,
                                                     program='documents.get %s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % js(id=record),
                                                     oracle='“%s” gives %s %s.' % (calc.title, decimal, unit), expect='CONTAINS', value='"value.decimal": "%s"' % decimal, refutes_on_fail=True)),
                    ('run the checks that are due', op('investigation.continue', id=inv))]
                out.append(Step('Check it against “%s”' % calc.title, 'write', lines[0][1], 'it says %s %s, which is that calculation’s result; the check holds it to that' % (decimal, unit), 'execute', more=tuple(lines[1:])))
                out[-1].words_first = lines[0][0]
    quoted = next(((was, now, name) for was, now, name in (field.moved if field is not None else ()) if was in obj.title and now not in obj.title), None) if finding else None"""),
])

edit('workbench/field_page.py', [
("""    else:
        done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
        card = face.stage(obj.title, step, done=done)
        _await_go(host, step.words[:1].lower() + step.words[1:], lambda:face.run_staged(card, done))""",
 """    elif step.more:                            # a step that is several changes: put up together, named, for one go
        from .field_do import Step
        parts = [(obj, Step(getattr(step, 'words_first', step.words), 'write', step.line))] + [(obj, Step(words, 'write', line)) for words, line in step.more]
        done = lambda results, obj=obj:_after(host, obj, any(ok for _, ok, _ in results), None)
        card = face.say_plan(parts, done=done, title='For “%s”: %s. That is %d changes.' % (obj.title, step.words[:1].lower() + step.words[1:], len(parts)))
        _await_go(host, 'all %d changes, as listed in Talk' % len(parts), lambda:face.run_plan(card, done))
    else:
        done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
        card = face.stage(obj.title, step, done=done)
        _await_go(host, step.words[:1].lower() + step.words[1:], lambda:face.run_staged(card, done))"""),
])
edit('workbench/shell2.py', [
("""    def say_plan(self, plan, done=None):""", """    def say_plan(self, plan, done=None, title=None):"""),
("""        card = self.say('To settle the desk I would make %d change%s. One Run does them in order, as written here, and stops at the first that is refused.' % (len(plan), '' if len(plan) == 1 else 's'))
        card.rows = []""", """        card = self.say((title or 'To settle the desk I would make %d change%s.' % (len(plan), '' if len(plan) == 1 else 's'))
                        + ' One Run does them in order, as written here, and stops at the first that is refused.')
        card.rows = []"""),
("""        if r.get('ok') and len(rows) > 1 and all(isinstance(row, dict) and len(row) >= 4 for row in rows):""",
 """        if r.get('ok') and len(rows) > 1 and all(isinstance(row, dict) and len(row) >= 3 for row in rows):"""),
])
print('edits applied')
