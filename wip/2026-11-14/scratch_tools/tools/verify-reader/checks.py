"""Checks on a finding: (1) a check that does not hold (outcome CHECK_FAILED): how is its wire worded? (2) a check whose input sheet
changed: is the wire from that sheet stale and the finding RECHECK?"""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
inv = call(k, 'investigation.list')['investigations'][0]['id']
with k.db() as db:
    row = db.execute('SELECT claim, program, oracle, expect, value, refutes FROM inv_checks').fetchall()
print('existing checks:', [(r[2][:40], r[3], r[4], r[5], r[1][:140]) for r in row])
program = row[0][1]
claim = call(k, 'investigation.claim', {'id': inv, 'text': 'The reviewed sheet lists a 5 ms limit.', 'role': 'FINDING'}); cid = claim['claim']
chk = call(k, 'investigation.check', {'claim': cid, 'program': program, 'oracle': 'the sheet names 5 ms', 'expect': 'CONTAINS', 'value': 'zz-no-such-words-zz', 'refutes_on_fail': True}); print('check:', chk)
ran = call(k, 'investigation.continue', {'id': inv}); print('continue:', json.dumps(ran, default=str)[:300])
path = call(k, 'investigation.path', {'claim': cid}); print('path of the new claim:', [(s['kind'], s.get('outcome'), s.get('direction'), s.get('counts')) for s in path.get('path', ())], '| evidence_state', path.get('evidence_state'))
f, r = read_field(k, P); o = f.get('claim:' + cid)
print('FIELD: the new claim ->', o.kind, '| state', repr(o.state), '| lines', o.lines, '| wires in:', [(f.get(l.source).title, l.label, l.stale) for l in f.fed_by(o.id)])
# (2) the Rev B sheet changes; the investigation reads its sources again
old = next(c for c in f.objects if c.kind == 'finding' and 'keeps the 80 ms' in c.title)
rowb = next(x for x in call(k, 'office.list')['documents'] if 'Rev B' in x['title'])
got = call(k, 'office.get', {'id': rowb['id']}); doc = json.loads(json.dumps(got['document'])); cells = doc['sheets'][0]['cells']
key = next(c for c in sorted(cells) if '80' in str(cells[c].get('value', ''))); print('editing cell', key, repr(cells[key].get('value')))
cells[key] = {**cells[key], 'value': '95'}
print('office.save:', 'revision' in call(k, 'office.save', {'id': rowb['id'], 'expected_revision': got['revision'], 'document': doc}))
out = call(k, 'investigation.refresh', {'id': inv}); print('refresh changed:', out.get('changed'), out.get('REFUSED'))
sheet = call(k, 'investigation.sheet', {'id': inv})
print('checks now:', [(c.get('oracle', '')[:30], c.get('last_outcome')) for c in sheet.get('checks', ())])
p80 = call(k, 'investigation.path', {'claim': old.id.split(':', 1)[1]})
print('path of "keeps the 80 ms":', [(s['kind'], s.get('outcome'), s.get('counts')) for s in p80['path']], '| evidence_state', p80['evidence_state'], '| review', p80['review'])
f, r = read_field(k, P); o = f.get(old.id)
print('FIELD: "keeps the 80 ms" ->', o.kind, '| state', repr(o.state), '| lines', o.lines, '| wires in:', [(f.get(l.source).title, l.label, 'STALE' if l.stale else 'solid') for l in f.fed_by(o.id)])
o = f.get('claim:' + cid); print('FIELD: the new claim ->', o.kind, '| state', repr(o.state), '| lines', o.lines, '| wires in:', [(f.get(l.source).title, l.label, 'STALE' if l.stale else 'solid') for l in f.fed_by(o.id)])
print('census:', f.census())
