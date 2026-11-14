"""W9 follow-up: the Field keeps its reading while the journal's head stands still. A sheet's original changed on disk outside Graphite."""
from winbase import *
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel; P = operator()
def call(op, args=None):
    a = k.dispatch(op, args or {}, P)
    if not a.get('ok'): print('   REFUSED', op, a.get('error'))
    return a.get('result') if a.get('ok') else None
csv = root / 'probe_limits.csv'; csv.write_text('rail,limit_ms\n3V3,80\n5V,120\n')
plan = call('office.import.preview', {'path': str(csv)}); print('   import preview keys:', sorted(plan)[:12] if plan else None)
done = call('office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']}) if plan else None
print('   committed:', {k2: done[k2] for k2 in list(done)[:4]} if done else None)
rows = call('office.list')['documents']; mine = next((r for r in rows if 'probe_limits' in str(r.get('title', '')).lower() or 'probe' in str(r).lower()), None); print('   sheet row:', mine and (mine['id'], mine.get('title')))
def state(): return (call('office.get', {'id': mine['id']}) or {}).get('source_state', {}).get('state')
def head(): return call('ledger.journal.status')['head']
v = field(); obj = next((o for o in v.field.objects if o.id == 'office:' + mine['id']), None)
print('   Field shows it:', obj and (obj.title, obj.state, obj.lines), '| record says:', state(), '| journal head', head())
QTest.keyClick(v, Qt.Key_Escape); settle()
h0 = head(); csv.write_text('rail,limit_ms\n3V3,95\n5V,120\n')      # the original is changed outside Graphite (another program saves it)
print('   original changed on disk; record now says:', state(), '| journal head moved:', head() != h0)
v = field(); obj = v.field.get('office:' + mine['id']); stale = [l for l in v.field.links if l.stale]
print('   F9 -> the Field shows the sheet as: %r (census %s) | record says: %s' % (obj.state, [c for c in v.field.census() if 'recheck' in c], state()))
w.a_field.trigger(); settle(); print('   F9 again while showing ->', v.field.get('office:' + mine['id']).state)
QTest.keyClick(v, Qt.Key_Escape); settle(); v = field(); print('   Esc, F9 ->', v.field.get('office:' + mine['id']).state)
w.resize(1600, 1000); settle(); print('   after a resize ->', v.field.get('office:' + mine['id']).state)
QTest.keyClick(v, Qt.Key_R); settle(); print('   R -> the Field shows the sheet as: %r (census %s)' % (v.field.get('office:' + mine['id']).state, [c for c in v.field.census() if 'recheck' in c]))
finish()
