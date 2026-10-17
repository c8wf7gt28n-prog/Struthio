"""ARC-1 Agent Interface R07: stdio JSON lines, no listener or external shell.

The human GUI and AI client use the same on-disk project. All modifications require
--allow-writes and a matching SHA-256. No hardware writes exist in this interface.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL='arc1.agent/1'
_LAUNCHER=None
def launcher():
    global _LAUNCHER
    if _LAUNCHER is None:
        from .launcher import HostLauncher
        _LAUNCHER=HostLauncher(ROOT)
    return _LAUNCHER
READ_SUFFIXES={'.c','.h','.S','.s','.ld','.py','.md','.json','.txt','.yaml','.yml','.csv','.cmd','.sh'}
EDIT_DIRS=['firmware/f133/src/','firmware/f133/include/','firmware/stage/','sdk/include/','examples/','workbench/']
# Named build/test/inspect operations come from the shared engine, the same
# table the Qt Workbench uses (R10), so GUI and agent cannot drift apart.
from .engine import AGENT_ACTIONS as ACTIONS

class AgentError(Exception):
    pass

def _path(value:str)->tuple[Path,str]:
    if not isinstance(value,str) or not value or len(value)>512 or '\x00' in value:
        raise AgentError('invalid path')
    p=Path(value)
    if p.is_absolute() or any(x in ('.','..') for x in p.parts):
        raise AgentError('only normalized relative project paths are allowed')
    full=(ROOT/p).resolve()
    try: rel=full.relative_to(ROOT.resolve()).as_posix()
    except ValueError: raise AgentError('path escapes project root')
    return full,rel

def _read(full):
    if full.suffix not in READ_SUFFIXES or not full.is_file():
        raise AgentError('file unavailable for text read')
    if full.stat().st_size>1024*1024:
        raise AgentError('file too large for agent text read (1 MiB limit)')
    data=full.read_bytes()
    return {'content':data.decode('utf-8'),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}

def handle(request:dict[str,Any],allow_writes:bool=False)->dict[str,Any]:
    if not isinstance(request,dict): raise AgentError('expected JSON object')
    method=request.get('method'); params=request.get('params',{})
    if not isinstance(params,dict): raise AgentError('params must be object')
    if method=='hello':
        return {'protocol':PROTOCOL,'project':'ARC-1 Workbench R07','transport':'stdio JSON lines','device_connected':False,
                'flash_enabled':False,'source_writes_enabled':allow_writes,
                'evidence':'HOST_SIM or STATIC_CHECK only'}
    if method=='capabilities':
        return {'methods':['hello','capabilities','status','files.list','files.read','files.write','build.f133','build.d213',
                           'build.both','build.lcd','test.firmware','test.game','build.game','inspect.hardware','inspect.brand','doctor','boot.simulate','cartridge.package','cartridge.inspect','cartridge.stream','launcher.list','launcher.launch_sim','launcher.status','launcher.stop_sim','inspect.resources'],
                'file_write_requires_sha256':True,'file_write_requires_opt_in':True,'flash_methods':[],
                'arbitrary_command_execution':False}
    if method=='status':
        manifest=ROOT/'firmware'/'build'/'stage'/'manifest.json'
        m=json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else None
        return {'firmware_stage':m,'pcb_status':'FABRICATION HOLD',
                'lcd_status':'HOST_SIM ONLY','windows11_qualified':False,'hardware_deployment':False}
    if method=='inspect.resources':
        # Same cited figures the Qt Inspector draws; unknown values stay null.
        from .resources import load
        try:return load(ROOT)
        except (OSError,ValueError,KeyError) as e:raise AgentError('resource budgets unavailable: '+str(e))
    if method=='boot.simulate':
        from .bootlogic import simulate
        try:return simulate(params.get('events', []))
        except ValueError as e:raise AgentError(str(e))
    if method in ('cartridge.package','cartridge.inspect','cartridge.stream'):
        from .cartridge import package_game,inspect_cartridge,simulate_stream,CartridgeError
        if method=='cartridge.package':
            if not allow_writes:raise AgentError('cartridge packaging needs --allow-writes')
            out=ROOT/'cartridges'/'hello_arc1.arc1cart'
            try:return package_game(ROOT/'examples'/'hello_arc1',out)
            except (CartridgeError,OSError) as exc:raise AgentError(str(exc))
        value=params.get('path','cartridges/hello_arc1.arc1cart')
        full,rel=_path(value)
        if not rel.startswith('cartridges/') or full.suffix!='.arc1cart':
            raise AgentError('cartridge must be inside the Workbench cartridge shelf')
        try:
            if method=='cartridge.inspect':return inspect_cartridge(full)
            allowed={'frames','bandwidth_mib_s','latency_ms','chunk_bytes','prefetch_frames','consumption_bytes_per_frame'}
            if set(params)-{'path'}-allowed:raise AgentError('unknown stream parameter')
            return simulate_stream(full,**{k:v for k,v in params.items() if k in allowed})
        except (CartridgeError,OSError) as exc:raise AgentError(str(exc))
    if method in ('launcher.list','launcher.launch_sim','launcher.status','launcher.stop_sim'):
        from .launcher import games_on_shelf,LauncherError
        try:
            if method=='launcher.list':return {'games':games_on_shelf(ROOT),'evidence':'HOST_ARCHIVE_VERIFICATION_ONLY','board_observed':False}
            if method=='launcher.launch_sim':
                if set(params)-{'path','frames'}:raise AgentError('unknown launch parameter')
                return launcher().start(params.get('path','cartridges/hello_arc1.arc1cart'),frames=params.get('frames',120))
            if method=='launcher.status':return launcher().status()
            return launcher().stop()
        except LauncherError as exc:raise AgentError(exc.code+': '+str(exc)) from exc
    if method=='files.list':
        full,rel=_path(params.get('path','firmware'))
        if not full.is_dir():raise AgentError('not a directory')
        nodes=[]
        for entry in sorted(full.iterdir(),key=lambda p:(p.is_file(),p.name.lower())):
            if entry.is_symlink() or entry.name.startswith('.') or entry.name in ('__pycache__','build'):
                continue
            nodes.append({'name':entry.name,'path':str(entry.relative_to(ROOT)).replace('\\','/'),
                          'type':'directory' if entry.is_dir() else 'file'})
            if len(nodes)>=250:break
        return {'directory':rel,'entries':nodes}
    if method=='files.read':
        full,rel=_path(params.get('path'))
        return {'path':rel,**_read(full)}
    if method=='files.write':
        if not allow_writes:raise AgentError('source editing disabled; start with --allow-writes to opt in')
        full,rel=_path(params.get('path'))
        if full.suffix not in READ_SUFFIXES or not any(rel.startswith(d) for d in EDIT_DIRS):
            raise AgentError('path not in editable source directories')
        if full.is_symlink() or not full.is_file():raise AgentError('file must already exist and not be a symlink')
        content=params.get('content'); expected=params.get('expected_sha256')
        if not isinstance(content,str) or len(content.encode('utf-8'))>1024*1024:
            raise AgentError('replacement content must be UTF-8 <=1MiB')
        if not isinstance(expected,str) or len(expected)!=64:
            raise AgentError('expected_sha256 required')
        existing=full.read_bytes()
        if hashlib.sha256(existing).hexdigest()!=expected:
            raise AgentError('stale source: SHA-256 mismatch; no change made')
        import os,tempfile
        fd,tmp=tempfile.mkstemp(prefix='.arc1-agent-',dir=full.parent)
        try:
            with os.fdopen(fd,'wb') as f: f.write(content.encode('utf-8'))
            os.chmod(tmp, full.stat().st_mode & 0o777)
            os.replace(tmp,full)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return {'path':rel,'sha256':hashlib.sha256(content.encode()).hexdigest(),'bytes':len(content.encode()),'written':True}
    if method in ACTIONS:
        cmd=[sys.executable,str(ROOT/'arc1'),*ACTIONS[method],'--json']
        proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
        if len(proc.stdout)>200000 or len(proc.stderr)>200000: raise AgentError('tool output exceeds limit')
        try: output=json.loads(proc.stdout)
        except json.JSONDecodeError: output={'stdout':proc.stdout,'stderr':proc.stderr}
        return {'exit_code':proc.returncode,'tool_result':output}
    raise AgentError('unknown or unauthorized method')

def serve(allow_writes=False,instream=None,outstream=None):
    incoming=instream or sys.stdin; outgoing=outstream or sys.stdout
    for line in incoming:
        if not line.strip():continue
        try:
            if len(line)>1200000: raise AgentError('request too large')
            req=json.loads(line)
            rid=req.get('id') if isinstance(req,dict) else None
            result=handle(req,allow_writes)
            response={'id':rid,'ok':True,'result':result}
        except (AgentError,ValueError,TypeError,UnicodeError,subprocess.TimeoutExpired) as e:
            response={'id':locals().get('rid',None),'ok':False,'error':{'message':str(e)}}
        except Exception as e:
            response={'id':locals().get('rid',None),'ok':False,'error':{'message':'internal failure: '+type(e).__name__}}
        outgoing.write(json.dumps(response,ensure_ascii=False,separators=(',',':'))+'\n')
        outgoing.flush()
    return 0

if __name__=='__main__':
    serve('--allow-writes' in sys.argv[1:])
