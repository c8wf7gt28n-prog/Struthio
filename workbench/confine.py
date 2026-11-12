"""Confinement: run a program, or read untrusted files, with no network, only its own folder writable, and limits.

Two mechanisms, best first. Neither falls back to running unconfined:

  bubblewrap   when installed: new namespaces for everything, a read-only system, only the folder bound writable
               (the existing debian-workshop profile, workshop_sandbox.base_argv).
  Landlock     built into the Linux kernel (5.13+): a rule set the process can never leave. Here: the system read-only,
               the folder writable, nothing else readable; TCP bind and connect refused (ABI 4+); signals and abstract
               sockets kept inside (ABI 6+); plus, when the kernel allows it, a private network namespace. Set with
               no_new_privs, so nothing it runs can gain privileges.

Every run also gets resource limits (processor seconds, memory, file size, open files, no core dumps), its own session (so
a timeout or Stop ends the whole group), and a minimal environment. Master Stop ends it too: it is Ledger's descendant.

  confine.status    read     what this computer offers, and which mechanism a run would use
  confine.run       approve  run a command inside a working copy's folder (Slate's "test" work); output is kept bounded
  confine.inspect   read     look at every file of a working copy from inside confinement: kinds, sizes, what a parser
                             made of it. Untrusted files (a pill's) are parsed there, not in Ledger's own process.
"""
from __future__ import annotations
import ctypes
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$'}
FIELDS = {
    'confine.status': ({}, []),
    'confine.run': ({'copy': ID, 'command': {'type': 'array', 'minItems': 1, 'maxItems': 64, 'items': {'type': 'string', 'minLength': 1, 'maxLength': 4096}},
                     'seconds': {'type': 'integer', 'minimum': 1, 'maximum': 900}}, ['copy', 'command']),
    'confine.inspect': ({'copy': ID}, ['copy']),
}
SCOPES = {'confine.status': 'read', 'confine.run': 'approve', 'confine.inspect': 'read'}
LIMITS = {'cpu_seconds': 120, 'memory_bytes': 2 * 1024 ** 3, 'file_bytes': 512 * 1024 ** 2, 'open_files': 256}
OUTPUT = 1024 * 1024                        # what is kept of each output stream
SYSTEM_READ = ('/usr', '/bin', '/sbin', '/lib', '/lib32', '/lib64', '/etc', '/opt', '/dev/null', '/dev/zero', '/dev/urandom', '/dev/random', '/proc/self')

# Landlock (include/uapi/linux/landlock.h)
SYSCALLS = {'x86_64': (444, 445, 446), 'aarch64': (444, 445, 446), 'riscv64': (444, 445, 446)}
FS_EXECUTE, FS_WRITE, FS_READ_FILE, FS_READ_DIR = 1 << 0, 1 << 1, 1 << 2, 1 << 3
FS_ALL_V1 = (1 << 13) - 1
FS_REFER, FS_TRUNCATE, FS_IOCTL_DEV = 1 << 13, 1 << 14, 1 << 15
NET_BIND, NET_CONNECT = 1 << 0, 1 << 1
SCOPE_ABSTRACT, SCOPE_SIGNAL = 1 << 0, 1 << 1
FILE_RIGHTS = FS_EXECUTE | FS_WRITE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV  # the rights that apply to a file (not a folder)


class RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64), ('handled_access_net', ctypes.c_uint64), ('scoped', ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def libc():
    return ctypes.CDLL(None, use_errno=True)


def landlock_abi():
    numbers = SYSCALLS.get(platform.machine())
    if sys.platform != 'linux' or numbers is None:return 0
    abi = libc().syscall(numbers[0], None, ctypes.c_size_t(0), ctypes.c_uint32(1))
    return abi if abi > 0 else 0


def handled_fs(abi):
    rights = FS_ALL_V1
    if abi >= 2:rights |= FS_REFER
    if abi >= 3:rights |= FS_TRUNCATE
    if abi >= 5:rights |= FS_IOCTL_DEV
    return rights


def restrict(read_paths, write_paths, abi):
    """Apply a Landlock rule set to this process (and everything it starts). Raises OSError if any step fails."""
    create, add_rule, restrict_self = SYSCALLS[platform.machine()];c = libc()
    fs = handled_fs(abi);attr = RulesetAttr(fs, (NET_BIND | NET_CONNECT) if abi >= 4 else 0, (SCOPE_ABSTRACT | SCOPE_SIGNAL) if abi >= 6 else 0)
    size = 8 if abi < 4 else (16 if abi < 6 else 24)
    fd = c.syscall(create, ctypes.byref(attr), ctypes.c_size_t(size), ctypes.c_uint32(0))
    if fd < 0:raise OSError(ctypes.get_errno(), 'landlock_create_ruleset')
    read_rights = FS_EXECUTE | FS_READ_FILE | FS_READ_DIR
    for paths, rights in ((read_paths, read_rights), (write_paths, fs)):
        for path in paths:
            try:pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            except OSError:continue  # a system folder this computer does not have
            try:
                allowed = rights & fs
                if not os.path.isdir(path):allowed &= FILE_RIGHTS
                if path.startswith('/dev/'):allowed &= ~FS_EXECUTE
                rule = PathBeneath(allowed, pfd)
                if c.syscall(add_rule, ctypes.c_int(fd), ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint32(0)) != 0:
                    raise OSError(ctypes.get_errno(), 'landlock_add_rule ' + path)
            finally:os.close(pfd)
    if c.prctl(38, 1, 0, 0, 0) != 0:raise OSError(ctypes.get_errno(), 'no_new_privs')
    if c.syscall(restrict_self, ctypes.c_int(fd), ctypes.c_uint32(0)) != 0:raise OSError(ctypes.get_errno(), 'landlock_restrict_self')
    os.close(fd)


def private_network():
    """A new user and network namespace: no interfaces but a loopback that is down. True if it worked."""
    uid, gid = os.getuid(), os.getgid()
    if libc().unshare(0x10000000 | 0x40000000) != 0:return False  # CLONE_NEWUSER | CLONE_NEWNET
    try:
        Path('/proc/self/setgroups').write_text('deny')
        Path('/proc/self/uid_map').write_text('%d %d 1' % (uid, uid));Path('/proc/self/gid_map').write_text('%d %d 1' % (gid, gid))
    except OSError:pass
    return True


def limit(spec):
    for name, value in ((resource.RLIMIT_CPU, spec['cpu_seconds']), (resource.RLIMIT_AS, spec['memory_bytes']),
                        (resource.RLIMIT_FSIZE, spec['file_bytes']), (resource.RLIMIT_NOFILE, spec['open_files']), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(name, (value, value))


def runtime_paths():
    """Where Python and its packages live (read-only), so confined Python tools and the inspector can start."""
    out = {str(Path(sys.prefix).resolve()), str(Path(sys.base_prefix).resolve()), str(Path(sys.executable).resolve().parent)}
    for item in sys.path:
        if item and ('site-packages' in item or 'dist-packages' in item or item.endswith(('lib-dynload',))) and Path(item).is_dir():out.add(str(Path(item).resolve()))
    out.add(str(Path(__file__).resolve().parents[1]))  # Ledger's own code: read-only, for the inspector
    return sorted(p for p in out if p not in ('/', '/home', '/root'))


# -- status ----------------------------------------------------------------------------------------------------------

def bubblewrap():
    try:
        from . import workshop_sandbox
        return workshop_sandbox.status().get('available', False)
    except Exception:return False


def status():
    abi = landlock_abi();bwrap = bubblewrap()
    mechanism = 'bubblewrap' if bwrap else ('landlock' if abi else None)
    net = 'a private network namespace' if bwrap else ('TCP refused by Landlock' + (', and a private network namespace where the kernel allows it' if abi >= 4 else '') if abi >= 4 else
                                                       'a private network namespace, if the kernel allows it' if abi else 'none')
    return {'available': mechanism is not None, 'mechanism': mechanism, 'landlock_abi': abi, 'bubblewrap': bwrap, 'network': net,
            'limits': dict(LIMITS), 'words': ('Runs are confined with %s.' % {'bubblewrap': 'bubblewrap', 'landlock': 'Landlock (ABI %d)' % abi}[mechanism]) if mechanism else
            'This computer offers neither bubblewrap nor Landlock: confined runs are refused, never run unconfined.'}


# -- running ---------------------------------------------------------------------------------------------------------

def command_for(argv, folder, read_only=(), network=False, spec=None):
    """The argv that runs argv confined in folder, and the mechanism used. Raises ValueError if nothing can confine it."""
    info = status();spec = {**LIMITS, **(spec or {})}
    if not info['available']:raise ValueError('CONFINE_UNAVAILABLE: ' + info['words'])
    folder = str(Path(folder).resolve())
    plan = {'folder': folder, 'read': [*SYSTEM_READ, *runtime_paths(), *[str(Path(p).resolve()) for p in read_only]], 'limits': spec,
            'network': bool(network), 'abi': info['landlock_abi'], 'mechanism': info['mechanism'], 'argv': list(argv)}
    launcher = [sys.executable, '-I', '-c', 'import sys;sys.path.insert(0,%r);from workbench.confine import child;child(%r)'
                % (str(Path(__file__).resolve().parents[1]), json.dumps(plan))]
    if info['mechanism'] == 'bubblewrap':
        from . import workshop_sandbox
        outer = workshop_sandbox.base_argv() + ['--bind', folder, folder, '--chdir', folder]
        for p in runtime_paths() + [str(Path(p).resolve()) for p in read_only]:
            if not p.startswith('/usr'):outer += ['--ro-bind', p, p]
        if network:outer = [a for a in outer if a != '--unshare-all'] + ['--unshare-user', '--unshare-pid', '--unshare-ipc', '--unshare-uts']
        return outer + launcher, info['mechanism']
    return launcher, info['mechanism']


def child(plan):
    """Inside the new process: limits, then the network, then Landlock, then the program. Any failure ends it unrun."""
    if isinstance(plan, str):plan = json.loads(plan)
    os.chdir(plan['folder']);limit(plan['limits'])
    if not plan['network']:
        isolated = private_network()
        if not isolated and plan['abi'] < 4 and plan['mechanism'] == 'landlock':
            sys.stderr.write('CONFINE_NETWORK: this kernel can neither refuse TCP nor give a private network; not run\n');os._exit(126)
    if plan['abi']:restrict(plan['read'], [plan['folder'], '/dev/null'], plan['abi'])
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': plan['folder'], 'LANG': 'C.UTF-8', 'TMPDIR': plan['folder'], 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
    argv = plan['argv'];program = argv[0] if '/' in argv[0] else (shutil.which(argv[0], path=env['PATH']) or argv[0])
    try:os.execve(program, argv, env)
    except OSError as exc:sys.stderr.write('CONFINE_EXEC: %s: %s\n' % (argv[0], exc.strerror));os._exit(127)


def run(argv, folder, seconds=60, read_only=(), network=False, spec=None, stdin=None):
    """Run argv confined in folder. Returns exit code, bounded output, how it was confined, and whether it was killed."""
    full, mechanism = command_for(argv, folder, read_only, network, spec)
    started = time.time()
    proc = subprocess.Popen(full, cwd=str(folder), stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    killed = None
    try:
        out, err = proc.communicate(stdin, timeout=seconds)
    except subprocess.TimeoutExpired:
        killed = 'took longer than %d seconds' % seconds;stop(proc.pid);out, err = proc.communicate()
    if proc.returncode in (-signal.SIGKILL, -signal.SIGXCPU) and not killed:killed = 'stopped (a limit, or Stop)'
    return {'exit': proc.returncode, 'stdout': out[:OUTPUT].decode('utf-8', 'replace'), 'stderr': err[:OUTPUT].decode('utf-8', 'replace'),
            'truncated': len(out) > OUTPUT or len(err) > OUTPUT, 'mechanism': mechanism, 'killed': killed, 'seconds': round(time.time() - started, 2),
            'network': bool(network), 'limits': {**LIMITS, **(spec or {})}}


def stop(pid):
    try:os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):pass


# -- inspecting untrusted files --------------------------------------------------------------------------------------

def inspect_here(folder):
    """Runs inside confinement: describe every ordinary file under folder with Ledger's own readers; print JSON."""
    from . import universal_view
    out = []
    for path in sorted(Path(folder).rglob('*')):
        if path.is_symlink() or not path.is_file():continue
        rel = path.relative_to(folder).as_posix()
        try:
            view = universal_view.describe(universal_view.Source.file(path), with_hash=False)
            facts = '; '.join('%s %s' % (k, v) for k, v in view.get('summary', [])[1:4])
            out.append({'path': rel, 'kind': view.get('kind') or '?', 'bytes': path.stat().st_size, 'read': not view.get('notice'),
                        'note': (view.get('notice') or facts)[:200]})
        except Exception as exc:  # a file a reader chokes on is reported, never fatal
            out.append({'path': rel, 'kind': '?', 'bytes': path.stat().st_size, 'read': False, 'note': '%s: %s' % (type(exc).__name__, str(exc)[:160])})
    print(json.dumps({'files': out}))


def inspect(folder, scratch, seconds=120):
    """Untrusted files read where they can do least: the copy read-only, a scratch folder the only writable place."""
    Path(scratch).mkdir(parents=True, mode=0o700, exist_ok=True)
    r = run([sys.executable, '-I', '-c', 'import sys;sys.path.insert(0,%r);from workbench.confine import inspect_here;inspect_here(%r)'
             % (str(Path(__file__).resolve().parents[1]), str(Path(folder).resolve()))], scratch, seconds, read_only=[folder],
            spec={'cpu_seconds': seconds})
    shutil.rmtree(scratch, ignore_errors=True)
    try:files = json.loads(r['stdout'].strip().splitlines()[-1])['files'] if r['exit'] == 0 else []
    except (ValueError, IndexError, KeyError):files = []
    return {'files': files, 'mechanism': r['mechanism'], 'exit': r['exit'], 'killed': r['killed'], 'problems': r['stderr'][-2000:] if r['exit'] else ''}


# -- the Kernel ------------------------------------------------------------------------------------------------------

def copy_folder(kernel, ident):
    from . import files_service
    from .working_copies import opened, the_copy
    with opened(kernel) as db:row = the_copy(db, ident)
    if row['state'] != 'WORKING':raise ValueError('CONFINE_NOT_WORKING: this working copy was discarded')
    work = files_service.root(kernel) / row['work']
    if not work.exists():raise ValueError('CONFINE_COPY_MISSING: the working copy is not on disk')
    return work if work.is_dir() else work.parent, row


def dispatch(kernel, op, args, principal):
    if op == 'confine.status':return status()
    folder, row = copy_folder(kernel, args['copy'])
    if op == 'confine.inspect':
        import uuid
        return {**inspect(folder, Path(kernel.dbpath).parent / 'confine' / uuid.uuid4().hex), 'copy': row['id']}
    if op == 'confine.run':
        if folder == Path(folder).parent:raise ValueError('CONFINE_FOLDER')
        return {**run(args['command'], folder, int(args.get('seconds') or 60)), 'copy': row['id'], 'command': args['command']}
    raise ValueError('UNKNOWN_OPERATION')

