import sys, os, json, hashlib, stat
root = sys.argv[1]  # Graphite_Backup dir
m = json.load(open(os.path.join(root, 'BACKUP.json'), 'rb'))
print('keys', list(m.keys()))
print('schema', m.get('schema'), 'created', m.get('created'), 'models_included', m.get('models_included'))
print('scope', m.get('scope'))
print('skipped', m.get('skipped'))
files = m['files']; dirs = m['directories']
print('listed files', len(files), 'listed dirs', len(dirs))
ok = bad = absent = 0
listed = set()
tot = 0
for f in files:
    rel = os.path.join(f['area'], f['path'])
    listed.add(rel)
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        absent += 1; print('ABSENT', rel); continue
    b = open(p, 'rb').read()
    h = hashlib.sha256(b).hexdigest()
    tot += len(b)
    if len(b) == f['bytes'] and h == f['sha256']:
        ok += 1
    else:
        bad += 1; print('MISMATCH', rel, len(b), f['bytes'], h, f['sha256'])
print('match', ok, 'mismatch', bad, 'absent', absent, 'total bytes', tot, 'listed bytes', sum(f['bytes'] for f in files))
ldirs = set(os.path.join(d['area'], d['path']) for d in dirs)
ondisk_f = set(); ondisk_d = set()
for dp, dn, fn in os.walk(root):
    for n in fn:
        r = os.path.relpath(os.path.join(dp, n), root)
        ondisk_f.add(r)
    for n in dn:
        ondisk_d.add(os.path.relpath(os.path.join(dp, n), root))
print('on-disk files', len(ondisk_f), 'dirs', len(ondisk_d))
print('present-but-unlisted files', sorted(ondisk_f - listed))
print('listed-but-absent dirs', sorted(ldirs - ondisk_d))
print('present-but-unlisted dirs', sorted(ondisk_d - ldirs))
from collections import Counter
print('kinds', Counter(f['kind'] for f in files), 'areas', Counter(f['area'] for f in files))
print('modes', Counter(oct(f['mode']) for f in files))
# symlinks?
for dp, dn, fn in os.walk(root):
    for n in fn+dn:
        p=os.path.join(dp,n)
        if os.path.islink(p): print('SYMLINK', p)
