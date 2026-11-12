"""Refuse shared SQLite state on storage that cannot coordinate separate processes.

Ledger's engineering and Catalog databases use WAL from several processes at
once (coordinator, job workers, tools, CLI). WAL depends on two filesystem
guarantees: POSIX byte-range locks taken by one process are visible to and
enforced against another, and a MAP_SHARED mapping (the -shm index) is coherent
between processes. Where either is missing SQLite cannot know another process
is writing; it reports "database disk image is malformed" or loses commits.

The check runs one short child process against a private scratch file inside
the state directory itself. It reads no database and changes no setting.
"""
from __future__ import annotations
import fcntl
import json
import mmap
import os
from pathlib import Path
import subprocess
import sys
import uuid

OFFSET, LENGTH = 120, 8
SENTINEL = b'ledger-w'

CHILD = r'''
import errno,fcntl,json,mmap,os,struct,sys
path,offset,length=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
fd=os.open(path,os.O_RDWR);result={}
raw=fcntl.fcntl(fd,fcntl.F_GETLK,struct.pack('hhqqi',fcntl.F_WRLCK,0,offset,length,0))
result['lock_visible']=struct.unpack('hhqqi',raw)[0]!=fcntl.F_UNLCK
try:
    fcntl.lockf(fd,fcntl.LOCK_EX|fcntl.LOCK_NB,length,offset);result['lock_enforced']=False
except OSError as exc:result['lock_enforced']=exc.errno in (errno.EAGAIN,errno.EACCES)
view=mmap.mmap(fd,4096);result['shared_mapping']=view[0:8].hex();view.close();os.close(fd)
print(json.dumps(result))
'''


class UnsafeStorage(OSError):
    pass


def check(directory, timeout=15):
    """Return the measured cross-process properties of ``directory``."""
    directory = Path(directory)
    path = directory / ('.storage-check-' + uuid.uuid4().hex)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, b'\0' * 4096)
        view = mmap.mmap(fd, 4096)
        try:
            view[0:len(SENTINEL)] = SENTINEL
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, LENGTH, OFFSET)
            # Same interpreter and environment as the job workers that will share the databases.
            child = subprocess.run([sys.executable, '-I', '-c', CHILD, str(path), str(OFFSET), str(LENGTH)],
                                   capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        finally:
            view.close()
    finally:
        os.close(fd)
        path.unlink(missing_ok=True)
    if child.returncode:
        raise UnsafeStorage('Storage check could not run: ' + child.stderr.strip()[-200:])
    measured = json.loads(child.stdout)
    measured['shared_mapping'] = measured['shared_mapping'] == SENTINEL.hex()
    return measured


def require(directory, purpose='shared Graphite state'):
    """Fail closed unless ``directory`` supports multi-process WAL."""
    try:
        measured = check(directory)
    except UnsafeStorage:
        raise
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise UnsafeStorage('Storage check failed for ' + purpose + ': ' + str(exc)[:200]) from exc
    missing = [name for name in ('lock_visible', 'lock_enforced', 'shared_mapping') if measured.get(name) is not True]
    if missing:
        raise UnsafeStorage('UNSAFE_STORAGE: ' + str(directory) + ' does not share file locks or memory maps '
                            'between processes (' + ', '.join(missing) + '). ' + purpose.capitalize() +
                            ' would be corrupted here. Move the project or profile to a local disk '
                            '(for example ext4 in your home folder); no database was opened.')
    return measured
