import sys, zipfile, hashlib, os, json
zp = sys.argv[1]
src = sys.argv[2] if len(sys.argv) > 2 else None
print("zip sha256", hashlib.sha256(open(zp,'rb').read()).hexdigest(), os.path.getsize(zp))
z = zipfile.ZipFile(zp)
print("comment", z.comment)
print("testzip", z.testzip())
hs = {}
for i in z.infolist():
    data = z.read(i) if not i.is_dir() else b""
    h = hashlib.sha256(data).hexdigest()
    hs[i.filename] = h
    print(f"{i.file_size:>9} {i.compress_size:>9} {i.date_time} ct={i.compress_type} ext={i.external_attr>>16:o} {h} {i.filename!r}")
if src:
    for n in sorted(os.listdir(src)):
        p = os.path.join(src, n)
        h = hashlib.sha256(open(p,'rb').read()).hexdigest()
        print("SRC", n, os.path.getsize(p), h, "in zip as:", [k for k,v in hs.items() if v == h])
# print small json/text members
for i in z.infolist():
    if i.filename.lower().endswith((".json", ".md", ".txt", ".sha256")) or "SUMS" in i.filename:
        print("=====", i.filename)
        t = z.read(i).decode("utf-8", "replace")
        print(t[:6000])
