"""Dependency-free verification of the installed runtime payload, not publisher authentication."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def relative(name):
    if not isinstance(name, str) or not name or any(x in name for x in ('\\', '\x00', ':')):
        raise ValueError('Invalid manifest path')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')):
        raise ValueError('Invalid manifest path')
    return p


def package_parts(root):
    """1.1 PK1: {payload name: package} for files that another Debian package installs into the same program folder,
    read from PACKAGE_PARTS.json (written by tools/build_deb.sh, not listed in the manifest); {} for a folder install."""
    path = Path(root) / 'PACKAGE_PARTS.json'
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024: return {}
        record = json.loads(path.read_text(encoding='utf-8'))
        return {relative(name).as_posix(): package for package, names in record.get('parts', {}).items()
                for name in names if isinstance(package, str)}
    except (OSError, ValueError, AttributeError, TypeError):
        return {}


def verify(root):
    root = Path(root).resolve()
    manifest_path = root / 'MANIFEST.json'
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Invalid package manifest')
    record = json.loads(manifest_path.read_text())
    files = record.get('files')
    if not isinstance(files, dict) or not files or len(files) > 20000:
        raise ValueError('Invalid package file inventory')
    problems = []
    parts = package_parts(root)  # 1.1 PK1
    absent = {}
    for name, row in files.items():
        path = root.joinpath(*relative(name).parts)
        if any(p.is_symlink() for p in (path, *path.parents)):
            problems.append(name + ': linked path'); continue
        if not path.is_file():
            if name in parts: absent.setdefault(parts[name], []).append(name); continue  # 1.1 PK1: maybe a part not installed
            problems.append(name + ': missing'); continue
        if path.stat().st_size != row.get('bytes') or sha(path) != row.get('sha256'):
            problems.append(name + ': changed')
    not_installed = []  # 1.1 PK1: a part whose files are all absent is not installed; some absent is damage
    for package, names in sorted(absent.items()):
        if len(names) == sum(1 for owner in parts.values() if owner == package): not_installed.append(package)
        else: problems += [name + ': missing' for name in names]
    return {'state': 'VERIFIED' if not problems else 'DAMAGED', 'files': len(files),
            'version': record.get('version'), 'problems': problems, 'parts_not_installed': not_installed,
            'meaning': 'Payload matches the local manifest; this does not authenticate its publisher.'}
