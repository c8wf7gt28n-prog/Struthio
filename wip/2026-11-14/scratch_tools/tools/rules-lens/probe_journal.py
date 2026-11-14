import sys, time, json, sqlite3
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from workbench import field_page
calls = []
real_dispatch = Kernel.dispatch
def counted(self, operation, params=None, principal=None):
    t = time.perf_counter()
    try: return real_dispatch(self, operation, params, principal)
    finally: calls.append((operation, time.perf_counter() - t, getattr(principal, 'identity', None)))
Kernel.dispatch = counted
open_window(); settle(50, 30)
def journal_tail(n):
    db = sqlite3.connect('file:%s?mode=ro' % (RUN / ('ws' if CASE else '') / '.ledger/engineering.sqlite3'), uri=True) if CASE else None
    if db is None: return []
    rows = [(seq, json.loads(p)) for seq, p in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT ?', (n,))]
    db.close(); return rows
A = snapshot(); calls.clear()
settle(50, 30)
B = snapshot(); idle_calls = list(calls); calls.clear()
diff(A, B, 'IDLE baseline (window open, nothing done, 30 settles)')
print('  dispatches while idle:', sorted({c[0] for c in idle_calls}), len(idle_calls))
# (i) pure: show_field / leave_field three times, from the plain workspace
for n in range(3):
    calls.clear(); t = time.perf_counter(); w.show_field(); dt = time.perf_counter() - t
    field_calls = [c for c in calls]
    print('show_field #%d: %.1f ms, %d dispatches (%s), refused=%s' % (n + 1, dt * 1000, len(field_calls), ', '.join('%s x%d' % (op, sum(1 for c in field_calls if c[0] == op)) for op in sorted({c[0] for c in field_calls})), w.field_page.refused))
    print('   time inside dispatch: %.1f ms; by op: %s' % (sum(c[1] for c in field_calls) * 1000, ', '.join('%s %.1f' % (op, 1000 * sum(c[1] for c in field_calls if c[0] == op)) for op in sorted({c[0] for c in field_calls}))))
    settle(30, 4); field_page.leave_field(w); settle(30, 4)
C = snapshot(); after = list(calls); calls.clear()
diff(B, C, 'FIELD shown 3 times by show_field()/leave_field() (plus 24 settles)')
print('  other dispatches in that period:', sorted({c[0] for c in after}))
settle(50, 30)
D = snapshot(); diff(C, D, 'IDLE again (30 settles)'); calls.clear()
# (ii) realistic: F9 then Esc, three times (Esc with no tab open returns to Home)
for n in range(3):
    w.a_field.trigger(); settle(30, 4); QTest.keyClick(w.field_page.view, Qt.Key_Escape); settle(30, 4)
E = snapshot(); diff(D, E, 'F9 then Esc, three times (Esc lands on Home when no tab is open)'); print('  dispatches:', sorted({c[0] for c in calls})); calls.clear()
where('after F9/Esc x3')
# baseline for Home alone
for n in range(3):
    w._close_start(); settle(30, 4); w.show_start(); settle(30, 4)
F = snapshot(); diff(E, F, 'Home closed and shown three times (baseline for the Esc landing)'); print('  dispatches:', sorted({c[0] for c in calls}))
for seq, ev in journal_tail(6): print('   journal', seq, ev.get('origin'), ev.get('operation'), ev.get('state'))
w._closing = True; print('DONE')
