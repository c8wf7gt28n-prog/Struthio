"""Shared edit records, streamed protected objects and descriptor-relative Linux I/O.

The existing copies table owns source/work addresses. These tables extend it;
protected bytes use the existing copies object store. No new scheduler or grants.
"""
from __future__ import annotations
import contextlib
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import unicodedata
import uuid
from . import project_desk as records, working_copies as copies, files_service

MAX_FILE = 256 * 1024 * 1024
MIGRATIONS = [(1, (
    'CREATE TABLE edit_records(id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, copy TEXT, payload TEXT NOT NULL, digest TEXT NOT NULL)',
    'CREATE INDEX edit_owner ON edit_records(owner,kind,copy)',
    'CREATE TABLE edit_accepts(preview TEXT PRIMARY KEY, copy TEXT NOT NULL, work TEXT NOT NULL, state TEXT NOT NULL)',
    'CREATE TABLE edit_applications(proposal TEXT PRIMARY KEY, commit_id TEXT NOT NULL)',
    'CREATE TABLE edit_journal(seq INTEGER PRIMARY KEY AUTOINCREMENT, commit_id TEXT NOT NULL, actor TEXT NOT NULL, stage TEXT NOT NULL, payload TEXT NOT NULL, at REAL NOT NULL)',
))]


def ensure(db):
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS edit_migrations(version INTEGER PRIMARY KEY,digest TEXT NOT NULL,applied REAL NOT NULL)')
    applied = dict(db.execute('SELECT version,digest FROM edit_migrations'))
    known = {version: records.digest(sql) for version, sql in MIGRATIONS}
    if sorted(applied) != list(range(1, len(applied) + 1)) or any(known.get(v) != sha for v, sha in applied.items()):
        raise ValueError('EDIT_MIGRATION_UNSUPPORTED')
    for version, statements in MIGRATIONS:
        if version in applied: continue
        for statement in statements: db.execute(statement)
        db.execute('INSERT INTO edit_migrations VALUES(?,?,?)', (version, known[version], time.time()))


def put(db, owner, kind, value, replace=False):
    raw = records.canonical(value)
    if len(raw.encode()) > 8 * 1024 * 1024: raise ValueError('EDIT_RECORD_LIMIT')
    if replace:
        changed = db.execute('UPDATE edit_records SET payload=?,digest=? WHERE id=? AND owner=? AND kind=?',
            (raw, records.digest(value), value['id'], owner, kind)).rowcount
        if changed != 1: raise ValueError('Edit record unavailable')
    else:
        db.execute('INSERT INTO edit_records VALUES(?,?,?,?,?,?)',
            (value['id'], owner, kind, value.get('copy'), raw, records.digest(value)))
    return json.loads(raw)


def get(db, owner, kind, ident):
    from .engineering_kernel import identifier
    identifier(ident)
    row = db.execute('SELECT payload,digest FROM edit_records WHERE id=? AND owner=? AND kind=?', (ident, owner, kind)).fetchone()
    if not row: raise ValueError('Edit record unavailable to this caller')
    value = json.loads(row[0])
    if records.digest(value) != row[1]: raise ValueError('EDIT_RECORD_DAMAGED')
    return value


