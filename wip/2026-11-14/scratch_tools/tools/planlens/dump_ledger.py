import json, sys, collections
p = sys.argv[1]
with open(p, encoding='utf-8') as f:
    d = json.load(f)
for k in ('baseline','specification_version','checkpoint','date','commission','evidence_note'):
    print(k, '=', d[k])
print('\n== passes')
for k, v in d['passes'].items():
    print('-', k, ':', v)
print('\n== requirements')
c = collections.Counter()
for r in d['requirements']:
    c[r['state']] += 1
    lim = r.get('limits') or []
    print(r['id'], '|', r['state'], '| limits:', ' // '.join(str(x) for x in lim)[:400])
print(c)
print('\n== acceptance')
c2 = collections.Counter()
for a in d['acceptance']:
    c2[a['state']] += 1
    print(a['id'], '|', a['state'], '| mech:', a['mechanical'], '| engine:', a['actual_engine'], '| model:', a['actual_model'], '| gui:', a['real_gui'], '| host:', a['owner_host'])
    print('    limits:', ' // '.join(str(x) for x in (a.get('limits') or []))[:500])
    extra = set(a.keys()) - {'id','state','mechanical','actual_engine','actual_model','real_gui','owner_host','evidence','limits'}
    for e in extra:
        print('    EXTRA', e, ':', str(a[e])[:300])
print(c2)
