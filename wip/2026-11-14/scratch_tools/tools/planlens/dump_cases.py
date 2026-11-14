import json, sys
p = sys.argv[1]
with open(p, encoding='utf-8') as f:
    d = json.load(f)
print("== case_coverage")
for c in d['case_coverage']:
    print(json.dumps(c, ensure_ascii=False))
print("\n== subject_coverage")
for s in d['subject_coverage']:
    print(s['section'], '|', s['title'], '| lead', s['lead'], '| supp', s['supporting'])
