import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print('execution:', json.dumps(d['execution'], ensure_ascii=False))
print('latest_owner_decisions:')
for x in d['latest_owner_decisions']: print('  -', x)
print('milestones:')
for m in d['milestones']: print('  ', json.dumps(m, ensure_ascii=False)[:400])
print('passes:')
for p in d['passes']:
    print(f"  {p['id']} M{p['milestone']} [{p['status']}] {p['title']} | host_dependency={str(p.get('host_dependency'))[:110]} | owner_host_evidence={str(p.get('owner_host_evidence'))[:60]} | qualification={str(p.get('qualification'))[:110]}")
import collections
print('case states:', dict(collections.Counter(c['state'] for c in d['case_coverage'])))
print('baseline.observations:')
for o in d['baseline']['observations']: print('  -', str(o)[:300])
