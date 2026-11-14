import json, sys
for p in sys.argv[1:]:
    print('=====', p)
    with open(p, encoding='utf-8') as f:
        d = json.load(f)
    s = json.dumps(d, indent=1, ensure_ascii=False)
    print(s[:6000])
