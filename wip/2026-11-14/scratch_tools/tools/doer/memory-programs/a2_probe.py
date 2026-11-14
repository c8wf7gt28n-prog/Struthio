import json, time, sys, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs')
import last_touched as lt
from workbench import explore
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def stamp(t): return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t)) + ('.%03d' % int((t % 1) * 1000))
w.a_field.trigger(); settle(); v = w.field_page.view
head0 = d('ledger.journal.status')['result']['head']
# raw looks at what each read gives for time
r = d('intake.namespaces')['result']; ns = r['namespaces'][0]; print('intake.namespaces row keys:', sorted(ns.keys()))
it = d('intake.items', {'namespace': ns['id']})['result']['items'][0]; print('intake.items row:', json.dumps(it)[:700])
r = d('intake.read', {'id': it['id']}); print('intake.read:', r['ok'], json.dumps(r.get('result') or r.get('error'))[:500])
r = d('intake.batches', {'namespace': ns['id']}); print('intake.batches:', json.dumps(r.get('result') or r.get('error'))[:500])
inv = d('investigation.list')['result']['investigations'][0]; print('investigation.list row:', json.dumps(inv)[:500])
sh = d('investigation.sheet', {'id': inv['id']})['result']; print('investigation.sheet keys:', sorted(sh.keys())); print('   claim:', json.dumps((sh.get('learned') or sh.get('unresolved'))[0])[:500])
pa = d('investigation.path', {'claim': (sh.get('learned'))[0]['id']})['result']; print('investigation.path:', json.dumps(pa)[:900])
print('   steps on the sheet:', json.dumps(sh.get('steps') or sh.get('trail') or '')[:500])
jl = d('jobs.list')['result']; jl = jl if isinstance(jl, list) else jl.get('jobs'); print('jobs.list:', len(jl), 'row keys', sorted(jl[0].keys())); print('   request_spec of a references.page job:', json.dumps(next(j for j in jl if j['tool'] == 'references.page')['request_spec'])[:400])
print('conditions.list:', json.dumps(d('conditions.list')['result'])[:300])
# touch things, then compute
sid = 'owner:4f357ff3c843489a9758db71e23bf4b4'; got = d('office.get', {'id': sid})['result']; new = copy.deepcopy(got['document']); new['sheets'][0]['cells']['A1']['value'] = 'Parameter '
print('office.save:', d('office.save', {'id': sid, 'expected_revision': got['revision'], 'document': new})['ok'])
doc = next(o for o in v.field.objects if o.id == 'document:0e39bf65e24740a29a504a6be6e00885'); v.field.select(doc.id); v.update(); settle(5, 2); QTest.keyClick(v, Qt.Key_Return); settle(60, 5)
w.a_field.trigger(); settle(); v = w.field_page.view
views = [(row[0], row[7]) for row in explore.VIEWS]
rows = lt.journal(k, p); print('\njournal rows read:', len(rows), '| head', rows[-1]['seq'])
t0 = time.time(); out = lt.last_touched(k, p, v.field, rows); dt = time.time() - t0
print('last_touched took %.2f s; journal head moved by %d (reads are observers)' % (dt, d('ledger.journal.status')['result']['head'] - rows[-1]['seq']))
for key in ('_intake_keys', '_claim_keys', '_path_keys'): print(key, out.pop(key, None))
print('\n{field object id: last touched, operation, how}')
for obj in v.field.objects:
    hit = out.get(obj.id)
    print('  %-52s %-12s %s' % (obj.id, obj.kind, ('%s  %-22s %s' % (stamp(hit[0]), hit[1], hit[2])) if hit else 'NO TIME FOUND'))
print('extra ids with a time:', {i: (stamp(t[0]), t[1]) for i, t in out.items() if i not in {o.id for o in v.field.objects}})
pt = lt.programs_touched(rows, views)
print('\n{shelf key: last time one of its operations ran (journal by operation prefix)}')
for key, (at, what, seq) in sorted(pt.items(), key=lambda kv: -kv[1][0]): print('  app:%-16s %s  %s  seq %d' % (key, stamp(at), what, seq))
unowned = sorted({e['operation'] for e in rows if lt.program_of(e['operation'], views) is None})
print('journal operations no shelf program owns:', unowned)
# the awareness watermark, with a consumer of our own
r = d('ledger.awareness', {'consumer': 'field'}); x = r['result']; print('\nledger.awareness {consumer: field}:', {q: x[q] for q in ('consumer', 'state', 'cursor', 'head', 'backlog')})
r = d('ledger.awareness.catch_up', {'consumer': 'field', 'limit': 200}); x = r['result']; print('ledger.awareness.catch_up:', r['ok'], {q: x[q] for q in ('state', 'cursor', 'head', 'backlog')}, '| projection.last_event', x['projection']['last_event'], '| jobs in projection', len(x['projection']['jobs']))
r = d('ledger.awareness.catch_up', {'consumer': 'field', 'limit': 200}); x = r['result']; print('   again:', {q: x[q] for q in ('state', 'cursor', 'head', 'backlog')})
print('   stacy consumer:', {q: d('ledger.awareness')['result'][q] for q in ('state', 'cursor', 'head', 'backlog')})
# the approval: files.propose + files.decide
d('files.write', {'path': 'notes/probe.txt', 'text': 'first line\n'}); r = d('files.propose', {'path': 'notes/probe.txt', 'text': 'first line\nsecond line\n', 'why': 'probe: add a line'})
h = d('ledger.journal.status')['result']['head']
r = d('files.decide', {'id': r['result']['proposal'], 'apply': True}); print('\nfiles.decide ->', r['ok'], json.dumps(r.get('result') or r.get('error'))[:300])
for e in d('ledger.journal.read', {'after': str(h)})['result']['events']: print('     ', {q: e[q] for q in ('seq', 'origin', 'operation', 'state', 'detail') if e.get(q)})
print('files.story:', json.dumps(d('files.story', {'path': 'notes/probe.txt'})['result'])[:600])
print('files.proposals:', json.dumps(d('files.proposals')['result'])[:400])
print('agenda.view keys:', {q: (len(val) if isinstance(val, list) else val) for q, val in d('agenda.view')['result'].items()})
print('copies.list:', json.dumps(d('copies.list')['result'])[:200])
print('receiving.status:', json.dumps(d('receiving.status')['result'])[:400])
print('agent.list:', json.dumps(d('agent.list')['result'])[:300])
print('ledger.windows.list:', json.dumps(d('ledger.windows.list').get('result') or d('ledger.windows.list').get('error'))[:300])
print('ledger.resources active:', json.dumps({q: d('ledger.resources')['result'][q] for q in ('active_job_limits', 'gate')}))
