"""Static import scan. Never imports or executes the scanned code."""
import ast, os, sys, json, collections

root = os.path.abspath(sys.argv[1])
out_json = sys.argv[2]
stdlib = set(sys.stdlib_module_names) | {'__future__'}

pyfiles = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        if f.endswith('.py'):
            pyfiles.append(os.path.join(dp, f))
pyfiles.sort()
rel = lambda p: os.path.relpath(p, root).replace(os.sep, '/')

# search roots for absolute imports
search_roots = [root, os.path.join(root, 'sdk', 'cli'), os.path.join(root, 'sdk')]

def resolve_abs(dotted, extra_roots):
    """Return ('module'|'package'|'nspkg', path) or None."""
    parts = dotted.split('.')
    for r in list(extra_roots) + search_roots:
        base = os.path.join(r, *parts)
        if os.path.isfile(base + '.py'):
            return ('module', base + '.py')
        if os.path.isdir(base):
            if os.path.isfile(os.path.join(base, '__init__.py')):
                return ('package', os.path.join(base, '__init__.py'))
            # namespace package only if it has py files
            if any(x.endswith('.py') for x in os.listdir(base)):
                return ('nspkg', base)
    return None

_names_cache = {}
def module_names(path):
    """Top-level bound names of a module (recursing into if/try/with/for at module level)."""
    if path in _names_cache:
        return _names_cache[path]
    names = set(); star = False; getattr_hook = False
    try:
        tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    except SyntaxError:
        _names_cache[path] = (None, False, False)
        return _names_cache[path]
    def visit(body):
        nonlocal star, getattr_hook
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
                if n.name == '__getattr__':
                    getattr_hook = True
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            names.add(x.id)
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign)):
                if isinstance(n.target, ast.Name):
                    names.add(n.target.id)
            elif isinstance(n, ast.Import):
                for a in n.names:
                    names.add((a.asname or a.name).split('.')[0])
            elif isinstance(n, ast.ImportFrom):
                for a in n.names:
                    if a.name == '*':
                        star = True
                    else:
                        names.add(a.asname or a.name)
            elif isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.AsyncWith, ast.AsyncFor)):
                visit(n.body); visit(getattr(n, 'orelse', []))
            elif isinstance(n, ast.Try) or n.__class__.__name__ == 'TryStar':
                visit(n.body); visit(n.orelse); visit(n.finalbody)
                for h in n.handlers:
                    visit(h.body)
            elif isinstance(n, ast.Expr) and isinstance(n.value, ast.NamedExpr):
                names.add(n.value.target.id)
    visit(tree.body)
    _names_cache[path] = (names, star, getattr_hook)
    return _names_cache[path]

internal_tops = set()
for r in search_roots:
    if os.path.isdir(r):
        for x in os.listdir(r):
            p = os.path.join(r, x)
            if os.path.isdir(p) and any(y.endswith('.py') for y in os.listdir(p)):
                internal_tops.add(x)
            elif x.endswith('.py'):
                internal_tops.add(x[:-3])

unresolved = []          # intra-project imports that resolve to no file
missing_names = []       # from X import name where name not bound in X
third = collections.defaultdict(lambda: {'files': set(), 'guarded': 0, 'unguarded': 0, 'toplevel_unguarded': 0, 'subs': set()})
syntax_errors = []
n_imports = 0

