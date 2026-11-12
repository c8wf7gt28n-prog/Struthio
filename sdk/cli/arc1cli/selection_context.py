"""Portable revision-bound selection records. Presentation never grants rights."""
import hashlib
import json
import re

CONTRACT='arc.workspace-selection/1'
SHA=re.compile(r'[0-9a-f]{64}\Z')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def clean(value):
    fields={'schema','board_revision','kind','reference','native_uuid','revision','source_manifest'}
    if not isinstance(value,dict) or set(value)!=fields or value['schema']!=CONTRACT:
        raise ValueError('SELECTION_FIELDS')
    if value['board_revision']!='R10' or value['kind'] not in ('component','net'):
        raise ValueError('SELECTION_KIND_OR_BOARD')
    for key,limit in [('reference',500),('native_uuid',200)]:
        text=value[key]
        if not isinstance(text,str) or not 1<=len(text)<=limit or any(ord(c)<32 for c in text):
            raise ValueError('SELECTION_IDENTITY')
    if not isinstance(value['revision'],str) or not SHA.fullmatch(value['revision']):
        raise ValueError('SELECTION_REVISION')
    manifest=value['source_manifest']
    if not isinstance(manifest,dict) or not 1<=len(manifest)<=100:
        raise ValueError('SELECTION_MANIFEST')
    for path,row in manifest.items():
        if (not isinstance(path,str) or not path or len(path)>600 or path.startswith(('/','\\'))
            or '\\' in path or ':' in path or any(p in ('..','') or p.startswith('.') for p in path.split('/'))):
            raise ValueError('SELECTION_PATH')
        if not isinstance(row,dict) or set(row)!={'sha256','bytes'}:
            raise ValueError('SELECTION_SOURCE')
        if row['sha256'] is not None and (not isinstance(row['sha256'],str) or not SHA.fullmatch(row['sha256'])):
            raise ValueError('SELECTION_SOURCE_HASH')
        if row['bytes'] is not None and (type(row['bytes']) is not int or row['bytes']<0):
            raise ValueError('SELECTION_SOURCE_SIZE')
    if value['revision']!=digest(manifest):raise ValueError('SELECTION_BINDING')
    return json.loads(json.dumps(value))


def make(kind,reference,native_uuid,manifest):
    return clean({'schema':CONTRACT,'board_revision':'R10','kind':kind,'reference':reference,
        'native_uuid':native_uuid,'revision':digest(manifest),'source_manifest':manifest})


def currency(selection,current_manifest,native_uuid):
    selected=clean(selection)
    if selected['native_uuid']!=native_uuid:return 'IDENTITY_CHANGED'
    if selected['source_manifest']!=current_manifest:return 'STALE'
    return 'CURRENT_INPUTS'
