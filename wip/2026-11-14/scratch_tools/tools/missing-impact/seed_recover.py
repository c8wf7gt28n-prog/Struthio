"""Static, read-only reconstruction test: can project/stacy_seed/current/catalog.json and the carried note
docs/MODEL_TRIAL_01.md be rebuilt from index.sqlite + manifest.json alone?  Writes ONLY under the out dir given."""
import sys, json, sqlite3, hashlib, os
from pathlib import Path
seed = Path(sys.argv[1]); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
want_catalog = sys.argv[3]; want_note = sys.argv[4]
manifest = json.loads((seed / 'manifest.json').read_text(encoding='utf-8'))
print('seed manifest keys:', sorted(manifest))
print('seed manifest files:', manifest['files'])
print('seed manifest records:', manifest['records'], 'seed_id:', manifest['seed_id'])
print('inputs count:', len(manifest['inputs']))
print("inputs['docs/MODEL_TRIAL_01.md']:", manifest['inputs'].get('docs/MODEL_TRIAL_01.md'))
idx = seed / 'index.sqlite'
print('index.sqlite sha256:', hashlib.sha256(idx.read_bytes()).hexdigest(), 'bytes', idx.stat().st_size)
db = sqlite3.connect('file:' + str(idx) + '?mode=ro&immutable=1', uri=True)
db.execute('PRAGMA query_only=ON')
print('tables:', [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")])
rows = db.execute('SELECT rowid,id,payload FROM records ORDER BY rowid').fetchall()
print('records rows:', len(rows), 'first ids:', [r[1] for r in rows[:3]], 'last id:', rows[-1][1])
records = [json.loads(r[2]) for r in rows]
SCHEMA = manifest['schema']
catalog = {'schema': SCHEMA, 'seed_id': manifest['seed_id'], 'records': records,
           'scope': 'Ledger application sources and explicit owner intent; no imported hardware or vendor facts.'}
raw = json.dumps(catalog, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
h = hashlib.sha256(raw).hexdigest()
print('rebuilt catalog bytes:', len(raw), 'sha256:', h)
print('  matches seed manifest files[catalog.json]:', h == manifest['files']['catalog.json'])
print('  matches release MANIFEST value given     :', h == want_catalog)
(out / 'catalog.json').write_bytes(raw)
note = next((r for r in records if r['id'] == 'document:docs/MODEL_TRIAL_01.md'), None)
if note is None:
    print('NO record document:docs/MODEL_TRIAL_01.md')
else:
    nraw = note['text'].encode('utf-8'); nh = hashlib.sha256(nraw).hexdigest()
    print('note bytes:', len(nraw), 'sha256:', nh)
    print('  matches seed manifest inputs:', nh == manifest['inputs'].get('docs/MODEL_TRIAL_01.md'))
    print('  matches release MANIFEST value given:', nh == want_note)
    (out / 'MODEL_TRIAL_01.md').write_bytes(nraw)
    print('  first lines:'); print('\n'.join('    ' + l for l in note['text'].splitlines()[:6]))
# which carried/absent notes are in the catalog
docs = [r['id'] for r in records if r['kind'] == 'documentation']
print('documentation records:', len(docs))
db.close()
