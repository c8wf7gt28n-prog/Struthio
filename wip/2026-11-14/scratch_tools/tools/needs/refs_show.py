import json, sys
d = json.load(open(sys.argv[1]))
def seg(k): return k.split('/')[0] if '/' in k else '(bare)'
for k in sorted(d, key=lambda k: (seg(k), k)):
    where = '; '.join(f"{doc}:{','.join(map(str, lines[:3]))}" for doc, lines in d[k].items())
    print(f"{k}  <=  {where[:230]}")
