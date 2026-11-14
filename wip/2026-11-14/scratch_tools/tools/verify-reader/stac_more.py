"""staC lines of the kinds the worked case does not hold: a stale total, a written document, an imported sheet, a waiting source,
a record that could not be read; and network rows with awkward names (IPv6, a program name with a space or a pipe)."""
from common import *
from workbench.field_source import read_field, read_network
from workbench import conditions
k = Kernel(RUN / 'ws'); hold_processes()
def run(o):
    try: a = k.dispatch('language.run', {'text': o.stac}, operator())
    except Exception as e: a = {'ok': False, 'error': 'EXC ' + repr(e)}
    rows = (a.get('result') or {}).get('rows') if a.get('ok') else None
    print('  %-7s %-11s %-30s state=%-12r | %s\n          -> %s' % ('ok' if a.get('ok') else 'REFUSED', o.kind, o.title[:30], o.state, o.stac, (json.dumps(rows, default=str)[:150] if a.get('ok') else json.dumps(a.get('error'), default=str)[:300])))
    return bool(a.get('ok')), rows
made = call(k, 'documents.create', {'title': 'Cable budget', 'text': 'Cable 12 m\nHose 3 m\nTotal: 15 m'})
doc = call(k, 'documents.get', {'id': made.get('id') or made['document']['id']})['document']
qs = conditions.page_quantities(doc['blocks'][:2])
conditions.create(k, P, document=doc['id'], inputs=[conditions.span(q) for q in qs], expression='sum', result={'value': '15', 'unit': 'm', 'text': 'Total: 15 m'}, method=conditions.METHOD, assignment=None, result_block=doc['blocks'][2]['id'], origin='HUMAN')
blocks = json.loads(json.dumps(doc['blocks'])); blocks[0]['text'] = 'Cable 14 m'
call(k, 'documents.save', {'id': doc['id'], 'expected_revision': doc['revision'], 'blocks': blocks})
csv = RUN / 'ws' / 'plain table.csv'; csv.write_text('Part,Qty\nR1,2\n'); plan = call(k, 'office.import.preview', {'path': str(csv)}); call(k, 'office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']})
try:
    import docx; d = docx.Document(); d.add_paragraph('A letter.'); path = RUN / 'ws' / 'Supplier letter.docx'; d.save(str(path))
    plan = call(k, 'office.import.preview', {'path': str(path)}); call(k, 'office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']})
except ImportError: print('no python-docx')
real = Kernel.dispatch
def fake(self, operation, arguments=None, principal=None, *a, **kw):
    answer = real(self, operation, arguments, principal, *a, **kw)
    if operation == 'intake.items' and answer.get('ok') and not (arguments or {}).get('offset'):
        answer = json.loads(json.dumps(answer)); base = answer['result']['items'][0]
        answer['result']['items'].append({**base, 'id': 'f' * 32, 'name': 'never admitted.pdf', 'admission': 'UNREVIEWED', 'decision_id': None})
    if operation == 'documents.get' and (arguments or {}).get('id') == doc['id'] and principal is P: return {'ok': False, 'error': {'code': 'PROBE', 'message': 'refused'}}
    return answer
with patch.object(Kernel, 'dispatch', fake):
    f, r = read_field(k, P)
print('work face: census', f.census(), '| unread', r.unread)
bad = 0
for o in f.objects:
    if o.kind in ('condition',) or o.state in ('not read', 'waiting') or (o.id.startswith('office:') and 'reviewed' not in o.role):
        ok, rows = run(o); bad += (not ok) or not rows
print('work-face lines refused or empty:', bad)
def net(self, operation, arguments=None, principal=None, *a, **kw):
    if operation == 'network.observe':
        return {'ok': True, 'result': {'interfaces': [{'name': 'wlp0s20f3', 'up': True, 'rx_bps': 1200, 'tx_bps': 80}, {'name': 'br-9f2 lan', 'up': False}],
            'connections': [{'process': 'Web Content', 'user': 'owner', 'proto': 'tcp', 'state': 'ESTABLISHED', 'remote': '2606:4700:4700::1111', 'rport': 443, 'rservice': 'https', 'local': '::1', 'lport': 50000},
                            {'process': 'python3', 'user': 'owner', 'proto': 'tcp', 'state': 'LISTEN', 'local': '::', 'lport': 8000},
                            {'process': 'a|b=c', 'user': 'owner', 'proto': 'udp', 'state': 'UNCONN', 'remote': 'fe80::1%wlp0s20f3', 'rport': 5353, 'local': '::', 'lport': 5353},
                            {'process': None, 'user': None, 'proto': 'tcp', 'state': 'SYN_SENT', 'remote': '10.0.0.7', 'rport': 22, 'local': '10.0.0.2', 'lport': 40000}],
            'capture': {'state': 'NOT_RUNNING'}}}
    return real(self, operation, arguments, principal, *a, **kw)
with patch.object(Kernel, 'dispatch', net):
    n, nr = read_network(k, P)
    print('network face: title %r census %s' % (n.title, n.census())); bad = 0
    for o in n.objects:
        ok, rows = run(o); bad += (not ok) or not rows
    print('network lines refused or empty:', bad)
