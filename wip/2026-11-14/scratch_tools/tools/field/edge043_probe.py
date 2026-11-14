# 0.4.3 edges: what was shown is what is kept; an edited brief; a check on a replaced page; two inputs on one cell; the trail across faces
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def d(op, a):
    r = k.dispatch(op, a, p); return r['result'] if r.get('ok') else {'ERROR': (r.get('error') or {}).get('message')}
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:700].replace('\n', ' / ') for l in card.findChildren(QLabel)][:n]
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def pick(words):
    o = next(o for o in v.field.objects if words in o.title); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(5, 2); return o
inv = d('investigation.list', {})['investigations'][0]['id']
# (a) the desk changes between B and G: nothing is kept
QTest.keyClick(v, Qt.Key_B); settle(200, 6)
d('investigation.claim', {'id': inv, 'text': 'A late finding,\nwritten on two lines.', 'role': 'FINDING'})
QTest.keyClick(v, Qt.Key_G); settle(250, 6); c = cards()[-1]
print('(a) G after the desk changed ->', ' | '.join(said(c, 6))[-260:], '| briefs:', len([o for o in v.field.objects if o.tag == 'BRIEF']))
# (c) a record with a line break in its words: the brief is still written
QTest.keyClick(v, Qt.Key_R); settle(100, 5); QTest.keyClick(v, Qt.Key_B); settle(200, 6); QTest.keyClick(v, Qt.Key_G); settle(250, 6)
brief = next((o for o in v.field.objects if o.tag == 'BRIEF'), None); print('(c) with a two-line finding on the desk -> brief kept:', bool(brief), brief and brief.state)
got = d('documents.get', {'id': brief.target['id']}); print('    its line:', [b['text'] for b in got['document']['blocks'] if 'late finding' in b['text']][:1])
# (b) the owner edits the brief
blocks = got['document']['blocks'] + [{'id': 'f' * 32, 'style': 'Normal', 'text': 'My own note: ask the supplier.', 'marks': []}]
saved = d('documents.save', {'id': brief.target['id'], 'expected_revision': got['document']['revision'], 'blocks': blocks}); print('(b) saved by the owner:', saved.get('saved'), saved.get('ERROR'))
QTest.keyClick(v, Qt.Key_R); settle(100, 5); b2 = pick(' · brief'); print('    still a brief on the Field:', b2.tag, b2.state)
print('    X ->', [(r['verdict'], r['about'], r['why'][:90]) for r in d('field.doubt', {'id': b2.id})['rows']])
# (d) two inputs on one cell
from workbench import datasheet_work
doc = {'title': 't', 'derivation': {'profile': datasheet_work.REPORT, 'recipe': {'expression': '(a + b) * i', 'inputs': {'a': 'B2', 'b': 'B2', 'i': 'B3'}, 'output_unit': 'W'},
       'inputs': [{'symbol': 'a', 'cell': 'B2', 'parameter': 'V', 'value': '12', 'unit': 'V'}, {'symbol': 'b', 'cell': 'B2', 'parameter': 'V', 'value': '12', 'unit': 'V'}, {'symbol': 'i', 'cell': 'B3', 'parameter': 'I', 'value': '2', 'unit': 'A'}],
       'calculation': {'outputs': [{'value': {'decimal': '48', 'unit': 'W'}}]}}}
print('(d) (a+b)*i with a and b both on B2, B2 set to 10 ->', datasheet_work.what_if(doc, {'B2': '10'})['would_be'], '| by symbol a only ->', datasheet_work.what_if(doc, {'a': '10'})['would_be'])
# (e) a check bound on a calculation's page (by its address), then the calculation is worked again
f = pick('Settled draw is 3.36 W'); QTest.keyClick(v, Qt.Key_D); settle(80, 4)
n = next(i for i, s in enumerate(page.steps) if s.words.startswith('Check it against')); print('(e) step:', page.steps[n].words, '|', [line[:70] for _, line in page.steps[n].more][:1])
QTest.keyClick(v, Qt.Key_1 + n); settle(80, 4); QTest.keyClick(v, Qt.Key_G); settle(300, 6); c = cards()[-1]
print('    ran:', [(ok, (res.get('ran') or [{}])[0].get('outcome') if isinstance(res, dict) and res.get('ran') else 'done' if ok else str(res)[:90]) for _, ok, res in c.results])
print('    wires into the finding:', [(v.field.get(l.source).kind, l.label) for l in v.field.fed_by(f.id)])
print('    doubt now:', [(r['verdict'], r['about']) for r in d('field.doubt', {'id': f.id})['rows']][:5])
bench = next(o for o in v.field.objects if o.title == '07 Bench readings'); sheet = d('office.get', {'id': bench.target['id']}); cells = sheet['document']
cells['sheets'][0]['cells']['B3'] = {**cells['sheets'][0]['cells']['B3'], 'value': '300'}
print('    sheet saved with B3 = 300:', d('office.save', {'id': bench.target['id'], 'expected_revision': sheet['revision'], 'document': cells}).get('ERROR', 'ok'))
QTest.keyClick(v, Qt.Key_C); settle(250, 6); QTest.keyClick(v, Qt.Key_1); settle(100, 5); QTest.keyClick(v, Qt.Key_G); settle(400, 8)
f = next(o for o in v.field.objects if o.title.startswith('Settled draw is 3.36 W'))
rows = d('field.doubt', {'id': f.id})['rows']; print('    after the calculation was worked again -> finding:', f.state, '|', [(r['verdict'], r['about'], r['why'][:110]) for r in rows if r['verdict'] == 'doubt'])
print('    calculations now:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'], '| replaced ids known to the Field:', len(v.field.replaced))
# (f) the trail across faces
v.setFocus(); a = pick('07 Bench readings'); b = pick('07 Limits Rev A')
QTest.keyClick(v, Qt.Key_P); settle(150, 5); QTest.keyClick(v, Qt.Key_Right); settle(10, 2); QTest.keyClick(v, Qt.Key_Backspace); settle(10, 2); on_shelf = v.selected().title
QTest.keyClick(v, Qt.Key_W); settle(150, 5); QTest.keyClick(v, Qt.Key_Backspace); settle(10, 2)
print('(f) on the shelf Backspace went to %r; back on the work, Backspace went to %r' % (on_shelf[:24], v.selected().title[:28]))
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
