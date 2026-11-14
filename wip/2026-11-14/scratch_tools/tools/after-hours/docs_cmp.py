import sys, sqlite3, json, os, re
db, root = sys.argv[1], sys.argv[2]
con = sqlite3.connect('file:' + db + '?mode=ro&immutable=1', uri=True)
mds = {n: open(os.path.join(root, n), encoding='utf-8').read() for n in os.listdir(root) if n.endswith('.md')}
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
for rid, kind, rev, payload in con.execute('select id, kind, revision, payload from desk_records'):
    d = json.loads(payload)
    keys = [k for k in d if k != 'blocks']
    print('---', rid, kind, 'rev', rev, {k: (d[k] if not isinstance(d[k], (dict, list)) else type(d[k]).__name__) for k in keys})
    body = '\n'.join(b['text'] for b in d['blocks'])
    title = d.get('title') or d.get('name') or ''
    best = None
    for n, md in mds.items():
        mdbody = norm(re.sub(r'^# .*\n', '', md, count=1))
        if norm(body) == mdbody:
            best = n
            print('   body identical (whitespace-normalised) to', n, '| md H1:', md.splitlines()[0], '| record title:', title)
    if not best: print('   NO md match; first block:', d['blocks'][0]['text'][:80])
    for k in ('origin', 'provenance', 'report', 'source', 'links'):
        if k in d: print('   ', k, '=', json.dumps(d[k])[:600])
