"""Static import scan: which workbench modules are never imported by anything else, and whether launchers/tests/tools mention them."""
import ast, sys, os, re, json
from pathlib import Path

root = Path(sys.argv[1])
wb = root / 'workbench'
mods = {}
for p in sorted(wb.rglob('*.py')):
    rel = p.relative_to(root)
    name = '.'.join(rel.with_suffix('').parts)
    if name.endswith('.__init__'):
        name = name[:-9]
    mods[name] = p

def resolve(base_pkg_parts, level, module, names):
    out = set()
    if level:
        pkg = base_pkg_parts[:len(base_pkg_parts) - (level - 1)] if level > 0 else base_pkg_parts
        prefix = '.'.join(pkg)
        full = prefix + ('.' + module if module else '')
    else:
        full = module or ''
    if full:
        out.add(full)
    for n in names:
        if full:
            out.add(full + '.' + n)
    return out

imports = {m: set() for m in mods}
errors = []
allpy = []
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
    for f in files:
        if f.endswith('.py'):
            allpy.append(Path(dirpath) / f)

importers = {m: set() for m in mods}
for p in allpy:
    rel = p.relative_to(root)
    parts = list(rel.with_suffix('').parts)
    is_init = parts[-1] == '__init__'
    pkg_parts = parts[:-1]
    try:
        tree = ast.parse(p.read_text(encoding='utf-8', errors='replace'))
    except Exception as e:
        errors.append((str(rel), str(e)))
        continue
    me = '.'.join(parts[:-1] if is_init else parts)
    for node in ast.walk(tree):
        targets = set()
        if isinstance(node, ast.Import):
            for a in node.names:
                targets.add(a.name)
                # parents
        elif isinstance(node, ast.ImportFrom):
            targets |= resolve(pkg_parts, node.level, node.module, [a.name for a in node.names])
        for t in targets:
            # also count bare module name 'x' as workbench.x when importer is inside workbench w/o package (rare)
            if t in mods and t != me:
                importers[t].add(str(rel))
            # parent packages
    # dynamic: importlib.import_module('workbench.x') or '-m workbench.x' strings
    src = p.read_text(encoding='utf-8', errors='replace')
    for m in re.findall(r"workbench\.([A-Za-z0-9_\.]+)", src):
        t = 'workbench.' + m.rstrip('.')
        while t and t not in mods and '.' in t:
            t = t.rsplit('.', 1)[0]
        if t in mods and t != me:
            importers[t].add(str(rel) + ' (string)')

# non-py textual references (sh, cmd, md, json, toml, txt) by module basename
textrefs = {m: set() for m in mods}
textfiles = []
for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
    for f in files:
        if f.endswith(('.sh', '.cmd', '.desktop', '.service', '.toml', '.cfg', '.ini')) or f in ('arc1',):
            textfiles.append(Path(dirpath) / f)
for p in textfiles:
    try:
        s = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    for m in mods:
        base = m.split('.')[-1]
        if re.search(r'(?<![A-Za-z0-9_])' + re.escape(base) + r'(?![A-Za-z0-9_])', s):
            textrefs[m].add(str(p.relative_to(root)))

res = []
for m in sorted(mods):
    imps = importers[m]
    by_wb = sorted(i for i in imps if i.startswith('workbench/'))
    by_tests = sorted(i for i in imps if i.startswith('tests_integrated/') or '/tests/' in i or i.startswith('workbench/tests'))
    by_tools = sorted(i for i in imps if i.startswith('tools/'))
    by_other = sorted(i for i in imps if not (i.startswith('workbench/') or i.startswith('tests_integrated/') or i.startswith('tools/')))
    by_wb_nontest = [i for i in by_wb if '/tests/' not in i and not Path(i.split(' ')[0]).name.startswith('test_')]
    res.append(dict(module=m, lines=sum(1 for _ in open(mods[m], encoding='utf-8', errors='replace')),
                    wb=by_wb_nontest, tests=by_tests + [i for i in by_wb if i not in by_wb_nontest], tools=by_tools, other=by_other, launch=sorted(textrefs[m])))
json.dump(dict(result=res, errors=errors, n=len(mods)), open(sys.argv[2], 'w'), indent=1)
print(len(mods), 'modules;', len(errors), 'parse errors')
none_at_all = [r for r in res if not r['wb'] and not r['tests'] and not r['tools'] and not r['other'] and not r['launch']]
only_tests = [r for r in res if not r['wb'] and not r['other'] and not r['launch'] and (r['tests'] or r['tools'])]
print('\n== imported by nothing, no launcher/test/tool reference ==', len(none_at_all))
for r in none_at_all:
    print(' ', r['module'], r['lines'])
print('\n== only tests/tools import them (no workbench importer, no launcher) ==', len(only_tests))
for r in only_tests:
    print(' ', r['module'], r['lines'], 'tests:', len(r['tests']), 'tools:', len(r['tools']))
