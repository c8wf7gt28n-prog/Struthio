"""A finding that stands on a CHECK of a sheet; the sheet is a read source of the investigation; the sheet changes.
Expected (R2): the finding reads RECHECK and its wire from the changed sheet is stale (dashed)."""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
inv = call(k, 'investigation.list')['investigations'][0]['id']
rowb = next(x for x in call(k, 'office.list')['documents'] if 'Rev B' in x['title'])
print('add_source:', json.dumps(call(k, 'investigation.add_source', {'id': inv, 'address': 'office:' + rowb['id']}), default=str)[:160])
f, r = read_field(k, P); old = next(c for c in f.objects if c.kind == 'finding' and 'keeps the 80 ms' in c.title)
print('BEFORE: state', repr(old.state), '| wires in:', [(f.get(l.source).title, l.label, 'STALE' if l.stale else 'solid') for l in f.fed_by(old.id)])
got = call(k, 'office.get', {'id': rowb['id']}); doc = json.loads(json.dumps(got['document'])); cells = doc['sheets'][0]['cells']
key = next(c for c in sorted(cells) if '80' in str(cells[c].get('value', ''))); cells[key] = {**cells[key], 'value': '95'}
print('office.save (cell %s 80 -> 95):' % key, 'revision' in call(k, 'office.save', {'id': rowb['id'], 'expected_revision': got['revision'], 'document': doc}))
out = call(k, 'investigation.refresh', {'id': inv}); print('refresh changed:', [a[:20] for a in out.get('changed', ())])
p80 = call(k, 'investigation.path', {'claim': old.id.split(':', 1)[1]})
print('the record (investigation.path):', [(s['kind'], s.get('outcome'), 'counts=%s' % s.get('counts')) for s in p80['path']], '| evidence_state', p80['evidence_state'], '| review', p80['review'])
f, r = read_field(k, P); o = f.get(old.id)
print('AFTER:  kind', o.kind, '| state', repr(o.state), '| lines', o.lines, '| wires in:', [(f.get(l.source).title, l.label, 'STALE' if l.stale else 'solid') for l in f.fed_by(o.id)])
print('census:', f.census())
