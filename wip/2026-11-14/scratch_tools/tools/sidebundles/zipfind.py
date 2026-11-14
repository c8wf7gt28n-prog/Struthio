import sys, zipfile, re
pat = re.compile(sys.argv[1], re.I)
for zp in sys.argv[2:]:
    try:
        z = zipfile.ZipFile(zp)
    except Exception as e:
        print("ERR", zp, e); continue
    for n in z.namelist():
        if pat.search(n): print(zp.split("/")[-1], "::", n)
print("done")
