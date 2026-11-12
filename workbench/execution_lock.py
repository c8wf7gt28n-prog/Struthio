"""Advisory per-user/project lock for GUI and structured-agent command services."""
from pathlib import Path
import hashlib,os
from .session import config_dir

class ExecutionLock:
    def __init__(self,root):
        base=config_dir()/'execution'
        base.mkdir(parents=True,exist_ok=True)
        self.path=base/(hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()+'.lock')
        self.file=None
    def acquire(self):
        if self.file is not None:return True
        f=self.path.open('a+b')
        try:
            if self.path.stat().st_size==0:f.write(b'0');f.flush()
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.file=f;return True
        except OSError:
            f.close();return False
    def release(self):
        if self.file is None:return
        f,self.file=self.file,None
        try:
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        finally:f.close()
