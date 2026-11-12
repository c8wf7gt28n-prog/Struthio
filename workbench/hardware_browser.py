"""Scoped hardware file browsing shared by human navigation and automation.

Sources remain separate roots. Folder navigation cannot escape the selected
category, including through symlinks; it never changes project files.
"""
from pathlib import Path
from .hardware_nav import SKIP, group_files


def roots(root, device, category):
    root = Path(root).resolve()
    group = next(g for g in device.groups if g.title == category)
    found = []
    for rel in group.sources:
        path = root / rel
        if path.is_symlink():
            continue
        path = path.resolve()
        if path.is_relative_to(root) and path.exists() and path not in found:
            found.append(path)
    return found


def entries(root, device, category, folder=None):
    root = Path(root).resolve()
    sources = roots(root, device, category)
    if folder is None:
        paths = sources
    else:
        folder = Path(folder)
        if folder.is_symlink():
            raise ValueError('Linked folders are not browsable')
        folder = folder.resolve()
        if not any(s.is_dir() and folder.is_relative_to(s) for s in sources):
            raise ValueError('Folder is outside this hardware category')
        paths = list(folder.iterdir())
    result = []
    for path in paths:
        if path.name.startswith('.') or path.name in SKIP or path.is_symlink():
            continue
        if not path.resolve().is_relative_to(root):
            continue
        if not path.is_dir() and not path.is_file():
            continue
        result.append({'name': path.name, 'path': path.relative_to(root).as_posix(),
                       'kind': 'Folder' if path.is_dir() else (path.suffix[1:].upper() or 'File'),
                       'is_dir': path.is_dir(), 'bytes': None if path.is_dir() else path.stat().st_size})
    return sorted(result, key=lambda x: (not x['is_dir'], x['name'].casefold(), x['path']))


def tree_paths(root, device, category):
    sources = roots(root, device, category)
    for path in group_files(root, device, category):
        owners = [s for s in sources if s.is_dir() and path.is_relative_to(s)]
        if owners:
            owner = max(owners, key=lambda p: len(p.parts))
            # Preserve the source folder itself, so separate main.c files don't merge.
            prefix = Path(owner.name)
            if sum(s.name == owner.name for s in sources) > 1:
                prefix = Path(owner.parent.name) / owner.name
            yield path, prefix / path.relative_to(owner)
        else:
            yield path, Path(path.name)
