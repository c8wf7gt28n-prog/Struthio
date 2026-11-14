# an inventory of what a mouse can press in the window, in three states: the Field, a sheet in the centre, a page in the centre
from PySide6.QtWidgets import QAbstractButton, QComboBox, QTabBar, QAbstractScrollArea, QLineEdit, QAbstractItemView, QSplitter, QSplitterHandle, QScrollBar
from PySide6.QtCore import QPoint
def where(wd):
    names = []; p_ = wd.parentWidget()
    while p_ is not None and len(names) < 3:
        if p_.objectName() or type(p_).__name__ not in ('QWidget', 'QFrame'): names.append(p_.objectName() or type(p_).__name__)
        p_ = p_.parentWidget()
    return '<'.join(names)
def inventory(label):
    rows = []
    for b in w.findChildren(QAbstractButton):
        if not b.isVisible() or not b.isEnabled(): continue
        g = b.mapTo(w, QPoint(0, 0))
        if g.x() < 0 or g.y() < 0 or g.x() > w.width() or g.y() > w.height(): continue
        small = min(b.width(), b.height()) < 22
        hand = b.cursor().shape() != Qt.ArrowCursor or (b.property('greenPointer') is not None and int(b.property('greenPointer')) != 0)
        rows.append((small, not b.toolTip(), not hand, type(b).__name__, b.objectName(), (b.text() or '')[:22], b.width(), b.height(), where(b)[:60]))
    print('== %s: %d buttons | small (<22px a side): %d | no tooltip: %d | arrow pointer: %d' % (label, len(rows), sum(r[0] for r in rows), sum(r[1] for r in rows), sum(r[2] for r in rows)))
    for r in sorted(rows, key=lambda r: (-r[0], -r[2], -r[1]))[:40]:
        print('   %s%s%s %-14s %-18s %-24r %3dx%-3d %s' % ('S' if r[0] else '.', 'T' if r[1] else '.', 'A' if r[2] else '.', r[3][:14], r[4][:18], r[5], r[6], r[7], r[8]))
    bars = [(type(a).__name__, a.objectName(), a.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff, a.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff, a.verticalScrollBar().maximum(), a.horizontalScrollBar().maximum())
            for a in w.findChildren(QAbstractScrollArea) if a.isVisible()]
    hidden = [b for b in bars if (b[2] and b[4] > 0) or (b[3] and b[5] > 0)]
    print('   scroll areas: %d | with more to show but no scrollbar: %s' % (len(bars), hidden[:8]))
    hs = [h for h in w.findChildren(QSplitterHandle) if h.isVisible()]
    print('   dividers: %s' % [(h.width(), h.height()) for h in hs][:6])
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); v.repaint(); settle(20, 2)
inventory('the Field in front')
print('   Field hot zones: %d | smallest: %s | faces as hot zones: %s' % (len(v._hot), sorted((round(b.width()), round(b.height()), words[:28]) for b, k, tx, words in v._hot)[:4], any('face' in words.lower() for b, k, tx, words in v._hot)))
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(250, 6)
inventory('a sheet open in the centre'); save('Graphite_Mouse_Inv_Sheet_%s.png' % tag)
w.a_field.trigger(); settle(100, 4); o = next(o for o in v.field.objects if o.title.startswith('07 Case conclusion')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(250, 6)
inventory('a page open in the centre'); save('Graphite_Mouse_Inv_Page_%s.png' % tag)
