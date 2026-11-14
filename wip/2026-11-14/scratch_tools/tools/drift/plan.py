import json, sys
d = json.load(open(sys.argv[1]))
def show(o, depth=0, maxd=2):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)) and depth < maxd:
                print('  '*depth + str(k) + ':', type(v).__name__, len(v))
                show(v, depth+1, maxd)
            else:
                s = json.dumps(v, ensure_ascii=False)
                print('  '*depth + str(k) + ': ' + s[:400])
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            print('  '*depth + '[%d]' % i)
            show(v, depth+1, maxd)
        if len(o) > 3: print('  '*depth + '... %d more' % (len(o)-3))
show(d)
