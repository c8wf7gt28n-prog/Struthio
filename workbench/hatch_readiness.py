"""Owner-host preflight and bounded, isolated entry points to existing I05 checks."""
from __future__ import annotations
import argparse,hashlib,json,os,platform,shutil,signal,socket,sqlite3,subprocess,sys,time,uuid
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from . import locations,doctor,brain_runtime,math_backend,experiment_runtime,office_math_runtime

ROOT=locations.PACKAGE
REFERENCE_SHA='00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'
REFERENCE_BUILD='b11669'
REFERENCE_RUNTIME_SHA='cf07c1c112d709bd67e522017471de57ed0ec8bea031d732c5422351c07f65ac'
REFERENCE_COMMIT='620d2225cc436ab0b001e3200e590e3b286ef9ab'
MODES=('model-diagnostic','model-family','visible-calc')


def selected_model(workspace):
    """Read the existing selection without constructing a Kernel or workspace."""
    path=Path(workspace)/'.ledger/engineering.sqlite3'
    if not path.is_file():return None
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db, db:
            row=db.execute("SELECT value FROM settings WHERE key='brain.selection'").fetchone()
            selection=json.loads(row[0]) if row else {}
            row=db.execute('SELECT value FROM settings WHERE key=?',('brain.model.'+selection.get('model_id',''),)).fetchone()
            files=json.loads(row[0]).get('files',[]) if row else []
            return Path(files[0]['path']) if len(files)==1 else None
    except (OSError,ValueError,KeyError,TypeError,AttributeError,sqlite3.Error):return None


def runtime_probe():
    value=brain_runtime.status(ROOT);value['reference_match']=False
    if value['state']=='PINNED_CPU_AVAILABLE':
        entry=value['pin']['platforms'][value['platform']]
        path=(ROOT/brain_runtime.PIN).parent/entry['archive']
        with path.open('rb') as stream:value['archive_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        value['reference_match']=(value['build']==REFERENCE_BUILD and value['source_commit']==REFERENCE_COMMIT
            and value['archive_sha256']==REFERENCE_RUNTIME_SHA and entry['sha256']==REFERENCE_RUNTIME_SHA)
    return {k:v for k,v in value.items() if k!='pin'}


