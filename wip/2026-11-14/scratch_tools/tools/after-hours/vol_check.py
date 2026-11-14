import sys, zipfile, json, hashlib, os, sqlite3
zp, outdir = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(zp)
man = json.loads(z.read('Reference_Volume/MANIFEST.json'))
members = {i.filename[len('Reference_Volume/'):]: i for i in z.infolist() if not i.is_dir()}
ok = bad = 0
for name, meta in man['files'].items():
    d = z.read(members[name])
    if len(d) == meta['bytes'] and hashlib.sha256(d).hexdigest() == meta['sha256']: ok += 1
    else: bad += 1; print('MISMATCH', name)
print('volume manifest: listed', len(man['files']), 'match', ok, 'mismatch', bad, 'unlisted members', sorted(set(members) - set(man['files'])))
# extract only INDEX.sqlite bytes to new dir (written by us, not extractall)
p = os.path.join(outdir, 'INDEX.sqlite')
open(p, 'wb').write(z.read('Reference_Volume/INDEX.sqlite'))
con = sqlite3.connect('file:' + p + '?mode=ro&immutable=1', uri=True)
for t, sql in con.execute("select name, sql from sqlite_master where type='table'"):
    n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
    print(n, t, '|', (sql or '')[:160].replace('\n', ' '))
print('integrity', con.execute('pragma integrity_check').fetchall())
