"""Pills: self-describing, signed units of work between two computers (arc.pill/1). See docs/PILLS.md.

A pill carries files, context and an exact statement of what its recipient is asked to do. It never carries
authority: the receiving computer checks it, keeps it in quarantine, and its own policy decides what may happen.

This module is shared by Ledger and by the small workstation handler (pillkit.handler), so it needs only Python's
standard library plus `cryptography` for Ed25519 signatures. It reads pills as data: nothing in a pill is ever run,
extracted to an arbitrary place, or followed (no links, no folders, no absolute or parent paths).

What a signature proves: which paired computer made the pill and that not one byte has changed since. What it does not
prove: that the contents are harmless. Files inside are source material, never instructions.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import stat
import time
import uuid
import zipfile
from pathlib import Path

SCHEMA, MANIFEST, SIGNATURE, IDENTITY = 'arc.pill/1', 'arc.pill-members/1', 'arc.pill-signature/1', 'arc.pill-identity/1'
KINDS = ('request', 'result')
WORK = ('inspect', 'analyze', 'propose_revisions', 'test')          # what a request may ask for, and nothing else
EXPECT = ('findings', 'candidate_files', 'evidence', 'stac')
CHANGE_OPS = ('create', 'replace', 'delete')
MAX_PILL = 256 * 1024 * 1024          # the whole pill, as it travels
MAX_MEMBERS = 600                     # files inside it
MAX_FILE = 64 * 1024 * 1024           # one file inside it
MAX_JSON = 1024 * 1024                # its contract, manifest and signature
MAX_RATIO = 200                       # how much one member may expand: refuses zip bombs
RESERVED = {'con', 'prn', 'aux', 'nul', *('com%d' % i for i in range(10)), *('lpt%d' % i for i in range(10))}
PART = re.compile(r'[^\x00-\x1f\x7f/\\:*?"<>|]{1,200}')
ID = re.compile(r'[0-9a-f]{32}')
SHA = re.compile(r'[0-9a-f]{64}')
FIXED_TIME = (1980, 1, 1, 0, 0, 0)    # every pill member gets the same date: the same work makes the same bytes


class PillError(ValueError):
    """A pill that is refused. The message starts with a code, then says why in words."""


def refuse(code, words):
    raise PillError('%s: %s' % (code, words))


# -- canonical data ------------------------------------------------------------------------------------------------

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def strict_json(raw, what):
    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):refuse('PILL_JSON', '%s repeats a field' % what)
        return dict(items)
    def constant(name):refuse('PILL_JSON', '%s holds %s' % (what, name))
    try:return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):refuse('PILL_JSON', '%s is not plain JSON' % what)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_rel(text):
    """A file's place inside a pill, the same on Linux, Windows and macOS: forward slashes, no hidden parts, no '..',
    nothing absolute, no reserved device names. Anything else is refused, never cleaned up into something else."""
    if not isinstance(text, str) or not 0 < len(text) <= 1000 or text != text.strip():refuse('PILL_PATH', 'a file has no usable name')
    parts = text.split('/')
    if len(parts) > 32:refuse('PILL_PATH', 'a file is nested too deeply: %s' % text[:120])
    for part in parts:
        if not PART.fullmatch(part) or part in ('.', '..') or part.startswith('.') or part.endswith((' ', '.')):
            refuse('PILL_PATH', 'not an ordinary file name: %s' % text[:120])
        if part.split('.')[0].lower() in RESERVED:refuse('PILL_PATH', 'a reserved device name: %s' % text[:120])
    return text


# -- identities and keys -------------------------------------------------------------------------------------------

def crypto():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        refuse('PILL_NEEDS_CRYPTOGRAPHY', 'signing and checking pills needs the Python "cryptography" package (Debian: python3-cryptography)')
    return Ed25519PrivateKey, Ed25519PublicKey, serialization, InvalidSignature


def fingerprint(public_hex):
    """A key's short name: the first 32 hex digits of the SHA-256 of its 32 public bytes."""
    if not isinstance(public_hex, str) or not re.fullmatch(r'[0-9a-f]{64}', public_hex):refuse('PILL_KEY', 'not an Ed25519 public key (64 hex digits)')
    return sha256(bytes.fromhex(public_hex))[:32]


