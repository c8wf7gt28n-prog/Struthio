"""Graphite 1.0 F2b · Reads beside her writes: the window's reads never wait for her work.

PLAN_1.0.md, F2b: "give read-only operations a shared read path (WAL readers beside the one writer) if that is safe for
the journal."

Why the window still waited after F2. database_guard lets one Kernel connection of a workspace in at a time, across
threads and processes, readers included. So a read the window made on its own thread (the board's rebuild on a tile
click, the Field on its open, the head's control) waited while her step wrote its journal, and waited as long again while
one of the floor's own readers held the workspace. The workspace's database is in WAL mode, where SQLite itself lets any
number of readers read a committed snapshot beside the one writer, neither waiting for the other.

What is here.

  reading()          a context: while it is open, this thread's Kernel connections (Kernel.db) read beside the writer:
                     no guard, a connection SQLite keeps read-only (PRAGMA query_only), one snapshot for the connection's
                     whole block (BEGIN). A connection this thread opens while it already holds the guard (inside a
                     writer's block) is still the writer's, as before.
  suspended()        a context inside reading(): this thread's connections take the guard again (a Kernel's own schema
                     check, which may make its tables).
  first(fn, ...)     fn() read beside the writer. If anything in it tried to write (SQLite refused it: a table made on
                     first use, a mark kept while reading), what it read is put aside and fn() runs once more the old way,
                     under the guard. A caller always gets either a pure read or exactly what it got before.
  operation(op)      whether a Kernel operation is read beside the writer: an observer (activity.OBSERVER_OPERATIONS)
                     whose scope is read. Kernel.dispatch runs such an operation's handler through first(); the Ledger
                     service lets it past its dispatch lock (host_service), so both modes of the window read beside her.

Why the journal stays safe (K1: a step's "sent" and "confirmed" records; resume without doing anything twice).
  - A reader never writes. Its connection is query_only, so SQLite refuses any write in it (SQLITE_READONLY), and a
    "BEGIN IMMEDIATE" or "BEGIN EXCLUSIVE" in it is refused here before SQLite sees it; first() then runs the whole read
    again under the guard. The journal's records are written only under the guard, as before.
  - Writers are unchanged: one at a time under the guard, across threads and processes (the Ledger service and the
    window); each transaction is atomic and commits or not as a whole.
  - A reader sees only committed transactions, all of one snapshot for its block: a step's "sent" without its
    "confirmed" only while that is how the journal stands.
  - Nothing that decides reads beside: resume, a step's verification, a grant's check and every press are write
    operations (their scope is not read) and read under the guard inside their own work, so what they decide on is what
    the guard gave them before. The activity journal was already read beside the writer (activity._read, mode=ro).
  - A database not in WAL mode (rollback journal) is read the old way.

GRAPHITE_READ_BESIDE=0 turns it off: every connection takes the guard again, as in 0.8.7 and F2.
"""
from __future__ import annotations

import contextlib
import os
import sqlite3
import threading
from pathlib import Path

_local = threading.local()
READONLY = sqlite3.SQLITE_READONLY


def enabled():
    return os.environ.get('GRAPHITE_READ_BESIDE', '').strip() != '0'


class _State:
    __slots__ = ('refused',)

    def __init__(self):
        self.refused = False


def _refuse():
    state = getattr(_local, 'state', None)
    if state is not None:state.refused = True


def _checked(run, sql, *args):
    """Run a statement on a reader; a write SQLite refuses (or a writer's BEGIN) marks this reading as refused."""
    head = sql.lstrip()[:24].upper() if isinstance(sql, str) else ''
    if head.startswith('BEGIN') and ('IMMEDIATE' in head or 'EXCLUSIVE' in head):
        _refuse()
        raise sqlite3.OperationalError('attempt to write a readonly database')
    try:
        return run(sql, *args)
    except sqlite3.OperationalError as exc:
        if (getattr(exc, 'sqlite_errorcode', 0) or 0) & 0xff == READONLY or 'readonly database' in str(exc):_refuse()
        raise


class _ReaderCursor(sqlite3.Cursor):
    def execute(self, sql, *args):
        return _checked(super().execute, sql, *args)

    def executemany(self, sql, *args):
        return _checked(super().executemany, sql, *args)

    def executescript(self, script):
        return _checked(super().executescript, script)


