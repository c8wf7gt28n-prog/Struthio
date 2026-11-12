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
    for name, row in files.items():
        path = root.joinpath(*relative(name).parts)
        if any(p.is_symlink() for p in (path, *path.parents)):
            problems.append(name + ': linked path'); continue
        if not path.is_file():
            problems.append(name + ': missing'); continue
        if path.stat().st_size != row.get('bytes') or sha(path) != row.get('sha256'):
            problems.append(name + ': changed')
    return {'state': 'VERIFIED' if not problems else 'DAMAGED', 'files': len(files),
            'version': record.get('version'), 'problems': problems,
            'meaning': 'Payload matches the local manifest; this does not authenticate its publisher.'}
