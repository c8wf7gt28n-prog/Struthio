import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
for c in d['implementation_choices']:
    keys = [k for k in c if k not in ('id','pass','requirement','choice','reversible','review')]
    print(f"{c['id']} [{c.get('pass')}] req={c.get('requirement')} reversible={c.get('reversible')} extra={keys}")
    print("   choice:", str(c.get('choice'))[:300])
    print("   review:", str(c.get('review'))[:260])
    for k in keys:
        print(f"   {k}:", str(c[k])[:260])
