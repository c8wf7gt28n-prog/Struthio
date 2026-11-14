import ast, sys, subprocess, collections, os
root = '/home/user/Struthio'
files = subprocess.run(['git','-C',root,'ls-files','-z','*.py','arc1'],capture_output=True).stdout.decode().split('\0')
std = set(sys.stdlib_module_names)
local = {'workbench','sdk','pillkit','tools','tests_integrated','arc1cli','arc1','prepare_release','INSTALL_LS'}
# collect local top-level module names
for f in files:
    if not f: continue
    parts = f.split('/')
    local.add(parts[0]); 
    local.add(os.path.splitext(parts[-1])[0])
    for p in parts[:-1]: local.add(p)
found = collections.defaultdict(set)
for f in files:
    if not f: continue
    try:
        src = open(os.path.join(root,f),encoding='utf-8',errors='replace').read()
        tree = ast.parse(src)
    except Exception as e:
        print('PARSE FAIL', f, e); continue
    for n in ast.walk(tree):
        mods = []
        if isinstance(n, ast.Import): mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module: mods = [n.module]
        elif isinstance(n, ast.Call):
            fn = n.func
            name = getattr(fn,'id',None) or getattr(fn,'attr',None)
            if name in ('import_module','__import__','find_spec') and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value,str):
                mods = [n.args[0].value]
        for m in mods:
            top = m.split('.')[0]
            if top in std: continue
            found[top].add(f)
for k in sorted(found):
    fs = sorted(found[k])
    tag = 'LOCAL?' if k in local else 'THIRD'
    print(tag, k, len(fs), fs[:6])
