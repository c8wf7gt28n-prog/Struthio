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
WRITE_SUFFIXES={'.c','.h','.S','.s','.ld','.py','.md','.json','.txt','.yaml','.yml','.csv','.jsonl','.cmd','.sh','.js','.mjs','.css','.html','.webmanifest'}
READ_SUFFIXES={'.c','.h','.S','.s','.ld','.py','.md','.json','.txt','.yaml','.yml','.csv','.jsonl','.cmd','.sh',
               '.js','.mjs','.css','.html','.webmanifest','.sv','.v','.vhd','.lpf','.kicad_sch','.kicad_pcb','.xml'}
EDIT_DIRS=['development/diag_ticket_isolation/src/','firmware/f133/src/','firmware/f133/include/','firmware/stage/','sdk/include/','examples/','workbench/']
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

def _handle(request:dict[str,Any],allow_writes:bool=False)->dict[str,Any]:
    if not isinstance(request,dict): raise AgentError('expected JSON object')
    method=request.get('method'); params=request.get('params',{})
    if not isinstance(params,dict): raise AgentError('params must be object')
    if isinstance(method,str) and method.startswith('engineering.'):
        from .engine import engineering
        from .engineering_kernel import Principal
        scopes=frozenset({'read','execute','candidate'} if allow_writes else {'read','execute'})
        return engineering(ROOT).dispatch(method.removeprefix('engineering.'),params,Principal('jsonl-agent',scopes))
    if method=='files.write':
        raise AgentError('Direct agent writes retired: use engineering.candidates.create/patch with --allow-writes, then operator review')
    if method=='hello':
        return {'protocol':PROTOCOL,'project':'Arc Ledger 1.3 REVIEW','transport':'stdio JSON lines','device_connected':False,
                'flash_enabled':False,'source_writes_enabled':allow_writes,
                'evidence':'HOST_SIM or STATIC_CHECK only'}
    if method=='capabilities':
        return {'engineering_capabilities':'engineering.capabilities','direct_source_writes':False,
                'methods':['hello','capabilities','status','files.list','files.read','build.f133','build.d213',
                           'build.both','build.fpga45','build.fpga12','test.game','build.game','inspect.hardware','inspect.brand','inspect.workbench','doctor','boot.simulate','cartridge.package','cartridge.inspect','cartridge.stream','launcher.list','launcher.launch_sim','launcher.status','launcher.stop_sim','inspect.resources',
                           'inspect.nor','plan.nor','inspect.readiness','inspect.tools',
                           'inspect.project','files.search','inspect.activity','development.prepare','development.inspect','development.brief','development.run','inspect.hardware_import','inspect.hardware_review','test.struthio_port','sim.host','sim.system','sim.compare'],
                'file_write_requires_sha256':True,'file_write_requires_opt_in':True,'flash_methods':[],
                'arbitrary_command_execution':False}
    if method in ('development.prepare','development.inspect','development.brief','development.run'):
        from . import development,engine
        if method=='development.run':
            if set(params)-{'mode'}:raise AgentError('Unknown development run parameter')
            plan=engine.development_plan(params.get('mode','compare'),ROOT)
            proc=subprocess.run(plan.process_args(ROOT),cwd=ROOT,capture_output=True,text=True,timeout=110)
            return {'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'case':development.inspect(ROOT)}
        if params:raise AgentError(method+' takes no parameters')
        if method=='development.prepare':
            if not allow_writes:raise AgentError('Case preparation needs --allow-writes')
            return development.prepare(ROOT)
        if method=='development.brief':return {'text':development.brief(ROOT),'evidence':'HOST_SIM'}
        return development.inspect(ROOT)
    if method=='inspect.hardware_review':
        if params:raise AgentError('inspect.hardware_review takes no parameters')
        from .engine import hardware_review_snapshot
        return hardware_review_snapshot(ROOT)
    if method=='inspect.hardware_import':
        if params:raise AgentError('inspect.hardware_import takes no parameters')
        from .hardware_import import inspect
        return inspect(ROOT)
    if method=='test.struthio_port':
        if params:raise AgentError('test.struthio_port takes no parameters')
        from .engine import ledger_plan
        p=ledger_plan('parity',ROOT)
        proc=subprocess.run(p.process_args(ROOT),cwd=ROOT,capture_output=True,text=True,timeout=110)
        return {'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'evidence':'HOST_SIM','report':'build/arc_ledger/p11-host-latest.json'}
    if method=='status':
        manifest=ROOT/'firmware'/'build'/'stage'/'manifest.json'
        m=json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else None
        return {'firmware_stage':m,'pcb_status':'FABRICATION HOLD',
                'lcd_status':'HOST_SIM ONLY','windows11_qualified':False,'hardware_deployment':False}
    if method in ('inspect.project','inspect.activity','files.search'):
        from . import project_services, activity
        if method=='files.search':
            if set(params)-{'query','archives','case_sensitive','limit'}:raise AgentError('Unknown search option')
            if any(type(params[k]) is not bool for k in ('archives','case_sensitive') if k in params):
                raise AgentError('Search flags must be boolean')
            return project_services.search(ROOT,params.get('query'),**{k:v for k,v in params.items() if k!='query'})
        if params:raise AgentError(method+' takes no parameters')
        return project_services.overview(ROOT) if method=='inspect.project' else {'events':activity.recent(ROOT)}
    if method in ('sim.host','sim.system','sim.compare'):
        from . import engine
        if set(params)-{'project','frames','scenario','profile'}:raise AgentError('Unknown simulation option')
        plan=engine.simulation_plan(method.split('.')[1],params.get('project','examples/hello_arc1'),ROOT,
                                    params.get('frames',120),params.get('scenario'),params.get('profile'))
        proc=subprocess.run([*plan.process_args(ROOT),'--json'],cwd=ROOT,capture_output=True,text=True,
                            encoding='utf-8',errors='replace',timeout=120)
        if len(proc.stdout)>200000 or len(proc.stderr)>200000:raise AgentError('Tool output exceeds limit')
        try:output=json.loads(proc.stdout)
        except ValueError:output={'stdout':proc.stdout,'stderr':proc.stderr}
        return {'exit_code':proc.returncode,'tool_result':output,'evidence':'HOST_SIM' if method!='sim.compare' else 'SCENARIO_ASSUMPTION'}
    if method=='inspect.workbench':
        if params:
            raise AgentError('inspect.workbench takes no parameters')
        from .engine import workbench_sections
        return {'root': 'workbench/README.md', 'sections': workbench_sections(ROOT),
                'read_only_inspection': True}
    if method in ('inspect.nor', 'plan.nor'):
        from .nor_staging import NorStage, StageError, inspect
        try:
            if method == 'inspect.nor':
                if params:
                    raise AgentError('inspect.nor takes no parameters')
                return inspect(ROOT)
            if set(params) != {'partition_id', 'image_path'}:
                raise AgentError('plan.nor requires partition_id and image_path only')
            full, relative = _path(params['image_path'])
            model = NorStage(ROOT)
            model.stage(params['partition_id'], full)
            return model.review()  # host-only, immutable source references; no writes
        except (StageError, OSError) as exc:
            raise AgentError(str(exc)) from exc
    if method in ('inspect.readiness', 'inspect.tools'):
        if params:
            raise AgentError(method + ' takes no parameters')
        if method == 'inspect.readiness':
            from .readiness import snapshot
            return snapshot(ROOT)
        from .tool_inventory import inspect
        return inspect()
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
        if full.suffix not in WRITE_SUFFIXES or not any(rel.startswith(d) for d in EDIT_DIRS):
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

def handle(request:dict[str,Any],allow_writes:bool=False)->dict[str,Any]:
    from . import activity
    method=request.get('method') if isinstance(request,dict) else None
    # Only catalogued names are recorded: arbitrary request text could contain secrets.
    known={'hello','capabilities','status','files.list','files.read','files.write','inspect.project','files.search',
           'development.prepare','development.inspect','development.brief','development.run','inspect.hardware_import','inspect.hardware_review','test.struthio_port','sim.host','sim.system','sim.compare','inspect.readiness','inspect.tools','inspect.workbench',
           'inspect.nor','plan.nor','inspect.resources','boot.simulate',*ACTIONS}
    logged=method if isinstance(method,str) and method in known else 'other request'
    if method!='inspect.activity':activity.record(ROOT,'AGENT',logged,'RUNNING')
    lock=None
    try:
        if method in ACTIONS or method in ('files.write','development.prepare','development.run','test.struthio_port','sim.host','sim.system','sim.compare'):
            from .execution_lock import ExecutionLock
            lock=ExecutionLock(ROOT)
            if not lock.acquire():raise AgentError('Another GUI/agent command owns this project; try again later')
        result=_handle(request,allow_writes)
        state='FAIL' if isinstance(result,dict) and result.get('exit_code',0) else 'PASS'
        if method!='inspect.activity':activity.record(ROOT,'AGENT',logged,state)
        return result
    except Exception:
        if method!='inspect.activity':activity.record(ROOT,'AGENT',logged,'ERROR')
        raise
    finally:
        if lock:lock.release()


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
