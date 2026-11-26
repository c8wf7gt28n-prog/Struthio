"""Bulk files (Graphite 1.0 L6c): many files moved, copied or deleted in one press, with one Undo for the batch.

PLAN_1.0.md, L6c (added at X4's merge, 26 Nov: "the power user's first want"): "The Files tree selects many rows (click, a
range, add one); Move to…, Copy to… and Delete act on all of them in one press, with one line and one Undo for the batch. A
line can move or delete what it lists, as a step that asks (one press, the count and the folder shown; Undo for the batch)."
X4 found a bulk tidy took 48 presses and 48 Undos (session 3); this is the one press and the one Undo.

ONE CHANGE FOR THE BATCH. files.batch writes the batch down before it acts (what is prepared: every file it is to touch),
then acts file by file with the same rules as one file's Move to…, Copy to… and Delete (files_service: the Files rules,
home_reach for her, a free name where a name is taken, nothing overwritten; Delete is DELETE: your home's own bin, the
freedesktop.org one, for a file of your home, Files' own for a file of Files), then writes down each file's before and after
(its place, and the inode, size and time it has there). files.batch_undo puts the whole batch back as one: each moved file
back to its old place, each copy into DELETE, each deleted file out of DELETE where it was. What changed since is never
forced: a file no longer where the batch left it, an old place taken by another file, a copy changed since it was made, a
deletion restored already, is left as it is and named, and the rest are put back. A folder the batch made for a move is
taken away again only when it is empty.

WHAT A BATCH TOUCHES. Files and folders of your home and of Files, as the tree offers them (home_files_qt.changeable): never
your home folder itself, Files itself, Graphite's own records or program, a folder that holds Graphite's workspace, DELETE's
own folder, or anything outside your home. A folder chosen with something inside it carries it: the thing inside is left out
of the list ("goes with its folder"). The owner's press dispatches it with the owner's principal; anything of hers would pass
files_service.may_change (home_reach.her_change and her grants) file by file, as one file's change does.

A LINE THAT MOVES OR DELETES. The last step of a line may be `move to FOLDER`, `copy to FOLDER` or `delete`: split_act()
takes it off, the line before it reads as every line reads (language's own registered read, never a change), and
files.batch_plan says what one press would do (the count, the folder, the first few names, what is left out and why) before
anything moves. The press is the owner's; the window's console shows the plan and the press (bulk_files_qt). A line that
starts from `@files:<a folder>` reads that folder's files and folders (files.list … | pick entries), so
`@files:~/Downloads | where name has invoice-2026 | move to ~/Documents/Invoices 2026` lists the invoices it moves.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 L6c):
  files.batch_plan  {act, paths | line, to?}         read      what one press would do; nothing is changed
  files.batch       {act, paths, to?, make?, line?}  execute   done in one press; recorded as one change, every file's before and after
  files.batch_undo  {batch}                          approve   the whole batch put back as one; what changed since is named, never forced
  files.batches     {limit?}                         read      the batches lately done, newest first (an observer)

No floating point here: times are whole milliseconds, sizes bytes.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from . import home_reach as hr

ACTS = ('move', 'copy', 'delete')
MOST = 1000                    # files in one batch, at most (the Kernel's arrays hold 1000)
SHOWN = 5                      # names shown before the press
LEFT_SHOWN = 3                 # left-out names said in a sentence
ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
PATHS = {'type': 'array', 'items': PATH}
ACT = {'type': 'string', 'enum': list(ACTS)}
LINE = {'type': 'string', 'minLength': 1, 'maxLength': 8192}
FIELDS = {
    'files.batch_plan': ({'act': ACT, 'paths': PATHS, 'line': LINE, 'to': PATH}, ['act']),
    'files.batch': ({'act': ACT, 'paths': PATHS, 'to': PATH, 'make': {'type': 'boolean'}, 'line': LINE}, ['act', 'paths']),
    'files.batch_undo': ({'batch': ID}, ['batch']),
    'files.batches': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 50}}, []),
}
SCOPES = {'files.batch_plan': 'read', 'files.batch': 'execute', 'files.batch_undo': 'approve', 'files.batches': 'read'}
OBSERVERS = ('files.batches',)
VERB = {'move': 'Move', 'copy': 'Copy', 'delete': 'Delete'}
DONE = {'move': 'Moved', 'copy': 'Copied', 'delete': 'Deleted'}
# the last step of a line that changes what it lists: move to FOLDER, copy to FOLDER, delete (them)
ACT_STEP = re.compile(r'^(?:(move|copy)\s+(?:them\s+|these\s+)?(?:to|into)\s+(.+?)|(delete)(?:\s+them|\s+these)?)\s*$', re.I)


def _now_ms():
    return time.time_ns() // 1_000_000


def _why(exc):
    """A refusal's words without its code ('FILES_EXISTS: that name is taken here' -> 'that name is taken here')."""
    text = str(exc)
    head, sep, rest = text.partition(': ')
    return rest if sep and re.fullmatch(r'[A-Z][A-Z0-9_]+', head) else text


