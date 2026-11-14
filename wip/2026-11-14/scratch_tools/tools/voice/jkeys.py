import json, sys
p = sys.argv[1]
keys = sys.argv[2:]
with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)
if not keys:
    for k, v in d.items():
        t = type(v).__name__
        n = len(v) if hasattr(v, '__len__') else ''
        print(k, t, n)
else:
    for k in keys:
        print('=====', k)
        print(json.dumps(d.get(k), indent=1, ensure_ascii=False))
