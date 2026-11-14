import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:70])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_ripple.py', [('''    weak = weak_check(kernel, principal, check)
    if weak:
        carried = [cell for cell in setting if value and str((cells.get(cell) or {}).get('value') or '').strip() == value.strip()]
        if carried and ' | ' not in program:
            return 'would still pass', 'it looks for “%s” in the whole record, which keeps the words as they were first reviewed: it would not notice %s changing' % (value, ', '.join(carried))
        return 'would still pass', 'it is a check that cannot fail (%s)' % weak[0].split(',')[0]
''', '''    weak = weak_check(kernel, principal, check)
    if weak:
        if ' | ' not in program:
            return 'would still pass', 'it looks for “%s” in the whole record, which keeps the words as they were first reviewed: it would go on passing and not notice this change' % value
        return 'would still pass', 'it is a check that cannot fail (%s)' % weak[0].split(',')[0]
'''), ('''        for name, held in sorted(cells.items(), key=lambda pair: (len(pair[0]), pair[0])):      # column B before E: a row's words name its first number
            if str((held or {}).get('type') or '') == 'text' or _decimal((held or {}).get('value')) is None:continue
''', '''        numbers = [name for name, held in cells.items() if str((held or {}).get('type') or '') != 'text' and _decimal((held or {}).get('value')) is not None]
        measured = [name for name in numbers if _unit(cells, str(name))]       # on a sheet that gives units, a number without one is a page number or a count, not a value
        for name in sorted(measured or numbers, key=lambda name: (len(name), name)):      # column B before E: a row's words name its first number
            held = cells[name]
''')])
edit(W + 'field_brief.py', [('''        add('stands', '%s — %s%s' % (str(obj.title).rstrip(), '; '.join(holds) or 'nothing the records hold says why',
''', '''        add('stands', '%s — %s%s' % (str(obj.title).rstrip(), '; '.join(holds) or next((str(line) for line in obj.lines if line), 'it is recorded as standing'),
'''), ('''        _plural(len(things), 'thing'), ', '.join(_plural(count, KIND_WORD.get(kind, kind)) for kind, count in census.items()) or 'nothing yet',
''', '''        _plural(len(things), 'thing'), ', '.join(_plural(census[kind], KIND_WORD.get(kind, kind)) for kind in sorted(census, key=lambda kind: (list(KIND_WORD).index(kind) if kind in KIND_WORD else 99))) or 'nothing yet',
''')])
print('ok')
