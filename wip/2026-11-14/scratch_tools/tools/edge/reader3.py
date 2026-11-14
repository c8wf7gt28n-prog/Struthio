from common import *
k = Kernel(RUN / 'ws'); hold_processes()
got = call(k, 'documents.get', {'id': '218f9efb3315412099761113f1ef2e5d'})
doc = got['document']; print('page keys:', sorted(doc.keys()))
for b in doc['blocks']: print('  ', b.get('style'), '|', b.get('text')[:110], '|', b.get('marks'))
print('conditions on it:', call(k, 'conditions.list'))
inv = call(k, 'investigation.list')['investigations'][0]
sheet = call(k, 'investigation.sheet', {'id': inv['id']})
print('investigation read:', [(s['address'], s['state']) for s in sheet['read']])
print('checked:', [(c.get('claim_text', '')[:30], c.get('program'), c.get('last_outcome')) for c in sheet['checked']])
print('attempted:', [(s.get('program', '')[:80], s.get('outcome')) for s in sheet['attempted']])
