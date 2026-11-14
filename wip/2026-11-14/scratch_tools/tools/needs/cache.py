import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
def strip(o):
    if isinstance(o, dict):
        return {k: ('[%d parts]' % len(v) if k == 'parts' and isinstance(v, list) else strip(v)) for k, v in o.items()}
    if isinstance(o, list): return [strip(x) for x in o]
    return o
print(json.dumps(strip(d), indent=1, ensure_ascii=False)[:5000])
