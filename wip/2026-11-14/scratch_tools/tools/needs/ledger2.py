import json, sys, collections
d = json.load(open(sys.argv[1], encoding='utf-8'))
print("evidence_note:", d['evidence_note'])
print()
c = collections.Counter(r['state'] for r in d['requirements'])
print("requirement states:", dict(c))
for r in d['requirements']:
    print(f"- {r['id']} [{r['state']}] limits={str(r.get('limits'))[:400]}")
print()
c = collections.Counter(r['state'] for r in d['acceptance'])
print("acceptance states:", dict(c))
for r in d['acceptance']:
    print(f"- {r['id']} [{r['state']}] mech={r.get('mechanical')} engine={r.get('actual_engine')} model={r.get('actual_model')} gui={r.get('real_gui')} owner_host={r.get('owner_host')}\n    limits={str(r.get('limits'))[:500]}")
