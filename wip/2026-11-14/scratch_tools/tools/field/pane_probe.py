# the right pane as one view: one title, This and Now under Stacy, Activity and Context one word away and a way back
from PySide6.QtWidgets import QPushButton
sh = w.shell2; face = sh.face; ok = True; settle(600, 3)
tabs = sh.face_tabs; title = getattr(sh, 'title_word', None)
print('tabs shown:', [(b.text(), b.isVisible()) for b in tabs.buttons], '| title:', repr(title.text()) if title else None, title.isVisible() if title else None, title.geometry().getRect() if title else None)
rest = getattr(tabs, 'at_rest', None)      # 0.7.0: at rest the pane has no title row at all; before it, the title said Stacy
ok &= title is not None and not any(b.isVisible() for b in tabs.buttons) and ((rest is True and not tabs.isVisible()) if rest is not None else (title.isVisible() and title.text() == 'Stacy'))
print('at rest: title row shown', tabs.isVisible(), '| her face is the top of the pane')
w.a_field.trigger(); settle(400, 3); face.show_agenda(); settle(100, 2)
import re
plain = lambda label: re.sub('<[^>]+>', '', label.text())
print('in the Field:   ', plain(face.this), '|', plain(face.agenda)); save('Pane_00_Field_%s.png' % tag)
v = w.field_page.view; o = next(o for o in v.field.objects if o.title.startswith('07 Bench readings')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); face.show_agenda(); settle(100, 2)
print('a sheet open:   ', plain(face.this), '|', plain(face.agenda)); ok &= '07 Bench readings' in plain(face.this)
save('Pane_01_One_View_%s.png' % tag)
face.this.linkActivated.emit('more'); settle(300, 3); print('“more” ->', type(w.console_pages.currentWidget()).__name__, '| title:', repr(title.text())); ok &= w.console_pages.currentWidget() is w.arc_inspector and title.text().startswith('‹ Stacy') and tabs.isVisible() and title.isVisible()
save('Pane_02_Context_With_The_Way_Back_%s.png' % tag)
QTest.mouseClick(title, Qt.LeftButton); settle(300, 3); print('the title ->', type(w.console_pages.currentWidget()).__name__, '| title:', repr(title.text())); ok &= w.console_pages.currentWidget() is face and title.text() == 'Stacy' and (not tabs.isVisible() if rest is not None else True)
face.agenda.linkActivated.emit('activity'); settle(300, 3); print('“activity” ->', type(w.console_pages.currentWidget()).__name__, '| title:', repr(title.text())); ok &= w.console_pages.currentWidget() is w.operations_panel
save('Pane_03_Activity_With_The_Way_Back_%s.png' % tag); QTest.mouseClick(title, Qt.LeftButton); settle(300, 3); ok &= w.console_pages.currentWidget() is face
print('PANE PROBE', 'PASS' if ok else 'FAIL')
