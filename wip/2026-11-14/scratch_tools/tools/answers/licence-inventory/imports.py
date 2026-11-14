import ast, sys, os, collections
root = sys.argv[1]
std = set(sys.stdlib_module_names)
# local top-level packages
local = set()
for d in ("", "workbench", "sdk/cli", "tools", "tests_integrated"):
    p = os.path.join(root, d)
    if os.path.isdir(p):
        for n in os.listdir(p):
            if n.endswith(".py"): local.add(n[:-3])
            elif os.path.isdir(os.path.join(p, n)) and os.path.exists(os.path.join(p, n, "__init__.py")): local.add(n)
            elif os.path.isdir(os.path.join(p, n)): local.add(n)
found = collections.defaultdict(list)
for dp, dn, fn in os.walk(root):
    if ".git" in dp.split(os.sep): continue
    for f in fn:
        if not f.endswith(".py"): continue
        path = os.path.join(dp, f)
        try:
            src = open(path, encoding="utf-8", errors="replace").read()
            tree = ast.parse(src)
        except Exception as e:
            print("PARSE FAIL", path, e); continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [(a.name, node.lineno) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    mods = [(node.module, node.lineno)]
            elif isinstance(node, ast.Call):
                fnn = node.func
                name = getattr(fnn, "attr", getattr(fnn, "id", ""))
                if name in ("import_module", "__import__", "find_spec") and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    mods = [(node.args[0].value, node.lineno)]
            for m, ln in mods:
                top = m.split(".")[0]
                if top in std or top in local: continue
                found[top].append((os.path.relpath(path, root), ln, m))
for top in sorted(found):
    print("==", top, len(found[top]))
    seen = set()
    for p, ln, m in found[top][:400]:
        d = p.split(os.sep)[0]
        key = (p)
        if key in seen: continue
        seen.add(key)
    files = sorted(set(p for p, ln, m in found[top]))
    dirs = collections.Counter(p.split(os.sep)[0] for p in files)
    print("   dirs:", dict(dirs))
    for p, ln, m in found[top][:6]:
        print("   ", f"{p}:{ln}", m)
