"""File Manager operations for ARC-1 Workbench (R10). Importable without Qt.

Rules: everything stays inside the project; no symbolic links; never overwrite;
Windows naming rules apply on every platform so a project stays portable;
recorded evidence (pass records, vendored hardware sources) is read-only.
"""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re

READ_ONLY_PREFIXES = ('passes/', 'hardware/sources/', '.git/')
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = re.compile(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$', re.I)
MAX_NAME = 120
TYPE_NAMES = {'.c': 'C source', '.h': 'C header', '.s': 'Assembly source', '.S': 'Assembly source',
              '.ld': 'Linker script', '.py': 'Python script', '.md': 'Markdown document', '.json': 'JSON file',
              '.txt': 'Text document', '.png': 'PNG image', '.jpg': 'JPEG image', '.ppm': 'PPM image',
              '.arc1cart': 'ARC-1 cartridge', '.cmd': 'Windows command script', '.sh': 'Shell script',
              '.docx': 'Word document', '.csv': 'CSV file', '.sprite': 'ARC-1 sprite', '.replay': 'Input replay',
              '.bin': 'Binary image', '.elf': 'ELF executable', '.o': 'Object file'}


class FileOpError(ValueError):
    pass


def _root(root):
    return Path(root).resolve()


def check_inside(root, path, must_exist=True):
    root = _root(root)
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    # Refuse a symlink anywhere between the project root and the target.
    cur = root
    for part in p.resolve().relative_to(root).parts if _is_under(root, p) else ():
        cur = cur / part
        if cur.is_symlink():
            raise FileOpError('symbolic links are not handled by Workbench: %s' % cur.name)
    if not _is_under(root, p):
        raise FileOpError('outside the project folder')
    if p.is_symlink():
        raise FileOpError('symbolic links are not handled by Workbench')
    if must_exist and not p.exists():
        raise FileOpError('%s does not exist' % p.name)
    return p.resolve() if p.exists() else p


def _is_under(root, p):
    try:
        Path(p).resolve().relative_to(root)
        return True
    except ValueError:
        return False


def rel(root, path):
    return Path(path).resolve().relative_to(_root(root)).as_posix()


def is_read_only(root, path):
    r = rel(root, path)
    r_dir = r + '/'
    return any(r.startswith(p) or r_dir == p for p in READ_ONLY_PREFIXES)


def validate_name(name):
    if not isinstance(name, str) or not name.strip():
        raise FileOpError('a name is required')
    if len(name) > MAX_NAME:
        raise FileOpError('names are limited to %d characters' % MAX_NAME)
    if _BAD_CHARS.search(name):
        raise FileOpError('a name cannot contain any of  < > : " / \\ | ? *')
    if name in ('.', '..') or name.endswith(('.', ' ')) or name.startswith(' '):
        raise FileOpError('a name cannot start with a space or end with a dot or space')
    if _RESERVED.match(name):
        raise FileOpError('%s is reserved by Windows' % name.split('.')[0].upper())
    if name.startswith('.'):
        raise FileOpError('hidden (dot) names are not created by Workbench')
    return name


def _sibling_clash(folder, name, ignore=None):
    """Windows treats names case-insensitively: refuse 'Main.c' next to 'main.c'."""
    low = name.lower()
    for entry in folder.iterdir():
        if entry.name.lower() == low and (ignore is None or entry.resolve() != Path(ignore).resolve()):
            return entry
    return None


def _writable_folder(root, folder):
    folder = check_inside(root, folder)
    if not folder.is_dir():
        raise FileOpError('%s is not a folder' % folder.name)
    if is_read_only(root, folder):
        raise FileOpError('%s holds recorded evidence and is read-only in Workbench' % rel(root, folder))
    return folder


def new_file(root, folder, name, content=''):
    folder = _writable_folder(root, folder)
    validate_name(name)
    if _sibling_clash(folder, name):
        raise FileOpError('%s already exists' % name)
    target = folder / name
    with open(target, 'x', encoding='utf-8', newline='') as f:
        f.write(content)
    return target


def new_folder(root, folder, name):
    folder = _writable_folder(root, folder)
    validate_name(name)
    if _sibling_clash(folder, name):
        raise FileOpError('%s already exists' % name)
    target = folder / name
    target.mkdir()
    return target


def rename(root, path, new_name):
    path = check_inside(root, path)
    if path == _root(root):
        raise FileOpError('the project folder itself cannot be renamed here')
    if is_read_only(root, path):
        raise FileOpError('%s is recorded evidence and is read-only in Workbench' % rel(root, path))
    validate_name(new_name)
    if new_name == path.name:
        return path
    clash = _sibling_clash(path.parent, new_name, ignore=path)
    if clash:
        raise FileOpError('%s already exists' % clash.name)
    target = path.parent / new_name
    path.rename(target)
    return target


def duplicate(root, path):
    """Copies a file next to itself as 'name - Copy.ext', like Windows Explorer."""
    path = check_inside(root, path)
    if not path.is_file():
        raise FileOpError('only files can be duplicated here')
    _writable_folder(root, path.parent)
    stem, suffix = path.stem, path.suffix
    for n in range(1, 100):
        name = '%s - Copy%s%s' % (stem, '' if n == 1 else ' (%d)' % n, suffix)
        if not _sibling_clash(path.parent, name):
            target = path.parent / name
            with open(path, 'rb') as src, open(target, 'xb') as dst:
                dst.write(src.read())
            return target
    raise FileOpError('too many copies already exist')


def delete_file(root, path):
    """Deletes one file (never a folder). The caller must confirm with the user first."""
    path = check_inside(root, path)
    if path.is_dir():
        raise FileOpError('folders are not deleted from Workbench; use Windows Explorer')
    if is_read_only(root, path):
        raise FileOpError('%s is recorded evidence and is read-only in Workbench' % rel(root, path))
    path.unlink()


def type_name(path):
    p = Path(path)
    if p.is_dir():
        return 'File folder'
    return TYPE_NAMES.get(p.suffix, TYPE_NAMES.get(p.suffix.lower(), (p.suffix[1:].upper() + ' file') if p.suffix else 'File'))


def human_size(n):
    if n < 1024:
        return '%d bytes' % n
    for unit in ('KB', 'MB', 'GB'):
        n /= 1024.0
        if n < 1024 or unit == 'GB':
            return '%.0f %s' % (n, unit) if n >= 10 else '%.1f %s' % (n, unit)


def listing(root, folder):
    """Folder contents for the Browse view: folders first, then files, by name."""
    folder = check_inside(root, folder)
    if not folder.is_dir():
        raise FileOpError('%s is not a folder' % folder.name)
    rows = []
    for e in folder.iterdir():
        if e.name.startswith('.') or e.name == '__pycache__' or e.is_symlink():
            continue
        st = e.stat()
        rows.append({'name': e.name, 'path': rel(root, e), 'is_dir': e.is_dir(),
                     'size': None if e.is_dir() else st.st_size,
                     'size_text': '' if e.is_dir() else human_size(st.st_size),
                     'type': type_name(e),
                     'modified': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M')})
    rows.sort(key=lambda r: (not r['is_dir'], r['name'].lower()))
    return rows
