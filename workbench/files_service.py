"""Files: an ordinary folder on this computer, browsed and organised inside Ledger (Current Plans rev 1.3; the Files mockup).

The folder is ``Files`` in the workspace (``~/Concern/Office/Files`` for the Office). Any Debian program can open it too.

  Files/            your files and folders
  Files/Slate/      Slate's own area: he writes here directly
  Files/Egress/     copies made for manufacturing or sharing: the folder files leave from (Exports before AGENT-01)
  Files/.trash/     what was deleted, with where it came from: nothing is removed for good from Ledger
  Files/.versions/  the version before every change Ledger makes to a file

Rules the code enforces:
  - Every path stays inside Files. Names cannot climb out (no '..', no separators), and links are never followed out.
  - Deleting moves to Trash with its original place recorded; restore puts it back without overwriting anything.
  - A change Ledger makes to a file (Slate writing, a proposal applied, a revert) first keeps the version before it.
  - Slate (read and execute) may change only his own area. A change anywhere else needs the approve scope; Slate's way to
    ask is files.propose, which waits in his Agenda for your decision.
  - Egress holds copies, with SHA256SUMS; the originals stay as they are.
  - Machine files (caches, object files, lock files, hidden dot-files) are hidden unless you ask for all files.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
import zipfile
from pathlib import Path, PurePosixPath

REL = {'type': 'string', 'maxLength': 1000}
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 255}
ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
SLATE, EXPORTS, TRASH, VERSIONS = 'Slate', 'Egress', '.trash', '.versions'
OLD_EXPORTS = 'Exports'  # the folder's name before AGENT-01 (owner, D28: Egress); moved once by root()
MAX_TEXT = 4 * 1024 * 1024
MACHINE_SUFFIXES = {'.o', '.obj', '.pyc', '.pyo', '.so', '.dll', '.dylib', '.a', '.lib', '.class', '.lock', '.tmp', '.swp', '.swo',
                    '.pdb', '.ilk', '.d', '.dep', '.cache', '.sqlite3-wal', '.sqlite3-shm', '.db-wal', '.db-shm', '.part', '.crdownload'}
MACHINE_NAMES = {'__pycache__', 'node_modules', '.git', '.svn', '.hg', '.venv', 'venv', '.idea', '.vscode', '.pytest_cache',
                 '.mypy_cache', 'CMakeFiles', 'Thumbs.db', '.DS_Store', 'desktop.ini', 'fp-info-cache'}
MANUFACTURING = ('gerber', 'excellon', 'csv')
FIELDS = {
    'files.list': ({'path': REL, 'all': {'type': 'boolean'}}, []),
    'files.get': ({'path': REL, 'expected_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64},
                   'sheet': {'type': 'string', 'maxLength': 512}}, ['path']),
    'files.versions': ({'path': REL}, ['path']),
    'files.trash_list': ({}, []),
    'files.mkdir': ({'path': REL, 'name': NAME}, ['name']),
    'files.rename': ({'path': REL, 'name': NAME}, ['path', 'name']),
    'files.copy': ({'path': REL, 'to': REL}, ['path', 'to']),
    'files.move': ({'path': REL, 'to': REL}, ['path', 'to']),
    'files.trash': ({'path': REL}, ['path']),
    'files.restore': ({'id': ID}, ['id']),
    'files.write': ({'path': REL, 'text': {'type': 'string', 'maxLength': MAX_TEXT}}, ['path', 'text']),
    'files.cells': ({'path': REL, 'changes': {'type': 'string', 'minLength': 1, 'maxLength': 200000}}, ['path', 'changes']),
    'files.propose': ({'path': REL, 'text': {'type': 'string', 'maxLength': MAX_TEXT}, 'why': {'type': 'string', 'minLength': 1, 'maxLength': 400}},
                      ['path', 'text', 'why']),
    'files.proposals': ({}, []),
    'files.decide': ({'id': ID, 'apply': {'type': 'boolean'}}, ['id', 'apply']),
    'files.revert': ({'path': REL, 'version': NAME}, ['path', 'version']),
    'files.export': ({'path': REL, 'purpose': {'type': 'string', 'enum': ['share', 'manufacturing']}, 'name': NAME}, ['path', 'purpose']),
    'files.compare': ({'path': REL, 'other': REL, 'version': NAME, 'proposal': ID}, ['path']),
    'files.find': ({'text': {'type': 'string', 'maxLength': 200}, 'kind': {'type': 'string', 'maxLength': 40}, 'days': {'type': 'number', 'minimum': 0, 'maximum': 36500},
                    'under': REL, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}, 'all': {'type': 'boolean'}}, []),
    'files.smart': ({'path': REL, 'name': NAME, 'find': {'type': 'object'}}, ['name', 'find']),
    'files.keep': ({'delivery': ID, 'name': {'type': 'string', 'minLength': 1, 'maxLength': 1000}}, ['delivery', 'name']),
    'files.story': ({'path': REL}, ['path']),
}
RECEIVED = 'Received'
SCOPES = {op: 'read' if op in ('files.list', 'files.get', 'files.versions', 'files.trash_list', 'files.proposals', 'files.compare', 'files.find', 'files.story') else
          'approve' if op in ('files.restore', 'files.decide', 'files.revert') else 'execute' for op in FIELDS}


def root(kernel, create=True):
    """The Files folder of this workspace. A program folder keeps its Files in the Concern, never inside the program."""
    from . import locations
    base = locations.concern_home() / 'Files' if locations.contains_program(kernel.root) else Path(kernel.root) / 'Files'
    if create:
        base.mkdir(parents=True, mode=0o700, exist_ok=True)
        locations.move_once(base / OLD_EXPORTS, base / EXPORTS)  # Exports → Egress, once; nothing overwritten
        for sub in (SLATE, EXPORTS, TRASH, VERSIONS):(base / sub).mkdir(parents=True, mode=0o700, exist_ok=True)
    return base


def resolve(kernel, rel, must_exist=True):
    """A path inside Files, or a refusal. Symbolic links are never followed out of the folder."""
    base = root(kernel).resolve()
    parts = [p for p in PurePosixPath((rel or '').replace('\\', '/')).parts if p not in ('', '/', '.')]
    if any(p == '..' or '\0' in p for p in parts):raise ValueError('FILES_PATH_OUTSIDE: stay inside Files')
    path = base.joinpath(*parts)
    real = path.resolve() if path.exists() or path.is_symlink() else path.parent.resolve() / path.name
    if real != base and base not in real.parents:raise ValueError('FILES_PATH_OUTSIDE: stay inside Files')
    if parts and parts[0] in (TRASH, VERSIONS):raise ValueError('FILES_RESERVED: use Trash and versions through their own words')
    if must_exist and not path.exists():raise ValueError('FILES_NOT_FOUND: ' + '/'.join(parts)[:200])
    return path


def rel_of(kernel, path):
    return Path(path).relative_to(root(kernel)).as_posix()


def clean_name(name):
    name = name.strip()
    if not name or name in ('.', '..') or '/' in name or '\\' in name or '\0' in name:raise ValueError('FILES_NAME_INVALID')
    return name


def machine(path):
    name = path.name
    return name.startswith('.') or name in MACHINE_NAMES or path.suffix.lower() in MACHINE_SUFFIXES or name.endswith('~')


def kind_of(path):
    if path.is_dir():return 'folder'
    try:
        from .universal_view import Source, identify
        return identify(Source.file(path))
    except Exception:
        return 'file'


KIND_WORDS = {'folder': 'Folder', 'pdf': 'PDF', 'image': 'Image', 'document': 'Document', 'zip': 'ZIP archive', 'tar': 'Archive',
              'gerber': 'Gerber', 'excellon': 'Excellon drill', 'csv': 'Table', 'json': 'JSON', 'markdown': 'Markdown', 'text': 'Text',
              'code': 'Code', 'step': 'STEP model', 'stl': 'STL model', 'kicad': 'KiCad', 'sqlite': 'Database', 'elf': 'Program',
              'binary': 'Binary', 'iso': 'Disc image', 'fat': 'Disk image', 'ext': 'Disk image', 'ntfs': 'Disk image', 'disk': 'Disk image',
              'smart': 'Smart folder', 'spreadsheet': 'Spreadsheet', 'obj': 'OBJ model', '3mf': '3MF model', 'dxf': 'DXF drawing', 'audio': 'Audio', 'video': 'Video'}


def entry(kernel, path):
    stat = path.stat();kind = 'smart' if path.suffix == SMART and path.is_file() else kind_of(path)
    rel = rel_of(kernel, path)
    value = {'name': path.name, 'path': rel, 'kind': kind, 'kind_words': KIND_WORDS.get(kind, kind.title()), 'modified': stat.st_mtime,
             'size': None if path.is_dir() else stat.st_size, 'machine': machine(path), 'address': '@files:' + rel}
    if path.is_dir():
        try:value['items'] = sum(1 for p in path.iterdir() if not machine(p))
        except OSError:value['items'] = None
    return value


@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row
        db.execute('''CREATE TABLE IF NOT EXISTS files_trash(id TEXT PRIMARY KEY, owner TEXT, original TEXT, stored TEXT, at REAL, restored REAL)''')
        db.execute('CREATE TABLE IF NOT EXISTS files_origin(path TEXT PRIMARY KEY, delivery TEXT, name TEXT, label TEXT, at REAL)')
        db.execute('''CREATE TABLE IF NOT EXISTS files_proposals(id TEXT PRIMARY KEY, owner TEXT, path TEXT, text TEXT, why TEXT, base TEXT,
                      state TEXT, at REAL, decided REAL)''')
        yield db


def may_change(kernel, path, principal):
    """Slate's own area is his; anything else needs the approve scope (yours)."""
    area = root(kernel) / SLATE
    inside = path == area or area in path.parents
    if not inside and 'approve' not in principal.scopes:
        from .working_copies import assigned_to_slate
        if assigned_to_slate(kernel, path):return  # a working copy you gave him is his to edit; the original is not

        raise ValueError('FILES_OUTSIDE_SLATE_AREA: propose the change instead; the owner decides')


