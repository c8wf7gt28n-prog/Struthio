"""Provider/GUI-independent, hash-bound access to reusable ARC UX assets."""
from functools import lru_cache
import hashlib,json
from io import BytesIO
from pathlib import Path, PurePosixPath
import zipfile
from .record_store import inside, load, sha


@lru_cache(maxsize=4)
def _archive(path, expected, size, mtime):
    p=Path(path)
    if p.stat().st_size>32*1024*1024 or sha(p)!=expected:raise ValueError('UX_PACK_CHANGED')
    # Hold a validated immutable byte snapshot; no shared ZipFile seek state.
    return p.read_bytes()


@lru_cache(maxsize=2)
def _solid(path,expected,size,mtime):
    raw=_archive(path,expected,size,mtime)
    with zipfile.ZipFile(BytesIO(raw)) as z:
        if set(z.namelist())!={'INDEX.json','DATA.bin'} or len(z.namelist())!=2:raise ValueError('UX_SOLID_MEMBERS')
        if z.getinfo('INDEX.json').file_size>2*1024**2 or z.getinfo('DATA.bin').file_size>32*1024**2:raise ValueError('UX_SOLID_BYTE_BOUND')
        index=json.loads(z.read('INDEX.json'));data=z.read('DATA.bin')
    if not isinstance(index,dict) or len(index)>20000:raise ValueError('UX_SOLID_INDEX')
    for name,span in index.items():
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name or not isinstance(span,list) or len(span)!=2 or any(type(x) is not int or x<0 for x in span) or span[1]>8*1024**2 or sum(span)>len(data):raise ValueError('UX_SOLID_SPAN')
    return index,data

class AssetPack:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.meta=load(inside(self.root,'branding/ux17/catalog.json'))
        if self.meta.get('schema')!='arc.ux-assets/1':raise ValueError('UX_CATALOG_SCHEMA')
        self.icons={r['id']:r for r in self.meta['icons']}

    def catalog(self,query='',limit=100):
        if not isinstance(query,str) or len(query)>200 or type(limit) is not int or not 1<=limit<=200:raise ValueError('UX_QUERY_LIMIT')
        found=[r for r in self.icons.values() if query.casefold() in str(r).casefold()]
        return {'schema':'arc.ux-catalog/1','edition':self.meta['edition'],'total_icons':len(self.icons),
                'matches':len(found),'icons':found[:limit],'truncated':len(found)>limit,
                'variants':self.meta['variants'],'pack_sha256':self.meta['pack_sha256'],'runtime_network_required':False}

    def read(self,name):
        pure=PurePosixPath(name)
        if pure.is_absolute() or '..' in pure.parts or '\\' in name or name not in self.meta['files']:raise ValueError('UX_ASSET_NOT_CATALOGUED')
        p=inside(self.root,self.meta['pack_path']);s=p.stat()
        data=_archive(str(p),self.meta['pack_sha256'],s.st_size,s.st_mtime_ns)
        if self.meta.get('pack_storage')=='solid-v1':
            index,blob=_solid(str(p),self.meta['pack_sha256'],s.st_size,s.st_mtime_ns)
            if set(index)!=set(self.meta['files']):raise ValueError('UX_SOLID_CATALOG_MISMATCH')
            offset,length=index[name];raw=blob[offset:offset+length]
        elif self.meta.get('pack_storage','files-v1')=='files-v1':
            with zipfile.ZipFile(BytesIO(data)) as z:
                info=z.getinfo(name)
                if info.file_size>8*1024*1024:raise ValueError('UX_ASSET_SIZE_LIMIT')
                raw=z.read(info)
        else:raise ValueError('UX_STORAGE_UNSUPPORTED')
        if hashlib.sha256(raw).hexdigest()!=self.meta['files'][name]:raise ValueError('UX_ASSET_CHANGED')
        return raw

    def svg(self,name,variant='dark',size=24):
        name=self.meta['aliases'].get(name,name)
        if name not in self.icons or variant not in self.meta['variants']:raise ValueError('UX_ICON_OR_VARIANT_UNKNOWN')
        folder='svg16' if size<=18 else 'svg'
        return self.read('02_icons/'+folder+'/'+variant+'/'+name+'.svg')
