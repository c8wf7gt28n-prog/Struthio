"""Pinned CPU and Vulkan workers from one upstream revision. No runtime from PATH."""
import gzip,hashlib,json,os,platform,re,shutil,subprocess,sys,tarfile,tempfile,zipfile
from pathlib import Path,PurePosixPath
from .session import config_dir
from .locations import program

PIN='runtimes/llama.cpp/b11669/runtime.json'
ADDON_HINT='The runtime for this computer comes as an add-on: unzip the runtime add-on into the program folder, which places %s next to runtime.json.'

def host(profile=True):
    """This computer for a model: its memory now and, with `profile`, its hardware profile (inference_hardware.snapshot,
    which reads the installed packages through dpkg-query when its list is not kept). A reader of memory alone passes
    profile=False, so opening a page that shows memory starts no process (0.7.0)."""
    total=available=None;cpu=platform.processor() or platform.machine()
    if os.name=='nt':
        import ctypes
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(key,ctypes.c_ulonglong) for key in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
        memory=Memory();memory.length=ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):total,available=memory.total,memory.available
    else:
        try:
            total=os.sysconf('SC_PHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
            available=os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
            if Path('/proc/cpuinfo').is_file():
                cpu=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),cpu)
        except (OSError,ValueError,KeyError):pass
        try:
            # The worker guard's own reading (MemAvailable, then this process's cgroup v2 limit less usage), so a model
            # admitted here is not one the guard stops at once. Without /proc the sysconf figures above stand.
            from .brain_worker import host_memory
            total,available=host_memory()
        except (OSError,ValueError,KeyError):pass
    if not profile:
        return {'schema':'arc.brain-host/1','os':platform.system(),'release':platform.release(),'architecture':platform.machine(),
                'cpu':cpu,'logical_cpus':os.cpu_count(),'total_ram_bytes':total,'available_ram_bytes':available,
                'gpu':'NOT_READ_HERE','backend':'CPU','hardware_profile':None,'measured_on':'CURRENT_EXECUTION_HOST',
                'backend_note':'Memory only: the hardware profile is read where it is shown (the Brain room).'}
    from .inference_hardware import snapshot
    profile=snapshot()
    return {'schema':'arc.brain-host/1','os':platform.system(),'release':platform.release(),'architecture':platform.machine(),
            'cpu':cpu,'logical_cpus':os.cpu_count(),'total_ram_bytes':total,'available_ram_bytes':available,
            'gpu':'DETECTED_NOT_INFERENCE_QUALIFIED' if profile['graphics'] else 'NOT_DETECTED',
            'backend':'CPU','hardware_profile':profile,'measured_on':'CURRENT_EXECUTION_HOST',
            'backend_note':'CPU is the compatibility baseline here; the owned running worker reports its effective backend.'}

def status(root,backend='CPU'):
    if backend not in ('CPU','VULKAN'):raise ValueError('INFERENCE_BACKEND_INVALID')
    path=program(root)/PIN
    if not path.is_file():return {'schema':'arc.brain-runtime/1','state':'RUNTIME_NOT_INSTALLED','build':None,'source_commit':None,'platform':platform.system(),'backend':backend,'vulkan':'NOT_QUALIFIED','pin':{'platforms':{}}}
    pin=json.loads(path.read_text())
    machine=platform.machine().lower();base=('windows' if os.name=='nt' else 'linux')
    key=base+('-vulkan' if backend=='VULKAN' else '')+'-x64'
    supported=machine in ('x86_64','amd64') and platform.system() in ('Linux','Windows')
    item=pin['platforms'].get(key) if supported else None
    # 4.1: the Windows archive ships as an add-on, so a pinned platform whose archive is absent is "not installed yet", not unsupported.
    state='RUNTIME_PLATFORM_UNAVAILABLE' if not item else 'PINNED_'+backend+'_AVAILABLE' if (path.parent/item['archive']).is_file() else 'RUNTIME_ADDON_NOT_INSTALLED'
    vulkan=pin['platforms'].get(base+'-vulkan-x64') if supported else None
    vulkan_available=bool(vulkan and (path.parent/vulkan['archive']).is_file())
    found={'schema':'arc.brain-runtime/1','state':state,
            'build':pin['build'],'source_commit':pin['source_commit'],'platform':key,'backend':backend,
            'vulkan':'PINNED_AVAILABLE_NOT_DEVICE_QUALIFIED' if vulkan_available else 'NOT_INSTALLED_FOR_PLATFORM',
            'available_backends':[kind for kind,suffix in (('CPU',''),('VULKAN','-vulkan'))
                                  if supported and (candidate:=pin['platforms'].get(base+suffix+'-x64'))
                                  and (path.parent/candidate['archive']).is_file()],'pin':pin}
    if state=='RUNTIME_ADDON_NOT_INSTALLED':found['hint']=ADDON_HINT % item['archive']
    return found

