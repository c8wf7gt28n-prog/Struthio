"""A Windows hand's keys (Graphite 1.1 W1): the two settings, the file clipboard, Properties' words, and deleting for good.

PLAN_1.1.md, W1. What is held here has no window in it (windows_keys_qt is the window's side):

  the settings     "Show keys" (menus and tips show their keys; off, no key is printed, as 0.5.2 to 1.0 had it: this reverses
                   the owner's rule of 13 Nov, PLAN_1.1.md section 6) and "DOS words" in the Terminal: on, off, or "show me
                   only" (dos_words). Kept in Graphite's own small file, $XDG_CONFIG_HOME/graphite/windows_hand.json.
  the clipboard    Ctrl+C and Ctrl+X on files hold their paths (copy or cut); Ctrl+V in a folder is ONE change: the Kernel's
                   files.batch (1.0 L6c: act copy or move, to that folder), so one Undo puts the whole paste back
                   (files.batch_undo). A cut is held until it is pasted once; a copy can be pasted again.
  Properties       a small page's words: name, kind, size, dates, where it is, who may read and change it in words, what
                   opens it.
  for good         Shift+Delete asks first, then files.delete_for_good: the one operation in Graphite that removes a file
                   without the bin. It is your press only (approve; her work is refused it, whatever her grants say), and
                   only for a file or folder the Files tree may change (home_files_qt.changeable: your home and Files,
                   never your home itself, Files itself, Graphite's own records or a folder holding them).

Kernel operation (one block in engineering_kernel.py and engineering_cli.py, commented 1.1 W1):
  files.delete_for_good  {path}   approve   removed without the bin, after the window asked; never her work
"""
from __future__ import annotations

import json
import mimetypes
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

DOS_MODES = ('on', 'show', 'off')
DOS_WORDS = {'on': 'On: translated and run', 'show': 'Show me only: translated and shown, never run', 'off': 'Off: every line as typed'}
DEFAULTS = {'show_keys': True, 'dos_words': 'on'}
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
FIELDS = {'files.delete_for_good': ({'path': PATH}, ['path'])}
SCOPES = {'files.delete_for_good': 'approve'}


# ---- the two settings ------------------------------------------------------------------------------------------------------------
def settings_file(environ=None):
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_CONFIG_HOME') or os.path.join(environ.get('HOME') or str(Path.home()), '.config')
    return Path(base) / 'graphite' / 'windows_hand.json'


def read(environ=None):
    out = dict(DEFAULTS)
    try:
        got = json.loads(settings_file(environ).read_text(encoding='utf-8'))
        if isinstance(got.get('show_keys'), bool):out['show_keys'] = got['show_keys']
        if got.get('dos_words') in DOS_MODES:out['dos_words'] = got['dos_words']
    except (OSError, ValueError, AttributeError):
        pass
    return out


def write(environ=None, **changes):
    now = read(environ)
    if isinstance(changes.get('show_keys'), bool):now['show_keys'] = changes['show_keys']
    if changes.get('dos_words') in DOS_MODES:now['dos_words'] = changes['dos_words']
    path = settings_file(environ)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp');temp.write_text(json.dumps(now, indent=1), encoding='utf-8');os.replace(temp, path)
    except OSError:
        pass
    return now


def show_keys(environ=None):
    return read(environ)['show_keys']


def dos_words(environ=None):
    return read(environ)['dos_words']


def keyed(words, keys, shown=None):
    """A tip with its key when keys are shown: 'Rename (F2)'; the words alone when they are not."""
    shown = show_keys() if shown is None else shown
    keys = [k for k in (keys if isinstance(keys, (list, tuple)) else [keys]) if k]
    return '%s (%s)' % (words, ' or '.join(keys)) if shown and keys else words


# ---- the file clipboard -----------------------------------------------------------------------------------------------------------
class FileClipboard:
    """Files held by Ctrl+C (copy) or Ctrl+X (cut); a paste is one files.batch, so one Undo puts it all back."""

    def __init__(self):
        self.paths, self.act = [], ''

    def hold(self, paths, act):
        if act not in ('copy', 'move'):raise ValueError('copy or move')
        self.paths = [str(p) for p in paths if str(p)];self.act = act if self.paths else ''
        return self.words()

    def words(self):
        if not self.paths:return 'Nothing is held to paste.'
        from .bulk_files import counted
        return '%s %s: paste them in a folder.' % (counted(self.paths), 'copied' if self.act == 'copy' else 'cut')

    def batch_args(self, folder):
        """files.batch's arguments for a paste into `folder`."""
        if not self.paths:raise ValueError('Nothing is held to paste.')
        return {'act': self.act, 'paths': list(self.paths)[:1000], 'to': str(folder)}

    def pasted(self, result):
        """After a paste: a cut is pasted once (its files are where they were pasted now); a copy stays held."""
        if self.act == 'move' and result.get('done'):self.paths, self.act = [], ''

    def paste(self, kernel, folder, principal):
        """The paste through the Kernel (the owner's press): files.batch, whose result names the batch for its one Undo."""
        answer = kernel.dispatch('files.batch', self.batch_args(folder), principal)
        if answer.get('ok'):self.pasted(answer['result'])
        return answer


