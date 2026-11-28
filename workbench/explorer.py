"""The Explorer's words and rules, without Qt (Graphite 1.1 E1). explorer_qt.py is the window's part.

PLAN_1.1.md, E1: the Files tree and the centre become an Explorer, with the bulletin board as its third view.

    the navigation pane   arrange(): the tree's rows in the Explorer's order: Quick access first (Home, Desktop, Documents,
                          Downloads, Pictures, Music: those that are there, the system's own names from user-dirs.dirs), then
                          the Desk (the drawers of records), then This computer (System (C:) is /, one press down; each
                          removable drive with its letter and free space), then the cabinet as it was. The bin is the can at
                          the pane's foot, after them.
    the views             List (Name, Modified, Type, Size, Links), Icons (thumbnails for pictures), Board (1.0's board of the
                          selected thing). Each folder remembers its view (explorer.json); a folder mostly of pictures opens
                          in Icons the first time, every other in List.
    the address           address(): a typed path: ~/x, /x, a path from the folder in front, or a DOS one (C:\\x, D:\\).
    the bin's word        "Recycle Bin" on a profile that starts with 1.1; a profile that has used 1.0 keeps DELETE
                          (session.Session marks which); Rules ▸ The bin's name changes it.

Nothing here writes anything but the Explorer's own small settings file ($XDG_CONFIG_HOME/graphite/explorer.json).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

QUICK = ('Desktop', 'Documents', 'Downloads', 'Pictures', 'Music')
XDG_KEYS = {'Desktop': 'XDG_DESKTOP_DIR', 'Documents': 'XDG_DOCUMENTS_DIR', 'Downloads': 'XDG_DOWNLOAD_DIR',
            'Pictures': 'XDG_PICTURES_DIR', 'Music': 'XDG_MUSIC_DIR'}
VIEWS = ('list', 'icons', 'board')
VIEW_WORDS = {'list': 'List', 'icons': 'Icons', 'board': 'Board'}
BIN_WORDS = ('Recycle Bin', 'DELETE')
NEW_BIN = 'Recycle Bin'          # a profile that starts with 1.1
OLD_BIN = 'DELETE'               # a profile that has used 1.0 (the owner's word of 14 November 2026)
PICTURES = frozenset(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff', '.ppm', '.pgm', '.ico'))
COLUMNS = ('Name', 'Modified', 'Type', 'Size', 'Links')
FIRST_ORDER = {0: 'up', 1: 'down', 2: 'up', 3: 'down', 4: 'down'}   # a first press on Modified, Size, Links: newest, largest, most first
MOST_VIEWS = 400                 # the folders whose view is remembered
QUICK_ID = 'living:quick'
FS = 'living:fs:'                # computer_tree_qt.FS
COMPUTER = 'living:computer'     # computer_tree_qt.COMPUTER
DRIVES = 'living:drives'
DESK = 'living:desk'             # living_nav_qt.DESK
SYSTEM_ID = FS + 'root:/'


# ---- Quick access --------------------------------------------------------------------------------------------------------------
def user_dirs(home, text=None):
    """{name: path} from the system's own user-dirs.dirs (xdg-user-dirs), where a folder has another name; else home/name."""
    home = Path(home);out = {name: home / name for name in QUICK}
    if text is None:
        base = os.environ.get('XDG_CONFIG_HOME') or str(home / '.config')
        try:text = (Path(base) / 'user-dirs.dirs').read_text(encoding='utf-8', errors='replace')
        except OSError:
            text = ''
    keys = {v: k for k, v in XDG_KEYS.items()}
    for line in text.splitlines():
        m = re.match(r'\s*(XDG_[A-Z]+_DIR)\s*=\s*"([^"]*)"', line)
        if not m or m.group(1) not in keys:continue
        value = m.group(2).replace('$HOME', str(home))
        if value.startswith('/') and Path(value) != home:out[keys[m.group(1)]] = Path(value)
    return out


def quick_places(home, text=None):
    """[(label, path)]: Home, then each of Desktop, Documents, Downloads, Pictures, Music that is a folder."""
    home = Path(home);out = [('Home', home)]
    for name, path in user_dirs(home, text).items():
        if path.is_dir():out.append((path.name if path.name != name and path.parent == home else name, path))
    return out


# ---- sizes and space -------------------------------------------------------------------------------------------------------------
def bytes_words(size):
    """1.2 GB, 340 KB, 12 bytes: short, as a column says it."""
    size = int(size or 0)
    for unit, step in (('TB', 1 << 40), ('GB', 1 << 30), ('MB', 1 << 20), ('KB', 1 << 10)):
        if size >= step:
            value = size / step
            return ('%.1f %s' % (value, unit)) if value < 100 else ('%d %s' % (round(value), unit))
    return '%d bytes' % size if size != 1 else '1 byte'