def keep_version(kernel, path):
    """The version before a change, under .versions/<path>/<time>."""
    if not path.is_file():return None
    stamp = time.strftime('%Y%m%dT%H%M%S', time.gmtime()) + '-%06d' % (time.time_ns() // 1000 % 1_000_000)
    target = root(kernel) / VERSIONS / rel_of(kernel, path) / stamp
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True);shutil.copy2(path, target)
    return stamp


def versions(kernel, path):
    folder = root(kernel) / VERSIONS / rel_of(kernel, path)
    if not folder.is_dir():return []
    return [{'version': p.name, 'size': p.stat().st_size, 'kept': p.stat().st_mtime} for p in sorted(folder.iterdir(), reverse=True) if p.is_file()]


def free_name(folder, name):
    """A name not yet used in folder: 'notes.md', then 'notes 2.md'… Nothing is overwritten."""
    candidate = folder / name;stem, suffix = Path(name).stem, Path(name).suffix;n = 2
    while candidate.exists():candidate = folder / ('%s %d%s' % (stem, n, suffix));n += 1
    return candidate


def as_csv(rows):
    """Rows as a CSV a spreadsheet opens safely: every column that appears, and no cell that a spreadsheet would read as a formula."""
    import csv, io
    rows = [r if isinstance(r, dict) else {'value': r} for r in rows]
    columns = list(dict.fromkeys(k for r in rows for k in r))
    def safe(value):
        text = '' if value is None else (json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value))
        return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') and not isinstance(number(text), (int, float)) else text
    out = io.StringIO();writer = csv.writer(out, lineterminator='\n');writer.writerow(columns)
    for r in rows:writer.writerow([safe(r.get(c)) for c in columns])
    return out.getvalue()


