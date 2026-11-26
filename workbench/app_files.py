"""Programs by window and file (Graphite 1.0 A1): a file of Files opened in its own program from the board, its window
found and named on the board's tile, each save recorded as a new revision with what rests on it marked to recheck, and
the window's close said.

The owner's paper, section 7: "An Open full application action is available when the compact editor does not support a
necessary feature, but the file identity and revision must remain recognizable when returning from the native program."
And section 8: "Firefox, Blender, LibreOffice, and other programs operate as ordinary windows managed by the underlying
window manager." Graphite does not work inside these programs (her hand in other programs is 1.0 K9's); it opens a file in
one, sees its window, notices its saves and its close. The window's side is workbench/app_files_qt.py. What lives here has
no Qt:

    the programs      PROGRAMS: Firefox, GIMP, KiCad, Blender and Godot, whichever is installed, each with the files it
                      opens and the words its windows give (WM_CLASS). Only what helps and is cheap: a KiCad project's
                      schematic and board are watched together (.kicad_pro, .kicad_sch, .kicad_pcb of one name; a BOM or a
                      netlist read is the KiCad checks room's, never parsed here); a Godot project is its project.godot and
                      its scenes (opened through the existing bridge, programs.godot.open: the editor on the project
                      folder); a .blend through the existing bridge too (programs.blender.open, scripts in the file not run);
                      GIMP's .xcf is an image with layers and is not read; Firefox is given a page from Files and Graphite
                      fetches nothing (the network is 1.0 K8's). Any other installed program opens a file the same plain way.
    opening           appfile.open: the program is the one the owner chose (Open with), else the file's default program (S2's
                      mimeapps.list), else the family's own bridge or entry; it starts through S2's launch (1.0 S1's
                      session_launch: a session of its own, so a Graphite restart leaves it open) or the family's bridge.
                      A session row is kept in the Kernel: the file's identity (L1's), the program, its processes, the
                      files watched with their digests at the start, the window list's place at the start (S3).
    looking           appfile.look: called by the window only when something changed (a watched file, the window list, a
                      process). The Kernel looks itself: the window list (S3's Watcher: the program's window by its
                      process, else by its program and the file's name in its title, else by its program's window that
                      appeared or changed since the start), each watched file's bytes (a new digest is recorded through
                      L4's revisions.record: verified on disk, or nothing is recorded), and whether the window closed (or,
                      with no window list on this computer, whether its processes still run). Nothing is written when
                      nothing changed.
    the board         mark_board(desk): the FILE tile of a file open in a program says so in its state word (OPEN IN GIMP,
                      OPENING IN GIMP while its window is looked for, GIMP CLOSED for a while after) and its revision on its
                      first line; L4's depths.mark_board marks what rests on an earlier revision admitted as a source; here,
                      what the owner linked to the file by their word (board.keep) before its newest revision is marked to
                      recheck too, its wire marked. Nothing is changed in any record: marking is the board's reading.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 A1):
    appfile.open  {path | id, app?, chosen?}   execute  open a file of Files in a program (chosen: the owner chose this app
                                                        in Open with, so no bridge is put in its place)
    appfile.look  {session?}                   execute  look at the open sessions now: window, saves, close
    appfile.list  {open?, path?, id?, limit?}  read     the sessions, newest first, with their tile words
appfile.list is an observer (activity.OBSERVER_OPERATIONS): the board reads it each time it is drawn.

1.0 L6b: a file of your home opens the same way (its path kept whole, ~/… as you read it); her opening a file to work in it
(K9's hand goes through this door) passes home_reach.her_change first, so nothing of hers lands outside your home.

Her rules hold: a program is started only on a press (the owner's, or hers under a grant through the Kernel), argv only and
never a shell; a revision is recorded only when its bytes are on disk; nothing is sent anywhere; no floating point here (times
are whole nanoseconds, digests are text).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from . import mind_words

SCHEMA = 'graphite.appfiles/1'
FIND_LONGEST_NS = 90 * 1_000_000_000         # a program whose window is not seen in this long, its processes ended: it is said ended
WATCH_LONGEST_NS = 24 * 3600 * 1_000_000_000  # a session is not looked at after a day (the window side says so)
CLOSED_SHOWN_NS = 2 * 3600 * 1_000_000_000   # a FILE tile says "GIMP CLOSED" this long after its window closed
HANDOFF_NS = 4 * 1_000_000_000               # a program that ended this soon handed the file to one already running
MOST_WATCHED = 40                            # files watched with one (a Godot project's scenes)
BIGGEST = 512 * 1024 * 1024                  # the most read whole to see a new revision (as depths.BIGGEST)
STATES = ('starting', 'open', 'closed')


@dataclass(frozen=True)
class Program:
    key: str
    name: str            # the short name said on a tile
    suffixes: tuple      # the files it opens (lower case), or whole names (project.godot)
    classes: tuple       # words in its windows' WM_CLASS
    entries: tuple       # words in its desktop entries' ids
    bridge: str = ''     # the existing Graphite bridge that opens it (program_build): '' none
    note: str = ''       # what Graphite knows of its files, in words


PROGRAMS = (
    Program('firefox', 'Firefox', ('.html', '.htm', '.xhtml', '.mhtml'), ('firefox', 'navigator', 'firefox-esr'),
            ('firefox', 'org.mozilla.firefox'), '',
            'a page from Files, given to Firefox as a file; Graphite fetches nothing for it'),
    Program('gimp', 'GIMP', ('.xcf', '.ora'), ('gimp',), ('gimp', 'org.gimp.gimp'), '',
            'an image with layers; Graphite does not read inside it, it records its revisions'),
    Program('kicad', 'KiCad', ('.kicad_pro', '.kicad_sch', '.kicad_pcb'), ('kicad', 'pcbnew', 'eeschema'),
            ('kicad', 'org.kicad'), '',
            'a KiCad project: its schematic and board are watched together; a BOM or a netlist is read by the KiCad checks room'),
    Program('blender', 'Blender', ('.blend',), ('blender',), ('blender', 'org.blender'), 'programs.blender.open',
            'a Blender scene; Graphite does not read inside it, and opens it with its scripts not run'),
    Program('godot', 'Godot', ('project.godot', '.tscn', '.scn'), ('godot',), ('godot', 'org.godotengine'), 'programs.godot.open',
            'a Godot project: its project.godot and its scenes are watched; the editor opens on the project folder'),
)
BY_KEY = {p.key: p for p in PROGRAMS}

# Her words in her column (fixed templates; every number through a slot that names its record).
WORDS = {
    'opening': '{name} is opening in {program}. When {program} saves it, the new revision is recorded here and what rests on it is marked to recheck.',
    'note': 'This is {note}.',
    'window': '{name} is open in {program}, in its window “{title}”.',
    'running': '{name} is open in {program}. Its window cannot be seen on this computer, so its process is watched.',
    'saved': '{program} saved {name}: revision {n} is recorded, its bytes verified on disk.',
    'marked': 'What rests on it is marked to recheck on the board.',
    'closed': '{program} closed {name}; revision {n} is the newest here.',
    'closed_same': '{program} closed {name} without saving a change.',
    'ended': '{program} ended before its window was seen; {name} is as it was.',
    'refused': '{name} was not opened: {why}',
}
NUMBERS = {'saved': {'n': "the file's revisions (revisions.list)"}, 'closed': {'n': "the file's revisions (revisions.list)"}}
mind_words.register('app_files', WORDS, kind='sentence', numbers=NUMBERS)


def say(key, **slots):
    return WORDS[key].format(**slots)


# ---- the programs ----------------------------------------------------------------------------------------------------------
def family(path):
    """The Program a file belongs to (by its whole name, then its suffix), or None."""
    name = Path(str(path)).name.lower();suffix = Path(name).suffix
    for program in PROGRAMS:
        if name in program.suffixes or (suffix and suffix in program.suffixes):return program
    return None


def family_of_app(app):
    """The Program an installed app is (its id, its program or its window class names it), or None."""
    if app is None:return None
    words = ' '.join((str(getattr(app, 'id', '')), Path(str(app.exec_program() if hasattr(app, 'exec_program') else '')).name,
                      str(getattr(app, 'wm_class', '')), str(getattr(app, 'name', '')))).casefold()
    for program in PROGRAMS:
        if any(w in words for w in program.entries + program.classes):return program
    return None


def short_name(app_name, program):
    return program.name if program is not None else (str(app_name or '') or 'its program')


def watched_with(path, program):
    """The files watched with this one (all in its folder or, for Godot, its project): the file first."""
    path = Path(path);out = [path]
    if program is None:return out
    if program.key == 'kicad':
        for suffix in ('.kicad_pro', '.kicad_sch', '.kicad_pcb'):
            other = path.with_suffix(suffix)
            if other != path and other.is_file():out.append(other)
    elif program.key == 'godot':
        project = path if path.name == 'project.godot' else next((p / 'project.godot' for p in path.parents if (p / 'project.godot').is_file()), None)
        if project is not None:
            if project != path:out.append(project)
            try:
                from .program_build import _godot_scenes
                scenes, _ = _godot_scenes(project.parent)
            except (OSError, ValueError):
                scenes = []
            for scene in scenes:
                other = project.parent / scene.removeprefix('res://')
                if other not in out and other.is_file():out.append(other)
                if len(out) >= MOST_WATCHED:break
    return out[:MOST_WATCHED]


# ---- the store --------------------------------------------------------------------------------------------------------------
COLUMNS = ('id', 'object', 'path', 'program', 'app', 'route', 'family', 'pids', 'state', 'window', 'title', 'found_by', 'started_ns',
           'seen_ns', 'ended_ns', 'files', 'revisions', 'seq', 'match', 'said', 'principal')
JSONS = ('pids', 'files', 'revisions', 'match')


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS app_files(id TEXT PRIMARY KEY, object TEXT NOT NULL, path TEXT NOT NULL, program TEXT NOT NULL, '
               'app TEXT NOT NULL, route TEXT NOT NULL, family TEXT NOT NULL, pids TEXT NOT NULL, state TEXT NOT NULL, window TEXT NOT NULL, '
               'title TEXT NOT NULL, found_by TEXT NOT NULL, started_ns INTEGER NOT NULL, seen_ns INTEGER NOT NULL, ended_ns INTEGER NOT NULL, '
               'files TEXT NOT NULL, revisions TEXT NOT NULL, seq INTEGER NOT NULL, match TEXT NOT NULL, said TEXT NOT NULL, principal TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS app_files_object ON app_files(object, started_ns)')


def _row(r):
    out = dict(zip(COLUMNS, r))
    for key in JSONS:
        try:out[key] = json.loads(out[key] or ('{}' if key == 'files' else '[]'))
        except ValueError:out[key] = {} if key == 'files' else []
    return out


def _save(db, row):
    values = [json.dumps(row[k], sort_keys=True) if k in JSONS else row[k] for k in COLUMNS]
    db.execute('INSERT OR REPLACE INTO app_files VALUES(%s)' % ','.join('?' * len(COLUMNS)), values)


def _read(kernel, where='', params=()):
    with kernel.db() as db:
        ensure(db)
        rows = db.execute('SELECT %s FROM app_files %s ORDER BY started_ns DESC' % (','.join(COLUMNS), where), params).fetchall()
    return [_row(r) for r in rows]


# ---- choosing the program ----------------------------------------------------------------------------------------------------
def _bridge_ready(program):
    """The family's existing bridge, when its program is installed here (program_build._tool)."""
    if program is None or not program.bridge:return False
    try:
        from .program_build import _tool
        return bool(_tool(program.key).get('available'))
    except Exception:  # noqa: BLE001 - no bridge: the plain route
        return False