# ---- a line's last step ---------------------------------------------------------------------------------------------------------
def _last_bar(text):
    """The index of the last | outside double quotes (as typed_pipeline.split reads a line), or -1."""
    quote = escape = False;last = -1
    for index, char in enumerate(text):
        if escape:escape = False;continue
        if char == '\\' and quote:escape = True;continue
        if char == '"':quote = not quote
        elif char == '|' and not quote:last = index
    return last if not quote else -1


def split_act(text):
    """A line whose last step moves, copies or deletes what it lists: (the line that reads, {'act', 'to', 'step'}); any other
    line: (text, None). The line that reads is left exactly as typed."""
    if not isinstance(text, str):return text, None
    at = _last_bar(text)
    if at < 0:return text, None
    found = ACT_STEP.match(text[at + 1:].strip())
    head = text[:at].strip()
    if not found or not head:return text, None
    if found.group(3):return head, {'act': 'delete', 'to': '', 'step': text[at + 1:].strip()}
    to = found.group(2).strip()
    if len(to) >= 2 and to[0] == to[-1] == '"':to = to[1:-1]
    return head, {'act': found.group(1).lower(), 'to': to, 'step': text[at + 1:].strip()}


def folder_line(kernel, line):
    """`@files:<a folder> | …` reads that folder's files and folders (files.list … | pick entries) for a line that acts on
    what it lists; any other line as typed. Returns (the line that is read, the folder in words or '')."""
    text = str(line or '').strip()
    if not text.startswith('@files:'):return text, ''
    head, sep, rest = text.partition('|')
    named = head[len('@files:'):].strip()
    if not named:return text, ''
    from . import files_service
    try:folder = files_service.resolve(kernel, named)
    except ValueError:
        return text, ''
    if not folder.is_dir():return text, ''
    read = 'files.list %s | pick entries' % json.dumps({'path': named}, ensure_ascii=False, separators=(',', ':'))
    return read + ((' |' + rest) if sep else ''), hr.tilde(folder)


def line_rows(kernel, line, principal):
    """The rows a line lists, read as language.run reads them (a registered read; never a change), up to MOST rows."""
    from . import stacy_language as sl
    read, folder = folder_line(kernel, line)
    plan = sl._compile_plan(kernel, read, principal)
    sides = sl._joined_plans(kernel, plan, principal)
    try:out = sl._execute_plan(kernel, plan, principal, sides, MOST)
    except ValueError as exc:
        if 'exceeds' in str(exc):raise ValueError('FILES_BATCH_TOO_MANY: the line lists more than %d rows; narrow it first' % MOST) from None
        raise
    return out['rows'], read, folder


def row_paths(rows):
    """The paths of a line's rows: each row's 'path' (a file of Files by its path there, anything else by its whole path)."""
    paths, without = [], 0
    for row in rows or ():
        place = row.get('path') if isinstance(row, dict) else None
        if isinstance(place, str) and place.strip():paths.append(place)
        else:without += 1
    return paths, without


# ---- what a batch may touch -------------------------------------------------------------------------------------------------------
def _files_root(kernel):
    try:return hr.files_root(kernel).resolve()
    except (OSError, RuntimeError):
        return hr.files_root(kernel)


