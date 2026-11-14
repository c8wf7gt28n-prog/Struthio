from winbase import *
from workbench.engineering_kernel import operator
import sqlite3
k = w.ledger_bridge.kernel
def pick(v, test):
    ident = next(o.id for o in v.field.objects if test(o)); v.field.select(ident); v._describe(); v.update(); settle(10, 2); return v.selected()
which = sys.argv[1:]
if 's11' in which:
    print('== S11 Enter on an object whose tab is already open')
    v = field(); o = pick(v, lambda o: o.kind == 'sheet' and 'Bench' in o.title)
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the sheet (first time)')
    v = field(); print('   selection kept:', v.selected().title)
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the same sheet again'); print('   status line:', repr(status()))
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter a third time')
    # another tab in front, the sheet's tab behind
    QTest.keyClick(v, Qt.Key_Escape); settle()
    w.a_files.trigger(); settle(); where('Files in front, sheet tab behind')
    v = field(); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the sheet (its tab exists, not current)')
    pt = v.sheet_rect(v.field.selected).center().toPoint(); QTest.mouseDClick(v, Qt.LeftButton, Qt.NoModifier, pt); settle(); where('double-click on the same sheet')
    if w._field_active: QTest.keyClick(v, Qt.Key_Escape); settle()
    for kind, test in (('calculation', lambda o: o.kind == 'calculation'), ('finding', lambda o: o.kind == 'finding')):
        v = field(); o = pick(v, test); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on a %s (first)' % kind)
        v = field(); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on the same %s again' % kind)
if 's5' in which:
    print('== S5 close the last tab while the Field shows')
    from workbench.document_qt import show as show_document
    show_document(w); settle(); where('one tab open')
    v = field(); where('Field over one tab')
    w.close_tab(0); settle(); where('closed the last tab under the Field')
    print('   field view visible:', v.isVisible(), '| focus:', type(app.focusWidget()).__name__)
    w._close_start(); settle()
    show_document(w); settle(); v = field()
    QTest.keyClick(v, Qt.Key_W, Qt.ControlModifier); settle(); where('Ctrl+W while the Field shows')
if 's7' in which:
    print('== S7 art mode'); v = field(); print('   texture with desk_art=%r:' % w.session.state.get('desk_art'), v.texture)
    w.session.state['desk_art'] = 'clean'; w.field_page.refresh(); settle(); print('   texture after desk_art=clean + refresh:', v.texture)
    w.session.state['desk_art'] = 'illustrated'; w.a_field.trigger(); settle(); print('   texture after desk_art=illustrated + F9:', v.texture)
    QTest.keyClick(v, Qt.Key_Escape); settle()
if 's9' in which:
    print('== S9 a reader operation raises / refuses')
    real = Kernel.dispatch
    for bad, how in (('office.list', 'raise'), ('documents.get', 'refuse'), ('investigation.path', 'raise'), ('intake.namespaces', 'none'), ('investigation.sheet', 'shape')):
        def fake(self, operation, arguments=None, principal=None, *a, **kw):
            if operation == bad:
                if how == 'raise': raise RuntimeError('probe: %s failed' % operation)
                if how == 'refuse': return {'ok': False, 'error': {'code': 'PROBE', 'message': 'probe refused ' + operation}}
                if how == 'none': return None
                if how == 'shape': return {'ok': True, 'result': {'learned': [{'text': 'no id here'}], 'unresolved': None}}
            return real(self, operation, arguments, principal, *a, **kw)
        n = len(errors)
        with patch.object(Kernel, 'dispatch', fake):
            try:
                v = field()
            except Exception as e:
                print('   %s %s -> show_field RAISED %r' % (bad, how, e)); continue
        where('%s -> %s' % (bad, how)); print('   census:', v.field.census(), '| refused:', [(a2, b2[:40]) for a2, b2 in w.field_page.refused][:3], '| status:', repr(status())[:140], '| new uncaught:', len(errors) - n)
        if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:200])
        if w._field_active: QTest.keyClick(v, Qt.Key_Escape); settle()
if 's8' in which:
    print('== S8 no ledger_bridge'); bridge = w.ledger_bridge
    try:
        del w.ledger_bridge
        n = len(errors)
        try: v = field(); where('show_field without ledger_bridge'); print('   objects:', len(v.field.objects), '| refused:', w.field_page.refused, '| status:', repr(status()), '| uncaught:', len(errors) - n)
        except Exception as e: print('   RAISED', repr(e))
        if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:300])
    finally:
        w.ledger_bridge = bridge
    if w._field_active: QTest.keyClick(w.field_page.view, Qt.Key_Escape); settle(); where('Esc')
if 's10' in which:
    print('== S10 the record was deleted after the Field was drawn')
    v = field()
    # document
    o = pick(v, lambda o: o.kind == 'calculation'); ident = o.target['id']
    with k.db() as db: print('   deleting desk record', ident, db.execute('DELETE FROM desk_records WHERE id=?', (ident,)).rowcount)
    n = len(errors); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on a deleted calculation'); print('   status:', repr(status()), '| uncaught:', len(errors) - n)
    tab = w.tabs.currentWidget(); print('   tab shows document:', getattr(tab, 'document_id', None), '| foot:', getattr(getattr(tab, 'foot', None), 'text', lambda: None)())
    if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:300])
    # investigation
    w.field_page.view.field.select(next(o.id for o in v.field.objects if o.kind == 'finding'))
    w.central_stack.setCurrentWidget(w.field_page); w._field_active = True   # the Field as drawn before the delete (no refresh)
    o = v.selected(); ident = o.target['id']
    with k.db() as db: print('   deleting investigation', ident, db.execute('DELETE FROM inv_investigations WHERE id=?', (ident,)).rowcount)
    n = len(errors); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on a finding of a deleted investigation'); print('   status:', repr(status()), '| uncaught:', len(errors) - n)
    if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:300])
    # sheet
    w.field_page.view.field.select(next(o.id for o in v.field.objects if o.kind == 'sheet'))
    w.central_stack.setCurrentWidget(w.field_page); w._field_active = True
    o = v.selected(); ident = o.target['id']
    from workbench import office_service
    db = sqlite3.connect(str(office_service.path())); print('   deleting office document', ident, db.execute('DELETE FROM office_documents WHERE id=?', (ident,)).rowcount); db.commit(); db.close()
    n = len(errors); QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter on a deleted sheet'); print('   status:', repr(status()), '| uncaught:', len(errors) - n)
    if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:300])
    n = len(errors); v = field(); where('F9 after the deletes'); print('   census:', v.field.census(), '| refused:', w.field_page.refused, '| uncaught:', len(errors) - n)
    if errors[n:]: print('   ', errors[n].strip().splitlines()[-1][:300])
finish()