def choose(path, app_id='', chosen=False):
    """(route, app, program family, name said, reason): route 'bridge' (the family's own), 'app' (an installed app), or ''
    with the reason none can open it."""
    from . import apps_catalog
    program = family(path)
    catalog = apps_catalog.scan()
    if app_id:
        app = apps_catalog.find_app(app_id, catalog)
        if app is None:return '', None, program, '', '%s is not installed here' % str(app_id)[:120]
        if not chosen and _bridge_ready(program) and family_of_app(app) is not program:
            return 'bridge', None, program, program.name, ''
        return 'app', app, family_of_app(app) or program, short_name(app.name, family_of_app(app)), ''
    if _bridge_ready(program):return 'bridge', None, program, program.name, ''
    mime = apps_catalog.mime_of(path)
    default, _ = apps_catalog.default_for(mime, catalog)
    app = catalog.get(default) if default else None
    if app is None and program is not None:      # no default: an installed app of the family, by its entry or its program
        app = next((a for a in catalog.every() if a.available and family_of_app(a) is program), None)
    if app is None:
        return '', None, program, '', 'no program here says it opens %s: Open with chooses one' % apps_catalog.type_words(mime, Path(path).name)
    return 'app', app, family_of_app(app) or program, short_name(app.name, family_of_app(app)), ''


