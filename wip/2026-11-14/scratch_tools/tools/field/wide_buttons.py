# buttons drawn as words whose click area is much wider than their words, on the pages the Field opens and the panes
from PySide6.QtWidgets import QAbstractButton
from PySide6.QtCore import QPoint
def wide(label):
    rows = []
    for b in w.findChildren(QAbstractButton):
        if not b.isVisible() or not b.text(): continue
        need = b.fontMetrics().horizontalAdvance(b.text().replace('&', '')) + 40
        if b.width() > need + 60 and b.width() > 160: rows.append((b.width(), need, b.text()[:28], type(b.parentWidget()).__name__, b.objectName()))
    print('== %s: %d buttons far wider than their words%s' % (label, len(rows), ''.join('\n   %4d px for %3d px of words  %-30r in %s %s' % r for r in sorted(rows, reverse=True)[:12])))
w.a_field.trigger(); settle(); v = w.field_page.view
for title in ('07 Bench readings', '07 Case conclusion', '07 Settled power', '07_Bench_Readings.pdf', 'Settled draw'):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    if o is None: continue
    w.a_field.trigger(); settle(120, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(700, 8); wide('opened “%s” (%s)' % (title, type(w.tabs.currentWidget()).__name__))
for name in ('Settings', 'Machine'):
    tab = next((b for b in w.findChildren(QAbstractButton) if b.text() == name and b.isVisible()), None)
    if tab is not None: tab.click(); settle(200, 5); wide('the %s pane' % name)
