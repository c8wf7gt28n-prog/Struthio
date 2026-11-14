"""Simulated hardware, clock, worker processes and llama.cpp replies, injected only at Graphite's own seams.

Graphite's decisions (local_brain.configuration, resource_control.decision/claim/_view, gguf_inspect, the
start_server/run_model_job load path) run unchanged. What is replaced, with unittest.mock inside the attempt's
child process, is only what they read from the outside world:

  host readings     workbench.brain_runtime.host                   -> FakeHost
  pinned runtime    brain_runtime.status / prepare, and the device listing behind brain_runtime.probe
  process table     local_brain.process_identity / owned_tree / kill_owned, resource_control.process_identity /
                    process_memory, operation_stop.process_identity -> FakeProcesses
  the worker        local_brain.subprocess.Popen -> FakePopen (writes a scripted load log, scripted exit)
  its HTTP replies  local_brain.request -> scripted /health, /props, /apply-template, /tokenize, chat reply
  time              the `time` attribute of local_brain and resource_control -> FakeClock
  file hashing      gguf_inspect.identity and local_brain.identity -> gguf_fixture.bounded_identity
  side effects      job_priority.apply_worker (renice) -> no-op; Kernel.launch -> recorded, never started

Every fake pid is above any real pid (2**22 and up), so a stop path that is not held finds nothing to signal.
"""
from __future__ import annotations

import json
import subprocess
import time as real_time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

GiB = 1024 ** 3
MiB = 1024 ** 2
NOBODY = 2 ** 22
RADEON = {'vendor_id': '0x1002', 'driver': 'amdgpu', 'accessible': True, 'name': 'AMD Radeon 680M (simulated)',
          'device_id': '0x1681'}
DEVICE_TEXT = {
    'radeon': 'Available devices:\n  Vulkan0: AMD Radeon 680M (RADV REMBRANDT) (16384 MiB, 15872 MiB free)\n',
    'llvmpipe': 'Available devices:\n  Vulkan0: llvmpipe (LLVM 19.1.7, 256 bits) (32768 MiB, 32768 MiB free)\n',
    'none': 'Available devices:\n',
}


class StopWaiting(Exception):
    """Raised by FakeClock.sleep once a waiting loop has been observed for long enough."""


class FakeClock:
    """Monotonic and wall time that only move when Graphite sleeps; time() - monotonic() stays constant."""

    def __init__(self, start=1000.0, wall_offset=1_800_000_000.0, stretch=1.0, max_sleeps=None):
        self.now = float(start)
        self.offset = wall_offset
        self.stretch = stretch
        self.max_sleeps = max_sleeps
        self.sleeps = 0
        self.hooks = []

    def monotonic(self):
        return self.now

    def time(self):
        return self.now + self.offset

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds * self.stretch
        for hook in list(self.hooks):
            hook(self)
        if self.max_sleeps is not None and self.sleeps >= self.max_sleeps:
            raise StopWaiting()

    def __getattr__(self, name):          # strftime, perf_counter, ... stay real
        return getattr(real_time, name)


class FakeHost:
    """brain_runtime.host(profile=...) with chosen RAM readings and graphics; `available` may follow the clock."""

    def __init__(self, available_gib=60, total_gib=64, cpus=16, graphics='none', clock=None):
        self.available = available_gib
        self.total = total_gib
        self.cpus = cpus
        self.graphics = graphics
        self.clock = clock
        self.calls = 0

    def _bytes(self, value):
        if callable(value):
            value = value(self.clock)
        return None if value is None else int(value * GiB)

    def profile(self):
        graphics = {'none': [], 'accessible': [dict(RADEON)], 'inaccessible': [dict(RADEON, accessible=False)]}[self.graphics]
        return {'schema': 'graphite.inference-hardware/1', 'graphics': graphics, 'simulated': True,
                'cpu': {'name': 'AMD Ryzen 7 7735HS (simulated)', 'logical_cpus': self.cpus}}

    def __call__(self, profile=True):
        self.calls += 1
        return {'schema': 'arc.brain-host/1', 'os': 'Linux', 'release': 'simulated', 'architecture': 'x86_64',
                'cpu': 'AMD Ryzen 7 7735HS (simulated)', 'logical_cpus': self.cpus,
                'total_ram_bytes': self._bytes(self.total), 'available_ram_bytes': self._bytes(self.available),
                'gpu': 'SIMULATED', 'backend': 'CPU', 'hardware_profile': self.profile() if profile else None,
                'measured_on': 'SIMULATED_HOST_READING'}


