import json
from workbench.engine import engineering
k = engineering(w.root)
def d(op, a):
    r = k.dispatch(op, a, operator()); return r['result'] if r.get('ok') else {'ERROR': r.get('error')}
def cut(x, n=0):
    if isinstance(x, dict): return {key: cut(v, n + 1) for key, v in list(x.items())[:40]}
    if isinstance(x, list): return [cut(v, n + 1) for v in x[:4]] + (['… %d more' % (len(x) - 4)] if len(x) > 4 else [])
    if isinstance(x, str) and len(x) > 160: return x[:160] + '…'
    return x
f = d('field.read', {})
for o in f['objects']: print('OBJ', o['kind'], '|', o['id'], '|', o['title'], '|', o['state'], '|', o['stac'][:110])
for l in f['links']: print('LINK', l['from'][:30], '->', l['to'][:30], '|', l['label'], '|', l['stale'])
sheet = next(o for o in f['objects'] if o['kind'] == 'sheet' and 'Bench' in o['title'])
print('SHEET', json.dumps(cut(d('office.get', {'id': sheet['id'].split(':', 1)[1].split(':')[-1]})), ensure_ascii=False)[:6000])
calc = next(o for o in f['objects'] if o['kind'] == 'calculation')
print('CALC', json.dumps(cut(d('documents.get', {'id': calc['id'].split(':', 1)[1]})), ensure_ascii=False)[:7000])
page = next((o for o in f['objects'] if o['kind'] == 'document'), None)
if page: print('PAGE', page['id'], json.dumps(cut(d('documents.get', {'id': page['id'].split(':', 1)[1]})), ensure_ascii=False)[:5000])
