"""Local organizational catalog. References and notes confer no execution authority.

One identity can have several placements. This is a navigation index over existing
work, not a replacement rights register, project store, or evidence authority.
"""
from contextlib import contextmanager, closing
from pathlib import Path
import hashlib
import json
import sqlite3
import time
import uuid
import os
from pathlib import PurePosixPath

SCHEMA = 'arc.concern-catalog/1'
KINDS = ('concern', 'office', 'work', 'project', 'collection', 'note')
STATES = ('active', 'planned', 'paused', 'archived')
RELATIONS = ('part_of', 'maintained_by', 'related_to')
MAX_OBJECTS = 10000
MAX_NOTE = 128 * 1024

# Stable presentation declarations. They do not assert source acceptance or rights.
# 4.0: a new profile starts neutral. Personal projects (ARC-1, the Orange Book, games…) live in a separately
# preserved collection; an existing profile keeps every row it already has, because INSERT OR IGNORE never removes.
DEFAULTS = (
    ('concern', 'concern', 'My work', 'Your work and everything that supports it.', 'active'),
    ('inbox', 'collection', 'Notes', 'Notes and quick thoughts awaiting a more specific place.', 'active'),  # 4.2: was 'Inbox'
    ('ideas', 'collection', 'Ideas', 'Rough ideas, kept in your own words.', 'active'),
    ('projects', 'collection', 'Projects', 'Work with a goal, its sources and its results.', 'active'),
    ('library', 'collection', 'Research & references', 'Reference collections and research tools.', 'active'),
    ('ledger', 'work', 'Graphite', 'This workspace and its supporting services.', 'active'),  # GRAPHITE-01: the id stays 'ledger'
    ('legal', 'office', 'Legal', 'Agreements, rights records and notices.', 'active'),
    ('engineering', 'office', 'Engineering', 'Design, implementation and investigation.', 'active'),
    ('publishing', 'office', 'Publishing', 'Manuscripts, references and editorial work.', 'active'),
    ('operations', 'office', 'Operations', 'Graphite maintenance, installation and recovery.', 'active'),
)
DEFAULT_RELATIONS = tuple((row[0], 'part_of', 'concern') for row in DEFAULTS if row[0] != 'concern') + (
    ('ledger', 'maintained_by', 'engineering'), ('ledger', 'maintained_by', 'operations'), ('concern', 'maintained_by', 'legal'),
)
# GRAPHITE-01 (D32): Graphite is the public name; identities stay. A profile made before the rename keeps its stored seed rows
# (INSERT OR IGNORE never rewrites them and nothing here migrates them). While such a seed word is untouched it is shown in
# Graphite words; a title or description the owner chose is always shown as written.
OLD_SEED_WORDS = {('ledger', 'title'): ('Ledger', 'Graphite'),
                  ('operations', 'summary'): ('Ledger maintenance, installation and recovery.',
                                              'Graphite maintenance, installation and recovery.')}


def shown(ident, value, field='title'):
    """The words a person reads for a catalog row's title (or summary): the stored words, except an untouched pre-rename seed."""
    old, new = OLD_SEED_WORDS.get((ident, field), (None, None))
    return new if old is not None and value == old else value


class CatalogError(ValueError):
    pass


def text(value, label, maximum=240, empty=False):
    if (not isinstance(value, str) or len(value) > maximum or
            (not empty and not value.strip()) or '\x00' in value or
            any(ord(c) < 32 and c not in '\n\t' for c in value)):
        raise CatalogError('Invalid ' + label)
    return value.strip() if label != 'note' else value


VIEWS = ('works', 'offices', 'work', 'archive')


