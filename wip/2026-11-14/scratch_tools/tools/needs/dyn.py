import ast, os, sys
root = os.path.abspath(sys.argv[1])
std = set(sys.stdlib_module_names)
seen = {}
for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.endswith('.py'): continue
        p = os.path.join(dp, f)
        try: tree = ast.parse(open(p, encoding='utf-8', errors='replace').read())
        except SyntaxError: continue
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fnn = n.func
                name = fnn.id if isinstance(fnn, ast.Name) else (fnn.attr if isinstance(fnn, ast.Attribute) else '')
                if name in ('__import__', 'import_module', 'find_spec') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                    seen.setdefault(n.args[0].value, []).append((os.path.relpath(p, root), n.lineno))
missing = []
for mod, where in sorted(seen.items()):
    top = mod.lstrip('.').split('.')[0]
    if top in std: continue
    parts = mod.split('.')
    ok = False
    for r in (root, os.path.join(root, 'sdk', 'cli')):
        b = os.path.join(r, *parts)
        if os.path.isfile(b + '.py') or os.path.isdir(b): ok = True
    print(('OK      ' if ok else 'EXTERNAL'), mod, where[:2])
# view_modules NAMES
vm = os.path.join(root, 'workbench', 'view_modules')
tree = ast.parse(open(os.path.join(vm, '__init__.py'), encoding='utf-8').read())
for n in ast.walk(tree):
    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NAMES' for t in n.targets):
        names = ast.literal_eval(n.value)
        for nm in names:
            print('view_module', nm, os.path.isfile(os.path.join(vm, nm + '.py')))
