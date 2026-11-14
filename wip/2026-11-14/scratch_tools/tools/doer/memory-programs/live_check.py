import sys, json, time, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs')
import last_touched as lt
from full_window import full_window
from workbench import explore, version
k = w.ledger_bridge.kernel; p = operator()
print('version:', getattr(version, 'VERSION', None) or [x for x in dir(version) if not x.startswith('_')][:6])
print('seed:', k.dispatch('stacy.seed.status', {}, p)['result']['state'])
w.a_field.trigger(); settle(); v = w.field_page.view
out = lt.last_touched(k, p, v.field); print('last_touched on the live tree:', len(out), 'of', len(v.field.objects), 'objects have a time')
print('full_window(freecad, no file):', full_window(k, p, 'freecad', ''))
QTest.keyClick(v, Qt.Key_P); settle(30, 4)
fc = next(o for o in v.field.objects if o.id == 'app:freecad'); v.field.select(fc.id); v.update(); settle(5, 2)
got = []; v.full_asked.connect(lambda o: got.append(o.id)) if hasattr(v, 'full_asked') else None
QTest.keyClick(v, Qt.Key_F); settle(60, 4); where('F on app:freecad'); print('full_asked emitted:', got, '| status bar:', repr(w.statusBar().currentMessage()))
from workbench import field_do
print('field_do.steps_for(app:freecad):', field_do.steps_for(k, p, fc, v.field))