def story(kernel, path, principal):
    """One file's history from Ledger's own records, newest first: where it came from, its versions, proposals, working
    copies and their updates, Trash, and the Agenda. Each line is something that was recorded, never inferred."""
    rel = rel_of(kernel, path);events = []
    def add(at, what):
        if at:events.append({'at': at, 'what': what})
    if path.exists():add(path.stat().st_mtime, 'last changed on disk')
    for v in versions(kernel, path):add(v['kept'], 'a version was kept before a change (%s)' % v['version'][:15])
    with opened(kernel) as db:
        for r in db.execute('SELECT * FROM files_origin WHERE path=?', (rel,)):add(r['at'], 'kept in Files from the delivery “%s”' % (r['label'] or r['delivery'][:8]))
        for r in db.execute('SELECT * FROM files_proposals WHERE path=? AND owner=?', (rel, principal.identity)):
            add(r['at'], 'Graphite proposed a change: ' + (r['why'] or '')[:80]);add(r['decided'], {'APPLIED': 'you applied its change', 'DECLINED': 'you declined its change'}.get(r['state'], ''))
        for r in db.execute('SELECT * FROM files_trash WHERE original=?', (rel,)):add(r['at'], 'moved to Trash');add(r['restored'], 'restored from Trash')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'copies' in tables:
            for c in db.execute('SELECT * FROM copies WHERE work=? OR ? LIKE work || \'/%\'', (rel, rel)):
                add(c['created'], 'arrived in a pill and became a working copy' if str(c['source']).startswith('pill:') else 'became a working copy of ' + c['source'].replace(str(Path.home()), '~', 1))
                for p in db.execute('SELECT * FROM copies_proposals WHERE copy=?', (c['id'],)):add(p['at'], 'revision %d frozen for review' % p['revision'])
                for j in db.execute("SELECT * FROM copies_journal WHERE copy=? AND stage IN ('DONE','RECOVERY')", (c['id'],)):
                    add(j['finished'] or j['at'], {'update': 'the original was updated', 'undo': 'the update was undone', 'create': 'a file was added to the original',
                                                   'delete': 'a file was removed from the original'}.get(j['kind'], 'the original was changed') + ('' if j['stage'] == 'DONE' else ' (needs a look)'))
        if 'agenda_items' in tables:
            for a in db.execute('SELECT * FROM agenda_items WHERE owner=? AND program LIKE ?', (principal.identity, '%@files:' + rel + '%')):
                add(a['created'], ('watched' if a['watch'] else 'on the Agenda') + ': ' + a['title'][:60])
    events.sort(key=lambda e:-e['at'])
    return {'path': rel, 'events': events[:60]}


