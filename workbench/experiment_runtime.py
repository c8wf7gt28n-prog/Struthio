"""A distinct WASI CPython profile; never an unconfined native-Python fallback.

Only bundled, hash-pinned CPython and WASI preview1 imports are admitted. The
trusted embedding process stays in the Kernel job's cancellation process group.
"""
from __future__ import annotations
import hashlib, importlib.metadata, json, os, platform, shutil, struct, tempfile, time, zipfile
from pathlib import Path

PROFILE = 'ledger.python-wasi/1'
WASMTIME = '50.0.1'
ARCHIVE_SHA = 'ceec2512d4bf2d2377a4791603e9879329c9b6aa0e7514a19ef827cdefe3b274'
RUNTIME = Path(__file__).resolve().parents[1] / 'runtimes/python-wasi'
LIMITS = {'memory_bytes': 128*1024*1024, 'fuel': 20_000_000_000,
          'output_bytes': 2*1024*1024, 'open_calls': 128, 'seconds': 30}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def status():
    try:
        import wasmtime
        version = importlib.metadata.version('wasmtime')
        if version != WASMTIME: raise ValueError('Install the pinned wasmtime==' + WASMTIME)
        archive = RUNTIME/'python-wasi.zip'
        if sha(archive) != ARCHIVE_SHA: raise ValueError('Bundled CPython WASI archive changed')
        package = Path(wasmtime.__file__).parent
        binaries = sorted(package.rglob('*wasmtime*.so')) + sorted(package.rglob('*wasmtime*.dll')) + sorted(package.rglob('*wasmtime*.dylib'))
        if not binaries: raise ValueError('Wasmtime native library missing')
        return {'available': True, 'profile': PROFILE, 'python': '3.13.17 WASI SDK 24',
                'wasmtime': version, 'runtime_sha256': ARCHIVE_SHA,
                'embedding_sha256': sha(__file__), 'native_library': {str(p): sha(p) for p in binaries},
                'host': {'os': platform.system(), 'machine': platform.machine(), 'kernel': platform.release()},
                'limits': LIMITS, 'qualified': False,
                'scope': 'Single WASI CPython instance; selected read-only inputs and owned output directory. Standard library only; no native extensions, host processes, network or environment inheritance.'}
    except (OSError, ImportError, ValueError, importlib.metadata.PackageNotFoundError) as exc:
        return {'available': False, 'profile': PROFILE, 'qualified': False, 'reason': str(exc)}


def unpack(parent):
    """Extract the complete pinned distribution into a private, fresh directory."""
    if not status()['available']: raise ValueError('PYTHON_WASI_UNAVAILABLE')
    target = Path(parent)/'runtime'; target.mkdir(mode=0o700, parents=True, exist_ok=False)
    with zipfile.ZipFile(RUNTIME/'python-wasi.zip') as archive:
        for item in archive.infolist():
            path = Path(item.filename)
            if path.is_absolute() or '..' in path.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsafe runtime archive member')
            dest = target/path
            if item.is_dir(): dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as stream: stream.write(archive.read(item))
    return target


