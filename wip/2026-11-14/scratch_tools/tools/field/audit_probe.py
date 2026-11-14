# one home for each thing: the facts of the 0.4.9 audit, asked of the running window
from PySide6.QtWidgets import QPushButton, QToolButton, QMenu, QComboBox
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); v.repaint(); settle(20, 2); bar = w.centre_bar
places = [words for b, k, tx, words in v._hot]
print('Field click places:', [p_[:22] for p_ in places])
print('   no Open button (a click on a sheet opens it):', not any(p_.startswith('Open') for p_ in places), '| no words that scroll (the bars do):', not any(p_.startswith('Move') for p_ in places),
      '| the faces once (at the head):', sum(1 for p_ in places if 'face of the Field' in p_) == 2, '| what waits once (the lamp):', sum(1 for p_ in places if 'next thing that waits' in p_) <= 1,
      '| Z once (the strip):', sum(1 for p_ in places if p_.startswith(('Whole desk', 'Ordinary size'))) <= 1)
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8); return w.tabs.currentWidget()
def menu_of(button):
    button.menu().aboutToShow.emit(); return [a.text() for a in button.menu().actions() if not a.isSeparator()]
page = open_tile('07 Bench readings'); bar.sync()
print('sheet: the strip under the work shows:', w.concern.context_strip.isVisible(), '| the bar:', [b.text() for b in bar.findChildren(QPushButton)], '| Save lit with nothing to save:', bar.save.isEnabled(), '|', bar.save.toolTip()[:48])
print('   More:', menu_of(page.more))
sheet = page.current_sheet(); cell = dict(sheet['cells']['B3']); cell['value'] = '290'; sheet['cells']['B3'] = cell; page.refresh_table(); page.set_dirty(); bar.sync()
print('   a cell changed -> Save lit:', bar.save.isEnabled(), repr(bar.save.text())); QTest.mouseClick(bar.save, Qt.LeftButton); settle(300, 6); bar.sync(); print('   pressed -> unsaved:', page.is_dirty(), '| Save lit:', bar.save.isEnabled())
page = open_tile('07_Bench_Readings.pdf'); bar.sync()
shown = [b.text() for b in page.findChildren(QPushButton) if b.isVisible()] + [b.text() for b in page.findChildren(QToolButton) if b.isVisible()] + ['[size choice]' for c in page.findChildren(QComboBox) if c.isVisible() and c is page.zoom]
print('PDF: in view:', shown, '| its own heading shows:', page.heading.isVisible(), '| the bar says:', repr(bar.title.text()))
print('   More:', menu_of(page.more))
z0 = page.zoom.currentText(); QTest.mouseClick(bar.larger, Qt.LeftButton); settle(80, 3); z1 = page.zoom.currentText(); QTest.mouseClick(bar.smaller, Qt.LeftButton); settle(80, 3)
print('   + in the bar: page size', z0, '->', z1, '| − brings it back:', page.zoom.currentText(), '| Save lit with no note typed:', bar.save.isEnabled())
page.editor.setPlainText('a note typed by the probe'); settle(60, 3); bar.sync(); print('   a note typed -> Save lit:', bar.save.isEnabled(), repr(bar.save.text()))
page = open_tile('07 Case conclusion'); bar.sync(); print('writing page: Save lit:', bar.save.isEnabled(), '|', bar.save.toolTip()[:60])
work = next(b for b in w.findChildren(QToolButton) if b.objectName() == 'MoreMenus').menu(); work.aboutToShow.emit(); found = []
for a in work.actions():
    if a.menu() is not None and a.text().replace('&', '') != 'Tools':
        a.menu().aboutToShow.emit(); found += [a.text().replace('&', '') for x in a.menu().actions() if x.text().replace('&', '') == 'Desk artwork']
print('Work menu: “Desk artwork” is under', found)
