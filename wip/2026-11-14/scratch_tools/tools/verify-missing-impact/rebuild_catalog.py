import sys, json, sqlite3, hashlib, pathlib
seed = pathlib.Path(sys.argv[1])
man = json.loads((seed/'manifest.json').read_text(encoding='utf-8'))
print('manifest keys', sorted(man.keys()), 'records', man['records'], 'files', man['files'])
print('index sha', hashlib.sha256((seed/'index.sqlite').read_bytes()).hexdigest())
db = sqlite3.connect((seed/'index.sqlite').as_uri()+'?mode=ro', uri=True)
rows = [json.loads(r[0]) for r in db.execute('SELECT payload FROM records ORDER BY rowid')]
print('rows', len(rows))
cat = {'schema': 'arc.stacy-ledger-seed/1', 'seed_id': man['seed_id'], 'records': rows,
       'scope': 'Ledger application sources and explicit owner intent; no imported hardware or vendor facts.'}
raw = json.dumps(cat, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
print('rebuilt bytes', len(raw), 'sha', hashlib.sha256(raw).hexdigest(), 'match manifest files:', hashlib.sha256(raw).hexdigest()==man['files']['catalog.json'])
# MODEL_TRIAL_01 text
for r in rows:
    if r['id']=='document:docs/MODEL_TRIAL_01.md':
        b = r['text'].encode('utf-8')
        print('MODEL_TRIAL_01 bytes', len(b), hashlib.sha256(b).hexdigest(), 'inputs entry', man['inputs'].get('docs/MODEL_TRIAL_01.md'))
# carried inputs
def carried(name): return name.endswith(('.md','.txt')) and (name.startswith('docs/') or name=='AGENTS.md')
print('inputs', len(man['inputs']), 'carried-eligible', sum(1 for n in man['inputs'] if carried(n)))