class Runner:
    def __init__(self, runtime):
        import wasmtime as w
        self.w = w; self.runtime = Path(runtime)
        modules = list(self.runtime.rglob('*.wasm'))
        if len(modules) != 1: raise ValueError('Expected one pinned CPython WASI module')
        config = w.Config(); config.consume_fuel = True; config.wasm_threads = False
        self.engine = w.Engine(config); self.module = w.Module.from_file(self.engine, str(modules[0]))
        if any(i.module != 'wasi_snapshot_preview1' for i in self.module.imports):
            raise ValueError('Unsupported guest host imports')

    def execute(self, inputs, outputs, *, fuel=None, output_bytes=None):
        w = self.w; inputs = Path(inputs); outputs = Path(outputs)
        outputs.mkdir(parents=True, exist_ok=False)
        store = w.Store(self.engine); store.set_limits(memory_size=LIMITS['memory_bytes'], memories=1, instances=1)
        store.set_fuel(LIMITS['fuel'] if fuel is None else fuel)
        budget = {'bytes': 0, 'opens': 0}; logs = {'stdout': bytearray(), 'stderr': bytearray()}
        maximum = LIMITS['output_bytes'] if output_bytes is None else output_bytes
        def logger(name):
            def write(raw):
                # fd_write already reserves these bytes. Keep bounded diagnostics.
                logs[name].extend(raw[:max(0, 65536-len(logs[name]))]); return len(raw)
            return write
        wasi = w.WasiConfig(); wasi.argv = ['python', '-I', '-B', '/inputs/experiment.py', '/inputs/parameters.json', '/output']
        wasi.env = [('HOME', '/output'), ('TMPDIR', '/output')]
        wasi.stdout_custom = logger('stdout'); wasi.stderr_custom = logger('stderr')
        wasi.preopen_dir(str(self.runtime), '/usr/local', fs_mutable=False)
        wasi.preopen_dir(str(inputs), '/inputs', fs_mutable=False)
        wasi.preopen_dir(str(outputs), '/output', fs_mutable=True)
        store.set_wasi(wasi); linker = w.Linker(self.engine); linker.define_wasi()
        # Meter all guest file/stdout writes before the host performs them. Growing
        # files without writes and links are refused, avoiding disk-budget holes.
        imports = {i.name: i.type for i in self.module.imports}
        thunks = {}
        linker.allow_shadowing = True
        def fd_write(caller, fd, vector, count, written):
            if count < 0 or count > 1024: return 28  # WASI EINVAL
            memory = caller.get('memory'); raw = memory.read(caller, vector, vector+count*8)
            if len(raw) != count*8: return 21  # EFAULT
            size = sum(struct.unpack_from('<II', raw, i*8)[1] for i in range(count))
            if size > maximum-budget['bytes']: raise w.Trap('LEDGER_OUTPUT_BUDGET')
            budget['bytes'] += size
            return thunks['fd_write'](caller, fd, vector, count, written)
        def path_open(caller, *args):
            budget['opens'] += 1
            if budget['opens'] > LIMITS['open_calls']: raise w.Trap('LEDGER_FILE_OPEN_BUDGET')
            return thunks['path_open'](caller, *args)
        def fd_seek(caller, fd, offset, whence, result):
            code = thunks['fd_seek'](caller, fd, offset, whence, result)
            if code == 0:
                raw = caller.get('memory').read(caller, result, result+8)
                if len(raw)!=8 or struct.unpack('<Q',raw)[0]>maximum:raise w.Trap('LEDGER_FILE_POSITION_BUDGET')
            return code
        if 'fd_write' in imports: linker.define_func('wasi_snapshot_preview1', 'fd_write', imports['fd_write'], fd_write, access_caller=True)
        if 'path_open' in imports: linker.define_func('wasi_snapshot_preview1', 'path_open', imports['path_open'], path_open, access_caller=True)
        if 'fd_seek' in imports: linker.define_func('wasi_snapshot_preview1', 'fd_seek', imports['fd_seek'], fd_seek, access_caller=True)
        for name in ('fd_allocate', 'fd_pwrite', 'fd_filestat_set_size', 'path_link', 'path_symlink', 'path_create_directory'):
            if name in imports: linker.define_func('wasi_snapshot_preview1', name, imports[name], lambda *args: 63) # EPERM
        start = time.monotonic(); exit_code = 0; trapped = None
        try:
            instance = linker.instantiate(store, self.module)
            # WASI needs the calling Wasm instance's memory. These small Wasm
            # forwarding functions share the guest memory and keep that calling
            # convention intact when a metering callback re-enters WASI.
            forward = w.Linker(self.engine); forward.define_wasi()
            forward.define(store, 'guest', 'memory', instance.exports(store)['memory'])
            declarations = ['(module (import "guest" "memory" (memory 0))']; functions = []
            for name in ('fd_write', 'path_open', 'fd_seek'):
                if name not in imports: continue
                ty = imports[name]; params = ' '.join(str(t) for t in ty.params); results = ' '.join(str(t) for t in ty.results)
                declarations.append(f'(import "wasi_snapshot_preview1" "{name}" (func ${name} (param {params}) (result {results})))')
                functions.append(f'(func (export "{name}") (param {params}) (result {results}) '+ ' '.join('local.get '+str(i) for i in range(len(ty.params)))+f' call ${name})')
            shim = w.Module(self.engine, '\n'.join(declarations+['(export "memory" (memory 0))']+functions)+')')
            # One additional trusted forwarding instance and shared memory.
            store.set_limits(memory_size=LIMITS['memory_bytes'], memories=1, instances=2)
            shim_instance = forward.instantiate(store, shim)
            thunks.update(shim_instance.exports(store))
            instance.exports(store)['_start'](store)
        except w.ExitTrap as exc: exit_code = exc.code
        except w.Trap as exc: exit_code = None; trapped = str(exc)
        finally:
            # Explicit closure prevents guest streams surviving into another call.
            store.close(); linker.close()
        for name, raw in logs.items(): (outputs.parent/(outputs.name+'-'+name+'.log')).write_bytes(raw)
        return {'profile': PROFILE, 'exit_code': exit_code, 'trap': trapped,
                'seconds': time.monotonic()-start, 'metered_output_bytes': budget['bytes'],
                'open_calls': budget['opens'], 'stdout': logs['stdout'].decode('utf-8', 'replace'),
                'stderr': logs['stderr'].decode('utf-8', 'replace'), 'limits': LIMITS}


