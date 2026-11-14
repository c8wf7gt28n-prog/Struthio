import json,sys,hashlib
from pathlib import Path
m=json.loads(Path(sys.argv[1]).read_text())
print({k:(v if not isinstance(v,(dict,list)) else '<%s %d>'%(type(v).__name__,len(v))) for k,v in m.items()})
f=m['files']
print('MANIFEST.json listed in itself:', 'MANIFEST.json' in f)
k=next(iter(f));print('sample',k,f[k])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
print('manifest sha', sha(sys.argv[1]))
for name,path in [('PREPARE_DEBIAN.sh',sys.argv[2]+'/App/PREPARE_DEBIAN.sh'),('INSTALL_LS.py',sys.argv[2]+'/INSTALL_LS.py')]:
    print(name,'payload',f[name]['sha256'][:16],'on-disk',sha(path)[:16],f[name]['sha256']==sha(path))
for n in ['INSTALL_GRAPHITE.sh','OFFLINE_FILES.json','DEBIAN_USB.sha256','RELEASE_PARTS.json','LEDGER.sh','requirements-qt.txt','docs/THINKPAD_FIRST_INSTALL.md','tools/package_release_parts.py','tools/package_graphite.py','tests_integrated/test_install_media.py']:
    print(n, n in f)
print('runtimes:',[ (k,v['bytes']) for k,v in f.items() if k.startswith('runtimes/')])
print('gguf/model-ish files:',[k for k in f if k.lower().endswith(('.gguf','.bin','.safetensors'))][:20])
