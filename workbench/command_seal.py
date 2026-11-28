"""The seal a command runs in (Graphite 1.1 KS2): started as `python -I -S -B command_seal.py PLAN`, it seals its own
process and then becomes the program (execve). Standard library only; nothing of Graphite runs inside it but this file.

PLAN_1.1.md, KS2: "reads run sealed and their output is data". The coordinator's note: "Reads run sealed: no network
unless the form is a network read and the network rule allows it".

THE SEAL, in this order; any step that does not take ends the run before the program starts (exit 126, SEAL_...):
  1. limits      processor seconds, memory, the size of a file it writes, open files, no core dump (setrlimit)
  2. calls       seccomp: a socket of the internet (AF_INET, AF_INET6, AF_PACKET) is refused unless the form is a network
                 read; `none` refuses every socket, `local` lets the machine's own channels through (AF_UNIX for the
                 system's bus, AF_NETLINK for ip and ss); io_uring, ptrace and process_vm_writev are refused. Checked: an
                 internet socket must fail.
  3. files       Landlock: the system's own folders and the paths the form reads are readable, nothing else; only the
                 run's own scratch folder (and, for a change, the folders it was shown to write in) is writable; TCP
                 bind and connect refused unless the form is a network read (ABI 4+); signals and abstract sockets kept
                 inside (ABI 6+). Set with no_new_privs, so nothing it runs can gain privileges. Checked: a folder outside
                 the seal must not be listable.
  4. the program one argv, never a shell; found by the caller in /usr/local/bin, /usr/bin or /bin; a plain environment
                 (C.UTF-8, no colour, HOME the scratch folder); no input (stdin is /dev/null); its own session.
"""
import ctypes
import json
import os
import platform
import resource
import socket
import sys

LIMITS = {'cpu_seconds': 120, 'memory_bytes': 4 << 30, 'file_bytes': 1 << 30, 'open_files': 512}
SYSTEM_READ = ('/usr', '/bin', '/sbin', '/lib', '/lib32', '/lib64', '/etc', '/opt', '/dev/null', '/dev/zero', '/dev/urandom',
               '/dev/random', '/proc/self', '/proc/sys/kernel')
NOTE = 'SEAL_'      # the start of a line the seal writes on stderr when it ends the run unstarted

# Landlock (include/uapi/linux/landlock.h)
CALLS = {'x86_64': (444, 445, 446), 'aarch64': (444, 445, 446), 'riscv64': (444, 445, 446)}
FS_EXECUTE, FS_WRITE, FS_READ_FILE, FS_READ_DIR = 1 << 0, 1 << 1, 1 << 2, 1 << 3
FS_ALL_V1 = (1 << 13) - 1
FS_REFER, FS_TRUNCATE, FS_IOCTL_DEV = 1 << 13, 1 << 14, 1 << 15
NET_BIND, NET_CONNECT = 1 << 0, 1 << 1
SCOPE_ABSTRACT, SCOPE_SIGNAL = 1 << 0, 1 << 1
FILE_RIGHTS = FS_EXECUTE | FS_WRITE | FS_READ_FILE | FS_TRUNCATE | FS_IOCTL_DEV

# seccomp
SECCOMP = {'x86_64': (0xC000003E, {'socket': 41, 'ptrace': 101, 'process_vm_writev': 311, 'io_uring_setup': 425}),
           'aarch64': (0xC00000B7, {'socket': 198, 'ptrace': 117, 'process_vm_writev': 271, 'io_uring_setup': 425})}
AF_UNIX, AF_INET, AF_INET6, AF_NETLINK, AF_PACKET = 1, 2, 10, 16, 17


class RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64), ('handled_access_net', ctypes.c_uint64), ('scoped', ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


class Filter(ctypes.Structure):
    _fields_ = [('code', ctypes.c_uint16), ('jt', ctypes.c_uint8), ('jf', ctypes.c_uint8), ('k', ctypes.c_uint32)]


class Program(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]


def _libc():
    return ctypes.CDLL(None, use_errno=True)


def abi():
    """The Landlock ABI this kernel offers (0: none)."""
    numbers = CALLS.get(platform.machine())
    if sys.platform != 'linux' or numbers is None:return 0
    found = _libc().syscall(numbers[0], None, ctypes.c_size_t(0), ctypes.c_uint32(1))
    return found if found > 0 else 0


def available():
    """Whether this computer can seal a run (Landlock and a known processor for seccomp); never run unsealed otherwise."""
    return abi() > 0 and platform.machine() in SECCOMP


def _end(code, words):
    sys.stderr.write('%s%s: %s\n' % (NOTE, code, words));sys.stderr.flush();os._exit(126)


def limit(spec):
    for name, value in ((resource.RLIMIT_CPU, spec['cpu_seconds']), (resource.RLIMIT_AS, spec['memory_bytes']),
                        (resource.RLIMIT_FSIZE, spec['file_bytes']), (resource.RLIMIT_NOFILE, spec['open_files']), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(name, (value, value))


def calls(sockets):
    """seccomp: the sockets the form may open ('none', 'local', 'network'); io_uring, ptrace and process_vm_writev refused."""
    known = SECCOMP.get(platform.machine())
    if known is None:_end('CALLS', 'the call seal is not known on this processor (%s)' % platform.machine())
    arch, nr = known
    ALLOW, KILL, ERRNO = 0x7fff0000, 0x80000000, 0x00050000
    LD, JEQ, JGE, RET = 0x20, 0x15, 0x35, 0x06
    prog = [('ld', 4), ('jeq', arch, None, 'kill'), ('ld', 0), ('jge', 0x40000000, 'eperm', None)]
    for name in ('ptrace', 'process_vm_writev', 'io_uring_setup'):
        prog.append(('jeq', nr[name], 'eperm', None))
    if sockets == 'network':
        prog.append(('jeq', nr['socket'], None, 'allow'))
        prog += [('ld', 16), ('jeq', AF_PACKET, 'eacces', 'allow')]      # a raw link-layer socket: never
    elif sockets == 'local':
        prog.append(('jeq', nr['socket'], None, 'allow'))
        prog += [('ld', 16), ('jeq', AF_UNIX, 'allow', None), ('jeq', AF_NETLINK, 'allow', 'eacces')]
    else:
        prog.append(('jeq', nr['socket'], 'eacces', 'allow'))
    prog += [('label', 'allow'), ('ret', ALLOW), ('label', 'eperm'), ('ret', ERRNO | 1), ('label', 'eacces'), ('ret', ERRNO | 13),
             ('label', 'kill'), ('ret', KILL)]
    labels, n = {}, 0
    for ins in prog:
        if ins[0] == 'label':labels[ins[1]] = n
        else:n += 1
    built, at = [], 0
    for ins in prog:
        if ins[0] == 'label':continue
        if ins[0] == 'ld':built.append(Filter(LD, 0, 0, ins[1]))
        elif ins[0] == 'ret':built.append(Filter(RET, 0, 0, ins[1]))
        else:
            jt = 0 if ins[2] is None else labels[ins[2]] - at - 1
            jf = 0 if ins[3] is None else labels[ins[3]] - at - 1
            built.append(Filter({'jeq': JEQ, 'jge': JGE}[ins[0]], jt, jf, ins[1]))
        at += 1
    table = (Filter * len(built))(*built)
    fprog = Program(len(built), table)
    c = _libc();U = ctypes.c_ulong
    if c.prctl(38, U(1), U(0), U(0), U(0)) != 0 or c.prctl(22, U(2), ctypes.byref(fprog), U(0), U(0)) != 0:
        _end('CALLS', 'the call seal could not be laid (%s)' % os.strerror(ctypes.get_errno()))
    if sockets != 'network':
        try:
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM).close()
        except OSError:
            pass
        else:
            _end('CALLS', 'the call seal did not take: it could still open an internet socket')


def files(read, write, network, level):
    """Landlock: `read` readable, `write` writable, nothing else; TCP refused unless `network`."""
    create, add_rule, restrict_self = CALLS[platform.machine()];c = _libc()
    fs = FS_ALL_V1 | (FS_REFER if level >= 2 else 0) | (FS_TRUNCATE if level >= 3 else 0) | (FS_IOCTL_DEV if level >= 5 else 0)
    net = (NET_BIND | NET_CONNECT) if level >= 4 and not network else 0
    scoped = (SCOPE_ABSTRACT | SCOPE_SIGNAL) if level >= 6 else 0
    attr = RulesetAttr(fs, net, scoped)
    size = 8 if level < 4 else (16 if level < 6 else 24)
    fd = c.syscall(create, ctypes.byref(attr), ctypes.c_size_t(size), ctypes.c_uint32(0))
    if fd < 0:_end('FILES', 'the file seal could not be made (%s)' % os.strerror(ctypes.get_errno()))
    for paths, rights in ((read, FS_EXECUTE | FS_READ_FILE | FS_READ_DIR), (write, fs)):
        for path in paths:
            try:pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            except OSError:
                continue      # a place this computer does not have
            try:
                allowed = rights & fs
                if not os.path.isdir(path):allowed &= FILE_RIGHTS
                if path.startswith('/dev/'):allowed &= ~FS_EXECUTE
                rule = PathBeneath(allowed, pfd)
                if c.syscall(add_rule, ctypes.c_int(fd), ctypes.c_int(1), ctypes.byref(rule), ctypes.c_uint32(0)) != 0:
                    _end('FILES', 'the file seal could not take %s (%s)' % (path, os.strerror(ctypes.get_errno())))
            finally:
                os.close(pfd)
    if c.prctl(38, 1, 0, 0, 0) != 0:_end('FILES', 'no_new_privs could not be set')
    if c.syscall(restrict_self, ctypes.c_int(fd), ctypes.c_uint32(0)) != 0:
        _end('FILES', 'the file seal could not be laid (%s)' % os.strerror(ctypes.get_errno()))
    os.close(fd)


def _inside(path, roots):
    path = os.path.realpath(path)
    return any(path == r or path.startswith(r.rstrip('/') + '/') or r.startswith(path.rstrip('/') + '/') for r in roots)


def probe_for(read, write):
    """A folder that is listable now and outside every root of the seal: after the seal it must not be listable."""
    roots = [os.path.realpath(p) for p in list(read) + list(write)]
    for place in ('/srv', '/var/tmp', '/tmp', '/home', '/mnt', '/media', '/var/mail', '/root'):
        if os.path.isdir(place) and not _inside(place, roots):
            try:os.listdir(place)
            except OSError:
                continue
            return place
    return ''


def child(plan):
    """Inside the new process: limits, the call seal, the file seal, each checked; then the program."""
    if isinstance(plan, str):plan = json.loads(plan)
    level = abi()
    if level <= 0:_end('FILES', 'this computer has no Landlock, so nothing runs: never unsealed')
    os.chdir(plan['cwd'])
    limit({**LIMITS, **(plan.get('limits') or {})})
    read = list(SYSTEM_READ) + list(plan.get('read') or ())
    write = [plan['scratch'], '/dev/null'] + list(plan.get('write') or ())
    probe = probe_for(read, write)
    calls(plan.get('sockets') or 'none')
    files(read, write, plan.get('sockets') == 'network', level)
    if probe:
        try:
            os.listdir(probe)
        except OSError:
            pass
        else:
            _end('FILES', 'the file seal did not take: it could still list %s' % probe)
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': plan['scratch'], 'TMPDIR': plan['scratch'], 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
           'TERM': 'dumb', 'NO_COLOR': '1', 'SYSTEMD_COLORS': '0', 'SYSTEMD_PAGER': '', 'PAGER': 'cat', 'MANPAGER': 'cat', 'COLUMNS': '160'}
    env.update({k: str(v) for k, v in (plan.get('env') or {}).items()})
    try:
        os.execve(plan['program'], plan['argv'], env)
    except OSError as exc:
        _end('EXEC', '%s: %s' % (plan['argv'][0], exc.strerror))


if __name__ == '__main__':
    child(sys.argv[1])
