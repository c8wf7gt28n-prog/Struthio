import json, sys
def shape(o, depth=0, maxdepth=3, key=''):
    ind = '  '*depth
    if isinstance(o, dict):
        print(f"{ind}{key} dict[{len(o)}]")
        if depth < maxdepth:
            for k, v in o.items():
                shape(v, depth+1, maxdepth, k)
    elif isinstance(o, list):
        print(f"{ind}{key} list[{len(o)}]")
        if depth < maxdepth and o:
            shape(o[0], depth+1, maxdepth, '[0]')
    else:
        s = repr(o)
        print(f"{ind}{key} = {s[:160]}")
for p in sys.argv[1:]:
    print('=====', p)
    with open(p, encoding='utf-8') as f:
        shape(json.load(f))
