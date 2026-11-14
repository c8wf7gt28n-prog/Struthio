import json,sys,re
from pathlib import Path
root=Path(sys.argv[1])
off=json.loads((root/'App/OFFLINE_FILES.json').read_text())
print('schema',off.get('schema'),'target',off.get('target'),'python_target',off.get('python_target'))
print('top keys',list(off.keys()))
files=off['files']
debs=[k for k in files if k.startswith('debs/')]
whl=[k for k in files if k.startswith('wheels/')]
other=[k for k in files if not (k.startswith('debs/') or k.startswith('wheels/'))]
print('debs',len(debs),sum(files[k]['bytes'] for k in debs))
print('wheels',len(whl),sum(files[k]['bytes'] for k in whl))
print('other',other)
# sha list
lines=(root/'App/DEBIAN_USB.sha256').read_text().splitlines()
m={}
for l in lines:
    d,n=l.split(None,1); m[n]=d
print('sha256 list entries',len(m))
print('debs in sha list',sum(1 for n in m if n.startswith('debs/')),'wheels',sum(1 for n in m if n.startswith('wheels/')))
print('names equal to OFFLINE_FILES + self:',set(m)==set(files)|{'OFFLINE_FILES.json'})
mism=[n for n in files if m.get(n)!=files[n]['sha256']]
print('hash mismatches between the two inventories',mism[:5],len(mism))
print('--- wheels'); 
for k in sorted(whl): print(files[k]['bytes'],k)
print('--- debs names')
names=sorted(k[5:].split('_')[0] for k in debs)
print(' '.join(names))
for sub in ('Records','System','Wheels','App'):
    d=json.loads((root/sub/'RELEASE_PARTS.json').read_text())
    print('==',sub,{k:(v if not isinstance(v,(list,dict)) else '<%d>'%len(v)) for k,v in d.items()})
    print('  parts',len(d['parts']),'bytes',sum(p['bytes'] for p in d['parts']),'names',d['parts'][0]['name'],'..',d['parts'][-1]['name'])
    print('  file_chunks',{k:len(v['chunks']) for k,v in d.get('file_chunks',{}).items()})
