"""Read-only directory listing for the Finder (HATCH AGENT-01, UI-04): what is in a real folder on this computer.

CONTRACT (registered by the integrator; the implementer fills this module without changing names, arguments or shapes).

  ledger.browse {path, all?, limit?} -> {path, parent, mount, entries:[{name, kind, bytes, modified, hidden, symlink, readable}],
                                          count, truncated, free_bytes, total_bytes, basis}   read

path is an absolute folder on this computer (the owner's own machine; the Finder reaches it from Machine ▸ Storage, the
workspace and program folders, or a breadcrumb). kind is 'folder', 'file', 'link' or 'other'; bytes is the file's own
size (a symlink's target is never followed for size or listing); hidden entries (dot files) are returned only with all;
entries are sorted folders first then by natural name; at most limit (default 500, maximum 2000) entries, with truncated
set when more exist; free_bytes and total_bytes come from os.statvfs of the folder's mount. A path that is not a folder,
cannot be read or does not exist returns a ValueError with plain words, never a traceback. No file is opened; nothing
is written; no process starts. The Files folder of the workspace keeps its own files.* operations (Trash, versions,
proposals); this read is for looking, not for changing.

How it is filled (UI-04). The folder is read once with os.scandir; names and kinds come from the directory entries
themselves (no stat for an entry that is not returned), the returned entries are stat-ed without following links, and
`count` is the number of entries the folder holds after the hidden filter, so a status line can say "500 of 1,234
items" truthfully. A symlink's bytes are the link's own size and its kind is 'link' whatever it points at. `mount` is the
mount point holding the folder from /proc/mounts (None when that file is not readable). `parent` is None at the root.
A folder with more than SCAN_BOUND entries is read up to that bound and reported truncated with the count seen.
"""
from __future__ import annotations
import os
import stat as stat_module
from . import machine_overview

FIELDS = {
    'ledger.browse': ({'path': {'type': 'string', 'minLength': 1, 'maxLength': 4096}, 'all': {'type': 'boolean'},
                       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 2000}}, ['path']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = ('ledger.browse',)

DEFAULT_LIMIT = 500
MAX_LIMIT = 2000
SCAN_BOUND = 100000          # directory entries read before the listing stops and says so
BASIS = 'OBSERVED_ON_THIS_HOST_BY_SCANDIR_AND_STATVFS_NOTHING_OPENED_OR_WRITTEN'
KINDS = ('folder', 'file', 'link', 'other')


def plain_path(path):
    """The folder as an absolute, normalised path, or a ValueError in words."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError('Say which folder to look at.')
    if '\x00' in path:
        raise ValueError('That path is not a folder name.')
    if not os.path.isabs(path):
        raise ValueError('The folder must be named from the root of this computer, like /home: ' + path)
    return os.path.normpath(path)


def kind_of(entry):
    """folder / file / link / other from the directory entry, never following a link."""
    try:
        if entry.is_symlink():
            return 'link'
        if entry.is_dir(follow_symlinks=False):
            return 'folder'
        if entry.is_file(follow_symlinks=False):
            return 'file'
    except OSError:
        return 'other'
    return 'other'


def describe(entry, kind):
    """One entry's row: the entry's own stat (lstat), with unavailable values left None rather than invented."""
    try:
        st = entry.stat(follow_symlinks=False)
        size = int(st.st_size) if kind in ('file', 'link') else None
        modified = float(st.st_mtime)
    except OSError:
        size = None; modified = None
    try:
        readable = os.access(entry.path, os.R_OK, follow_symlinks=False) if os.access in os.supports_follow_symlinks else os.access(entry.path, os.R_OK)
    except (OSError, ValueError):
        readable = False
    return dict(name=entry.name, kind=kind, bytes=size, modified=modified, hidden=entry.name.startswith('.'), symlink=(kind == 'link'), readable=bool(readable))


def listing(path, show_all=False, limit=DEFAULT_LIMIT):
    """The bounded listing described above."""
    folder = plain_path(path)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError('The limit must be a whole number between 1 and %d.' % MAX_LIMIT)
    limit = max(1, min(MAX_LIMIT, limit))
    try:
        mode = os.lstat(folder)
    except FileNotFoundError:
        raise ValueError('There is no folder at ' + folder)
    except PermissionError:
        raise ValueError('That folder cannot be read: ' + folder)
    except OSError as exc:
        raise ValueError('That folder cannot be read: %s (%s)' % (folder, exc.strerror or 'error'))
    if stat_module.S_ISLNK(mode.st_mode):
        # The Finder shows a link as a link; the owner may follow it by choosing its real place from the path bar.
        real = os.path.realpath(folder)
        if not os.path.isdir(real):
            raise ValueError('That is a link, not a folder: ' + folder)
    elif not stat_module.S_ISDIR(mode.st_mode):
        raise ValueError('That is a file, not a folder: ' + folder)
    rows = []; seen = 0; bounded = False
    try:
        with os.scandir(folder) as it:
            for entry in it:
                hidden = entry.name.startswith('.')
                if hidden and not show_all:
                    continue
                seen += 1
                if seen > SCAN_BOUND:
                    bounded = True; break
                rows.append((entry, kind_of(entry)))
    except PermissionError:
        raise ValueError('That folder cannot be read: ' + folder)
    except NotADirectoryError:
        raise ValueError('That is a file, not a folder: ' + folder)
    except FileNotFoundError:
        raise ValueError('There is no folder at ' + folder)
    except OSError as exc:
        raise ValueError('That folder cannot be read: %s (%s)' % (folder, exc.strerror or 'error'))
    rows.sort(key=lambda row: (row[1] != 'folder', machine_overview.natural(row[0].name), row[0].name))
    count = len(rows)
    entries = [describe(entry, kind) for entry, kind in rows[:limit]]
    parent = os.path.dirname(folder) if folder != os.path.dirname(folder) else None
    space = machine_overview.space(folder)
    table, _ = machine_overview.mounts()
    mount = machine_overview.holder(folder, table) if table else None
    return dict(path=folder, parent=parent, mount=mount['mountpoint'] if mount else None, entries=entries, count=count,
                truncated=bool(count > len(entries) or bounded), free_bytes=space['free'] if space else None,
                total_bytes=space['total'] if space else None, basis=BASIS)


def dispatch(kernel, op, args, principal):
    if op == 'ledger.browse':
        return listing(args['path'], bool(args.get('all', False)), int(args.get('limit', DEFAULT_LIMIT)))
    raise ValueError('Unknown browse operation')
