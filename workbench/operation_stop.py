"""Qt-free stop diagnostics and termination of explicitly owned process trees.

Stop advice is a documented rule score, never a calibrated probability. Quiet
output, a paused debugger and an idle console are not evidence of a hang.
"""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

TERMINAL=frozenset(('Completed','Failed','Cancelled'))
UNKNOWN='<identity unavailable>'
WAITING=frozenset(('Paused','Interrupted','Waiting for Approval','Waiting for Agent',
                   'Waiting for Provider','Waiting for Execution Approval'))
_LINUX_PATHS={}


def _linux_row(path):
    fields=(path/'stat').read_text().rsplit(')',1)[1].split()
    status=(path/'status').read_text().splitlines()
    ids=next((r.split()[1:] for r in status if r.startswith('NSpid:')),[])
    return fields,[int(v) for v in ids]


def _linux_depth():
    _,ids=_linux_row(Path('/proc/self'))
    return max(0,len(ids)-1)


def _linux_path(pid):
    """Handle a procfs mounted by an ancestor PID namespace as well as normal /proc."""
    depth=_linux_depth();namespace=os.readlink('/proc/self/ns/pid')
    cached=_LINUX_PATHS.get(pid)
    if cached is not None:
        try:
            fields,ids=_linux_row(cached)
            if len(ids)>depth and ids[depth]==pid:return cached,fields
        except (OSError,IndexError,ValueError):pass
        _LINUX_PATHS.pop(pid,None)
    direct=Path('/proc')/str(pid)
    candidates=[direct]
    candidates.extend(p for p in Path('/proc').iterdir() if p.name.isdigit() and p!=direct)
    for path in candidates:
        try:
            if os.readlink(path/'ns/pid')!=namespace:continue
            fields,ids=_linux_row(path)
            if len(ids)>depth and ids[depth]==pid:
                _LINUX_PATHS[pid]=path;return path,fields
        except (FileNotFoundError,ProcessLookupError,PermissionError,IndexError,ValueError):continue
    return None,None


def process_identity(pid):
    """A start token, or None when absent/exited. Never guess from a process name."""
    if not isinstance(pid,int) or pid<=0:return None
    if sys.platform.startswith('linux'):
        try:
            _,fields=_linux_path(pid)
            if fields is None:return None
            return None if fields[0]=='Z' else fields[19]
        except PermissionError:return UNKNOWN
        except (OSError,IndexError):return None
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
        api.OpenProcess.restype=wintypes.HANDLE
        api.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
        api.GetProcessTimes.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME))
        api.CloseHandle.argtypes=(wintypes.HANDLE,)
        handle=api.OpenProcess(0x1000,False,pid)
        if not handle:return None if ctypes.get_last_error()==87 else UNKNOWN
        try:
            code=wintypes.DWORD()
            if not api.GetExitCodeProcess(handle,ctypes.byref(code)):return UNKNOWN
            if code.value!=259:return None
            created,exited,kernel,user=(wintypes.FILETIME() for _ in range(4))
            if not api.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),ctypes.byref(kernel),ctypes.byref(user)):return UNKNOWN
            return str((created.dwHighDateTime<<32)|created.dwLowDateTime)
        finally:api.CloseHandle(handle)
    try:
        r=subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True,timeout=2)
        return r.stdout.strip() or None
    except (OSError,subprocess.SubprocessError):return None


@dataclass(frozen=True)
class ProcessRef:
    pid:int
    token:str
    depth:int=0


