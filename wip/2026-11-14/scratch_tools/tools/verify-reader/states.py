"""Reader states through real operations on the disposable copy."""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
which = sys.argv[1]
def field(tag):
    f, reader = read_field(k, P); print('\n--- ' + tag + ' ---'); dump(f, reader); return f
if which == 'import':
    csv = RUN / 'ws' / 'plain_table.csv'; csv.write_text('Part,Qty\nR1,2\nC1,4\n')
    plan = call(k, 'office.import.preview', {'path': str(csv)}); print('preview:', {k2: plan.get(k2) for k2 in ('id', 'digest', 'mode', 'REFUSED', 'EXC')})
    done = call(k, 'office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']}); print('commit:', json.dumps(done, default=str)[:300])
    rows = call(k, 'office.list')['documents']; print('office.list:', [(r['title'], r['kind'], r['state']) for r in rows])
    new = next(r for r in rows if 'plain' in r['title'].lower())
    print('office.get source_state of the imported sheet:', call(k, 'office.get', {'id': new['id']})['source_state'])
    field('after importing one ordinary CSV (original untouched)')
if which == 'revoke':
    items = call(k, 'intake.items', {'namespace': call(k, 'intake.namespaces')['namespaces'][0]['id']})['items']
    it = next(i for i in items if 'Rev_A' in i['name'])
    out = call(k, 'intake.revoke', {'id': it['id'], 'expected_decision': it['decision_id'], 'reason': 'reviewer probe: revoke Rev A'}); print('revoke:', json.dumps(out, default=str)[:300])
    items = call(k, 'intake.items', {'namespace': it['namespace']})['items']; print('admissions now:', [(i['name'], i['admission']) for i in items])
    print('sheet from Rev A source_state:', [call(k, 'office.get', {'id': r['id']})['source_state']['state'] for r in call(k, 'office.list')['documents'] if 'Rev A' in r['title']])
    field('after revoking the admission of 07_Rail_Limits_Rev_A.pdf')
if which == 'review':
    inv = call(k, 'investigation.list')['investigations'][0]
    # change the Rev B sheet through the room's own save, then let the investigation read its sources again
    row = next(r for r in call(k, 'office.list')['documents'] if 'Rev B' in r['title'])
    got = call(k, 'office.get', {'id': row['id']}); doc = json.loads(json.dumps(got['document']))
    cells = doc['sheets'][0]['cells']; key = sorted(cells)[-1]; print('editing cell', key, cells[key])
    cells[key] = {**cells[key], 'value': str(cells[key].get('value', '')) + ' (edited)'}
    saved = call(k, 'office.save', {'id': row['id'], 'expected_revision': got['revision'], 'document': doc}); print('office.save:', json.dumps(saved, default=str)[:200])
    out = call(k, 'investigation.refresh', {'id': inv['id']}); print('investigation.refresh changed:', out.get('changed'), out.get('REFUSED'), out.get('EXC'))
    sheet = call(k, 'investigation.sheet', {'id': inv['id']})
    print('learned:', [(c['text'][:40], c['evidence_state'], c['review']) for c in sheet['learned']])
    print('unresolved:', [(c['text'][:40], c['role'], c['evidence_state'], c['review']) for c in sheet['unresolved']])
    f = field('after a source of a supported finding changed (investigation.refresh)')
    print('duplicate links:', len(f.links), 'distinct:', len({(l.source, l.target, l.label) for l in f.links}))
if which == 'second':
    out = call(k, 'investigation.create', {'question': 'Why does the fan stall at 40 C?'}); print('create:', json.dumps(out, default=str)[:200])
    print('list:', [(r['question'], r['state']) for r in call(k, 'investigation.list')['investigations']])
    f = field('with a second investigation'); print('title from the reader:', repr(f.title))
if which == 'time':
    import time
    for _ in range(3):
        t0 = time.time(); f, refused = read_field(k, P); print('read_field %.3fs' % (time.time() - t0))
    from workbench import activity
