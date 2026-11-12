"""Reentrant process/file lock for the existing personal configuration file."""
from contextlib import contextmanager
from pathlib import Path
import os
import threading

_guard=threading.Lock()
_locks={}
_held=threading.local()


@contextmanager
def locked(path):
    name=str(Path(path).resolve())
    with _guard:mutex=_locks.setdefault(name,threading.RLock())
    with mutex:
        active=getattr(_held,'paths',set())
        if name in active:
            yield
            return
        target=Path(name+'.lock');target.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(target,os.O_CREAT|os.O_RDWR,0o600)
        with os.fdopen(descriptor,'r+b') as stream:
            if os.name=='nt':
                import msvcrt
                if not target.stat().st_size:stream.write(b'\0');stream.flush()
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            _held.paths=active|{name}
            try:yield
            finally:
                _held.paths=active
                if os.name=='nt':stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
