import sys, zipfile, os, collections
for p in sys.argv[1:]:
    z = zipfile.ZipFile(p)
    il = z.infolist()
    dts = sorted(i.date_time for i in il)
    c = collections.Counter(i.date_time[:3] for i in il)
    print(os.path.basename(p), 'members', len(il), 'files', sum(1 for i in il if not i.is_dir()),
          'min', dts[0], 'max', dts[-1], 'create_system', set(i.create_system for i in il), 'top', set(i.filename.split('/')[0] for i in il))
    print('   by-day', dict(c))