def write_text(kernel, path, text):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    kept = keep_version(kernel, path)
    temporary = path.with_name('.' + path.name + '.writing');temporary.write_text(text, encoding='utf-8');os.replace(temporary, path)
    return kept


def export(kernel, path, purpose, name=None):
    files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file() and not any(machine(q) for q in p.relative_to(path).parents if str(q) != '.') and not machine(p))
    left_out = []
    if purpose == 'manufacturing':
        chosen = []
        for f in files:(chosen if kind_of(f) in MANUFACTURING else left_out).append(f)
        files = chosen
    if not files:raise ValueError('FILES_NOTHING_TO_EXPORT: nothing of that kind here')
    stamp = time.strftime('%Y-%m-%d')
    target = free_name(root(kernel) / EXPORTS, clean_name(name) if name else '%s_%s_%s.zip' % (path.name or 'Files', 'fab' if purpose == 'manufacturing' else 'share', stamp))
    sums = []
    base = path if path.is_dir() else path.parent
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for f in files:
            arc = f.relative_to(base).as_posix();data = f.read_bytes()
            archive.writestr(arc, data);sums.append('%s  %s' % (hashlib.sha256(data).hexdigest(), arc))
        archive.writestr('SHA256SUMS', '\n'.join(sums) + '\n')
    return {'export': rel_of(kernel, target), 'files': len(files), 'left_out': [f.name for f in left_out][:50], 'purpose': purpose,
            'note': 'A copy. Your files stay as they are.'}


DATA_ROWS = 2000


def number(text):
    """A cell as staC sees it: numbers as numbers, everything else as the text it is."""
    if isinstance(text, (int, float)):return text
    s = str(text).strip().replace(',', '') if isinstance(text, str) and text.strip().count(',') <= 3 else str(text).strip()
    try:
        value = float(s)
        return int(value) if value.is_integer() and '.' not in s and 'e' not in s.lower() else value
    except ValueError:
        return text


def keyed(rows):
    """Rows keyed by the header row (its first non-empty row), so staC can say `where Qty>10 | select Ref`."""
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:return []
    names, seen = [], {}
    for i, cell in enumerate(rows[0]):
        name = str(cell).strip() or 'column_%d' % (i + 1)
        name = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in name).strip('_') or 'column_%d' % (i + 1)
        if name[0].isdigit():name = 'c_' + name
        seen[name] = seen.get(name, 0) + 1;names.append(name if seen[name] == 1 else '%s_%d' % (name, seen[name]))
    return [{names[i]: number(cell) for i, cell in enumerate(row) if i < len(names)} for row in rows[1:DATA_ROWS + 1]]


def data_of(view):
    """What a viewer module understands about a file, as plain data for staC."""
    kind = view.get('kind');data = {}
    if view.get('sheets'):
        data['sheets'] = {s['name']: keyed(s['rows']) for s in view['sheets']}
        data['rows'] = next(iter(data['sheets'].values()), [])
    elif view.get('table'):
        data['rows'] = keyed([view['table']['columns']] + view['table']['rows'])
    if view.get('drawing'):
        layers = {}
        for e in view['drawing']:
            row = layers.setdefault(e['layer'], {'layer': e['layer'], 'entities': 0})
            row['entities'] += 1;row[e['type'].lower()] = row.get(e['type'].lower(), 0) + 1
        data['layers'] = sorted(layers.values(), key=lambda r:r['layer'])
        data['texts'] = [{'layer': e['layer'], 'text': e['text'], 'x': e.get('x'), 'y': e.get('y')} for e in view['drawing'] if e.get('text')][:DATA_ROWS]
    if view.get('gerber'):
        data['layers'] = [{'layer': l['name'], 'role': l.get('role'), 'strokes': len(l.get('lines', [])), 'pads': len(l.get('flashes', [])),
                           'holes': len(l.get('holes', []))} for l in view['gerber'].get('layers', [])]
    if kind in ('markdown', 'text', 'code') and view.get('text') is not None:
        lines = view['text'].splitlines()
        data['lines'] = [{'line': i + 1, 'text': line} for i, line in enumerate(lines[:DATA_ROWS])]
        if kind == 'markdown':data['headings'] = [{'line': r['line'], 'level': len(r['text']) - len(r['text'].lstrip('#')), 'text': r['text'].lstrip('#').strip()}
                                                  for r in data['lines'] if r['text'].startswith('#')]
    return data


TEXT_KINDS = ('text', 'code', 'markdown', 'json', 'csv', 'kicad', 'gerber', 'excellon', 'dxf')
DIFF_LINES = 4000