def _match_words(app, program):
    """The words a window of this program gives (its WM_CLASS), lower case."""
    words = set(program.classes) if program is not None else set()
    if app is not None:
        if getattr(app, 'wm_class', ''):words.add(app.wm_class.casefold())
        exe = Path(app.exec_program()).name.casefold() if hasattr(app, 'exec_program') else ''
        if exe and exe not in ('python3', 'python', 'sh', 'bash', 'env', 'flatpak', 'snap'):words.add(exe)
    return sorted(w for w in words if w)


# ---- the operations ------------------------------------------------------------------------------------------------------------
def _place(kernel, args):
    from . import depths
    try:return depths._place(kernel, args)
    except ValueError as exc:
        if str(exc).startswith('REVISIONS_OUTSIDE'):  # 1.0 L6b: Files or your home
            raise ValueError('APPFILE_OUTSIDE: a file in Files or in your home is opened here, so its saves can be recorded; this one is outside them') from None
        raise


def _file_state(path):
    st = os.stat(path)
    return [int(st.st_size), int(st.st_mtime_ns), int(st.st_ino)]


def _window_seq():
    """The window list's place now (S3), or -1 when this computer has none."""
    try:
        from . import windows_x11
        watcher = windows_x11.shared()
        if not watcher.start():return -1
        return int(watcher.observe()['seq'])
    except Exception:  # noqa: BLE001 - no window list: processes are watched instead
        return -1


