import sys, zipfile
for zp in sys.argv[1:]:
    z = zipfile.ZipFile(zp)
    ts = sorted(i.date_time for i in z.infolist())
    print(zp.split("/")[-1], "members", len(ts), "min", ts[0], "max", ts[-1])