def described(path, name=None):
    from .universal_view import Source, describe
    source = Source.file(path)
    if name:source.name = name  # a kept snapshot has no extension of its own; it is read as the file it came from
    return describe(source, with_hash=True)


def text_diff(before, after):
    """Lines as added, removed or the same, with long unchanged runs folded. Words, not colours, carry the meaning."""
    import difflib
    a, b = before.splitlines()[:DIFF_LINES], after.splitlines()[:DIFF_LINES];rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            run = list(range(i1, i2))
            keep = run if len(run) <= 6 else run[:3] + [None] + run[-3:]
            for i in keep:
                if i is None:rows.append({'op': 'folded', 'text': '%d unchanged lines' % (len(run) - 6)})
                else:rows.append({'op': 'same', 'before': i + 1, 'after': j1 + (i - i1) + 1, 'text': a[i]})
            continue
        for i in range(i1, i2):rows.append({'op': 'removed', 'before': i + 1, 'text': a[i]})
        for j in range(j1, j2):rows.append({'op': 'added', 'after': j + 1, 'text': b[j]})
    return {'lines': rows, 'added': sum(r['op'] == 'added' for r in rows), 'removed': sum(r['op'] == 'removed' for r in rows),
            'cut': max(len(before.splitlines()), len(after.splitlines())) > DIFF_LINES}


def cell(row, col):
    letters = '';col += 1
    while col:col, r = divmod(col - 1, 26);letters = chr(65 + r) + letters
    return '%s%d' % (letters, row + 1)


def sheet_diff(before_sheets, after_sheets):
    """Cell by cell, per sheet: what changed, what was added, what was removed."""
    out = [];names = list(dict.fromkeys(list(before_sheets) + list(after_sheets)))
    for name in names:
        a, b = before_sheets.get(name), after_sheets.get(name)
        if a is None or b is None:out.append({'sheet': name, 'state': 'added' if a is None else 'removed', 'cells': []});continue
        cells = []
        for r in range(max(len(a), len(b))):
            ra = a[r] if r < len(a) else [];rb = b[r] if r < len(b) else []
            for c in range(max(len(ra), len(rb))):
                va = ra[c] if c < len(ra) else '';vb = rb[c] if c < len(rb) else ''
                if str(va) != str(vb):cells.append({'cell': cell(r, c), 'before': va, 'after': vb,
                                                    'op': 'added' if va == '' else 'removed' if vb == '' else 'changed'})
                if len(cells) >= DIFF_LINES:break
        out.append({'sheet': name, 'state': 'changed' if cells else 'same', 'cells': cells})
    return out


def compare(kernel, args, principal):
    """Two files, a file and one of its versions, or a file and Slate's proposed change."""
    path = resolve(kernel, args['path'])
    if path.is_dir():raise ValueError('FILES_IS_A_FOLDER')
    label_b = rel_of(kernel, path)
    if args.get('proposal'):
        with opened(kernel) as db:
            row = db.execute('SELECT * FROM files_proposals WHERE id=? AND owner=?', (args['proposal'], principal.identity)).fetchone()
        if row is None or row['path'] != rel_of(kernel, path):raise ValueError('FILES_PROPOSAL_NOT_FOUND')
        before_text = path.read_text(encoding='utf-8', errors='replace');after_text = row['text']
        return {'kind': 'text', 'before': label_b, 'after': 'Graphite\'s proposal: ' + row['why'], **text_diff(before_text, after_text)}
    if args.get('version'):
        other = root(kernel) / VERSIONS / rel_of(kernel, path) / clean_name(args['version'])
        if not other.is_file():raise ValueError('FILES_VERSION_NOT_FOUND')
        older, newer, label_a = other, path, 'version ' + args['version']
    elif args.get('other'):
        older, newer, label_a = resolve(kernel, args['other']), path, None
        if older.is_dir():raise ValueError('FILES_IS_A_FOLDER')
        label_a, label_b = rel_of(kernel, older), rel_of(kernel, path)
    else:raise ValueError('FILES_COMPARE_WHAT: give other, version or proposal')
    return compare_paths(older, newer, label_a, label_b)


