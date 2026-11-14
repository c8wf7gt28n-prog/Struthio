# Orchestrator's own restore: copy hash-verified manifest files from the extracted parts into one tree, join split files.
import json, os, hashlib, shutil, sys
X, DEST = sys.argv[1], sys.argv[2]
T=os.path.join(X,'Graphite_00_START_HERE','Graphite_Transfer')
parts=['Graphite_0.2a13_part_01','Graphite_0.2a13_part_05_2','Graphite_0.2a13_part_06','Graphite_0.2a13_part_07','Graphite_0.2a13_part_08','Graphite_0.2a13_part_09','Graphite_0.2a13_part_02','Graphite_0.2a13_part_03','Graphite_0.2a13_part_04']
files=json.load(open(os.path.join(X,parts[0],'MANIFEST.json')))['files']
rp=json.load(open(os.path.join(T,'App','RELEASE_PARTS.json')))
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
n=0; dup=0
for d in parts:
    root=os.path.join(X,d)
    for dp,_,fn in os.walk(root):
        for f in fn:
            p=os.path.join(dp,f); rel=os.path.relpath(p,root)
            if rel=='MANIFEST.json' or rel in files:
                out=os.path.join(DEST,rel)
                if os.path.exists(out): dup+=1; continue
                if rel in files: assert sha(p)==files[rel]['sha256'], rel
                os.makedirs(os.path.dirname(out),exist_ok=True); shutil.copyfile(p,out); n+=1
for path,info in rp['file_chunks'].items():
    srcs=[]
    for c in info['chunks']:
        hit=[os.path.join(X,d,c['entry']) for d in parts if os.path.exists(os.path.join(X,d,c['entry']))]
        if not hit: srcs=None; break
        srcs.append(hit[0])
    if srcs:
        out=os.path.join(DEST,path); os.makedirs(os.path.dirname(out),exist_ok=True)
        with open(out,'wb') as o:
            for s in srcs: o.write(open(s,'rb').read())
        assert sha(out)==info['sha256']; n+=1; print('joined',path)
    else: print('cannot join (chunks absent):',path)
missing=[k for k in files if not os.path.exists(os.path.join(DEST,k))]
print('restored',n,'duplicates across parts',dup,'still missing',len(missing))
open(os.path.join(DEST,'..','full_MISSING.txt'),'w').write('\n'.join(f"{files[k]['bytes']:>10}  {files[k]['sha256']}  {k}" for k in sorted(missing))+'\n')
