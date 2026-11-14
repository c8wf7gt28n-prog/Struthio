"""List (never extract to disk) the members of newly arrived part ZIPs and say which of the still-missing payload files they carry."""
import hashlib, json, sys
from pathlib import Path
from zipfile import ZipFile

release = json.loads(Path(sys.argv[1]).read_text())      # App/RELEASE_PARTS.json
manifest = json.loads(Path(sys.argv[2]).read_text())['files']  # restored/MANIFEST.json
restored = Path(sys.argv[3])
zips = [Path(p) for p in sys.argv[4:]]

missing = sorted(n for n in manifest if not (restored / n).is_file())
print('payload files absent from the restored tree:', len(missing))
chunks = {}
for name, meta in release['file_chunks'].items():
    for c in meta['chunks']:
        chunks[c['entry']] = (name, c)

covered = {}
chunk_seen = {}
for z in zips:
    h = hashlib.sha256(z.read_bytes()).hexdigest()
    row = next((p for p in release['parts'] if p['sha256'] == h), None)
    print(f"\n{z.name}: bytes={z.stat().st_size} sha256={h[:16]}.. matches official part: {row['name'] if row else None}")
    with ZipFile(z) as a:
        infos = a.infolist()
        print('   members:', len(infos), 'uncompressed bytes:', sum(i.file_size for i in infos))
        bad = [i.filename for i in infos if i.filename.startswith('/') or '..' in i.filename.split('/') or (i.external_attr >> 16) & 0o170000 == 0o120000]
        print('   absolute/dotdot/symlink members:', bad)
        for i in infos:
            n = i.filename
            if n in manifest:
                data = a.read(i)
                ok = len(data) == manifest[n]['bytes'] and hashlib.sha256(data).hexdigest() == manifest[n]['sha256']
                if n in missing:
                    covered[n] = (z.name, ok)
                elif not ok:
                    print('   MISMATCH vs manifest:', n)
            elif n in chunks:
                data = a.read(i)
                c = chunks[n][1]
                chunk_seen[n] = (z.name, len(data) == c['bytes'] and hashlib.sha256(data).hexdigest() == c['sha256'])
            elif n != 'MANIFEST.json' and not n.endswith('/'):
                print('   member not in manifest or chunk table:', n)

print('\nmissing files now covered by these ZIPs:')
for n in missing:
    print('  ', f"{manifest[n]['bytes']:>10}", n, '->', covered.get(n, 'NOT IN THESE ZIPS'))
print('\nchunk entries carried by these ZIPs:')
for n, (target, c) in sorted(chunks.items()):
    print('  ', n, 'of', target.rsplit('/', 1)[1], '->', chunk_seen.get(n, 'not in these ZIPs'))
still = [n for n in missing if n not in covered]
print('\nstill absent after these ZIPs (non-chunked):', still)