def owned_tree(pids,descendants_only=False):
    """Snapshot only descendants of supplied, application-owned live roots."""
    roots={int(pid) for pid in pids if pid and int(pid)>0 and (int(pid)!=os.getpid() or descendants_only)}
    parents={}
    if sys.platform.startswith('linux'):
        rows={};outer_roots={};namespace_depth=_linux_depth()
        for pid in roots:
            path,_=_linux_path(pid)
            if path is not None:outer_roots[int(path.resolve().name)]=pid
        for path in Path('/proc').iterdir():
            if not path.name.isdigit():continue
            try:
                fields,ids=_linux_row(path)
                rows[int(path.name)]=(path,fields,ids)
                parents[int(path.name)]=int(fields[1])
            except (OSError,ValueError,IndexError):pass
        depths={pid:0 for pid in outer_roots}
        for _ in range(64):
            added={pid:depths[parent]+1 for pid,parent in parents.items() if parent in depths and pid not in depths}
            if not added:break
            depths.update(added)
        refs=[]
        for outer_pid,depth in depths.items():
            if outer_pid not in rows:continue
            path,fields,ids=rows[outer_pid]
            if fields[0]=='Z' or len(ids)<=namespace_depth:continue
            pid=ids[namespace_depth]
            if pid==os.getpid():continue
            _LINUX_PATHS[pid]=path
            refs.append(ProcessRef(pid,fields[19],depth))
        return sorted(refs,key=lambda r:r.depth,reverse=True)
    elif os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Entry(ctypes.Structure):
            _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),('pid',wintypes.DWORD),
                      ('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),
                      ('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('exe',wintypes.WCHAR*260)]
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateToolhelp32Snapshot.argtypes=(wintypes.DWORD,wintypes.DWORD);api.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
        api.Process32FirstW.argtypes=(wintypes.HANDLE,ctypes.POINTER(Entry));api.Process32NextW.argtypes=(wintypes.HANDLE,ctypes.POINTER(Entry))
        api.CloseHandle.argtypes=(wintypes.HANDLE,)
        snapshot=api.CreateToolhelp32Snapshot(2,0)
        if snapshot==ctypes.c_void_p(-1).value:raise OSError('Unable to inspect owned process descendants')
        try:
            entry=Entry();entry.dwSize=ctypes.sizeof(entry);ok=api.Process32FirstW(snapshot,ctypes.byref(entry))
            while ok:
                parents[entry.pid]=entry.parent;ok=api.Process32NextW(snapshot,ctypes.byref(entry))
        finally:api.CloseHandle(snapshot)
    else:
        r=subprocess.run(['ps','-axo','pid=,ppid='],capture_output=True,text=True,timeout=3)
        for row in r.stdout.splitlines():
            parts=row.split()
            if len(parts)==2:parents[int(parts[0])]=int(parts[1])
    depths={pid:0 for pid in roots}
    for _ in range(64):
        added={pid:depths[parent]+1 for pid,parent in parents.items() if parent in depths and pid not in depths and pid!=os.getpid()}
        if not added:break
        depths.update(added)
    refs=[]
    for pid,depth in depths.items():
        if pid==os.getpid():continue
        token=process_identity(pid)
        if token is not None and token!=UNKNOWN:refs.append(ProcessRef(pid,token,depth))
    return sorted(refs,key=lambda r:r.depth,reverse=True)


def kill_owned(refs):
    """Revalidate every PID/start token before signalling; refuse our own PID."""
    results=[]
    for ref in refs:
        if ref.pid==os.getpid() or ref.token==UNKNOWN:continue
        if process_identity(ref.pid)!=ref.token:
            results.append({'pid':ref.pid,'state':'already_exited'});continue
        try:
            if os.name=='nt':
                r=subprocess.run(['taskkill.exe','/PID',str(ref.pid),'/T','/F'],capture_output=True,timeout=8,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode and process_identity(ref.pid)==ref.token:raise OSError('taskkill did not confirm termination')
            else:
                # Only a group led by this known child is eligible. Never signal
                # the desktop's inherited process group.
                if os.getpgid(ref.pid)==ref.pid:os.killpg(ref.pid,signal.SIGKILL)
                else:os.kill(ref.pid,signal.SIGKILL)
            results.append({'pid':ref.pid,'state':'kill_requested'})
        except ProcessLookupError:results.append({'pid':ref.pid,'state':'already_exited'})
        except (OSError,subprocess.SubprocessError) as exc:results.append({'pid':ref.pid,'state':'error','error':str(exc)})
    return results


def stop_advice(operations):
    """Max severity of observable rules, 0–100; unknown stays unknown.

    Bands: 25 approaching a recorded limit; 50 queued >60s; 85 overdue by
    >3s; 95 a running job's worker is confirmed absent. No output/CPU guesses.
    """
    active=[o for o in operations if o.get('active')]
    reasons=[];scores=[];unassessed=[]
    for o in active:
        label=o.get('label','Operation')
        if o.get('waiting'):
            reasons.append(label+': waiting; that state alone is not evidence of a hang.');continue
        if o.get('alive') is False:
            scores.append(95);reasons.append(label+': recorded running worker has exited.');continue
        elapsed=o.get('elapsed');limit=o.get('timeout')
        valid=lambda v:isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
        if o.get('queued') and valid(elapsed):
            score=50 if elapsed>60 else 0;scores.append(score)
            if score:reasons.append(label+': queued for over 60 seconds without being claimed.')
        elif valid(elapsed) and valid(limit) and limit>0:
            score=85 if elapsed>limit+3 else 25 if elapsed>=limit*.9 else 0
            scores.append(score)
            if score:reasons.append(label+(': exceeded its recorded time limit.' if score==85 else ': approaching its recorded time limit.'))
        else:unassessed.append(label)
    if not active:score=0;reasons=['No monitored operations are running.']
    elif scores:score=max(scores)
    elif all(o.get('waiting') for o in active):score=0
    else:score=None
    if active and scores and not reasons:reasons.append('No recorded deadline or worker-exit warning is currently present.')
    if unassessed:reasons.append('Insufficient health data for: '+', '.join(unassessed[:5])+'.')
    return {'schema':'arc.stop-advice/1','score':score,'active':len(active),
            'meaning':'Rule-based stop recommendation; not a statistical probability or automatic stop.',
            'coverage':'limited' if unassessed else 'recorded signals','reasons':reasons,
            'rules':{'near_deadline':25,'unclaimed_60_seconds':50,'overdue_3_seconds':85,'worker_exited':95}}


def job_operations(jobs,clock=None):
    clock=time.time() if clock is None else clock;rows=[]
    for j in jobs:
        state=j.get('state')
        if state in TERMINAL:continue
        row={'label':str(j.get('tool','Job')),'active':True,'waiting':state in WAITING,
             'queued':state=='Queued','elapsed':max(0,clock-(j.get('started') or j.get('created') or clock)),
             'timeout':j.get('timeout') if state=='Running' else None}
        pid=j.get('pid')
        if state=='Running' and isinstance(pid,int) and pid>0:
            identity=process_identity(pid)
            row['alive']=None if identity==UNKNOWN else identity is not None
        rows.append(row)
    return rows


def force_cancel_worker(kernel,job):
    """Force only a verified worker after the normal cancellation request.

    Older records without a start token remain unverified. A cancelled terminal
    state is recorded only after the owned worker is confirmed gone.
    """
    current=kernel.record('jobs',job['id'])
    pid=current.get('pid');token=current.get('worker_start')
    if not current.get('cancel') or not pid or not token or token==UNKNOWN:return False
    if process_identity(pid) not in (None,token):return False
    refs=owned_tree([pid])
    kill_owned(refs)
    end=time.monotonic()+2
    while process_identity(pid)==token and time.monotonic()<end:time.sleep(.02)
    if process_identity(pid) is not None:return False
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        current=kernel.record('jobs',job['id'])
        if current.get('cancel') and current['state'] not in TERMINAL:
            current.update(state='Cancelled',finished=time.time(),current_operation='master stop',
                           error='Owner master stop terminated the verified job worker after cancellation.')
            kernel.save('jobs',current,db)
    kernel.audit('desktop-owner','jobs.cancel','MASTER_STOP_VERIFIED_WORKER_EXIT')
    return True