def open_file(kernel, args, principal):
    """appfile.open: start the program on the file and keep the session."""
    from . import depths, files_service
    ident, rel, target = _place(kernel, args)
    from . import home_reach  # 1.0 L6b: her work (her hand opening a file to work in it) passes her_change first
    if home_reach.in_her_work(principal):
        never = home_reach.her_change(kernel, target)
        if never:raise ValueError('APPFILE_OUTSIDE_HOME: ' + never)
    if target.stat().st_size > BIGGEST:raise ValueError('APPFILE_TOO_LARGE: %s is larger than Graphite reads whole to see its revisions' % target.name)
    route, app, program, name, reason = choose(target, str(args.get('app') or ''), bool(args.get('chosen')))
    if not route:raise ValueError('APPFILE_NO_PROGRAM: ' + reason)
    base = files_service.root(kernel).resolve()
    watched = {}
    for path in watched_with(target, program):
        try:
            rel_path = files_service.place_of(kernel, path.resolve())  # 1.0 L6b: a file of your home is kept by its whole path
            if rel_path.startswith('/') and not str(rel).startswith('/') or rel_path.startswith('..'):continue
            watched[rel_path] = [depths.sha256_of(path)[0]] + _file_state(path)
        except (OSError, ValueError):
            continue
    seq = _window_seq()
    if route == 'bridge':
        bridge_args = {'path': rel, 'expected_sha256': watched[rel][0]}
        if program.key == 'godot':
            project = next((p for p in watched if Path(p).name == 'project.godot'), None)
            if project is None:raise ValueError('APPFILE_NO_PROJECT: %s is not in a Godot project (no project.godot beside it)' % target.name)
            bridge_args = {'path': project, 'expected_sha256': watched[project][0]}
        from . import program_build
        answer = program_build.dispatch(kernel, program.bridge, bridge_args, principal)
        pids = [int(answer['pid'])] if answer.get('pid') else []
        started = [{'pid': p, 'ok': True, 'reason': ''} for p in pids]
        app_id, how = program.bridge, 'the existing %s bridge (%s)' % (program.name, program.bridge)
        match = _match_words(None, program)
    else:
        from . import apps_catalog
        result = apps_catalog.launch_app(app, [str(target)])
        if not result.get('ok'):raise ValueError('APPFILE_NOT_STARTED: ' + str(result.get('reason') or 'it did not start'))
        started = result.get('started') or []
        pids = [int(s['pid']) for s in started if s.get('ok') and s.get('pid')]
        app_id, how = app.id, 'its desktop entry %s, in a session of its own' % app.id
        match = _match_words(app, program)
    now = time.time_ns()
    row = {'id': 'appfile:' + uuid.uuid4().hex, 'object': ident, 'path': rel, 'program': name, 'app': app_id, 'route': route,
           'family': program.key if program is not None else '', 'pids': pids, 'state': 'starting', 'window': '', 'title': '', 'found_by': '',
           'started_ns': now, 'seen_ns': now, 'ended_ns': 0, 'files': watched, 'revisions': [], 'seq': seq, 'match': match,
           'said': say('opening', name=target.name, program=name), 'principal': str(getattr(principal, 'identity', ''))[:80]}
    with kernel.db() as db:
        ensure(db)
        for old in db.execute('SELECT %s FROM app_files WHERE object=? AND state!=?' % ','.join(COLUMNS), (ident, 'closed')).fetchall():
            old = _row(old)          # the same file opened again: the earlier session is set aside (its window, if any, stays the owner's)
            old.update(state='closed', ended_ns=now, said='opened again in %s' % name)
            _save(db, old)
        _save(db, row)
    words = row['said'] + ((' ' + say('note', note=program.note)) if program is not None and program.note else '')
    return {'schema': SCHEMA, 'ok': True, 'session': row['id'], 'object': ident, 'path': rel, 'name': name, 'program': name, 'id': app_id,
            'route': route, 'how': how, 'started': started, 'pids': pids, 'watched': sorted(watched), 'window_list': seq >= 0,
            'reason': '%s started in a session of its own.' % name if route == 'app' else '%s started through %s.' % (name, program.bridge),
            'words': words, 'verified': 'started; its window is looked for', 'done': True}


