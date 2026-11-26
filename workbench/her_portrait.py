"""Her portrait from your workspace (Graphite 1.0, P1): kasandra/portrait.png (or .jpg), admitted like her character file.

The plan's decision (PLAN_1.0 section 3): your own pictures stay out of the program. Her portrait in every look is drawn
from <workspace>/kasandra/portrait.png (or portrait.jpg / portrait.jpeg) when you put one there and admit it; until then
the shipped art is used. Admitting keeps the picture's exact bytes as a kept copy under kasandra/.revisions/
(portrait-<sha256>.png or .jpg) and a line in kasandra/.revisions/portrait.json; her column draws the kept copy, never the
file itself, so a picture you change afterwards changes nothing until you admit it again. Taking an earlier one back is a
new line pointing at the same bytes. "Shipped art" again is a line with no picture.

    kasandra.portrait        {}                                read     the portrait in force, the file now, in plain words
    kasandra.portrait.admit  {expected_sha256} or {revision}   approve  admit the file as it is now (the bytes you read),
                             or {shipped: true}                         take an earlier one back, or go back to the shipped art

Only a picture is admitted: PNG or JPEG by its first bytes, at most MOST_BYTES; whether it decodes is the window's to find
(a picture that will not decode is not drawn, and the shipped art is). A link is never followed. Nothing here is a model's
word: admitting is your press (the approve scope), and the read is an observer (showing her column is not an event).

Your picture and its kept copies are private, as your character file is: PRIVATE_NAME finds them by name in a payload or
an archive (tools/check_hatch.py carries the same rule).

Pure Python: no Qt, no model, no network, no float.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

FOLDER = 'kasandra'
NAMES = ('portrait.png', 'portrait.jpg', 'portrait.jpeg')
REVISIONS = '.revisions'
INDEX = 'portrait.json'
SCHEMA = 'kasandra.portrait/1'
INDEX_SCHEMA = 'ledger.portrait/1'
MOST_BYTES = 16 * 1024 * 1024
KINDS = {'png': b'\x89PNG\r\n\x1a\n', 'jpg': b'\xff\xd8\xff'}
PRIVATE_NAME = re.compile(r'(?:^|[/!\\])(?:kasandra[/\\]portrait\.(?:png|jpe?g)|\.revisions[/\\]portrait-[0-9a-f]{64}\.(?:png|jpg))$', re.IGNORECASE)

WORDS = {
    'none': 'There is no portrait of yours in this workspace; her column shows the shipped art.',
    'waiting': 'Your picture {name} is in the workspace and not admitted; her column shows {shown}.',
    'in_force': 'Her portrait is your picture, admitted as revision {revision}.',
    'shipped': 'Her portrait is the shipped art.',
    'changed': 'Your picture {name} changed after it was admitted; the admitted one is shown until you admit it again.',
    'kept': 'Kept your picture as revision {revision}; her column shows it now.',
    'same': 'That picture is already the one in force; nothing changed.',
    'back': 'Her column shows the shipped art again (revision {revision}); your picture stays where it is.',
}
_SHA = {}       # path -> (mtime_ns, size, sha256): the file is read again only when it changed


def _say(key, **slots):
    return WORDS[key].format(**slots)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _folder(root):
    folder = Path(root) / FOLDER
    if folder.is_symlink():raise ValueError('PORTRAIT_LINK: the kasandra folder is a link; it is not followed')
    return folder


def kind_of(raw):
    """'png' or 'jpg' by the picture's first bytes, else ''."""
    for kind, magic in KINDS.items():
        if raw[:len(magic)] == magic:return kind
    return ''


def your_file(root):
    """Your picture in the workspace (the first of NAMES that is a plain file), or None. A link is never followed."""
    folder = _folder(root)
    for name in NAMES:
        path = folder / name
        if path.is_symlink():raise ValueError('PORTRAIT_LINK: %s is a link; it is not followed' % name)
        if path.is_file():return path
    return None


