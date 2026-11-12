"""Fixed Linux bubblewrap profile. Unavailable isolation never falls back."""
from __future__ import annotations
from functools import lru_cache
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROFILE='debian-workshop-v1'

def base_argv():
    bwrap=shutil.which('bwrap')
    if sys.platform!='linux' or not bwrap:raise ValueError('Linux bubblewrap is required for automatic isolated native execution')
    argv=[bwrap,'--unshare-all','--new-session','--die-with-parent','--cap-drop','ALL',
          '--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home/ledger',
          '--setenv','HOME','/home/ledger','--setenv','PATH',os.environ.get('PATH','/usr/bin:/bin'),
          '--setenv','LANG','C.UTF-8','--setenv','QT_QPA_PLATFORM','offscreen',
          '--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','PYTHONUNBUFFERED','1']
    for path in ('/usr','/bin','/sbin','/lib','/lib64'):
        if Path(path).exists():argv+=['--ro-bind',path,path]
    for path in ('/etc/ld.so.cache','/etc/fonts','/etc/alternatives'):
        if Path(path).exists():argv+=['--ro-bind',path,path]
    return argv

@lru_cache(maxsize=4)
def status():
    try:
        argv=base_argv()+['/usr/bin/true']
        r=subprocess.run(argv,capture_output=True,text=True,timeout=8)
        return {'profile':PROFILE,'available':r.returncode==0,'reason':r.stderr.strip()[:1000],
                'mechanism':'bubblewrap namespaces and read-only source mount','physical_hardware':False,
                'network':'isolated namespace','source':'read-only; build and private execution state writable'}
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'profile':PROFILE,'available':False,'reason':str(exc)[:1000],'physical_hardware':False}

def command(argv,source,env):
    info=status()
    if not info['available']:raise ValueError('Automatic isolation unavailable: '+info['reason'])
    source=Path(source).resolve()
    writable=[source/'build',source/'.ledger']
    for p in writable:p.mkdir(exist_ok=True)
    result=base_argv()
    # Include only interpreter/tool dependency locations, never the account's
    # home or the accepted project's .ledger state. The execution source is a
    # clean hash-bound copy made by the Kernel before this function is called.
    runtime={Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()}
    for item in sys.path:
        if not item:continue
        p=Path(item).resolve()
        if p.exists() and not p.is_relative_to(source) and ('site-packages' in p.parts or 'dist-packages' in p.parts):runtime.add(p)
    for item in os.environ.get('LD_LIBRARY_PATH','').split(':'):
        if item and Path(item).is_dir():runtime.add(Path(item).resolve())
    for p in sorted(runtime):
        if str(p) not in ('/','/home','/root') and not p.is_relative_to('/usr'):
            result+=['--ro-bind',str(p),str(p)]
    result+=['--ro-bind',str(source),str(source),'--chdir',str(source)]
    for p in writable:result+=['--bind',str(p),str(p)]
    for key in ('PYTHONPATH','QT_QPA_PLATFORM','PYTHONUNBUFFERED','PYTHONDONTWRITEBYTECODE','LD_LIBRARY_PATH'):
        if key in env:result+=['--setenv',key,env[key]]
    result+=argv
    return result,info
