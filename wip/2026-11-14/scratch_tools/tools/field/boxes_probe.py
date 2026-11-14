# no white boxes: every surface where a pale outline or a white sheet could stand out, in one walk
from PySide6.QtWidgets import QApplication, QToolButton, QPushButton, QMenu, QDialog
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
save('Boxes_00_Field_%s.png' % tag)
# the PDF page: in the desk's light, then in its own, by the one line in More
page = open_tile('07_Bench_Readings.pdf'); settle(300, 4)
def brightest(widget):
    img = widget.grab().toImage(); top = 0
    for y in range(4, img.height() - 4, 7):
        for x in range(4, img.width() - 4, 7):
            top = max(top, QColor(img.pixel(x, y)).lightness())
    return top
print('PDF page opens in own light:', page.canvas.own_light, '| brightest point of the page as shown:', brightest(page.canvas))
save('Boxes_01_PDF_desk_light_%s.png' % tag)
page.more.menu().aboutToShow.emit(); rows = [a for a in page.more.menu().actions() if not a.isSeparator()]
print('More:', [a.text() for a in rows])
line = next(a for a in rows if 'light' in a.text()); line.trigger(); settle(200, 3)
print('after the line:', page.canvas.own_light, '| brightest:', brightest(page.canvas), '| status:', page.status.text(), '| kept in session:', w.session.state.get('page_own_light'))
save('Boxes_02_PDF_own_light_%s.png' % tag)
page.more.menu().aboutToShow.emit(); line = next(a for a in page.more.menu().actions() if 'light' in a.text()); print('the line now reads:', line.text()); line.trigger(); settle(200, 3)
print('and back:', page.canvas.own_light, '| brightest:', brightest(page.canvas), '| kept:', w.session.state.get('page_own_light'), '| status:', page.status.text())
# the table review dialog (a modal: pictured from a timer, then closed)
def picture_dialog():
    d = QApplication.activeModalWidget()
    if d is None: print('no dialog came up'); return
    try: d.grab().save(str(OUT / ('Boxes_03_Review_table_%s.png' % tag))); print('dialog pictured:', type(d).__name__, d.width(), 'x', d.height())
    finally: d.reject()
b = page.buttons['Review table']; print('Review table can be pressed:', b.isEnabled())
if b.isEnabled(): QTimer.singleShot(1500, picture_dialog); b.click(); settle(300, 3)
# the menus
def picture_menu(name):
    def go():
        m = QApplication.activePopupWidget()
        if m is None: print(name, ': no menu came up'); return
        try: save('Boxes_%s_%s.png' % (name, tag))
        finally: m.close()
    return go
for name, button in (('04_Work_menu', getattr(w, 'work_button', None)), ('05_System_menu', getattr(w, 'system_button', None))):
    if button is None: print(name, 'button not found by that name'); continue
    QTimer.singleShot(700, picture_menu(name)); button.click(); settle(300, 3)
# the left pane's other two faces, and Talk
for name in ('Machine', 'Settings'):
    b = next((b for b in w.findChildren(QPushButton) if b.text() == name and b.isVisible()), None)
    if b is None: print(name, 'tab not found'); continue
    b.click(); settle(400, 4); save('Boxes_06_%s_%s.png' % (name, tag))
b = next((b for b in w.findChildren(QPushButton) if b.text() == 'Files' and b.isVisible()), None)
if b: b.click(); settle(200, 2)
b = next((b for b in w.findChildren(QPushButton) if b.text() == 'Talk' and b.isVisible()), None)
if b: b.click(); settle(300, 3); save('Boxes_07_Talk_%s.png' % tag)