def listing(kernel, args):
    """appfile.list: the sessions, newest first (open only, or one file's), each with its tile words."""
    where, params = [], []
    if args.get('open'):where.append('state!=?');params.append('closed')
    if args.get('id') or args.get('path'):
        ident, _, _ = _place(kernel, args);where.append('object=?');params.append(ident)
    rows = _read(kernel, ('WHERE ' + ' AND '.join(where)) if where else '', tuple(params))[:int(args.get('limit') or 100)]
    now = time.time_ns()
    for row in rows:
        row['tile'] = tile_words(row, now)
    return {'schema': SCHEMA, 'sessions': rows}


def match_window(row, look):
    """(the window row, how it was found) of a session in a reading of the window list (windows_x11.observe), or (None, '')."""
    wins = [w for w in look.get('windows') or () if not w.get('graphite')]
    by_id = {w['id']: w for w in wins}
    pids = set(row.get('pids') or ())
    if row.get('window') and row['window'] in by_id:
        same = by_id[row['window']]      # an X window id is used again by a later program: the one found by its process must still be it
        if row.get('found_by') != 'its process' or same.get('pid') in pids:return same, row.get('found_by') or 'its window'
    mine = [w for w in wins if w.get('pid') in pids]
    if mine:return (next((w for w in mine if not w.get('dialog')), mine[0])), 'its process'
    words = [str(w).casefold() for w in row.get('match') or ()]

    def of_program(w):
        klass = ('%s %s' % (w.get('klass') or '', w.get('instance') or '')).casefold()
        return bool(words) and any(word in klass for word in words)
    stem = Path(row.get('path') or '').stem.casefold();name = Path(row.get('path') or '').name.casefold()
    project = Path(row.get('path') or '').parent.name.casefold() if Path(row.get('path') or '').name == 'project.godot' else ''
    for w in wins:
        title = str(w.get('title') or '').casefold()
        if of_program(w) and ((stem and stem in title) or (name and name in title) or (project and project in title)):
            return w, 'its program and the file\'s name in its title'
    for event in reversed(look.get('events') or ()):
        w = by_id.get(event.get('window'))
        if w is not None and of_program(w) and event.get('event') in ('a new window appeared', 'title changed', 'became active'):
            return w, 'its program\'s window that %s after it was started' % ('appeared' if event['event'] == 'a new window appeared' else 'changed')
    return None, ''


