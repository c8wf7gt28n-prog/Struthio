"""Resource boundary for an owned native model worker.

CPU retains its address-space cap. Vulkan needs a larger virtual address range
for driver mappings, so its supervisor watches resident memory and host/cgroup
headroom instead. That observation is not a hard cap on GPU allocations.
"""
import argparse,os,signal,subprocess,sys
from pathlib import Path

# Where the memory reading comes from; module names so a test can point them at fixture files.
MEMINFO=Path('/proc/meminfo');OWN_CGROUP=Path('/proc/self/cgroup');CGROUPS=Path('/sys/fs/cgroup')


def host_memory():
    """Installed and available RAM as this process may use them: /proc/meminfo, narrowed by the cgroup v2 limit (less
    usage) of the process's own group and of the root. brain_runtime.host reads memory through this too, so admission
    and this guard see the same number: under a systemd scope with MemoryMax, admission no longer admits what the guard
    would stop at once."""
    values=dict(line.split(':',1) for line in MEMINFO.read_text().splitlines())
    total=int(values['MemTotal'].split()[0])*1024;available=int(values['MemAvailable'].split()[0])*1024
    # The launch process inherits its service/container cgroup; do not create or relax one.
    paths=[CGROUPS]
    try:
        group=next(line[3:] for line in OWN_CGROUP.read_text().splitlines() if line.startswith('0::'))
        if '..' not in Path(group).parts:paths.insert(0,CGROUPS/group.lstrip('/'))
    except (OSError,StopIteration):pass
    for path in paths:
        try:
            maximum=(path/'memory.max').read_text().strip()
            if maximum.isdigit():
                total=min(total,int(maximum));available=min(available,max(0,int(maximum)-int((path/'memory.current').read_text())))
        except OSError:pass
    return total,available


def memory_sample(pid):
    total,available=host_memory()
    rows=dict(line.split(':',1) for line in Path('/proc',str(pid),'status').read_text().splitlines() if ':' in line)
    return int(rows['VmRSS'].split()[0])*1024,total,available


def _child_setup(parent,memory_mb=None):
    # This trampoline is single threaded. Kill the native child if its supervisor
    # disappears between launch and the desktop's owned-process-tree snapshot.
    import ctypes,resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if memory_mb:
        limit=memory_mb*1024**2;resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0:raise OSError('Parent-death signal unavailable')
    if os.getppid()!=parent:os.kill(os.getpid(),signal.SIGKILL)


def supervise(command,memory_mb,backend='VULKAN',reserve_mb=None):
    if not sys.platform.startswith('linux'):raise ValueError('Shared-memory resource guard requires Linux')
    parent=os.getpid()
    child=subprocess.Popen(command,stdin=subprocess.DEVNULL,preexec_fn=lambda:_child_setup(parent,memory_mb if backend=='CPU' else None))
    def stop(signum,_frame):
        if child.poll() is None:child.send_signal(signum)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while True:
            try:return child.wait(timeout=.25)
            except subprocess.TimeoutExpired:pass
            try:rss,total,available=memory_sample(child.pid)
            except FileNotFoundError:
                if child.poll() is not None:return child.returncode
                raise
            reserve=min((reserve_mb or 2048)*1024**2,max(128*1024**2,total//4))
            if rss>memory_mb*1024**2 or available<reserve:
                print('GRAPHITE_HOST_MEMORY_LIMIT: resident budget or shared-host headroom exhausted',file=sys.stderr,flush=True)
                child.kill();child.wait(timeout=5);return 75
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=5)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--memory-mb',type=int,required=True)
    parser.add_argument('--backend',choices=('CPU','VULKAN'),default='CPU')
    parser.add_argument('--reserve-mb',type=int,default=2048)
    parser.add_argument('command',nargs=argparse.REMAINDER);args=parser.parse_args()
    if not 512<=args.memory_mb<=262144 or not 128<=args.reserve_mb<=16384 or not args.command:raise ValueError('Worker resource contract')
    if sys.platform.startswith('linux'):return supervise(args.command,args.memory_mb,args.backend,args.reserve_mb)
    if args.backend=='VULKAN':raise ValueError('Vulkan resource guard requires Linux')
    if os.name!='nt':
        import resource
        limit=args.memory_mb*1024*1024;resource.setrlimit(resource.RLIMIT_AS,(limit,limit))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    # Windows is monitored by the supervisor; a hard Job Object cap remains a qualification limit.
    os.execv(args.command[0],args.command)

if __name__=='__main__':sys.exit(main())
