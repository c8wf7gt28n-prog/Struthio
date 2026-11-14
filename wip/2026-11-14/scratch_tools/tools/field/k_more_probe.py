nav = w.settings_navigator
for i, b in enumerate(nav.bar.buttons):
    b.click(); settle(300, 4); save('KMore_%d_%s_%s.png' % (i, b.text(), tag))
nav.bar.buttons[0].click(); settle(200, 3)
try:
    from workbench import meter_cards
    w.shell2.top  # the Brain room through the GPU card's word
    mon = w.shell2.top.pulse; v = mon.values['GPU']; QTest.mouseClick(mon, Qt.LeftButton, pos=v.mapTo(mon, v.rect().center())); settle(300, 4)
    c = w._meter_card; QTest.mouseClick(c.words['Brain room'], Qt.LeftButton); settle(600, 6); save('KMore_Brain_room_%s.png' % tag)
except Exception as exc: print('brain room:', exc)
