"""Your home's Trash: DELETE for the files of your home, the system's own way (Graphite 1.0 L6b).

The owner's tree reaches the whole computer (1.0 L6); everything a person does to a file works in Home, DELETE included. A file
or folder of your home that you delete goes to the system's Trash, the one every desktop on this computer shares (the
freedesktop.org Trash specification, version 1.0): $XDG_DATA_HOME/Trash, which is ~/.local/share/Trash when the system says
nothing else. Nothing is ever removed for good here: Delete moves the thing into the Trash with a note of where it was, and
Restore (or Undo, at once) moves it back.

    ~/.local/share/Trash/files/<name>               the file or folder itself, moved there whole (one rename: never copied,
                                                    never rewritten; a thing on another drive than the Trash is refused, with
                                                    the words why, and nothing is moved)
    ~/.local/share/Trash/info/<name>.trashinfo      [Trash Info] / Path=<where it was, URL-escaped> / DeletionDate=<local
                                                    time, YYYY-MM-DDThh:mm:ss>: written first, created only if no such name is
                                                    there yet (the name is claimed atomically), so two programs never take one name

Restore puts it back where it was; when that name is taken by then, beside it under a free name ('letter 2.odt'), never over
anything. Its .trashinfo note is removed once the thing is back (as the specification says); the 'directorysizes' cache line of
a folder put back is dropped too. What other programs put in the Trash is listed and restored the same way.

The Kernel's operations stay files.trash, files.trash_list and files.restore (files_service): a path in your home goes here, a
path in Files to Files' own DELETE as before. Nothing here has Qt; no floating point is used (times are whole seconds).
"""
from __future__ import annotations

import errno
import hashlib
import os
import time
from pathlib import Path
from urllib.parse import quote, unquote_to_bytes

INFO_SUFFIX = '.trashinfo'
MOST_LISTED = 500                     # entries the Trash lists at most (newest first)
# The specification's own words, kept as its bytes: they name a file format and a folder, never anything shown (on screen the
# place is DELETE, the owner's word of 14 November 2026).
HEADER = b'[Trash Info]'.decode('ascii')
FOLDER = b'Trash'.decode('ascii')


def trash_dir():
    """The home Trash: $XDG_DATA_HOME/Trash (an absolute XDG_DATA_HOME only, as the base directory specification says), else
    ~/.local/share/Trash."""
    data = os.environ.get('XDG_DATA_HOME') or ''
    base = Path(data) if data.startswith('/') else Path(os.path.expanduser('~')) / '.local' / 'share'
    return base / FOLDER


def files_dir():
    return trash_dir() / 'files'


def info_dir():
    return trash_dir() / 'info'


def ensure():
    """The Trash's two folders, made when missing (only yours to read: 0700)."""
    for folder in (files_dir(), info_dir()):
        folder.mkdir(parents=True, mode=0o700, exist_ok=True)


def ident_of(name):
    """A stable 32-hex id for an entry of the Trash named so (files.restore takes it)."""
    return hashlib.sha256(('home-trash:' + name).encode('utf-8', 'surrogateescape')).hexdigest()[:32]


def inside(path):
    """Whether a path is the Trash or inside it, or holds it."""
    trash = os.path.normpath(str(trash_dir()));text = os.path.normpath(str(path))
    return text == trash or text.startswith(trash + '/') or trash.startswith(text.rstrip('/') + '/')


def in_trash(path):
    """Whether a whole path is in the Trash's files/ (L1 keeps an object deleted there as 'in DELETE')."""
    folder = os.path.normpath(str(files_dir()));text = os.path.normpath(str(path))
    return text.startswith(folder + '/')


def tilde(path):
    from .home_reach import tilde as named
    return named(path)


def in_home(kernel, path):
    """Whether a file or folder (the thing itself where it is: a link is where it is, not where it points) is in your home,
    outside Files and outside Graphite's own records: the things whose DELETE is your home's Trash."""
    from . import home_reach as hr
    path = Path(path)
    try:place = Path(os.path.realpath(path.parent)) / path.name
    except (OSError, RuntimeError):
        return False
    if hr.is_system(place):return False      # (the Trash itself, or a folder holding it, is refused by put(), with the words why)
    try:files = hr.files_root(kernel).resolve()
    except (OSError, RuntimeError):
        files = hr.files_root(kernel)
    if hr.within(place, files) or any(hr.within(place, own) for own in hr.own_folders(kernel)):return False
    return hr.within(place, hr.home()) and place != hr.home()


