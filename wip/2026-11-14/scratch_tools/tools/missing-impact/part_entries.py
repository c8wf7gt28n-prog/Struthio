import sys, zipfile, json, hashlib, os
up = sys.argv[1]; rp = json.load(open(sys.argv[2])); mani = json.load(open(sys.argv[3]))
want = {r['sha256']: r['name'] for r in rp['parts']}
have = {}
for f in sorted(os.listdir(up)):
    if not f.endswith('.zip'): continue
    h = hashlib.sha256(open(os.path.join(up, f), 'rb').read()).hexdigest()
    if h in want and want[h] not in have: have[want[h]] = os.path.join(up, f)
print('official parts on hand:', sorted(have))
print('official parts NOT on hand:', sorted(set(want.values()) - set(have)))
entries = {}
for name, path in sorted(have.items()):
    with zipfile.ZipFile(path) as z:
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        print(name, 'entries', len(names), 'chunks', [n for n in names if n.startswith('__LS_RELEASE_CHUNKS__/')])
        for n in names: entries.setdefault(n, []).append(name)
dups = {n: p for n, p in entries.items() if len(p) > 1}
print('duplicate entries across parts:', len(dups))
files = set(mani['files']) | {'MANIFEST.json'}
split = set(rp['file_chunks'])
all_chunks = {c['entry'] for g in rp['file_chunks'].values() for c in g['chunks']}
expected_entries = (files - split) | all_chunks
print('expected part entries overall:', len(expected_entries), '| on hand:', len(set(entries)), '| not on hand:', len(expected_entries - set(entries)))
for n in sorted(expected_entries - set(entries)): print('  NOT ON HAND:', n, mani['files'].get(n, {}).get('bytes', ''))
print('unexpected entries on hand:', sorted(set(entries) - expected_entries)[:10])
