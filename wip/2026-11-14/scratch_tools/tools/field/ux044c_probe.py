from workbench import ledger_control
k = w.ledger_bridge.kernel; p = operator()
def ui_pt(points):
    row = next(r for r in ledger_control.settings(k)['settings'] if r['key'] == 'reading.ui_pt')
    if row['value'] != float(points):
        r = k.dispatch('ledger.settings.set', {'key': 'reading.ui_pt', 'value': float(points), 'expected_revision': row['revision']}, p); assert r['ok'], r
    settle(40, 4)
w.a_field.trigger(); settle(); v = w.field_page.view
for points in (18, 28):
    ui_pt(points); w.a_field.trigger(); settle(60, 4); align(); v.setFocus(); QTest.keyClicks(v, '?'); settle(60, 4)
    r = v._reading_rect(v.body()); print('at %d pt: scale %.2f | page %dx%d inside the widget: %s | can scroll: %s' % (points, v.scale(), r.width(), r.height(), v.rect().contains(r.toRect()), v._read_room > 1))
    if points == 28: save('Graphite_UX_06_The_Keys_At_28pt_%s.png' % tag)
    QTest.keyClick(v, Qt.Key_End); settle(20, 2); print('   End reaches the last line: %s' % (abs(v._read_at - v._read_room) < 1)); QTest.keyClick(v, Qt.Key_Escape); settle(20, 2)
    f = next(o for o in v.field.objects if 'The reviewed sheet keeps' in o.title); v.field.select(f.id); v._reveal(); v._describe(); v.update(); settle(5, 2)
    QTest.keyClick(v, Qt.Key_X); settle(150, 5); print('   X at %d pt: page %s | scrolls: %s' % (points, v.reading is not None, v._read_room > 1))
    if points == 28: save('Graphite_UX_07_A_Doubt_At_28pt_%s.png' % tag)
    QTest.keyClick(v, Qt.Key_Escape); settle(20, 2)
print('keyboard in:', type(app.focusWidget()).__name__, '| Field in front:', w._field_active)
