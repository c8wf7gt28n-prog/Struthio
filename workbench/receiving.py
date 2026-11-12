"""The Office receiving dock: files arrive, are revived, analyzed, cataloged and translated into staC.

One delivery moves through the existing services and adds no second store of the files:

  REVIVING   archives inside the delivery are unpacked (ZIP, TAR, GZIP), and old
             text encodings get a UTF-8 copy beside the original. Nothing is
             changed in the delivered folder.
  SCANNING   ``intake.scan`` snapshots every file into private quarantine.
  REVIEWING  ``intake.review`` reads each file's structure.
  REVIEWED   files wait for the owner. Accepting is the owner's decision.
  INDEXING   ``references.index`` builds the searchable catalog.
  CATALOGED  every accepted file has a staC card: its address and the staC
             programs that read it.

Each step is an ordinary Kernel call with the caller's own principal.
"""
from __future__ import annotations
import bz2
import codecs
import gzip
import io
import json
import lzma
import re
import stat
import shutil
import tarfile
import time
import unicodedata
import uuid
import zipfile
from pathlib import Path

TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
FIELDS = {
    'receiving.status': ({}, []),
    'receiving.deliveries': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}}, []),
    'receiving.receive': ({'path': TEXT, 'label': {'type': 'string', 'maxLength': 120}, 'request_key': TEXT}, ['path']),
    'receiving.advance': ({'id': ID, 'accept': {'type': 'boolean'}, 'reason': {'type': 'string', 'minLength': 3, 'maxLength': 1000}}, ['id']),
    'receiving.cards': ({'id': ID, 'offset': {'type': 'integer', 'minimum': 0, 'maximum': 100000}}, ['id']),
    'receiving.translate': ({'item': ID}, ['item']),
}
SCOPES = {'receiving.status': 'read', 'receiving.deliveries': 'read', 'receiving.cards': 'read', 'receiving.translate': 'read',
          'receiving.receive': 'approve', 'receiving.advance': 'approve'}
NAMESPACE = 'Office'
INBOX = 'Ingress'  # AGENT-01 (owner, D28); the earlier 'Arrived' (4.2) and 'Inbox' (4.1) folders are moved here once by locations.ingress
ARCHIVES = ('.zip', '.tar', '.tgz', '.tar.gz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.gz', '.bz2', '.xz')
TEXT_SUFFIXES = {'.txt', '.md', '.csv', '.tsv', '.json', '.xml', '.html', '.htm', '.ini', '.cfg', '.log', '.rtf', '.c', '.h', '.py',
                 '.js', '.ts', '.java', '.cpp', '.hpp', '.cs', '.sh', '.bat', '.yaml', '.yml', '.toml', '.tex', '.srt', '.vtt'}
MAX_DEPTH = 3
MAX_MEMBERS = 10000
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
DONE = ('Completed', 'Failed', 'Cancelled', 'Interrupted')


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS receiving_deliveries(id TEXT PRIMARY KEY,owner TEXT,created REAL,payload TEXT)')


def staging_home(kernel):
    from . import locations
    if locations.contains_program(kernel.root):
        from .session import config_dir
        return Path(config_dir()) / 'receiving'
    return kernel.state / 'receiving'


def inbox(kernel):
    """The workspace's Ingress folder (Arrived before AGENT-01, Inbox before 4.2)."""
    from . import locations
    return None if locations.contains_program(kernel.root) else locations.ingress(kernel.root)


# Revive ---------------------------------------------------------------------

def archive_kind(name):
    lower = name.lower()
    return next((suffix for suffix in sorted(ARCHIVES, key=len, reverse=True) if lower.endswith(suffix)), None)


class Budget:
    def __init__(self):self.members = 0;self.total = 0

    def take(self, size):
        self.members += 1;self.total += size
        if size > MAX_MEMBER:raise ValueError('REVIVE_MEMBER_RESOURCE_LIMIT')
        if self.members > MAX_MEMBERS or self.total > MAX_TOTAL:raise ValueError('REVIVE_DELIVERY_RESOURCE_LIMIT')


