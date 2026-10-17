"""R07 host game launcher. Runs only local SDK-built executable, never code from cartridge.

A .arc1cart remains a manifest+asset archive; the trusted host executable is bound
by manifest bytes, SDK build stamp, binary SHA256 and source input digest.
No physical USB, target boot, or board launch occurs.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import zipfile
from .cartridge import inspect_cartridge, CartridgeError

ROOT = Path(__file__).resolve().parents[1]
GAME_NAME = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
MAX_FRAMES = 36000

class LauncherError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

def _sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def games_on_shelf(root=ROOT):
    shelf=Path(root)/'cartridges'
    found=[]
    if not shelf.is_dir():return found
    for path in sorted(shelf.glob('*.arc1cart'))[:200]:
        if path.is_symlink():continue
        try:
            record=inspect_cartridge(path)
            found.append({'path':str(path.relative_to(root)).replace('\\','/'), 'name':record['name'],
                          'version':record['game_version'], 'valid':True, 'evidence':'HOST_ARCHIVE_VERIFICATION_ONLY',
                          'executable_included':False})
        except (CartridgeError,OSError) as e:
            found.append({'path':str(path.relative_to(root)).replace('\\','/'), 'name':path.stem,
                          'valid':False,'error':'CARTRIDGE_INVALID: '+str(e),'evidence':'STATIC_CHECK'})
    return found

def resolve_cart(value,root=ROOT):
    root=Path(root).resolve();shelf=(root/'cartridges').resolve()
    if not isinstance(value,str) or '\x00' in value or len(value)>260:raise LauncherError('INVALID_PATH','Invalid cartridge path')
    given=Path(value)
    if given.is_absolute() or any(p in ('..','.') for p in given.parts):
        raise LauncherError('INVALID_PATH','Cartridge must be a normalized relative shelf path')
    target=(root/given).resolve()
    if not target.is_relative_to(shelf) or target.parent!=shelf or target.suffix!='.arc1cart' or target.is_symlink():
        raise LauncherError('INVALID_PATH','Cartridge must be a regular .arc1cart file in cartridges/')
    return target

def prepare(value='cartridges/hello_arc1.arc1cart',root=ROOT):
    """Validate stored assets, local source compatibility, and a fresh trusted host binary."""
    root=Path(root).resolve();cart=resolve_cart(value,root)
    try:archive=inspect_cartridge(cart)
    except (CartridgeError,OSError) as e:raise LauncherError('CARTRIDGE_INVALID',str(e)) from e
    name=archive['name']
    if not GAME_NAME.fullmatch(name):raise LauncherError('CARTRIDGE_INVALID','Unsafe game name')
    project=root/'examples'/name
    if not project.is_dir() or project.is_symlink() or not project.resolve().is_relative_to(root):
        raise LauncherError('NO_HOST_PROJECT','No trusted host project matches cartridge')
    source_manifest=project/'arc1.game.json'
    if not source_manifest.is_file():raise LauncherError('NO_HOST_PROJECT','Host project manifest missing')
    try:
        with zipfile.ZipFile(cart) as z:archived_manifest=z.read('arc1.game.json')
    except (OSError,ValueError,zipfile.BadZipFile) as e:raise LauncherError('CARTRIDGE_INVALID','Cannot read cartridge manifest') from e
    if archived_manifest!=source_manifest.read_bytes():
        raise LauncherError('CARTRIDGE_SOURCE_MISMATCH','Cartridge does not match trusted local game source; repackage')
    sdk_cli=root/'sdk'/'cli'
    if str(sdk_cli) not in sys.path:sys.path.insert(0,str(sdk_cli))
    from arc1cli.project import Project
    p=Project(project)
    binary=p.binary(name)
    stamp=project/'build'/'host'/'build-stamp.json'
    try:record=json.loads(stamp.read_text(encoding='utf-8'))
    except (OSError,ValueError):record={}
    if not binary.is_file() or binary.is_symlink() or not binary.resolve().is_relative_to(project.resolve()) or stamp.is_symlink() or record.get('input_digest')!=p.build_digest() or record.get('binary_sha256')!=_sha(binary):
        raise LauncherError('HOST_BUILD_STALE','Host game is missing or stale; run Build game then retry')
    return {'name':name,'game_version':archive['game_version'],'cartridge':str(cart.relative_to(root)).replace('\\','/'),
            'cartridge_sha256':archive['cartridge_sha256'],'asset_bytes':archive['asset_bytes'],
            'executable':str(binary),'executable_sha256':_sha(binary),'input_digest':p.build_digest(),
            'evidence':'HOST_TEST','executable_in_cartridge':False,'board_observed':False}

class HostLauncher:
    """Shared command engine for GUI and JSON-lines agent; async and stoppable."""
    def __init__(self,root=ROOT):
        self.root=Path(root).resolve()
        self._lock=threading.RLock()
        self._proc=None
        self._state='IDLE';self._result=None;self._start_time=None;self._cancel=False
        self._name=None;self._frames=0;self._artifact_dir=None
    def status(self):
        with self._lock:
            result={'state':self._state,'name':self._name,'frames_requested':self._frames,
                    'board_observed':False,'evidence':'HOST_TEST' if self._state in ('COMPLETED','FAILED','STOPPED') else 'HOST_SIM',
                    'physical_usb_tested':False}
            if self._result is not None:result['result']=dict(self._result)
            return result
    def start(self,cart='cartridges/hello_arc1.arc1cart',*,frames=120):
        if type(frames) is not int or not 1<=frames<=MAX_FRAMES:
            raise LauncherError('INVALID_FRAMES','frames must be an integer from 1 to 36000')
        with self._lock:
            if self._state in ('STARTING','RUNNING'):
                raise LauncherError('ALREADY_RUNNING','Host simulator already running')
            plan=prepare(cart,self.root)  # no cartridge-supplied executable is ever invoked
            output=self.root/'examples'/plan['name']/'build'/'launcher-run'
            project=(self.root/'examples'/plan['name']).resolve()
            if output.is_symlink() or not output.resolve().is_relative_to(project):
                raise LauncherError('OUTPUT_UNSAFE','Simulator output directory escapes trusted project')
            output.mkdir(parents=True,exist_ok=True)
            for f in output.glob('frame_*.ppm'):f.unlink()
            trace=output/'trace.txt'
            cmd=[plan['executable'],'--frames',str(frames),'--trace',str(trace),'--dump-dir',str(output),
                 '--dump',','.join(str(f) for f in sorted({0,min(frames-1,frames//3),min(frames-1,2*frames//3),frames-1}))]
            self._state='STARTING';self._result=None;self._cancel=False;self._name=plan['name'];self._frames=frames
            self._start_time=time.monotonic();self._artifact_dir=output
            try:
                self._proc=subprocess.Popen(cmd,cwd=str((self.root/'examples'/plan['name'])),
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',
                    stdin=subprocess.DEVNULL,env=os.environ.copy())
            except OSError as e:
                self._state='FAILED';self._proc=None
                self._result={'code':'EXEC_START_FAILED','message':str(e)}
                raise LauncherError('EXEC_START_FAILED',str(e)) from e
            self._state='RUNNING';proc=self._proc
            threading.Thread(target=self._watch,args=(proc,plan,trace,output),daemon=True).start()
            return self.status()
    def _watch(self,proc,plan,trace,output):
        try:
            try:stdout,stderr=proc.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill();stdout,stderr=proc.communicate();timed_out=True
            else:timed_out=False
            with self._lock:
                stopped=self._cancel
                if stopped:
                    state='STOPPED';code='USER_STOPPED'
                elif timed_out:
                    state='FAILED';code='SIM_TIMEOUT'
                elif proc.returncode!=0:
                    state='FAILED';code='HOST_RUNTIME_FAILED'
                elif not trace.is_file() or not trace.stat().st_size:
                    state='FAILED';code='TRACE_MISSING'
                else:
                    state='COMPLETED';code='HOST_RUN_COMPLETED'
                frames=sorted(output.glob('frame_*.ppm')) if state=='COMPLETED' else []
                self._state=state
                self._result={'code':code,'exit_code':proc.returncode,'output_tail':(stdout+'\n'+stderr)[-1500:],
                    'trace':str(trace.relative_to(self.root)).replace('\\','/') if trace.exists() else None,
                    'trace_sha256':_sha(trace) if state=='COMPLETED' else None,
                    'preview_frames':[str(p.relative_to(self.root)).replace('\\','/') for p in frames],
                    'cartridge_sha256':plan['cartridge_sha256'],'host_binary_sha256':plan['executable_sha256'],
                    'elapsed_wall_s':round(time.monotonic()-self._start_time,4),'evidence':'HOST_TEST',
                    'is_realtime_gameplay':False,'physical_usb_tested':False,'board_observed':False}
                self._proc=None
        except (OSError,ValueError) as e:
            with self._lock:
                self._state='FAILED';self._result={'code':'HOST_IO_FAILED','message':str(e),'evidence':'HOST_TEST'};self._proc=None
    def stop(self):
        with self._lock:
            if self._state not in ('STARTING','RUNNING') or self._proc is None:
                return {'stopped':False,'reason':'No active host simulation',**self.status()}
            self._cancel=True
            proc=self._proc
        try:proc.terminate()
        except OSError:pass
        return {'stopped':True,'state':'STOPPING','evidence':'HOST_SIM','board_observed':False}
