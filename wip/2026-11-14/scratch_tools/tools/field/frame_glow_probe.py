# the amber light outside the Field: Talk's Approve while it waits, the writing line while it has the keyboard, the Clean desk
from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtCore import QRect, QPoint, QSize
from workbench import boss_qt
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus()
o = next(o for o in v.field.objects if o.title == '07 Bench readings'); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(10, 2)
w.shell2.ask('set B3 to 300'); settle(200, 6)
run = next((b for b in w.findChildren(QPushButton) if b.objectName() == 'StagedRun' and b.isVisible()), None)
print('Talk’s Approve waits and is lit:', run is not None and bool(run.property(boss_qt.WAITS)) and run.graphicsEffect() is not None)
bar = w.type_bar; bar.box.setFocus(); settle(40, 3)
print('the writing line has the keyboard:', bar.box.hasFocus(), '| the Field’s selected sheet is no longer the lit one:', not v.hasFocus())
save('Graphite_Amber_06_Talk_And_The_Line_%s.png' % tag)
g = bar.box.mapTo(w, QPoint(0, 0)); strip = w.grab(QRect(g.x() - 40, g.y() - 14, min(700, bar.box.width() + 80), bar.box.height() + 28)); strip.scaled(strip.width() * 2, strip.height() * 2).save(str(OUT / 'crop_line.png'))
if run is not None:
    rg = run.mapTo(w, QPoint(0, 0)); c = w.grab(QRect(rg.x() - 30, rg.y() - 20, run.width() + 220, run.height() + 40)); c.scaled(c.width() * 2, c.height() * 2).save(str(OUT / 'crop_approve.png'))
boss_qt.choose_art(w, 'clean'); settle(40, 3)
print('Clean: Talk’s Approve lit:', run.graphicsEffect() is not None if run else None)
boss_qt.choose_art(w, 'illustrated'); settle(40, 3)
print('Illustrated: Talk’s Approve lit:', run.graphicsEffect() is not None if run else None)
v.setFocus(); settle(20, 2); QTest.keyClick(v, Qt.Key_G); settle(300, 8)
print('after Approve: the button', repr(run.text()) if run else None, '| still lit:', run.graphicsEffect() is not None if run else None, '| enabled:', run.isEnabled() if run else None)
