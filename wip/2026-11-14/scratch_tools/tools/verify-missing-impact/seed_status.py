import sys, json, hashlib, pathlib
def carried(name): return name.endswith(('.md','.txt')) and (name.startswith('docs/') or name=='AGENTS.md')
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
root = pathlib.Path(sys.argv[1]); overlay = sys.argv[2] if len(sys.argv)>2 else None
seed = root/'project/stacy_seed/current'
man = json.loads((seed/'manifest.json').read_text(encoding='utf-8'))
print('seed_id ok', man['seed_id']==sha(canonical(man['inputs'])), 'file set', set(man['files']))
for name, exp in man['files'].items():
    p = seed/name
    if name=='catalog.json' and overlay and not p.exists(): p = pathlib.Path(overlay)
    if not p.is_file(): print('  MEMBER MISSING ->INVALID:', name); continue
    print('  member', name, sha(p.read_bytes())==exp)
changed=[];missing=[];absent=[]
for name, exp in man['inputs'].items():
    p = root/name
    if carried(name) and not p.exists(): absent.append(name); continue
    if not p.is_file(): missing.append(name); continue
    if sha(p.read_bytes())!=exp: changed.append(name)
print('records', man['records'], 'changed', changed, 'missing', missing, 'carried absent', len(absent), absent[:5])
