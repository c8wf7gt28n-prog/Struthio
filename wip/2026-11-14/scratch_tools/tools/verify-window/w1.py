from winbase import *
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._describe(); v.update(); settle(10, 2); return v.selected()
v = field()
print('kinds in the field:', sorted({o.kind for o in v.field.objects}), '| target kinds:', sorted({(o.target or {}).get('kind', '-') if isinstance(o.target, dict) else '-' for o in v.field.objects}))
QTest.keyClick(v, Qt.Key_Escape); settle()
tests = [('sheet', lambda o: o.kind == 'sheet' and 'Bench' in o.title), ('calculation', lambda o: o.kind == 'calculation'), ('finding', lambda o: o.kind == 'finding'),
         ('source', lambda o: o.kind == 'source'), ('question', lambda o: o.kind == 'question'), ('document', lambda o: o.kind == 'document')]
for kind, test in tests:
    v = field()
    try: o = pick(v, test)
    except StopIteration: print('-- no %s in the field' % kind); QTest.keyClick(v, Qt.Key_Escape); settle(); continue
    print('-- %s: %r target=%s' % (kind, o.title[:40], (o.target or {}).get('kind') if isinstance(o.target, dict) else o.target))
    assert w._field_active and v.isVisible(); QTest.keyClick(v, Qt.Key_Return); settle(); where('  Enter, no tab yet'); t1 = w.tabs.currentWidget(); n1 = w.tabs.count()
    v = field(); assert w._field_active and v.isVisible() and v.selected().id == o.id; QTest.keyClick(v, Qt.Key_Return); settle(); where('  Enter, tab exists and is current'); print('     same tab shown:', w.tabs.currentWidget() is t1, '| tabs', n1, '->', w.tabs.count(), '| status:', repr(status())[:90])
    w.a_files.trigger(); settle(); assert type(w.tabs.currentWidget()).__name__ == 'FilesTab'
    v = field(); assert w._field_active and v.isVisible(); QTest.keyClick(v, Qt.Key_Return); settle(); where('  Enter, another tab in front'); print('     same tab shown:', w.tabs.currentWidget() is t1, '| tabs', w.tabs.count())
    w.a_files.trigger(); settle()
    v = field(); assert w._field_active and v.isVisible(); pt = v.sheet_rect(v.field.selected, v._layout()).center().toPoint(); print('     dclick point inside body:', v.body().contains(QPointF(pt)), '| hit:', v._hit(QPointF(pt)) == o.id)
    QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, pt); settle(); where('  double-click, another tab in front'); print('     same tab shown:', w.tabs.currentWidget() is t1, '| focus:', type(app.focusWidget()).__name__)
    v = field(); pt = v.sheet_rect(v.field.selected, v._layout()).center().toPoint(); QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, pt); settle(); where('  double-click, tab current'); print('     same tab shown:', w.tabs.currentWidget() is t1)
    if w._field_active: QTest.keyClick(v, Qt.Key_Escape); settle()
finish()
