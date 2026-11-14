"""Worked case as restored: the Field, raw admission/source_state, and every staC line run through language.run."""
from common import *
from workbench.field_source import read_field, read_network, problems
k = Kernel(RUN / 'ws'); hold_processes()
ns = call(k, 'intake.namespaces')['namespaces']
for space in ns:
    print('intake.items:', [(i['name'], i['admission']) for i in call(k, 'intake.items', {'namespace': space['id']})['items']])
for row in call(k, 'office.list')['documents']:
    got = call(k, 'office.get', {'id': row['id']}); print('office:', row['title'], '| kind', row.get('kind'), '| source_state', (got.get('source_state') or {}).get('state'))
for row in call(k, 'documents.list')['documents']:
    got = call(k, 'documents.get', {'id': row['id']}); print('document:', row['title'], '| derivation', bool((got.get('document') or {}).get('derivation')), '| source_state', (got.get('source_state') or {}).get('state'))
f, reader = read_field(k, P)
print('\n--- Field of the worked case ---'); dump(f, reader); print('problems:', repr(problems(reader)))
def run_all(field, tag):
    bad = 0
    for o in field.objects:
        if not o.stac: print('  NO STAC:', o.id, o.kind, o.title); bad += 1; continue
        try: a = k.dispatch('language.run', {'text': o.stac}, operator())
        except Exception as e: a = {'ok': False, 'error': 'EXC ' + repr(e)}
        ok = isinstance(a, dict) and a.get('ok')
        res = a.get('result') if ok else None
        inner_ok = None
        if isinstance(res, dict): inner_ok = res.get('ok', res.get('state'))
        if not ok: bad += 1
        print('  %-5s %-11s %-34s | %s' % ('ok' if ok else 'REFUSED', o.kind, o.title[:34], o.stac))
        if not ok: print('        reason:', json.dumps(a.get('error'), default=str)[:400])
        else: print('        result:', json.dumps(res, default=str)[:260])
    print('%s: %d objects, %d without a line or refused' % (tag, len(field.objects), bad))
print('\n--- staC lines of the work face ---'); run_all(f, 'work face')
if 'net' in sys.argv:
    n, nreader = read_network(k, P)
    print('\n--- network face ---'); dump(n, nreader)
    run_all(n, 'network face')
