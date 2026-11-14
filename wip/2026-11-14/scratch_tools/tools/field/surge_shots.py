# 0.8.2 the surge: frames of Trace on 07 Bench readings at fixed moments of its clock, and the settled route.
from PySide6.QtCore import QRect
w.a_field.trigger(); settle(400, 5); v = w.field_page.view
print('texture', v.texture, 'glow', __import__('workbench.boss_theme', fromlist=['glow']).glow())
for title in ('07_Bench_Readings.pdf', 'Settled draw is'):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    if o is None: print('no', title); continue
    v.field.select(o.id); v._reveal(); v._describe(); v.update(); v.setFocus(); settle(150, 3)
    route, hops, ends = v.trace_route(o.id)
    print(title, '| route links', len(route), 'hops', hops, 'ends', [v.field.get(e).title for e in ends])
    v.surge(o.id); settle(30, 1); v._surge_timer.stop()
    real = type(v).surge_elapsed
    name = ''.join(ch for ch in title if ch.isalnum())[:18]
    for n, at in enumerate((0.20, 0.45, 0.72, 0.80, 1.00, 1.20, None)):
        v.surge_elapsed = (lambda at=at: at); v.repaint(); settle(20, 1)
        img = v.grab().toImage()
        img.save(str(OUT / ('Surge_%s_%02d_%s_%s.png' % (name, n, 'settled' if at is None else '%03dms' % int(at * 1000), tag))))
    v.surge_elapsed = real.__get__(v)
    # a second trace takes over; a selection move clears it
    v.surge(o.id); v.field.select(next(x.id for x in v.field.objects if x.id != o.id)); v.repaint(); print('after the selection moved, route:', v._route)
    v.field.select(o.id); v.update(); settle(50, 1)
# reduced motion: straight to the settled route
v.still = lambda: True; v.surge(v.field.selected); print('reduced motion: animated?', v._surge_timer.isActive(), '| at', v._route['at'])
print('SURGE SHOTS DONE')
