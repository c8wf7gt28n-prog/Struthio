"""Complete workspace plus profile snapshots. Restore always uses NEW destinations.

The older state_backup command remains available for private-state-only backups.
This format also keeps ordinary files, Arrived, and working copies. External
masters and externally registered model weights are not part of a workspace.
"""
from __future__ import annotations
from contextlib import ExitStack
import datetime
import ctypes
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
from . import locations, state_backup
from .release_integrity import relative, sha

SCHEMA = 'arc.workspace-backup/1'
LIMIT = 16 * 1024 * 1024


def safe_base(path):
    path = Path(path).expanduser().absolute()
    if Path(os.path.realpath(path)) != path:
        raise ValueError('Use a real path, without symbolic links: ' + str(path))
    return path


def fresh(path):
    path = safe_base(path)
    if path.exists():
        raise ValueError('Choose a NEW destination; existing files are preserved: ' + str(path))
    return path


def nested(path, base):
    return path == base or base in path.parents


def reason(area, name, include_models):
    parts = name.parts
    if area == 'workspace' and parts[:2] in (('.ledger', 'service'), ('.ledger', 'brain')):
        return 'transient worker or coordinator state'
    if area == 'profile' and parts[0] == 'runtimes':
        return 'rebuildable extracted runtime'
    if '__pycache__' in parts or '.venv' in parts or parts[-1].startswith('.storage-check-'):
        return 'rebuildable cache or environment'
    if not include_models and (name.suffix.lower() == '.gguf' or (area == 'profile' and parts[:2] == ('stacy', 'models'))):
        return 'model weights omitted by selected policy'
    return None


def entries(area, base, include_models, skipped, folders):
    if not base.exists():
        return
    for folder, directories, files in os.walk(base, followlinks=False):
        here = Path(folder)
        for name in list(directories):
            path = here / name; rel = path.relative_to(base)
            why = reason(area, rel, include_models)
            if path.is_symlink():
                raise ValueError('A linked folder cannot be snapshotted: ' + str(path))
            if why:
                skipped.append({'area': area, 'path': rel.as_posix(), 'reason': why}); directories.remove(name)
            else:
                folders.append({'area': area, 'path': rel.as_posix()})
        for name in sorted(files):
            path = here / name; rel = path.relative_to(base)
            if name.endswith(state_backup.SIDE_FILES) and path.with_name(name.rsplit('-', 1)[0]).is_file():
                continue  # Sidecars can vanish when a SQLite reader closes.
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Only ordinary files can be snapshotted: ' + str(path))
            why = reason(area, rel, include_models)
            if why:
                skipped.append({'area': area, 'path': rel.as_posix(), 'reason': why}); continue
            yield rel, path, info


