import json
from workbench import field_source
k = w.ledger_bridge.kernel; p = operator()
print('PRINCIPAL', p.identity, sorted(p.scopes), getattr(p,'mode',None))
def show(x, depth=0, maxitems=3, width=150):
    if isinstance(x, dict):
        for kk, vv in list(x.items())[:60]:
            if isinstance(vv, (dict, list)) and vv: print('  ' * depth + str(kk) + ':'); show(vv, depth + 1, maxitems, width)
            else: print('  ' * depth + '%s: %s' % (kk, str(vv)[:width]))
    elif isinstance(x, list):
        for item in x[:maxitems]:
            if isinstance(item,(dict,list)): print('  ' * depth + '-'); show(item, depth + 1, maxitems, width)
            else: print('  ' * depth + '- ' + str(item)[:width])
        if len(x) > maxitems: print('  ' * depth + '… %d more' % (len(x) - maxitems))
def call(op, args=None, quiet=False):
    r = k.dispatch(op, args or {}, p)
    if not quiet: print('\n>>>', op, json.dumps(args or {})[:300], '->', 'ok' if r['ok'] else 'REFUSED')
    return r['result'] if r['ok'] else {'__error__': r['error']}
def field():
    f, reader = field_source.read_field(k, p)
    print('\n=== FIELD: %s | refused=%s unread=%s' % (f.title, reader.refused, reader.unread))
    for o in f.objects:
        print('  %-11s %-9s %-60s %s' % (o.kind, o.state or '-', o.title[:60], ' ; '.join(o.lines)))
    for l in f.links:
        print('    wire %s -> %s  [%s]%s' % (l.source[:22], l.target[:22], l.label, '  STALE' if l.stale else ''))
    return f
f = field()
for o in f.objects:
    print('OBJ', o.id, '|', o.kind, '|', o.state, '|', json.dumps(o.target), '|', o.stac)
# raw reads
ns = call('intake.namespaces'); show(ns)
for space in ns['namespaces']:
    items = call('intake.items', {'namespace': space['id']}); show(items, maxitems=1)
    for it in items['items'][:1]:
        show(call('intake.read', {'id': it['id']}), maxitems=2, width=200)
        show(call('intake.item', {'id': it['id']}), maxitems=2, width=200)
ol = call('office.list'); show(ol, maxitems=5)
for row in ol['documents'][:1]:
    g = call('office.get', {'id': row['id']})
    print('office.get keys', list(g.keys())); print('origin keys', list(g['origin'].keys())); show({kk: vv for kk, vv in g.items() if kk not in ('document',)}, maxitems=2, width=160)
    sh = g['document']['sheets'][0]; print('sheet keys', list(sh.keys())); print('cells:'); 
    for a, c in sorted(sh['cells'].items(), key=lambda kv: (int(kv[0][1:]), kv[0][0])): print('   ', a, json.dumps(c))
dl = call('documents.list'); show(dl, maxitems=6)
for row in dl['documents']:
    g = call('documents.get', {'id': row['id']})
    print('documents.get keys', list(g.keys()), '| has derivation', bool(g['document'].get('derivation')), '| source_state', g.get('source_state'))
    if g['document'].get('derivation'):
        d = g['document']['derivation']; print('derivation keys', list(d.keys()))
        show({kk: vv for kk, vv in d.items() if kk != 'pdf'}, maxitems=4, width=220)
        print('plain:\n' + g['plain'])
cl = call('conditions.list'); show(cl)
il = call('investigation.list'); show(il)
for row in il['investigations']:
    s = call('investigation.sheet', {'id': row['id']}); print('sheet keys', list(s.keys())); show(s, maxitems=6, width=260)
    for c in s['learned'] + s['unresolved']:
        show(call('investigation.path', {'claim': c['id']}), maxitems=6, width=260)
jl = call('jobs.list'); print(type(jl)); show(jl if isinstance(jl, dict) else jl[:3], maxitems=2)
