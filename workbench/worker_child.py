"""Standalone trusted gate, copied into a read-only isolated worker bundle.

No task input is read before the broker confirms the actual cgroup controls.
Only this small gate runs before that confirmation.
"""
import ctypes
import json
import os
import resource
import sys


def main():
    token, raw, *command = sys.argv[1:]
    limits = json.loads(raw)
    for kind, value in ((resource.RLIMIT_CORE,0),(resource.RLIMIT_CPU,limits['seconds']),
        (resource.RLIMIT_FSIZE,16*1024*1024),(resource.RLIMIT_NOFILE,128)):
        resource.setrlimit(kind,(value,value))
    if ctypes.CDLL(None).prctl(38,1,0,0,0)!=0: raise SystemExit('no_new_privs unavailable')
    os.umask(0o077)
    print('LEDGER_WORKER_READY',flush=True)
    if sys.stdin.buffer.readline(100).strip()!=token.encode(): raise SystemExit('No broker admission')
    sys.stdin.close()
    os.execve(command[0],command,{'PATH':'/usr/bin:/bin','HOME':'/scratch','TMPDIR':'/scratch','LANG':'C.UTF-8',
        'PYTHONDONTWRITEBYTECODE':'1','LD_LIBRARY_PATH':'/runtime'})


if __name__=='__main__':main()
