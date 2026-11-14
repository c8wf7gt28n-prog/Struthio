import sys, zipfile, re
z = zipfile.ZipFile(sys.argv[1])
x = z.read('word/document.xml').decode('utf-8', 'replace')
t = re.sub(r'<[^>]+>', ' ', x)
for pat in sys.argv[2:]:
    ms = [m.start() for m in re.finditer(pat, t, re.I)]
    print(pat, len(ms))
    for s in ms[:5]: print('   ...', re.sub(r'\s+', ' ', t[max(0, s-120): s+160]))
