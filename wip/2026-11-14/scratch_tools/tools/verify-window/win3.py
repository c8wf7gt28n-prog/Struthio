from winbase import *
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel
def fit(v, tag):
    body = v._layout(); app.processEvents(); body = v._layout()
    rects = {i: v.sheet_rect(i, body) for i in v._placed}
    cut = [(v.field.get(i).title[:22], round(r.left()), round(r.right())) for i, r in rects.items() if r.right() > body.right() + 0.5 or r.left() < body.left() - 0.5]
    sel = v.sheet_rect(v.field.selected, body); p0 = next(iter(v._placed.values())) if v._placed else None
    print('   %-30s window %dx%d view %dx%d scale %.2f rail %.0f cols %d sheet %.0fx%.0f | surface %.0fx%.0f body %.0fx%.0f scroll x %.0f y %.0f | sheets not wholly inside sideways: %d of %d | selected wholly visible: %s' % (
        tag, w.width(), w.height(), v.width(), v.height(), v.scale(), v.rail(), len(v.field.ranks()), p0.w if p0 else 0, p0.h if p0 else 0, v._surface[0], v._surface[1], body.width(), body.height(), v.scroll_x, v.scroll_y,
        len(cut), len(rects), body.contains(sel) if sel else None))
    return body.contains(sel) if sel else None
which = sys.argv[1:]
if 'resize' in which:
    v = field(); where('Field'); fit(v, 'as opened')
    print('   window minimum size:', w.minimumSize().width(), w.minimumSize().height(), '| minimumSizeHint:', w.minimumSizeHint().width(), w.minimumSizeHint().height())
    for size in ((1600, 900), (1366, 768), (1280, 720), (1024, 768), (1024, 600), (800, 600), (640, 480), (1920, 1200)):
        n = len(errors); w.resize(*size); settle(30, 4); fit(v, 'resized to %dx%d' % size)
        if errors[n:]: print('   uncaught:', errors[n].strip().splitlines()[-1])
        if size in ((1280, 720), (1024, 600), (800, 600)): save('edge_resize_%dx%d.png' % size)
    where('after resizing with the Field showing')
    QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc')
if 'place' in which:
    # losing place: pick the lowest finding at a laptop size, open it, come back
    w.resize(1280, 720); settle(30, 4); v = field(); fit(v, 'opened at 1280x720')
    ident = v.field.column(3)[-1]; 
    for _ in range(12):
        if v.field.selected == ident: break
        QTest.keyClick(v, Qt.Key_Down if v.field.rank_of(v.field.selected) == 3 else Qt.Key_Left); settle(10, 1)
    print('   selected by keyboard:', v.selected().title); fit(v, 'lowest finding selected'); save('edge_place_1_selected.png')
    QTest.keyClick(v, Qt.Key_Return); settle(); where('Enter')
    v = field(); where('F9 back'); print('   selection kept:', v.selected().title); fit(v, 'back in the Field'); save('edge_place_2_back.png')
    QTest.keyClick(v, Qt.Key_Escape); settle()
if 'typing' in which:
    from workbench.document_qt import show as show_document
    docs = k.dispatch('documents.list', {}, operator())['result']['documents']
    tab = show_document(w, docs[0]['id']); settle(); page = tab.page
    QTest.keyClicks(app.focusWidget(), 'abc'); settle(10, 2); n1 = len(page.toPlainText()); print('   focus before:', type(app.focusWidget()).__name__, '| typed 3 keys, page length', n1)
    v = field(); QTest.keyClick(v, Qt.Key_Escape); settle(); fw = app.focusWidget(); print('   focus after Field + Esc:', type(fw).__name__)
    QTest.keyClicks(fw, 'xyz'); settle(10, 2); n2 = len(page.toPlainText()); print('   typed 3 more keys after coming back: page length', n2, '->', 'text arrived' if n2 == n1 + 3 else 'KEYS WENT NOWHERE')
if 'journal' in which:
    def count():
        try:
            with k.db() as db: return db.execute('SELECT count(*) FROM activity_journal').fetchone()[0]
        except Exception as e: return repr(e)
    a = count(); v = field(); b = count(); w.a_field.trigger(); settle(); c = count(); QTest.keyClick(v, Qt.Key_Escape); settle(); d = count()
    print('   journal rows: before %s, after first F9 %s, after second F9 %s, after Esc %s' % (a, b, c, d))
if 'tab' in which:
    v = field(); where('Field'); print('   waiting objects:', sum(o.needs_attention() for o in v.field.objects), '| focus:', type(app.focusWidget()).__name__)
    seq = []
    for _ in range(4):
        QTest.keyClick(app.focusWidget(), Qt.Key_Tab); settle(10, 1); fw = app.focusWidget(); seq.append((type(fw).__name__, v.selected().title[:18]))
    print('   Tab x4 with a waiting object:', seq)
    # make nothing wait (as in a workspace whose question is answered): drop the open question from the model
    from workbench.field_model import Field
    calm = Field([o for o in v.field.objects if not o.needs_attention()], list(v.field.links), v.field.title); v.set_field(calm); v.setFocus(); settle(10, 2)
    seq = []
    for _ in range(6):
        QTest.keyClick(app.focusWidget(), Qt.Key_Tab); settle(10, 1); fw = app.focusWidget(); seq.append(type(fw).__name__ + ':' + (fw.objectName() or fw.accessibleName() or '')[:24])
    print('   Tab x6 with nothing waiting:', seq)
    where('after tabbing away'); fw = app.focusWidget()
    QTest.keyClick(fw, Qt.Key_Escape); settle(); where('Esc with the focus outside the Field')
    QTest.keyClick(fw, Qt.Key_F9); settle(); where('F9 with the focus outside the Field'); print('   focus:', type(app.focusWidget()).__name__)
    QTest.keyClick(app.focusWidget(), Qt.Key_Escape); settle(); where('Esc')
finish()