def compare_paths(older, newer, label_a, label_b, name=None):
    """Any two files Ledger may read, described by the viewer modules and compared in words."""
    va, vb = described(older, name), described(newer, name)
    out = {'before': label_a, 'after': label_b, 'kind': vb['kind'], 'same_bytes': va.get('sha256') == vb.get('sha256')}
    fa, fb = dict(va['summary']), dict(vb['summary'])
    out['facts'] = [{'fact': k, 'before': fa.get(k), 'after': fb.get(k), 'op': 'same' if fa.get(k) == fb.get(k) else 'changed'}
                    for k in dict.fromkeys(list(fa) + list(fb))]
    if va.get('sheets') and vb.get('sheets'):
        out['sheets'] = sheet_diff({s['name']: s['rows'] for s in va['sheets']}, {s['name']: s['rows'] for s in vb['sheets']})
    elif va.get('table') and vb.get('table'):
        out['sheets'] = sheet_diff({'rows': [va['table']['columns']] + va['table']['rows']}, {'rows': [vb['table']['columns']] + vb['table']['rows']})
    if va['kind'] in TEXT_KINDS and vb['kind'] in TEXT_KINDS:
        def text_of(path, view):
            if view.get('text') is not None:return view['text']
            from .universal_view import decode
            return decode(path.read_bytes()[:8 * 1024 * 1024])[0]
        out.update(text_diff(text_of(older, va), text_of(newer, vb)))
    out['visual'] = va['kind'] in ('image', 'pdf', 'gerber', 'excellon', 'stl', 'obj', '3mf', 'dxf', 'spreadsheet', 'video')
    return out


SEARCH_TEXT_KINDS = ('text', 'code', 'markdown', 'json', 'csv', 'kicad', 'dxf')
SEARCH_BYTES = 2 * 1024 * 1024
FIND_KEYS = ('text', 'kind', 'days', 'under', 'limit', 'all')
SMART = '.find'


def find(kernel, args):
    """Files whose name or words match, of a kind, changed recently: the answer to a search or a smart folder."""
    import time as clock
    base = resolve(kernel, args.get('under', ''));needle = (args.get('text') or '').strip().casefold()
    kind = (args.get('kind') or '').strip().lower();since = clock.time() - args['days'] * 86400 if args.get('days') else None
    limit = args.get('limit', 200);found = [];looked = 0
    for path in sorted(base.rglob('*')):
        relative = path.relative_to(root(kernel)).parts
        if relative and relative[0] in (TRASH, VERSIONS):continue
        if not args.get('all') and any(machine(Path(part)) for part in relative):continue
        if path.is_dir() or path.is_symlink() or path.suffix == SMART:continue
        looked += 1
        try:stat = path.stat()
        except OSError:continue
        if since and stat.st_mtime < since:continue
        file_kind = kind_of(path)
        if kind and kind not in (file_kind, KIND_WORDS.get(file_kind, '').lower()):continue
        where = None
        if needle:
            if needle in path.name.casefold():where = 'name'
            elif file_kind in SEARCH_TEXT_KINDS and stat.st_size <= SEARCH_BYTES:
                try:
                    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                        if needle in line.casefold():where = 'line %d: %s' % (number, line.strip()[:120]);break
                except OSError:pass
            if where is None:continue
        row = entry(kernel, path)
        if where:row['found'] = where
        found.append(row)
        if len(found) >= limit:break
    return {'records': found, 'looked_at': looked, 'question': {k: args[k] for k in FIND_KEYS if k in args}}


