# the work pages after the pass: the sheet, the PDF, a page of writing, a finding
from PySide6.QtWidgets import QApplication, QToolButton, QPushButton, QMenu
from PySide6.QtCore import QTimer
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
def menu_of(button):
    button.menu().aboutToShow.emit(); return [(a.text(), a.isEnabled()) for a in button.menu().actions() if not a.isSeparator()]
page = open_tile('07 Bench readings'); save('Pages_01_Sheet_%s.png' % tag)
shown = [b.text() for b in page.findChildren(QPushButton) if b.isVisible()] + [b.text() for b in page.findChildren(QToolButton) if b.isVisible()]
print('sheet page, buttons in view:', shown); print('   More:', menu_of(page.more)); print('   bar says:', repr(bar.title.text()))
page = open_tile('07_Bench_Readings.pdf'); save('Pages_02_PDF_%s.png' % tag)
shown = [b.text() for b in page.findChildren(QPushButton) if b.isVisible()] + [b.text() for b in page.findChildren(QToolButton) if b.isVisible()]
print('PDF page, buttons in view:', shown); print('   More:', menu_of(page.more)); print('   bar says:', repr(bar.title.text()))
page = open_tile('07 Case conclusion'); save('Pages_03_Writing_%s.png' % tag); print('writing page: bar says:', repr(bar.title.text()))
page = open_tile('Settled draw'); save('Pages_04_Finding_%s.png' % tag); print('finding page: bar says:', repr(bar.title.text()))
