# a doubt and the step that removes it: the check that cannot fail is replaced by one that can, and then it does fail when the cell changes
import json, copy
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def op(name, args=None):
    r = k.dispatch(name, args or {}, p); return r['result'] if r['ok'] else {'REFUSED': r['error']['message']}
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=8): return [l.text().replace('​', '')[:260].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
def rows(ident): return [(r_['verdict'], r_['about'], r_['why'][:110]) for r_ in op('field.doubt', {'id': ident})['rows']]
def find(words): return next(o for o in v.field.objects if words in o.title)
def pick(words):
    o = find(words); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2); return o
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
f = pick('keeps the 80 ms'); print('before:'); [print('   ', r_) for r_ in rows(f.id)]
QTest.keyClick(v, Qt.Key_D); settle(60, 4); print('D ->', [(s.words, s.kind, len(s.more)) for s in page.steps])
n = next(i for i, s in enumerate(page.steps) if s.words.startswith('Give it a check'))
QTest.keyClick(v, Qt.Key_1 + n); settle(80, 4); c = cards()[-1]; print('%d -> put up, go offered: %r' % (n + 1, v.go))
for line in said(c, 7): print('   |', line[:230])
save('Graphite_Doubt_03_The_Step_That_Removes_It_%s.png' % tag)
QTest.keyClick(v, Qt.Key_G); settle(250, 6); print('G -> ran:', [(ok, (res.get('ran') if isinstance(res, dict) else res) if not ok or (isinstance(res, dict) and 'ran' in res) else 'done') for _, ok, res in c.results])
f = find('keeps the 80 ms'); print('after:', f.state); [print('   ', r_) for r_ in rows(f.id)]
# now the trap the check exists for: the cell is changed
sheet_id = 'owner:4f357ff3c843489a9758db71e23bf4b4'; s = op('office.get', {'id': sheet_id}); d = copy.deepcopy(s['document']); d['sheets'][0]['cells']['D3']['value'] = 'Up to 95 ms'
op('office.save', {'id': sheet_id, 'expected_revision': s['revision'], 'document': d}); print('\ncell D3 of the Rev B sheet changed to “Up to 95 ms”')
QTest.keyClick(v, Qt.Key_C); settle(200, 6); c = cards()[-1]; print('C ->', said(c, 1)[0], '| waits:', [(o.title[:40], why[:70]) for o, why, _ in c.waiting], '| doubts:', [(r_['title'][:30], r_['about']) for r_ in c.doubts][:6])
inv = f.target['id']; r1 = op('investigation.refresh', {'id': inv}); print('refresh -> changed:', r1.get('changed') or r1.get('REFUSED'))
sh = op('investigation.sheet', {'id': inv}); print('next:', sh['next'].get('kind'), '|', [(c_['claim_text'][:30], c_['last_outcome']) for c_ in sh['checked']])
QTest.keyClick(v, Qt.Key_R); settle(60, 4); f = find('keeps the 80 ms'); print('the finding now:', f.state, f.lines); [print('   ', r_) for r_ in rows(f.id)]
# the other kind: a finding with no check, held to the calculation it quotes
f2 = pick('Settled draw is 3.36 W'); QTest.keyClick(v, Qt.Key_D); settle(60, 4)
n = next((i for i, s in enumerate(page.steps) if s.words.startswith('Check it against')), None); print('\nD on “Settled draw …” ->', [s.words for s in page.steps])
if n is not None:
    QTest.keyClick(v, Qt.Key_1 + n); settle(80, 4); c = cards()[-1]; QTest.keyClick(v, Qt.Key_G); settle(250, 6)
    print('G -> ran:', [ok for _, ok, _ in c.results], '| refusals:', [res for _, ok, res in c.results if not ok]); [print('   ', r_) for r_ in rows(find('Settled draw is 3.36 W').id)]
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