def space(path):
    """(free, total) bytes of the drive that holds path, or None."""
    try:
        usage = shutil.disk_usage(str(path))
        return usage.free, usage.total
    except OSError:
        return None


def space_words(path):
    got = space(path)
    return ('%s free of %s' % (bytes_words(got[0]), bytes_words(got[1]))) if got else 'space not read'


def letters(mounts=None):
    """{'C': '/', 'D': the first mounted drive, ...}: dos_words' letters, the same in the Terminal and here."""
    from .dos_words import drives
    return drives(mounts)


def letter_of(path, places):
    from .dos_words import drive_of
    return drive_of(str(path), places)


# ---- the tree in the Explorer's order ----------------------------------------------------------------------------------------
def node(ident, parent, role, label, canonical, description='', **extra):
    return dict(id=ident, parent=parent, role=role, label=label, target={'kind': 'living', 'id': canonical}, scope='owner_private',
                provider='living_nav', canonical_id=canonical, owning=False, description=description, **extra)


def subtree(nodes, top):
    """The ids of top and everything under it."""
    kids = {}
    for n in nodes:kids.setdefault(n['parent'], []).append(n['id'])
    out, todo = [], [top]
    while todo:
        ident = todo.pop(0)
        if ident in out:continue
        out.append(ident);todo.extend(kids.get(ident, ()))
    return out


def arrange(nodes, home_id, quick, canonical, places=None, spaces=None):
    """The rows in the Explorer's order (a new list; the given rows are copied, never changed):

    Quick access (the Home row and its folders moved here; then a row for each other quick place), the Desk (lifted to the
    top), This computer (System (C:) is the folder /, holding what was under This computer; then each removable drive with
    its letter and free space; the Drives drawer and its notes go), then everything else as it was.
    quick: [(label, path)] (Home first); canonical(path) -> the row's object id; places: {letter: path}; spaces(path) -> words.
    Returns (rows, {row id: path} for the rows made here)."""
    places = places or {'C': '/'};spaces = spaces or space_words
    rows = [dict(n) for n in nodes];by_id = {n['id']: n for n in rows};paths = {}
    if COMPUTER not in by_id:return rows, paths
    out = [node(QUICK_ID, None, 'drawer', 'Quick access', QUICK_ID, 'Quick access: Home and the folders you use most')]
    taken = set()
    if home_id in by_id:
        by_id[home_id]['parent'] = QUICK_ID
        moved = subtree(rows, home_id);out += [by_id[i] for i in moved];taken.update(moved)
    for label, path in quick[1:]:
        ident = FS + 'quick:' + str(path);paths[ident] = str(path)
        out.append(node(ident, QUICK_ID, 'folder', label, canonical(path), 'Quick access · %s' % path))
    if DESK in by_id:
        by_id[DESK]['parent'] = None
        moved = subtree(rows, DESK);out += [by_id[i] for i in moved];taken.update(moved)
    computer = by_id[COMPUTER];computer['label'] = 'This computer';taken.add(COMPUTER)
    computer['description'] = 'This computer: System (C:) is its top folder /, then each drive with its letter'
    out.append(computer)
    system = node(SYSTEM_ID, COMPUTER, 'folder', 'System (C:)', canonical('/'), 'System (C:): the top folder / · %s' % spaces('/'))
    paths[SYSTEM_ID] = '/';out.append(system)
    drives = [n for n in rows if n['parent'] == DRIVES and n.get('role') == 'drive']
    skip = set(subtree(rows, DRIVES)) if DRIVES in by_id else set()
    for n in rows:
        if n['parent'] == COMPUTER and n['id'] not in skip and n['id'] not in taken:
            n['parent'] = SYSTEM_ID
    for ident in [i for i in subtree(rows, COMPUTER) if i not in skip and i != COMPUTER and i not in taken]:
        out.append(by_id[ident]);taken.add(ident)
    for d in drives:
        d['parent'] = COMPUTER
        mounted = [n for n in rows if n['parent'] == d['id'] and n['id'].startswith(FS + 'drive:')]
        name = d['label'].split(' · ')[0]
        if mounted:
            where = mounted[0]['id'][len(FS + 'drive:'):]
            d['label'] = '%s (%s:) · %s' % (name, letter_of(where, places), spaces(where))
        else:
            d['label'] = '%s · not mounted' % name
        for ident in subtree(rows, d['id']):
            out.append(by_id[ident]);taken.add(ident)
    taken.update(skip);taken.update(o['id'] for o in out)
    out += [n for n in rows if n['id'] not in taken]
    return out, paths


