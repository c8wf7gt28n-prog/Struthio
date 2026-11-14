import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print('TOP KEYS:', list(d.keys()))
for p in d['passes']:
    print(p['id'], p['status'], '|', p['title'], '| note:', (p.get('implementation_note') or '')[:160], '| qual:', (p.get('qualification') or '')[:120])
for k in d:
    if k in ('passes', 'milestones', 'baseline', 'latest_owner_decisions'): continue
    v = d[k]
    if isinstance(v, list):
        print('\n==', k, len(v))
        for i in v[:60]:
            print('  ', json.dumps(i, ensure_ascii=False)[:420])
    elif isinstance(v, dict):
        print('\n==', k)
        print('  ', json.dumps(v, ensure_ascii=False)[:1500])
    else:
        print('\n==', k, ':', str(v)[:400])
print('\nBASELINE OBS:')
for o in d['baseline']['observations']: print('  -', o[:400])