def safe_member(name):
    """An archive member's path, refused if it climbs out or is absolute."""
    parts = [p for p in name.replace('\\', '/').split('/') if p not in ('', '.')]
    if not parts or any(p == '..' for p in parts) or name.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', name):
        raise ValueError('REVIVE_UNSAFE_ARCHIVE_PATH')
    return '/'.join(parts)


JUNK = re.compile(r'(?i)^(\.ds_store|thumbs\.db|desktop\.ini|\._.*|~\$.*)$')
JUNK_FOLDERS = {'__macosx', '.git', '.svn', '.hg', '__pycache__'}
RESERVED = re.compile(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$')


def junk(name):
    parts = name.split('/')
    return any(p.casefold() in JUNK_FOLDERS for p in parts[:-1]) or bool(JUNK.match(parts[-1]))


def portable_part(part):
    part = unicodedata.normalize('NFC', part)
    part = ''.join('_' if ord(ch) < 32 or ch in '<>:"|?*\\' else ch for ch in part).rstrip(' .') or '_'
    if part.startswith('.') or RESERVED.match(part):part = '_' + part.lstrip('.')
    return part


class Names:
    """Portable, unique staging names. A case-only clash counts as a clash, as it does on Windows and macOS."""
    def __init__(self):self.used = set()

    def __call__(self, name):
        parts = [portable_part(p) for p in name.split('/')]
        candidate = '/'.join(parts);stem, dot, suffix = parts[-1].rpartition('.')
        number = 2
        while candidate.casefold() in self.used:
            leaf = (stem + ' (%d).' % number + suffix) if dot and stem else (parts[-1] + ' (%d)' % number)
            candidate = '/'.join(parts[:-1] + [leaf]);number += 1
        self.used.add(candidate.casefold())
        return candidate


def write_new(path, raw, budget):
    budget.take(len(raw))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():raise ValueError('REVIVE_PATH_COLLISION: ' + path.name)
    path.write_bytes(raw)


def members(raw, kind):
    """(name, bytes) pairs of one archive, checked before anything is written."""
    if kind == '.zip':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for member in archive.infolist():
                if member.is_dir():continue
                if stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:raise ValueError('REVIVE_ARCHIVE_LINK_OR_ENCRYPTED')
                if member.file_size > MAX_MEMBER or member.file_size > max(1, member.compress_size) * 1000:raise ValueError('REVIVE_MEMBER_RESOURCE_LIMIT')
                yield member.filename, archive.read(member)
        return
    if kind in ('.gz', '.bz2', '.xz'):
        opener = {'.gz': gzip.decompress, '.bz2': bz2.decompress, '.xz': lzma.decompress}[kind]
        data = opener(raw)
        if len(data) > MAX_MEMBER:raise ValueError('REVIVE_MEMBER_RESOURCE_LIMIT')
        yield '', data
        return
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
        for member in archive.getmembers():
            if member.isdir():continue
            if not member.isreg():raise ValueError('REVIVE_ARCHIVE_LINK_OR_DEVICE')
            if member.size > MAX_MEMBER:raise ValueError('REVIVE_MEMBER_RESOURCE_LIMIT')
            yield member.name, archive.extractfile(member).read()


def reencode(raw):
    """A UTF-8 copy of text in an older encoding, or None when it is already UTF-8 or not text."""
    if b'\x00' in raw[:4096] and not raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):return None
    try:
        raw.decode('utf-8');return None
    except UnicodeDecodeError:pass
    for encoding in (('utf-16',) if raw.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else ()) + ('cp1252', 'latin-1'):
        try:return encoding, raw.decode(encoding).encode('utf-8')
        except UnicodeDecodeError:continue
    return None