# ---- the views a folder remembers ----------------------------------------------------------------------------------------------
def settings_file(environ=None):
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_CONFIG_HOME') or os.path.join(environ.get('HOME') or str(Path.home()), '.config')
    return Path(base) / 'graphite' / 'explorer.json'


def read(environ=None):
    try:
        got = json.loads(settings_file(environ).read_text(encoding='utf-8'))
        views = got.get('views') if isinstance(got, dict) else None
        return {'views': {str(k): v for k, v in (views or {}).items() if v in VIEWS}}
    except (OSError, ValueError, AttributeError):
        return {'views': {}}


def write(data, environ=None):
    path = settings_file(environ)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp');temp.write_text(json.dumps(data, indent=1), encoding='utf-8');os.replace(temp, path)
    except OSError:
        pass
    return data


def pictures_mostly(entries):
    files = [e for e in entries if e.get('kind') != 'folder']
    if len(files) < 2:return False
    return sum(1 for e in files if is_picture(e.get('name', ''))) * 2 > len(files)


def view_for(path, entries=(), saved=None):
    """The view a folder opens in: the one it was left in, else Icons for a folder mostly of pictures, else List."""
    saved = read()['views'] if saved is None else saved
    got = saved.get(str(path))
    if got in VIEWS:return got
    return 'icons' if pictures_mostly(entries) else 'list'


def remember_view(path, view, environ=None):
    if view not in VIEWS:return None
    data = read(environ);views = data['views'];views.pop(str(path), None);views[str(path)] = view
    while len(views) > MOST_VIEWS:views.pop(next(iter(views)))
    return write(data, environ)


# ---- a typed path ----------------------------------------------------------------------------------------------------------------
def address(text, here, home, places=None):
    """The folder or file a typed address names, as a whole path; '' when it names nothing that is there.
    ~ and ~/x are Home's, /x is the computer's, x is the folder in front's, and C:\\x, D:\\ and \\x are DOS's."""
    text = str(text or '').strip().strip('"')
    if not text:return ''
    if text.lower().startswith('file://'):text = text[7:]
    if re.match(r'^[A-Za-z]:', text) or '\\' in text:
        from .dos_words import to_path
        try:text = to_path(text, str(here or home), places or letters())
        except LookupError:
            return ''
    if text == '~' or text.startswith('~/'):text = str(home) + text[1:]
    path = Path(text) if text.startswith('/') else Path(here or home) / text
    path = Path(os.path.normpath(str(path)))
    return str(path) if path.exists() else ''


def is_picture(name):
    return Path(str(name)).suffix.lower() in PICTURES


# ---- sorting -----------------------------------------------------------------------------------------------------------------
def natural(name):
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r'(\d+)', str(name))]


def sort_key(entry, column, type_words=lambda e: ''):
    """What a column sorts by: names naturally, dates and sizes by value, types by their words, links by their count."""
    name = natural(entry.get('name', ''))
    if column == 1:return (float(entry.get('modified') or 0.0), name)
    if column == 2:return (type_words(entry).casefold(), name)
    if column == 3:return (int(entry.get('bytes') if entry.get('bytes') is not None else -1), name)
    if column == 4:return (int(entry.get('links') or 0), name)
    return (name,)


def ordered(entries, column, descending=False, type_words=lambda e: ''):
    """Folders first in either direction (as Windows keeps them), then the column's order."""
    folders = sorted((e for e in entries if e.get('kind') == 'folder'), key=lambda e: sort_key(e, column, type_words), reverse=descending)
    files = sorted((e for e in entries if e.get('kind') != 'folder'), key=lambda e: sort_key(e, column, type_words), reverse=descending)
    return folders + files


# ---- thumbnails' cache ---------------------------------------------------------------------------------------------------------
def thumbs_dir(environ=None):
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_CACHE_HOME') or os.path.join(environ.get('HOME') or str(Path.home()), '.cache')
    return Path(base) / 'graphite' / 'thumbs'


def thumb_name(path, size, mtime_ns, px):
    return hashlib.sha1(('%s|%d|%d|%d' % (path, int(size), int(mtime_ns), int(px))).encode('utf-8', 'surrogateescape')).hexdigest() + '.png'


# ---- the bin's word ----------------------------------------------------------------------------------------------------------
def bin_word(state):
    """The bin's name for this profile: what the session says (session.Session marks a new profile Recycle Bin and one that
    has used 1.0 DELETE); DELETE when nothing says."""
    word = (state or {}).get('bin_word') if isinstance(state, dict) else None
    return word if word in BIN_WORDS else OLD_BIN


def in_words(words, word):
    """A line written with DELETE as the bin's name, said with this profile's name for it."""
    if word == OLD_BIN or not words:return words
    return re.sub(r'\bDELETE\b', 'the ' + word if word == NEW_BIN else word, str(words)).replace('the the ', 'the ')
