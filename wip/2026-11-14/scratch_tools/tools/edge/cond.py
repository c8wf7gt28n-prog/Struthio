"""A real condition card that goes STALE: how does the Field name it?"""
from common import *
from workbench.field_source import read_field
from workbench import conditions
k = Kernel(RUN / 'ws'); hold_processes()
made = call(k, 'documents.create', {'title': 'Cable budget', 'text': 'Cable 12 m\nHose 3 m\nTotal: 15 m'}); print('create:', json.dumps(made, default=str)[:160])
doc = call(k, 'documents.get', {'id': made.get('id') or made['document']['id']})['document']
qs = conditions.page_quantities(doc['blocks'][:2]); print('quantities:', [(q['text'], q['block'][:6]) for q in qs])
card = conditions.create(k, P, document=doc['id'], inputs=[conditions.span(q) for q in qs], expression='sum', result={'value': '15', 'unit': 'm', 'text': 'Total: 15 m'},
                         method=conditions.METHOD, assignment=None, result_block=doc['blocks'][2]['id'], origin='HUMAN')
print('card state:', card['state'])
f, _ = read_field(k, P); print('while CURRENT: condition objects in the Field:', [o.title for o in f.objects if o.id.startswith('condition:')])
blocks = json.loads(json.dumps(doc['blocks'])); blocks[0]['text'] = 'Cable 14 m'
saved = call(k, 'documents.save', {'id': doc['id'], 'expected_revision': doc['revision'], 'blocks': blocks}); print('save:', json.dumps(saved, default=str)[:120])
rows = call(k, 'conditions.list')['conditions']; print('conditions.list:', [(r['state'], r['reason'][:50], r['result']) for r in rows])
f, _ = read_field(k, P)
for o in f.objects:
    if o.id.startswith('condition:'):
        print('STALE condition in the Field -> kind:', o.kind, '| title:', repr(o.title), '| state:', o.state, '| facts:', o.lines, '| role:', o.role, '| fed by:', [f.get(l.source).title for l in f.fed_by(o.id)])
print('census:', f.census())
for rank in f.ranks(): print(' ', rank, f.rank_title(rank), [(f.get(i).kind, f.get(i).title[:30]) for i in f.column(rank)])
