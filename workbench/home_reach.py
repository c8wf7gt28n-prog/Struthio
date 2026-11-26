"""The whole computer, and Kasandra's reach in it (Graphite 1.0 L6).

The owner, 26 November 2026: "Shouldn't the files part of the left tree start at root /?" The Files tab starts at "This
computer /", so every folder the owner's account can read is reachable; Home (the owner's home folder) is where the tree
lands. This module is the rule book behind it, with no Qt:

  where a path is   area(): 'files' (the workspace's Files folder: its own rules, her own area Files/Slate, as before),
                    'own' (Graphite's own records and program, outside Files: they change only through the desk, never as
                    files), 'home' (the owner's home folder), 'system' (the pseudo-filesystems /proc, /sys, /dev and /run:
                    shown in the tree as such, never read for the board, relevance or ids; a removable drive mounted under
                    /run/media is a drive, not a system folder), 'outside' (everything else on this computer).
  reading           anywhere the owner's account can read (the system's own permissions decide; Graphite never asks for
                    more), the system folders apart. Her reads never send anything out: her model is local and sealed.
  her changes       her file tools (K2), her steps under grants (K3), what a utility made (K6's Apply) and her hand in
                    other programs (A1) reach only inside Home (and the workspace's Files, by its own rules), under grants
                    as before, and never outside it, at any place of the dial: her_change() says "outside your home: never".
                    Inside Home, Graphite's own records and program are never hers to change as files.
  your own press    a change the owner makes by their own press follows the system's permissions anywhere.
  names             a path is named from / or from ~ ('/etc/hosts', '~/Rail notes/note.txt'); a path with no leading / or ~
                    is inside Files, as it always was.

It also lists one folder for the tree (listing()): one level, never deeper, folders first, dot-names left out unless the
owner shows them. Nothing here writes anything.
"""
from __future__ import annotations

import contextlib
import contextvars
import os
import stat as statmod
from pathlib import Path, PurePosixPath

NEVER = 'outside your home: never'
SYSTEM_FOLDERS = ('/proc', '/sys', '/dev', '/run')
DRIVES_UNDER_RUN = ('/run/media',)          # where some systems mount removable drives: a drive, not a system folder
SYSTEM_WORDS = 'a system folder: shown, never read'
OWN_WORDS = "Graphite's own records and program change only through the desk, never as files: never"
FILES, OWN, HOME, SYSTEM, OUTSIDE = 'files', 'own', 'home', 'system', 'outside'
AREA_WORDS = {FILES: 'in Files', OWN: "Graphite's own", HOME: 'in your home', SYSTEM: 'a system folder', OUTSIDE: 'outside your home'}
MOST_ROWS = 400                             # rows one folder lists in the tree, at most (the rest are counted)
# what a change lands on: the arguments that name a place it writes (files.copy reads its 'path' and writes into 'to')
WRITES = {'files.copy': ('to',)}
READS_ONLY = ('sandbox.run',)               # a utility runs on copies, in its own sealed folder


# ---- names ---------------------------------------------------------------------------------------------------------------
def home():
    """The owner's home folder, as the system names it (HOME), with its links followed."""
    named = Path(os.path.expanduser('~'))
    try:return named.resolve()
    except (OSError, RuntimeError):
        return named


def named_absolute(text):
    """Whether the words name a path from / or from ~ (anything else is a path inside Files)."""
    return isinstance(text, str) and (text.startswith('/') or text == '~' or text.startswith('~/'))


def expand(text):
    """The path the words name ('/…' or '~/…'), normalised; None when it climbs ('..') or holds a NUL."""
    raw = str(text or '').replace('\\', '/')
    if raw == '~' or raw.startswith('~/'):
        base, rest = home(), raw[1:]
    else:
        base, rest = Path('/'), raw
    parts = [p for p in PurePosixPath(rest).parts if p not in ('', '/', '.')]
    if any(p == '..' or '\0' in p for p in parts):return None
    return base.joinpath(*parts)


def real(path):
    """The path as the system finds it, its links followed (a path not there yet: its folder's, with its own name)."""
    path = Path(path)
    try:
        if path.exists() or path.is_symlink():return path.resolve()
        return path.parent.resolve() / path.name
    except (OSError, RuntimeError):
        return path


def tilde(path):
    """A path as the owner reads it: ~/… inside the home folder, else the whole path."""
    path = Path(path);h = home()
    if path == h:return '~'
    try:return '~/' + path.relative_to(h).as_posix()
    except ValueError:
        return str(path)


def within(path, folder):
    path, folder = Path(path), Path(folder)
    return path == folder or folder in path.parents


def is_system(path):
    """/proc, /sys, /dev and /run, and anything in them (a removable drive mounted under /run/media apart)."""
    text = os.path.normpath(str(path))
    if any(text == d or text.startswith(d + '/') for d in DRIVES_UNDER_RUN):return False
    return any(text == s or text.startswith(s + '/') for s in SYSTEM_FOLDERS)


