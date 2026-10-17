"""ARC-1 host-only cartridge archive, verification, and deterministic stream scheduling.

R06 experimental packaging contract: .arc1cart ZIP containing arc1.game.json and
its declared assets. It contains NO native ARC-1 executable. No USB access.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import zipfile

FORMAT = 'arc1.cartridge/0.1-host'
MAX_ASSET = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_ASSETS = 10000
MAX_MANIFEST = 128 * 1024

class CartridgeError(ValueError):
    pass

def _asset_names(manifest: dict) -> list[tuple[str,str]]:
    if not isinstance(manifest,dict):raise CartridgeError('manifest must be a JSON object')
    import re
    if not isinstance(manifest.get('name'),str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}',manifest['name']):
        raise CartridgeError('invalid game name')
    if not isinstance(manifest.get('game_version'),str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',manifest['game_version']):
        raise CartridgeError('invalid game version')
    if manifest.get('schema') != 'arc1.game-package/0.2' or manifest.get('target',{}).get('board_family')!='ARC-1':
        raise CartridgeError('unsupported game manifest or target')
    if manifest.get('verification',{}).get('status') == 'board_tested':
        raise CartridgeError('host packager will not reassert board-tested claims')
    arr=manifest.get('assets')
    if not isinstance(arr,list) or len(arr)>MAX_ASSETS:
        raise CartridgeError('invalid asset list')
    out=[]; seen=set()
    for a in arr:
        if not isinstance(a,dict):raise CartridgeError('invalid asset descriptor')
        name=a.get('path'); sha=a.get('sha256')
        # Match the existing 0.2 schema exactly, excluding path traversal.
        import re
        if not isinstance(name,str) or not re.fullmatch(r'assets/[A-Za-z0-9_]+\.sprite',name):
            raise CartridgeError('asset path not allowed')
        if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
            raise CartridgeError('invalid asset digest')
        if name in seen:raise CartridgeError('duplicate asset name')
        seen.add(name);out.append((name,sha))
    return out

def _bytes_digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def package_game(project:Path,output:Path)->dict:
    project=Path(project).resolve();output=Path(output).resolve()
    mf=project/'arc1.game.json'
    if not mf.is_file():raise CartridgeError('arc1.game.json not found')
    raw=mf.read_bytes()
    if len(raw)>MAX_MANIFEST:raise CartridgeError('manifest too large')
    try:manifest=json.loads(raw)
    except (UnicodeError,ValueError) as e:raise CartridgeError('invalid manifest JSON') from e
    assets=_asset_names(manifest)
    total=0;blobs={}
    for name,expected in assets:
        p=project/name
        if p.is_symlink() or not p.resolve().is_relative_to(project):raise CartridgeError('asset escapes game folder')
        try:
            size=p.stat().st_size
            if size>MAX_ASSET:raise CartridgeError('individual asset exceeds host limit')
            data=p.read_bytes()
        except OSError as e:raise CartridgeError(f'asset unavailable: {name}') from e
        if _bytes_digest(data)!=expected:raise CartridgeError(f'asset digest mismatch: {name}')
        total+=len(data)
        if total>MAX_TOTAL:raise CartridgeError('cartridge exceeds host limit')
        blobs[name]=data
    if output.is_relative_to(project):raise CartridgeError('output cannot overwrite game sources')
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.arc1-cart-',suffix='.tmp',dir=output.parent);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for name,data in [('arc1.game.json',raw),*sorted(blobs.items())]:
                info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o644<<16
                z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
        os.replace(tmp,output)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return {'format':FORMAT,'name':manifest['name'],'game_version':manifest['game_version'],
            'asset_count':len(assets),'asset_bytes':total,'cartridge':str(output),
            'cartridge_sha256':_bytes_digest(output.read_bytes()),'evidence':'HOST_PACKAGE_ONLY',
            'executable_included':False}

def inspect_cartridge(path:Path)->dict:
    path=Path(path)
    try:
        with zipfile.ZipFile(path,'r') as z:
            infos=z.infolist()
            names=[i.filename for i in infos]
            if len(set(names))!=len(names):raise CartridgeError('duplicate entries')
            if 'arc1.game.json' not in names:raise CartridgeError('missing manifest')
            if any(i.is_dir() or i.file_size>MAX_ASSET or i.flag_bits & 1 for i in infos):
                raise CartridgeError('invalid, encrypted, or oversized zip entry')
            if sum(i.file_size for i in infos)>MAX_TOTAL+MAX_MANIFEST:raise CartridgeError('archive too large')
            mi=z.getinfo('arc1.game.json')
            if mi.file_size>MAX_MANIFEST:raise CartridgeError('manifest too large')
            manifest=json.loads(z.read(mi).decode('utf-8'))
            assets=_asset_names(manifest)
            if set(names)!={'arc1.game.json',*(name for name,_ in assets)}:
                raise CartridgeError('unlisted or missing entries')
            total=0
            for name,expected in assets:
                data=z.read(name)
                if _bytes_digest(data)!=expected:raise CartridgeError('asset digest mismatch: '+name)
                total+=len(data)
            return {'format':FORMAT,'name':manifest['name'],'game_version':manifest['game_version'],
                    'asset_count':len(assets),'asset_bytes':total,'cartridge_sha256':_bytes_digest(path.read_bytes()),
                    'valid':True,'evidence':'HOST_ARCHIVE_VERIFICATION_ONLY','executable_included':False}
    except (OSError,zipfile.BadZipFile,UnicodeError,KeyError,ValueError) as e:
        if isinstance(e,CartridgeError):raise
        raise CartridgeError(f'cannot inspect cartridge: {e}') from e

def simulate_stream(path:Path, *, frames:int=120, bandwidth_mib_s:float=5.0,
                    latency_ms:float=4.0, chunk_bytes:int=4096, prefetch_frames:int=12,
                    consumption_bytes_per_frame:int|None=None)->dict:
    """Deterministic throughput/latency model, NOT measured USB or realtime frame rendering.

    Each chunk incurs request latency and throughput time. A buffer is prefetched
    before the first frame. Frames with less bytes buffered than requested stall.
    """
    inf=inspect_cartridge(path)
    if not isinstance(frames,int) or not 1<=frames<=100000:raise CartridgeError('invalid frame count')
    if not isinstance(chunk_bytes,int) or not 1<=chunk_bytes<=1024*1024:raise CartridgeError('invalid chunk size')
    if not isinstance(prefetch_frames,int) or not 0<=prefetch_frames<=600:raise CartridgeError('invalid prefetch duration')
    if not isinstance(latency_ms,(int,float)) or not 0<=latency_ms<=10000:raise CartridgeError('invalid latency')
    if not isinstance(bandwidth_mib_s,(int,float)) or not 0<bandwidth_mib_s<=10000:raise CartridgeError('invalid bandwidth')
    size=inf['asset_bytes']
    rate=bandwidth_mib_s*1048576/1000 # bytes / ms
    perframe=consumption_bytes_per_frame if consumption_bytes_per_frame is not None else max(1,math.ceil(size/frames))
    if not isinstance(perframe,int) or perframe<0 or perframe>MAX_ASSET:raise CartridgeError('invalid consumption rate')
    t=-prefetch_frames*(1000/60);complete=[];delivered=0
    while delivered<size:
        n=min(chunk_bytes,size-delivered)
        t+=latency_ms+n/rate
        delivered+=n;complete.append((t,delivered))
    stalls=[];k=0;buffered=0
    for frame in range(frames):
        deadline=frame*(1000/60)
        while k<len(complete) and complete[k][0]<=deadline:
            buffered=complete[k][1];k+=1
        required=min(size,(frame+1)*perframe)
        if required>buffered:stalls.append(frame)
    return {'cartridge':inf['name'],'format':FORMAT,'frames':frames,'frame_deadline_ms':round(1000/60,5),
            'simulated_stall_frames':len(stalls),'first_stall_frames':stalls[:15],
            'total_asset_bytes':size,'chunk_count':len(complete),'prefetch_frames':prefetch_frames,
            'bandwidth_mib_s':bandwidth_mib_s,'request_latency_ms':latency_ms,
            'consumption_bytes_per_frame':perframe,'evidence':'DETERMINISTIC_HOST_MODEL',
            'physical_usb_tested':False,'sustained_60fps_proven':False}