class Reach:
    """changeable() for many paths: the places it compares with (your home, Files, Graphite's own, DELETE's folder) are read
    once, and each folder's real place once, so a choice of a few hundred rows is weighed without asking the system again for
    each (the rules are home_files_qt.changeable's and home_reach.area's, in the same order)."""

    def __init__(self, kernel):
        from . import files_service
        from .home_trash import trash_dir
        self.home = hr.home();self.files = _files_root(kernel)
        self.own = []
        for folder in hr.own_folders(kernel):
            try:self.own.append(Path(folder).resolve())
            except (OSError, RuntimeError):
                self.own.append(Path(folder))
        self.trash = os.path.normpath(str(trash_dir()))
        self.kept = (self.files / files_service.TRASH, self.files / files_service.VERSIONS)
        self.stay = (self.files / files_service.SLATE, self.files / files_service.EXPORTS)
        self.parents = {}

    def real_parent(self, path):
        key = str(path.parent)
        if key not in self.parents:self.parents[key] = Path(os.path.realpath(path.parent))
        return self.parents[key]

    def area(self, named, actual):
        if hr.is_system(named) or hr.is_system(actual):return hr.SYSTEM
        if hr.within(actual, self.files):return hr.FILES
        if any(hr.within(actual, own) for own in self.own):return hr.OWN
        if hr.within(actual, self.home):return hr.HOME
        return hr.OUTSIDE

    def __call__(self, path):
        path = Path(path)
        try:
            parent = self.real_parent(path);place = parent / path.name
            link = path.is_symlink()
            where = self.area(place, parent if link else place)
            folder = path.is_dir() and not link
        except (OSError, RuntimeError):
            return '', 'not readable here'
        if where not in (hr.HOME, hr.FILES):return '', hr.AREA_WORDS.get(where, where)
        if place == self.home:return '', 'your home folder itself'
        if place == self.files:return '', "the workspace's Files folder itself"
        if where == hr.FILES:
            if any(hr.within(place, k) for k in self.kept):return '', 'kept by Graphite (DELETE and the versions)'
            if place in self.stay:return '', 'the Slate folder and Egress stay where they are'
        text = os.path.normpath(str(place))
        if text == self.trash or text.startswith(self.trash + '/') or self.trash.startswith(text.rstrip('/') + '/'):
            return '', "DELETE's own folder, or it holds it"
        if folder and any(hr.within(mine, place) for mine in [self.files] + self.own):return '', "it holds Graphite's workspace"
        return where, ''


def changeable(kernel, path, reach=None):
    """(area, '') when a batch may change this file or folder (as the tree offers it: home_files_qt.changeable); else ('', why).
    Give `reach` (a Reach) when weighing many."""
    return (reach or Reach(kernel))(path)


def _destination(kernel, act, to):
    """(the folder, whether it is to be made first) for move and copy; refused in words when it may not be one."""
    from . import files_service
    from .home_trash import trash_dir
    if act == 'delete':return None, False
    if not to or not str(to).strip():raise ValueError('FILES_BATCH_WHERE: say the folder: %s to <a folder>' % act)
    folder = files_service.resolve(kernel, str(to).strip(), must_exist=False)
    actual = hr.real(folder)
    where = hr.area(kernel, actual)
    if where not in (hr.HOME, hr.FILES):
        raise ValueError('FILES_BATCH_OUTSIDE: %s is %s; a batch lands only in your home or in Files' % (hr.tilde(folder)[:200], hr.AREA_WORDS.get(where, where)))
    if hr.within(actual, hr.real(trash_dir())):raise ValueError("FILES_BATCH_DELETE: %s is DELETE's own folder: use Delete" % hr.tilde(folder)[:200])
    if folder.exists() and not folder.is_dir():raise ValueError('FILES_NOT_A_FOLDER: %s is a file, not a folder' % hr.tilde(folder)[:200])
    if folder.exists():return actual, False
    if not folder.parent.is_dir():
        raise ValueError('FILES_BATCH_NO_FOLDER: %s is not there, and neither is the folder it would be made in' % hr.tilde(folder)[:200])
    return hr.real(folder.parent) / folder.name, True


def _resolve(kernel, text, reach):
    """files_service.resolve for a batch: a path named from / or ~ outside Files is found here with the places read once (the
    same refusals: a climb, a system folder, not there); a path of Files, or named inside Files, goes through Files' own rules."""
    from . import files_service
    if isinstance(text, str) and text.startswith(('/', '~')):
        named = hr.expand(text)
        if named is None:raise ValueError('FILES_PATH_INVALID: a path with no ".."')
        try:actual = reach.real_parent(named) / named.name
        except (OSError, RuntimeError):
            actual = named
        if hr.is_system(named) or hr.is_system(actual):raise ValueError('FILES_SYSTEM_FOLDER: %s (%s)' % (hr.SYSTEM_WORDS, os.path.normpath(str(named))[:200]))
        if not hr.within(actual, reach.files) and not (named.is_symlink() and hr.within(hr.real(named), reach.files)):
            if not os.path.lexists(named):raise ValueError('FILES_NOT_FOUND: ' + hr.tilde(named)[:200])
            return named
    return files_service.resolve(kernel, text)


def _may(kernel, path, principal):
    """files_service.may_change, which lets your own press through everywhere it is asked (your home, and Files with your
    approve scope): asked for her work only, where her rules decide (home_reach.her_change, her grants, the Files rules)."""
    if hr.in_her_work(principal):
        from . import files_service
        files_service.may_change(kernel, path, principal)


