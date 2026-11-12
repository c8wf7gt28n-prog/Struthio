"""Owner-selected background CPU scheduling for Ledger-owned work, Qt-free.

The desktop stays responsive at its existing priority. Unix uses nice +10;
Windows uses BELOW_NORMAL_PRIORITY_CLASS. This does not cap memory or CPU time.
"""
import json
import os
from pathlib import Path
from .operation_stop import process_identity,UNKNOWN

MODES=('normal','background')


def windows_background_class(current):
    # Preserve a process already at idle priority instead of increasing it.
    return current if current in (0x40,0x4000) else 0x4000


def policy(root):
    path=Path(root)/'.ledger/master-stop/priority.json'
    try:
        if path.stat().st_size>4096:raise ValueError('Priority preference exceeds its bound')
        value=json.loads(path.read_text())
        if value.get('mode') not in MODES:raise ValueError('Unknown priority mode')
        return value['mode']
    except FileNotFoundError:return 'normal'


def select(root,mode):
    if mode not in MODES:raise ValueError('Unknown priority mode')
    from .record_io import write_json
    write_json(Path(root)/'.ledger/master-stop/priority.json',{'schema':'arc.work-priority/1','mode':mode})
    return mode


def background_process(root,pid,token=None,allow_self=False):
    try:mode=policy(root)
    except (OSError,ValueError) as exc:return {'pid':pid,'state':'denied','reason':'Priority preference unavailable: '+str(exc)}
    if mode!='background':return {'pid':pid,'state':'unchanged'}
    if not isinstance(pid,int) or pid<=0 or pid==os.getpid() and not allow_self:
        return {'pid':pid,'state':'refused','reason':'The desktop process is excluded'}
    if token is not None and process_identity(pid)!=token:return {'pid':pid,'state':'exited_or_changed'}
    if token==UNKNOWN:return {'pid':pid,'state':'refused','reason':'Process identity could not be verified'}
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            api=ctypes.WinDLL('kernel32',use_last_error=True)
            api.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD);api.OpenProcess.restype=wintypes.HANDLE
            api.SetPriorityClass.argtypes=(wintypes.HANDLE,wintypes.DWORD);api.CloseHandle.argtypes=(wintypes.HANDLE,)
            api.GetPriorityClass.argtypes=(wintypes.HANDLE,);api.GetPriorityClass.restype=wintypes.DWORD
            handle=api.OpenProcess(0x0200|0x1000,False,pid)
            if not handle:raise OSError('Unable to open the tracked process for priority adjustment')
            try:
                current=api.GetPriorityClass(handle)
                if not current:raise OSError('Windows process priority is unavailable')
                target=windows_background_class(current)
                if target!=current and not api.SetPriorityClass(handle,target):raise OSError('Windows refused below-normal priority')
            finally:api.CloseHandle(handle)
            return {'pid':pid,'state':'background','priority':'IDLE' if target==0x40 else 'BELOW_NORMAL'}
        previous=os.getpriority(os.PRIO_PROCESS,pid)
        os.setpriority(os.PRIO_PROCESS,pid,max(previous,10))
        return {'pid':pid,'state':'background','previous':previous,'priority':os.getpriority(os.PRIO_PROCESS,pid)}
    except ProcessLookupError:return {'pid':pid,'state':'exited'}
    except OSError as exc:return {'pid':pid,'state':'denied','reason':str(exc)}


def apply_self(root):
    """Only call from a dedicated job-worker entry point, never from the GUI."""
    return background_process(root,os.getpid(),allow_self=True)


def watch_qprocess(process,root):
    def started():
        pid=int(process.processId())
        if pid:background_process(root,pid,process_identity(pid))
    process.started.connect(started)