def listing(db, owner, kind, copy=None, limit=100, offset=0):
    where = 'owner=? AND kind=?'; args = [owner, kind]
    if copy: where += ' AND copy=?'; args.append(copy)
    ids = list(db.execute('SELECT id FROM edit_records WHERE ' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?', (*args, limit, offset)))
    return [get(db, owner, kind, row[0]) for row in ids]


def relative(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 1000: raise ValueError('Expected a relative edit path')
    if text != unicodedata.normalize('NFC', text) or any(ord(c) < 32 for c in text) or '\\' in text or ':' in text:
        raise ValueError('Unsafe or non-normalized edit path')
    parts = text.split('/')
    if any(p in ('', '.', '..') or len(p) > 240 or p.endswith((' ', '.')) for p in parts): raise ValueError('Unsafe edit path')
    if any(re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in parts): raise ValueError('Reserved portable filename')
    return text


@contextlib.contextmanager
def directory(path):
    """Open every absolute path component without following a symbolic link."""
    path = Path(path)
    if os.name != 'posix' or not path.is_absolute(): raise ValueError('Edit filesystem operations require Linux absolute roots')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = next_fd
        yield fd
    finally: os.close(fd)


@contextlib.contextmanager
def parent(root, rel, create=False):
    relative(rel)
    with directory(root) as base:
        fd = os.dup(base)
        try:
            for part in rel.split('/')[:-1]:
                if create:
                    try: os.mkdir(part, 0o700, dir_fd=fd); os.fsync(fd)
                    except FileExistsError: pass
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd); fd = next_fd
            yield fd, rel.split('/')[-1]
        finally: os.close(fd)


def open_file(root, rel):
    with parent(root, rel) as (fd, name): return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)


def fingerprint_fd(fd, sink=None, maximum=MAX_FILE):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1: raise ValueError('Only ordinary unlinked files are supported')
    if before.st_size > maximum: raise ValueError('Edit file exceeds its byte limit')
    sha = hashlib.sha256(); size = 0
    while True:
        block = os.read(fd, 1048576)
        if not block: break
        size += len(block)
        if size > maximum: raise ValueError('Edit file grew beyond its byte limit')
        sha.update(block)
        if sink: sink.write(block)
    after = os.fstat(fd)
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or size != after.st_size: raise ValueError('File changed while being read')
    return {'sha256': sha.hexdigest(), 'bytes': size, 'mode': stat.S_IMODE(after.st_mode) & 0o777}


def inspect_file(root, rel, maximum=MAX_FILE):
    try: fd = open_file(root, rel)
    except FileNotFoundError: return None
    try: return fingerprint_fd(fd, maximum=maximum)
    finally: os.close(fd)


def read_bytes(root, rel, maximum=4194304):
    import io
    out = io.BytesIO(); fd = open_file(root, rel)
    try: value = fingerprint_fd(fd, out, maximum)
    finally: os.close(fd)
    return out.getvalue(), value


def publish_object(kernel, temp, sha):
    destination = copies.store(kernel) / sha
    os.chmod(temp, 0o400)
    try: os.link(temp, destination)
    except FileExistsError:
        if copies.sha_of(destination) != sha: raise ValueError('PROTECTED_OBJECT_DAMAGED')
    finally: Path(temp).unlink(missing_ok=True)
    with directory(destination.parent) as fd: os.fsync(fd)
    return sha


def keep_stream(kernel, stream, maximum=MAX_FILE):
    temp = copies.store(kernel) / ('.edit-' + uuid.uuid4().hex)
    sha = hashlib.sha256(); size = 0
    try:
        with temp.open('xb') as out:
            os.chmod(temp, 0o600)
            while True:
                block = stream.read(1048576)
                if not block: break
                size += len(block)
                if size > maximum: raise ValueError('Stream exceeds the reviewed file bound')
                sha.update(block); out.write(block)
            out.flush(); os.fsync(out.fileno())
        return publish_object(kernel, temp, sha.hexdigest()), size
    finally: temp.unlink(missing_ok=True)


def keep_file(kernel, root, rel, maximum=MAX_FILE):
    temp = copies.store(kernel) / ('.edit-' + uuid.uuid4().hex)
    fd = open_file(root, rel)
    try:
        with temp.open('xb') as out:
            os.chmod(temp, 0o600); value = fingerprint_fd(fd, out, maximum)
            out.flush(); os.fsync(out.fileno())
        publish_object(kernel, temp, value['sha256']); return value
    finally: os.close(fd); temp.unlink(missing_ok=True)


def keep_bytes(kernel, raw):
    import io
    return keep_stream(kernel, io.BytesIO(raw))[0]


def object_bytes(kernel, sha, maximum=8 * 1024 * 1024):
    if not re.fullmatch('[0-9a-f]{64}', sha): raise ValueError('Invalid object identity')
    path = copies.store(kernel) / sha
    if path.stat().st_size > maximum: raise ValueError('Adapter input exceeds its byte limit')
    return copies.object_bytes(kernel, sha)


def rename_linux(fd, source, target, exchange=False):
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None: raise ValueError('Linux renameat2 is required; no unsafe fallback')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(fd, os.fsencode(source), fd, os.fsencode(target), 2 if exchange else 1) != 0:
        code = ctypes.get_errno(); raise OSError(code, os.strerror(code))
    os.fsync(fd)


def workspace(kernel, ident, principal, check_root=True):
    with copies.opened(kernel) as db:
        meta = get(db, principal.identity, 'workspace', ident)
        row = dict(copies.the_copy(db, ident))
    if row['owner'] != principal.identity or row['state'] != 'WORKING': raise ValueError('Working copy unavailable to this caller')
    relative(row['work'])
    root = files_service.root(kernel, create=False) / row['work']
    if check_root:
        with directory(root): pass
    return meta, row, root


def is_profiled(db, ident):
    table = db.execute("SELECT 1 FROM sqlite_master WHERE name='edit_records'").fetchone()
    return bool(table and db.execute("SELECT 1 FROM edit_records WHERE id=? AND kind='workspace'", (ident,)).fetchone())


@contextlib.contextmanager
def lock(kernel, ident):
    import fcntl
    from .engineering_kernel import identifier
    identifier(ident)
    folder = kernel.state / 'edits' / 'locks'; folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (folder / ident).open('a+b') as stream:
        os.chmod(folder / ident, 0o600)
        try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('Another Graphite operation is changing this working copy') from None
        try: yield
        finally: fcntl.flock(stream, fcntl.LOCK_UN)