def _alive(pids):
    from .session_launch import start_time
    return [p for p in pids or () if start_time(p) is not None]


def _look_window(row):
    """(the window list's reading or None when there is none here, the window found, how)."""
    try:
        from . import windows_x11
        watcher = windows_x11.shared()
        if not watcher.start():return None, None, ''
        since = row.get('seq')
        look = watcher.observe(since if isinstance(since, int) and since >= 0 else None)
        if not look.get('available'):return None, None, ''
    except Exception:  # noqa: BLE001 - no window list: the processes decide
        return None, None, ''
    window, how = match_window(row, look)
    return look, window, how


def _look_files(kernel, row, principal):
    """Each watched file's bytes now: a new digest is recorded (L4's revisions.record, verified on disk). The events."""
    from . import depths, files_service
    events = []
    for rel, seen in sorted(row['files'].items()):
        try:
            path = files_service.resolve(kernel, rel)
            state = _file_state(path)
        except (OSError, ValueError):
            continue          # not there this moment (a program writing a new file over the old one): looked at again
        if state == seen[1:]:continue
        if state[0] > BIGGEST:continue
        try:digest, _ = depths.sha256_of(path)
        except OSError:continue
        if digest == seen[0]:
            row['files'][rel] = [digest] + state;continue
        try:
            got = depths.record(kernel, {'path': rel, 'expected_sha256': digest, 'previous_sha256': seen[0], 'how': 'full program',
                                         'program': row['program'][:120]}, principal)
        except ValueError:
            continue          # it changed again while it was read: the next look records the bytes then on disk
        row['files'][rel] = [digest] + state
        row['revisions'].append({'path': rel, 'n': got['revision'], 'digest': digest, 'at_ns': time.time_ns()})
        kept = _kept_of(kernel, got['object'])
        marked = bool(got.get('earlier_admitted')) or bool(kept)
        words = say('saved', program=row['program'], name=Path(rel).name, n=got['revision']) + ((' ' + say('marked')) if marked else '')
        events.append({'event': 'saved', 'session': row['id'], 'path': rel, 'object': got['object'], 'revision': got['revision'],
                       'recorded': got.get('recorded', False), 'earlier_admitted': len(got.get('earlier_admitted') or ()), 'kept_links': len(kept),
                       'marked': marked, 'verified': got.get('verified', ''), 'words': words})
    return events


def _kept_of(kernel, ident):
    try:
        from .board_model import kept_links
        return [k for k in kept_links(kernel) if ident in (k.get('a'), k.get('b'))]
    except Exception:  # noqa: BLE001 - no links kept by the owner's word
        return []