# ---- Properties ------------------------------------------------------------------------------------------------------------------
def _size_words(size):
    for unit, step in (('GB', 1 << 30), ('MB', 1 << 20), ('KB', 1 << 10)):
        if size >= step:return '%.1f %s (%s bytes)' % (size / step, unit, format(size, ','))
    return '%d bytes' % size


def _when(seconds):
    return time.strftime('%A %d %B %Y, %H:%M', time.localtime(seconds))


def _who(mode, owner_name, group_name, mine):
    def can(r, w):
        return 'read and change it' if r and w else 'read it' if r else 'change it but not read it' if w else 'neither read nor change it'
    you = 'You' if mine else 'Its owner, %s,' % owner_name
    parts = ['%s may %s' % (you, can(mode & stat.S_IRUSR, mode & stat.S_IWUSR)),
             'others in the group %s may %s' % (group_name, can(mode & stat.S_IRGRP, mode & stat.S_IWGRP)),
             'everyone else may %s' % can(mode & stat.S_IROTH, mode & stat.S_IWOTH)]
    return '; '.join(parts) + '.'


def opens_with(path, query=None):
    """The app that opens this kind of file (the system's default, xdg-mime), in its own name, or ''."""
    kind = mimetypes.guess_type(str(path))[0] or ('inode/directory' if Path(path).is_dir() else '')
    if not kind:return ''
    if query is None:
        def query(k):
            if not shutil.which('xdg-mime'):return ''
            try:return subprocess.run(['xdg-mime', 'query', 'default', k], capture_output=True, text=True, timeout=3).stdout.strip()
            except (OSError, subprocess.SubprocessError):return ''
    desktop = query(kind)
    if not desktop:return ''
    for folder in (Path.home() / '.local/share/applications', Path('/usr/local/share/applications'), Path('/usr/share/applications')):
        entry = folder / desktop
        try:
            for line in entry.read_text(encoding='utf-8', errors='replace').splitlines():
                if line.startswith('Name='):return line[5:].strip()
        except OSError:
            continue
    return desktop[:-8] if desktop.endswith('.desktop') else desktop


def properties(path, query=None):
    """Properties' rows, in order: [(label, words)]."""
    import grp
    import pwd
    path = Path(path)
    st = path.lstat()
    if path.is_symlink():kind = 'A link to %s' % os.readlink(path)
    elif path.is_dir():kind = 'A folder'
    else:
        guessed = mimetypes.guess_type(str(path))[0]
        kind = ('A %s file' % path.suffix[1:].upper() if path.suffix else 'A file') + (' (%s)' % guessed if guessed else '')
    if path.is_dir() and not path.is_symlink():
        try:
            inside = list(os.scandir(path))
            size = '%d thing%s inside' % (len(inside), '' if len(inside) == 1 else 's')
        except OSError:
            size = 'not readable here'
    else:size = _size_words(st.st_size)
    try:owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    try:group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    from . import home_reach as hr
    rows = [('Name', path.name), ('Kind', kind), ('Size', size), ('Where', hr.tilde(path.parent)),
            ('Changed', _when(st.st_mtime)), ('Opened', _when(st.st_atime)), ('Status changed', _when(st.st_ctime)),
            ('Who may', _who(st.st_mode, owner, group, st.st_uid == os.getuid()))]
    app = opens_with(path, query) if not path.is_dir() else ''
    rows.append(('Opens with', app or 'no app is set for this kind of file'))
    return rows


# ---- for good ----------------------------------------------------------------------------------------------------------------------
def delete_for_good(kernel, args, principal):
    """files.delete_for_good: the window asked first (Shift+Delete); removed without the bin. Your press only."""
    from . import home_reach as hr
    from .home_files_qt import changeable
    if hr.in_her_work(principal):
        raise ValueError('FILES_FOR_GOOD_OWNER_ONLY: deleting for good is your press only; Kas puts things in the bin')
    path = Path(os.path.abspath(hr.expand(str(args['path'])) or args['path']))
    if not os.path.lexists(path):raise ValueError('FILES_NOT_FOUND: ' + hr.tilde(path)[:200])
    where, why = changeable(kernel, path)
    if not where:raise ValueError('FILES_FOR_GOOD_NOT_HERE: %s is %s; only a file of your home or of Files is deleted for good' % (path.name, why))
    kind = 'folder' if path.is_dir() and not path.is_symlink() else 'file'
    if kind == 'folder':shutil.rmtree(path)
    else:path.unlink()
    from . import activity
    try:activity.record(kernel.root, principal.identity, 'files.delete_for_good', 'REQUEST_COMPLETED', str(path)[:300])
    except Exception:  # noqa: BLE001 - the record is a courtesy; the deletion is done and said
        pass
    return {'path': str(path), 'kind': kind, 'words': '%s was deleted for good (not in the bin; it cannot be put back).' % path.name}


def dispatch(kernel, op, args, principal):
    if op == 'files.delete_for_good':return delete_for_good(kernel, args, principal)
    raise ValueError('FILES_UNKNOWN_OPERATION')
