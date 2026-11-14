from workbench import boss_qt
w.a_field.trigger(); settle(); v = w.field_page.view; v.setFocus()
o = next(o for o in v.field.objects if o.title.startswith('07 Settled power')); v.field.select(o.id); v._reveal(); v._describe(); v.update(); settle(10, 2)
def amberish(img):
    n = 0
    for y in range(0, img.height(), 2):
        for x in range(0, img.width(), 2):
            c = img.pixelColor(x, y)
            if c.red() > 60 and c.red() > c.blue() * 1.8 and c.red() > c.green() * 1.15: n += 1
    return n
r = v.sheet_rect(o.id, v._layout()).adjusted(-16, -16, 16, 16).toRect()
lit = amberish(v.grab(r).toImage()); boss_qt.choose_art(w, 'clean'); settle(40, 3); v.setFocus(); v.repaint(); settle(10, 2)
plain = amberish(v.grab(r).toImage()); save('Graphite_Amber_05_Clean_%s.png' % tag); boss_qt.choose_art(w, 'illustrated'); settle(40, 3)
print('amber pixels around the selected sheet: Illustrated %d, Clean %d (the edge and ticks remain, the glow does not)' % (lit, plain))
