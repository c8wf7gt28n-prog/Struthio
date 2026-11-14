import json, re, sys
root='/home/user/Struthio/'
cat=json.load(open(root+'project/stacy_seed/current/catalog.json'))
recs=cat['records']
print('records',len(recs), 'keys', sorted(cat.keys()))
pat=re.compile(r"licen[sc]|copyright|all rights|rights reserved|RIGHTS\.md|proprietary|unlicen|SPDX|redistribut|source[- ]available|non-?commercial|commercial|open[- ]source|copyleft|\bGPL|public(ly)? (release|distribution|repository)|publication|private project|in-house|confidential|trade ?mark|owner-supplied|free-of-charge", re.I)
import os
seen={}
for r in recs:
    t=r.get('text') or ''
    title=r.get('title')
    for m in pat.finditer(t):
        s=max(0,m.start()-110); e=min(len(t), m.end()+150)
        seen.setdefault(title,[]).append((t.count('\n',0,m.start())+1, t[s:e].replace('\n',' ')))
for title,hits in sorted(seen.items(), key=lambda kv: str(kv[0])):
    intree=os.path.exists(root+str(title))
    print('\n##',title,'| in tree:',intree,'| hits',len(hits))
    if not intree or '--all' in sys.argv:
        for ln,h in hits[:12]:
            print('   L%d: %s'%(ln,h))
