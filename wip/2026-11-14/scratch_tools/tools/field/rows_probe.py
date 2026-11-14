import json
k = w.ledger_bridge.kernel; p = operator()
w.a_field.trigger(); settle(); v = w.field_page.view
for kind in ('finding', 'question', 'source', 'sheet', 'document'):
    obj = next((o for o in v.field.objects if o.kind == kind), None)
    if obj is None: continue
    print('\n==', kind, '|', obj.title, '|', obj.stac)
    op = obj.stac.split(' ', 1)[0]; args = json.loads(obj.stac.split(' | ')[0].split(' ', 1)[1]) if ' {' in obj.stac.split(' | ')[0] else {}
    r = k.dispatch(op, args, p)
    def show(x, depth=0, key=''):
        if isinstance(x, dict):
            for kk, vv in list(x.items())[:40]:
                if isinstance(vv, (dict, list)): print('  ' * depth + kk + ':'); show(vv, depth + 1, kk)
                else: print('  ' * depth + '%s: %s' % (kk, str(vv)[:110]))
        elif isinstance(x, list):
            for item in x[:2]: print('  ' * depth + '-'); show(item, depth + 1)
            if len(x) > 2: print('  ' * depth + '… %d more' % (len(x) - 2))
    show(r['result'] if r['ok'] else r['error'])