def prepare(root,backend='CPU'):
    # The diagnostics thread and a model job can reach the same private cache.
    # Serialize Linux materialization so one cannot replace another's libraries.
    if os.name!='nt':
        import fcntl
        info=status(root,backend);folder=config_dir()/'runtimes'/str(info['build'])
        folder.mkdir(parents=True,mode=0o700,exist_ok=True)
        with (folder/(info['platform']+'.lock')).open('ab') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            return _prepare(root,backend)
    return _prepare(root,backend)

def _prepare(root,backend='CPU'):
    info=status(root,backend)
    if info['state']!='PINNED_'+backend+'_AVAILABLE':raise ValueError(info.get('hint') or 'No pinned '+backend+' runtime for this OS/architecture')
    key=info['platform'];entry=info['pin']['platforms'][key];archive=(program(root)/PIN).parent/entry['archive']
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('PINNED_RUNTIME_ARCHIVE_CHANGED')
    destination=config_dir()/'runtimes'/info['build']/key
    receipt=destination/'EXTRACTED.json'
    def valid():
        try:
            document=json.loads(receipt.read_text())
            return document['archive_sha256']==entry['sha256'] and all(
                (destination/name).is_file() and not (destination/name).is_symlink() and hashlib.sha256((destination/name).read_bytes()).hexdigest()==digest
                for name,digest in document['files'].items())
        except (OSError,ValueError,KeyError):return False
    if not valid():
        destination.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        temporary=Path(tempfile.mkdtemp(prefix='llama-',dir=destination.parent));files={}
        try:
            # Read validated upstream bytes; materialize regular files only.
            import io
            if entry['format']=='zip':
                with zipfile.ZipFile(io.BytesIO(raw)) as z:members=[(m.filename,z.read(m)) for m in z.infolist() if not m.is_dir()]
            else:
                # Read compressed bytes once. Resolving tar aliases via repeated
                # seeks in a gzip stream otherwise re-inflates the distribution
                # for each linked library during first-use materialization.
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:expanded=compressed.read(512*1024*1024+1)
                if len(expanded)>512*1024*1024:raise ValueError('RUNTIME_ARCHIVE_LIMIT')
                with tarfile.open(fileobj=io.BytesIO(expanded),mode='r:') as z:
                    members=[]
                    for member in z.getmembers():
                        if member.isfile() or member.issym() or member.islnk():
                            stream=z.extractfile(member)
                            if stream:members.append((member.name,stream.read()))
            if len(members)>1000 or sum(len(data) for _,data in members)>512*1024*1024:raise ValueError('RUNTIME_ARCHIVE_LIMIT')
            for name,data in members:
                pure=PurePosixPath(name)
                if pure.is_absolute() or '..' in pure.parts or '\\' in name or name in files:raise ValueError('RUNTIME_ARCHIVE_PATH')
                target=temporary/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                target.chmod(0o500 if target.suffix not in ('.dll','.so') else 0o400)
                files[name]=hashlib.sha256(data).hexdigest()
            (temporary/'EXTRACTED.json').write_text(json.dumps({'archive_sha256':entry['sha256'],'files':files}))
            if destination.exists():shutil.rmtree(destination)
            os.replace(temporary,destination)
        finally:
            if temporary.exists():shutil.rmtree(temporary)
    executable=destination/entry['root']/entry['executable']
    if not executable.is_file():raise ValueError('PINNED_RUNTIME_EXECUTABLE_MISSING')
    return executable,{'build':info['build'],'source_commit':info['source_commit'],'archive_sha256':entry['sha256'],'platform':key,'backend':backend}


