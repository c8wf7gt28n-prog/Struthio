# with the real small model: X (doubt) told in her words
exec(open(S / 'tools/field/ask1.py').read().split("w.shell2.show_slate_face()")[0])
w.shell2.show_slate_face(); settle(); face.refresh()
w.a_field.trigger(); settle(); v = w.field_page.view
def after(seconds=300):
    t = time.time(); settle(80, 3)
    while face.job and time.time() - t < seconds: settle(150, 3)
    settle(120, 4); return time.time() - t
for wordsin in ('keeps the 80 ms', 'Startup ran 30 ms', '07 Settled power'):
    o = next(x for x in v.field.objects if wordsin in x.title); v.field.select(o.id); v._describe(); v.update(); settle(5, 2)
    n = len(bubbles()); QTest.keyClick(v, Qt.Key_X); took = after()
    cardsnow = bubbles()[n + 1:]
    print('\nX on “%s” (%.1f s)' % (o.title[:50], took))
    for line in words(cardsnow[0])[2:3]: print('   rows |', line[:520].replace('\n', '\n        |   '))
    if len(cardsnow) > 1: print('   HER WORDS |', words(cardsnow[-1])[0][:420])
    if 'keeps' in wordsin: save('Graphite_Doubt_04_With_A_Model_%s.png' % tag)