def model_probe(path):
    if path is None:return {'state':'MISSING','ready':False,'required_sha256':REFERENCE_SHA,'reason':'Select the reference GGUF in Brain or pass --model FILE. No weights are downloaded.'}
    path=Path(path).expanduser().resolve()
    if not path.is_file():return {'state':'MISSING','ready':False,'path':str(path),'reason':'The selected model file is absent.'}
    digest=hashlib.sha256();began=time.monotonic();before=path.stat()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):
            if time.monotonic()-began>60:return {'state':'HASH_BUDGET_EXHAUSTED','ready':False,'path':str(path)}
            digest.update(block)
    after=path.stat();current=(before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
    sha=digest.hexdigest();ready=current and sha==REFERENCE_SHA
    return {'state':'REFERENCE_HASH_VERIFIED' if ready else 'CHANGED_DURING_READ' if not current else 'DIFFERENT_MODEL',
        'ready':ready,'path':str(path),'bytes':after.st_size,'sha256':sha,'required_sha256':REFERENCE_SHA,
        'seconds':time.monotonic()-began,'notice':'This I05 reference family uses its recorded model. Other models remain usable through their existing Graphite routes.'}


def socket_probe(family):
    try:
        with socket.socket(family,socket.SOCK_STREAM) as stream:
            if family==socket.AF_INET:stream.bind(('127.0.0.1',0));stream.listen(1)
        return {'ready':True,'state':'AVAILABLE'}
    except OSError as exc:return {'ready':False,'state':'UNAVAILABLE','reason':str(exc)}


def display_probe():
    display=os.environ.get('DISPLAY');backend=os.environ.get('QT_QPA_PLATFORM','')
    result={'ready':False,'display':display,'wayland_display':os.environ.get('WAYLAND_DISPLAY'),'qt_backend':backend or 'default',
        'state':'X11_NOT_VERIFIED','notice':'A connectable display is a prerequisite, not visible Calc acceptance.'}
    if backend.split(':')[0] in ('offscreen','minimal'):
        return {**result,'reason':'Offscreen/minimal Qt cannot qualify visible Calc.'}
    command=shutil.which('xdpyinfo')
    if not display or not command:return {**result,'reason':'A live X11 DISPLAY and xdpyinfo are required for this native-session check.'}
    try:
        child=subprocess.run([command,'-display',display],capture_output=True,text=True,timeout=3)
        return {**result,'ready':child.returncode==0,'state':'X11_CONNECTABLE' if child.returncode==0 else 'X11_CONNECTION_FAILED',
            'reason':None if child.returncode==0 else child.stderr[-400:]}
    except (OSError,subprocess.SubprocessError) as exc:return {**result,'reason':str(exc)}


def collect(workspace=None,model=None):
    began=time.monotonic();workspace=doctor.chosen_root(workspace);parts={};timings={}
    def probe(name,fn):
        start=time.monotonic()
        try:parts[name]=fn()
        except Exception as exc:parts[name]={'ready':False,'available':False,'state':'ERROR','reason':str(exc)[:500]}
        timings[name]=time.monotonic()-start
    probe('doctor',lambda:doctor.probe(workspace))
    probe('math',math_backend.status)
    probe('office',office_math_runtime.probe)
    probe('python_wasi',experiment_runtime.status)
    probe('loopback',lambda:socket_probe(socket.AF_INET))
    probe('unix_socket',lambda:socket_probe(socket.AF_UNIX))
    probe('display',display_probe)
    def qt():
        from PySide6.QtCore import qVersion
        from PySide6 import QtWidgets
        return {'ready':qVersion()=='6.8.3','version':qVersion(),'state':'IMPORTED','scope':'Core/Widgets imports only; no window opened.'}
    probe('qt',qt)
    chosen=Path(model) if model else selected_model(workspace)
    probe('model',lambda:model_probe(chosen))
    probe('runtime',runtime_probe);runtime=parts['runtime'];d=parts.get('doctor',{})
    package=(d.get('payload',{}).get('state')=='VERIFIED' and d.get('foundation',{}).get('state')=='VERIFIED_SOURCE_BINDINGS')
    common={'linux_host':platform.system()=='Linux','program_integrity':package,
        'operation_registry':bool(d.get('inventory',{}).get('schema_digest')),
        'pinned_math':all(isinstance(parts['math'].get(n),dict) and parts['math'][n].get('state')=='PINNED' for n in math_backend.PINS),
        'native_office_bridge':bool(parts['office'].get('available')),'protected_python':bool(parts['python_wasi'].get('available')),
        'local_loopback':parts['loopback']['ready']}
    memory=d.get('host',{}).get('available_ram_bytes') or 0
    model_gate={**common,'reference_runtime':runtime.get('reference_match',False),
        'reference_model':parts['model'].get('ready',False),'reference_memory':memory>=6144*1024*1024}
    visible_gate={**common,'qt_core_widgets':parts['qt'].get('ready',False),'connectable_x11':parts['display']['ready'],
        'unix_sockets':parts['unix_socket']['ready']}
    gates={name:{'ready':all(values.values()),'checks':values,'blockers':[k for k,v in values.items() if not v]}
        for name,values in [('model',model_gate),('visible_calc',visible_gate)]}
    return {'schema':'ledger.hatch-readiness/1','state':'READY_FOR_EXPLICIT_TRIAL' if all(g['ready'] for g in gates.values()) else 'BLOCKED',
        'captured_utc':datetime.now(timezone.utc).isoformat(),'workspace':str(workspace),'program':str(ROOT),'python':sys.executable,
        'host_scope':'CURRENT_EXECUTION_HOST; owner ThinkPad identity is not assumed','runtime':{k:v for k,v in runtime.items() if k!='pin'},
        'parts':parts,'gates':gates,'seconds':time.monotonic()-began,'timings':timings,
        'preflight_effects':{'model_generations':0,'jobs_started':0,'workspace_created':False,'packages_or_weights_downloaded':False},
        'acceptance':'NOT_PERFORMED; preflight never closes I05, I06 or a HATCH milestone.'}


def supervise(command,folder,seconds):
    """Bound one owned runner; retain output and terminate only verified descendants."""
    from .operation_stop import owned_tree,kill_owned,process_identity
    started=time.monotonic();state='RETURNED';refs=[]
    with (folder/'stdout.log').open('wb') as stdout,(folder/'stderr.log').open('wb') as stderr:
        child=subprocess.Popen(command,cwd=ROOT,env=locations.child_env(ROOT),stdout=stdout,stderr=stderr,start_new_session=True)
        try:child.wait(timeout=seconds)
        except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
            state='BUDGET_EXHAUSTED' if isinstance(exc,subprocess.TimeoutExpired) else 'INTERRUPTED'
            refs=owned_tree([child.pid]);child.send_signal(signal.SIGINT)
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:pass
        finally:
            if state!='RETURNED':kill_owned(refs)
            if child.poll() is None:child.kill();child.wait(timeout=3)
    return {'state':state,'returncode':child.returncode,'seconds':time.monotonic()-started,'budget_seconds':seconds,
        'runner_descendants_gone':all(process_identity(r.pid)!=r.token for r in refs)}


def cleanup_trial(folder):
    """Use existing owner cancellation/identity checks inside this new fixture only."""
    from .baseline import environment
    from .engineering_kernel import Kernel,operator
    from . import local_brain,work_trail,operation_stop
    root=folder/'Office';database=root/'.ledger/engineering.sqlite3'
    if not database.exists():return {'state':'NOT_CREATED','active_jobs':0}
    if any(p.is_symlink() for p in (folder,root,root/'.ledger',database)):return {'state':'REFUSED_LINKED_FIXTURE'}
    with patch.dict(os.environ,{**environment(os.environ,root,folder/'profile'),'HOME':str(folder/'Home')}):
        kernel=Kernel(root);p=operator();work_trail.hold(kernel,p);problems=[]
        for job in kernel.listing('jobs'):
            if job['owner']!=p.identity:problems.append('Unexpected fixture job owner');continue
            if job['state'] in ('Queued','Running'):
                response=kernel.dispatch('jobs.cancel',{'id':job['id']},p)
                if not response.get('ok'):problems.append('Cancellation refused: '+job['id']);continue
                confirmed=operation_stop.force_cancel_worker(kernel,job)
                live=kernel.record('jobs',job['id'])
                if not confirmed and live.get('pid') and operation_stop.process_identity(live['pid']) is not None:
                    problems.append('Worker exit unconfirmed: '+job['id'])
        try:local_brain.stop(kernel,'HATCH_OWNED_FIXTURE_FINISHED')
        except (ValueError,OSError) as exc:problems.append(str(exc))
        active=[j['id'] for j in kernel.listing('jobs') if j['state'] in ('Queued','Running')]
    return {'state':'CLEANUP_REQUIRED' if problems or active else 'CONFIRMED','active_jobs':len(active),'problems':problems}


def run_trial(mode,report,folder,seconds):
    """The unchanged checkers create fresh bounded grants and retain first-failure stop."""
    key='visible_calc' if mode=='visible-calc' else 'model'
    if not report['gates'][key]['ready']:return {'state':'BLOCKED_BEFORE_LAUNCH','blockers':report['gates'][key]['blockers']}
    if shutil.disk_usage(folder).free<1024**3:return {'state':'BLOCKED_BEFORE_LAUNCH','blockers':['At least 1 GiB free in the trial output filesystem is required.']}
    trial=folder/'trial';output=folder/'trial-result.json'
    command=[sys.executable,'-B','-m','workbench.joined_checks' if mode=='visible-calc' else 'workbench.joined_model_checks',
        '--keep',str(trial),'--output',str(output)]
    command+=['--visible'] if mode=='visible-calc' else ['--model',report['parts']['model']['path']]
    (folder/'trial-intent.json').write_text(json.dumps({'mode':mode,'command':command,'budget_seconds':seconds,
        'fixture':str(trial),'frozen_criteria_modified':False,'execution_authority':'EXPLICIT_OWNER_CLI; existing checkers create scoped fixture grants'},indent=2)+'\n')
    result={}
    try:result=supervise(command,folder,seconds)
    except (OSError,ValueError,subprocess.SubprocessError) as exc:result={'state':'FAILED','reason':str(exc)}
    finally:
        cleanup_started=time.monotonic()
        try:result['cleanup']=cleanup_trial(trial)
        except Exception as exc:result['cleanup']={'state':'CLEANUP_REQUIRED','reason':str(exc)}
        result['cleanup_seconds']=time.monotonic()-cleanup_started
    if output.is_file() and output.stat().st_size<16*1024*1024:
        try:result['checker_state']=json.loads(output.read_text()).get('state')
        except ValueError:result['checker_state']='PARTIAL_OR_UNREADABLE_REPORT'
    result['scope']='DEVELOPMENT_DIAGNOSTIC' if mode=='model-diagnostic' else 'EXPLICIT_FROZEN_FAMILY_REVIEW_REQUIRED' if mode=='model-family' else 'VISIBLE_NATIVE_CHECK_REVIEW_REQUIRED'
    result['acceptance_promoted']=False
    result['execution_effects']='Isolated fixture jobs may have run; counts and validated generations belong to the checker receipt. Preflight counters exclude this trial.'
    if not result.get('runner_descendants_gone',True) or result.get('cleanup',{}).get('state') not in ('CONFIRMED','NOT_CREATED'):result['state']='CLEANUP_REQUIRED'
    elif result['state']=='RETURNED':result['state']='CHECKER_REVIEW_REQUIRED' if result['returncode']==0 and result.get('checker_state','').startswith('PASSED') else 'FAILED'
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,help='Existing workspace to inspect; never initialized by preflight')
    parser.add_argument('--model',type=Path,help='Existing reference GGUF; otherwise inspect the saved selection read-only')
    parser.add_argument('--output',type=Path,help='New report directory; an existing path is refused')
    parser.add_argument('--run',choices=MODES,help='Explicit isolated trial after its prerequisites pass; absent means report only')
    parser.add_argument('--budget-seconds',type=int,help='Diagnostic default 600; a full model-family budget must be supplied explicitly')
    args=parser.parse_args(argv)
    if args.run=='model-family' and args.budget_seconds is None:parser.error('--run model-family requires a declared --budget-seconds')
    budget=args.budget_seconds if args.budget_seconds is not None else 600
    if not 1<=budget<=7200:parser.error('--budget-seconds must be 1 to 7200')
    folder=(args.output or Path.cwd()/('hatch-check-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])).expanduser().absolute()
    try:folder.mkdir(parents=True,exist_ok=False,mode=0o700)
    except OSError as exc:parser.error('Use a new writable --output directory: '+str(exc))
    report=collect(args.workspace,args.model)
    (folder/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.run:
        report['trial']=run_trial(args.run,report,folder,budget)
        (folder/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['Graphite - HATCH readiness',report['state'],'']
    labels={'linux_host':'Linux host','program_integrity':'program/source integrity','operation_registry':'command registry',
        'pinned_math':'pinned SymPy, mpmath and Z3','native_office_bridge':'Calc/Writer and Java bridge',
        'protected_python':'protected Python (wasmtime==50.0.1)','local_loopback':'local TCP sockets',
        'reference_runtime':'pinned b11669 CPU runtime','reference_model':'exact reference GGUF',
        'reference_memory':'6 GiB available memory','qt_core_widgets':'Qt Core/Widgets 6.8.3',
        'connectable_x11':'connectable X11 display and xdpyinfo','unix_sockets':'Unix sockets'}
    for key,gate in report['gates'].items():
        lines.append(key+': '+('READY TO ATTEMPT' if gate['ready'] else 'BLOCKED'))
        lines.extend('  Missing/unverified: '+labels.get(k,k) for k in gate['blockers'])
    lines+=['','Preflight starts no model or jobs. Actual trials require --run. No acceptance result is promoted.',
        'No packages or weights are installed by this command.','Report: '+str(folder/'readiness.json')]
    if args.run:lines.append('Trial: '+report['trial']['state'])
    (folder/'READ_ME.txt').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
    if args.run:return 0 if report['trial']['state']=='CHECKER_REVIEW_REQUIRED' else 2
    return 0 if report['state']=='READY_FOR_EXPLICIT_TRIAL' else 2


if __name__=='__main__':raise SystemExit(main())
