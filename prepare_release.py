"""Assemble verified duplicate assets after extracting the three ordinary ZIPs.

No archive concatenation, external packages, network, file deletion or overwrite.
"""
from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path,PurePosixPath

def load(path,limit=4*1024**2):
    if path.stat().st_size>limit:raise ValueError('Release metadata is too large')
    return json.loads(path.read_text())
def safe(root,name):
    pure=PurePosixPath(name)
    if not isinstance(name,str) or pure.is_absolute() or '..' in pure.parts or '\\' in name or ':' in name or any(x in {'.ledger','.git','__pycache__'} for x in pure.parts):raise ValueError('Invalid release member')
    path=root.joinpath(*pure.parts)
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Linked paths are not release targets')
    return path

def prepare(root):
    root=Path(root).absolute()
    if not (root/'DELIVERY.json').is_file():return {'state':'LEGACY_NO_ASSEMBLY'}
    delivery=load(root/'DELIVERY.json');manifest_raw=(root/'MANIFEST.json').read_bytes();manifest=load(root/'MANIFEST.json')
    if delivery.get('schema')!='arc.three-zip-delivery/1' or delivery.get('parts')!=3:raise ValueError('Unknown release delivery format')
    for index in (1,2,3):
        p=root/('delivery-part-'+str(index)+'.json')
        if not p.is_file():raise ValueError('Extract all THREE ZIP packages into the same parent folder before starting Ledger. Missing part '+str(index))
        receipt=load(p,4096)
        if receipt!={'schema':'arc.delivery-part/1','part':index,'release_id':delivery['release_id'],'manifest_sha256':hashlib.sha256(manifest_raw).hexdigest()}:raise ValueError('Mixed release parts: use all three packages from the same delivery')
    aliases=delivery['aliases'];files=manifest['files']
    if not isinstance(aliases,dict) or len(aliases)>2000:raise ValueError('Invalid duplicate asset table')
    # Check every ordinary file first. No partial assembly on a missing component.
    for name,row in files.items():
        p=safe(root,name)
        if name in aliases:
            source=aliases[name]
            if source in aliases or name not in files or source not in files or files[source]!=row:raise ValueError('Duplicate asset identity mismatch')
            if not p.exists():continue
        if not p.is_file() or p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Release file is missing or changed: '+name)
    created=[]
    for name,source in aliases.items():
        p=safe(root,name)
        if p.exists():continue
        raw=safe(root,source).read_bytes();p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=files[name]['sha256']:raise ValueError('Duplicate asset readback failed: '+name)
        created.append(name)
    return {'state':'READY','parts_verified':3,'duplicate_assets_created':len(created),'all_existing_files_preserved':True,'network_calls':0}
if __name__=='__main__':
    try:print(json.dumps(prepare(Path(__file__).resolve().parent),indent=2))
    except (ValueError,OSError,KeyError,TypeError) as exc:print('Ledger package check: '+str(exc),file=sys.stderr);raise SystemExit(1)
