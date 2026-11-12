"""Provider/GUI-independent access to optional owner-supplied project artwork."""
from pathlib import Path
from .record_store import inside,load,sha

CATALOG='branding/editorial/catalog.json'


def artwork(root):
    root=Path(root).resolve()
    if not (root/CATALOG).is_file():return None
    data=load(inside(root,CATALOG),cap=64000)
    if (data.get('schema')!='arc.editorial-art/1' or data.get('classification')!='EDITORIAL_CONCEPT_ART'
            or data.get('engineering_authority') is not False or data.get('workflow_authority') is not False):
        raise ValueError('EDITORIAL_ART_CATALOG_INVALID')
    name=data.get('path','')
    if not isinstance(name,str) or not name.startswith('branding/editorial/'):
        raise ValueError('EDITORIAL_ART_PATH_INVALID')
    path=inside(root,name)
    if path.stat().st_size>8*1024*1024 or sha(path)!=data.get('sha256'):
        raise ValueError('EDITORIAL_ART_CHANGED')
    return data,path
