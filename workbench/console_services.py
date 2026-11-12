"""Bounded functional-console operations through the existing Kernel authority."""
import threading
from . import record_io as io,console_build
from .console_runtime import ConsoleSession
from sdk.cli.arc1cli import target_plan

ID={'type':'string','minLength':32,'maxLength':32}
FIXTURE={'type':'string','enum':['normal','missing','corrupt','incompatible','bad_csw','bad_fat','sample']}
BOOT_FIXTURE={'type':'string','enum':FIXTURE['enum']+['stale_d213','reset_participant']}
FIELDS={
 'console.inspect':({},[]),
 'console.open':({'fixture':BOOT_FIXTURE},[]),
 'console.input':({'id':ID,'port':{'type':'integer','minimum':0,'maximum':1},'hat':{'type':'integer','minimum':0,'maximum':8},'buttons':{'type':'integer','minimum':0,'maximum':511},'ticks':{'type':'integer','minimum':1,'maximum':60}},['id']),
 'console.media':({'id':ID,'fixture':FIXTURE},['id']),
 'console.state':({'id':ID},['id']),
 'console.close':({'id':ID},['id']),
 'console.plan':({'path':{'type':'string','maxLength':300},'profile':{'type':'string','enum':['qemu-virt-rv64-existing','r10-f133-board','egon-format-tool-limit']}},['path','profile'])}
SCOPES={name:'read' if name in ('console.inspect','console.state','console.plan') else 'execute' for name in FIELDS}
_INITIALIZE=threading.Lock()

def open_session(kernel,principal,fixture='normal',native=None):
    with _INITIALIZE:
        if not hasattr(kernel,'console_sessions'):kernel.console_sessions={};kernel.console_lock=threading.RLock()
    with kernel.console_lock:
        sessions=kernel.console_sessions
        if sum(not s.closed for s in sessions.values())>=2:raise ValueError('VIRTUAL_CONSOLE_SESSION_LIMIT')
        session=ConsoleSession(kernel.root,principal.identity,fixture,native=native);sessions[session.id]=session
        if len(sessions)>16:
            for ident in list(sessions):
                if sessions[ident].closed:del sessions[ident];break
        return session.snapshot()


def inspect(root):
    profile=io.load(root,'project/console/profile.json');latest=None
    path=io.project_path(root,console_build.OUT+'/build.json',False)
    if path.is_file():
        r=io.load(root,console_build.OUT+'/build.json');latest={'status':r.get('status'),'revision':r.get('revision'),'current':r.get('input_hashes')==console_build.sources(root)}
    campaign=io.project_path(root,console_build.OUT+'/lifecycle.json',False)
    latest_lifecycle=io.load(root,console_build.OUT+'/lifecycle.json') if campaign.is_file() else None
    if latest_lifecycle:
        latest_lifecycle={**latest_lifecycle,'source_current':latest_lifecycle.get('input_hashes')==console_build.sources(root)}
    return {'schema':'arc.virtual-console-inspect/1','profile':profile,'build':latest,'latest_lifecycle':latest_lifecycle,'class':'HOST_SIM','target_status':'BLOCKED','physical_hardware':False}


def dispatch(kernel,operation,args,principal):
    if operation in ('console.open','console.input','console.media'):
        from .service_lifecycle import require_admission
        require_admission(kernel)
    if operation=='console.inspect':return inspect(kernel.root)
    if operation=='console.plan':
        path=io.project_path(kernel.root,args['path'])
        if path.stat().st_size>16*1024*1024:raise ValueError('OFFLINE_IMAGE_SIZE')
        return {**target_plan.plan(path.read_bytes(),args['profile']),'source_path':args['path']}
    with _INITIALIZE:
        if not hasattr(kernel,'console_sessions'):kernel.console_sessions={};kernel.console_lock=threading.RLock()
    if SCOPES[operation]!='read' and 'console.lifecycle' not in principal.tools:raise ValueError('Console execution is outside the delegated tool scope')
    with kernel.console_lock:
        if operation=='console.open':
            return open_session(kernel,principal,args.get('fixture','normal'))
        ident=args['id']
        if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('INVALID_CONSOLE_ID')
        session=kernel.console_sessions.get(ident)
        if session is None:
            if operation=='console.state':
                path=io.project_path(kernel.root,'.ledger/console/'+ident+'/state.json',private=True)
                if path.stat().st_size>4*1024*1024:raise ValueError('CONSOLE_RECORD_LIMIT')
                return {**io.strict_json(path.read_bytes()),'state':'RECORDED_ONLY','live_process':False}
            raise ValueError('LIVE_CONSOLE_NOT_AVAILABLE: reboot the functional session; recorded traces remain readable')
        if SCOPES[operation]!='read' and session.owner!=principal.identity:raise ValueError('Console belongs to another execution principal')
        if operation=='console.input':return session.control(args.get('port',0),args.get('hat',8),args.get('buttons',0),args.get('ticks',1))
        if operation=='console.media':return session.media(args.get('fixture'))
        if operation=='console.close':session.close();return session.snapshot()
        return session.snapshot()
