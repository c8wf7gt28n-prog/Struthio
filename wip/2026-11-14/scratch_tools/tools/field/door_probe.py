# 0.7.0: the System menu dissolved. Each meter is a door; leaving is under Work; the game is in Programs; Stacy's pane has
# no name tag and no two links; the typing line has its own expand.
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QAbstractButton
top = w.shell2.top; bar = w.type_bar; mon = bar.monitors.findChild(type(top.pulse)) if hasattr(top, 'pulse') else None
mon = top.pulse; face = w.shell2.face; ok = True; settle(700, 3); align()
print('head: System button shown', top.nice.isVisible(), '| Programs shown', top.programs.isVisible(), 'right edge', top.programs.geometry().right(), 'of', top.width(), '| equalizer', top.equalizer.geometry().getRect())
ok &= not top.nice.isVisible() and top.programs.isVisible() and top.programs.geometry().right() >= top.width() - 40
def click_meter(key):
    v = mon.values[key]; at = v.mapTo(mon, v.rect().center()); QTest.mouseClick(mon, Qt.LeftButton, pos=at); settle(350, 4); return getattr(w, '_meter_card', None)
def words(card): return [b.text() for b in card.findChildren(QPushButton) if b.isVisibleTo(card) and b.text()]
def lines(card): return [l.text()[:90] for l in card.findChildren(QLabel) if l.isVisibleTo(card) and l.text()]
def inside(card): g = card.frameGeometry(); o = w.mapToGlobal(QPoint(0, 0)); return g.left() >= o.x() and g.right() <= o.x() + w.width() and g.top() >= o.y() and g.bottom() <= o.y() + w.height()
# CPU: Graphite's work
c = click_meter('CPU'); print('CPU ->', type(c).__name__, 'shown', c.isVisible(), '| inside the window', inside(c), '| words:', words(c)[:8], '|', c.title.text())
ok &= c.isVisible() and inside(c) and 'Open Agenda' in words(c) and 'Work trail' in words(c) and 'Game' not in words(c) and c.kill.isVisible()
c.grab().save(str(OUT / ('Door_CPU_%s.png' % tag))); save('Door_00_CPU_%s.png' % tag); c.hide(); settle(100, 2)
# GPU: the model and the services
c = click_meter('GPU'); print('GPU ->', 'shown', c.isVisible(), 'inside', inside(c), '| words:', words(c), '|', lines(c)[:3])
ok &= c.isVisible() and inside(c) and 'Brain room' in words(c) and all(x in words(c) for x in ('On', 'Off', 'Restart'))
c.grab().save(str(OUT / ('Door_GPU_%s.png' % tag))); before = w.tabs.count(), type(w.tabs.currentWidget()).__name__
QTest.mouseClick(c.words['Brain room'], Qt.LeftButton); settle(600, 6); print('   Brain room -> card gone:', not c.isVisible(), '| in the centre:', type(w.tabs.currentWidget()).__name__, getattr(w.tabs.currentWidget(), 'objectName', lambda: '')()); ok &= not c.isVisible()
# RAM: memory and Machine
c = click_meter('RAM'); print('RAM ->', 'shown', c.isVisible(), 'inside', inside(c), '| words:', words(c), '|', lines(c)[:4]); ok &= c.isVisible() and inside(c) and words(c) == ['Machine']
c.grab().save(str(OUT / ('Door_RAM_%s.png' % tag)))
nav = w.settings_navigator; QTest.mouseClick(c.words['Machine'], Qt.LeftButton); settle(500, 5); print('   Machine -> the left pane shows:', [b.text() for b in nav.bar.buttons if b.isChecked()]); ok &= [b.text() for b in nav.bar.buttons if b.isChecked()] == ['Machine']
nav.bar.buttons[0].click(); settle(200, 3)
# TXT: the conversation
c = click_meter('TXT'); print('TXT ->', 'shown', c.isVisible(), 'inside', inside(c), '| words:', words(c), '|', lines(c)[:2]); ok &= c.isVisible() and inside(c) and words(c) == ['Full chat', 'What she has in view']
c.grab().save(str(OUT / ('Door_TXT_%s.png' % tag)))
tabs = w.shell2.face_tabs; print('   Stacy’s pane at rest: title row shown', tabs.isVisible(), '| her face starts at y', face.portrait.mapTo(w.right_pane, QPoint(0, 0)).y(), '| links in it:', [b.text() for b in face.findChildren(QPushButton) if b.text() in ('Brain room', 'Full chat')])
ok &= not tabs.isVisible() and not [b for b in face.findChildren(QPushButton) if b.text() in ('Brain room', 'Full chat')] and face.portrait.mapTo(w.right_pane, QPoint(0, 0)).y() < 40
QTest.mouseClick(c.words['What she has in view'], Qt.LeftButton); settle(500, 5); title = w.shell2.title_word
print('   What she has in view -> pane shows', type(w.console_pages.currentWidget()).__name__, '| title row shown', tabs.isVisible(), repr(title.text())); ok &= w.console_pages.currentWidget() is w.arc_inspector and tabs.isVisible() and title.text().startswith('‹ Stacy')
save('Door_01_Context_With_The_Way_Back_%s.png' % tag)
QTest.mouseClick(title, Qt.LeftButton); settle(400, 4); print('   the title -> back to her:', w.console_pages.currentWidget() is face, '| title row shown', tabs.isVisible()); ok &= w.console_pages.currentWidget() is face and not tabs.isVisible()
# leaving is under Work; the game is among the programs
work = w.menu_groups['File']; work.aboutToShow.emit(); last = [a.text().replace('&', '') for a in work.actions() if not a.isSeparator()][-4:]
print('the Work menu ends:', last); ok &= last[0] == 'Log out' and last[2:] == ['Restart', 'Shut down'] and last[1] in ('Exit Graphite', 'Return to Debian')
programs = bar.hatch.programs; rows = [r.word for r in programs.page.findChildren(type(programs.explore_row))]; print('Programs ends:', rows[-2:]); ok &= rows[-1] == 'Game'
# the line's expand
con = w.console; e = bar.expand; seen = [con.size_level]
for _ in range(3): QTest.mouseClick(e, Qt.LeftButton); settle(250, 3); seen.append(con.size_level)
print('expand shown', e.isVisible(), e.geometry().getRect(), '| sizes on three clicks:', seen, '| it says', repr(e.toolTip())); ok &= e.isVisible() and seen == [0, 1, 2, 0] and e.geometry().right() < bar.box.geometry().left()
QTest.mouseClick(bar.targets['shell'], Qt.LeftButton); settle(200, 3); QTest.mouseClick(e, Qt.LeftButton); settle(300, 3)
bar.box.setFocus(); QTest.keyClicks(bar.box, 'echo graphite-expands'); QTest.mouseClick(bar.send, Qt.LeftButton); settle(1500, 8)
out = con.output.toPlainText() if hasattr(con.output, 'toPlainText') else ''; print('Terminal, expanded, “echo graphite-expands” -> size', con.size_level, '| page', con.mode, '| the output shows it:', 'graphite-expands' in out, '| control says', repr(e.toolTip()))
ok &= con.size_level == 1 and 'graphite-expands' in out
save('Door_02_The_Line_Expanded_On_The_Terminal_%s.png' % tag)
QTest.mouseClick(bar.targets['log'], Qt.LeftButton); settle(400, 4); view = w.log_view; print('Log, expanded: its streams are chosen at its top:', [b.text() for b in view.findChildren(QAbstractButton) if b.text() in ('Events', 'Network') and b.isVisibleTo(view)]); save('Door_03_Log_Expanded_%s.png' % tag)
con.set_size(0); QTest.mouseClick(bar.targets['slate'], Qt.LeftButton); settle(300, 3)
save('Door_04_At_Rest_%s.png' % tag)
print('DOOR PROBE', 'PASS' if ok else 'FAIL')
print('DONE')
