import json, sys
p = sys.argv[1]
with open(p, encoding='utf-8') as f:
    d = json.load(f)
print("== top scalars")
for k, v in d.items():
    if not isinstance(v, (dict, list)):
        print(k, '=', v)
print("\n== baseline")
print(json.dumps(d['baseline'], indent=1, ensure_ascii=False))
print("\n== latest_owner_decisions")
for x in d['latest_owner_decisions']:
    print('-', x)
print("\n== milestones")
for m in d['milestones']:
    print(json.dumps(m, ensure_ascii=False))
print("\n== passes (compact)")
for ps in d['passes']:
    print('---', ps['id'], '| M', ps['milestone'], '|', ps['title'], '|', ps['status'])
    print('  depends_on:', ps['depends_on'])
    print('  master_sections:', ps['master_sections'])
    print('  host_dependency:', ps['host_dependency'])
    print('  qualification:', ps.get('qualification'))
    print('  implementation_evidence:', ps.get('implementation_evidence'))
    print('  owner_host_evidence:', ps.get('owner_host_evidence'))
    print('  implementation_note:', ps.get('implementation_note'))
    extra = set(ps.keys()) - {'id','number','milestone','title','depends_on','master_sections','outcome','reuse','completion','host_dependency','status','implementation_evidence','owner_host_evidence','implementation_note','qualification'}
    for e in extra:
        print('  EXTRA', e, ':', ps[e])
print("\n== execution")
print(json.dumps(d['execution'], indent=1, ensure_ascii=False))