def holds_graphite(kernel, path):
    """Whether a folder is your home itself or holds Graphite's workspace, its Files or its program: it stays where it is (the
    owner's tree offers no rename, move or Delete for it, and files.trash refuses it)."""
    from . import home_reach as hr
    try:place = Path(os.path.realpath(path))
    except (OSError, RuntimeError):
        return True
    if place == hr.home():return True
    try:files = hr.files_root(kernel).resolve()
    except (OSError, RuntimeError):
        files = hr.files_root(kernel)
    return any(hr.within(mine, place) for mine in [files] + hr.own_folders(kernel))      # it is one of them, or holds one


STORED = '~trash:'                  # how files_trash keeps a thing it put in your home's Trash: '~trash:<its name there>'


def listed(rows=()):
    """The Trash for files.trash_list: each entry with the id files.restore takes (Graphite's own row's id for what Graphite
    put there, else the entry's own id) and by_graphite."""
    mine = {str(r.get('stored'))[len(STORED):]: r.get('id') for r in rows or () if str(r.get('stored') or '').startswith(STORED)}
    out = []
    for entry in entries():
        ident = mine.get(entry['name'])
        out.append(dict(entry, id=ident or entry['id'], by_graphite=bool(ident)))
    return out


# ---- Delete ---------------------------------------------------------------------------------------------------------------------
def _candidates(name):
    yield name
    stem, dot, suffix = name.partition('.') if not name.startswith('.') else (name, '', '')
    for n in range(2, 10000):
        yield ('%s.%d.%s' % (stem, n, suffix)) if dot else ('%s.%d' % (name, n))


def _claim(name):
    """A name not used in the Trash yet, claimed by creating its .trashinfo exclusively: (name, the open descriptor)."""
    for candidate in _candidates(name):
        if os.path.lexists(files_dir() / candidate):continue
        try:
            fd = os.open(str(info_dir() / (candidate + INFO_SUFFIX)), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        return candidate, fd
    raise ValueError("TRASH_FULL_OF_NAMES: no free name for %s in your home's bin" % name[:120])


def info_text(original, when=None):
    """The .trashinfo note for a thing that was at `original` (an absolute path), deleted at `when` (local time)."""
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(int(when if when is not None else time.time())))
    return '%s\nPath=%s\nDeletionDate=%s\n' % (HEADER, quote(os.fsencode(str(original)), safe='/'), stamp)


def put(path):
    """Move a file or folder of your home into the Trash, with its note. Returns {'name', 'stored', 'original', 'at', 'id'}.
    Refused, with nothing moved: the Trash itself, your home folder, a thing on another drive than the Trash."""
    path = Path(os.path.abspath(str(path)))
    if not os.path.lexists(path):raise ValueError('TRASH_NOT_FOUND: %s is not there' % tilde(path)[:200])
    from .home_reach import home
    if path == home() or path == Path(os.path.expanduser('~')):raise ValueError('TRASH_HOME: your home folder itself stays')
    if inside(path):raise ValueError("TRASH_ITSELF: %s is your home's bin (DELETE) or holds it; it is not deleted" % tilde(path)[:200])
    ensure()
    try:
        here = os.lstat(path).st_dev;there = os.stat(files_dir()).st_dev
    except OSError as exc:
        raise ValueError('TRASH_NOT_READ: %s (%s)' % (tilde(path)[:200], exc.strerror or type(exc).__name__)) from None
    if here != there:
        raise ValueError("TRASH_OTHER_DRIVE: %s is on another drive than your home's bin (DELETE); Kas moves nothing across "
                         'drives to delete it, so nothing was moved' % tilde(path)[:200])
    now = int(time.time())
    name, fd = _claim(path.name)
    note = info_dir() / (name + INFO_SUFFIX)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(info_text(path, now))
    except OSError:
        _drop(note);raise
    stored = files_dir() / name
    try:
        os.rename(path, stored)          # one rename: the same bytes, the same inode, nothing copied or rewritten
    except OSError as exc:
        _drop(note)
        if exc.errno == errno.EXDEV:
            raise ValueError("TRASH_OTHER_DRIVE: %s is on another drive than your home's bin (DELETE); nothing was moved" % tilde(path)[:200]) from None
        raise ValueError('TRASH_NOT_MOVED: %s (%s); nothing was moved' % (tilde(path)[:200], exc.strerror or type(exc).__name__)) from None
    return {'name': name, 'stored': str(stored), 'original': str(path), 'at': now, 'id': ident_of(name)}


def _drop(note):
    """Remove a .trashinfo note Graphite wrote (never a file of yours)."""
    try:os.unlink(note)
    except OSError:
        pass