def pairing_code(public_a, public_b):
    """The code both computers show while pairing. If the two screens show the same code, each has the other's real key."""
    joined = ''.join(sorted((public_a, public_b))).encode()
    digest = sha256(joined)[:12].upper()
    return '-'.join(digest[i:i + 4] for i in (0, 4, 8))


def write_private(path, data):
    path = Path(path);path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())


def write_state(path, value):
    """Replace a small state file whole: written beside it, flushed, then renamed over it."""
    path = Path(path);path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.part')
    with open(temporary, 'wb') as f:f.write(json.dumps(value, indent=1, sort_keys=True).encode());f.flush();os.fsync(f.fileno())
    os.chmod(temporary, 0o600);os.replace(temporary, path)


def read_state(path, default):
    try:return json.loads(Path(path).read_text())
    except FileNotFoundError:return default


class Keyring:
    """One computer's pill identity: its private key (never leaves the folder), its paired peers, what it has seen.

    folder/identity.key   the private key, 32 bytes, readable by you only
    folder/identity.json  this computer's name and public key
    folder/peers.json     paired computers: fingerprint -> name and public key
    folder/state.sqlite3 persistent send counter and replay exclusions, never pruned
    folder/seen.json and sent.json are imported once for compatibility
    """

    def __init__(self, folder, name=None):
        self.folder = Path(folder).expanduser().absolute()
        if any(p.is_symlink() for p in (self.folder,*self.folder.parents)):refuse('PILL_KEY_PATH','linked identity directories are refused')
        self.folder.mkdir(parents=True, mode=0o700, exist_ok=True)
        try:os.chmod(self.folder, 0o700)
        except OSError:pass
        key_path = self.folder / 'identity.key'
        Ed25519PrivateKey, _, serialization, _ = crypto()
        from .state import lock
        with lock(self.folder):
            if not key_path.exists():
                key = Ed25519PrivateKey.generate()
                write_private(key_path, key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
                public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
                write_state(self.folder / 'identity.json', {'schema': IDENTITY, 'name': (name or 'This computer')[:80], 'public': public})
            if key_path.is_symlink() or not key_path.is_file() or key_path.stat().st_nlink!=1:refuse('PILL_KEY_PATH','use an ordinary private identity file')
            if stat.S_IMODE(os.stat(key_path).st_mode) & 0o077:refuse('PILL_KEY_EXPOSED', 'the private key can be read by others; it should be readable by you only (chmod 600)')
            self._key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
            info = read_state(self.folder / 'identity.json', {})
            public=self._key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
            if info.get('schema')!=IDENTITY or info.get('public')!=public:refuse('PILL_KEY_IDENTITY','public identity differs from its private key; inspect recovery')
            if name and info.get('name') != name[:80]:info['name'] = name[:80];write_state(self.folder / 'identity.json', info)
        self.name, self.public = info['name'], info['public'];self.key = fingerprint(self.public)

    def card(self):
        """What this computer gives another to be paired: its name and public key. Nothing secret."""
        return {'schema': IDENTITY, 'name': self.name, 'public': self.public, 'key': self.key}

    def peers(self):
        return read_state(self.folder / 'peers.json', {})

    def pair(self, card):
        from .state import lock
        with lock(self.folder,'peers'):return self._pair(card)

    def _pair(self, card):
        if not isinstance(card, dict) or card.get('schema') != IDENTITY:refuse('PILL_CARD', 'not a pill identity card')
        name = str(card.get('name') or 'Computer')[:80];public = card.get('public');key = fingerprint(public)
        if key == self.key:refuse('PILL_CARD', 'this is this computer\'s own card')
        peers = self.peers();peers[key] = {'name': name, 'public': public, 'paired': time.time()};write_state(self.folder / 'peers.json', peers)
        return {'key': key, 'name': name, 'code': pairing_code(self.public, public)}

    def unpair(self, key):
        from .state import lock
        # Keep the same lock order as TLS pairing. Re-pairing a legacy public
        # pill card must not silently reactivate an earlier TLS certificate.
        with lock(self.folder,'tls-peers'),lock(self.folder,'peers'):return self._unpair(key)

    def _unpair(self, key):
        peers = self.peers()
        if peers.pop(key, None) is None:refuse('PILL_PEER', 'no paired computer has that key')
        write_state(self.folder / 'peers.json', peers)
        tls=read_state(self.folder/'tls-peers.json',{});tls.pop(key,None);write_state(self.folder/'tls-peers.json',tls)

    def peer(self, key_or_name):
        peers = self.peers()
        if key_or_name in peers:return key_or_name, peers[key_or_name]
        found = [(k, v) for k, v in peers.items() if v['name'] == key_or_name]
        if len(found) != 1:refuse('PILL_PEER', 'no single paired computer called %r' % key_or_name)
        return found[0]

    def next_sequence(self):
        from .state import database
        with database(self.folder) as db:
            value=db.execute('SELECT value FROM counter WHERE id=1').fetchone()[0]+1
            if value>=2**53:refuse('PILL_SEQUENCE_EXHAUSTED','rotate this signing identity')
            db.execute('UPDATE counter SET value=? WHERE id=1',(value,))
            return value

    def sign(self, data):
        return self._key.sign(data).hex()

    def seen(self, sender, pill_id, sequence):
        """Refuse a pill already accepted: by its id, and by its sender's sequence number (each number is used once, so a
        copy re-signed under a fresh id is still caught). Out of order is fine: two results may be applied either way."""
        from .state import database
        with database(self.folder) as db:
            if db.execute('SELECT 1 FROM seen WHERE sender=? AND (id=? OR sequence=?)',(sender,pill_id,sequence)).fetchone():
                refuse('PILL_REPLAY','this pill id or sequence was already accepted here')

    def remember(self, sender, pill_id, sequence):
        from .state import database
        import sqlite3
        try:
            with database(self.folder) as db:db.execute('INSERT INTO seen VALUES(?,?,?)',(sender,pill_id,sequence))
        except sqlite3.IntegrityError:refuse('PILL_REPLAY','this pill id or sequence was already accepted here')


# -- the contract --------------------------------------------------------------------------------------------------

def file_list(files):
    if not isinstance(files, dict) or len(files) > MAX_MEMBERS:refuse('PILL_CONTRACT', 'the file list is missing or too long')
    folded = set()
    for rel, entry in files.items():
        safe_rel(rel)
        if rel.lower() in folded:refuse('PILL_PATH', 'two files differ only in capitals: %s' % rel[:120])
        folded.add(rel.lower())
        if not isinstance(entry, dict) or set(entry) != {'sha256', 'bytes'} or not SHA.fullmatch(str(entry['sha256'])) \
                or not isinstance(entry['bytes'], int) or not 0 <= entry['bytes'] <= MAX_FILE:refuse('PILL_CONTRACT', 'a file entry is not {sha256, bytes}: %s' % rel[:120])
    return files


def check_contract(c):
    """Every field of pill.json, exactly. Unknown fields are refused, so a pill cannot smuggle in new meanings."""
    keys = {'schema', 'id', 'kind', 'sender', 'recipient', 'sequence', 'created', 'in_reply_to', 'task', 'source', 'requested', 'limits', 'expected', 'result'}
    if not isinstance(c, dict) or set(c) != keys:refuse('PILL_CONTRACT', 'pill.json does not have exactly the fields of %s' % SCHEMA)
    if c['schema'] != SCHEMA:refuse('PILL_VERSION', 'not an %s pill' % SCHEMA)
    if not ID.fullmatch(str(c['id'])):refuse('PILL_CONTRACT', 'the pill id is not 32 hex digits')
    if c['kind'] not in KINDS:refuse('PILL_CONTRACT', 'a pill is a request or a result')
    for who in ('sender', 'recipient'):
        v = c[who]
        if not isinstance(v, dict) or set(v) != {'name', 'key'} or not ID.fullmatch(str(v['key'])) or not isinstance(v['name'], str) or len(v['name']) > 80:
            refuse('PILL_CONTRACT', 'the %s is not {name, key}' % who)
    if not isinstance(c['sequence'], int) or not 0 < c['sequence'] < 2 ** 53:refuse('PILL_CONTRACT', 'the sequence number is not a positive whole number')
    if not isinstance(c['created'], str) or len(c['created']) > 40:refuse('PILL_CONTRACT', 'the creation time is not a short text')
    task = c['task']
    if not isinstance(task, dict) or set(task) != {'id', 'title', 'purpose'} or not ID.fullmatch(str(task['id'])) \
            or not isinstance(task['title'], str) or not 0 < len(task['title']) <= 200 or not isinstance(task['purpose'], str) or len(task['purpose']) > 4000:
        refuse('PILL_CONTRACT', 'the task is not {id, title, purpose}')
    src = c['source']
    if not isinstance(src, dict) or set(src) != {'label', 'revision', 'files'} or not isinstance(src['label'], str) or len(src['label']) > 200 \
            or not SHA.fullmatch(str(src['revision'])):refuse('PILL_CONTRACT', 'the source is not {label, revision, files}')
    file_list(src['files'])
    if src['revision'] != revision(src['files']):refuse('PILL_CONTRACT', 'the source revision does not match its own file list')
    limits = c['limits']
    if limits != {'changes_to_originals': False}:refuse('PILL_LIMITS', 'a pill may never ask to change originals directly')
    if c['kind'] == 'request':
        if c['in_reply_to'] is not None or c['result'] is not None:refuse('PILL_CONTRACT', 'a request answers nothing and carries no result')
        if not isinstance(c['requested'], list) or not c['requested'] or any(w not in WORK for w in c['requested']) or len(set(c['requested'])) != len(c['requested']):
            refuse('PILL_REQUEST', 'a request may ask only for: ' + ', '.join(WORK))
        if not isinstance(c['expected'], list) or any(w not in EXPECT for w in c['expected']):refuse('PILL_REQUEST', 'a request may expect only: ' + ', '.join(EXPECT))
    else:
        if not ID.fullmatch(str(c['in_reply_to'])):refuse('PILL_CONTRACT', 'a result names the request it answers')
        if c['requested'] != [] or c['expected'] != []:refuse('PILL_CONTRACT', 'a result asks for nothing')
        r = c['result']
        if not isinstance(r, dict) or set(r) != {'findings', 'changes', 'evidence'} or not isinstance(r['findings'], str) or len(r['findings']) > 200000:
            refuse('PILL_CONTRACT', 'the result is not {findings, changes, evidence}')
        if not isinstance(r['changes'], list) or len(r['changes']) > MAX_MEMBERS:refuse('PILL_CONTRACT', 'the list of changes is missing or too long')
        paths = set()
        for ch in r['changes']:
            if not isinstance(ch, dict) or set(ch) != {'op', 'path', 'before', 'after'} or ch['op'] not in CHANGE_OPS:refuse('PILL_CONTRACT', 'a change is not {op, path, before, after}')
            safe_rel(ch['path'])
            if ch['path'].lower() in paths:refuse('PILL_CONTRACT', 'a file is changed twice: %s' % ch['path'][:120])
            paths.add(ch['path'].lower())
            want_before, want_after = ch['op'] != 'create', ch['op'] != 'delete'
            if bool(SHA.fullmatch(str(ch['before']))) != want_before or (not want_before and ch['before'] != ''):refuse('PILL_CONTRACT', 'a change has the wrong "before": %s' % ch['path'][:120])
            if bool(SHA.fullmatch(str(ch['after']))) != want_after or (not want_after and ch['after'] != ''):refuse('PILL_CONTRACT', 'a change has the wrong "after": %s' % ch['path'][:120])
            base = src['files'].get(ch['path'])
            if ch['op'] == 'create' and base is not None:refuse('PILL_CONTRACT', 'creates a file the source already has: %s' % ch['path'][:120])
            if ch['op'] != 'create' and (base is None or base['sha256'] != ch['before']):refuse('PILL_CONTRACT', 'changes a file that is not in the source as sent: %s' % ch['path'][:120])
        if not isinstance(r['evidence'], list) or len(r['evidence']) > 100:refuse('PILL_CONTRACT', 'the evidence list is too long')
        for n in r['evidence']:note_name(n)
    return c


def revision(files):
    """A revision's identity: the hash of its file list. The same files make the same revision on any computer."""
    return sha256(canonical({rel: entry['sha256'] for rel, entry in files.items()}))


def note_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,79}\.(md|txt|json|csv)', name) or '..' in name:
        refuse('PILL_PATH', 'a note has an unusual name: %s' % str(name)[:80])
    return name