def revive_file(name, raw, target, report, budget, names, depth=0, delivered=None):
    """Copy one file into staging under a portable name; unpack it or re-encode it when it can be revived."""
    delivered = delivered or name
    if junk(delivered):
        report.append({'name': delivered, 'action': 'SKIPPED', 'reason': 'SYSTEM_FILE'});return
    name = names(name)
    renamed = {} if name == delivered else {'delivered_as': delivered}
    kind = archive_kind(name)
    if kind and depth < MAX_DEPTH:
        base = name[:-len(kind)] if name.lower().endswith(kind) else name
        try:
            # Every member name is checked before anything is written; a hostile archive is kept, never unpacked.
            unpacked = [(base + '.unpacked/' + safe_member(member) if member else base, data) for member, data in members(raw, kind)]
            if sum(len(data) for _, data in unpacked) + budget.total > MAX_TOTAL:raise ValueError('REVIVE_DELIVERY_RESOURCE_LIMIT')
        except (ValueError, OSError, EOFError, zipfile.BadZipFile, tarfile.TarError, lzma.LZMAError) as exc:
            write_new(target / name, raw, budget)
            report.append({'name': name, 'action': 'KEPT_AS_IS', 'reason': 'ARCHIVE_NOT_UNPACKED: ' + str(exc)[:160], **renamed})
            return
        write_new(target / name, raw, budget)
        report.append({'name': name, 'action': 'UNPACKED', 'members': len(unpacked), **renamed})
        for child, data in unpacked:
            revive_file(child, data, target, report, budget, names, depth + 1)
        return
    write_new(target / name, raw, budget)
    suffix = Path(name).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        converted = reencode(raw)
        if converted:
            encoding, text = converted
            write_new(target / names(name + '.utf8' + (suffix if suffix != '.txt' else '') + ('.txt' if suffix == '.txt' else '')), text, budget)
            report.append({'name': name, 'action': 'REENCODED', 'from': encoding, **renamed})
            return
    report.append({'name': name, 'action': 'COPIED', **renamed})


def revive(source, target):
    """Copy a delivery into ``target``, unpacking archives and re-encoding old text."""
    from sdk.cli.arc1cli.intake_files import read_stable, regular
    source = regular(source);target.mkdir(parents=True, mode=0o700);report = [];budget = Budget();names = Names()
    def one(path, name, maximum=MAX_MEMBER):
        if path.is_symlink():report.append({'name': name, 'action': 'SKIPPED', 'reason': 'LINK_NOT_FOLLOWED'});return
        try:raw = read_stable(path, maximum)
        except (ValueError, OSError) as exc:report.append({'name': name, 'action': 'SKIPPED', 'reason': str(exc)[:160]});return
        revive_file(name, raw, target, report, budget, names)
    if source.is_dir():
        skipped = set()
        for path in sorted(source.rglob('*')):
            relative = path.relative_to(source).as_posix();parts = relative.split('/')
            folder = next(('/'.join(parts[:i + 1]) for i, part in enumerate(parts[:-1]) if part.casefold() in JUNK_FOLDERS), None)
            if folder:
                if folder not in skipped:skipped.add(folder);report.append({'name': folder + '/', 'action': 'SKIPPED', 'reason': 'SYSTEM_FOLDER'})
                continue
            if path.is_symlink() or path.is_file():one(path, relative)
    else:
        one(source, source.name, MAX_TOTAL)
    return report


# Deliveries -----------------------------------------------------------------

