"""Fixed clangd and GDB services through the shared Engineering Kernel.

Host debugger sessions belong to this backend process and creating principal.
Only the registered ARC-OS diagnostic can be launched. No shell, debugger CLI,
arbitrary expression evaluation or device attachment is exposed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import threading
import time
import uuid
from . import locations

S={'type':'string','maxLength':1000000}
ID={'type':'string','minLength':32,'maxLength':32}
FIELDS={
 'desktop.tools':({},[]),
 'desktop.compile_commands':({},[]),
 'desktop.code':({'path':S,'text':S,'line':{'type':'integer','minimum':0},'character':{'type':'integer','minimum':0},
    'operation':{'type':'string','enum':['diagnostics','definition','references','completion','hover']}},['path','line','character','operation']),
 'desktop.debug.build':({},[]),
 'desktop.debug.open':({'run':{'type':'boolean'}},[]),
 'desktop.debug.command':({'id':ID,'command':{'type':'string','enum':['next','step','continue','locals','stack','registers','break','source_lines','close']},
    'path':S,'line':{'type':'integer','minimum':1}},['id','command']),
}
SCOPES={op:'read' if op=='desktop.tools' else 'execute' for op in FIELDS}
DEBUG_SOURCES=('software/arcos/tests/test_launcher.c','software/arcos/src/launcher.c','software/arcos/src/controller.c')
_SESSIONS={}
_LANGUAGE={}
_LOCK=threading.Lock()

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(root,path):
    root=Path(root).resolve();p=(root/path).resolve()
    if not p.is_relative_to(root) or not p.is_file():raise ValueError('Select a source file inside this project')
    return p

def env_for(root):
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LD_LIBRARY_PATH','SystemRoot','WINDIR')}
    home=Path(root)/'.ledger'/'desktop-tools';home.mkdir(parents=True,exist_ok=True)
    env.update(HOME=str(home),XDG_CACHE_HOME=str(home/'cache'),DEBUGINFOD_URLS='',QT_QPA_PLATFORM='offscreen')
    return env

def tool(name):
    p=shutil.which(name)
    if not p:raise ValueError(name+' is unavailable. Install the Debian '+('clangd' if name=='clangd' else 'gdb')+' package; Graphite still opens without it.')
    return p

def versions(root):
    result={}
    for name in ('clangd','gdb','cc','bwrap'):
        path=shutil.which(name)
        if not path:result[name]={'available':False};continue
        try:
            r=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=5,env=env_for(root))
            result[name]={'available':r.returncode==0,'path':path,'version':(r.stdout or r.stderr).splitlines()[0]}
        except (OSError,subprocess.TimeoutExpired) as e:result[name]={'available':False,'reason':str(e)}
    return {'tools':result,'profile':'ARC-OS native host diagnostic','target_soc_debugging':False,
            'debug_sessions':'backend-process lifetime; reopen after restart','physical_hardware':False}

def inputs(root):
    root=Path(root)
    names=set(DEBUG_SOURCES)
    for prefix in ('software/arcos/include','sdk/include'):
        names.update(p.relative_to(root).as_posix() for p in (root/prefix).rglob('*.h'))
    names.add('workbench/desktop_services.py')
    return {n:sha(root/n) for n in sorted(names)}

def flags(root):
    root=Path(root)
    return ['-std=c11','-g','-O0','-Wall','-Wextra',
            '-I'+str(root/'software/arcos/include'),'-I'+str(locations.program(root)/'sdk/include'),'-I'+str(root/'software/struthio')]

def compilation_database(root):
    root=Path(root).resolve();cc=shutil.which('cc') or shutil.which('gcc')
    if not cc:raise ValueError('Install a C11 compiler before creating native compilation commands')
    folder=root/'build/workshop/language';folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    names=['software/arcos/'+n for n in ('src/host.c','src/launcher.c','src/controller.c','tests/test_launcher.c','games/pulse.c','games/struthio_bridge.c')]
    names+=['software/struthio/'+n for n in ('struthio_core.c','game.c','state.c')]
    for name in names:
        p=root/name
        if not p.is_file():continue
        args=[cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',
            '-I'+str(root/'software/arcos/include'),'-I'+str(locations.program(root)/'sdk/include'),'-I'+str(root/'software/struthio')]
        if '/games/' in name or name.startswith('software/struthio/'):args+=['-fPIC']
        rows.append({'directory':str(root),'file':str(p),'arguments':[*args,'-c',str(p)]})
    for manifest in sorted((root/'examples').glob('*/native.json')):
        p=manifest.parent/'game.c'
        if manifest.is_symlink() or p.is_symlink() or not p.is_file():continue
        rows.append({'directory':str(manifest.parent),'file':str(p),'arguments':[cc,'-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fPIC',
            '-I'+str(root/'software/arcos/include'),'-I'+str(locations.program(root)/'sdk/include'),'-c',str(p)]})
    (folder/'compile_commands.json').write_text(json.dumps(rows,indent=2)+'\n')
    report={'schema':'arc-ledger.compilation-database/1','profile':'native-host ARC-OS and STRUTHIO C11',
            'target_hardware':False,'path':'build/workshop/language/compile_commands.json',
            'entries':len(rows),'sha256':sha(folder/'compile_commands.json'),'input_hashes':{
                **inputs(root),**{Path(row['file']).relative_to(root).as_posix():sha(row['file']) for row in rows}},
            'context':'Host flags from arcos_tools/native_sdk; indexing uses -c. Target firmware has no compiler context.'}
    (folder/'profile.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

class LanguageClient:
    def __init__(self,root):
        root=Path(root).resolve();self.root=root;compilation_database(root)
        self.queue=queue.Queue();self.id=0;self.notifications=[]
        log=root/'.ledger/desktop-tools/clangd.log';log.parent.mkdir(parents=True,exist_ok=True)
        self.log=log.open('wb')
        self.proc=subprocess.Popen([tool('clangd'),'--background-index=false','--clang-tidy=false',
            '--enable-config=false','--query-driver=','--header-insertion=never','--log=error','-j=1',
            '--compile-commands-dir='+str(root/'build/workshop/language')],
            cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,env=env_for(root),start_new_session=True)
        threading.Thread(target=self.reader,daemon=True).start()
        with _LOCK:_LANGUAGE[id(self)]=self
        from .operation_priority import background_process
        background_process(root,self.proc.pid)
        try:
            self.request('initialize',{'processId':None,'rootUri':root.as_uri(),'capabilities':{'textDocument':{'completion':{'completionItem':{'snippetSupport':False}}}}})
            self.send({'jsonrpc':'2.0','method':'initialized','params':{}})
        except Exception:
            self.close();raise
    def reader(self):
        try:
            while True:
                line=self.proc.stdout.readline()
                if not line:return
                if len(line)>4096:raise ValueError('LSP header limit')
                headers={}
                while line not in (b'\r\n',b'\n',b''):
                    key,_,value=line.decode().partition(':');headers[key.lower()]=value.strip()
                    line=self.proc.stdout.readline()
                n=int(headers.get('content-length','0'))
                if not 0<n<=1000000:raise ValueError('LSP body limit')
                body=self.proc.stdout.read(n)
                self.queue.put(json.loads(body))
        except Exception as e:self.queue.put({'transport_error':str(e)})
    def send(self,payload):
        raw=json.dumps(payload).encode();self.proc.stdin.write(('Content-Length: '+str(len(raw))+'\r\n\r\n').encode()+raw);self.proc.stdin.flush()
    def request(self,method,params):
        self.id+=1;id=self.id;self.send({'jsonrpc':'2.0','id':id,'method':method,'params':params})
        end=time.monotonic()+10
        while time.monotonic()<end:
            try:r=self.queue.get(timeout=.1)
            except queue.Empty:
                if self.proc.poll() is not None:raise ValueError('clangd exited; inspect its local log')
                continue
            if r.get('transport_error'):raise ValueError(r['transport_error'])
            if r.get('id')==id and 'method' not in r:
                if 'error' in r:raise ValueError(str(r['error']))
                return r.get('result')
            if 'method' in r and 'id' in r:self.send({'jsonrpc':'2.0','id':r['id'],'result':None})
            else:self.notifications.append(r)
        raise ValueError('clangd request timed out')
    def close(self):
        with _LOCK:_LANGUAGE.pop(id(self),None)
        if self.proc.poll() is None:os.killpg(self.proc.pid,signal.SIGKILL)
        self.proc.wait(timeout=5);self.log.close()

def language(root,a):
    root=Path(root).resolve();path=safe(root,a['path'])
    if path.relative_to(root).as_posix()!=a['path'] or path.suffix not in ('.c','.h'):raise ValueError('Select a current C source inside this project')
    profile=compilation_database(root)
    rows=json.loads((root/profile['path']).read_text());entry=next((r for r in rows if r['file']==str(path)),None)
    if entry is None:
        return {'operation':a['operation'],'path':a['path'],'result':None,'context_state':'CONTEXT_UNAVAILABLE',
            'reason':'No exact translation-unit command is registered for this file. Open a supported host C implementation; target compiler context is unavailable.',
            'profile':None,'source_sha256':sha(path),'writes_source':False,'physical_hardware':False}
    content=a.get('text',path.read_text())
    if len(content.encode())>200000:raise ValueError('Editor buffer exceeds language request limit')
    lines=content.split('\n')
    if not 0<=a['line']<len(lines) or not 0<=a['character']<=len(lines[a['line']].encode('utf-16-le'))//2:raise ValueError('Position is outside the editor buffer')
    client=LanguageClient(root)
    try:
        uri=path.as_uri()
        client.send({'jsonrpc':'2.0','method':'textDocument/didOpen','params':{'textDocument':{'uri':uri,'languageId':'c','version':1,'text':content}}})
        operation=a['operation'];method={'diagnostics':'textDocument/documentSymbol','definition':'textDocument/definition',
            'references':'textDocument/references','completion':'textDocument/completion','hover':'textDocument/hover'}[operation]
        params={'textDocument':{'uri':uri}}
        if operation!='diagnostics':params['position']={'line':a['line'],'character':a['character']}
        if operation=='references':params['context']={'includeDeclaration':True}
        result=client.request(method,params)
        if operation=='diagnostics':
            # documentSymbol waits for this buffer's parse. Drain the queued
            # published diagnostics without confusing another URI's messages.
            until=time.monotonic()+1
            while time.monotonic()<until:
                try:client.notifications.append(client.queue.get(timeout=.05))
                except queue.Empty:pass
            result=[n['params'] for n in client.notifications if n.get('method')=='textDocument/publishDiagnostics' and n['params'].get('uri')==uri]
        if operation=='completion':
            items=result.get('items',[]) if isinstance(result,dict) else result or []
            result={'items':items[:50],'truncated':len(items)>50}
        if len(json.dumps(result).encode())>200000:raise ValueError('Language response exceeds display budget; narrow the request')
        return {'operation':operation,'path':a['path'],'result':result,'buffer_sha256':hashlib.sha256(content.encode()).hexdigest(),
                'profile':'native-host C11','source_sha256':sha(path),'writes_source':False,'physical_hardware':False,
                'context_state':'CURRENT_INPUTS' if all((root/n).is_file() and sha(root/n)==h for n,h in profile['input_hashes'].items()) else 'STALE',
                'compile_command':entry,'compile_database_sha256':profile['sha256'],
                'context_inputs':profile['input_hashes'],
                'reference_scope':'Open host translation unit and included declarations; background project indexing is disabled.'}
    finally:client.close()

def build_debug(root):
    root=Path(root).resolve();cc=shutil.which('cc') or shutil.which('gcc')
    if not cc:raise ValueError('Install a C11 compiler')
    out=root/'build/workshop/debug';out.mkdir(parents=True,exist_ok=True)
    artifact=out/'arc_os_diagnostic'
    argv=[cc,*flags(root),*(str(root/n) for n in DEBUG_SOURCES),'-o',str(artifact)]
    r=subprocess.run(argv,cwd=root,env=env_for(root),capture_output=True,text=True,timeout=45)
    report={'schema':'arc-ledger.host-debug/1','argv':argv,'exit_status':r.returncode,'stdout':r.stdout[-12000:],
            'stderr':r.stderr[-12000:],'input_hashes':inputs(root),'created':time.time(),
            'artifact':'build/workshop/debug/arc_os_diagnostic','sha256':sha(artifact) if r.returncode==0 else None,
            'class':'HOST_SIM','physical_hardware':False,'os_sandbox':False}
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    if r.returncode:raise ValueError(r.stderr[-4000:] or 'Diagnostic build failed')
    return report

class DebugSession:
    def __init__(self,root,owner,run=True):
        self.root=Path(root).resolve();self.owner=owner;self.id=uuid.uuid4().hex
        report=json.loads((self.root/'build/workshop/debug/build.json').read_text())
        if report.get('artifact')!='build/workshop/debug/arc_os_diagnostic':raise ValueError('Unregistered debugger artifact rejected')
        artifact=self.root/'build/workshop/debug/arc_os_diagnostic'
        if artifact.is_symlink() or artifact.resolve().parent!=(self.root/'build/workshop/debug').resolve():raise ValueError('Debugger artifact path rejected')
        if report['input_hashes']!=inputs(self.root) or sha(artifact)!=report['sha256']:raise ValueError('Rebuild the current host diagnostic before debugging')
        self.inputs=report['input_hashes'];self.artifact_sha=report['sha256'];self.queue=queue.Queue();self.lock=threading.Lock()
        self.count=0;self.records=[];self.last=time.monotonic();self.state='SYMBOLS_LOADED'
        self.executed=False
        log=self.root/'.ledger/desktop-tools/gdb.log';log.parent.mkdir(parents=True,exist_ok=True)
        self.log=log.open('wb')
        self.proc=subprocess.Popen([tool('gdb'),'-nx','-nh','--interpreter=mi2','-iex','set auto-load off',
            '-iex','set debuginfod enabled off','--quiet',str(artifact)],cwd=self.root,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,env=env_for(self.root),start_new_session=True)
        from .operation_priority import background_process
        background_process(self.root,self.proc.pid)
        threading.Thread(target=self.reader,daemon=True).start()
        try:
            self.command('-gdb-set confirm off');self.command('-gdb-set pagination off')
            self.command('-gdb-set startup-with-shell off')
            self.command('-break-insert main')
            if run:
                self.command('-exec-run',True);self.executed=True
        except Exception:
            self.close();raise
    def reader(self):
        try:
            for raw in iter(self.proc.stdout.readline,b''):
                if len(raw)>200000:break
                self.queue.put(raw.decode(errors='replace').rstrip())
        finally:self.queue.put('__CLOSED__')
    def command(self,text,wait=False):
        with self.lock:
            self.count+=1;token=str(self.count);self.last=time.monotonic()
            self.proc.stdin.write((token+text+'\n').encode());self.proc.stdin.flush()
            end=time.monotonic()+10;rows=[];done=False;stopped=False
            while time.monotonic()<end:
                try:line=self.queue.get(timeout=.1)
                except queue.Empty:continue
                if line=='__CLOSED__':raise ValueError('Debugger exited; reopen the host diagnostic')
                rows.append(line)
                if line.startswith(token+'^error'):raise ValueError(line[:3000])
                if line.startswith(token+'^'):done=True
                if line.startswith('*stopped'):
                    stopped=True;self.state='EXITED' if 'exited' in line else 'STOPPED'
                if done and (not wait or stopped):
                    self.records=(self.records+rows)[-250:]
                    return rows
            self.close();raise ValueError('Debugger command timed out; its process group was stopped')
    def close(self):
        if self.proc.poll() is None:
            try:self.proc.stdin.write(b'9999-gdb-exit\n');self.proc.stdin.flush();self.proc.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):os.killpg(self.proc.pid,signal.SIGKILL);self.proc.wait(timeout=3)
        self.log.close();self.state='CLOSED'
    def snapshot(self,rows=None):
        result={'id':self.id,'state':self.state,'artifact_sha256':self.artifact_sha,
                'records':self.records if rows is None else rows,'class':'HOST_SIM' if self.executed else 'STATIC_CHECK','physical_hardware':False,
                'backend':'GDB/MI native ARC-OS diagnostic','os_sandbox':False}
        p=self.root/'.ledger/desktop-tools'/('debug-'+self.id+'.json');p.write_text(json.dumps(result,indent=2)+'\n')
        return result

def close_all(root):
    root=str(Path(root).resolve())
    with _LOCK:
        sessions=[s for key,s in list(_SESSIONS.items()) if key[0]==root]
        for key in list(_SESSIONS):
            if key[0]==root:del _SESSIONS[key]
        languages=[s for s in list(_LANGUAGE.values()) if str(s.root)==root]
    for s in sessions+languages:s.close()

def active_processes(root):
    """Snapshot owned handles without blocking the UI on a debugger command."""
    root=str(Path(root).resolve())
    try:
        sessions=[s for key,s in list(_SESSIONS.items()) if key[0]==root]
        sessions += [s for s in list(_LANGUAGE.values()) if str(s.root)==root]
        return [s.proc for s in sessions if s.proc.poll() is None]
    except RuntimeError:return []

def debug(root,a,p):
    keyroot=str(Path(root).resolve())
    if 'id' not in a:
        with _LOCK:
            for key,s in list(_SESSIONS.items()):
                if time.monotonic()-s.last>120:s.close();del _SESSIONS[key]
            if len(_SESSIONS)>=4:raise ValueError('Close an existing debugger session first')
            s=DebugSession(root,p.identity,a.get('run',True));_SESSIONS[(keyroot,s.id)]=s
        return s.snapshot()
    key=(keyroot,a['id']);s=_SESSIONS.get(key)
    if not s:raise ValueError('Debugger session is not in this backend; reopen it after a restart')
    if s.owner!=p.identity:raise ValueError('Debugger session belongs to another principal')
    if inputs(root)!=s.inputs or sha(Path(root)/'build/workshop/debug/arc_os_diagnostic')!=s.artifact_sha:
        s.close();_SESSIONS.pop(key,None);raise ValueError('Debug source or artifact changed; rebuild and reopen the diagnostic')
    command=a['command']
    if command=='close':s.close();_SESSIONS.pop(key,None);return s.snapshot([])
    if command in ('break','source_lines'):
        path=a.get('path','')
        if path not in DEBUG_SOURCES:raise ValueError('Select registered diagnostic source')
        if command=='break':
            if not 1<=a.get('line',0)<=len(safe(root,path).read_text().splitlines()):raise ValueError('Breakpoint must be in the registered diagnostic source')
            text='-break-insert '+json.dumps(str(safe(root,path))+':'+str(a['line']))
        else:text='-symbol-list-lines '+json.dumps(str(safe(root,path)))
    else:text={'next':'-exec-next','step':'-exec-step','continue':'-exec-continue','locals':'-stack-list-variables --simple-values',
        'stack':'-stack-list-frames','registers':'-data-list-register-values x'}[command]
    rows=s.command(text,command in ('next','step','continue'))
    return s.snapshot(rows)

def dispatch(k,op,a,p):
    if op in ('desktop.code','desktop.debug.open') or op=='desktop.debug.command' and a['command']!='close':
        from .service_lifecycle import require_admission
        require_admission(k)
    if op=='desktop.tools':return versions(k.root)
    if op=='desktop.compile_commands':return compilation_database(k.root)
    if op=='desktop.code':return language(k.root,a)
    if op=='desktop.debug.build':return k.submit({'tool':'workshop.debug_build','timeout':60,'goal':'Build registered ARC-OS host debug diagnostic'},p)
    return debug(k.root,a,p)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['debug-build']);parser.add_argument('--root',type=Path,required=True)
    a=parser.parse_args();print(json.dumps(build_debug(a.root)),flush=True)
