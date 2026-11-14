import sys, os, re, json, collections
tree = sys.argv[1]
man = json.load(open(os.path.join(tree, "MANIFEST.json"), encoding="utf-8"))["files"]
names = set(man)
dirs = set()
for n in names:
    parts = n.split("/")
    for i in range(1, len(parts)): dirs.add("/".join(parts[:i]))
refs = collections.defaultdict(set)
pat = re.compile(r"(?<![A-Za-z0-9_/.-])((?:docs|build|branding|project|tools|tests_integrated|examples|policy|runtimes)/[A-Za-z0-9_./-]+\.(?:md|json|pdf|docx|txt|png|webp|zip|patch|html|sqlite3|csv|ods|svg))")
for dp, dn, fn in os.walk(tree):
    for n in fn:
        if not n.endswith((".md", ".py", ".json", ".txt", ".sh")): continue
        p = os.path.join(dp, n); rel = os.path.relpath(p, tree)
        if rel == "MANIFEST.json": continue
        try: t = open(p, encoding="utf-8").read()
        except Exception: continue
        for m in pat.finditer(t):
            r = m.group(1)
            if r not in names: refs[r].add(rel)
print("referenced paths not in MANIFEST:", len(refs))
by_top = collections.Counter(r.split("/")[0] + "/" + (r.split("/")[1] if r.count("/") > 1 else "") for r in refs)
print(by_top.most_common(30))
for r in sorted(refs):
    if r.startswith("docs/") :
        print("  ", r, "<-", sorted(refs[r])[:3], len(refs[r]))
