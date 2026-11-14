import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'

# ---- what_if: two inputs on one cell are both set when the cell is named -------------------------------------------------
edit(W + 'datasheet_work.py', [('''    recipe = derivation['recipe'];named = {}
    for item in derivation['inputs']:
        named[str(item['symbol']).lower()] = item;named[str(item['cell']).lower()] = item
    setting = {}
    for key, value in changes.items():
        item = named.get(str(key).strip().lower())
        if item is None:
            raise ValueError('%s is not an input of this calculation. Its inputs are %s.' % (
                str(key)[:40], ', '.join('%s (%s)' % (i['symbol'], i['cell']) for i in derivation['inputs'])))
        try:
            math_units.rational(str(value).strip())
        except Exception:  # noqa: BLE001 - whatever the number parser says, the owner is told the same plain thing
            raise ValueError('%s needs a plain number, in %s' % (item['symbol'], item['unit'])) from None
        setting[item['symbol']] = str(value).strip()
''', '''    recipe = derivation['recipe'];by_symbol = {};by_cell = {}
    for item in derivation['inputs']:
        by_symbol[str(item['symbol']).lower()] = [item];by_cell.setdefault(str(item['cell']).lower(), []).append(item)
    setting = {}
    for key, value in changes.items():
        # A symbol names one input. A cell names every input that reads it: two symbols on one cell move together.
        items = by_symbol.get(str(key).strip().lower()) or by_cell.get(str(key).strip().lower())
        if not items:
            raise ValueError('%s is not an input of this calculation. Its inputs are %s.' % (
                str(key)[:40], ', '.join('%s (%s)' % (i['symbol'], i['cell']) for i in derivation['inputs'])))
        try:
            math_units.rational(str(value).strip())
        except Exception:  # noqa: BLE001 - whatever the number parser says, the owner is told the same plain thing
            raise ValueError('%s needs a plain number, in %s' % (items[0]['symbol'], items[0]['unit'])) from None
        for item in items:setting[item['symbol']] = str(value).strip()
''')])

# ---- words that carry a number: whole numbers only ("13.36 W" does not carry "3.36 W") -----------------------------------
edit(W + 'field_model.py', [('''LATELY = 12 * 3600                       # "lately": the last twelve hours, a working day's reach
''', '''LATELY = 12 * 3600                       # "lately": the last twelve hours, a working day's reach


def carries(text, words):
    """Whether a text says these words as a whole number with its unit: "3.36 W" is carried by "is 3.36 W." and not by
    "13.36 W" or "3.36 Wh". The match of words that says a finding still quotes an old result."""
    import re
    return bool(words) and re.search(r'(?<![\\w.])' + re.escape(str(words)) + r'(?![\\w])', str(text)) is not None


def rewritten(text, was, now):
    """The text with one number put in the place of another, where it is carried whole."""
    import re
    return re.sub(r'(?<![\\w.])' + re.escape(str(was)) + r'(?![\\w])', lambda _: str(now), str(text))
''')])
edit(W + 'field_source.py', [('''            if was in obj.title and now not in obj.title:
                obj.state = STATE_RECHECK''', '''            if carries(obj.title, was) and not carries(obj.title, now):
                obj.state = STATE_RECHECK''')])
t = io.open(W + 'field_source.py', encoding='utf8').read()
assert 'from .field_model import' in t
import re
m = re.search(r'from \.field_model import ([^\n]+)\n', t)
print('field_source imports:', m.group(1)[:200])