class _Reader(sqlite3.Connection):
    """A Kernel connection that reads beside the writer: every statement is watched for a write SQLite refuses."""

    def cursor(self, factory=None):
        return super().cursor(factory or _ReaderCursor)

    def execute(self, sql, *args):
        head = sql.lstrip()[:8].upper() if isinstance(sql, str) else ''
        if head.startswith('BEGIN') and self.in_transaction and 'IMMEDIATE' not in sql.upper() and 'EXCLUSIVE' not in sql.upper():
            return super().execute('SELECT 1 WHERE 0')      # a reader's own BEGIN: already in one snapshot
        return _checked(super().execute, sql, *args)

    def executemany(self, sql, *args):
        return _checked(super().executemany, sql, *args)

    def executescript(self, script):
        return _checked(super().executescript, script)


@contextlib.contextmanager
def reading():
    """This thread's Kernel connections read beside the writer while this is open (nested: the outer reading's state)."""
    depth = getattr(_local, 'depth', 0)
    outer = getattr(_local, 'state', None)
    state = outer if outer is not None else _State()
    _local.depth = depth + 1;_local.state = state
    try:
        yield state
    finally:
        _local.depth = depth
        if outer is None:_local.state = None


@contextlib.contextmanager
def suspended():
    """Inside reading(): this thread's connections take the guard again until this closes."""
    depth = getattr(_local, 'depth', 0)
    _local.depth = 0
    try:
        yield
    finally:
        _local.depth = depth


def active():
    return bool(getattr(_local, 'depth', 0))


_names = {}


def _named(path):
    """The database's resolved path (database_guard's key) and its URI, worked out once per path: resolving walks every
    folder of the path, each a call to the system that gives up Python's lock, and the window's thread waits to take it back
    while other threads run Python."""
    raw = str(path)
    got = _names.get(raw)
    if got is None:
        key = str(Path(raw).resolve())
        got = _names[raw] = (key, Path(key).as_uri() + '?mode=rw')
    return got


def _file_id(key):
    st = os.stat(key)
    return st.st_dev, st.st_ino


def _kept_reader(key):
    """This thread's idle reader on this database, made ready for a new block, or None. Opening a connection costs its
    files and the whole schema read again (183 tables and indexes on Rail Demo); a reader kept open costs neither. It is
    dropped when the database file is not the one it opened (a database put back from elsewhere)."""
    kept = getattr(_local, 'kept', None)
    db = kept.pop(key, None) if kept else None
    if db is None:return None
    try:
        if db.in_transaction or _file_id(key) != db._f2b_file:raise sqlite3.OperationalError('not the same')
        db.row_factory = None;db.text_factory = str;db.isolation_level = ''      # what a block before may have set
        sqlite3.Connection.execute(db, 'BEGIN')
        return db
    except (OSError, sqlite3.Error):
        db.close();return None


def release(db):
    """Kernel.db, at the end of a block read beside: the reader is kept open for this thread's next block (one per
    database; a second one is closed)."""
    kept = getattr(_local, 'kept', None)
    if kept is None:kept = _local.kept = {}
    key = getattr(db, '_f2b_key', None)
    try:
        if key is None or key in kept or db.in_transaction or not enabled():
            db.close();return
    except sqlite3.Error:
        return
    kept[key] = db


def beside(path):
    """Kernel.db: a read-only connection beside the writer on this database, in one snapshot, or None (the old way): not
    reading, turned off, this thread already holds the guard (a writer's block), not WAL, or it cannot be opened so."""
    if not getattr(_local, 'depth', 0) or not enabled():return None
    try:
        key, uri = _named(path)
        from . import database_guard
        if key in (getattr(database_guard._local, 'held', None) or {}):return None
        again = _kept_reader(key)
        if again is not None:return again
        db = sqlite3.connect(uri, uri=True, timeout=10, factory=_Reader)      # mode=rw: never makes a missing database
        db._f2b_key = key;db._f2b_file = _file_id(key)
    except (OSError, ValueError, sqlite3.Error):
        return None
    try:
        db.execute('PRAGMA query_only=1')
        mode = db.execute('PRAGMA journal_mode').fetchone()
        if not mode or str(mode[0]).lower() != 'wal':
            db.close();return None
        sqlite3.Connection.execute(db, 'BEGIN')      # one snapshot for the block (it starts at the first read)
        return db
    except sqlite3.Error:
        db.close();return None


MISSING = object()
_marks = {}


def mark(root):
    """floor.head's change mark (the activity journal's last number) on this thread's kept reader: no walk of the path and
    no schema read each time (the head's control, the timeline and her column ask it several times a second). MISSING when
    it cannot be read so (floor.head then reads it as before)."""
    if not enabled():return MISSING
    raw = str(root)
    path = _marks.get(raw)
    if path is None:path = _marks[raw] = Path(raw).resolve() / '.ledger' / 'engineering.sqlite3'
    with reading():
        db = beside(path)
        if db is None:return MISSING
        try:
            with db:
                row = db.execute('SELECT MAX(seq) FROM activity_journal').fetchone()
        except sqlite3.Error:
            db.close();return MISSING
        release(db)
    return int(row[0] or 0)