def publish(source, destination):
    """Linux no-replace rename: a destination appearing after preflight is never overwritten."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise ValueError('This host has no qualified no-replace directory publication; not restored')
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    for folder, _, _ in os.walk(source, topdown=False):
        fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(destination))
    for parent in {Path(source).parent, Path(destination).parent}:
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)


def flush_file(path):
    with path.open('rb') as f: os.fsync(f.fileno())


def write_record(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    path.chmod(0o600)


def load(backup):
    backup = safe_base(backup); record_path = backup / 'BACKUP.json'
    if not record_path.is_file() or record_path.is_symlink() or record_path.stat().st_size > LIMIT:
        raise ValueError('Missing or oversized workspace backup manifest')
    record = json.loads(record_path.read_text())
    if record.get('schema') != SCHEMA or not isinstance(record.get('files'), list):
        raise ValueError('Not a complete workspace backup; private-state backups use workbench.state_backup')
    seen = set()
    for row in record.get('directories', []):
        if row.get('area') not in ('workspace', 'profile'):
            raise ValueError('Invalid directory area')
        relative(row.get('path'))
    for row in record['files']:
        if row.get('area') not in ('workspace', 'profile'):
            raise ValueError('Invalid backup area')
        name = relative(row.get('path')).as_posix(); key = (row['area'], name)
        if key in seen or row.get('kind') not in ('file', 'sqlite'):
            raise ValueError('Duplicate or invalid backup entry')
        seen.add(key)
        if type(row.get('bytes')) is not int or row['bytes'] < 0 or not isinstance(row.get('sha256'), str) or len(row['sha256']) != 64:
            raise ValueError('Invalid backup identity')
        if type(row.get('mode', 0o600)) is not int or not 0 <= row.get('mode', 0o600) <= 0o777:
            raise ValueError('Invalid backup permissions')
    return record


def verify(backup):
    backup = safe_base(backup); record = load(backup)
    for row in record.get('directories', []):
        path = backup / row['area'] / row['path']
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_dir():
            raise ValueError('Missing or linked backup directory: ' + row['path'])
    for row in record['files']:
        path = backup / row['area'] / row['path']
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise ValueError('Missing or linked backup member: ' + row['path'])
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('Changed backup member: ' + row['path'])
        if row['kind'] == 'sqlite' and state_backup.integrity(path) != 'ok':
            raise ValueError('Damaged database: ' + row['path'])
    return {'state': 'VERIFIED', 'schema': SCHEMA, 'files': len(record['files']),
            'databases': sum(r['kind'] == 'sqlite' for r in record['files']),
            'bytes': sum(r['bytes'] for r in record['files']), 'skipped': record.get('skipped', []),
            'external_originals_included': False}


def create(root, out, include_models=False):
    root = safe_base(root); profile = safe_base(state_backup.config_dir())
    if locations.contains_program(root) or not locations.marker(root):
        raise ValueError('Choose a separate Graphite workspace, such as ~/Concern/Office')
    if nested(profile, root) or nested(root, profile):
        raise ValueError('Keep the profile and workspace in separate folders before backing up')
    out = fresh(out)
    if any(nested(out, base) for base in (root, profile)):
        raise ValueError('The backup must be outside the workspace and profile')
    out.parent.mkdir(parents=True, exist_ok=True)
    with state_backup.closed_ledger(root / '.ledger'):
        with tempfile.TemporaryDirectory(prefix='.ledger-backup-', dir=out.parent) as temporary:
            stage = Path(temporary) / 'snapshot'; stage.mkdir(mode=0o700)
            rows, skipped, folders = [], [], []
            for area, base in (('workspace', root), ('profile', profile)):
                for rel, source, info in entries(area, base, include_models, skipped, folders):
                    target = stage / area / rel; target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                    kind = 'sqlite' if state_backup.is_sqlite(source) else 'file'
                    if kind == 'sqlite':
                        state_backup.copy_database(source, target)
                    else:
                        shutil.copyfile(source, target)
                        if sha(source) != sha(target):
                            raise ValueError('File changed during backup: ' + rel.as_posix())
                    flush_file(target)
                    target.chmod(0o600)
                    rows.append({'area': area, 'path': rel.as_posix(), 'bytes': target.stat().st_size,
                                 'sha256': sha(target), 'kind': kind, 'mode': stat.S_IMODE(info.st_mode) & 0o777})
            for row in folders:
                (stage / row['area'] / row['path']).mkdir(parents=True, mode=0o700, exist_ok=True)
            write_record(stage / 'BACKUP.json', {'schema': SCHEMA, 'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         'models_included': bool(include_models), 'files': rows, 'directories': folders, 'skipped': skipped,
                         'scope': 'Workspace and selected profile; external originals and external model files are excluded.'})
            checked = verify(stage)
            if out.exists():
                raise ValueError('The backup destination appeared during the snapshot; nothing replaced')
            publish(stage, out)
    return {**checked, 'backup': str(out)}


def restore(backup, root, profile=None):
    backup = safe_base(backup); checked = verify(backup); record = load(backup)
    root = fresh(root)
    if any(locations.contains_program(p) for p in root.parents) or root == Path.home() or root == Path('/'):
        raise ValueError('Restore into a NEW workspace outside the program')
    profile = fresh(profile if profile else root.with_name(root.name + '-profile'))
    if nested(root, profile) or nested(profile, root) or nested(backup, root) or nested(backup, profile):
        raise ValueError('Restore destinations must be separate from one another and the backup')
    root.parent.mkdir(parents=True, exist_ok=True); profile.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        stages = {}
        for area, destination in (('workspace', root), ('profile', profile)):
            directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='.ledger-restore-', dir=destination.parent)))
            stages[area] = directory / 'ready'; stages[area].mkdir(mode=0o700)
        for row in record['files']:
            path = stages[row['area']] / row['path']; path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            shutil.copyfile(backup / row['area'] / row['path'], path)
            if sha(path) != row['sha256']:
                raise ValueError('Restore readback failed: ' + row['path'])
            flush_file(path)
            path.chmod(row.get('mode', 0o600))
        for row in record.get('directories', []):
            (stages[row['area']] / row['path']).mkdir(parents=True, mode=0o700, exist_ok=True)
        if not locations.marker(stages['workspace']):
            raise ValueError('Backup does not contain a valid workspace marker')
        if root.exists() or profile.exists():
            raise ValueError('A restore destination appeared; nothing replaced')
        publish(stages['profile'], profile)
        try:
            if root.exists(): raise ValueError('Workspace destination appeared; nothing replaced')
            publish(stages['workspace'], root)
        except Exception as exc:
            raise ValueError('Workspace was not published. The restored profile is kept at ' + str(profile)) from exc
    return {'state': 'RESTORED', 'files': checked['files'], 'workspace': str(root), 'profile': str(profile),
            'existing_work_untouched': True, 'open': ['open', '--root', str(root), '--profile', str(profile)]}
