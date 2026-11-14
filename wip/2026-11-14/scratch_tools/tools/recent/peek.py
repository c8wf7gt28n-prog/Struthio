import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding='utf-8'))
def show(o, depth=0, maxd=2, pre=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                n = len(v)
                print('  '*depth + '%s: <%s len %d>' % (k, type(v).__name__, n))
                if depth < maxd and not (isinstance(v, dict) and n > 40) and not (isinstance(v, list) and n > 40):
                    show(v, depth+1, maxd)
            else:
                s = json.dumps(v, ensure_ascii=False)
                print('  '*depth + '%s: %s' % (k, s[:600]))
    elif isinstance(o, list):
        for i, v in enumerate(o[:6]):
            if isinstance(v, (dict, list)):
                print('  '*depth + '[%d]' % i)
                show(v, depth+1, maxd)
            else:
                print('  '*depth + '- ' + json.dumps(v, ensure_ascii=False)[:300])
show(d, 0, int(sys.argv[2]) if len(sys.argv) > 2 else 1)
