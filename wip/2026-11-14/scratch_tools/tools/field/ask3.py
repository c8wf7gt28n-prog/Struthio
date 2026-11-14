# with the real small model: T (trace) told in her words, what-if told in her words
exec(open(S / 'tools/field/ask1.py').read().split("w.shell2.show_slate_face()")[0])
w.shell2.show_slate_face(); settle(); face.refresh()
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title); v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
def after(seconds=300):
    t = time.time(); settle(80, 3)
    while face.job and time.time() - t < seconds: settle(150, 3)
    settle(120, 4); return time.time() - t
n = len(bubbles()); QTest.keyClick(v, Qt.Key_T); took = after()
print('T (trace), %.1f s:' % took)
for card in bubbles()[n + 1:]:
    for line in words(card)[:4]: print('   |', line[:330].replace('\n', '\n   |   '))
save('Graphite_Power_03_Trace_With_A_Model_%s.png' % tag)
ask('what if B3 were 320?')
save('Graphite_Power_04_What_If_With_A_Model_%s.png' % tag)
ask('what if the voltage were 11.4 and the settled current 350?')
