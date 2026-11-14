# the centre's bar: shown over the work, hidden for the Field and Home; each control honest about the open view
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidget, QMenu
from PySide6.QtCore import QTimer, QPoint, QRect
def state(bar): return {b.text(): (b.isEnabled(), b.toolTip()[:58]) for b in (bar.field, bar.find, bar.smaller, bar.larger, bar.undo, bar.redo, bar.save)}
bar = w.centre_bar
w.a_field.trigger(); settle(); v = w.field_page.view
print('Field in front -> the bar shows:', bar.isVisible())
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(600, 8)
print('a sheet open -> the bar shows:', bar.isVisible(), '| above the work:', bar.mapTo(w, QPoint(0, 0)).y() < w.tabs.mapTo(w, QPoint(0, 0)).y(), '| height', bar.height(), '| says:', repr(bar.title.text()))
for k, val in state(bar).items(): print('   %-10s %-5s %s' % (k, val[0], val[1]))
page = w.tabs.currentWidget(); grid = page.grid; h0 = grid.verticalHeader().defaultSectionSize(); f0 = grid.fontInfo().pointSizeF()
QTest.mouseClick(bar.larger, Qt.LeftButton); QTest.mouseClick(bar.larger, Qt.LeftButton); settle(60, 3)
print('clicked + twice: the table’s letters %.1f -> %.1f pt | rows %d -> %d px' % (f0, grid.fontInfo().pointSizeF(), h0, grid.verticalHeader().defaultSectionSize()))
save('Graphite_Mouse_03_The_Centre_Bar_%s.png' % tag)
QTest.mouseClick(bar.smaller, Qt.LeftButton); QTest.mouseClick(bar.smaller, Qt.LeftButton); settle(60, 3); print('clicked − twice: back to %.1f pt' % grid.fontInfo().pointSizeF())
# change a cell the way the page does, then Save from the bar
sheet = page.current_sheet(); cell = dict(sheet['cells']['B3']); cell['value'] = '290'; sheet['cells']['B3'] = cell; page.refresh_table(); page.set_dirty(); bar.sync()
print('a cell changed -> Save reads', repr(bar.save.text()), '| title says:', repr(bar.title.text()))
QTest.mouseClick(bar.save, Qt.LeftButton); settle(300, 6); print('clicked Save -> unsaved:', page.is_dirty(), '| Save reads', repr(bar.save.text()))
QTest.mouseClick(bar.field, Qt.LeftButton); settle(200, 6); print('clicked ‹ Field -> Field in front:', w._field_active, '| selected:', v.field.get(v.field.selected).title, '| the bar shows:', bar.isVisible())
# a page of writing
o = next(o for o in v.field.objects if o.title.startswith('07 Case conclusion')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(600, 8)
print('a page open -> the bar shows:', bar.isVisible(), '| says:', repr(bar.title.text()))
for k, val in state(bar).items(): print('   %-10s %-5s %s' % (k, val[0], val[1]))
save('Graphite_Mouse_04_The_Centre_Bar_Page_%s.png' % tag)
w.show_start() if hasattr(w, 'show_start') else None; settle(200, 5); print('Home -> the bar shows:', bar.isVisible())