def _file_sha(path):
    stat = path.stat()
    seen = _SHA.get(str(path))
    if seen and seen[0] == stat.st_mtime_ns and seen[1] == stat.st_size:return seen[2]
    if stat.st_size > MOST_BYTES:raise ValueError('PORTRAIT_TOO_LARGE: a portrait is at most %d bytes' % MOST_BYTES)
    sha = sha256(path.read_bytes())
    _SHA[str(path)] = (stat.st_mtime_ns, stat.st_size, sha)
    return sha


def _index_path(root):
    return _folder(root) / REVISIONS / INDEX


def index(root):
    """{'schema', 'revisions': [{'revision', 'sha256' ('' for the shipped art), 'kind', 'origin', 'at', 'from'?}]}."""
    try:value = json.loads(_index_path(root).read_text(encoding='utf-8'))
    except (OSError, ValueError):return {'schema': INDEX_SCHEMA, 'revisions': []}
    if not isinstance(value, dict) or value.get('schema') != INDEX_SCHEMA or not isinstance(value.get('revisions'), list):
        return {'schema': INDEX_SCHEMA, 'revisions': []}
    return value


def kept_path(root, sha, kind):
    return _folder(root) / REVISIONS / ('portrait-%s.%s' % (sha, 'png' if kind == 'png' else 'jpg'))