PROBE = r'''
import os, json, socket, subprocess
def denied(fn):
    try: fn()
    except (OSError, ImportError, RuntimeError, NotImplementedError, AttributeError): return True
    return False
checks = {
 'outside_read': denied(lambda: open('/etc/passwd').read()),
 'outside_write': denied(lambda: open('/escape.txt','w').write('bad')),
 'input_write': denied(lambda: open('/inputs/parameters.json','w').write('bad')),
 'process_spawn': denied(lambda: subprocess.run(['/bin/true'])),
 'fork': denied(lambda: os.fork()),
 'tcp': denied(lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('127.0.0.1',80))),
 'udp': denied(lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'x',('127.0.0.1',80))),
 'unix_socket': denied(lambda: socket.socket(socket.AF_UNIX, socket.SOCK_STREAM).connect('/run/no.sock')),
 'environment_private': 'LEDGER_QUALIFICATION_SECRET' not in os.environ,
 'input_read': json.load(open('/inputs/parameters.json')) == {'probe': True},
}
open('/output/probe.json','w').write(json.dumps(checks))
'''


def qualify(folder):
    """Actual capability-denial, execution, memory, fuel and output probes."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=False)
    binding = status()
    if not binding['available']: raise ValueError('PYTHON_WASI_UNAVAILABLE: '+binding['reason'])
    runtime = unpack(folder); runner = Runner(runtime); cases = {}
    def run(name, code, **kwargs):
        inp = folder/(name+'-inputs'); inp.mkdir(); (inp/'experiment.py').write_text(code)
        (inp/'parameters.json').write_text('{"probe":true}')
        cases[name] = runner.execute(inp, folder/name, **kwargs); return cases[name]
    os.environ['LEDGER_QUALIFICATION_SECRET'] = 'must-not-enter-guest'
    try: run('boundary', PROBE)
    finally: os.environ.pop('LEDGER_QUALIFICATION_SECRET', None)
    checks = json.loads((folder/'boundary/probe.json').read_text())
    if cases['boundary']['exit_code'] != 0 or not checks or not all(checks.values()): raise ValueError('WASI_BOUNDARY_PROBE_FAILED: '+str(checks))
    if not run('fuel', "open('/output/entered','w').write('entered')\nwhile True: pass", fuel=8_000_000_000)['trap'] or not (folder/'fuel/entered').is_file(): raise ValueError('WASI_FUEL_LIMIT_FAILED')
    memory = run('memory', "x = bytearray(256*1024*1024)")
    if memory['exit_code'] == 0 or not ('MemoryError' in memory['stderr'] or memory['trap']): raise ValueError('WASI_MEMORY_LIMIT_FAILED')
    if not run('output', "open('/output/big','wb').write(b'x'*100000)", output_bytes=20000)['trap']: raise ValueError('WASI_OUTPUT_LIMIT_FAILED')
    if not run('sparse', "f=open('/output/sparse','wb'); f.seek(10**12); f.write(b'x')")['trap']:raise ValueError('WASI_SPARSE_FILE_LIMIT_FAILED')
    return {'schema': 'ledger.python-qualification/1', 'qualified': True, 'binding': binding,
            'checks': checks, 'cases': cases, 'created': time.time(), 'expires': time.time()+86400,
            'wall_timeout_and_group_cancellation': 'Enforced by the registered Kernel job; qualification does not grant an arbitrary native Python process.'}
