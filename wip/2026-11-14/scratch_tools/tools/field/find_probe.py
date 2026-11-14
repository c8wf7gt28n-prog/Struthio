# Find, on every page: the bar's Find opens one line; it counts, steps, and gives the keyboard back
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QTableView, QLabel
from workbench import centre_find
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar; fl = bar.finder; ok = True
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
def where(what):
    if isinstance(what, (QPlainTextEdit, QTextEdit)): c = what.textCursor(); return 'text %d..%d “%s”' % (c.selectionStart(), c.selectionEnd(), c.selectedText()[:24])
    if isinstance(what, QTableView): i = what.currentIndex(); return 'cell r%d c%d “%s”' % (i.row() + 1, i.column() + 1, str(i.data())[:24])
    return 'line “%s”' % (centre_find.words_of(fl.found[fl.at])[:40] if fl.found and fl.at >= 0 else '')
CASES = (('Sheet', '07 Bench readings', 'current'), ('PDF', '07_Bench_Readings.pdf', 'pulse'), ('Writing', '07 Case conclusion', 'pulse'), ('Finding', 'Settled draw', 'rev b'), ('Calc', '07 Settled power', '3.36'))
for n, (name, tile, words) in enumerate(CASES):
    page = open_tile(tile); settle(200, 3); bar.sync()
    lit = bar.find.isEnabled(); ok &= lit
    QTest.mouseClick(bar.find, Qt.LeftButton); settle(150, 2)
    shown = fl.isVisible(); has_keys = QApplication.focusWidget() is fl.line; ok &= shown and has_keys
    QTest.keyClicks(fl.line, words); settle(350, 3)
    first = (fl.at, len(fl.found), where(fl.what))
    QTest.keyClick(fl.line, Qt.Key_Return); settle(120, 2); second = (fl.at, where(fl.what))
    QTest.keyClick(fl.line, Qt.Key_Return, Qt.ShiftModifier); settle(120, 2); back = (fl.at, where(fl.what))
    print('%-8s Find lit: %s | line shown with the keyboard: %s | searches a %s | “%s”: %s | first %s | Enter -> %s | Shift+Enter -> %s' % (
        name, lit, shown and has_keys, type(fl.what).__name__, words, fl.count.text(), first[2], second[1], back[1]), flush=True)
    ok &= len(fl.found) >= 1 and (len(fl.found) == 1 or second[0] != first[0]) and back[0] == first[0]
    save('Find_%02d_%s_%s.png' % (n + 1, name, tag))
    QTest.keyClicks(fl.line, 'zzqx'); settle(350, 3); none = fl.count.text(); ok &= none == 'not here'
    QTest.keyClick(fl.line, Qt.Key_Escape); settle(120, 2)
    print('         words that are not there: “%s” | Esc: line hidden %s' % (none, fl.isHidden()), flush=True); ok &= fl.isHidden()
# Ctrl+F is the same road; another page coming to the front closes the line
page = open_tile('07 Bench readings'); settle(200, 3); w.a_find.trigger(); settle(150, 2); print('Ctrl+F on the sheet opens the line:', fl.isVisible()); ok &= fl.isVisible()
QTest.keyClicks(fl.line, 'rail'); settle(350, 3); w.a_find_next.trigger(); settle(100, 2); print('F3 steps:', fl.count.text())
page = open_tile('07_Bench_Readings.pdf'); settle(300, 3); bar.sync(); print('another page in front: line hidden', fl.isHidden()); ok &= fl.isHidden()
# a finding replaces its sheet while the line is open on it
page = open_tile('Settled draw'); settle(200, 3); QTest.mouseClick(bar.find, Qt.LeftButton); settle(100, 2); QTest.keyClicks(fl.line, 'rev'); settle(350, 3); a = fl.count.text()
page.render(); settle(300, 3); QTest.keyClick(fl.line, Qt.Key_Return); settle(200, 3); print('finding replaced while searching: before “%s”, after Enter “%s”, still running' % (a, fl.count.text()))
QTest.keyClick(fl.line, Qt.Key_Escape); settle(100, 2)
print('FIND PROBE', 'PASS' if ok else 'FAIL')