def first(fn, *args, **kwargs):
    """fn(*args) read beside the writer; when something in it tried to write, run again the old way (under the guard)."""
    if not enabled():return fn(*args, **kwargs)
    with reading() as state:
        before = state.refused;state.refused = False
        error = None;result = None
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - raised again below unless the read is made again the old way
            error = exc
        wanted = state.refused
        state.refused = before
    if wanted:
        with suspended():
            return fn(*args, **kwargs)
    if error is not None:raise error
    return result


def worker_kernel(kernel):
    """The Kernel a floor worker uses in place of the window's: the Ledger service's client as it is (each call its own
    connection to the service), else the worker thread's own Kernel on the same workspace (floor.kernel_for)."""
    if kernel is None or getattr(kernel, 'is_host_client', False):return kernel
    from . import floor
    return floor.kernel_for(kernel.root)


def off_thread(kernel, fn, key, done=None):
    """A write the window made on its own timer (her awareness's cursor, the desktop's receipts) made on one of the floor's
    workers instead: fn(worker's kernel) there, one at a time per key (the latest kept), done(result, error) back on the
    window's thread. With GRAPHITE_READ_BESIDE=0 it is made at once on the window's thread, as before."""
    if not enabled():
        try:result = fn(kernel);error = None
        except Exception as exc:  # noqa: BLE001 - said to done(), as a worker's would be
            result = None;error = exc
        if done is not None:done(result, error)
        return
    from . import floor
    floor.submit(lambda: fn(worker_kernel(kernel)), done, key=('f2b', key))


def desk_later(page, kernel, draw):
    """The Field shown again (field_page.show_field, not forced): what it showed stays in front while a new reading of the
    desk (board_model.read_desk, the same reads) is made on a floor worker; draw(reading) runs on the window's thread when
    it lands. False when nothing is shown yet or this is turned off: the first reading is made at once, as before. A forced
    refresh (after an act of the owner's, R) is never later: its caller reads what it changed right after."""
    view = getattr(page, 'view', None)
    field = getattr(view, 'field', None)
    if not enabled() or field is None or not getattr(field, 'objects', None):return False
    from . import board_model, floor
    from .engineering_kernel import operator
    skip = set(getattr(page, 'unread', ()) or ())

    def work():
        return board_model.read_desk(worker_kernel(kernel), operator(), skip=skip)

    def landed(result, error):
        if error is not None or result is None or getattr(getattr(page, 'host', None), '_closing', False):return
        reader = result[1]
        if getattr(reader, 'kernel', None) is not None:reader.kernel = kernel      # what the board asks it later, on the window's Kernel
        draw(result)
    floor.submit(work, landed, key=('f2b-desk', id(page)))
    return True


def prefetch_desk(host):
    """A window that did not open on the Field (Home first): the desk's first reading is made on a floor worker as soon as
    the window is up, kept with the workspace's change mark, and taken by the Field when it is first shown (desk_kept)."""
    if not enabled() or getattr(host, 'field_page', None) is not None:return
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    root = getattr(kernel, 'root', None) if kernel is not None else None
    if root is None:return
    from . import board_model, floor
    from .engineering_kernel import operator

    def work():
        mark = floor.head(root)
        return mark, board_model.read_desk(worker_kernel(kernel), operator())

    def landed(result, error):
        if error is None and result is not None and getattr(host, 'field_page', None) is None:host._f2b_desk = result
    floor.submit(work, landed, key=('f2b-prefetch', id(host)))


def desk_kept(host, kernel):
    """The reading prefetch_desk kept (taken once), and whether the workspace changed since it was made; (None, False) when
    there is none."""
    kept = getattr(host, '_f2b_desk', None)
    if kept is None:return None, False
    host._f2b_desk = None
    from . import floor
    mark, reading = kept
    reader = reading[1]
    if getattr(reader, 'kernel', None) is not None:reader.kernel = kernel
    now = floor.head(getattr(kernel, 'root', None) or getattr(host, 'root', ''))
    return reading, (mark is None or now is None or now != mark)


def operation(op):
    """Whether Kernel.dispatch reads this operation beside the writer: an observer whose scope is read."""
    if not enabled():return False
    from .activity import OBSERVER_OPERATIONS
    if op not in OBSERVER_OPERATIONS:return False
    from .engineering_kernel import CAPABILITIES
    return CAPABILITIES.get(op) == 'read'