def look(kernel, args, principal):
    """appfile.look: every open session (or the one named) looked at now. Writes only what changed."""
    where = 'WHERE id=?' if args.get('session') else 'WHERE state!=?'
    rows = _read(kernel, where, (args['session'],) if args.get('session') else ('closed',))
    events = [];changed = []
    now = time.time_ns()
    for row in rows:
        if row['state'] == 'closed':continue
        before = json.dumps(row, sort_keys=True)
        name = Path(row['path']).name
        found = _look_files(kernel, row, principal)       # a save just before the close is recorded first
        events += found
        reading, window, how = _look_window(row)
        alive = _alive(row['pids'])
        if reading is not None:
            if window is not None:
                if row['state'] != 'open' or row['window'] != window['id']:
                    row.update(state='open', window=window['id'], found_by=how)
                    events.append({'event': 'window', 'session': row['id'], 'path': row['path'], 'window': window['id'], 'title': window['title'],
                                   'how': how, 'words': say('window', name=name, program=row['program'], title=str(window['title'])[:120])})
                if window['title'] != row['title']:row['title'] = str(window['title'])[:300]
                row['seen_ns'] = now
            elif row['state'] == 'open' and row['window']:
                row.update(state='closed', ended_ns=now)
            elif row['state'] == 'starting' and not alive and now - row['started_ns'] > FIND_LONGEST_NS:
                row.update(state='closed', ended_ns=now, found_by='never seen')
        else:      # no window list here: its processes are watched
            if alive and row['state'] == 'starting':
                row.update(state='open', found_by='its process (no window list here)', seen_ns=now)
                events.append({'event': 'window', 'session': row['id'], 'path': row['path'], 'window': '', 'title': '', 'how': row['found_by'],
                               'words': say('running', name=name, program=row['program'])})
            elif not alive and (row['state'] == 'open' or now - row['started_ns'] > HANDOFF_NS):
                row.update(state='closed', ended_ns=now, found_by=row['found_by'] or 'its process ended')
        if now - row['started_ns'] > WATCH_LONGEST_NS and row['state'] != 'closed':
            row.update(state='closed', ended_ns=now, found_by=row['found_by'] or 'no longer watched')
        if row['state'] == 'closed':
            latest = row['revisions'][-1]['n'] if row['revisions'] else None
            if row['found_by'] == 'never seen':words = say('ended', program=row['program'], name=name)
            elif latest is None:words = say('closed_same', program=row['program'], name=name)
            else:words = say('closed', program=row['program'], name=name, n=latest)
            row['said'] = words
            events.append({'event': 'closed', 'session': row['id'], 'path': row['path'], 'window': row['window'], 'saved': latest, 'words': words})
        elif found or any(e['session'] == row['id'] for e in events):
            row['said'] = events[-1]['words']
        if json.dumps(row, sort_keys=True) != before:
            changed.append(row)
    if changed:
        with kernel.db() as db:
            ensure(db)
            for row in changed:_save(db, row)
    sessions = _read(kernel, 'WHERE state!=?', ('closed',))
    for row in sessions:row['tile'] = tile_words(row, now)
    return {'schema': SCHEMA, 'events': events, 'sessions': sessions, 'changed': [r['id'] for r in changed],
            'words': ' '.join(e['words'] for e in events) or 'Nothing changed in the programs that have your files open.'}


def dispatch(kernel, op, args, principal):
    if op == 'appfile.open':return open_file(kernel, args, principal)
    if op == 'appfile.look':return look(kernel, args, principal)
    if op == 'appfile.list':return listing(kernel, args)
    raise ValueError('Unknown appfile operation')


TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4000}
FIELDS = {
    'appfile.open': ({'path': TEXT, 'id': {'type': 'string', 'pattern': '^fileid:[0-9a-f]{32}$', 'maxLength': 39},
                      'app': {'type': 'string', 'maxLength': 300}, 'chosen': {'type': 'boolean'}}, []),
    'appfile.look': ({'session': {'type': 'string', 'pattern': '^appfile:[0-9a-f]{32}$', 'maxLength': 40}}, []),
    'appfile.list': ({'open': {'type': 'boolean'}, 'path': TEXT, 'id': {'type': 'string', 'pattern': '^fileid:[0-9a-f]{32}$', 'maxLength': 39},
                      'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}}, []),
}
SCOPES = {'appfile.open': 'execute', 'appfile.look': 'execute', 'appfile.list': 'read'}
OBSERVERS = ('appfile.list',)


# ---- the board ---------------------------------------------------------------------------------------------------------------
def tile_words(row, now=None):
    """(state word, first line) a FILE tile says for this session, or None when it says nothing any more."""
    now = time.time_ns() if now is None else now
    program = row.get('program') or 'its program'
    latest = (row.get('revisions') or [{}])[-1] if row.get('revisions') else None
    saved = ('revision %d, saved in %s' % (latest['n'], program)) if latest and latest.get('path') == row.get('path') else ''
    if row.get('state') == 'starting':return ('opening in %s' % program, saved)
    if row.get('state') == 'open':return ('open in %s' % program, saved or 'since %s, not saved yet' % _clock(row.get('started_ns')))
    if row.get('state') == 'closed' and row.get('found_by') != 'never seen' and now - int(row.get('ended_ns') or 0) <= CLOSED_SHOWN_NS \
            and not str(row.get('said') or '').startswith('opened again'):
        return ('%s closed' % program, saved or '%s closed it at %s, nothing saved' % (program, _clock(row.get('ended_ns'))))
    return None


def _clock(ns):
    try:return time.strftime('%H:%M', time.localtime(int(ns) // 1_000_000_000))
    except (TypeError, ValueError, OverflowError):return ''


def mark_board(desk):
    """board_model.Desk: the FILE tile of a file open in a program (or just closed) says so; what the owner linked to it by
    their word before its newest revision is marked to recheck. Reads only (appfile.list, revisions.list, board.links)."""
    reader = getattr(desk, 'reader', None)
    if reader is None or not hasattr(reader, 'call'):return 0
    from .board_model import Edge, file_object
    from .field_model import STATE_RECHECK
    from .depths import MARKED, SETTLED
    entries = {e.get('id'): e for e in ((desk.files or {}).get('entries') or ())}
    root = (desk.files or {}).get('root')

    def bring(ident):
        """A plain file of Files on the desk (as add_file does), or None."""
        if ident not in desk.objects and ident in entries:desk.objects[ident] = file_object(entries[ident], root)
        return desk.objects.get(ident)
    marked = 0
    # 1. the FILE tiles of files open in a program, or just closed
    rows = ((reader.call('appfile.list', {'limit': 200}) or {}).get('sessions') or [])
    newest = {}
    for row in rows:      # newest first: the first row of each file is its session now
        newest.setdefault(row.get('object'), row)
    now = time.time_ns()
    for ident, row in newest.items():
        words = row.get('tile') or tile_words(row, now)
        if words is None:continue
        obj = bring(ident)
        if obj is None:continue
        state, line = words
        lines = tuple(obj.lines)
        if line and not (lines and str(lines[0]).startswith('revision')):lines = (line,) + lines[1:3]
        desk.objects[ident] = replace(obj, state=state, lines=lines[:3])
        marked += 1
    # 2. what the owner linked to a file by their word (board.keep) before its newest revision: to recheck, its wire marked
    links = [k for k in ((reader.call('board.links', {}) or {}).get('links') or ()) if k.get('state') == 'IN'
             and (str(k.get('a')).startswith('fileid:') or str(k.get('b')).startswith('fileid:'))]
    if links:
        latest = {}
        for rev in ((reader.call('revisions.list', {'limit': 500}) or {}).get('revisions') or ()):
            if rev.get('how') != 'seen' and int(rev.get('n') or 0) >= 2:
                was = latest.get(rev.get('object'))
                if was is None or int(rev['n']) > int(was['n']):latest[rev['object']] = rev
        for link in links:
            a, b = link.get('a'), link.get('b')
            if bring(a) is None or bring(b) is None:continue
            if not any(e.relation == 'kept' and {e.source, e.target} == {a, b} for e in desk.edges):
                desk.edges.append(Edge(a, b, 'kept', 'by your word', said=link.get('said') or '', kept=link.get('id') or ''))
            for ident, other in ((a, b), (b, a)):
                rev = latest.get(ident)
                if rev is None or int(link.get('at') or 0) * 1_000_000_000 >= int(rev.get('at_ns') or 0):continue   # kept after it: about the new one
                for edge in desk.edges:
                    if edge.relation == 'kept' and {edge.source, edge.target} == {a, b}:edge.stale = True     # its wire says "recheck"
                rests = desk.objects.get(other)
                if rests is not None and rests.kind in MARKED and rests.state in SETTLED:
                    desk.objects[other] = replace(rests, state=STATE_RECHECK);marked += 1
    if marked:desk._df = None
    return marked
