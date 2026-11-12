"""Bounded virtual thumb-drive package, not a USB BOT/FAT/physical driver.

A package carries trusted locally built native code. Integrity is not a
signature, sandbox or permission to execute arbitrary uploaded programs.
"""
from io import BytesIO
import hashlib,json,zipfile,re

MAX_PACKAGE=8*1024*1024

class MediaError(ValueError):
    pass


def pack(card,artifact,revision):
    record={'schema':'arc.virtual-usb/1','revision':revision,'gamecard':card}
    stream=BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('gamecard.json',json.dumps(record,sort_keys=True))
        z.writestr(card['artifact'],artifact)
    return stream.getvalue()


def inspect(data,*,target,revision,artifact_sha256,sources,artifact_name=None):
    if not isinstance(data,bytes) or not 1<=len(data)<=MAX_PACKAGE:raise MediaError('MEDIA_SIZE')
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            entries=z.infolist();names=[i.filename for i in entries]
            if len(entries)!=2 or len(set(names))!=2 or 'gamecard.json' not in names:raise MediaError('MEDIA_LAYOUT')
            if any(i.flag_bits&1 or i.file_size>MAX_PACKAGE or i.compress_size>MAX_PACKAGE or (i.external_attr>>16)&0o170000==0o120000 for i in entries):raise MediaError('MEDIA_UNSAFE_ENTRY')
            meta=z.getinfo('gamecard.json')
            if meta.file_size>65536:raise MediaError('MEDIA_METADATA_SIZE')
            r=json.loads(z.read(meta))
            if not isinstance(r,dict) or not isinstance(r.get('gamecard'),dict):raise MediaError('MEDIA_METADATA_SCHEMA')
            card=r['gamecard']
            if r.get('schema')!='arc.virtual-usb/1' or r.get('revision')!=revision:raise MediaError('MEDIA_STALE_SOURCE')
            if card.get('schema')!='arc-os.gamecard/1' or card.get('abi')!=1 or card.get('target')!=target or card.get('physical_boot') is not False:raise MediaError('MEDIA_INCOMPATIBLE')
            name=card.get('artifact')
            if artifact_name is not None and (not isinstance(artifact_name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}\.(so|dylib)',artifact_name)):raise MediaError('MEDIA_ARTIFACT_PATH')
            allowed=(artifact_name,) if artifact_name is not None else ('struthio.so','struthio.dylib')
            if name not in allowed or sorted(names)!=sorted(['gamecard.json',name]):raise MediaError('MEDIA_ARTIFACT_PATH')
            raw=z.read(name)
            if not raw or hashlib.sha256(raw).hexdigest()!=card.get('sha256') or card.get('sha256')!=artifact_sha256:raise MediaError('MEDIA_CORRUPT')
            if card.get('sources')!=sources:raise MediaError('MEDIA_STALE_SOURCE')
            return {'schema':'arc.virtual-usb-read/1','name':name,'artifact':raw,'package_bytes':len(data),'read_bytes':meta.file_size+len(raw),'file_reads':2,'artifact_sha256':artifact_sha256,'revision':revision,'class':'HOST_SIM','physical_usb_packets':None}
    except (zipfile.BadZipFile,KeyError,TypeError,json.JSONDecodeError,UnicodeError,RuntimeError,AttributeError,RecursionError) as exc:
        raise MediaError('MEDIA_CORRUPT: '+str(exc)) from exc
