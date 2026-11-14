import json, os, hashlib, sys, subprocess
X=sys.argv[1]; REPO=sys.argv[2]
m=json.load(open(os.path.join(X,'Graphite_0.2a13_part_01','MANIFEST.json')))['files']
g={k:v for k,v in m.items() if k.startswith('games/')}
# hash every file at HEAD in repo working tree
by_sha={}
for dp,dn,fn in os.walk(REPO):
    if '.git' in dp.split(os.sep): continue
    for f in fn:
        p=os.path.join(dp,f)
        h=hashlib.sha256(open(p,'rb').read()).hexdigest()
        by_sha.setdefault(h,[]).append(os.path.relpath(p,REPO))
have=set(l.split()[-1] if False else l.rstrip('\n')[22:] for l in open(sys.argv[3]))
hit=0
for k in sorted(g):
    v=g[k]; r=by_sha.get(v['sha256'])
    hit+= bool(r)
    print(f"{'HAVE' if k in have else 'miss'} {v['bytes']:9d} {k:62s} repo-identical: {r[:3] if r else '-'}")
print('games files',len(g),'identical-in-repo',hit)
