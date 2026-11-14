import sys, zipfile, hashlib, os
zp, d = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(zp)
print("zip", os.path.basename(zp), os.path.getsize(zp), "testzip", z.testzip())
mem = {}
dirs = 0
dts = set()
for i in z.infolist():
    dts.add(i.date_time[:3])
    if i.is_dir(): dirs += 1; continue
    mem[i.filename] = (i.file_size, hashlib.sha256(z.read(i)).hexdigest())
print("file members", len(mem), "dir members", dirs, "total uncompressed", sum(v[0] for v in mem.values()), "dates", sorted(dts))
print("top-level", sorted({n.split('/')[0] for n in mem}))
disk = {}
for dp, dn, fn in os.walk(d):
    for n in fn:
        p = os.path.join(dp, n)
        disk[os.path.relpath(p, d).replace(os.sep, "/")] = (os.path.getsize(p), hashlib.sha256(open(p, "rb").read()).hexdigest())
print("disk files", len(disk))
print("only in zip", sorted(set(mem) - set(disk))[:10])
print("only on disk", sorted(set(disk) - set(mem))[:10])
print("differing", [k for k in mem if k in disk and mem[k] != disk[k]][:10])
if len(sys.argv) > 3:
    for k in sorted(mem): print(mem[k][1], mem[k][0], k)