def member_name(name):
    if name in ('pill.json', 'manifest.json', 'signature.json'):return name
    if name.startswith('files/'):safe_rel(name[6:]);return name
    if name.startswith('notes/'):note_name(name[6:]);return name
    refuse('PILL_MEMBER', 'an unexpected member: %s' % name[:120])


# -- making a pill -------------------------------------------------------------------------------------------------

def now_text():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def contract(keyring, recipient_key, kind, task, source_label, source_files, requested=(), expected=(), in_reply_to=None, result=None):
    _, peer = keyring.peer(recipient_key)
    return {'schema': SCHEMA, 'id': uuid.uuid4().hex, 'kind': kind,
            'sender': {'name': keyring.name, 'key': keyring.key}, 'recipient': {'name': peer['name'], 'key': fingerprint(peer['public'])},
            'sequence': keyring.next_sequence(), 'created': now_text(), 'in_reply_to': in_reply_to, 'task': task,
            'source': {'label': source_label[:200], 'revision': revision(source_files), 'files': source_files},
            'requested': list(requested), 'limits': {'changes_to_originals': False}, 'expected': list(expected), 'result': result}


def build(keyring, c, files, notes=None):
    """The pill's bytes: pill.json, files/…, notes/…, a manifest of every member's hash, and the signature over it."""
    check_contract(c)
    members = {'pill.json': canonical(c)}
    for rel, data in sorted(files.items()):members['files/' + safe_rel(rel)] = data
    for name, data in sorted((notes or {}).items()):members['notes/' + note_name(name)] = data
    manifest = canonical({'schema': MANIFEST, 'members': {n: {'sha256': sha256(d), 'bytes': len(d)} for n, d in members.items()}})
    signature = canonical({'schema': SIGNATURE, 'algorithm': 'ed25519', 'signer': keyring.key, 'manifest_sha256': sha256(manifest),
                           'signature': keyring.sign(manifest)})
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in [('pill.json', members.pop('pill.json')), ('manifest.json', manifest), ('signature.json', signature)] + sorted(members.items()):
            info = zipfile.ZipInfo(name, FIXED_TIME);info.external_attr = (stat.S_IFREG | 0o600) << 16;info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    raw = out.getvalue()
    if len(raw) > MAX_PILL:refuse('PILL_TOO_LARGE', 'the pill would be larger than %d MB' % (MAX_PILL // 2 ** 20))
    return raw


# -- opening a pill ------------------------------------------------------------------------------------------------

class Pill:
    def __init__(self, contract, files, notes, signer):
        self.contract, self.files, self.notes, self.signer = contract, files, notes, signer
        self.id, self.kind = contract['id'], contract['kind']

    def summary(self):
        c = self.contract;r = c['result'] or {}
        return {'id': c['id'], 'kind': c['kind'], 'from': c['sender']['name'], 'from_key': c['sender']['key'], 'to': c['recipient']['name'],
                'sequence': c['sequence'], 'created': c['created'], 'task': c['task'], 'source': c['source']['label'],
                'revision': c['source']['revision'], 'files': len(c['source']['files']), 'requested': c['requested'],
                'expected': c['expected'], 'in_reply_to': c['in_reply_to'], 'changes': len(r.get('changes', [])),
                'notes': sorted(self.notes)}


def read_members(raw):
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > MAX_PILL:refuse('PILL_TOO_LARGE', 'larger than %d MB' % (MAX_PILL // 2 ** 20))
    try:
        with zipfile.ZipFile(io.BytesIO(bytes(raw))) as z:
            rows = z.infolist()
            if not 3 <= len(rows) <= MAX_MEMBERS + 3:refuse('PILL_MEMBERS', 'too few or too many members')
            names = [r.filename for r in rows]
            if len(set(names)) != len(names) or len({n.lower() for n in names}) != len(names):refuse('PILL_MEMBERS', 'a member name repeats')
            if sum(r.file_size for r in rows) > MAX_PILL:refuse('PILL_TOO_LARGE', 'it would expand past %d MB' % (MAX_PILL // 2 ** 20))
            members = {}
            for r in rows:
                member_name(r.filename);mode = r.external_attr >> 16
                if r.is_dir() or r.flag_bits & 1 or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG):refuse('PILL_MEMBER', 'not an ordinary file: %s' % r.filename[:120])
                if r.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):refuse('PILL_MEMBER', 'an unusual compression: %s' % r.filename[:120])
                limit = MAX_JSON if r.filename in ('pill.json', 'manifest.json', 'signature.json') else MAX_FILE
                if r.file_size > limit:refuse('PILL_TOO_LARGE', 'a member is too large: %s' % r.filename[:120])
                if r.file_size > 4096 and r.file_size > max(1, r.compress_size) * MAX_RATIO:refuse('PILL_EXPANSION', 'a member expands too much: %s' % r.filename[:120])
                with z.open(r) as stream:data = stream.read(r.file_size + 1)
                if len(data) != r.file_size:refuse('PILL_MEMBER', 'a member is not the size it says: %s' % r.filename[:120])
                members[r.filename] = data
            return members
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, EOFError, OSError) as exc:
        refuse('PILL_DAMAGED', 'not a readable pill (%s)' % type(exc).__name__)


def open_pill(raw, keyring, expect_kind=None, replay=True):
    """Check everything, in an order that trusts nothing early: size and shape, then the signature of a paired computer,
    then every member's hash, then the contract, then that it is meant for this computer and is not a replay.
    Returns a Pill held in memory; nothing is written anywhere. Call keyring.remember(...) once it is accepted."""
    _, Ed25519PublicKey, _, InvalidSignature = crypto()
    members = read_members(raw)
    for name in ('pill.json', 'manifest.json', 'signature.json'):
        if name not in members:refuse('PILL_MEMBERS', '%s is missing' % name)
    sig = strict_json(members.pop('signature.json'), 'signature.json')
    if not isinstance(sig, dict) or set(sig) != {'schema', 'algorithm', 'signer', 'manifest_sha256', 'signature'} or sig['schema'] != SIGNATURE or sig['algorithm'] != 'ed25519':
        refuse('PILL_SIGNATURE', 'signature.json is not an Ed25519 pill signature')
    peers = keyring.peers();peer = peers.get(sig['signer'])
    if peer is None:refuse('PILL_UNKNOWN_SENDER', 'signed by a computer this one is not paired with (%s)' % str(sig['signer'])[:32])
    manifest_raw = members.pop('manifest.json')
    if sha256(manifest_raw) != sig['manifest_sha256']:refuse('PILL_SIGNATURE', 'the manifest is not the one that was signed')
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(peer['public'])).verify(bytes.fromhex(str(sig['signature'])), manifest_raw)
    except (InvalidSignature, ValueError):refuse('PILL_SIGNATURE', 'the signature does not match: changed after signing, or not from %s' % peer['name'])
    manifest = strict_json(manifest_raw, 'manifest.json')
    if not isinstance(manifest, dict) or set(manifest) != {'schema', 'members'} or manifest['schema'] != MANIFEST or not isinstance(manifest['members'], dict):
        refuse('PILL_MANIFEST', 'manifest.json is not a pill manifest')
    if set(manifest['members']) != set(members):refuse('PILL_MANIFEST', 'the manifest and the members differ')
    for name, data in members.items():
        if manifest['members'][name] != {'sha256': sha256(data), 'bytes': len(data)}:refuse('PILL_MANIFEST', 'a member does not match its hash: %s' % name[:120])
    c = check_contract(strict_json(members.pop('pill.json'), 'pill.json'))
    if c['sender']['key'] != sig['signer']:refuse('PILL_SENDER', 'the contract names a different sender than the signature')
    if c['recipient']['key'] != keyring.key:refuse('PILL_NOT_FOR_US', 'this pill is for %s, not this computer' % c['recipient']['name'])
    if expect_kind and c['kind'] != expect_kind:refuse('PILL_KIND', 'expected a %s pill, this is a %s' % (expect_kind, c['kind']))
    if replay:keyring.seen(c['sender']['key'], c['id'], c['sequence'])  # off only to re-read a pill already acted on
    files = {n[6:]: d for n, d in members.items() if n.startswith('files/')}
    notes = {n[6:]: d for n, d in members.items() if n.startswith('notes/')}
    if c['kind'] == 'request':
        if set(files) != set(c['source']['files']):refuse('PILL_FILES', 'the files carried are not the files listed')
        for rel, entry in c['source']['files'].items():
            if {'sha256': sha256(files[rel]), 'bytes': len(files[rel])} != entry:refuse('PILL_FILES', 'a file does not match the source revision: %s' % rel[:120])
    else:
        wanted = {ch['path']: ch['after'] for ch in c['result']['changes'] if ch['op'] != 'delete'}
        if set(files) != set(wanted):refuse('PILL_FILES', 'the files carried are not the changed files listed')
        for rel, after in wanted.items():
            if sha256(files[rel]) != after:refuse('PILL_FILES', 'a changed file does not match its hash: %s' % rel[:120])
        if set(c['result']['evidence']) - set(notes):refuse('PILL_FILES', 'evidence names a note the pill does not carry')
    return Pill(c, files, notes, peer)


def scan_folder(root, max_files=500, max_total=256 * 1024 * 1024):
    """A folder's ordinary files for a pill: no links, nothing hidden, every name pill-safe. ({rel: Path}, skipped)."""
    root = Path(root);found, skipped, total = {}, [], 0
    if root.is_file():
        safe_rel(root.name);return {root.name: root}, []
    for folder, dirs, names in os.walk(root, followlinks=False):
        here = Path(folder);keep = []
        for d in sorted(dirs):
            if d.startswith('.') or (here / d).is_symlink() or d in ('__pycache__', 'node_modules'):skipped.append(((here / d).relative_to(root).as_posix() + '/', 'hidden, a link or a machine folder'))
            else:keep.append(d)
        dirs[:] = keep
        for name in sorted(names):
            p = here / name;rel = p.relative_to(root).as_posix();info = os.lstat(p)
            if name.startswith('.') or not stat.S_ISREG(info.st_mode):skipped.append((rel, 'hidden, a link or not an ordinary file'));continue
            try:safe_rel(rel)
            except PillError:skipped.append((rel, 'a name other computers cannot hold'));continue
            found[rel] = p;total += info.st_size
            if len(found) > max_files or total > max_total:refuse('PILL_TOO_LARGE', 'up to %d files and %d MB in one pill for now' % (max_files, max_total // 2 ** 20))
    return found, skipped