def _listed(kernel, act, texts, folder):
    """The things a batch acts on, in the order given (each once), and those left out with why."""
    items, left, seen = [], [], set();reach = Reach(kernel)
    for text in texts:
        try:path = _resolve(kernel, text, reach)
        except ValueError as exc:
            left.append({'path': str(text), 'name': Path(str(text)).name, 'why': _why(exc)});continue
        path = Path(os.path.abspath(path))
        if str(path) in seen:continue
        seen.add(str(path))
        where, why = reach(path)
        if not where:left.append({'path': str(path), 'name': path.name, 'why': why});continue
        if folder is not None:
            if act == 'move' and reach.real_parent(path) == folder:
                left.append({'path': str(path), 'name': path.name, 'why': 'it is in %s already' % hr.tilde(folder)});continue
            if path.is_dir() and not path.is_symlink() and hr.within(folder, reach.real_parent(path) / path.name):
                left.append({'path': str(path), 'name': path.name, 'why': 'it would go inside itself'});continue
        items.append(path)
    chosen = {str(p) for p in items if p.is_dir() and not p.is_symlink()}
    kept = []
    for path in items:      # a thing inside a chosen folder goes with its folder
        holder = next((Path(c) for c in chosen if c != str(path) and hr.within(path, Path(c))), None)
        if holder is not None:left.append({'path': str(path), 'name': path.name, 'why': 'it goes with its folder %s' % holder.name})
        else:kept.append(path)
    return kept, left


def counted(paths, kinds=None):
    """'48 files', '1 folder', '2 folders and 10 files'."""
    folders = sum(1 for p in paths if (kinds.get(str(p)) == 'folder' if kinds else (Path(p).is_dir() and not Path(p).is_symlink())))
    files = len(paths) - folders
    parts = [('%d folder%s' % (folders, '' if folders == 1 else 's')) if folders else '', ('%d file%s' % (files, '' if files == 1 else 's')) if files or not folders else '']
    return ' and '.join(p for p in parts if p)


def _left_words(left, verb='left as it was'):
    if not left:return ''
    shown = '; '.join('%s (%s)' % (l['name'], l['why']) for l in left[:LEFT_SHOWN])
    more = ' and %d more' % (len(left) - LEFT_SHOWN) if len(left) > LEFT_SHOWN else ''
    return ' %d %s %s: %s%s.' % (len(left), 'was' if len(left) == 1 else 'were', verb if len(left) == 1 else verb.replace('it was', 'they were'), shown, more)


def _from_words(paths):
    folders = sorted({str(Path(p).parent) for p in paths})
    return hr.tilde(folders[0]) if len(folders) == 1 else '%d folders' % len(folders)


# ---- the plan ---------------------------------------------------------------------------------------------------------------------
def plan(kernel, args, principal):
    """files.batch_plan: what one press would do, in words and in full (the paths it would act on, exactly), nothing changed."""
    act = args['act'];read = folder_words = '';rows = without = 0
    if args.get('line'):
        found, read, folder_words = line_rows(kernel, args['line'], principal)
        texts, without = row_paths(found);rows = len(found)
        if found and not texts:
            raise ValueError('FILES_BATCH_NO_PATHS: the line lists %d rows, none with a path: a line moves, copies or deletes the files it lists '
                             '(start it from @files:<a folder>)' % rows)
    elif 'paths' in args:texts = list(args['paths'])
    else:raise ValueError('FILES_BATCH_WHAT: give the paths, or the line that lists them')
    if len(texts) > MOST:raise ValueError('FILES_BATCH_TOO_MANY: at most %d in one batch' % MOST)
    folder, make = _destination(kernel, act, args.get('to'))
    items, left = _listed(kernel, act, texts, folder)
    names = [p.name for p in items]
    count = counted(items)
    where = hr.tilde(folder) if folder is not None else ''
    if not items:
        words = 'Nothing to %s: %s' % (act, ('the line lists no file.' if not texts else 'none of them can be changed from here.' + _left_words(left)))
    elif act == 'delete':
        words = '%s %s from %s into DELETE (restore puts each back; Undo puts them all back).' % (VERB[act], count, _from_words(items))
    else:
        words = '%s %s to %s%s.' % (VERB[act], count, where, ' (not there yet: it is made first)' if make else '')
    if items:
        shown = ', '.join(names[:SHOWN]) + (' and %d more' % (len(names) - SHOWN) if len(names) > SHOWN else '')
        words += ' ' + shown + '.' + _left_words(left, 'left out')
    press = ('%s the %s' % (VERB[act], count) if len(items) > 1 else '%s %s' % (VERB[act], names[0])) if items else ''
    return {'act': act, 'count': len(items), 'count_words': count, 'paths': [str(p) for p in items], 'names': names[:SHOWN],
            'more': max(0, len(names) - SHOWN), 'folder': where, 'to': str(folder) if folder is not None else '', 'make': make,
            'left': left, 'words': words, 'press': press, 'line': read, 'read_from': folder_words, 'rows': rows, 'without_path': without}


