# the keyboard on a button of a finding while the finding replaces its sheet: 0.4.7 to the first 0.4.9 ended the program here
from PySide6.QtWidgets import QPushButton, QApplication
w.a_field.trigger(); settle(); v = w.field_page.view
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
page = open_tile('Settled draw'); settle(300, 4)
for round_ in range(3):
    b = next(b for b in page.findChildren(QPushButton) if b.text() == 'Compare sources again' and b.isVisible())
    b.setFocus(); settle(100, 2); print('round', round_, '| keyboard on:', QApplication.focusWidget().text() if isinstance(QApplication.focusWidget(), QPushButton) else type(QApplication.focusWidget()).__name__, flush=True)
    page.render(); settle(300, 4); print('   the sheet was replaced; still running | bar says:', repr(w.centre_bar.title.text()), flush=True)
page = open_tile('Settled draw'); settle(300, 4)
print('FINDING REPLACED WITH THE KEYBOARD ON IT: PASS')
