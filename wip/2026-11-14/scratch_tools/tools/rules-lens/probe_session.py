import sys, time, json, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from workbench import field_page
MODE = os.environ.get('PROBE_MODE', 'field')
sess = RUN / 'prof/session.json'
def read(): return json.loads(sess.read_text())
open_window(); settle(50, 20)
before = read(); print('session.json bytes before:', sess.stat().st_size, 'keys', sorted(before))
import traceback
from workbench import session as session_mod
real_save = session_mod.Session.save
def traced(self, *a, **k):
    print('--- Session.save called from:'); print(''.join(traceback.format_stack(limit=9)[:-1]))
    return real_save(self, *a, **k)
session_mod.Session.save = traced
if MODE == 'field':
    w.a_field.trigger(); settle(30, 4); print('after F9: bytes', sess.stat().st_size)
    QTest.keyClick(w.field_page.view, Qt.Key_Escape); settle(30, 4); print('after Esc: bytes', sess.stat().st_size)
elif MODE == 'home':
    w.show_start(); settle(30, 4); print('after Home: bytes', sess.stat().st_size)
    w._close_start(); settle(30, 4); print('after closing Home: bytes', sess.stat().st_size)
elif MODE == 'fieldonly':
    w.show_field(); settle(30, 4); print('after show_field: bytes', sess.stat().st_size)
    field_page.leave_field(w); settle(30, 4); print('after leave_field: bytes', sess.stat().st_size)
after = read()
for key in sorted(set(before) | set(after)):
    if before.get(key) != after.get(key): print('  changed key %-28s %r -> %r' % (key, str(before.get(key))[:160], str(after.get(key))[:160]))
w._closing = True; print('DONE')
