import json, time, sys, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/memory-programs')
import last_touched as lt
from workbench import explore
k = w.ledger_bridge.kernel; p = operator()
def d(op, a=None): return k.dispatch(op, a or {}, p)
def stamp(t): return time.strftime('%m-%d %H:%M:%S', time.gmtime(t))
views = [(row[0], row[7]) for row in explore.VIEWS]
w.a_field.trigger(); settle(); v = w.field_page.view
print('== as restored (nothing done in this session) ==')
out = lt.last_touched(k, p, v.field)
for obj in v.field.objects:
    hit = out.get(obj.id); print('  %-48s %-11s %s' % (obj.id, obj.kind, ('%s  %-18s %s' % (stamp(hit[0]), hit[1], hit[2])) if hit else 'NO TIME FOUND'))
# ---- the owner does five things
obj = {o.id: o for o in v.field.objects}
sheetB = obj['office:owner:4f357ff3c843489a9758db71e23bf4b4']; v.field.select(sheetB.id); v.update(); QTest.keyClick(v, Qt.Key_Return); settle(60, 5)           # opens a sheet
sid = 'owner:db5f669f863d4c71b89fa7ba348957da'; got = d('office.get', {'id': sid})['result']; new = copy.deepcopy(got['document']); new['sheets'][0]['cells']['B3']['value'] = '0.29'
print('office.save', d('office.save', {'id': sid, 'expected_revision': got['revision'], 'document': new})['ok'])                                                # edits a cell
dg = d('documents.get', {'id': '218f9efb3315412099761113f1ef2e5d'})['result']['document']; blocks = copy.deepcopy(dg['blocks']); blocks[1]['text'] += ' (seen)'
print('documents.save', d('documents.save', {'id': dg['id'], 'expected_revision': dg['revision'], 'blocks': blocks})['ok'])                                    # saves a page
w.a_field.trigger(); settle(); v = w.field_page.view; obj = {o.id: o for o in v.field.objects}
for ident in ('claim:c3bfcad59ccf4868b419107ef1b5288c', 'intake:b60c03c9f5ac6c02b7d1c1c0b09a2026'):
    print('language.run', obj[ident].stac[:60], d('language.run', {'text': obj[ident].stac})['ok'])                                                             # runs two staC lines
it = d('intake.items', {'namespace': '34259ad099cfdec0a683ff3ef5b90773'})['result']['items']; src = next(i for i in it if i['id'] == '496798047c86ccc5f46a4120f1c0e7f8')
r = d('references.pdf.page', {'namespace': src['namespace'], 'item': src['id'], 'source_sha256': src['sha256'], 'page_index': 0}); print('references.pdf.page', r['ok'], (r.get('result') or r.get('error')))
if r['ok'] and isinstance(r['result'], dict) and r['result'].get('id'): wait_job(r['result']['id'], 120, 'page')
elif r['ok'] and isinstance(r['result'], dict) and r['result'].get('job'): wait_job(r['result']['job'] if isinstance(r['result']['job'], str) else r['result']['job']['id'], 120, 'page')
w.a_field.trigger(); settle(); v = w.field_page.view
rows = lt.journal(k, p); t = time.time(); out = lt.last_touched(k, p, v.field, rows); took = time.time() - t
print('\n== after: {field object id: last touched · operation · where the time came from}   (%.2f s, %d journal rows, head unchanged: %s) ==' % (took, len(rows), d('ledger.journal.status')['result']['head'] == rows[-1]['seq']))
for o in sorted(v.field.objects, key=lambda o: -(out.get(o.id) or (0,))[0]):
    hit = out.get(o.id); print('  %-48s %-11s %s' % (o.id, o.kind, ('%s  %-18s %s' % (stamp(hit[0]), hit[1], hit[2])) if hit else 'NO TIME FOUND'))
out2 = lt.last_touched(k, p, v.field, rows, office_rows=False)
print('through operations only (office_rows=False), the sheets become:', {i: (stamp(out2[i][0]), out2[i][1]) if i in out2 else None for i in out if i.startswith('office:')})
pt = lt.programs_touched(rows, views)
print('\n== the shelf: last time one of each program\'s operations finished (journal, by operation prefix) ==')
for key, (at, what, seq) in sorted(pt.items(), key=lambda kv: -kv[1][0]): print('  app:%-15s %s  %-44s seq %d' % (key, stamp(at), what, seq))
