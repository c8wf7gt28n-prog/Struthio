import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def show(o, depth=0, maxdepth=2, key=''):
    ind = '  '*depth
    if isinstance(o, dict):
        print(f"{ind}{key} dict[{len(o)}] keys={list(o.keys())[:40]}")
        if depth < maxdepth:
            for k, v in o.items():
                show(v, depth+1, maxdepth, k)
    elif isinstance(o, list):
        print(f"{ind}{key} list[{len(o)}]")
        if depth < maxdepth and o:
            show(o[0], depth+1, maxdepth, '[0]')
    else:
        s = repr(o)
        print(f"{ind}{key} = {s[:300]}")
show(d, 0, int(sys.argv[2]) if len(sys.argv) > 2 else 2)
