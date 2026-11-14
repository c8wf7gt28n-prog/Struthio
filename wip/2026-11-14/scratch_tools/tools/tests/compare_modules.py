import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
f = lambda d: {(n, str(x)) for n, m in d.items() for x in m.get('bad', [])}
print('base: modules', len(a), 'tests', sum(m.get('tests', 0) or 0 for m in a.values()), 'failing', len(f(a)))
print('now : modules', len(b), 'tests', sum(m.get('tests', 0) or 0 for m in b.values()), 'failing', len(f(b)))
print('newly failing:', sorted(f(b) - f(a))[:8]); print('no longer failing:', sorted(f(a) - f(b))[:6])
print('new modules:', sorted(set(b) - set(a)), '| modules with a nonzero code not in base:', [n for n, m in b.items() if m.get('code') and not a.get(n, {}).get('code')])
