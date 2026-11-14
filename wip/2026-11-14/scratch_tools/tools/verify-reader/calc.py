"""Calculations and sheets when the record itself says recheck: (1) the Bench sheet is edited -> its two calculations;
(2) the Bench PDF's admission is revoked -> its sheet and calculations; (3) the Rev A PDF revoked -> its sheet (nothing refers to it)."""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
def show(tag):
    f, r = read_field(k, P); print('--- ' + tag + ' | census:', f.census())
    for o in f.objects:
        if o.kind in ('sheet', 'calculation', 'source'): print('    %-11s %-28s state=%-12r lines=%s | wires in: %s' % (o.kind, o.title[:28], o.state, o.lines, [(f.get(l.source).title[:18], 'STALE' if l.stale else 'solid') for l in f.fed_by(o.id)]))
    return f
which = sys.argv[1]
if which == 'edit':
    row = next(r for r in call(k, 'office.list')['documents'] if 'Bench' in r['title'])
    got = call(k, 'office.get', {'id': row['id']}); doc = json.loads(json.dumps(got['document'])); cells = doc['sheets'][0]['cells']
    cells['B3'] = {**cells['B3'], 'value': str(cells['B3'].get('value')) + '1'}
    print('office.save Bench B3:', 'revision' in call(k, 'office.save', {'id': row['id'], 'expected_revision': got['revision'], 'document': doc}))
    print('record:', [(r['title'][:24], (call(k, 'documents.get', {'id': r['id']}).get('source_state') or {}).get('state')) for r in call(k, 'documents.list')['documents']])
    show('after the Bench sheet was edited')
else:
    items = call(k, 'intake.items', {'namespace': call(k, 'intake.namespaces')['namespaces'][0]['id']})['items']
    it = next(i for i in items if which in i['name'])
    out = call(k, 'intake.revoke', {'id': it['id'], 'expected_decision': it['decision_id'], 'reason': 'probe'}); print('revoke %s:' % it['name'], out.get('decision'))
    print('record: sheets', [(r['title'][:24], call(k, 'office.get', {'id': r['id']})['source_state']['state']) for r in call(k, 'office.list')['documents']])
    print('record: pages ', [(r['title'][:24], (call(k, 'documents.get', {'id': r['id']}).get('source_state') or {}).get('state')) for r in call(k, 'documents.list')['documents']])
    f = show('after revoking ' + it['name'])
    print('    sheets of this case missing from the Field:', [r['title'] for r in call(k, 'office.list')['documents'] if f.get('office:' + r['id']) is None])
