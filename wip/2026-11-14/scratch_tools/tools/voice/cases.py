import json, sys, collections
with open(sys.argv[1], encoding='utf-8') as f:
    d = json.load(f)
cc = d['case_coverage']
print(len(cc), 'cases; keys:', list(cc[0].keys()))
print(collections.Counter(c.get('state') or c.get('status') for c in cc))
for c in cc:
    print(json.dumps(c, ensure_ascii=False)[:230])
sc = d['subject_coverage']
print(len(sc), 'subjects; keys:', list(sc[0].keys()))
print(collections.Counter(s.get('state') or s.get('status') for s in sc))
for p in d['passes']:
    print(p.get('id'), p.get('state'), '|', p.get('title'))
print(list(d['passes'][10].keys()))
