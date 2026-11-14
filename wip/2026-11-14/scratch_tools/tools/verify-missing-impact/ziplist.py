import sys, zipfile, hashlib
for p in sys.argv[1:]:
    z = zipfile.ZipFile(p)
    print(p, len(z.infolist()), "entries")
    for i in z.infolist():
        h = hashlib.sha256(z.read(i)).hexdigest()
        print("  %10d %10d %s %s" % (i.file_size, i.compress_size, h, i.filename))
