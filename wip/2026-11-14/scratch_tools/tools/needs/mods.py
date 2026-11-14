import os, re, sys, collections
root = os.path.abspath(sys.argv[1])
pat = re.compile(r"(?:-m['\"]?[, ]+['\"]?|python3? -B -m |python3? -m |\.venv/bin/python -m )((?:workbench|tools|pillkit|arc1cli|tests_integrated)(?:\.[A-Za-z_][A-Za-z_0-9]*)+)")
seen = collections.defaultdict(set)
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.endswith(('.py', '.sh', '.md', '.cmd', '.txt')) or f in ('arc1',):
            p = os.path.join(dp, f)
            try: s = open(p, encoding='utf-8', errors='replace').read()
            except OSError: continue
            for m in pat.finditer(s):
                seen[m.group(1)].add(os.path.relpath(p, root))
bad = []
for mod in sorted(seen):
    parts = mod.split('.')
    ok = False
    for r in (root, os.path.join(root, 'sdk', 'cli')):
        b = os.path.join(r, *parts)
        if os.path.isfile(b + '.py') or os.path.isfile(os.path.join(b, '__main__.py')) or os.path.isdir(b):
            ok = True
    if not ok: bad.append((mod, sorted(seen[mod])[:3]))
print('module invocations found:', len(seen), 'unresolved:', len(bad))
for b in bad: print('  ', b)
