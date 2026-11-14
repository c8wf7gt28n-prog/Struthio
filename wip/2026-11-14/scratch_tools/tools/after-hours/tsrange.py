import sys, re, datetime
for p in sys.argv[1:]:
    s = open(p, encoding='utf-8', errors='replace').read()
    ts = sorted(set(float(x) for x in re.findall(r'(?<![0-9a-f])(17\d{8}\.\d+)', s)))
    f = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat()
    print(p.split('/')[-1], len(ts), 'timestamps')
    print('  min', ts[0], f(ts[0])); print('  max', ts[-1], f(ts[-1]))
    # distribution by day
    from collections import Counter
    c = Counter(f(t)[:13] for t in ts)
    for k in sorted(c): print('   ', k, c[k])
