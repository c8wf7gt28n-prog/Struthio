# 0.8.0, the owner: "I know sometimes scrolling is unavoidable, but if we can really try to eliminate or reduce it as much
# as possible." On each main surface, every visible scroll area whose content is larger than its window, and by how much;
# and the Field's own surface against its room. Prints one line per overflow: SCROLL <surface> | <widget> | <axis> <px> of <view px>.
from PySide6.QtWidgets import QAbstractScrollArea, QPushButton
rows = []
def name_of(x):
    parts = []
    while x is not None and len(parts) < 4:
        parts.append(x.objectName() or type(x).__name__);x = x.parentWidget()
    return '<'.join(parts)
def census(surface):
    settle(150, 3); align()
    for a in w.findChildren(QAbstractScrollArea):
        if not a.isVisible() or a.width() < 40 or a.height() < 30:continue
        vb, hb = a.verticalScrollBar(), a.horizontalScrollBar()
        if vb.maximum() > 0:rows.append((surface, name_of(a), 'v', vb.maximum(), a.viewport().height()))
        if hb.maximum() > 0:rows.append((surface, name_of(a), 'h', hb.maximum(), a.viewport().width()))
    if getattr(w, '_field_active', False):
        v = w.field_page.view;v._layout();room = v.room(v.body())
        over_x, over_y = v._surface[0] - room[0], v._surface[1] - room[1]
        if over_x > 1:rows.append((surface, 'FieldView', 'h', round(over_x * v.zoom), round(room[0] * v.zoom)))
        if over_y > 1:rows.append((surface, 'FieldView', 'v', round(over_y * v.zoom), round(room[1] * v.zoom)))
census('start')
w.a_home.trigger(); census('Home')
w.a_field.trigger(); settle(300, 4); v = w.field_page.view
def pick(title):
    o = next(o for o in v.field.objects if o.title.startswith(title)); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(30, 2); return o
pick('07 Bench readings'); census('Field')
w.shell2.ask('set B3 to 300'); settle(400, 8); census('Field, a change waits')
approve = [b for b in w.shell2.face.findChildren(QPushButton) if b.property('waitsForOwner') and b.isEnabled()]
if approve:QTest.mouseClick(approve[-1], Qt.LeftButton); settle(400, 8)
census('Field, after Approve')
for title, label in (('07 Bench readings', 'Sheet page'), ('07_Bench_Readings', 'PDF page'), ('07 Case conclusion', 'Writing page'), ('Settled draw', 'Finding page')):
    try:
        w.a_field.trigger(); settle(200, 3); o = pick(title); QTest.keyClick(v, Qt.Key_Return); settle(500, 6); census(label)
    except Exception as exc:print('could not open', title, exc)
nav = w.settings_navigator
for b in nav.bar.buttons:
    b.click(); settle(300, 4); census('Left pane: ' + b.text())
nav.bar.buttons[0].click(); settle(100, 2)
mon = w.shell2.top.pulse
for key in ('CPU', 'GPU', 'RAM', 'TXT'):
    val = mon.values[key]; QTest.mouseClick(mon, Qt.LeftButton, pos=val.mapTo(mon, val.rect().center())); settle(300, 4)
    card = getattr(w, '_meter_card', None)
    if card is not None:
        for a in card.findChildren(QAbstractScrollArea):
            if a.isVisible() and a.verticalScrollBar().maximum() > 0:rows.append(('Meter card ' + key, name_of(a), 'v', a.verticalScrollBar().maximum(), a.viewport().height()))
        if key == 'GPU':
            QTest.mouseClick(card.words['Brain room'], Qt.LeftButton); settle(600, 6); census('Brain room')
        else:card.hide()
    settle(100, 2)
seen = set()
for r in rows:
    if r in seen:continue
    seen.add(r);print('SCROLL %s | %s | %s %d of %d' % r)
print('SCROLL CENSUS', len(seen), 'overflows')
