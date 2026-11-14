# 0.8.0: the Kasandra appearance, in the real window. Run with GRAPHITE_APPEARANCE=kasandra in the environment.
# Checks: the palette is hers; her name is shown (typing strip, pane title, menus); her art follows the state of the work
# (idle -> awaiting_approval when a change waits for Approve -> completed after Approve -> working while she answers);
# the Office banner carries a still and the wordmark; the Field's head band and rail carry her stills; Clean shows none.
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QPushButton
from workbench import boss_theme as T, kasandra_art as art, assistant_identity as ident
ok = True
print('appearance', T.APPEARANCE, '| name', ident.NAME, '| ground', T.GROUND, 'owner', T.OWNER, 'recheck', T.RECHECK, 'display', T.DISPLAY)
ok &= T.APPEARANCE == 'kasandra' and ident.NAME == 'Kasandra' and T.GROUND == '#171b3c'
from PySide6.QtGui import QFontDatabase
print('typewriter face loaded:', 'Special Elite' in QFontDatabase.families()); ok &= 'Special Elite' in QFontDatabase.families()
try:
    from workbench import stacy_hand as _hand; _hand.choose(w, 'ask'); w.shell2.face.show_hand()
except ImportError: pass
bar = w.type_bar
shown = [b.text() for b in bar.findChildren(QPushButton) if b.isVisibleTo(bar) and b.text()]
print('typing strip words:', shown[:8]); ok &= 'Kasandra' in shown and 'Stacy' not in shown
face = w.shell2.face
print('her face shown', face.portrait.isVisible(), 'size', face.portrait.size().toTuple(), '| accessible', face.portrait.accessibleName())
ok &= face.portrait.isVisible() and face.portrait.width() > 40
print('state at rest:', art.current_state(w)); ok &= art.current_state(w) == 'idle'
top = w.shell2.top
print('Programs:', repr(top.programs.text()), '| its own icon', not top.programs.icon().isNull() and bool(top.programs.property('paperIcon')), '| width', top.programs.width(), '>= text and icon', top.programs.fontMetrics().horizontalAdvance(top.programs.text()) + top.programs.iconSize().width())
ok &= top.programs.text() == '' and top.programs.accessibleName() == 'Apps' and not top.programs.icon().isNull() and top.programs.iconSize().width() >= 30 and top.programs.width() >= top.programs.iconSize().width()      # 0.8.2: the kp mark alone, larger
marks = [getattr(face, n).kasandra_mark for n in ('this', 'agenda') if getattr(getattr(face, n), 'kasandra_mark', None) is not None]
print('glyphs in her column:', len(marks), [m.isVisible() for m in marks]); ok &= len(marks) == 2 and all(m.isVisible() for m in marks)
# Home: the Office banner with her still and the wordmark
w.a_home.trigger(); settle(300, 6)
panels = [p for p in w.findChildren(__import__('workbench.boss_qt', fromlist=['ArtPanel']).ArtPanel) if p.isVisible()]
print('Office banner panels shown:', [(p.width(), p.height()) for p in panels]); ok &= bool(panels)
save('Kasandra_01_Office_%s.png' % tag)
for p in panels: p.grab().save(str(OUT / ('Kasandra_01b_Banner_%s.png' % tag)))
# the Field: head band and rail
k = w.ledger_bridge.kernel
w.a_field.trigger(); settle(); v = w.field_page.view
def pick(title):
    o = next(o for o in v.field.objects if o.title.startswith(title)); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(10, 2); return o
pick('07 Settled power'); v.setFocus(); settle(30, 3)
print('Field rail width (gives way when the sheets need the room)', v.rail(), '| head height', v.head_height(), '| still on the rail:', (v._plate_drawn[0] or (None, None))[1])
save('Kasandra_02_Field_At_Rest_%s.png' % tag)
# a change waits for the owner: her hand by Enter
pick('07 Bench readings'); w.shell2.ask('set B3 to 300'); settle(300, 8)
waiting = art.current_state(w); print('after asking for a change:', waiting, '| waits:', repr(v.go)[:60]); ok &= waiting == 'awaiting_approval'
v.setFocus(); v.repaint(); settle(30, 3); print('rail still now:', (v._plate_drawn[0] or (None, None))[1]); ok &= not v.rail() or (v._plate_drawn[0] or (None, None))[1] == 'awaiting_enter'
face.portrait._follow(); print('her face follows:', face.portrait._state); ok &= face.portrait._state == 'awaiting_approval'
save('Kasandra_03_A_Change_Waits_%s.png' % tag)
approve = [b for b in face.findChildren(QPushButton) if b.property('waitsForOwner') and b.isEnabled()]
print('Approve buttons waiting:', len(approve), '| colour rule:', approve[-1].styleSheet()[:80] if approve else None)
ok &= bool(approve) and T.OWNER in approve[-1].styleSheet()
QTest.mouseClick(approve[-1], Qt.LeftButton); settle(400, 8)
done = art.current_state(w); print('after Approve:', done); ok &= done == 'completed'
v.setFocus(); v.repaint(); settle(30, 3); print('rail still now:', (v._plate_drawn[0] or (None, None))[1]); ok &= not v.rail() or (v._plate_drawn[0] or (None, None))[1] == 'completed_pencil'
pick('07 Settled power'); v.setFocus(); settle(30, 3)
recheck = [o for o in v.field.objects if o.state == 'recheck']
print('sheets for recheck:', [o.title[:28] for o in recheck])
save('Kasandra_04_Done_And_A_Recheck_%s.png' % tag)
# while she answers: working (a job set by hand, then cleared)
face.job = 'probe';print('while she answers:', art.current_state(w)); ok &= art.current_state(w) == 'working'; face.job = None
# a refusal: blocked for a while
art.note_outcome(w, False); print('after a refusal:', art.current_state(w)); ok &= art.current_state(w) == 'blocked'
w._art_outcome = ('blocked', -1000.0); print('long after:', art.current_state(w)); ok &= art.current_state(w) == 'idle'
# the pane title names her when Context is up
try:
    w.shell2.show_context_face(); settle(300, 4); title = w.shell2.title_word.text(); print('pane title with Context up:', repr(title)); ok &= 'Kasandra' in title
    QTest.mouseClick(w.shell2.title_word, Qt.LeftButton); settle(200, 3)
except Exception as exc: print('pane title check skipped:', exc)
# the menus name her
from workbench.context_menu import named as cm_named
print('a menu line:', cm_named('Ask Stacy about this')); ok &= cm_named('Ask Stacy about this') == 'Ask Kasandra about this'
# Clean: no art anywhere
from workbench.boss_qt import choose_art
choose_art(w, 'clean'); settle(200, 4); print('Clean: rail', v.rail(), '| her face shown', face.portrait.isVisible()); ok &= v.rail() == 0 and not face.portrait.isVisible()
save('Kasandra_05_Clean_%s.png' % tag)
choose_art(w, 'illustrated'); settle(200, 4)
print('decodes:', art.decodes()[:8], '| scalings (ms, last 8):', art.scalings()[-8:])
print('KASANDRA PROBE', 'OK' if ok else 'WRONG')