class FakeProcesses:
    """A process table for fake pids; real pids pass through to Graphite's own process_identity."""

    def __init__(self):
        from workbench import operation_stop
        self.real_identity = operation_stop.process_identity
        self.alive = {}           # pid -> token
        self.memory = {}          # pid -> (rss_bytes, private_bytes)
        self.killed = []
        self.next = NOBODY + 100

    def spawn(self, rss_bytes=0, private_bytes=0):
        self.next += 1
        pid = self.next
        self.alive[pid] = 'sim-%d' % pid
        self.memory[pid] = (rss_bytes, private_bytes)
        return pid

    def add(self, pid, rss_bytes=0, private_bytes=0, token=None):
        self.alive[pid] = token or 'sim-%d' % pid
        self.memory[pid] = (rss_bytes, private_bytes)
        return self.alive[pid]

    def identity(self, pid):
        if isinstance(pid, int) and pid >= NOBODY:
            return self.alive.get(pid)
        return self.real_identity(pid)

    def owned_tree(self, pids):
        refs = []
        for pid in pids:
            if isinstance(pid, int) and pid >= NOBODY and pid in self.alive:
                refs.append(SimpleNamespace(pid=pid, token=self.alive[pid]))
        return refs

    def kill_owned(self, refs, *args, **kwargs):
        for ref in refs:
            pid = ref['pid'] if isinstance(ref, dict) else ref.pid
            if pid in self.alive:
                del self.alive[pid]
                self.killed.append(pid)

    def process_memory(self, pid, token, private=False):
        if not pid or pid not in self.alive or self.alive[pid] != token:
            return dict(rss_bytes=0, private_bytes=0, observed=False)
        rss, priv = self.memory.get(pid, (0, 0))
        return dict(rss_bytes=rss, private_bytes=priv if private else 0, observed=True)

    def live_fake(self):
        return sorted(self.alive)


class Worker:
    """One scripted llama.cpp worker: its load log, whether it exits, its health and replies."""

    def __init__(self, log='', exit=None, health=True, n_ctx=None, reply='ready', on_health=None):
        self.log = log
        self.exit = exit
        self.health = health
        self.n_ctx = n_ctx
        self.reply = reply
        self.on_health = on_health


