from winbase import *
which = sys.argv[1]
if which == 'empty':
    where('opened (empty workspace)'); before = snap()
    v = field(); where('Field'); print('   objects:', len(v.field.objects), '| title:', repr(v.field.title), '| refused:', (w.field_page.problem, sorted(w.field_page.unread)), '| status:', repr(status()), '| focus:', type(app.focusWidget()).__name__)
    save('edge_empty_field.png')
    for key in (Qt.Key_Return, Qt.Key_Left, Qt.Key_Down, Qt.Key_Home): QTest.keyClick(v, key)
    settle(10, 2)
    QTest.keyClick(v, Qt.Key_Tab); settle(10, 2); print('   Tab in the empty Field -> focus:', type(app.focusWidget()).__name__, (app.focusWidget().accessibleName() or app.focusWidget().objectName())[:30])
    v.setFocus(); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); after = snap(); diff(before, after, 'empty: start -> Field -> Esc')
    w.show_start(); settle(); where('Home (empty workspace)'); h1 = snap()
    v = field(); where('Field from Home'); QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); diff(h1, snap(), 'empty: Home -> Field -> Esc')
if which == 'typing':
    from workbench.document_qt import show as show_document
    from workbench.engineering_kernel import operator
    docs = w.ledger_bridge.kernel.dispatch('documents.list', {}, operator())['result']['documents']
    tab = show_document(w, docs[0]['id']); settle(); page = tab.page; n0 = len(page.toPlainText())
    QTest.keyClicks(app.focusWidget(), 'abc'); settle(10, 2); n1 = len(page.toPlainText()); print('   focus before the Field:', type(app.focusWidget()).__name__, '| page length %d -> %d after typing abc' % (n0, n1))
    v = field(); QTest.keyClick(v, Qt.Key_Escape); settle(); fw = app.focusWidget(); print('   focus after Field + Esc:', type(fw).__name__, '| focus policy of the tab:', tab.focusPolicy(), '| page has focus:', page.hasFocus())
    QTest.keyClicks(fw, 'xyz'); settle(10, 2); n2 = len(page.toPlainText()); print('   typed xyz after coming back: page length %d -> %d' % (n1, n2))
    # the sheet room and the investigation room
    from workbench.office_qt import open_office
    row = w.ledger_bridge.kernel.dispatch('office.list', {}, operator())['result']['documents'][0]
    t2 = open_office(w, row['id']); settle(); f1 = app.focusWidget(); 
    grid = t2.findChild(type(f1)) if f1 else None
    f1 = app.focusWidget(); print('   sheet room: focus before', type(f1).__name__)
    v = field(); QTest.keyClick(v, Qt.Key_Escape); settle(); print('   sheet room: focus after Field + Esc', type(app.focusWidget()).__name__)
finish()