class V(ast.NodeVisitor):
    def __init__(self, path):
        self.path = path
        self.dir = os.path.dirname(path)
        self.guard = 0      # inside try with except ImportError/Exception/bare
        self.depth = 0      # inside function/class
        # package context for relative imports
        self.pkgdir = self.dir
    def visit_Try(self, node):
        guarded = False
        for h in node.handlers:
            t = h.type
            names = []
            if t is None:
                guarded = True
            else:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name): names.append(x.id)
                    if isinstance(x, ast.Attribute): names.append(x.attr)
                if any(n in ('ImportError', 'ModuleNotFoundError', 'Exception', 'BaseException') for n in names):
                    guarded = True
        if guarded: self.guard += 1
        for n in node.body: self.visit(n)
        if guarded: self.guard -= 1
        for h in node.handlers:
            for n in h.body: self.visit(n)
        for n in node.orelse + node.finalbody: self.visit(n)
    visit_TryStar = visit_Try
    def visit_FunctionDef(self, node):
        self.depth += 1; self.generic_visit(node); self.depth -= 1
    visit_AsyncFunctionDef = visit_FunctionDef
    def visit_ClassDef(self, node):
        self.generic_visit(node)
    def handle(self, dotted, names, lineno, level):
        global n_imports
        n_imports += 1
        r = rel(self.path)
        if level:
            base = self.pkgdir
            for _ in range(level - 1):
                base = os.path.dirname(base)
            parts = dotted.split('.') if dotted else []
            target = os.path.join(base, *parts) if parts else base
            if parts:
                if os.path.isfile(target + '.py'):
                    kind, tpath = 'module', target + '.py'
                elif os.path.isdir(target):
                    kind, tpath = 'package', os.path.join(target, '__init__.py')
                else:
                    unresolved.append((r, lineno, '.' * level + dotted, 'relative module not found', bool(self.guard)))
                    return
            else:
                kind, tpath = 'package', os.path.join(base, '__init__.py')
            self.check_names(kind, tpath, names, lineno, '.' * level + (dotted or ''))
            return
        top = dotted.split('.')[0]
        if top in stdlib:
            return
        extra = [self.dir]
        res = resolve_abs(dotted, extra)
        if res is None:
            # is top-level internal?
            if top in internal_tops or resolve_abs(top, extra) is not None:
                unresolved.append((r, lineno, dotted, 'internal module not found', bool(self.guard)))
            else:
                t = third[top]
                t['files'].add(r)
                t['subs'].add(dotted)
                if self.guard: t['guarded'] += 1
                else:
                    t['unguarded'] += 1
                    if self.depth == 0: t['toplevel_unguarded'] += 1
            return
        kind, tpath = res
        self.check_names(kind, tpath, names, lineno, dotted)
    def check_names(self, kind, tpath, names, lineno, dotted):
        if not names:
            return
        r = rel(self.path)
        if kind == 'nspkg':
            for nm in names:
                if nm == '*': continue
                if not (os.path.isfile(os.path.join(tpath, nm + '.py')) or os.path.isdir(os.path.join(tpath, nm))):
                    missing_names.append((r, lineno, dotted, nm, 'not a submodule of namespace dir', bool(self.guard)))
            return
        if not os.path.isfile(tpath):
            # package dir without __init__
            pdir = os.path.dirname(tpath)
            for nm in names:
                if nm == '*': continue
                if not (os.path.isfile(os.path.join(pdir, nm + '.py')) or os.path.isdir(os.path.join(pdir, nm))):
                    missing_names.append((r, lineno, dotted, nm, 'no __init__ and no submodule', bool(self.guard)))
            return
        bound, star, hook = module_names(tpath)
        if bound is None or star or hook:
            return
        pdir = os.path.dirname(tpath) if kind == 'package' else None
        for nm in names:
            if nm == '*': continue
            if nm in bound: continue
            if pdir and (os.path.isfile(os.path.join(pdir, nm + '.py')) or os.path.isdir(os.path.join(pdir, nm))):
                continue
            missing_names.append((r, lineno, dotted, nm, 'name not bound at module top level', bool(self.guard)))
    def visit_Import(self, node):
        for a in node.names:
            self.handle(a.name, [], node.lineno, 0)
    def visit_ImportFrom(self, node):
        self.handle(node.module or '', [a.name for a in node.names], node.lineno, node.level)

for p in pyfiles:
    try:
        tree = ast.parse(open(p, encoding='utf-8', errors='replace').read())
    except SyntaxError as e:
        syntax_errors.append((rel(p), str(e)))
        continue
    V(p).visit(tree)

print('python files scanned:', len(pyfiles), 'import statements:', n_imports, 'syntax errors:', len(syntax_errors))
for s in syntax_errors: print('  SYNTAX', s)
print('internal top-level names:', sorted(internal_tops))
print()
print('UNRESOLVED intra-project imports:', len(unresolved))
for u in unresolved: print('  ', u)
print()
print('MISSING NAMES (from X import name; name not bound in X):', len(missing_names))
for u in missing_names: print('  ', u)
print()
print('THIRD-PARTY top-level packages:', len(third))
for k in sorted(third, key=str.lower):
    t = third[k]
    print(f"  {k}: files={len(t['files'])} unguarded={t['unguarded']} (module-level {t['toplevel_unguarded']}) guarded={t['guarded']} e.g. {sorted(t['files'])[:4]} subs={sorted(t['subs'])[:6]}")
json.dump({'unresolved': unresolved, 'missing_names': missing_names,
           'third': {k: {'files': sorted(v['files']), 'guarded': v['guarded'], 'unguarded': v['unguarded'], 'toplevel_unguarded': v['toplevel_unguarded'], 'subs': sorted(v['subs'])} for k, v in third.items()}},
          open(out_json, 'w'), indent=1)
