"""A finding that is still SUPPORTED but NEEDS_REVIEW (one of two sources changed); and an item that was never admitted."""
from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
which = sys.argv[1]
if which == 'both':
    inv = call(k, 'investigation.list')['investigations'][0]['id']
    rows = call(k, 'office.list')['documents']; a = next(r for r in rows if 'Rev A' in r['title']); b = next(r for r in rows if 'Rev B' in r['title'])
    claim = call(k, 'investigation.claim', {'id': inv, 'text': 'Both limit sheets list the pulse row.', 'role': 'FINDING'}); print('claim:', json.dumps(claim, default=str)[:160])
    cid = claim['claim']
    srcs = []
    for r in (a, b):
        s = call(k, 'investigation.add_source', {'id': inv, 'address': 'office:' + r['id']}); print('add_source:', json.dumps(s, default=str)[:200]); srcs.append(s)
    sheet = call(k, 'investigation.sheet', {'id': inv})
    read = {s['address']: s['id'] for s in sheet['read']}
    for r in (a, b):
        e = call(k, 'investigation.evidence', {'claim': cid, 'direction': 'SUPPORTS', 'source': read['office:' + r['id']], 'note': 'probe'}); print('evidence:', json.dumps(e, default=str)[:120])
    f, _ = read_field(k, P); o = f.get('claim:' + cid); print('BEFORE the change  ->', o.kind, '|', o.state, '|', o.lines, '| fed by', [f.get(l.source).title for l in f.fed_by(o.id)])
    got = call(k, 'office.get', {'id': a['id']}); doc = json.loads(json.dumps(got['document'])); cells = doc['sheets'][0]['cells']; key = sorted(cells)[-1]
    cells[key] = {**cells[key], 'value': str(cells[key].get('value', '')) + ' (edited)'}
    print('office.save Rev A:', 'revision' in call(k, 'office.save', {'id': a['id'], 'expected_revision': got['revision'], 'document': doc}))
    # only look at whether THIS claim's own source changed; the three PDF addresses also read differently on this machine
    out = call(k, 'investigation.refresh', {'id': inv}); print('refresh changed:', out.get('changed'))
    sheet = call(k, 'investigation.sheet', {'id': inv})
    print('in learned:', [(c['evidence_state'], c['review']) for c in sheet['learned'] if c['id'] == cid], '| in unresolved:', [(c['evidence_state'], c['review']) for c in sheet['unresolved'] if c['id'] == cid])
    f, _ = read_field(k, P); o = f.get('claim:' + cid)
    print('AFTER the change   ->', o.kind, '|', o.state, '|', o.lines, '| fed by', [f.get(l.source).title for l in f.fed_by(o.id)], '| stale flags', [l.stale for l in f.fed_by(o.id)])
    print('census:', f.census())
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    from PySide6.QtWidgets import QApplication
    app = QApplication([]); from workbench.field_qt import FieldView
    v = FieldView(); v.resize(1400, 900); v.set_field(f); v.field.select(o.id); v._describe(); print('accessible description:', v.accessibleDescription())
if which == 'unadmitted':
    real = Kernel.dispatch
    def fake(self, operation, arguments=None, principal=None, *a, **kw):
        answer = real(self, operation, arguments, principal, *a, **kw)
        if operation == 'intake.items':
            answer = json.loads(json.dumps(answer)); base = answer['result']['items'][0]
            for word in ('UNREVIEWED', 'HELD', 'REJECTED'):
                answer['result']['items'].append({**base, 'id': 'f' * 31 + word[0].lower().replace('u', 'a').replace('h', 'b').replace('r', 'c'), 'name': 'never_admitted_%s.pdf' % word.lower(), 'admission': word, 'decision_id': None})
        return answer
    with patch.object(Kernel, 'dispatch', fake):
        f, refused = read_field(k, P)
    for o in f.objects:
        if o.kind == 'source': print(o.title, '| state:', o.state, '| role:', o.role, '| facts:', o.lines)
