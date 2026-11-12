"""Trusted same-account desktop/CLI client; no mutation retries or local fallback."""
from __future__ import annotations
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import threading
import time
from sdk.cli.arc1cli import host_ipc as ipc
from .engineering_kernel import Kernel, Principal, operator

_CLIENTS = {}
_LOCK = threading.RLock()
_OWNED = {}


class HostUnavailable(ValueError):
    pass


def principal_request(principal):
    return {'identity': principal.identity, 'scopes': sorted(principal.scopes),
            'paths': list(principal.paths), 'tools': list(principal.tools), 'mode': principal.mode}


class HostClient(Kernel):
    """Existing local read/presentation helpers; all dispatch runs in the host.

    No writable database or arbitrary method is exposed over IPC. Trusted local
    desktop presentation adapters retain their existing local profile access.
    """
    is_host_client = True

    def __init__(self, root):
        from .host_service import code_digest
        self.root = Path(root).resolve()
        self.state = self.root / '.ledger'
        self.dbpath = self.state / 'engineering.sqlite3'
        self._workers = {}
        self.digest = code_digest(self.root)
        self.address = ipc.socket_path(self.root)
        self.transport = ipc.transport()
        self.endpoint_path = self.address if self.transport == 'unix' else self.address.with_name('loopback.json')

    def rpc(self, method, args=None, principal=None, timeout=35):
        p = principal or operator()
        try:
            auth = None
            if self.transport == 'unix':
                info = self.address.lstat()
                if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise HostUnavailable('Private host socket is unavailable')
                address = str(self.address); family = socket.AF_UNIX
            else:
                endpoint = ipc.read_endpoint(self.endpoint_path)
                address = ('127.0.0.1', endpoint['port']); auth = endpoint['token']; family = socket.AF_INET
            with socket.socket(family, socket.SOCK_STREAM) as connection:
                connection.settimeout(timeout); connection.connect(address)
                if self.transport == 'unix': ipc.peer(connection)
                ipc.send(connection, {'schema': ipc.SCHEMA, 'root_id': ipc.root_id(self.root),
                         'code_digest': self.digest, 'delegation': principal_request(p), 'auth':auth}, ipc.MAX_REQUEST)
                hello = ipc.receive(connection, ipc.MAX_RESPONSE)
                if not hello.get('ok'): raise HostUnavailable(hello.get('error', 'Host refused this client'))
                ipc.send(connection, {'method': method, 'args': args or {}}, ipc.MAX_REQUEST)
                result = ipc.receive(connection, ipc.MAX_RESPONSE)
                if not result.get('ok'): raise HostUnavailable(result.get('error', 'Host request failed'))
                return result['result']
        except (OSError, ipc.TransportError) as exc:
            raise HostUnavailable('Background service unavailable. A sent request may have completed; inspect its work record before retrying. Use Service to reconnect.') from exc

    def dispatch(self, operation, params=None, principal=None):
        try:
            # Reviewed bulk I/O can outlast an ordinary UI read. Keep the same
            # authenticated transport and unknown-outcome rule; never auto retry.
            bulk = operation in ('imports.preview','imports.accept') or isinstance(operation,str) and operation.startswith(('changes.','workers.','work.','exchange.','releases.','deployment.'))
            return self.rpc('dispatch', {'operation': operation, 'params': {} if params is None else params}, principal or Principal('anonymous'), timeout=600 if bulk else 35)
        except HostUnavailable as exc:
            return {'ok': False, 'error': {'code': 'HOST_UNAVAILABLE', 'message': str(exc)},
                    'operation': operation, 'outcome': 'UNKNOWN_IF_SENT', 'automatic_retry': False}

    def save(self, *args, **kwargs):
        raise HostUnavailable('Job and engineering-record writes belong to the background service')

    def launch(self, *args, **kwargs):
        raise HostUnavailable('Job launch belongs to the background service')

    def submit(self, args, principal):
        reply = self.dispatch('jobs.submit', args, principal)
        if not reply['ok']: raise HostUnavailable(reply['error']['message'])
        return reply['result']

    def run_job(self, *args, **kwargs):
        raise HostUnavailable('Job execution belongs to a Kernel worker')

    def recover_interrupted(self):
        result = self.dispatch('jobs.recover', {}, operator())
        if not result['ok']: raise HostUnavailable(result['error']['message'])
        return result['result']


def ensure(root, timeout=10):
    """Initial attach / explicit reconnect only. Never replay a pending request."""
    for pid, previous in list(_OWNED.items()):
        if previous.poll() is not None:
            previous.wait(); _OWNED.pop(pid,None)
    client = HostClient(root)
    try:
        client.rpc('status', timeout=1)
        return client
    except HostUnavailable as exc:
        # An existing live socket with incompatible code must not be displaced.
        if 'edition differs' in str(exc): raise
    state = client.state
    state.mkdir(mode=0o700, exist_ok=True)
    info = state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise HostUnavailable('Private project state is unavailable')
    # Older desktops could create this parent with the account's ordinary
    # umask. Tighten only this owned directory; never widen source permissions.
    if stat.S_IMODE(info.st_mode) & 0o077: state.chmod(0o700)
    directory = ipc.private_directory(state / 'service')
    log_path = directory / 'host.log'
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as log:
        # Keep service startup diagnostics bounded across repeated starts.
        if os.fstat(log.fileno()).st_size > 1024 * 1024:
            log.truncate(0)
        from .locations import child_env
        env = {**child_env(client.root), 'PYTHONUNBUFFERED': '1'}
        env.pop('ARC_LEDGER_EMBEDDED', None)
        env.pop('INVOCATION_ID', None)
        env.pop('ARC_LEDGER_SUPERVISION', None)
        process = subprocess.Popen([sys.executable, '-m', 'workbench.host_service', '--root', str(client.root)],
                                   cwd=client.root, env=env, start_new_session=True,
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    _OWNED[process.pid] = process
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            client.rpc('status', timeout=.5)
            return client
        except HostUnavailable as exc:
            if 'edition differs' in str(exc): raise
            if process.poll() == 74:
                # The service refused unsafe storage; its one-line reason is the latest log line.
                with open(log_path, 'rb') as log:
                    log.seek(max(0, os.fstat(log.fileno()).st_size - 2048))
                    reason = log.read().decode(errors='replace').strip().splitlines()[-1:]
                raise HostUnavailable(reason[0] if reason else 'Background service refused unsafe storage') from exc
            if process.poll() not in (None, 73):
                raise HostUnavailable('Background service did not start. Inspect its private host log.') from exc
        time.sleep(.04)
    raise HostUnavailable('Background service did not become ready; inspect its private host log.')


def engineering(root):
    if os.environ.get('ARC_LEDGER_EMBEDDED') == '1' or not sys.platform.startswith('linux'):
        return Kernel(root)
    key = str(Path(root).resolve())
    with _LOCK:
        if key not in _CLIENTS:
            _CLIENTS[key] = ensure(root)
        return _CLIENTS[key]


def reconnect(root):
    with _LOCK:
        client = ensure(root)
        _CLIENTS[str(client.root)] = client
        return client
