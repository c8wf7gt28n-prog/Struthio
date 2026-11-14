import json, os, hashlib, sys, collections
X=sys.argv[1]; OUT=sys.argv[2]
T=os.path.join(X,'Graphite_00_START_HERE','Graphite_Transfer')
parts={'01':'Graphite_0.2a13_part_01','05':'Graphite_0.2a13_part_05_2','06':'Graphite_0.2a13_part_06','07':'Graphite_0.2a13_part_07','08':'Graphite_0.2a13_part_08','09':'Graphite_0.2a13_part_09'}
m=json.load(open(os.path.join(X,parts['01'],'MANIFEST.json')))
files=m['files']
rp=json.load(open(os.path.join(T,'App','RELEASE_PARTS.json')))
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
have={}  # relpath -> part
bad=[]; extra=[]
for pn,d in parts.items():
    root=os.path.join(X,d)
    for dp,dn,fn in os.walk(root):
        for f in fn:
            p=os.path.join(dp,f); rel=os.path.relpath(p,root)
            if rel in files:
                ok = os.path.getsize(p)==files[rel]['bytes'] and sha(p)==files[rel]['sha256']
                have[rel]=pn
                if not ok: bad.append((pn,rel))
            else:
                extra.append((pn,rel,os.path.getsize(p)))
print('manifest files:',len(files),'total bytes:',sum(v['bytes'] for v in files.values()))
print('present & matched:',len(have)-len(bad),'bad:',bad)
print('extra (not in manifest):',extra)
# chunks
chunk_status={}
for path,info in rp['file_chunks'].items():
    st=[]
    for c in info['chunks']:
        found=None
        for pn,d in parts.items():
            p=os.path.join(X,d,c['entry'])
            if os.path.exists(p):
                found=(pn, sha(p)==c['sha256'] and os.path.getsize(p)==c['bytes'])
        st.append((c['entry'],found))
    chunk_status[path]=st
    print('CHUNKED',path,info['bytes'],st)
    if all(s[1] and s[1][1] for s in st):
        h=hashlib.sha256(); n=0
        for c in info['chunks']:
            for pn,d in parts.items():
                p=os.path.join(X,d,c['entry'])
                if os.path.exists(p):
                    b=open(p,'rb').read(); h.update(b); n+=len(b)
        print('   reassembled bytes',n,'sha ok:',h.hexdigest()==info['sha256'], 'manifest sha ok:', h.hexdigest()==files[path]['sha256'])
        have[path]='05+06'
missing={k:v for k,v in files.items() if k not in have}
print('missing files:',len(missing),'bytes:',sum(v['bytes'] for v in missing.values()))
print('have files:',len(have),'bytes:',sum(files[k]['bytes'] for k in have))
def top(k,depth):
    return '/'.join(k.split('/')[:depth]) if '/' in k else '(root)'
for depth in (1,2):
    agg=collections.defaultdict(lambda:[0,0,0,0])
    for k,v in files.items():
        a=agg[top(k,depth)]
        a[0]+=1; a[1]+=v['bytes']
        if k in missing: a[2]+=1; a[3]+=v['bytes']
    print('\n== by dir depth',depth,'(total files, total bytes, MISSING files, MISSING bytes)')
    for k in sorted(agg):
        a=agg[k]
        if depth==2 and a[0]<3 and a[2]==0: continue
        print(f'{k:55s} {a[0]:5d} {a[1]:11d}   missing {a[2]:5d} {a[3]:11d}')
ext=collections.Counter(); exth=collections.Counter()
for k in files:
    e=os.path.splitext(k)[1].lower() or '(none)'
    (ext if k in missing else exth)[e]+=1
print('\nmissing by ext:',ext.most_common())
print('have by ext:',exth.most_common())
ms=sorted(missing.items(), key=lambda kv:-kv[1]['bytes'])
print('\nlargest missing:')
for k,v in ms[:45]: print(f"  {v['bytes']:10d} {k}")
print('smallest have:', sorted((files[k]['bytes'],k,have[k]) for k in have)[:12])
json.dump({'missing':sorted(missing), 'have':have}, open(os.path.join(OUT,'reconcile.json'),'w'), indent=1)
open(os.path.join(OUT,'missing_files.txt'),'w').write('\n'.join(f"{v['bytes']:10d}  {k}" for k,v in sorted(missing.items()))+'\n')
open(os.path.join(OUT,'have_files.txt'),'w').write('\n'.join(f"{files[k]['bytes']:10d}  part{have[k]}  {k}" for k in sorted(have))+'\n')
