"""Bounded local host transport, independent of Qt and Ledger's authority.

Linux peer credentials and private pathname sockets authenticate an OS account.
They do not isolate that account from its own programs. No pickle or SQL protocol.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import socket
import stat
import struct

SCHEMA = 'arc.ledger-host/1'
MAX_REQUEST = 2 * 1024 * 1024
MAX_RESPONSE = 16 * 1024 * 1024


class TransportError(ValueError):
    pass


def root_id(root):
    return hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:24]


def private_directory(path):
    """Create one owned directory; reject links and permissive existing entries."""
    path = Path(path)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise TransportError('Private host directory is unavailable')
    return path


def socket_path(root):
    # Deliberately short: Linux sockaddr_un has a 108-byte pathname limit.
    # A root-specific persistent flock below .ledger arbitrates all runtimes.
    base = private_directory(Path('/tmp') / ('arc-ledger-' + str(os.getuid())))
    return private_directory(base / root_id(root)) / 'host.sock'


def transport():
    value = os.environ.get('ARC_LEDGER_HOST_TRANSPORT', 'unix')
    if value not in ('unix', 'loopback'):
        raise TransportError('Unsupported host transport; select unix or explicit loopback')
    return value


def read_endpoint(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 4096):
            raise TransportError('Private loopback endpoint is unavailable')
        raw = os.read(fd, 4097)
    finally: os.close(fd)
    try: value = json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError) as exc: raise TransportError('Invalid loopback endpoint') from exc
    if (set(value) != {'port', 'token'} or type(value['port']) is not int
            or not 1 <= value['port'] <= 65535 or not isinstance(value['token'], str)
            or len(value['token']) != 64):
        raise TransportError('Invalid loopback endpoint')
    return value


def peer(connection):
    pid, uid, gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    if uid != os.getuid():
        raise TransportError('Host socket belongs to another OS account')
    return pid, uid, gid


def _exact(connection, count):
    parts = bytearray()
    while len(parts) < count:
        block = connection.recv(count - len(parts))
        if not block:
            raise TransportError('Host disconnected; the request outcome may be unknown')
        parts.extend(block)
    return bytes(parts)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise TransportError('Duplicate protocol member')
        result[key] = value
    return result


def receive(connection, limit=MAX_REQUEST):
    size = struct.unpack('!I', _exact(connection, 4))[0]
    if not 1 <= size <= limit:
        raise TransportError('Host message exceeds its size limit')
    try:
        value = json.loads(_exact(connection, size), object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(TransportError('Non-finite protocol number')))
        def finite(obj, depth=0):
            if depth > 64:
                raise TransportError('Host message is too deeply nested')
            if isinstance(obj, float) and not math.isfinite(obj):
                raise TransportError('Non-finite protocol number')
            for child in obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else ():
                finite(child, depth + 1)
        finite(value)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise TransportError('Invalid host message') from exc
    if not isinstance(value, dict):
        raise TransportError('Host message must be an object')
    return value


def send(connection, value, limit=MAX_RESPONSE):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if not 1 <= len(raw) <= limit:
        raise TransportError('Host message exceeds its size limit')
    connection.sendall(struct.pack('!I', len(raw)) + raw)


def delegation(value, ceiling):
    """Validate an authenticated local owner's request for a narrower grant.

    The coordinator issues the resulting Principal. Kernel dispatch accepts only
    that issued Principal, never a principal object supplied with an operation.
    Remote phone grants use the separate existing pairing authority.
    """
    expected = {'identity', 'scopes', 'paths', 'tools', 'mode'}
    if not isinstance(value, dict) or set(value) != expected:
        raise TransportError('Invalid local delegation')
    identity = value['identity']
    if (not isinstance(identity, str) or not 1 <= len(identity) <= 80
            or any(not (c.isalnum() or c in '-_.:') for c in identity)):
        raise TransportError('Invalid local caller label')
    if value['mode'] not in ('Engineer', 'Tutor', 'Autonomous'):
        raise TransportError('Unsupported caller mode')
    for key, max_items in (('scopes', 5), ('paths', 50), ('tools', 512)):
        items = value[key]
        if not isinstance(items, list) or len(items) > max_items or any(not isinstance(x, str) for x in items):
            raise TransportError('Invalid local delegation bounds')
    if not set(value['scopes']) <= {'read', 'execute', 'candidate', 'approve', 'repair.review'}:
        raise TransportError('Unknown local scope')
    if 'repair.review' in value['scopes'] and set(value['scopes']) != {'read', 'repair.review'}:
        raise TransportError('Repair review cannot acquire execution or approval')
    if not set(value['tools']) <= set(ceiling['tools']):
        raise TransportError('Tool exceeds local delegation ceiling')
    for path in value['paths']:
        parts = PurePosixPath(path.rstrip('/')).parts
        if (not path or '\\' in path or ':' in path or '\x00' in path
                or path.startswith('/') or any(x in ('.', '..') or x.startswith('.') for x in path.rstrip('/').split('/'))
                or not parts or not any(path.startswith(p) if p.endswith('/') else path == p for p in ceiling['paths'])):
            raise TransportError('Source path exceeds local delegation ceiling')
    return {**value, 'scopes': frozenset(value['scopes']), 'paths': tuple(value['paths']), 'tools': tuple(value['tools'])}
