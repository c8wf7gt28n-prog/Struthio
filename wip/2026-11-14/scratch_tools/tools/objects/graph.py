"""Read-only: the After Hours 07 objects by kind and every recorded link among them, through Kernel operations only."""
import sys, json; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
from workbench import addresses
k = Kernel(ws); p = operator(); common.hold_processes()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']: print('!!', op, args, v['error']); return None
    return v['result']
nodes = {}; edges = []
def node(address, kind, name, state=None, rev=None): nodes[address] = dict(kind=kind, name=name, state=state, revision=rev)
for ns in call('intake.namespaces')['namespaces']:
    node('collection:' + ns['id'], 'collection', ns['name'], rev=ns['generation'])
    avail = {s['item']: s['state'] for s in call('references.sources', {'namespace': ns['id']})['sources']}
    for it in call('intake.items', {'namespace': ns['id']})['items']:
        node('intake:' + it['id'], 'source', it['name'], state=it['admission'] + '/' + avail.get(it['id'], '?'), rev=it['sha256'][:12]); edges.append(('intake:' + it['id'], 'part_of', 'collection:' + ns['id']))
        for a in call('references.pdf.annotations', {'namespace': ns['id'], 'item': it['id']})['annotations']:
            node('annotation:' + a['id'], 'annotation', a.get('text', '')[:60], rev=a.get('version')); edges.append(('annotation:' + a['id'], 'annotates page %d of' % (a.get('page_index', a.get('anchor', {}).get('page_index', -1)) + 1), 'intake:' + it['id'])); print('annotation keys', sorted(a))
for row in call('office.list')['documents']:
    s = call('office.get', {'id': row['id']}); o = s['origin']
    node('office:' + row['id'], 'sheet', row['title'], state=s['source_state']['state'], rev=s['revision'][:12])
    if o.get('pdf'): edges.append(('office:' + row['id'], 'reviewed from page %d of' % (o['pdf']['page_index'] + 1), 'intake:' + o['pdf']['item'])); edges.append(('office:' + row['id'], 'page read by', 'job:' + o['pdf']['job']))
for row in call('documents.list')['documents']:
    g = call('documents.get', {'id': row['id']}); d = g['document'].get('derivation')
    node('document:' + row['id'], 'calculation report' if d else 'document', row['title'], state=(g.get('source_state') or {}).get('state'), rev=row['revision'])
    if d:
        edges.append(('document:' + row['id'], 'calculated from cells %s of' % ','.join(i['cell'] for i in d['inputs']), 'office:' + d['sheet'])); edges.append(('document:' + row['id'], 'source page', 'intake:' + d['pdf']['item']))
for c in call('conditions.list')['conditions']:
    node('condition:' + c['id'], 'condition', str(c.get('result')), state=c.get('state')); edges.append(('condition:' + c['id'], 'bound to words of', 'document:' + c['document']))
for inv in call('investigation.list')['investigations']:
    s = call('investigation.sheet', {'id': inv['id']}); node('investigation:' + inv['id'], 'investigation', inv['question'], state=inv['state'])
    for r in s['read']: edges.append(('investigation:' + inv['id'], 'read (%s)' % r['state'], r['address']))
    for c in s['learned'] + s['unresolved']:
        node('claim:' + c['id'], c['role'].lower(), c['text'], state=c['evidence_state'] + '/' + c['review']); edges.append(('claim:' + c['id'], 'claim of', 'investigation:' + inv['id']))
        for l in call('investigation.path', {'claim': c['id']})['path']:
            if l['kind'] == 'SOURCE': edges.append(('claim:' + c['id'], l['direction'].lower() + ' by source', l['address']))
            else:
                for a in addresses_in(l['program']) if False else [x.removeprefix('@') for x in l['program'].split() if x.startswith('@')]: edges.append(('claim:' + c['id'], 'checked (%s) against' % l['outcome'], a))
jobs = call('jobs.list')
for j in jobs:
    node('job:' + j['id'], 'job', j['tool'], state=j['state'])
    if j.get('evidence'): edges.append(('evidence:' + j['evidence'], 'evidence of', 'job:' + j['id']))
print('\n== OBJECTS BY KIND =='); kinds = {}
for a, n in nodes.items(): kinds.setdefault(n['kind'], []).append((a, n))
for kind, rows in kinds.items():
    print('%s (%d)' % (kind, len(rows)))
    for a, n in rows[:9]: print('   %-46s %-44s state=%s rev=%s' % (a, n['name'][:44], n['state'], n['revision']))
print('\n== LINKS (%d) ==' % len(edges))
name = lambda a: (nodes.get(a) or {}).get('name', '?')[:38]
for s, rel, t in edges:
    if s.startswith('evidence:'): continue
    print('   %-40s --%s--> %s' % (name(s) + ' [' + s.split(':')[0] + ']', rel, name(t) + ' [' + t.split(':')[0] + ']'))
print('evidence-of-job links:', sum(1 for e in edges if e[0].startswith('evidence:')))
print('address kinds that resolve:', {a.split(':')[0]: bool(call('ledger.address.read', {'address': a})) for a in list(nodes) if a.split(':')[0] in addresses.KINDS and a.split(':')[0] in ('office', 'document', 'intake', 'collection')})
