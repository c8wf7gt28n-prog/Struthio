import sys, os, re
root = sys.argv[1]
pats = sys.argv[2:]
rx = [re.compile(p, re.I) for p in pats]
skip_ext = {'.png','.webp','.jpg','.jpeg','.gz','.zip','.jar','.otf','.ttf','.sqlite','.sqlite3','.mp3','.ogg','.wav','.pdf','.ico','.woff','.woff2','.bin'}
for dp, dn, fn in os.walk(root):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, root)
        if os.path.splitext(f)[1].lower() in skip_ext: continue
        try:
            data = open(p, 'rb').read()
        except OSError: continue
        try: text = data.decode('utf-8')
        except UnicodeDecodeError: text = data.decode('latin-1')
        for i, line in enumerate(text.split('\n'), 1):
            for r in rx:
                m = r.search(line)
                if m:
                    s = max(0, m.start()-150); e = min(len(line), m.end()+150)
                    print(f'{rel}:{i}: [{r.pattern}] ...{line[s:e]}...')
                    break
