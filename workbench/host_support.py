"""What this computer supports (File-Management Plan, section 16): a read-only look, nothing configured or changed.

Each line says what was looked at, what was found, and why it matters. The words follow the plan: "verified here" means
Ledger tried it just now and it worked; "available" means the computer reports it; "not available" and "not known" say
so. This is the first step towards confining programs Slate may one day run; it confines nothing by itself.
"""
from __future__ import annotations
import ctypes
import os
import platform
import shutil
from pathlib import Path

FIELDS = {'system.supports': ({}, [])}
SCOPES = {'system.supports': 'read'}
LANDLOCK_SYSCALL = {'x86_64': 444, 'aarch64': 444, 'riscv64': 444}


def read(path):
    try:return Path(path).read_text(errors='replace').strip()
    except OSError:return None


def landlock():
    number = LANDLOCK_SYSCALL.get(platform.machine())
    if number is None:return 'not known', 'no Landlock call number for %s' % platform.machine()
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(number, None, ctypes.c_size_t(0), ctypes.c_uint32(1))  # LANDLOCK_CREATE_RULESET_VERSION
    if abi > 0:return 'available', 'Landlock ABI version %d' % abi
    err = ctypes.get_errno()
    return 'not available', {38: 'the kernel was built without Landlock', 95: 'Landlock is built in but turned off (boot option lsm=)'}.get(err, 'error %d' % err)


def mount_of(path):
    best, kind = '', None
    for line in (read('/proc/mounts') or '').splitlines():
        parts = line.split()
        if len(parts) >= 3 and str(path).startswith(parts[1]) and len(parts[1]) > len(best):best, kind = parts[1], parts[2]
    return best, kind


def probe(kernel=None):
    rows = []
    def add(what, state, found, why):rows.append({'what': what, 'state': state, 'found': found, 'why': why})
    add('Linux kernel', 'available', platform.release(), 'Every check below depends on what this kernel offers.')
    try:
        from .workshop_sandbox import status
        s = status()  # runs /usr/bin/true inside Ledger's fixed profile
        add('bubblewrap (bwrap)', 'verified here' if s.get('available') else ('installed, but it did not start here' if shutil.which('bwrap') else 'not available'),
            ('a program ran inside Graphite\'s profile just now' if s.get('available') else (s.get('reason') or 'bwrap is not installed'))[:160],
            'Builds a private view of the computer for a program: only what it is given.')
    except Exception as exc:
        add('bubblewrap (bwrap)', 'available' if shutil.which('bwrap') else 'not available', str(exc)[:120], 'Builds a private view of the computer for a program.')
    try:state, found = landlock()
    except (OSError, AttributeError) as exc:state, found = 'not known', str(exc)[:120]
    add('Landlock', state, found, 'Lets a program limit which files it can touch, a second layer under bubblewrap.')
    try:  # the layer Ledger actually uses: tried for real, in a throwaway folder
        import tempfile
        from . import confine
        with tempfile.TemporaryDirectory(prefix='ledger-confine-') as scratch:
            tried = confine.run(['/bin/sh', '-c', 'cat /etc/hostname >/dev/null 2>&1; echo ok'], scratch, 10)
        info = confine.status()
        add('Legacy confined launch', 'launch tested' if tried['exit'] == 0 and tried['stdout'].strip() == 'ok' else 'not available',
            '%s · network: %s' % (info['words'], info['network']),
            'A launch probe only; it does not test forbidden access or aggregate resource containment. Continuing work uses separately qualified profiles.')
    except Exception as exc:
        add('Confined runs', 'not available', str(exc)[:160], 'How Graphite runs programs and reads untrusted files; without it they are refused.')
    status_text = read('/proc/self/status') or ''
    seccomp = next((l.split(':', 1)[1].strip() for l in status_text.splitlines() if l.startswith('Seccomp:')), None)
    add('seccomp', 'available' if seccomp is not None else 'not known', 'filter mode %s in this process' % seccomp if seccomp is not None else 'not reported',
        'Narrows which kernel calls a program may make.')
    clone = read('/proc/sys/kernel/unprivileged_userns_clone');most = read('/proc/sys/user/max_user_namespaces')
    usable = (clone in (None, '1')) and most not in (None, '0')
    add('User namespaces', 'available' if usable else 'not available', 'max %s%s' % (most, '' if clone is None else ', unprivileged %s' % ('on' if clone == '1' else 'off')),
        'Needed by bubblewrap without root.')
    controllers = read('/sys/fs/cgroup/cgroup.controllers')
    own = (read('/proc/self/cgroup') or '').split('::')[-1].strip()
    here = read('/sys/fs/cgroup' + own + '/cgroup.controllers') if own else None
    add('cgroups v2', 'available' if controllers is not None else 'not available',
        ('system: %s · this session: %s' % (controllers or '-', here or 'none delegated')) if controllers is not None else 'no unified hierarchy at /sys/fs/cgroup',
        'Limits memory, processes and time, and stops a program and everything it started at once.')
    try:
        from . import files_service
        where = files_service.root(kernel, create=False) if kernel is not None else Path.home()
    except Exception:where = Path.home()
    point, kind = mount_of(Path(where).resolve())
    add('Files folder filesystem', 'available' if kind else 'not known', '%s on %s' % (kind or '?', point or '?'),
        'Where updates rename and flush; network or removable filesystems are not supported for updates.')
    try:
        st = os.statvfs(where);free = st.f_bavail * st.f_frsize
        add('Free space for Files', 'available', '%.1f GB free' % (free / 1e9), 'Kept versions and snapshots need room; updates check before they write.')
    except OSError:pass
    if kernel is not None:
        from . import worker_boundary
        coverage=worker_boundary.status(kernel)
        for name,row in coverage['profiles'].items():
            add('Protected '+name.lower()+' worker','qualified on this boot' if row['qualified'] else row['tested'].lower().replace('_',' '),
                'Available: %s · configured: %s · tested: %s' % (row['available'],row['configured'],row['tested']),
                'Requires real forbidden-access, network, memory, child and termination probes; unavailable profiles refuse work.')
    return {'schema': 'arc.host-support/1', 'rows': rows, 'note': 'A look only: nothing was configured or changed. "verified here" means it was tried just now.'}


def dispatch(kernel, op, args, principal):
    if op == 'system.supports':return probe(kernel)
    raise ValueError('UNKNOWN_OPERATION')