def view_preference(db):
    """One observation of value and opaque revision, including pre-revision profiles."""
    rows={row[0]:row[1] for row in db.execute(
        "SELECT key,value FROM preferences WHERE key IN ('view','view_revision')")}
    value=json.loads(rows.get('view','"works"'))
    revision=json.loads(rows['view_revision']) if 'view_revision' in rows else 'legacy'
    if value not in VIEWS or not isinstance(revision,str) or revision!='legacy' and (
            len(revision)!=32 or any(c not in '0123456789abcdef' for c in revision)):
        raise CatalogError('Catalogue view preference is invalid; original retained')
    return value,revision


def write_view_preference(db,value,expected_revision=None,revision_token=None):
    """Called in the catalogue write transaction, including by the legacy chooser."""
    if value not in VIEWS:raise CatalogError('Unsupported catalog view')
    _,current=view_preference(db)
    if expected_revision is not None and current!=expected_revision:
        raise CatalogError('SETTING_REVISION_CHANGED: catalogue changed; your draft is preserved')
    token=revision_token or uuid.uuid4().hex
    if not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):
        raise CatalogError('Invalid catalogue revision')
    for key,item in [('view',value),('view_revision',token)]:
        db.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                   (key,json.dumps(item)))
    return token


class Catalog:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.exists():
            # closing(): a sqlite3 connection used as a context manager commits but never closes.
            with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)) as check:
                if check.execute('PRAGMA user_version').fetchone()[0] not in (0, 1):
                    raise CatalogError('Unsupported concern catalog version; original retained')
        with self.db() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise CatalogError('Unsupported concern catalog version; original retained')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS objects(
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
                    summary TEXT NOT NULL, state TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS relations(
                    source TEXT NOT NULL REFERENCES objects(id), kind TEXT NOT NULL,
                    target TEXT NOT NULL REFERENCES objects(id),
                    PRIMARY KEY(source,kind,target));
                CREATE TABLE IF NOT EXISTS notes(
                    object_id TEXT PRIMARY KEY REFERENCES objects(id),
                    body TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sources(
                    object_id TEXT NOT NULL REFERENCES objects(id), root TEXT NOT NULL,
                    path TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
                    PRIMARY KEY(object_id,root,path));
                CREATE TABLE IF NOT EXISTS drafts(
                    object_id TEXT NOT NULL REFERENCES objects(id), writer TEXT NOT NULL,
                    body TEXT NOT NULL, base_version INTEGER NOT NULL, at REAL NOT NULL,
                    PRIMARY KEY(object_id,writer));
                CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
                    operation TEXT NOT NULL, object_id TEXT NOT NULL, detail TEXT NOT NULL);
                PRAGMA user_version=1;
            ''')
            try:
                db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts USING fts5(object_id UNINDEXED,title,summary,body)')
                self.fts = True
            except sqlite3.OperationalError:
                self.fts = False
            db.commit()
            db.execute('BEGIN IMMEDIATE')
            new = db.execute('SELECT count(*) FROM objects').fetchone()[0] == 0
            for ident, kind, title, summary, state in DEFAULTS:
                db.execute('INSERT OR IGNORE INTO objects VALUES(?,?,?,?,?,1)',
                           (ident, kind, title, summary, state))
            # 4.2: the quick-notes collection is called Notes. Only an untouched default is renamed; a title you chose stays.
            if db.execute("UPDATE objects SET title='Notes', summary='Notes and quick thoughts awaiting a more specific place.' "
                          "WHERE id='inbox' AND title='Inbox' AND summary='Ideas and notes awaiting a more specific place.'").rowcount:
                if self.fts:
                    db.execute("DELETE FROM catalog_fts WHERE object_id='inbox'")
                    db.execute("INSERT INTO catalog_fts SELECT o.id,o.title,o.summary,coalesce(n.body,'') FROM objects o LEFT JOIN notes n ON n.object_id=o.id WHERE o.id='inbox'")
                self._event(db, 'rename', 'inbox', 'Inbox is now called Notes')
            if new:
                db.executemany('INSERT INTO relations VALUES(?,?,?)', DEFAULT_RELATIONS)
                self._event(db, 'initialize', 'concern', 'Built-in navigation declarations')
            if self.fts and db.execute('SELECT count(*) FROM catalog_fts').fetchone()[0] != db.execute('SELECT count(*) FROM objects').fetchone()[0]:
                db.execute('DELETE FROM catalog_fts')
                db.execute("INSERT INTO catalog_fts SELECT o.id,o.title,o.summary,coalesce(n.body,'') FROM objects o LEFT JOIN notes n ON n.object_id=o.id")

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db
        finally:
            db.close()

    def _index(self, db, ident):
        if self.fts:
            db.execute('DELETE FROM catalog_fts WHERE object_id=?', (ident,))
            db.execute("INSERT INTO catalog_fts SELECT o.id,o.title,o.summary,coalesce(n.body,'') FROM objects o LEFT JOIN notes n ON n.object_id=o.id WHERE o.id=?", (ident,))

    def search(self, query, limit=25):
        query = text(query, 'search', 240, True)
        if type(limit) is not int or not 1 <= limit <= 75:
            raise CatalogError('Invalid search limit')
        if not query:
            return []
        with self.db() as db:
            if self.fts:
                terms = ' AND '.join('"' + part.replace('"', '""') + '"' for part in query.split()[:20])
                rows = db.execute('SELECT o.* FROM catalog_fts f JOIN objects o ON o.id=f.object_id WHERE catalog_fts MATCH ? ORDER BY rank LIMIT ?', (terms, limit))
            else:
                rows = db.execute("SELECT * FROM objects WHERE instr(lower(title || ' ' || summary),lower(?)) > 0 ORDER BY title LIMIT ?", (query, limit))
            return [{**dict(row), 'search_profile': 'Saved titles, descriptions and notes' if self.fts else 'Titles and descriptions only; FTS5 unavailable'} for row in rows]

    @staticmethod
    def _event(db, operation, object_id, detail=''):
        db.execute('INSERT INTO events(at,operation,object_id,detail) VALUES(?,?,?,?)',
                   (time.time(), operation, object_id, detail))

    @staticmethod
    def _object(db, ident):
        row = db.execute('SELECT * FROM objects WHERE id=?', (ident,)).fetchone()
        if row is None:
            raise CatalogError('Catalog item no longer exists')
        return dict(row)

    def get(self, ident):
        with self.db() as db:
            row = self._object(db, ident)
            note = db.execute('SELECT body,version FROM notes WHERE object_id=?', (ident,)).fetchone()
            row['note'] = dict(note) if note else {'body': '', 'version': 0}
            row['sources'] = [dict(r) for r in db.execute('SELECT * FROM sources WHERE object_id=? ORDER BY root,path', (ident,))]
            row['relations'] = [dict(r) for r in db.execute(
                'SELECT * FROM relations WHERE source=? OR target=? ORDER BY kind,source,target',
                (ident, ident))]
            return row

    def snapshot(self):
        with self.db() as db:
            db.execute('BEGIN')
            return {'schema': SCHEMA, 'authority': 'organization-only',
                    'objects': [dict(r) for r in db.execute('SELECT * FROM objects ORDER BY id')],
                    'relations': [dict(r) for r in db.execute('SELECT * FROM relations ORDER BY source,kind,target')],
                    'notes': [dict(r) for r in db.execute('SELECT * FROM notes ORDER BY object_id')],
                    'sources': [dict(r) for r in db.execute('SELECT * FROM sources ORDER BY object_id,root,path')],
                    'drafts': [dict(r) for r in db.execute('SELECT * FROM drafts ORDER BY object_id,writer')],
                    'generation': db.execute('SELECT coalesce(max(seq),0) FROM events').fetchone()[0]}

    def create(self, kind, title, parent='inbox', summary=''):
        if kind not in KINDS or kind == 'concern':
            raise CatalogError('Choose a supported item kind')
        title = text(title, 'title'); summary = text(summary, 'summary', 4000, True)
        ident = 'owner:' + uuid.uuid4().hex
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); parent_row = self._object(db, parent)
            if parent_row['state'] == 'archived':
                raise CatalogError('Restore the destination before adding work')
            if db.execute('SELECT count(*) FROM objects').fetchone()[0] >= MAX_OBJECTS:
                raise CatalogError('Catalog item limit reached')
            db.execute('INSERT INTO objects VALUES(?,?,?,?,?,1)',
                       (ident, kind, title, summary, 'active'))
            relation = 'maintained_by' if parent_row['kind'] == 'office' else 'part_of'
            db.execute('INSERT INTO relations VALUES(?,?,?)', (ident, relation, parent))
            self._index(db, ident)
            self._event(db, 'create', ident, title)
        return ident

    def rename(self, ident, title, expected):
        title = text(title, 'title')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); row = self._object(db, ident)
            if row['version'] != expected:
                raise CatalogError('Item changed in another view; refresh before renaming')
            db.execute('UPDATE objects SET title=?,version=version+1 WHERE id=?', (title, ident))
            self._index(db, ident)
            self._event(db, 'rename', ident, title)

    def set_state(self, ident, state, expected):
        if state not in STATES or ident == 'concern':
            raise CatalogError('Invalid lifecycle change')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); row = self._object(db, ident)
            if row['version'] != expected:
                raise CatalogError('Item changed; refresh before changing its state')
            db.execute('UPDATE objects SET state=?,version=version+1 WHERE id=?', (state, ident))
            self._event(db, 'state', ident, state)

    def link(self, source, kind, target):
        if kind not in RELATIONS or source == target:
            raise CatalogError('Invalid relationship')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); self._object(db, source); other = self._object(db, target)
            if kind == 'maintained_by' and other['kind'] != 'office':
                raise CatalogError('A maintaining office must be an office')
            if kind == 'part_of':
                # Follow target's ancestors. A new edge cannot contain its own source.
                cyclic = db.execute('''WITH RECURSIVE ancestors(id) AS (
                    SELECT ? UNION SELECT r.target FROM relations r JOIN ancestors a
                    ON r.source=a.id WHERE r.kind='part_of') SELECT 1 FROM ancestors WHERE id=?''',
                    (target, source)).fetchone()
                if cyclic:
                    raise CatalogError('This placement would create a containment loop')
            cur = db.execute('INSERT OR IGNORE INTO relations VALUES(?,?,?)', (source, kind, target))
            if cur.rowcount:
                self._event(db, 'link', source, kind + ':' + target)

    def unlink(self, source, kind, target):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); self._object(db, source)
            cur = db.execute('DELETE FROM relations WHERE source=? AND kind=? AND target=?',
                             (source, kind, target))
            if cur.rowcount:
                self._event(db, 'unlink', source, kind + ':' + target)

    def save_note(self, ident, body, expected):
        body = text(body, 'note', MAX_NOTE, True)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); self._object(db, ident)
            row = db.execute('SELECT version FROM notes WHERE object_id=?', (ident,)).fetchone()
            if (row['version'] if row else 0) != expected:
                raise CatalogError('This note changed elsewhere; copy your draft or refresh before saving')
            version = expected + 1
            db.execute('INSERT INTO notes VALUES(?,?,?) ON CONFLICT(object_id) DO UPDATE SET body=excluded.body,version=excluded.version',
                       (ident, body, version))
            self._index(db, ident)
            self._event(db, 'save_note', ident)
        return version

    def save_draft(self, ident, writer, body, base_version):
        if not isinstance(writer, str) or len(writer) != 32 or any(c not in '0123456789abcdef' for c in writer):
            raise CatalogError('Invalid draft identity')
        body = text(body, 'note', MAX_NOTE, True)
        if type(base_version) is not int or base_version < 0:
            raise CatalogError('Invalid saved-note revision')
        with self.db() as db:
            self._object(db, ident)
            db.execute('INSERT INTO drafts VALUES(?,?,?,?,?) ON CONFLICT(object_id,writer) DO UPDATE SET body=excluded.body,base_version=excluded.base_version,at=excluded.at',
                       (ident, writer, body, base_version, time.time()))

    def drafts(self, ident):
        with self.db() as db:
            self._object(db, ident)
            return [dict(r) for r in db.execute('SELECT * FROM drafts WHERE object_id=? ORDER BY at DESC', (ident,))]

    def discard_draft(self, ident, writer):
        with self.db() as db:
            db.execute('DELETE FROM drafts WHERE object_id=? AND writer=?', (ident, writer))

    def attach_source(self, ident, root, relative, expected=None):
        observed = fingerprint(root, relative)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE'); self._object(db, ident)
            prior = db.execute('SELECT sha256 FROM sources WHERE object_id=? AND root=? AND path=?',
                               (ident, observed['root'], relative)).fetchone()
            if prior and expected != prior['sha256']:
                raise CatalogError('Source is already linked; use Update reference after reviewing it')
            if not prior and expected is not None:
                raise CatalogError('Source link changed; refresh before updating it')
            db.execute('INSERT INTO sources VALUES(?,?,?,?,?) ON CONFLICT(object_id,root,path) DO UPDATE SET sha256=excluded.sha256,bytes=excluded.bytes',
                       (ident, observed['root'], relative, observed['sha256'], observed['bytes']))
            self._event(db, 'source_reference', ident, relative)
        return observed

    def preference(self, key, default=None):
        with self.db() as db:
            row = db.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_preference(self, key, value):
        if key not in ('view', 'expanded'):
            raise CatalogError('Unsupported presentation preference')
        if key == 'view' and value not in ('works', 'offices', 'work', 'archive'):
            raise CatalogError('Unsupported catalog view')
        if key == 'expanded' and (not isinstance(value, list) or len(value) > 1000 or
                any(not isinstance(v, str) or len(v) > 500 for v in value)):
            raise CatalogError('Invalid expansion state')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if key=='view':write_view_preference(db,value)
            else:db.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, json.dumps(value)))

    def backup(self, destination):
        destination = Path(destination)
        if destination.exists():
            raise CatalogError('Choose a new backup file; existing files are preserved')
        if not destination.parent.is_dir():
            raise CatalogError('Choose an existing backup folder')
        try:
            with destination.open('xb'):
                pass
            source = sqlite3.connect(self.path)
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CatalogError('Backup integrity check failed')
            finally:
                target.close(); source.close()
        except Exception:
            # No overwrite or restore is attempted. The failed destination is explicit.
            raise
        return {'schema': SCHEMA, 'bytes': destination.stat().st_size,
                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                'scope': 'Concern catalog, saved notes and recovery drafts only; not a complete Ledger edition'}


def tree(snapshot, view='works'):
    """Bounded view projection. Placements refer to shared IDs, never copied records."""
    if view not in ('works', 'offices', 'work', 'archive'):
        raise CatalogError('Unsupported catalog view')
    objects = {r['id']: r for r in snapshot['objects']}
    relations = snapshot['relations']
    remaining = [2000]
    depth_limited = [False]
    children = {}
    for r in relations:
        if r['kind'] == 'part_of':
            children.setdefault(r['target'], []).append(r['source'])
    def node(ident, path=()):
        remaining[0] -= 1
        row = objects[ident]
        if len(path) >= 12 and children.get(ident):
            depth_limited[0] = True
        return {'id': ident, 'title': row['title'], 'kind': row['kind'], 'state': row['state'],
                'children': [node(c, path + (ident,)) for c in sorted(children.get(ident, []),
                    key=lambda c: (objects[c]['title'].casefold(), c))
                    if c not in path and len(path) < 12 and remaining[0] > 0 and objects[c]['state'] != 'archived' and
                    objects[c]['kind'] != 'office']}
    root = {**objects['concern'], 'children': []}
    if view == 'works':
        ids = [i for i, r in objects.items() if i != 'concern' and r['kind'] != 'office' and
               r['state'] != 'archived' and not any(i in v for k, v in children.items() if k != 'concern' and objects[k]['state'] != 'archived' and objects[k]['kind'] != 'office')]
        order = {'arc1': 0, 'ledger': 1, 'slate': 2, 'stac': 3, 'orange_book': 4,
                 'games': 5, 'library': 6, 'inbox': 7}
        root['children'] = [node(i) for i in sorted(ids, key=lambda i: (order.get(i, 20), objects[i]['title'].casefold())) if remaining[0] > 0]
    elif view == 'offices':
        for ident, row in sorted(objects.items(), key=lambda item: item[1]['title'].casefold()):
            if remaining[0] <= 0 or row['kind'] != 'office' or row['state'] == 'archived':
                continue
            item = node(ident)
            item['children'] = [node(r['source']) for r in relations if r['kind'] == 'maintained_by' and
                                r['target'] == ident and r['source'] != 'concern' and
                                objects[r['source']]['state'] != 'archived' and remaining[0] > 0]
            root['children'].append(item)
    else:
        states = ('archived',) if view == 'archive' else ('active', 'planned', 'paused')
        root['children'] = [{**node(i), 'children': []} for i, r in sorted(objects.items(),
            key=lambda item: item[1]['title'].casefold()) if i != 'concern' and
            remaining[0] > 0 and r['state'] in states and (view == 'archive' or r['kind'] in ('project', 'note'))]
    root['bounded'] = remaining[0] <= 0 or depth_limited[0]
    return root


def fingerprint(root, relative):
    """Check saved bytes in an explicit current root; no parsing or execution."""
    pure = PurePosixPath(relative)
    if (not relative or pure.is_absolute() or '\\' in relative or ':' in relative or
            any(p in ('..', '.', '.ledger', '.git', '__pycache__') for p in pure.parts)):
        raise CatalogError('Choose a source in the current working directory')
    root = Path(root).resolve(); path = root.joinpath(*pure.parts)
    if any(p.is_symlink() for p in (path, *path.parents) if p != root and root in p.parents):
        raise CatalogError('Linked paths are not source references')
    path.resolve().relative_to(root)
    before = path.stat()
    size = before.st_size
    if size > 32 * 1024 * 1024 or not path.is_file():
        raise CatalogError('Source reference supports ordinary files up to 32 MiB')
    digest = hashlib.sha256(); count = 0; started = time.monotonic()
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        path.resolve().relative_to(root)
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_mtime_ns, opened.st_size) != (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size):
            raise CatalogError('Source changed before reading; retry when saved')
        for chunk in iter(lambda: stream.read(65536), b''):
            count += len(chunk)
            if count > 32 * 1024 * 1024 or time.monotonic() - started > 3:
                raise CatalogError('Source reference read exceeded its bound')
            digest.update(chunk)
    after = path.stat()
    if count != size or (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size) != (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size):
        raise CatalogError('Source changed while reading; retry when saved')
    return {'root': str(root), 'path': relative, 'sha256': digest.hexdigest(), 'bytes': count}


def source_state(source, root):
    if source['root'] != str(Path(root).resolve()):
        return 'Different working directory'
    try:
        current = fingerprint(root, source['path'])
    except (OSError, ValueError):
        return 'Unavailable'
    return 'Current saved file' if current['sha256'] == source['sha256'] else 'Changed since linked'


def attention(item, *, dirty=False):
    """Presentation metadata only. Private note/source contents are not included."""
    return {'schema': 'arc.concern-attention/1', 'object_id': item['id'],
            'title': item['title'], 'kind': item['kind'], 'state': item['state'],
            'version': item['version'], 'dirty': bool(dirty),
            'authority': 'organization-only', 'effects': []}
