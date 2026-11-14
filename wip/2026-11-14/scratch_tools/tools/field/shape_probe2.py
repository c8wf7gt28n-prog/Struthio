import json
from workbench.engine import engineering
k = engineering(w.root)
def d(op, a):
    r = k.dispatch(op, a, operator()); return r['result'] if r.get('ok') else {'ERROR': r.get('error')}
def cut(x, n=0):
    if isinstance(x, dict): return {key: cut(v, n + 1) for key, v in list(x.items())[:60]}
    if isinstance(x, list): return [cut(v, n + 1) for v in x[:5]] + (['… %d more' % (len(x) - 5)] if len(x) > 5 else [])
    if isinstance(x, str) and len(x) > 200: return x[:200] + '…'
    return x
f = d('field.read', {})
for o in f['objects']:
    if o['kind'] == 'sheet':
        g = d('office.get', {'id': o['id'][len('office:'):]})
        cells = ((g.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        print('CELLS', o['title'], '|', {name: held.get('value') for name, held in sorted(cells.items())})
        if 'Bench' in o['title']: print('SHEET', json.dumps(cut(g), ensure_ascii=False)[:5000])
inv = 'c574ae94d79542f582932d151fad631f'
print('INV', json.dumps(cut(d('investigation.sheet', {'id': inv})), ensure_ascii=False)[:6000])
print('PATH', json.dumps(cut(d('investigation.path', {'claim': 'f2a610f24ca84112a400e02d6ad04869'})), ensure_ascii=False)[:2500])
page = next(o for o in f['objects'] if o['kind'] == 'document')
print('PLAIN', d('documents.get', {'id': page['id'].split(':', 1)[1]})['plain'])