# ---- what is in it --------------------------------------------------------------------------------------------------------------
def read_info(note):
    """(original path, deleted at in whole seconds or 0) from a .trashinfo note; None when it is not one."""
    try:
        text = Path(note).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    lines = [line.strip() for line in text.splitlines()]
    if HEADER not in lines:return None
    values = {}
    for line in lines[lines.index(HEADER) + 1:]:
        if line.startswith('['):break
        key, eq, value = line.partition('=')
        if eq:values.setdefault(key.strip(), value.strip())
    raw = values.get('Path')
    if not raw:return None
    original = os.fsdecode(unquote_to_bytes(raw))
    if not original.startswith('/'):original = str(trash_dir().parent / original)   # relative to the Trash's own top folder
    at = 0
    try:at = int(time.mktime(time.strptime(values.get('DeletionDate', '')[:19], '%Y-%m-%dT%H:%M:%S')))
    except (ValueError, OverflowError):
        pass
    return original, at


def entries(most=MOST_LISTED):
    """What is in the Trash, newest first: [{'id', 'name', 'original' (whole path), 'place' (as you read it), 'at', 'kind',
    'size'}]. An entry whose thing is gone from files/ is left out."""
    folder = info_dir()
    if not folder.is_dir():return []
    out = []
    try:notes = list(os.scandir(folder))
    except OSError:
        return []
    for note in notes:
        if not note.name.endswith(INFO_SUFFIX):continue
        name = note.name[:-len(INFO_SUFFIX)]
        stored = files_dir() / name
        try:st = os.lstat(stored)
        except OSError:
            continue
        found = read_info(note.path)
        if found is None:continue
        original, at = found
        import stat as statmod
        kind = 'folder' if statmod.S_ISDIR(st.st_mode) else 'file'
        out.append({'id': ident_of(name), 'name': name, 'shown': Path(original).name, 'original': original, 'place': tilde(original), 'at': at,
                    'kind': kind, 'size': 0 if kind == 'folder' else int(st.st_size)})
    out.sort(key=lambda e: (-e['at'], e['name']))
    return out[:most]


def by_id(ident):
    return next((e for e in entries(most=100000) if e['id'] == ident), None)


# ---- Restore --------------------------------------------------------------------------------------------------------------------
def _free(target):
    """target itself when nothing is there; else 'name 2.ext', 'name 3.ext'… beside it (nothing is overwritten)."""
    if not os.path.lexists(target):return target
    stem, suffix = target.stem, target.suffix
    if target.name.startswith('.') and target.suffix == target.name:stem, suffix = target.name, ''
    for n in range(2, 10000):
        candidate = target.with_name('%s %d%s' % (stem, n, suffix))
        if not os.path.lexists(candidate):return candidate
    raise ValueError('TRASH_NO_FREE_NAME: %s' % tilde(target)[:200])


def restore(name):
    """Put an entry back where it was (beside it under a free name when the name is taken now). Returns {'restored' (the whole
    path), 'original', 'renamed' (True when it is beside its old name), 'stored'}."""
    if not name or '/' in name or name in ('.', '..') or '\0' in name:raise ValueError('TRASH_NAME: not a thing in DELETE')
    note = info_dir() / (name + INFO_SUFFIX);stored = files_dir() / name
    found = read_info(note)
    if found is None or not os.path.lexists(stored):raise ValueError('TRASH_NOT_FOUND: that is no longer in DELETE')
    original = Path(found[0])
    original.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = _free(original)
    try:
        os.rename(stored, target)
    except OSError as exc:
        raise ValueError('TRASH_NOT_RESTORED: %s (%s); it stays in DELETE' % (tilde(original)[:200], exc.strerror or type(exc).__name__)) from None
    _drop(note)
    _forget_size(name)
    return {'restored': str(target), 'original': str(original), 'renamed': target != original, 'stored': str(stored)}


def _forget_size(name):
    """The 'directorysizes' cache (the specification's, for folders) without the line of an entry that left the Trash."""
    cache = trash_dir() / 'directorysizes'
    try:lines = cache.read_text(encoding='utf-8', errors='surrogateescape').splitlines()
    except OSError:
        return
    wanted = quote(os.fsencode(name), safe='')
    kept = [line for line in lines if line.split(' ', 2)[2:3] != [wanted]]
    if len(kept) == len(lines):return
    temporary = cache.with_name('.directorysizes.writing')
    try:
        temporary.write_text(''.join(line + '\n' for line in kept), encoding='utf-8', errors='surrogateescape');os.replace(temporary, cache)
    except OSError:
        pass