class Bench:
    """Installs every seam for one simulated scenario; read .popen_argv, .procs, .clock afterwards."""

    def __init__(self, host=None, clock=None, workers=(), devices='radeon', vulkan_installed=True):
        self.clock = clock or FakeClock()
        self.host = host or FakeHost(clock=self.clock)
        if self.host.clock is None:
            self.host.clock = self.clock
        self.workers = list(workers)
        self.devices = devices
        self.vulkan_installed = vulkan_installed
        self.popen_argv = []
        self.launched = []
        self.by_pid = {}
        self.requests = []
        self.stack = None
        self.procs = None

    # -- fakes ---------------------------------------------------------------------------------
    def _status(self, root, backend='CPU'):
        state = 'PINNED_%s_AVAILABLE' % backend if (backend == 'CPU' or self.vulkan_installed) else 'RUNTIME_ADDON_NOT_INSTALLED'
        return {'schema': 'arc.brain-runtime/1', 'state': state, 'build': 'b11669', 'source_commit': 'simulated',
                'platform': 'linux-vulkan-x64' if backend == 'VULKAN' else 'linux-x64', 'backend': backend,
                'vulkan': 'PINNED_AVAILABLE_NOT_DEVICE_QUALIFIED' if self.vulkan_installed else 'NOT_INSTALLED_FOR_PLATFORM',
                'available_backends': ['CPU', 'VULKAN'] if self.vulkan_installed else ['CPU'], 'pin': {'platforms': {}}}

    def _prepare(self, root, backend='CPU'):
        return Path('/simulated/llama-server'), {'build': 'b11669', 'source_commit': 'simulated', 'archive_sha256': 'simulated',
                                                 'platform': 'linux-vulkan-x64' if backend == 'VULKAN' else 'linux-x64',
                                                 'backend': backend, 'simulated': True}

    def _run(self, argv, *args, **kwargs):
        if argv and '--list-devices' in argv:
            return subprocess.CompletedProcess(argv, 0, DEVICE_TEXT[self.devices], '')
        return self._real_run(argv, *args, **kwargs)

    def _popen_class(self):
        bench = self

        class FakePopen:
            def __init__(self, argv, cwd=None, stdin=None, stdout=None, stderr=None, env=None, **kwargs):
                bench.popen_argv.append(list(argv))
                script = bench.workers.pop(0) if bench.workers else Worker(log='', health=False)
                self.script = script
                self.pid = bench.procs.spawn()
                bench.by_pid[self.pid] = script
                if stdout is not None and script.log:
                    stdout.write(script.log.encode())
                    stdout.flush()
                self.returncode = None

            def poll(self):
                if self.pid not in bench.procs.alive:
                    self.returncode = -9 if self.returncode is None else self.returncode
                    return self.returncode
                if self.script.exit is not None:
                    bench.procs.alive.pop(self.pid, None)
                    self.returncode = self.script.exit
                    return self.returncode
                return None

            def kill(self):
                bench.procs.alive.pop(self.pid, None)

            def terminate(self):
                self.kill()

            def wait(self, timeout=None):
                self.kill()
                return self.poll()

        return FakePopen

    def _request(self, worker, path, payload=None, timeout=90):
        self.requests.append(path)
        pid = worker.get('pid')
        script = self.by_pid.get(pid)
        if script is None or pid not in self.procs.alive:
            raise ValueError('MODEL_WORKER_NOT_LIVE')
        if path == '/health':
            if script.on_health:
                script.on_health(self)
            if not script.health:
                raise ValueError('LOCAL_WORKER_HTTP_503')
            return {'status': 'ok'}
        if path == '/props':
            return {'default_generation_settings': {'n_ctx': script.n_ctx}} if script.n_ctx else {}
        if path == '/apply-template':
            return {'prompt': '<|im_start|>user\n' + json.dumps(payload.get('messages'))[:200]}
        if path == '/tokenize':
            return {'tokens': [1] * 12}
        if path == '/v1/chat/completions':
            if isinstance(script.reply, str) and script.reply.startswith('HTTP'):
                raise ValueError('LOCAL_WORKER_' + script.reply.replace(' ', '_'))
            return {'choices': [{'message': {'content': script.reply}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 12, 'completion_tokens': 1}, 'timings': {'simulated': True}}
        raise ValueError('LOCAL_ENDPOINT_NOT_REGISTERED')

    def live_workers(self):
        """Model worker processes this scenario started that are still alive (owned workers left behind)."""
        return sorted(pid for pid in self.by_pid if pid in self.procs.alive)

    # -- install -------------------------------------------------------------------------------
    def __enter__(self):
        from sdk.cli.arc1cli import gguf_inspect
        from workbench import brain_runtime, job_priority, local_brain, operation_stop, resource_control
        from workbench.engineering_kernel import Kernel
        from . import gguf_fixture
        self.procs = FakeProcesses()
        self._real_run = subprocess.run
        s = self.stack = ExitStack()
        s.enter_context(patch.object(brain_runtime, 'host', side_effect=self.host))
        s.enter_context(patch.object(brain_runtime, 'status', side_effect=self._status))
        s.enter_context(patch.object(brain_runtime, 'prepare', side_effect=self._prepare))
        s.enter_context(patch.object(brain_runtime.subprocess, 'run', side_effect=self._run))
        s.enter_context(patch.object(local_brain, 'process_identity', side_effect=self.procs.identity))
        s.enter_context(patch.object(local_brain, 'owned_tree', side_effect=self.procs.owned_tree))
        s.enter_context(patch.object(local_brain, 'kill_owned', side_effect=self.procs.kill_owned))
        s.enter_context(patch.object(operation_stop, 'process_identity', side_effect=self.procs.identity))
        s.enter_context(patch.object(resource_control, 'process_identity', side_effect=self.procs.identity))
        s.enter_context(patch.object(resource_control, 'process_memory', side_effect=self.procs.process_memory))
        s.enter_context(patch.object(local_brain.subprocess, 'Popen', self._popen_class()))
        s.enter_context(patch.object(local_brain, 'request', side_effect=self._request))
        s.enter_context(patch.object(local_brain, 'time', self.clock))
        s.enter_context(patch.object(resource_control, 'time', self.clock))
        s.enter_context(patch.object(gguf_inspect, 'identity', side_effect=gguf_fixture.bounded_identity))
        s.enter_context(patch.object(local_brain, 'identity', side_effect=gguf_fixture.bounded_identity))
        s.enter_context(patch.object(job_priority, 'apply_worker', side_effect=lambda job: None))
        s.enter_context(patch.object(Kernel, 'launch', side_effect=lambda kernel_self, ident: self.launched.append(ident),
                                     autospec=True))
        return self

    def __exit__(self, *exc):
        self.stack.close()
        return False