def files_root(kernel):
    from . import files_service
    return files_service.root(kernel, create=False)


def own_folders(kernel):
    """Graphite's own: the workspace's records folder (its Files is the owner's, by its own rules) and the program."""
    out = []
    try:out.append(Path(kernel.root).resolve())
    except (OSError, RuntimeError, AttributeError, TypeError):
        pass
    try:
        from . import locations
        out.append(Path(locations.PACKAGE).resolve())
    except (OSError, RuntimeError, ImportError):
        pass
    return out


def absolute(kernel, text):
    """The absolute path a path argument names: from / or ~, or inside Files (None when it climbs out)."""
    if named_absolute(text):return expand(text)
    parts = [p for p in PurePosixPath(str(text or '').replace('\\', '/')).parts if p not in ('', '/', '.')]
    if any(p == '..' or '\0' in p for p in parts):return None
    try:base = files_root(kernel).resolve()
    except (OSError, RuntimeError):
        base = files_root(kernel)
    return base.joinpath(*parts)


def area(kernel, path):
    """Where a path is: FILES, OWN, HOME, SYSTEM or OUTSIDE (by the path as named and as the system finds it)."""
    named = Path(path);actual = real(named)
    if is_system(named) or is_system(actual):return SYSTEM
    try:files = files_root(kernel).resolve()
    except (OSError, RuntimeError):
        files = files_root(kernel)
    if within(actual, files):return FILES
    if any(within(actual, own) for own in own_folders(kernel)):return OWN
    if within(actual, home()):return HOME
    return OUTSIDE


def place_words(kernel, path):
    """Where a path is, in words: 'Files/notes/x.md', '~/Rail notes/x.md', '/etc/hosts'."""
    path = Path(path)
    try:
        rel = path.relative_to(files_root(kernel).resolve()).as_posix()
        return 'Files' if rel == '.' else 'Files/' + rel
    except (ValueError, OSError, RuntimeError):
        return tilde(path)


def folder_words(text):
    """'in Files/…', 'in ~/…' or 'in /…': the folder a file's path (as the Kernel keeps it) is in."""
    text = str(text or '')
    if text.startswith('/'):
        folder = str(PurePosixPath(text).parent)
        return 'in ' + tilde(folder)
    folder = text.rpartition('/')[0]
    return 'in ' + ('Files/' + folder if folder else 'Files')


def role_words(text):
    """'a file in Files', 'a file in your home' or 'a file on this computer', for a path as the Kernel keeps it."""
    text = str(text or '')
    if not text.startswith('/'):return 'in Files'
    return 'in your home' if within(Path(text), home()) else 'on this computer'


# ---- reading -------------------------------------------------------------------------------------------------------------
def read_refusal(path):
    """'' when the path may be read for the board, relevance and ids; else why not (a system folder)."""
    if is_system(path) or is_system(real(path)):return '%s (%s)' % (SYSTEM_WORDS, os.path.normpath(str(path))[:200])
    return ''


# ---- her changes ---------------------------------------------------------------------------------------------------------
def her_change(kernel, path):
    """'' when a change of hers may land on this path by the rules that still apply there (the Files rules, a grant of
    yours, your press on her step); else why it never may, at any place of the dial."""
    where = area(kernel, path)
    if where in (FILES, HOME):return ''
    if where == OWN:return OWN_WORDS + ' (%s)' % tilde(path)
    if where == SYSTEM:return '%s (%s is a system folder; her changes reach only inside your home, at every place of the dial)' % (NEVER, tilde(path))
    return '%s (%s is outside your home; her changes reach only inside it, at every place of the dial)' % (NEVER, tilde(path))


def change_paths(operation, arguments):
    """The path arguments a change lands on (as given): 'path' and 'to', a new folder's place and name."""
    a = arguments if isinstance(arguments, dict) else {}
    if operation in READS_ONLY:return []
    if operation == 'files.mkdir':
        name = a.get('name')
        if not isinstance(name, str):return []
        base = a.get('path') or ''
        return [(base.rstrip('/') + '/' + name) if base else name]
    keys = WRITES.get(operation, ('path', 'to'))
    return [a[k] for k in keys if isinstance(a.get(k), str)]


def never_words(kernel, operation, arguments):
    """'' unless this call is a change that would land outside your home (or on Graphite's own): then why it never may."""
    try:
        from .engineering_kernel import CAPABILITIES
        scope = CAPABILITIES.get(operation)
    except ImportError:
        scope = None
    if scope in (None, 'read'):return ''
    for text in change_paths(operation, arguments):
        path = absolute(kernel, text)
        if path is None:continue
        why = her_change(kernel, path)
        if why:return why
    return ''


_HERS = contextvars.ContextVar('kas_hers', default=None)


@contextlib.contextmanager
def hers(operation='', arguments=None, pressed=False):
    """Around a change of hers that is dispatched with your principal (her hand's card in Talk, done by her dial, or by
    your Approve when `pressed`): inside your home a grant of yours or your Approve on that very card decides; outside it,
    never. Files keeps its own rules."""
    token = _HERS.set({'operation': str(operation or ''), 'arguments': dict(arguments or {}), 'pressed': bool(pressed)})
    try:
        yield
    finally:
        _HERS.reset(token)


