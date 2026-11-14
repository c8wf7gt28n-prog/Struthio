# C on the reading sheet; the reading sheet at 28 pt on a small screen; the desk's own step still works from it
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
w.a_field.trigger(); settle(); v = w.field_page.view; page = w.field_page
def ui_pt(points):
    row = k.dispatch('ledger.settings.get', {'key': 'reading.ui_pt'}, p)
    row = row['result'] if row.get('ok') else {'revision': None}
    r = k.dispatch('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row.get('revision')}, p); print('   reading size %d pt set: %s' % (points, r.get('ok') or r.get('error')))
    settle(40, 4)
# make something wait: change a cell so the calculations go to recheck
bench = next(o for o in v.field.objects if o.title == '07 Bench readings'); sheet = k.dispatch('office.get', {'id': bench.target['id']}, p)['result']; doc = sheet['document']
doc['sheets'][0]['cells']['B3'] = {**doc['sheets'][0]['cells']['B3'], 'value': '300'}; k.dispatch('office.save', {'id': bench.target['id'], 'expected_revision': sheet['revision'], 'document': doc}, p)
QTest.keyClick(v, Qt.Key_C); settle(250, 6)
print('C -> page: %s | light: %s | steps offered: %s' % (v.reading and v.reading['title'], v.reading and v.reading['light'], [s[0] for s in v.steps]))
for style, text in (v.reading['lines'] if v.reading else ()): print('     [%s] %s' % (style, text[:150]))
print('   foot:', v.reading and v.reading['foot'])
save('Graphite_UX_05_The_Desk_Checked_%s.png' % tag)
QTest.keyClick(v, Qt.Key_1); settle(120, 5); print('1 from the page -> page closed: %s | go offered: %r' % (v.reading is None, v.go))
QTest.keyClick(v, Qt.Key_G); settle(500, 8); print('G -> desk checked again, page: %s | first lines: %s' % (v.reading and v.reading['title'], [t_[:60] for _, t_ in (v.reading['lines'] if v.reading else ())][:3]))
QTest.keyClick(v, Qt.Key_A); settle(30, 3); print('A from the page -> page closed: %s | selected: %s' % (v.reading is None, v.selected().title[:40]))
ui_pt(28); w.a_field.trigger(); settle(60, 4); v.setFocus(); QTest.keyClicks(v, '?'); settle(60, 4)
r = v._reading_rect(v.body()); print('at 28 pt: scale %.2f | page %dx%d inside the widget: %s | can scroll: %s' % (v.scale(), r.width(), r.height(), v.rect().contains(r.toRect()), v._read_room > 1))
save('Graphite_UX_06_The_Keys_At_28pt_%s.png' % tag)
QTest.keyClick(v, Qt.Key_End); settle(20, 2); print('   End reaches the last line: %s' % (abs(v._read_at - v._read_room) < 1)); QTest.keyClick(v, Qt.Key_Escape); settle(20, 2)
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