def load(db, ident, owner):
    ensure(db)
    row = db.execute('SELECT payload FROM receiving_deliveries WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if not row:raise ValueError('RECEIVING_DELIVERY_NOT_FOUND')
    return json.loads(row[0])


def save(kernel, value):
    value['updated'] = time.time()
    with kernel.db() as db:
        ensure(db)
        db.execute('INSERT OR REPLACE INTO receiving_deliveries VALUES(?,?,?,?)', (value['id'], value['owner'], value['created'], json.dumps(value)))
    return value


def call(kernel, op, args, principal):
    r = kernel.dispatch(op, args, principal)
    if not r['ok']:raise ValueError(op + ': ' + r['error']['message'])
    from .project_context import refusal
    if refusal(r['result']):raise ValueError(op + ': ' + refusal(r['result']))
    return r['result']


def namespace(kernel, principal):
    found = [n for n in call(kernel, 'intake.namespaces', {}, principal)['namespaces'] if n.get('name') == NAMESPACE]
    return found[0]['id'] if found else call(kernel, 'intake.namespace.create', {'name': NAMESPACE}, principal)['id']


def job_state(kernel, ident, principal):
    return call(kernel, 'jobs.get', {'id': ident}, principal) if ident else None


def check_source(kernel, path):
    """A delivery comes from outside Ledger: never its live state, its staging or the program."""
    from . import locations
    source = Path(path).expanduser().resolve()
    if not source.exists():raise ValueError('RECEIVING_SOURCE_MISSING')
    for inside in (kernel.state, staging_home(kernel), locations.program(kernel.root)):
        inside = Path(inside).resolve()
        if inside.is_relative_to(source) or source.is_relative_to(inside):
            raise ValueError('RECEIVING_SOURCE_INSIDE_LEDGER: choose files from outside the program and its .ledger state')
    return source


def receive(kernel, args, principal):
    check_source(kernel, args['path'])
    ns = namespace(kernel, principal)
    ident = uuid.uuid4().hex;target = staging_home(kernel) / ident / 'delivery'
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    label = args.get('label') or Path(args['path']).name
    # Each delivery is its own catalog folder, so the same file name can arrive again.
    folder = portable_part(label[:60] + ' ' + ident[:6])
    try:
        target.mkdir(mode=0o700)
        report = revive(args['path'], target / folder)
    except Exception:
        shutil.rmtree(target.parent, ignore_errors=True);raise
    if not report:
        shutil.rmtree(target.parent, ignore_errors=True);raise ValueError('RECEIVING_DELIVERY_EMPTY')
    job = call(kernel, 'intake.import', {'namespace': ns, 'path': str(target), 'mode': 'snapshot', 'request_key': args.get('request_key') or ident}, principal)
    value = {'schema': 'arc.receiving-delivery/1', 'id': ident, 'owner': principal.identity, 'created': time.time(),
             'label': label, 'folder': folder, 'source': str(Path(args['path']).expanduser().absolute()),
             'staging': str(target), 'namespace': ns, 'revived': report, 'stage': 'SCANNING', 'scan_job': job['id'],
             'batch': None, 'review_job': None, 'index_job': None, 'accepted': [], 'held': [], 'rejected': [], 'revived_originals': [], 'error': None}
    return save(kernel, value)


def file_inbox(kernel, value):
    """Once Ingress is safely snapshotted, file what came in under Received/ so it is not received twice."""
    folder = inbox(kernel)
    if not folder or Path(value['source']).resolve() != folder.resolve():return
    filed = kernel.root / 'Received' / value['folder'];moved = 0
    # Only what this delivery took: a file dropped in while it was scanning waits for the next one.
    taken = {(r.get('delivered_as') or r['name']).split('/')[0] for r in value['revived']}
    for path in sorted(folder.iterdir()):
        if path.name not in taken:continue
        filed.mkdir(parents=True, mode=0o700, exist_ok=True)
        try:path.rename(filed / path.name);moved += 1
        except OSError:continue  # left in Ingress; nothing is lost
    value['filed'] = str(filed) if moved else None


def advance(kernel, args, principal):
    """Move a delivery as far as it can go now. Accepting files needs ``accept`` and a reason."""
    with kernel.db() as db:value = load(db, args['id'], principal.identity)
    if value['stage'] in ('CATALOGED', 'FAILED'):
        if not (value['stage'] == 'CATALOGED' and args.get('accept')):return value
    def failed(job, what):
        if job['state'] in ('Cancelled', 'Interrupted'):
            reason = what + ' stopped when Graphite stopped or restarted. Resume work (Master Stop → Open Work trail / Resume…), then receive this delivery again.'
        else:reason = what + ' ' + job['state'] + (': ' + job['error'] if job.get('error') else '')
        value.update(stage='FAILED', error=reason);return save(kernel, value)
    if value['stage'] == 'SCANNING':
        job = job_state(kernel, value['scan_job'], principal)
        if job['state'] not in DONE:return value
        if job['state'] != 'Completed':return failed(job, 'Scan')
        batches = call(kernel, 'intake.batches', {'namespace': value['namespace'], 'limit': 200}, principal)['batches']
        batch = next((b for b in batches if b['job'] == value['scan_job']), None)
        if batch is None:value.update(stage='FAILED', error='Scan finished without a batch');return save(kernel, value)
        file_inbox(kernel, value)
        review = call(kernel, 'intake.review', {'namespace': value['namespace'], 'batch': batch['id'], 'request_key': uuid.uuid4().hex}, principal)
        value.update(batch=batch['id'], files=batch['files'], review_job=review['id'], stage='REVIEWING');save(kernel, value)
    if value['stage'] == 'REVIEWING':
        job = job_state(kernel, value['review_job'], principal)
        if job['state'] not in DONE:return value
        if job['state'] != 'Completed':return failed(job, 'Review')
        value['stage'] = 'REVIEWED'
    items = {'items': []}
    while value['batch']:
        page = call(kernel, 'intake.items', {'namespace': value['namespace'], 'batch': value['batch'], 'limit': 200, 'offset': len(items['items'])}, principal)
        items['items'] += page['items']
        if not page['items'] or len(items['items']) >= page['total']:break
    value['accepted'] = [i['id'] for i in items['items'] if i['admission'] == 'ACCEPTED']
    # Archives that were unpacked and text that was re-encoded are kept as delivered; their revived copies carry on.
    for i in items['items']:i['name'] = local_name(value, i['name'])
    revived = {r['name'] for r in value['revived'] if r['action'] in ('UNPACKED', 'REENCODED')}
    value['revived_originals'] = [{'id': i['id'], 'name': i['name'], 'admission': i['admission']} for i in items['items'] if i['name'] in revived]
    value['held'] = [{'id': i['id'], 'name': i['name'], 'profile': i['profile'], 'reasons': i['reasons']} for i in items['items'] if i['admission'] == 'HELD' and i['name'] not in revived]
    value['rejected'] = [{'id': i['id'], 'name': i['name'], 'reasons': i['reasons']} for i in items['items'] if i['admission'] == 'REJECTED' and i['name'] not in revived]
    reviewable = [i['id'] for i in value['held'] if i['reasons'] == ['OWNER_REVIEW_REQUIRED']]
    if args.get('accept') and reviewable:
        if not args.get('reason'):raise ValueError('RECEIVING_ACCEPT_REASON_REQUIRED')
        policy = call(kernel, 'intake.policy', {'namespace': value['namespace']}, principal);accepted = set();value['accept_problem'] = None
        for start in range(0, len(reviewable), 50):
            chunk = reviewable[start:start + 50]
            generation = call(kernel, 'intake.items', {'namespace': value['namespace'], 'limit': 1}, principal)['generation']
            try:
                call(kernel, 'intake.bundle.decide', {'namespace': value['namespace'], 'items': chunk, 'expected_generation': generation,
                                                      'expected_policy_hash': policy['policy_hash'], 'reason': args['reason']}, principal)
                accepted.update(chunk)
            except ValueError as exc:
                value['accept_problem'] = str(exc)[:300]  # shown on the delivery; the files stay held
        value['accepted'] += [i for i in reviewable if i in accepted];value['held'] = [i for i in value['held'] if i['id'] not in accepted]
        if accepted:value['index_job'] = None
    if value['stage'] in ('REVIEWED', 'CATALOGED') and value['accepted'] and not value['index_job']:
        job = call(kernel, 'references.index', {'namespace': value['namespace'], 'request_key': uuid.uuid4().hex}, principal)
        value.update(index_job=job['id'], stage='INDEXING')
    if value['stage'] == 'INDEXING':
        job = job_state(kernel, value['index_job'], principal)
        if job['state'] in DONE:
            if job['state'] != 'Completed':return failed(job, 'Index')
            value['stage'] = 'CATALOGED'
    return save(kernel, value)


# staC cards -----------------------------------------------------------------

KEYWORD_STOP = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are', 'was', 'have', 'not', 'you', 'your', 'but'}


def keyword(name, text):
    import re
    for word in re.findall(r'[A-Za-z][A-Za-z0-9]{3,}', (text or '')[:2000]):
        if word.casefold() not in KEYWORD_STOP:return word.casefold()
    stem = re.sub(r'[^A-Za-z0-9]+', ' ', Path(name).stem).split()
    return (stem[0].casefold() if stem else 'document')


def local_name(delivery, name):
    """A catalog path without its delivery folder, as the owner delivered it."""
    folder = delivery.get('folder')
    return name[len(folder) + 1:] if folder and name.startswith(folder + '/') else name


def translate(kernel, item, principal, ns=None, delivery=None):
    """One received file as staC: its address, what it is, and programs that read it."""
    value = call(kernel, 'intake.read', {'id': item}, principal)
    ns = ns or call(kernel, 'intake.item', {'id': item}, principal).get('namespace')
    word = keyword(value['name'], value.get('text'))
    programs = [{'purpose': 'Show this file\'s record', 'program': '@intake:' + item + ' | select name,sha256,working_version'},
                {'purpose': 'Read this file\'s text', 'program': '@intake:' + item + ' | select text'}]
    if ns:programs.append({'purpose': 'Find related passages in the Office catalog', 'program': 'library ' + ns + ' | search ' + word + ' | take 5'})
    checked = []
    for row in programs:
        operation = 'stac.compile' if row['program'].startswith('library ') else 'language.parse'
        argument = {'program': row['program']} if operation == 'stac.compile' else {'text': row['program']}
        r = kernel.dispatch(operation, argument, principal)
        checked.append({**row, 'run_with': 'stac.run' if operation == 'stac.compile' else 'language.run',
                        'valid': r['ok'], **({} if r['ok'] else {'error': r['error']['message']})})
    text = value.get('text') or ''
    return {'schema': 'arc.stac-card/1', 'address': 'intake:' + item, 'name': local_name(delivery or {}, value['name']), 'catalog_path': value['name'], 'sha256': value['sha256'],
            'profile': (value.get('qualification') or {}).get('structural_check'), 'summary': ' '.join(text.split())[:240],
            'characters': len(text), 'programs': checked, 'authority': 'READ_ONLY_EXISTING_KERNEL_CALLS'}


def dispatch(kernel, op, args, principal):
    if op == 'receiving.status':
        with kernel.db() as db:
            ensure(db)
            stages = dict(db.execute("SELECT json_extract(payload,'$.stage'),COUNT(*) FROM receiving_deliveries WHERE owner=? GROUP BY 1", (principal.identity,)).fetchall())
        folder = inbox(kernel)
        waiting = sorted(p.name for p in folder.iterdir())[:200] if folder and folder.is_dir() else []
        return {'schema': 'arc.receiving/1', 'inbox': str(folder) if folder else None, 'inbox_waiting': waiting, 'stages': stages,
                'namespace_name': NAMESPACE, 'flow': ['REVIVING', 'SCANNING', 'REVIEWING', 'REVIEWED', 'INDEXING', 'CATALOGED'],
                'originals': 'UNCHANGED; snapshots live in private quarantine'}
    if op == 'receiving.deliveries':
        with kernel.db() as db:
            ensure(db)
            found = db.execute('SELECT payload FROM receiving_deliveries WHERE owner=? ORDER BY created DESC LIMIT ?', (principal.identity, args.get('limit', 30))).fetchall()
        return {'deliveries': [json.loads(r[0]) for r in found]}
    if op == 'receiving.receive':return receive(kernel, args, principal)
    if op == 'receiving.advance':return advance(kernel, args, principal)
    if op == 'receiving.cards':
        with kernel.db() as db:value = load(db, args['id'], principal.identity)
        start = args.get('offset', 0)
        return {'delivery': value['id'], 'stage': value['stage'], 'total': len(value['accepted']), 'offset': start,
                'cards': [translate(kernel, i, principal, value['namespace'], value) for i in value['accepted'][start:start + 200]]}
    if op == 'receiving.translate':return translate(kernel, args['item'], principal)
    raise ValueError('RECEIVING_OPERATION_UNKNOWN')
