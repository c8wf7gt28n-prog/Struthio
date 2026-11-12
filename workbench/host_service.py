"""One headless local coordinator over the existing Engineering Kernel.

The service owns clients' dispatch and in-memory console handles. The Kernel
continues to own durable jobs, execution grants, model leases and recovery.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import socketserver
import sqlite3
import stat
import sys
import threading
import time
import uuid
from sdk.cli.arc1cli import host_ipc as ipc
from .engineering_kernel import Kernel, Principal, operator
from . import activity, local_brain, work_trail, stacy_awareness, storage_check, continuing_work, worker_boundary
from .session import config_dir
from .locations import program
from .operation_stop import TERMINAL, force_cancel_worker, process_identity

CODE_INPUTS = ('MANIFEST.json', 'sdk/cli/arc1cli/host_ipc.py', 'workbench/host_service.py',
               'workbench/host_client.py', 'workbench/engineering_kernel.py',
               'workbench/engineering_cli.py', 'workbench/engine.py')


def code_digest(root):
    h = hashlib.sha256()
    for name in CODE_INPUTS:
        h.update(name.encode()); h.update(b'\0'); h.update((program(root) / name).read_bytes())
    return h.hexdigest()


class AlreadyRunning(ValueError):
    pass


class RemoteKernel:
    """Keep paired HTTP calls on the same dispatch boundary as local clients."""
    def __init__(self, coordinator): self.coordinator = coordinator
    def __getattr__(self, name): return getattr(self.coordinator.kernel, name)
    def dispatch(self, operation, params=None, principal=None):
        return self.coordinator.invoke('dispatch', {'operation': operation, 'params': params or {}}, principal)


class Coordinator:
    def __init__(self, root):
        self.root = Path(root).resolve()
        state = self.root / '.ledger'
        state.mkdir(mode=0o700, exist_ok=True)
        info = state.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Private project state is unavailable')
        if stat.S_IMODE(info.st_mode) & 0o077: state.chmod(0o700)
        self.directory = ipc.private_directory(state / 'service')
        self.lock = None
        fd = os.open(self.directory / 'coordinator.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        self.lock = os.fdopen(fd, 'r+b')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.lock.close(); self.lock = None
            raise AlreadyRunning('A coordinator already owns this project') from exc
        try:
            # Before any database opens: WAL shared by workers needs cross-process locks.
            storage_check.require(state, 'the engineering database')
            profile = config_dir(); profile.mkdir(mode=0o700, parents=True, exist_ok=True)
            if profile.stat().st_dev != state.stat().st_dev:
                storage_check.require(profile, 'the Catalog database')
            self.kernel = Kernel(self.root)
            self.instance = uuid.uuid4().hex
            self.started = time.time()
            self.digest = code_digest(self.root)
            self.transport = ipc.transport()
            self.secret = secrets.token_hex(32) if self.transport == 'loopback' else None
            self.dispatch_lock = threading.RLock()
            self.stop_lock = threading.Lock()
            self.closing = threading.Event()
            self.remote = None
            self.remote_thread = None
            self.remote_config = None
            self.recovery_error = None
            self.last_stop = None
            self.agenda_thread = None
            # A restarted broker never inherits an unobserved native unit.
            stale_workers=worker_boundary.stop_all(self.kernel)
            if any(not r['stopped'] for r in stale_workers):work_trail.hold(self.kernel,operator())
            self.reconcile()
        except BaseException:
            self.release(); raise

    def release(self):
        if self.lock is not None:
            self.lock.close(); self.lock = None

    def reconcile(self):
        try:
            with self.dispatch_lock:
                self.recovery = self.kernel.recover_interrupted()
                self.recovery_error = None
        except (ValueError, OSError, sqlite3.Error):
            # Do not silently grant fresh work when existing ownership or a
            # promotion journal needs a human's reconciliation.
            self.recovery_error = 'Existing work needs explicit reconciliation; inspect job logs and recovery.'
            work_trail.hold(self.kernel, operator())

    def info(self):
        jobs = stacy_awareness.live_jobs(self.kernel)
        pending = [j for j in jobs if j['state'] not in TERMINAL]
        return {'schema': ipc.SCHEMA, 'instance': self.instance, 'pid': os.getpid(),
                'started': self.started, 'process_start': process_identity(os.getpid()),
                'code_digest': self.digest, 'root_id': ipc.root_id(self.root),
                'transport': self.transport,
                'qt_loaded': any(n == 'PySide6' or n.startswith('PySide6.') for n in sys.modules),
                'supervision': 'systemd-user' if os.environ.get('INVOCATION_ID') and os.environ.get('ARC_LEDGER_SUPERVISION') == 'systemd-user' else 'detached-local',
                'work': work_trail.work_status(self.kernel),
                'jobs': [{'id': j['id'], 'tool': j['tool'], 'state': j['state']} for j in pending[:100]],
                'jobs_total': len(jobs), 'pending_total': len(pending), 'jobs_display_limited': len(pending) > 100,
                'recovery_error': self.recovery_error,
                'model': local_brain.status(self.kernel)['state'],
                'remote': self.remote_info(), 'closing': self.closing.is_set()}

    def remote_info(self):
        if self.remote is None:
            return {'listening': False}
        return {'listening': True, 'origin': self.remote.origin, 'profile': self.remote.profile,
                'port': self.remote.server_port, 'pair_expires': self.remote.pair_expiry}

    def remote_start(self, args):
        from .service_lifecycle import require_admission
        require_admission(self.kernel)
        from .remote_service import RemoteServer
        allowed = {'port', 'origin', 'bind', 'cert', 'key', 'profile'}
        if set(args) - allowed or not {'port', 'origin'} <= set(args):
            raise ValueError('Invalid phone listener options')
        if type(args['port']) is not int or not 0 <= args['port'] <= 65535:
            raise ValueError('Invalid phone listener port')
        if work_trail.work_status(self.kernel)['held'] or self.closing.is_set():
            raise ValueError('Work is held; explicitly resume before starting phone access')
        if self.remote is not None and args != self.remote_config:
            raise ValueError('Stop the existing phone listener before changing its configuration')
        if self.remote is None:
            server = RemoteServer(RemoteKernel(self), args['port'], args['origin'],
                                  bind=args.get('bind', '127.0.0.1'), cert=args.get('cert'),
                                  key=args.get('key'), profile=args.get('profile', 'develop'))
            self.remote = server; self.remote_config = dict(args)
            self.remote_thread = threading.Thread(target=server.serve_forever, daemon=True, name='ledger-phone')
            self.remote_thread.start()
        else:
            with self.remote.lock:
                self.remote.pair_code = secrets.token_urlsafe(24)
                self.remote.pair_expiry = time.time() + 300
        return {**self.remote_info(), 'pair_code': self.remote.pair_code}

    def remote_stop(self, revoke=True):
        revoked = True
        if revoke:
            revoked = self.kernel.dispatch('remote.disable', {}, operator())['ok']
        server, self.remote = self.remote, None
        if server is not None:
            server.shutdown(); server.server_close()
            self.remote_thread.join(timeout=2)
        self.remote_config = None
        if not revoked:
            raise ValueError('Phone listener stopped, but session revocation needs reconciliation')
        return {'listening': False, 'sessions_revoked': revoke}

    def master_stop(self):
        # Admission/revocation precede the dispatch lock: a long request cannot
        # leave new jobs open while the owner is trying to stop work.
        work_trail.hold(self.kernel, operator())
        protected_workers=worker_boundary.stop_all(self.kernel)
        revoked = self.kernel.dispatch('remote.disable', {}, operator())['ok']
        with self.stop_lock:
            report = {'schema': 'arc.host-stop/1', 'cancel_requested': [], 'errors': [], 'sessions_closed': []}
            report['protected_workers']=protected_workers
            if any(not r['stopped'] for r in protected_workers):report['errors'].append('A protected worker unit needs reconciliation')
            if not revoked: report['errors'].append('Phone session revocation needs reconciliation')
            with self.dispatch_lock:
                # AGENT-02: both sides of the one kill switch pause the assignments (the desktop's driver pauses its own); under the
                # dispatch lock no service step is in flight. The service's own shutdown runs this too and says so instead.
                from . import agent_loop
                report['assignments_paused'] = agent_loop.pause_all(self.kernel, 'The Graphite service stopped' if self.closing.is_set() else 'Master Stop')
                try: self.remote_stop()
                except ValueError: report['errors'].append('Phone session revocation needs reconciliation')
                for job in stacy_awareness.live_jobs(self.kernel):
                    if job['state'] in TERMINAL: continue
                    reply = self.kernel.dispatch('jobs.cancel', {'id': job['id']}, operator())
                    if reply['ok']: report['cancel_requested'].append(job['id'])
                    else: report['errors'].append('A job cancellation needs reconciliation')
                try: local_brain.stop(self.kernel, 'MASTER_STOP')
                except (ValueError, OSError): report['errors'].append('A model worker could not be confirmed stopped')
                for ident, session in list(getattr(self.kernel, 'console_sessions', {}).items()):
                    if not session.closed:
                        try: session.close(); report['sessions_closed'].append(ident)
                        except (ValueError, OSError): report['errors'].append('A console could not be confirmed closed')
                from . import desktop_services
                try: desktop_services.close_all(self.root)
                except (ValueError, OSError): report['errors'].append('A desktop tool could not be confirmed closed')
            began = time.monotonic()
            while True:
                jobs = stacy_awareness.live_jobs(self.kernel)
                pending = [j for j in jobs if j['state'] not in TERMINAL]
                if time.monotonic() - began > 1:
                    for job in pending:
                        if job.get('cancel') and job.get('worker_start'):
                            force_cancel_worker(self.kernel, job)
                live = [j for j in jobs if j.get('worker_start') and process_identity(j.get('pid')) == j['worker_start']]
                if not pending and not live: break
                if time.monotonic() - began >= 8: break
                time.sleep(.05)
            jobs = stacy_awareness.live_jobs(self.kernel)
            report['jobs_pending'] = [j['id'] for j in jobs if j['state'] not in TERMINAL]
            report['workers_pending'] = [j['id'] for j in jobs if j.get('worker_start') and process_identity(j.get('pid')) == j['worker_start']]
            report['result'] = 'INCOMPLETE' if report['jobs_pending'] or report['workers_pending'] or report['errors'] else 'STOPPED'
            report['work'] = work_trail.work_status(self.kernel)
            report['remote_reenabled'] = False
            self.last_stop = report
            activity.record(self.root, 'desktop-owner', 'host.master_stop', report['result'])
            return report

    def invoke(self, method, args, principal):
        if method == 'status':
            if args: raise ValueError('Status takes no options')
            return self.info()
        if method == 'dispatch':
            if set(args) != {'operation', 'params'}: raise ValueError('Invalid Kernel request')
            # These narrow record/control operations must remain reachable while
            # a bounded worker call owns the ordinary service dispatch lock.
            if args['operation'] in ('work.pause','work.revoke','work.get','work.list','workers.status','workers.runs','workers.run','workers.stop'):
                return self.kernel.dispatch(args['operation'],args['params'],principal)
            with self.dispatch_lock:
                if self.closing.is_set(): raise ValueError('Host is stopping; reconcile the request before retrying')
                return self.kernel.dispatch(args['operation'], args['params'], principal)
        if 'approve' not in principal.scopes or principal.mode == 'Tutor':
            raise ValueError('Host lifecycle control requires the local owner')
        if method == 'hold' and not args:
            return work_trail.hold(self.kernel, principal)
        if method == 'service_quiesce' and set(args)=={'cycle_id'}:
            from .service_lifecycle import close_owned_services
            with self.dispatch_lock:
                return close_owned_services(self.kernel,principal,args['cycle_id'],self.remote_stop)
        if method == 'master_stop' and not args:
            return self.master_stop()
        if method == 'shutdown' and not args:
            # Mark closing before asynchronous cleanup. Never acknowledge that
            # jobs stopped merely because the shutdown request was accepted.
            self.closing.set()
            return {'state': 'STOPPING', 'jobs_stopped': False}
        with self.dispatch_lock:
            if method == 'remote_start': return self.remote_start(args)
            if method == 'remote_stop' and set(args) <= {'revoke'} and type(args.get('revoke', True)) is bool:
                return self.remote_stop(args.get('revoke', True))
        raise ValueError('Unknown host method')

    def tick_agenda(self):
        if self.closing.is_set() or work_trail.execution_held(self.kernel):return
        if self.agenda_thread is not None and self.agenda_thread.is_alive():return
        def work():
            try:continuing_work.pump(self.kernel)
            except (ValueError,OSError,sqlite3.Error):pass  # durable work state carries actionable waiting reasons
            # AGENT-02: running assignments no desktop is stepping take one step each (the owner's setting; never raises).
            # The dispatch lock is held around each single step, so a desktop request never interleaves with one; under it, before
            # every step, the pump checks again for a hold (Master Stop), the setting and this closing flag, so a batch under way
            # ends at the step in flight.
            if not self.closing.is_set():
                from . import agent_loop
                agent_loop.pump(self.kernel,guard=self.dispatch_lock,stop=self.closing.is_set)
        self.agenda_thread=threading.Thread(target=work,name='ledger-agenda',daemon=True)
        self.agenda_thread.start()


class HostMixIn(socketserver.ThreadingMixIn):
    daemon_threads = False
    block_on_close = True
    request_queue_size = 16

    def __init__(self, address, coordinator):
        self.coordinator = coordinator
        self.capacity = threading.BoundedSemaphore(16)
        super().__init__(address, HostHandler)
        self.timeout = .2

    def process_request(self, request, address):
        if not self.capacity.acquire(blocking=False):
            self.shutdown_request(request); return
        try: super().process_request(request, address)
        except BaseException: self.capacity.release(); raise

    def process_request_thread(self, request, address):
        try: super().process_request_thread(request, address)
        finally: self.capacity.release()

    def handle_error(self, request, client_address):
        # No arbitrary request bodies, pairing codes, prompts or source text in logs.
        pass


class HostServer(HostMixIn, socketserver.UnixStreamServer):
    pass


class LoopbackServer(HostMixIn, socketserver.TCPServer):
    allow_reuse_address = False


class HostHandler(socketserver.BaseRequestHandler):
    def handle(self):
        connection = self.request
        connection.settimeout(30)
        try:
            if connection.family == socket.AF_UNIX: ipc.peer(connection)
            hello = ipc.receive(connection)
            c = self.server.coordinator
            if set(hello) != {'schema', 'root_id', 'code_digest', 'delegation', 'auth'}:
                raise ValueError('Invalid host handshake')
            if c.transport == 'loopback' and (not isinstance(hello['auth'],str) or not secrets.compare_digest(hello['auth'],c.secret)):
                raise ValueError('Local host authentication failed')
            if (hello['schema'] != ipc.SCHEMA or hello['root_id'] != ipc.root_id(c.root)
                    or hello['code_digest'] != c.digest):
                raise ValueError('Host edition differs; close clients and restart the matching program')
            ceiling = operator()
            grant = ipc.delegation(hello['delegation'], {'paths': ceiling.paths, 'tools': ceiling.tools})
            principal = Principal(**grant)
            ipc.send(connection, {'ok': True, 'instance': c.instance})
            request = ipc.receive(connection)
            if set(request) != {'method', 'args'} or not isinstance(request['method'], str) or not isinstance(request['args'], dict):
                raise ValueError('Invalid host method request')
            result = c.invoke(request['method'], request['args'], principal)
            ipc.send(connection, {'ok': True, 'result': result})
        except (ValueError, OSError, sqlite3.Error, TypeError, KeyError, RecursionError) as exc:
            try: ipc.send(connection, {'ok': False, 'error': activity.redact(str(exc), 300)})
            except (ValueError, OSError): pass


def serve(root):
    c = Coordinator(root)
    address = ipc.socket_path(root)
    endpoint = address.with_name('loopback.json')
    server = None
    ready = False
    published = False
    try:
        if c.transport == 'unix' and (address.exists() or address.is_symlink()):
            info = address.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError('Host socket path is occupied by an unexpected entry')
            address.unlink()  # exclusive project flock proves the old owner exited
        if c.transport == 'unix':
            server = HostServer(str(address), c); address.chmod(0o600)
            published = True
        else:
            server = LoopbackServer(('127.0.0.1', 0), c)
            # Only the exclusive project-lock holder publishes this private
            # endpoint. No token enters stdout, status or the audit stream.
            if endpoint.exists() or endpoint.is_symlink(): ipc.read_endpoint(endpoint)
            temporary = endpoint.with_name(uuid.uuid4().hex + '.tmp')
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    json.dump({'port': server.server_address[1], 'token': c.secret}, stream)
                os.replace(temporary, endpoint)
                published = True
            finally: temporary.unlink(missing_ok=True)
        def stop(signum, frame): c.closing.set()
        signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
        ready = True
        print(json.dumps({'state': 'READY', 'schema': ipc.SCHEMA, 'pid': os.getpid()}), flush=True)
        checked = time.monotonic()
        while not c.closing.is_set():
            server.handle_request()
            if time.monotonic() - checked >= 5:
                c.reconcile(); checked = time.monotonic()
                c.tick_agenda()
                for ident, process in list(c.kernel._workers.items()):
                    if process.poll() is not None:
                        process.wait(); c.kernel._workers.pop(ident, None)
    finally:
        c.closing.set()
        try:
            if ready: c.master_stop()
        finally:
            if server is not None: server.server_close()
            if published:
                (address if c.transport == 'unix' else endpoint).unlink(missing_ok=True)
            c.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=None)
    args = parser.parse_args(argv)
    if args.root is None:
        from .locations import default_root
        args.root = default_root()
    if not sys.platform.startswith('linux'):
        parser.error('This host service targets Linux; the agreed owner platform is Debian 13')
    os.umask(0o077)
    try: serve(args.root)
    except AlreadyRunning as exc:
        print(str(exc), file=sys.stderr); return 73
    except storage_check.UnsafeStorage as exc:
        print(str(exc), file=sys.stderr, flush=True); return 74
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