def worker_environment(backend='CPU',runtime=None,cache=None):
    """The model worker's environment from an allow-list (0.8.7, the sealed room), replacing "everything except
    LLAMA_ARG_*": PATH, the locale and the runtime's own library folder; for Vulkan XDG_RUNTIME_DIR and a shader cache
    under Graphite's state. A key the owner's shell sets for another tool (LLAMA_API_KEY, HF_TOKEN), LLAMA_CACHE,
    GGML_BACKEND_PATH, debug switches and proxies never reach it; saved Graphite options alone set the worker."""
    from .brain_seal import environment
    return environment(os.environ,backend,runtime,cache)


def parse_devices(text):
    devices=[]
    for line in text.splitlines():
        match=re.match(r'^\s*(Vulkan\d+):\s*(.+)$',line)
        if not match:continue
        name=match[2].strip();memory=re.search(r'\((\d+)\s*(MiB|MB),\s*(\d+)\s*(?:MiB|MB)\s+free\)',name)
        factor=1024*1024 if memory and memory[2]=='MiB' else 1000000
        devices.append(dict(id=match[1],name=name[:memory.start()].strip() if memory else name,
                            software=bool(re.search(r'llvmpipe|lavapipe|swiftshader|software',name,re.I)),
                            reported_total_bytes=int(memory[1])*factor if memory else None,
                            reported_free_bytes=int(memory[3])*factor if memory else None))
    return devices[:16]


def _listing(root,executable,sealed):
    """`--list-devices` once: inside the sealed room (through brain_worker, which unshares the runtime's own network
    before exec, as for a model) or, when `sealed` is False, without it. The environment is the allow-list either way."""
    command=[str(executable),'--list-devices']
    if sealed:
        from .locations import child_env
        command=[sys.executable,'-m','workbench.brain_worker','--memory-mb','2048','--backend','VULKAN','--reserve-mb','128',
                 '--seal','network']+command
        env=child_env(root,worker_environment('VULKAN',executable.parent))
    else:env=worker_environment('VULKAN',executable.parent)
    result=subprocess.run(command,env=env,cwd=str(root) if sealed else None,
                          stdin=subprocess.DEVNULL,capture_output=True,text=True,errors='replace',timeout=12)
    return result,(result.stdout+'\n'+result.stderr)[-65536:]


def probe(root):
    """Explicit bounded device discovery, never model inference or a benchmark.

    0.8.7, the sealed room: discovery looks from inside the runtime's own empty network first, as a model would run. If
    the Radeon is seen only from outside it (Vulkan inside a user namespace is untested), the result says so in
    `network_seal`, and the model start takes open question 4's default: the Radeon without its own network, still
    offline, behind its private socket and both allow-lists, labelled not sealed; the sealed processor one press away."""
    try:
        executable,runtime=prepare(root,'VULKAN')
        from .brain_seal import NOT_SEALED_MARK,network_seal_possible
        sealed=network_seal_possible()
        result,text=_listing(root,executable,sealed)
        devices=parse_devices(text);physical=[d for d in devices if not d['software']]
        seal='NOT_TRIED' if not sealed else 'COMPUTER_REFUSED' if NOT_SEALED_MARK in text else 'SEEN_IN_ITS_OWN_NETWORK'
        if seal=='SEEN_IN_ITS_OWN_NETWORK' and not (result.returncode==0 and physical):
            outside,outside_text=_listing(root,executable,False)
            outside_devices=parse_devices(outside_text)
            if outside.returncode==0 and [d for d in outside_devices if not d['software']]:
                result,text,devices=outside,outside_text,outside_devices
                physical=[d for d in devices if not d['software']];seal='VULKAN_NOT_SEEN_IN_ITS_OWN_NETWORK'
            else:seal='NOT_SEEN_EITHER_WAY'
        state='AVAILABLE' if result.returncode==0 and physical else 'NO_PHYSICAL_VULKAN_DEVICE' if result.returncode==0 else 'VULKAN_PROBE_FAILED'
        lines=[line for line in text.strip().splitlines() if not line.startswith(NOT_SEALED_MARK)]
        reason=None if state=='AVAILABLE' else ('No physical device was reported by the pinned worker.' if result.returncode==0 else lines[-1][:300] if lines else 'Worker exited '+str(result.returncode))
        return dict(state=state,devices=devices,runtime=runtime,reason=reason,network_seal=seal,
                    qualification='DEVICE_DISCOVERY_ONLY_NOT_MODEL_OR_PERFORMANCE_QUALIFICATION')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        return dict(state='VULKAN_UNAVAILABLE',devices=[],reason=str(exc)[:300],qualification='NOT_RUN')
