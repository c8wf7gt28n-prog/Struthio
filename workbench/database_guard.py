"""Serialize Kernel connection lifetimes across its own threads/processes.

Keep SQLite's WAL and transaction semantics. The sidecar lock is separate from
the database and reentrant within one thread, including multiple Kernel objects.
It never opens the SQLite file itself or replaces a database to recover an error.
"""
import contextlib
import os
from pathlib import Path
import threading

_registry_lock=threading.Lock()
_locks={}
_local=threading.local()


@contextlib.contextmanager
def connection(path):
    key=str(Path(path).resolve())
    with _registry_lock:lock=_locks.setdefault(key,threading.RLock())
    with lock:
        held=getattr(_local,'held',None)
        if held is None:held={};_local.held=held
        if key in held:
            yield;return
        fd=None
        try:
            if os.name=='posix':
                import fcntl
                fd=os.open(key+'.guard',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
                fcntl.flock(fd,fcntl.LOCK_EX)
            held[key]=fd
            yield
        finally:
            held.pop(key,None)
            if fd is not None:
                fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