def _write_atomic(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.%s.partial' % path.name)
    with open(temporary, 'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temporary, path)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def in_force(root):
    """(path of the kept copy or None, the revision row or None): what her column draws. A kept copy whose bytes are not
    the recorded ones is not drawn (the shipped art is)."""
    rows = index(root)['revisions']
    if not rows:return None, None
    row = rows[-1]
    if not row.get('sha256'):return None, row
    path = kept_path(root, row['sha256'], row.get('kind'))
    try:
        if path.is_symlink() or not path.is_file() or _file_sha(path) != row['sha256']:return None, row
    except (OSError, ValueError):
        return None, row
    return path, row


def state(root):
    """The portrait in force and your file now, in plain words (what kasandra.portrait answers)."""
    path, row = in_force(root)
    try:mine = your_file(root)
    except ValueError as exc:
        mine = None;problem = str(exc)
    else:problem = ''
    file = None
    if mine is not None:
        try:
            sha = _file_sha(mine);raw = mine.open('rb').read(16)
            file = {'name': '%s/%s' % (FOLDER, mine.name), 'sha256': sha, 'bytes': mine.stat().st_size, 'kind': kind_of(raw)}
        except (OSError, ValueError) as exc:
            problem = str(exc)
    words = []
    if path is not None:words.append(_say('in_force', revision=row['revision']))
    elif row is not None and not row.get('sha256'):words.append(_say('shipped'))
    if file is not None and (row is None or row.get('sha256') != file['sha256']):
        admitted = path is not None
        words.append(_say('changed', name=file['name']) if admitted else _say('waiting', name=file['name'], shown='the shipped art'))
    if file is None and path is None:words.append(_say('none'))
    if problem:words.append(problem)
    return {'schema': SCHEMA, 'in_force': ({'revision': row['revision'], 'sha256': row['sha256'], 'kind': row.get('kind'),
                                           'path': str(path)} if path is not None else None),
            'revision': row['revision'] if row else 0, 'file': file, 'waiting': bool(file and (row is None or row.get('sha256') != file['sha256'])),
            'words': words}


def _append(root, row):
    value = index(root);rows = value['revisions']
    row = dict(row, revision=len(rows) + 1, at=_now());rows.append(row)
    _write_atomic(_index_path(root), json.dumps(value, indent=1, sort_keys=True).encode('utf-8'))
    return row


def admit(root, expected_sha256=None, revision=None, shipped=False):
    """Admit your picture as it is now (only when its bytes are the ones you read), take an earlier revision back, or go
    back to the shipped art. Each is a new line in the index; your picture itself is never written."""
    if sum(1 for given in (expected_sha256 is not None, revision is not None, bool(shipped)) if given) != 1:
        raise ValueError('PORTRAIT_ADMIT: give expected_sha256, revision or shipped')
    rows = index(root)['revisions']
    if shipped:
        if rows and not rows[-1].get('sha256'):return {'changed': False, 'words': [_say('same')], 'state': state(root)}
        row = _append(root, {'sha256': '', 'kind': '', 'origin': 'SHIPPED_ART'})
        return {'changed': True, 'revision': row, 'words': [_say('back', revision=row['revision'])], 'state': state(root)}
    if revision is not None:
        if not 1 <= revision <= len(rows):raise ValueError('PORTRAIT_NO_SUCH_REVISION: there is no revision %d' % revision)
        old = rows[revision - 1]
        if old.get('sha256'):
            kept = kept_path(root, old['sha256'], old.get('kind'))
            if not kept.is_file() or sha256(kept.read_bytes()) != old['sha256']:
                raise ValueError('PORTRAIT_KEPT_COPY_DAMAGED: the kept copy of revision %d is not the picture admitted' % revision)
        if rows[-1].get('sha256') == old.get('sha256'):return {'changed': False, 'words': [_say('same')], 'state': state(root)}
        row = _append(root, {'sha256': old.get('sha256', ''), 'kind': old.get('kind', ''), 'origin': 'TAKEN_BACK', 'from': revision})
        return {'changed': True, 'revision': row, 'words': [_say('kept', revision=row['revision'])], 'state': state(root)}
    path = your_file(root)
    if path is None:raise ValueError('PORTRAIT_NO_FILE: there is no kasandra/portrait.png or portrait.jpg in this workspace')
    if path.stat().st_size > MOST_BYTES:raise ValueError('PORTRAIT_TOO_LARGE: a portrait is at most %d bytes' % MOST_BYTES)
    raw = path.read_bytes()
    if sha256(raw) != expected_sha256:
        raise ValueError('PORTRAIT_FILE_CHANGED: the picture changed after you read it; read it again before admitting')
    kind = kind_of(raw)
    if not kind:raise ValueError('PORTRAIT_NOT_A_PICTURE: only a PNG or JPEG picture is admitted')
    if rows and rows[-1].get('sha256') == expected_sha256:return {'changed': False, 'words': [_say('same')], 'state': state(root)}
    kept = kept_path(root, expected_sha256, kind)
    if not kept.is_file() or sha256(kept.read_bytes()) != expected_sha256:_write_atomic(kept, raw)
    row = _append(root, {'sha256': expected_sha256, 'kind': kind, 'origin': 'YOUR_FILE'})
    return {'changed': True, 'revision': row, 'words': [_say('kept', revision=row['revision'])], 'state': state(root)}


def private_in(names):
    """The names (shipped paths, or archive!member) that are your portrait or its kept copies."""
    return [name for name in names if PRIVATE_NAME.search(str(name))]


# -- the Kernel's operations (1.0 P1) -----------------------------------------------------------------------------------------
_SHA_FIELD = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
FIELDS = {
    'kasandra.portrait': ({}, []),
    'kasandra.portrait.admit': ({'expected_sha256': _SHA_FIELD, 'revision': {'type': 'integer', 'minimum': 1, 'maximum': 100000},
                                 'shipped': {'type': 'boolean'}}, []),
}
SCOPES = {'kasandra.portrait': 'read', 'kasandra.portrait.admit': 'approve'}
OBSERVERS = ('kasandra.portrait',)


def dispatch(kernel, op, args, principal):
    root = kernel.root
    if op == 'kasandra.portrait':return state(root)
    if op == 'kasandra.portrait.admit':return admit(root, args.get('expected_sha256'), args.get('revision'), bool(args.get('shipped')))
    raise ValueError('Unknown portrait operation')
