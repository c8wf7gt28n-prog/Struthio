"""Consistent backup, verification and restore of Ledger's private state.

  python3 -m workbench.state_backup create  [--root FOLDER] [--out NEW_FOLDER] [--include-models]
  python3 -m workbench.state_backup verify  BACKUP_FOLDER
  python3 -m workbench.state_backup restore BACKUP_FOLDER [--root FOLDER]

Private state is the project's .ledger folder and the profile folder (Catalog,
notes, settings). Ledger must be closed: the background service's own lock is
held for the whole operation, so it cannot start part-way. SQLite databases are
copied with SQLite's online backup and integrity-checked, never by copying a
live file without its -wal/-shm. Restore verifies the backup first and moves the
current state aside; nothing is deleted. Rebuildable data is not copied: the
extracted inference runtime, model-worker scratch and (unless asked) managed
copies of model weights.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import sys
from . import locations

SCHEMA = 'arc.ledger-state-backup/1'
SQLITE_MAGIC = b'SQLite format 3\x00'
SIDE_FILES = ('-wal', '-shm', '-journal')
SKIP = {'ledger': ('service', 'brain'), 'profile': ('runtimes',)}
MODELS = 'stacy/models'


class StateBusy(RuntimeError):
    pass


def config_dir():
    from .session import config_dir as profile
    return profile()


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while chunk := stream.read(1 << 20): h.update(chunk)
    return h.hexdigest()


@contextmanager
def closed_ledger(state):
    """Hold the coordinator's lock; refuse while a service or desktop is running."""
    service = Path(state) / 'service'
    service.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(service / 'coordinator.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    agenda_fd=None
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise StateBusy('Graphite\'s background service is running. Quit Graphite, then run: '
                            'python3 -m workbench.host_cli stop') from None
        for lease in (Path(state) / 'desktops').glob('*.json'):
            try: os.kill(json.loads(lease.read_text())['pid'], 0)
            except ProcessLookupError: continue
            except (OSError, ValueError, KeyError): pass
            raise StateBusy('A Graphite desktop window is open. Close it first.')
        agenda_fd=os.open(Path(state)/'agenda-run.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:fcntl.flock(agenda_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise StateBusy('A continuing Agenda step is running. Stop work and close Graphite first.') from None
        database=Path(state)/'engineering.sqlite3'
        if database.is_file():
            conn=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='worker_runs'").fetchone() and conn.execute("SELECT 1 FROM worker_runs WHERE state IN ('STARTING','RUNNING','CLEANUP_REQUIRED') LIMIT 1").fetchone():
                    raise StateBusy('A protected worker needs stopping/reconciliation before backup.')
            finally:conn.close()
        yield
    finally:
        if agenda_fd is not None:os.close(agenda_fd)
        os.close(fd)


def members(area, base, include_models):
    if not base.is_dir(): return
    for path in sorted(base.rglob('*')):
        relative = path.relative_to(base)
        parts = relative.parts
        if path.is_symlink(): raise ValueError('Linked entry in private state: ' + str(path))
        if not path.is_file(): continue
        if parts[0] in SKIP[area] or '__pycache__' in parts or parts[-1].startswith('.storage-check-'): continue
        if area == 'profile' and not include_models and relative.as_posix().startswith(MODELS + '/'): continue
        if parts[-1].endswith(SIDE_FILES) and path.with_name(parts[-1].rsplit('-', 1)[0]).is_file(): continue
        yield relative, path


def is_sqlite(path):
    with open(path, 'rb') as stream: return stream.read(16) == SQLITE_MAGIC


def copy_database(source, target):
    # The backup API reads committed pages, including those still in the WAL.
    src = sqlite3.connect(source, timeout=10); dst = sqlite3.connect(target)
    try:
        src.backup(dst)
        # A backup is one self-contained file; Ledger re-enables WAL when it next opens it.
        dst.execute('PRAGMA journal_mode=DELETE')
        result = dst.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        dst.close(); src.close()
    if result != 'ok': raise ValueError('Database copy failed integrity check: ' + str(source))


def integrity(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try: return db.execute('PRAGMA integrity_check').fetchone()[0]
    finally: db.close()


def state_areas(root):
    return {'ledger': Path(root).resolve() / '.ledger', 'profile': config_dir().resolve()}


def create(root, out=None, include_models=False):
    root = Path(root).resolve(); sources = state_areas(root)
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    out = Path(out) if out else Path.home() / 'Ledger-backups' / stamp
    if out.exists(): raise ValueError('Choose a new backup folder; existing files are preserved: ' + str(out))
    files = []
    with closed_ledger(sources['ledger']):
        out.parent.mkdir(parents=True, exist_ok=True); out.mkdir(mode=0o700)
        for area, base in sources.items():
            for relative, path in members(area, base, include_models):
                target = out / area / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                if is_sqlite(path): copy_database(path, target); kind = 'sqlite'
                else: shutil.copyfile(path, target); kind = 'file'
                target.chmod(0o600)
                files.append({'area': area, 'path': relative.as_posix(), 'kind': kind,
                              'bytes': target.stat().st_size, 'sha256': sha(target)})
    edition = None
    try: edition = json.loads((locations.program(root) / 'MANIFEST.json').read_text()).get('edition')
    except (OSError, ValueError): pass
    record = {'schema': SCHEMA, 'created': stamp, 'edition': edition, 'sqlite': sqlite3.sqlite_version,
              'sources': {k: str(v) for k, v in sources.items()}, 'models_included': include_models, 'files': files}
    (out / 'BACKUP.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
    return {**verify(out), 'backup': str(out)}


def load(backup):
    record = json.loads((Path(backup) / 'BACKUP.json').read_text())
    if record.get('schema') != SCHEMA: raise ValueError('Not a Graphite state backup')
    for row in record['files']:
        pure = PurePosixPath(row['path'])
        if row['area'] not in SKIP or pure.is_absolute() or '..' in pure.parts: raise ValueError('Invalid backup entry')
    return record


def verify(backup):
    backup = Path(backup); record = load(backup); problems = []
    for row in record['files']:
        path = backup / row['area'] / row['path']
        if not path.is_file() or path.is_symlink() or sha(path) != row['sha256']: problems.append('changed or missing: ' + row['area'] + '/' + row['path']); continue
        if row['kind'] == 'sqlite' and integrity(path) != 'ok': problems.append('integrity failed: ' + row['area'] + '/' + row['path'])
    if problems: raise ValueError('BACKUP_NOT_VALID: ' + '; '.join(problems[:5]))
    return {'state': 'VERIFIED', 'files': len(record['files']),
            'databases': sum(r['kind'] == 'sqlite' for r in record['files']),
            'bytes': sum(r['bytes'] for r in record['files']), 'created': record['created']}


def restore(backup, root, areas=('ledger', 'profile')):
    backup = Path(backup); record = load(backup); checked = verify(backup)
    every = state_areas(root); targets = {k: v for k, v in every.items() if k in areas}
    stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'); moved = {}
    with closed_ledger(every['ledger']):
        for area, target in targets.items():
            if target.exists():
                aside = target.with_name(target.name + '.before-restore-' + stamp)
                target.rename(aside); moved[area] = str(aside)
            target.mkdir(mode=0o700, parents=True)
        # Re-take the service lock inside the new state before copying anything in.
        with closed_ledger(every['ledger']):
            for row in (r for r in record['files'] if r['area'] in targets):
                destination = targets[row['area']] / row['path']
                destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                shutil.copyfile(backup / row['area'] / row['path'], destination); destination.chmod(0o600)
                if sha(destination) != row['sha256']: raise ValueError('Restore readback failed: ' + row['path'])
    return {'state': 'RESTORED', 'files': sum(r['area'] in targets for r in record['files']), 'areas': sorted(targets), 'previous_state_kept_at': moved}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('create'); c.add_argument('--root'); c.add_argument('--out'); c.add_argument('--include-models', action='store_true')
    v = sub.add_parser('verify'); v.add_argument('backup')
    r = sub.add_parser('restore'); r.add_argument('backup'); r.add_argument('--root')
    args = parser.parse_args(argv)
    if getattr(args, 'root', None) is None and args.command != 'verify':
        from .locations import default_root
        args.root = default_root()
    try:
        result = (create(args.root, args.out, args.include_models) if args.command == 'create' else
                  verify(args.backup) if args.command == 'verify' else restore(args.backup, args.root))
    except (StateBusy, ValueError, OSError, sqlite3.Error) as exc:
        print('Graphite state backup: ' + str(exc), file=sys.stderr); return 1
    print(json.dumps(result, indent=2)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