# ---- the batch --------------------------------------------------------------------------------------------------------------------
def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS files_batches(id TEXT PRIMARY KEY, owner TEXT, act TEXT, folder TEXT, at INTEGER, state TEXT,
                  items TEXT, left TEXT, made TEXT, undone INTEGER, line TEXT)''')


def _stat(path):
    st = os.lstat(path)
    return {'ino': int(st.st_ino), 'size': int(st.st_size), 'mtime_ns': int(st.st_mtime_ns)}


def _same(path, item, keys=('ino',)):
    try:now = _stat(path)
    except OSError:
        return False
    return all(now.get(k) == item.get(k) for k in keys)


def carry_all(kernel, pairs):
    """Each moved thing (and everything inside a moved folder) keeps its object's id at its new place, in one pass over the
    identity store (living_nav.moved does one at a time). Never fails the batch: the next reading of the tree finds them by
    their inodes all the same."""
    if not pairs:return 0
    try:
        from . import living_nav as ln
        base = ln.files_root(kernel, create=False);real_base = Path(base).resolve()

        def kept_as(path):      # living_nav._kept_as, with Files' real place found once
            try:return ln.rel_of(base, path)
            except ValueError:
                try:return ln.rel_of(real_base, Path(path))
                except ValueError:
                    return str(Path(path))
        moves = [(kept_as(old), kept_as(new)) for old, new in pairs]
        count = 0
        with kernel.db() as db:
            ln.ensure(db)
            rows = ln._rows(db)
            by_path = {}
            for row in rows.values():by_path.setdefault(row['path'], []).append(row['id'])
            for was, now in moves:
                if not was:continue
                touched = list(by_path.get(was, ()))
                prefix = was + '/'
                touched += [i for p, ids in by_path.items() if p.startswith(prefix) for i in ids]
                for ident in touched:
                    row = rows[ident]
                    if row['state'] == ln.MISSING or not ln.under(row['path'], was):continue
                    path = now + row['path'][len(was):]
                    new = dict(row, path=path, state=ln.DELETED if ln.in_delete(path) else ln.PRESENT, names=ln._earlier(row, row['path']))
                    ln._save(db, new);rows[ident] = new;count += 1
        return count
    except Exception:  # noqa: BLE001 - the identity follows at the next reading of the tree
        return 0


def _put_in_delete(kernel, path, principal, rows, pairs, reach=None):
    """One thing into DELETE as Delete puts it there (files_service files.trash); its row for files_trash kept in `rows` and
    written once for the whole batch. Returns its DELETE id and its name there. `reach` weighs it with the places read once
    (its refusals are home_trash.holds_graphite's and in_home's)."""
    from . import files_service, home_trash
    if reach is not None:
        where, why = reach(path)
        if not where:raise ValueError('FILES_RESERVED: %s; it stays' % why)
        home = where == hr.HOME
    else:
        if home_trash.holds_graphite(kernel, path):raise ValueError("FILES_RESERVED: it is your home or holds Graphite's workspace; it stays")
        home = home_trash.in_home(kernel, path)
    if home:
        _may(kernel, path, principal)
        put = home_trash.put(path)
        ident = uuid.uuid4().hex
        rows.append((ident, principal.identity, put['original'], home_trash.STORED + put['name'], time.time()))
        pairs.append((path, Path(put['stored'])))
        return ident, put['name']
    got = files_service.dispatch(kernel, 'files.trash', {'path': str(path)}, principal)      # a file of Files: Files' own DELETE
    return got['id'], ''


def _write_trash_rows(kernel, rows):
    if not rows:return
    from . import files_service
    with files_service.opened(kernel) as db:
        db.executemany('INSERT INTO files_trash VALUES(?,?,?,?,?,NULL)', rows)


def run(kernel, args, principal):
    """files.batch: the batch done in one press, recorded before (what is prepared) and after (every file's before and after)."""
    from . import files_service
    act = args['act']
    if len(args['paths']) > MOST:raise ValueError('FILES_BATCH_TOO_MANY: at most %d in one batch' % MOST)
    folder, make = _destination(kernel, act, args.get('to'))
    if make and not args.get('make'):
        raise ValueError('FILES_BATCH_NO_FOLDER: %s is not there; say make it (the plan offers it)' % hr.tilde(folder)[:200])
    items, left = _listed(kernel, act, args['paths'], folder)
    if not items:raise ValueError('FILES_BATCH_NOTHING: nothing to %s here.%s' % (act, _left_words(left)))
    ident = uuid.uuid4().hex;at = _now_ms()
    kinds = {str(p): ('folder' if p.is_dir() and not p.is_symlink() else 'file') for p in items}
    prepared = [{'from': str(p), 'kind': kinds[str(p)], 'back': False, 'done': False} for p in items]
    with files_service.opened(kernel) as db:      # what is prepared, written before anything is touched
        ensure(db)
        db.execute('INSERT INTO files_batches VALUES(?,?,?,?,?,?,?,?,?,NULL,?)',
                   (ident, principal.identity, act, str(folder or ''), at, 'running', json.dumps(prepared), json.dumps(left), '', str(args.get('line') or '')[:2000]))
    made = ''
    if make:
        files_service.dispatch(kernel, 'files.mkdir', {'path': str(folder.parent), 'name': folder.name}, principal);made = str(folder)
    done, failed, pairs, trash_rows = [], [], [], []
    reach = Reach(kernel);stay = reach.stay
    for item in prepared:
        path = Path(item['from'])
        try:
            if act == 'move':
                _may(kernel, path, principal)
                target = files_service.free_name(folder, path.name)
                _may(kernel, target, principal)
                if path in stay:raise ValueError('FILES_RESERVED: the Slate folder and Egress stay where they are')
                shutil.move(str(path), str(target));pairs.append((path, target))
                item.update(to=str(target), renamed=target.name != path.name, **_stat(target))
            elif act == 'copy':
                target = files_service.free_name(folder, path.name)
                _may(kernel, target, principal)
                if path.is_dir() and not path.is_symlink():shutil.copytree(path, target, symlinks=True)
                else:shutil.copy2(path, target, follow_symlinks=False)
                item.update(to=str(target), renamed=target.name != path.name, **_stat(target))
            else:
                trash_id, stored = _put_in_delete(kernel, path, principal, trash_rows, pairs, reach)
                item.update(trash_id=trash_id, stored=stored)
            item['done'] = True;done.append(item)
        except (ValueError, OSError, shutil.Error) as exc:
            failed.append({'path': str(path), 'name': path.name, 'why': _why(exc) if isinstance(exc, ValueError) else (getattr(exc, 'strerror', '') or str(exc))[:200]})
    _write_trash_rows(kernel, trash_rows)
    carry_all(kernel, pairs)
    left = left + failed
    state = 'done' if done else 'not done'
    with files_service.opened(kernel) as db:
        ensure(db)
        db.execute('UPDATE files_batches SET state=?, items=?, left=?, made=? WHERE id=?', (state, json.dumps(done), json.dumps(left), made, ident))
    return _result(ident, act, folder, done, left, made, kinds)


def _result(ident, act, folder, done, left, made, kinds):
    froms = [d['from'] for d in done];count = counted(froms, kinds)
    where = hr.tilde(folder) if folder is not None else ''
    renamed = [d for d in done if d.get('renamed')]
    if not done:words = 'Nothing was %s.%s' % ({'move': 'moved', 'copy': 'copied', 'delete': 'deleted'}[act], _left_words(left))
    elif act == 'move':words = 'Moved %s to %s%s.' % (count, where, ' (made first)' if made else '')
    elif act == 'copy':words = 'Copied %s to %s%s; the originals stay where they were.' % (count, where, ' (made first)' if made else '')
    else:words = '%s %s in DELETE (from %s).' % (count[0].upper() + count[1:], 'is' if len(done) == 1 else 'are', _from_words(froms))
    if renamed:
        words += ' %d took a free name there (the name was taken): %s.' % (len(renamed), ', '.join('%s as %s' % (Path(d['from']).name, Path(d['to']).name) for d in renamed[:LEFT_SHOWN]))
    if done:words += _left_words(left)
    back = {'move': 'the %s %s back in %s' % (count, 'is' if len(done) == 1 else 'are', _from_words(froms)),
            'copy': 'the %s %s in DELETE' % ('copy' if len(done) == 1 else '%d copies' % len(done), 'is' if len(done) == 1 else 'are'),
            'delete': 'the %s %s back where %s %s' % (count, 'is' if len(done) == 1 else 'are', 'it' if len(done) == 1 else 'they', 'was' if len(done) == 1 else 'were')}[act]
    return {'batch': ident, 'act': act, 'done': len(done), 'count_words': count, 'folder': where, 'made': hr.tilde(made) if made else '',
            'paths': [d.get('to') or d['from'] for d in done], 'from': froms, 'left': left, 'words': words, 'undo_words': back if done else ''}


# ---- one Undo for the batch ----------------------------------------------------------------------------------------------------
def _load(kernel, ident, owner):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        row = db.execute('SELECT * FROM files_batches WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if row is None:raise ValueError('FILES_BATCH_NOT_FOUND: that batch is not known here')
    return dict(row)


def _prepared_trash(kernel, item, since_ms, owner):
    """A deletion the batch was making when it stopped (no id written yet): its DELETE row by its old place, made after the batch began."""
    from . import files_service
    with files_service.opened(kernel) as db:
        row = db.execute('SELECT id FROM files_trash WHERE owner=? AND original=? AND restored IS NULL AND at>=? ORDER BY at DESC',
                         (owner, item['from'], since_ms / 1000)).fetchone()
    return row['id'] if row is not None else ''


def undo(kernel, args, principal):
    """files.batch_undo: the whole batch put back as one; what changed since is left as it is and named."""
    from . import files_service
    row = _load(kernel, args['batch'], principal.identity)
    if row['state'] == 'undone':raise ValueError('FILES_BATCH_UNDONE: it was put back already')
    act = row['act'];items = json.loads(row['items'] or '[]')
    if row['state'] == 'running':      # stopped half way (a crash): each prepared file is looked for where the batch would have left it
        for item in items:
            if act == 'delete' and not item.get('trash_id'):item['trash_id'] = _prepared_trash(kernel, item, row['at'], principal.identity)
            item['done'] = bool(item.get('trash_id')) if act == 'delete' else bool(item.get('to'))
    back, not_back, pairs, copies, restored, already = [], [], [], [], [], []
    reach = Reach(kernel)
    still = {}
    if act == 'delete':      # which of its deletions are still in DELETE (one that was restored since is never taken out again)
        from . import home_trash
        ids = [i['trash_id'] for i in items if i.get('trash_id')]
        with files_service.opened(kernel) as db:
            for start in range(0, len(ids), 500):
                part = ids[start:start + 500]
                still.update({r['id']: r['restored'] is None for r in db.execute('SELECT id, restored FROM files_trash WHERE owner=? AND id IN (%s)' % ','.join('?' * len(part)),
                                                                                (principal.identity, *part))})
    for item in reversed(items):
        if item.get('back') or not item.get('done'):continue
        name = Path(item['from']).name
        try:
            if act == 'move':
                now, old = Path(item['to']), Path(item['from'])
                if not os.path.lexists(now):raise ValueError('it is no longer in %s' % hr.tilde(now.parent))
                if not _same(now, item):raise ValueError('another file is at its place in %s now' % hr.tilde(now.parent))
                if os.path.lexists(old):raise ValueError('its old place in %s is taken now' % hr.tilde(old.parent))
                if not old.parent.is_dir():raise ValueError('its old folder %s is gone' % hr.tilde(old.parent))
                _may(kernel, now, principal);_may(kernel, old, principal)
                shutil.move(str(now), str(old));pairs.append((now, old))
            elif act == 'copy':
                now = Path(item['to'])
                if not os.path.lexists(now):raise ValueError('the copy is no longer in %s' % hr.tilde(now.parent))
                keys = ('ino', 'mtime_ns') if item.get('kind') == 'folder' else ('ino', 'size', 'mtime_ns')
                if not _same(now, item, keys):raise ValueError('the copy changed since it was made: it stays in %s' % hr.tilde(now.parent))
                _put_in_delete(kernel, now, principal, copies, pairs, reach)
            elif item.get('stored') and item.get('trash_id') in still:      # your home's bin: back where it was (beside it when its name is taken)
                if not still[item['trash_id']]:      # restored from DELETE since, by your press: back already, nothing to do
                    item['back'] = True;item['already'] = True;already.append(item);continue
                try:put = home_trash.restore(item['stored'])
                except ValueError as exc:
                    if 'NOT_FOUND' in str(exc):raise ValueError('it is no longer in DELETE: the bin was emptied') from None
                    raise
                restored.append(item['trash_id']);pairs.append((Path(put['stored']), Path(put['restored'])))
                if put.get('renamed'):item['beside'] = put['restored']
            else:      # Files' own DELETE
                try:files_service.dispatch(kernel, 'files.restore', {'id': item['trash_id']}, principal)
                except ValueError as exc:
                    if 'NOT_FOUND' in str(exc):raise ValueError('it is no longer in DELETE: restored already, or the bin was emptied') from None
                    raise
            item['back'] = True;back.append(item)
        except (ValueError, OSError, shutil.Error) as exc:
            not_back.append({'name': name, 'why': _why(exc) if isinstance(exc, ValueError) else (getattr(exc, 'strerror', '') or str(exc))[:200]})
    _write_trash_rows(kernel, copies)
    if restored:
        with files_service.opened(kernel) as db:
            for start in range(0, len(restored), 500):
                part = restored[start:start + 500]
                db.execute('UPDATE files_trash SET restored=? WHERE restored IS NULL AND id IN (%s)' % ','.join('?' * len(part)), (time.time(), *part))
    carry_all(kernel, pairs)
    beside = [i for i in back if i.get('beside')]
    folder_words = (' %d went back beside %s old name%s, which another file has now.' % (len(beside), 'its' if len(beside) == 1 else 'their', '' if len(beside) == 1 else 's')
                    if beside else '')
    if row['made'] and act in ('move', 'copy'):
        made = Path(row['made'])
        try:
            if made.is_dir() and not any(made.iterdir()):made.rmdir();folder_words = ' The folder %s it made is gone again (it was empty).' % made.name
            elif made.is_dir():folder_words = ' The folder %s it made stays: it is not empty.' % made.name
        except OSError:
            folder_words = ' The folder %s it made stays.' % made.name
    done = [i for i in items if i.get('done')]
    whole = all(i.get('back') for i in done)
    state = 'undone' if whole else 'partly undone'
    with files_service.opened(kernel) as db:
        ensure(db)
        db.execute('UPDATE files_batches SET state=?, items=?, undone=? WHERE id=?', (state, json.dumps(items), _now_ms(), row['id']))
    froms = [i['from'] for i in back];count = counted(froms, {i['from']: i.get('kind') for i in back}) if back else ''
    said = {'move': '%s %s back in %s' % (count, 'is' if len(back) == 1 else 'are', _from_words(froms) if froms else ''),
            'copy': '%s %s in DELETE' % ('the copy' if len(back) == 1 else '%d copies' % len(back), 'is' if len(back) == 1 else 'are'),
            'delete': '%s %s back where %s %s' % (count, 'is' if len(back) == 1 else 'are', 'it' if len(back) == 1 else 'they', 'was' if len(back) == 1 else 'were')}[act]
    if not back:words = 'Nothing was put back.' if not already else 'Nothing more to put back.'
    elif not not_back:words = 'Undone: %s.' % said
    else:words = 'Undone for %d of %d: %s.' % (len(back), len(back) + len(not_back) + len(already), said)
    if already:
        names = ', '.join(Path(i['from']).name for i in already[:LEFT_SHOWN]) + (' and %d more' % (len(already) - LEFT_SHOWN) if len(already) > LEFT_SHOWN else '')
        words += ' %s %d %s restored from DELETE before: %s.' % ('The other' if not not_back else 'And', len(already), 'was' if len(already) == 1 else 'were', names)
    if not_back:
        shown = '; '.join('%s (%s)' % (n['name'], n['why']) for n in not_back[:LEFT_SHOWN])
        words += ' %d could not be put back, and %s left as %s: %s%s.' % (len(not_back), 'is' if len(not_back) == 1 else 'are',
                                                                          'it is' if len(not_back) == 1 else 'they are', shown,
                                                                          ' and %d more' % (len(not_back) - LEFT_SHOWN) if len(not_back) > LEFT_SHOWN else '')
    words += folder_words
    return {'batch': row['id'], 'act': act, 'state': state, 'back': len(back), 'already': len(already), 'not_back': not_back, 'paths': froms, 'words': words}


def listing(kernel, args, principal):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        rows = [dict(r) for r in db.execute('SELECT id, act, folder, at, state, items, left, made, undone FROM files_batches WHERE owner=? ORDER BY at DESC LIMIT ?',
                                            (principal.identity, int(args.get('limit') or 10)))]
        out = []
        for r in rows:
            items = json.loads(r.pop('items') or '[]');left = json.loads(r.pop('left') or '[]')
            froms = [i['from'] for i in items]
            entry = dict(r, count=len(items), back=sum(1 for i in items if i.get('back')), left=len(left), folder=hr.tilde(r['folder']) if r['folder'] else '',
                         count_words=counted(froms, {i['from']: i.get('kind') for i in items}) if items else '', from_words=_from_words(froms) if froms else '')
            ids = [i['trash_id'] for i in items if i.get('trash_id')][:MOST]
            if r['act'] == 'delete' and ids:      # how many of its deletions are still in DELETE
                entry['in_delete'] = db.execute('SELECT COUNT(*) FROM files_trash WHERE owner=? AND restored IS NULL AND id IN (%s)' % ','.join('?' * len(ids)),
                                                (principal.identity, *ids)).fetchone()[0]
            out.append(entry)
    return {'batches': out}


def dispatch(kernel, op, args, principal):
    if op == 'files.batch_plan':return plan(kernel, args, principal)
    if op == 'files.batch':return run(kernel, args, principal)
    if op == 'files.batch_undo':return undo(kernel, args, principal)
    if op == 'files.batches':return listing(kernel, args, principal)
    raise ValueError('FILES_UNKNOWN_OPERATION')
