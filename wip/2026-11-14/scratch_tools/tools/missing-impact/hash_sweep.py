"""Hash every file (and every zip member, read-only) under given roots; report matches with the missing list by sha256 or by basename/size."""
import sys, os, hashlib, zipfile, io
missing = {}
for line in open(sys.argv[1], encoding='utf-8'):
    parts = line.split(None, 2)
    if len(parts) == 3:
        missing[parts[1]] = (int(parts[0]), parts[2].strip())
names = {os.path.basename(p): (h, s) for h, (s, p) in missing.items()}
sizes = {s: p for h, (s, p) in missing.items()}
count = 0; zcount = 0
def check(label, data_hash, size, base):
    if data_hash in missing:
        print('SHA256 MATCH :', missing[data_hash][1], '<=', label)
    elif base in names:
        print('NAME ONLY    :', base, 'size', size, 'want', names[base][1], '<=', label)
def scan_zip(label, fileobj, depth=0):
    global zcount
    try:
        with zipfile.ZipFile(fileobj) as z:
            for info in z.infolist():
                if info.is_dir(): continue
                zcount += 1
                base = os.path.basename(info.filename)
                if info.file_size in sizes or base in names or info.filename.lower().endswith('.zip'):
                    data = z.read(info)
                    check(label + '!' + info.filename, hashlib.sha256(data).hexdigest(), info.file_size, base)
                    if info.filename.lower().endswith('.zip') and depth < 2:
                        scan_zip(label + '!' + info.filename, io.BytesIO(data), depth + 1)
    except (zipfile.BadZipFile, OSError) as exc:
        print('unreadable zip', label, type(exc).__name__)
for root in sys.argv[2:]:
    for dp, dn, fn in os.walk(root):
        if '.git' in dn: dn.remove('.git')
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.islink(p) or not os.path.isfile(p): continue
            count += 1
            size = os.path.getsize(p)
            h = hashlib.sha256()
            with open(p, 'rb') as s:
                for block in iter(lambda: s.read(1 << 20), b''): h.update(block)
            check(p, h.hexdigest(), size, f)
            if f.lower().endswith(('.zip', '.docx', '.xlsx')):
                scan_zip(p, p)
print('files hashed:', count, 'zip members listed:', zcount)
