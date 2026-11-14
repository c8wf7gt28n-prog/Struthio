"""Independent re-implementation (no project code executed) of stacy_foundation.seed_status and release_integrity.verify,
optionally overlaying replacement files from an overlay dir (path -> file)."""
import sys, ast, json, hashlib, os
from pathlib import Path
root = Path(sys.argv[1]); overlay = Path(sys.argv[2]) if len(sys.argv) > 2 else None
over = {}
if overlay:
    over = {'project/stacy_seed/current/catalog.json': overlay / 'catalog.json'}
def get(name):
    p = over.get(name) or (root / name)
    return p if p.is_file() else None
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
# --- payload verify
mani = json.loads((root / 'MANIFEST.json').read_text())
problems = []
for name, row in mani['files'].items():
    p = get(name)
    if p is None: problems.append(name + ': missing'); continue
    if p.stat().st_size != row['bytes'] or sha(p) != row['sha256']: problems.append(name + ': changed')
print('payload:', 'VERIFIED' if not problems else 'DAMAGED', 'files', len(mani['files']), 'problems', problems)
# --- seed status
tree = ast.parse((root / 'workbench/stacy_foundation.py').read_text(encoding='utf-8'))
consts = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SEED_FILES', 'CARRIED_NOTES', 'SCHEMA', 'SEED_DIR'):
        consts[node.targets[0].id] = ast.literal_eval(node.value)
SEED_INPUTS = set(consts['SEED_FILES']) | set(consts['CARRIED_NOTES'])
print('SEED_FILES', len(consts['SEED_FILES']), 'CARRIED_NOTES', len(consts['CARRIED_NOTES']), 'SEED_INPUTS', len(SEED_INPUTS))
def carried(name): return name.endswith(('.md', '.txt')) and (name.startswith('docs/') or name == 'AGENTS.md')
sd = consts['SEED_DIR']
mp = get(sd + '/manifest.json'); m = json.loads(mp.read_text(encoding='utf-8'))
state = None; reason = None
canonical = lambda v: json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
if m.get('schema') != consts['SCHEMA'] or set(m.get('inputs', {})) != SEED_INPUTS: state, reason = 'INVALID', 'input set or schema differs'
elif m.get('seed_id') != hashlib.sha256(canonical(m['inputs'])).hexdigest(): state, reason = 'INVALID', 'seed identity differs'
elif set(m.get('files', {})) != {'catalog.json', 'index.sqlite'}: state, reason = 'INVALID', 'unexpected members'
else:
    for name, expected in m['files'].items():
        p = get(sd + '/' + name)
        if p is None: state, reason = 'INVALID', 'Source is missing or exceeds its bound: ' + sd + '/' + name; break
        if sha(p) != expected: state, reason = 'INVALID', 'Seed artifact hash mismatch: ' + name; break
if state is None:
    changed, missing, absent = [], [], []
    for name, expected in m['inputs'].items():
        if carried(name) and not (root / name).exists(): absent.append(name); continue
        p = get(name)
        if p is None: missing.append(name)
        elif sha(p) != expected: changed.append(name)
    state = 'SOURCE_UNAVAILABLE' if missing else 'STALE' if changed else 'VERIFIED_SOURCE_BINDINGS'
    print('seed:', state, 'records', m['records'], 'changed', changed, 'missing', missing, 'carried_in_seed(absent from tree)', len(absent))
    print('  absent carried notes that are in CARRIED_NOTES:', len(set(absent) & set(consts['CARRIED_NOTES'])), '| absent but listed in SEED_FILES:', sorted(set(absent) - set(consts['CARRIED_NOTES'])))
else:
    print('seed:', state, '| reason:', reason)