def in_her_work(principal):
    """Whether the call being made now is her work: inside a step or a tool use (a grant's permit is in force), inside her
    hand's card (hers()), or by a principal without your approve scope."""
    try:
        from .grants import _PERMIT
        if _PERMIT.get() is not None:return True
    except ImportError:
        pass
    if _HERS.get() is not None:return True
    return 'approve' not in getattr(principal, 'scopes', ())


def let_through(kernel, principal, path):
    """Inside your home, outside Files: whether this change of hers is let through, by your Approve on her very card (its
    own targets) or by a grant of yours in force that covers the call (her hand's card has no assignment)."""
    held = _HERS.get()
    if held is None:return False
    target = Path(path)
    if held['pressed']:
        for text in change_paths(held['operation'], held['arguments']):
            named = absolute(kernel, text)
            if named is not None and within(target, named):return True
    try:
        from .grants import covering
        return covering(kernel, principal.identity, held['operation'], held['arguments'], None, include_built_in=False) is not None
    except Exception:  # noqa: BLE001 - grants that cannot be read let nothing through
        return False


def grant_folder(kernel, text):
    """A grant's folder named from / or ~: (its value, '') — the folder inside Files as Files names it, or '~/…' in your
    home — or ('', why no grant can be given for it)."""
    path = expand(text)
    if path is None:return '', 'GRANT_FOLDER: a folder in your home, with no ".."'
    actual = real(path)
    if actual.exists() and not actual.is_dir():return '', 'GRANT_FOLDER: %s is a file; a grant names a folder' % tilde(path)
    where = area(kernel, path)
    if where == FILES:
        try:base = files_root(kernel).resolve()
        except (OSError, RuntimeError):
            base = files_root(kernel)
        rel = actual.relative_to(base).as_posix() if within(actual, base) else ''
        if rel in ('', '.'):return '', 'GRANT_FOLDER: name a folder inside Files (a grant over all of Files is never given)'
        if rel.split('/')[0] in ('.trash', '.versions'):return '', 'GRANT_FOLDER: DELETE and kept versions keep their own words'
        return rel, ''
    if where == HOME:
        if actual == home():return '', 'GRANT_FOLDER: a grant over all of your home is never given; name a folder in it'
        return tilde(actual), ''
    if where == OWN:return '', 'GRANT_FOLDER: ' + OWN_WORDS
    return '', 'GRANT_FOLDER: %s is %s: never (her changes reach only inside your home)' % (tilde(path), 'a system folder' if where == SYSTEM else 'outside your home')


# ---- one folder, for the tree --------------------------------------------------------------------------------------------
def listing(folder, hidden=False, most=MOST_ROWS):
    """One folder's rows, one level only: {'rows': [{name, path, kind ('folder', 'file', 'system'), link}], 'left': rows
    not listed past `most`, 'hidden': dot-names left out, 'error': why it could not be read, or ''}. Folders first, then
    files, each by name. A system folder is listed as such, never read; the folder itself is read only when it is not one."""
    out = {'rows': [], 'left': 0, 'hidden': 0, 'error': ''}
    refusal = read_refusal(folder)
    if refusal:
        out['error'] = refusal;return out
    try:
        entries = list(os.scandir(folder))
    except PermissionError:
        out['error'] = 'not readable with your account';return out
    except OSError as exc:
        out['error'] = 'not readable here (%s)' % (exc.strerror or type(exc).__name__);return out
    rows = []
    for entry in entries:
        if entry.name.startswith('.') and not hidden:
            out['hidden'] += 1;continue
        path = os.path.join(str(folder), entry.name)
        try:link = entry.is_symlink()
        except OSError:
            link = False
        if is_system(path):
            rows.append((0, entry.name.casefold(), {'name': entry.name, 'path': path, 'kind': 'system', 'link': link}));continue
        try:
            folder_like = entry.is_dir()
            plain = not folder_like and entry.is_file()
        except OSError:
            folder_like = plain = False
        if not (folder_like or plain):
            if link:      # a link that leads nowhere (or somewhere unreadable): shown as a file, for what it is
                rows.append((1, entry.name.casefold(), {'name': entry.name, 'path': path, 'kind': 'file', 'link': True}))
            continue
        rows.append((0 if folder_like else 1, entry.name.casefold(), {'name': entry.name, 'path': path, 'kind': 'folder' if folder_like else 'file', 'link': link}))
    rows.sort(key=lambda r: (r[0], r[1]))
    out['rows'] = [r[2] for r in rows[:most]];out['left'] = max(0, len(rows) - most)
    return out


def size_of(path):
    """A file's size in bytes, without following a link out (0 when it cannot be read)."""
    try:
        st = os.stat(path)
        return int(st.st_size) if statmod.S_ISREG(st.st_mode) else 0
    except OSError:
        return 0
