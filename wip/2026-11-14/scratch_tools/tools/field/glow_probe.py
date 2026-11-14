# the glow dial, the circuit tree and the head, in pictures at each level
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItemIterator, QApplication
from workbench import boss_qt, boss_theme as t
print('opens with glow:', w.session.state.get('glow', '(nothing chosen)'), '| level in force:', t.glow())
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus(); settle()
tree = w.nav
it = QTreeWidgetItemIterator(tree); deep = None
while it.value() is not None:
    item = it.value()
    if item.text(0) in ('Questions', 'Documents') and item.parent() is not None: deep = item
    it += 1
if deep is not None:
    p = deep.parent()
    while p is not None: p.setExpanded(True); p = p.parent()
    tree.setCurrentItem(deep); settle(150, 2); print('tree: current row', deep.text(0), 'under', deep.parent().text(0))
for key in ('soft', 'bright', 'neon'):
    boss_qt.choose_glow(w, key); settle(250, 3); print('glow', key, '-> level', t.glow(), '| kept:', w.session.state.get('glow'))
    w.a_field.trigger(); settle(150, 3); save('Glow_%s_Field_%s.png' % (key, tag))
boss_qt.choose_glow(w, 'bright'); settle(200, 3)
o = next(o for o in v.field.objects if o.title.startswith('07 Bench readings')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8)
save('Glow_bright_Page_%s.png' % tag)
boss_qt.choose_art(w, 'clean'); settle(250, 3); w.a_field.trigger(); settle(150, 3); save('Glow_clean_desk_Field_%s.png' % tag); boss_qt.choose_art(w, 'illustrated'); settle(200, 3)