def dispatch(kernel, op, args, principal):
    owner = principal.identity
    if op == 'files.list':
        folder = resolve(kernel, args.get('path', ''))
        if not folder.is_dir():raise ValueError('FILES_NOT_A_FOLDER')
        rows = [entry(kernel, p) for p in folder.iterdir() if not (folder == root(kernel) and p.name in (TRASH, VERSIONS))]
        shown = rows if args.get('all') else [r for r in rows if not r['machine']]
        order = lambda r:(r['kind'] not in ('folder', 'smart'), r['name'].casefold())
        return {'schema': 'arc.files/1', 'root': str(root(kernel)), 'path': rel_of(kernel, folder) if folder != root(kernel) else '',
                'entries': sorted(shown, key=order), 'hidden': len(rows) - len(shown), 'slate_area': SLATE, 'exports': EXPORTS}
    if op == 'files.get':
        path = resolve(kernel, args['path']);value = entry(kernel, path)
        expected = args.get('expected_sha256');sheet = args.get('sheet')
        if (expected or sheet is not None) and not path.is_file():raise ValueError('The selected source is no longer a file.')
        value['versions'] = versions(kernel, path) if path.is_file() else []
        value['in_slate_area'] = (root(kernel) / SLATE) in path.parents or path == root(kernel) / SLATE
        if path.is_file():
            from .universal_view import Source, describe, sha256
            try:
                source = Source.file(path)
                if expected and sha256(source) != expected:
                    raise ValueError('The selected source changed. Reload the worksheet and select the rows again.')
                view = describe(source, with_hash=False)
                value['view'] = {'kind': view['kind'], 'summary': [list(s) for s in view['summary']][:12], 'notice': view.get('notice')}
                value['facts'] = {str(k): v for k, v in view['summary']}
                value['data'] = data_of(view)
            except Exception as exc:
                if expected or sheet is not None:raise
                value['view'] = {'summary': 'Not readable here: ' + str(exc)[:200]}
            if sheet is not None:
                rows = value['data'].get('sheets', {}).get(sheet)
                if rows is None:raise ValueError('The selected sheet is unavailable.')
                value['data'] = {'rows': rows}
            if expected:
                if sha256(source) != expected:raise ValueError('The selected source changed while it was being read.')
                value['sha256'] = expected
        return value
    if op == 'files.versions':return {'path': args['path'], 'versions': versions(kernel, resolve(kernel, args['path']))}
    if op == 'files.mkdir':
        folder = resolve(kernel, args.get('path', ''));target = folder / clean_name(args['name'])
        may_change(kernel, target, principal)
        if target.exists():raise ValueError('FILES_EXISTS: that name is taken here')
        target.mkdir(mode=0o700);return entry(kernel, target)
    if op == 'files.rename':
        path = resolve(kernel, args['path']);target = path.with_name(clean_name(args['name']))
        may_change(kernel, path, principal);may_change(kernel, target, principal)
        if path in (root(kernel) / SLATE, root(kernel) / EXPORTS):raise ValueError('FILES_RESERVED: the Slate folder (Graphite’s area) and Egress keep their names')
        if target.exists():raise ValueError('FILES_EXISTS: that name is taken here')
        path.rename(target);return entry(kernel, target)
    if op in ('files.copy', 'files.move'):
        path = resolve(kernel, args['path']);folder = resolve(kernel, args['to'])
        if not folder.is_dir():raise ValueError('FILES_NOT_A_FOLDER')
        if path.is_dir() and (folder == path or path in folder.parents):raise ValueError('FILES_INTO_ITSELF')
        target = free_name(folder, path.name);may_change(kernel, target, principal)
        if op == 'files.move':
            may_change(kernel, path, principal)
            if path in (root(kernel) / SLATE, root(kernel) / EXPORTS):raise ValueError('FILES_RESERVED: the Slate folder (Graphite’s area) and Egress stay where they are')
            shutil.move(str(path), str(target))
        elif path.is_dir():shutil.copytree(path, target, symlinks=True)
        else:shutil.copy2(path, target)
        return entry(kernel, target)
    if op == 'files.trash':
        path = resolve(kernel, args['path']);may_change(kernel, path, principal)
        if path == root(kernel) or path in (root(kernel) / SLATE, root(kernel) / EXPORTS):raise ValueError('FILES_RESERVED: this folder stays')
        ident = uuid.uuid4().hex;stored = root(kernel) / TRASH / ident
        stored.mkdir(mode=0o700);original = rel_of(kernel, path);shutil.move(str(path), str(stored / path.name))
        with opened(kernel) as db:db.execute('INSERT INTO files_trash VALUES(?,?,?,?,?,NULL)', (ident, owner, original, ident + '/' + path.name, time.time()))
        return {'trashed': original, 'id': ident, 'note': 'In Trash. Restore puts it back.'}
    if op == 'files.trash_list':
        with opened(kernel) as db:
            return {'trash': [dict(r) for r in db.execute('SELECT id, original, at FROM files_trash WHERE owner=? AND restored IS NULL ORDER BY at DESC', (owner,))]}
    if op == 'files.restore':
        with opened(kernel) as db:
            row = db.execute('SELECT * FROM files_trash WHERE id=? AND owner=? AND restored IS NULL', (args['id'], owner)).fetchone()
            if row is None:raise ValueError('FILES_TRASH_NOT_FOUND')
            source = root(kernel) / TRASH / row['stored']
            original = resolve(kernel, row['original'], must_exist=False);original.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            target = free_name(original.parent, original.name);shutil.move(str(source), str(target))
            with contextlib.suppress(OSError):(root(kernel) / TRASH / args['id']).rmdir()
            db.execute('UPDATE files_trash SET restored=? WHERE id=?', (time.time(), args['id']))
            return {'restored': rel_of(kernel, target)}
    if op == 'files.write':
        path = resolve(kernel, args['path'], must_exist=False);may_change(kernel, path, principal)
        if path.is_dir():raise ValueError('FILES_IS_A_FOLDER')
        kept = write_text(kernel, path, args['text']);return {**entry(kernel, path), 'kept_version': kept}
    if op == 'files.cells':  # a spreadsheet changed cell by cell (sheet_edit): the version before is kept, as for text
        from . import sheet_edit
        path = resolve(kernel, args['path']);may_change(kernel, path, principal)
        if path.suffix.lower() != '.xlsx':raise ValueError('FILES_NOT_A_WORKBOOK: cell changes are for .xlsx workbooks')
        data = path.read_bytes();edits = sheet_edit.parse_edits(args['changes'], sheet_edit.first_sheet(data))
        new = sheet_edit.apply(data, edits);kept = keep_version(kernel, path)
        temporary = path.with_name('.' + path.name + '.writing');temporary.write_bytes(new);os.replace(temporary, path)
        return {**entry(kernel, path), 'kept_version': kept, 'cells': len(edits)}
    if op == 'files.propose':
        path = resolve(kernel, args['path'], must_exist=False)
        if path.is_dir():raise ValueError('FILES_IS_A_FOLDER')
        base = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        ident = uuid.uuid4().hex
        with opened(kernel) as db:
            db.execute('INSERT INTO files_proposals VALUES(?,?,?,?,?,?,?,?,NULL)', (ident, owner, rel_of(kernel, path), args['text'], args['why'], base, 'WAITING', time.time()))
        return {'proposal': ident, 'path': rel_of(kernel, path), 'state': 'WAITING', 'note': 'Waiting for your decision.'}
    if op == 'files.proposals':
        with opened(kernel) as db:
            return {'proposals': [dict(r) for r in db.execute("SELECT id, path, why, at, length(text) AS size FROM files_proposals WHERE owner=? AND state='WAITING' ORDER BY at",
                                                               (owner,))]}
    if op == 'files.decide':
        with opened(kernel) as db:
            row = db.execute("SELECT * FROM files_proposals WHERE id=? AND owner=? AND state='WAITING'", (args['id'], owner)).fetchone()
            if row is None:raise ValueError('FILES_PROPOSAL_NOT_FOUND')
            if not args['apply']:
                db.execute("UPDATE files_proposals SET state='DECLINED', decided=? WHERE id=?", (time.time(), row['id']));return {'state': 'DECLINED'}
            path = resolve(kernel, row['path'], must_exist=False)
            now = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            if now != row['base']:raise ValueError('FILES_CHANGED_SINCE_PROPOSED: look at it again before applying')
            kept = write_text(kernel, path, row['text'])
            db.execute("UPDATE files_proposals SET state='APPLIED', decided=? WHERE id=?", (time.time(), row['id']))
            return {'state': 'APPLIED', 'path': row['path'], 'kept_version': kept}
    if op == 'files.revert':
        path = resolve(kernel, args['path']);may_change(kernel, path, principal)
        version = root(kernel) / VERSIONS / rel_of(kernel, path) / clean_name(args['version'])
        if not version.is_file():raise ValueError('FILES_VERSION_NOT_FOUND')
        kept = keep_version(kernel, path);shutil.copy2(version, path)
        return {'reverted': rel_of(kernel, path), 'to': args['version'], 'kept_version': kept}
    if op == 'files.compare':return compare(kernel, args, principal)
    if op == 'files.find':return find(kernel, args)
    if op == 'files.smart':
        question = {k: v for k, v in args['find'].items() if k in FIND_KEYS}
        if not question:raise ValueError('FILES_SMART_EMPTY: say what it should find')
        find(kernel, {**question, 'limit': 1})  # the question must work before it is kept
        folder = resolve(kernel, args.get('path', ''));target = folder / (clean_name(args['name']) + SMART)
        may_change(kernel, target, principal)
        if target.exists():raise ValueError('FILES_EXISTS: that name is taken here')
        target.write_text(json.dumps({'schema': 'arc.files-smart/1', 'find': question}, indent=2) + '\n', encoding='utf-8')
        return entry(kernel, target)
    if op == 'files.story':return story(kernel, resolve(kernel, args['path'], must_exist=False), principal)
    if op == 'files.keep':
        # Pass A: a file the Office received, copied into Files › Received › <delivery>, with where it came from recorded
        with opened(kernel) as db:
            row = db.execute('SELECT payload FROM receiving_deliveries WHERE id=?', (args['delivery'],)).fetchone() if db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='receiving_deliveries'").fetchone() else None
        if row is None:raise ValueError('FILES_DELIVERY_NOT_FOUND')
        delivery = json.loads(row['payload']);base = Path(delivery.get('staging') or '').resolve()
        source = (base / args['name']).resolve()
        if not str(delivery.get('staging') or '') or base not in source.parents or not source.is_file() or (base / args['name']).is_symlink():
            raise ValueError('FILES_RECEIVED_NOT_FOUND: the received copy is not there')
        label = clean_name((delivery.get('label') or args['delivery'][:8]).replace('/', ' ')[:120])
        folder = root(kernel) / RECEIVED / label;may_change(kernel, folder / source.name, principal)
        folder.mkdir(parents=True, mode=0o700, exist_ok=True);target = free_name(folder, source.name);shutil.copy2(source, target)
        with opened(kernel) as db:
            db.execute('INSERT OR REPLACE INTO files_origin VALUES(?,?,?,?,?)', (rel_of(kernel, target), args['delivery'], args['name'], delivery.get('label') or '', time.time()))
        return {**entry(kernel, target), 'came_from': delivery.get('label') or args['delivery']}
    if op == 'files.export':
        return export(kernel, resolve(kernel, args['path']), args['purpose'], args.get('name'))
    raise ValueError('FILES_UNKNOWN_OPERATION')
