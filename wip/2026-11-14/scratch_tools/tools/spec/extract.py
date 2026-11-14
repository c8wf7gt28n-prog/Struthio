import sys, re, json
from pypdf import PdfReader
r = PdfReader(sys.argv[1]); out = sys.argv[2]
pages = []
for i, p in enumerate(r.pages, 1):
    try: t = p.extract_text() or ''
    except Exception as e: t = '[extract failed: %r]' % e
    pages.append(t)
    open('%s/p%03d.txt' % (out, i), 'w').write(t)
print('pages', len(pages), 'chars', sum(map(len, pages)))
keys = ['objects and instruments', 'Work objects with shared', 'Overview and detail', 'Historical working surface', 'Lain', 'Navi', 'Hello computer',
        'desk as a working composition', 'Terminal lettering', 'Color meanings', 'Today as a calm', 'Work as a shared artifact', 'Retained methods as usable',
        'Cooperation that shows', 'Construction freedom', 'layer', 'depth', 'wired', 'Wired']
for k in keys:
    hits = [i for i, t in enumerate(pages, 1) if k in t]
    print('%-34s %s' % (k, hits[:30]))
