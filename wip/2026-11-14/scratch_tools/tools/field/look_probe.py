# the look pass: what the head says, the glide on Z, icons at first sight, Stacy on the right
from PySide6.QtWidgets import QApplication
from workbench import tool_faces as faces
ok = True
print('a fresh workspace: buttons are', faces.mode(), '| the right pane shows', type(w.console_pages.currentWidget()).__name__, '| is Stacy:', w.console_pages.currentWidget() is w.shell2.face)
ok &= faces.mode() == 'icons' and w.console_pages.currentWidget() is w.shell2.face
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle(); bar = w.centre_bar; head = w.findChild(type(w.shell2).__mro__[0].__bases__[0].__class__, 'x') if False else None
from workbench.shell2 import PathBar
head = w.findChild(PathBar)
print('in the Field the head says:', head.friendly(), '| the line still holds:', head.text()[:60] + '…')
save('Look_00_Field_%s.png' % tag)
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); head.refresh(); settle(50, 2); return w.tabs.currentWidget()
for n, tile in enumerate(('07_Bench_Readings.pdf', '07 Bench readings', '07 Case conclusion', 'Settled draw')):
    open_tile(tile); name, where = head.friendly(); print('   %-24s head says: %-34r %-34r | its text: %s' % (tile, name, where, head.text()[:44]))
    ok &= bool(name) and not name.startswith('graphite://') and head.text().startswith(('graphite://', '/'))
    save('Look_%02d_%s_%s.png' % (n + 1, tile.split()[0].replace('.pdf', ''), tag))
# a click on the head shows the address, whole and selected; Esc puts the name back
head.edit_location(); settle(150, 3); print('asked for the address: has the keyboard', head.hasFocus(), '| selected:', head.selectedText()[:50]); ok &= head.hasFocus() and head.selectedText() == head.text()
save('Look_05_The_Address_When_Wanted_%s.png' % tag); QTest.keyClick(head, Qt.Key_Escape); settle(100, 2); ok &= not head.hasFocus()
# the glide
w.a_field.trigger(); settle(200, 3); v.setFocus(); settle(50, 2); z0 = v.zoom; seen = []
QTest.keyClick(v, Qt.Key_Z)
for _ in range(12): app.processEvents(); QTest.qWait(22); seen.append(round(v.zoom, 3))
settle(200, 3); print('Z from %.2f: zoom seen every 22 ms %s -> rests at %.2f, whole %s' % (z0, seen, v.zoom, v._fitted))
between = [z for z in seen if min(z0, v.zoom) + 0.01 < z < max(z0, v.zoom) - 0.01]; z1 = v.zoom
# from the reading size Z shows the whole desk; from a desk already shown whole (0.8.0: it opens whole when 80 per cent is enough) Z brings the reading size
ok &= len(between) >= 2 and (v._fitted if abs(z0 - 1.0) < 1e-6 else abs(z1 - 1.0) < 1e-6)
save('Look_06_After_The_Glide_%s.png' % tag)
v.still = lambda: True; QTest.keyClick(v, Qt.Key_Z); app.processEvents(); print('with motion reduced, Z is at once:', v.zoom); ok &= abs(v.zoom - z1) > 0.05 and (abs(v.zoom - 1.0) < 1e-6 or v._fitted)      # at once, and the other of the two
print('LOOK PROBE', 'PASS' if ok else 'FAIL')
