"""Portable ARC founding record, RFC 3161 evidence and local Concern register.

Standard library only. OpenSSL is invoked with fixed argument lists for timestamp
verification. Register entries are local declarations, never identity proofs or
Ledger permission grants. No operation edits the original founding documents.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
import zipfile

RECORD_ID = 'ARC-GENESIS-0001'
CANONICAL_SHA256 = '8baef4e1a17db877c8eec16c1b36617e42f6473378a154d3e87000484ae6fea4'
CANONICAL = 'originals/complete/ARC_GENESIS_0001_Canonical.txt'
GENESIS_UTC = '2026-10-25T08:52:34Z'
FOUNDER = 'R. A. Peddycoart'
MAX_FILE = 32 * 1024 * 1024
MAX_RESPONSE = 256 * 1024
TRUST = {
    'freetsa': {
        'name': 'FreeTSA', 'endpoint': 'https://freetsa.org/tsr',
        'root_sha256': '2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438',
        'chain_sha256': '8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467',
        'trust_scope': 'Pinned FreeTSA service CA; no operating-system trust installation',
    },
}


class GenesisError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise GenesisError('Duplicate JSON field')
            result[key] = value
        return result
    def invalid(_):
        raise GenesisError('Non-finite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def instant(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError) as exc:
        raise GenesisError('Use an ISO date/time with an explicit timezone') from exc
    if result.tzinfo is None:
        raise GenesisError('A timezone is required')
    return result.astimezone(timezone.utc)


def text(value, label, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\0' in value:
        raise GenesisError(label + ' is missing or too long')
    return value.strip()


def inside(base, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\0' in name:
        raise GenesisError('Invalid record path')
    pure = PurePosixPath(name)
    if pure.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise GenesisError('Invalid record path')
    base = Path(base).absolute()
    if base.is_symlink():
        raise GenesisError('Symbolic links are not record storage')
    target = base
    for part in pure.parts:
        target = target / part
        if target.is_symlink():
            raise GenesisError('Symbolic links are not record files')
    if not target.resolve().is_relative_to(base.resolve()):
        raise GenesisError('Record path escapes its root')
    return target


def read_bytes(path, limit=MAX_FILE):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise GenesisError('Record file is missing, linked or exceeds its size limit')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise GenesisError('Record file exceeds its size limit')
    return raw


def atomic(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise GenesisError('Refusing a linked destination')
    fd, temporary = tempfile.mkstemp(prefix='.arc-genesis-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GenesisError('Timestamp endpoint redirected; review its published address')


class GenesisStore:
    def __init__(self, root, state_dir=None):
        self.root = Path(root).absolute()
        self.bundle = inside(self.root, 'concern/genesis')
        self.state = Path(state_dir).absolute() if state_dir is not None else inside(self.root, '.ledger/concern')
        if self.state.is_symlink():
            raise GenesisError('Concern state cannot be a symbolic link')

    def manifest(self):
        data = strict_json(read_bytes(inside(self.bundle, 'record.json'), 2 * 1024 * 1024))
        if data.get('schema') != 'arc.genesis-record/1' or data.get('record_id') != RECORD_ID:
            raise GenesisError('Unknown Genesis record')
        if data.get('canonical_sha256') != CANONICAL_SHA256 or data.get('canonical_path') != CANONICAL:
            raise GenesisError('The founding record does not match its fixed authority')
        if not isinstance(data.get('files'), dict) or not 1 <= len(data['files']) <= 100:
            raise GenesisError('Invalid Genesis file inventory')
        return data

    def integrity(self):
        manifest = self.manifest()
        rows = []
        for name, expected in sorted(manifest['files'].items()):
            try:
                raw = read_bytes(inside(self.bundle, name))
                found = digest(raw)
                ok = found == expected['sha256'] and len(raw) == expected['bytes']
                rows.append(dict(path=name, ok=ok, sha256=found, expected=expected['sha256'], bytes=len(raw)))
            except (OSError, ValueError, KeyError) as exc:
                rows.append(dict(path=name, ok=False, error=str(exc)))
        charter = read_bytes(inside(self.bundle, CANONICAL))
        canonical_ok = digest(charter) == CANONICAL_SHA256
        return dict(ok=canonical_ok and all(r['ok'] for r in rows), canonical_ok=canonical_ok,
                    canonical_sha256=digest(charter), files=rows)

    def require_integrity(self):
        report = self.integrity()
        if not report['ok']:
            raise GenesisError('Founding evidence changed or is incomplete; inspect the failed checks')
        return report

    def charter(self):
        raw = read_bytes(inside(self.bundle, CANONICAL))
        if digest(raw) != CANONICAL_SHA256:
            raise GenesisError('The canonical charter fingerprint does not match')
        return raw.decode('utf-8')

    def public_file(self, name):
        manifest = self.manifest()
        if name not in manifest['files']:
            raise GenesisError('File is not in the founding evidence inventory')
        path = inside(self.bundle, name)
        raw = read_bytes(path)
        if digest(raw) != manifest['files'][name]['sha256']:
            raise GenesisError('Founding evidence fingerprint mismatch')
        return path

    def _openssl(self, arguments):
        program = shutil.which('openssl')
        if not program:
            raise GenesisError('OpenSSL is required for timestamp verification; integrity checks remain available')
        env = dict(os.environ, LC_ALL='C')
        try:
            p = subprocess.run([program, *arguments], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               timeout=20, env=env)
        except subprocess.TimeoutExpired as exc:
            raise GenesisError('OpenSSL exceeded its verification time limit') from exc
        output = (p.stdout + '\n' + p.stderr).strip()
        if p.returncode:
            # Temporary filesystem paths and certificate email addresses do not belong in UI reports.
            summary = '\n'.join(line for line in output.splitlines()
                                if not line.startswith(('Using configuration', 'Warning:')))[:1200]
            raise GenesisError('Timestamp verification failed: ' + summary)
        return p.stdout.strip()

    def _query(self, query, target):
        output = self._openssl(['ts', '-query', '-in', str(query), '-text'])
        if not re.search(r'^Hash Algorithm: sha256\s*$', output, re.M) or not re.search(r'^Nonce: 0x[0-9A-Fa-f]+\s*$', output, re.M):
            raise GenesisError('A SHA-256 request with a nonce is required')
        lines = output.split('Message data:', 1)[-1].split('Policy OID:', 1)[0].splitlines()
        hexadecimal = ''
        for line in lines:
            if re.match(r'\s*[0-9a-fA-F]{4} - ', line):
                part = re.split(r'\s{2,}', line.split(' - ', 1)[1], maxsplit=1)[0]
                hexadecimal += ''.join(re.findall(r'[0-9a-fA-F]{2}', part))
        if hexadecimal.lower() != digest(read_bytes(target)):
            raise GenesisError('Timestamp request is bound to different document bytes')
        return output

    def _verify_timestamp(self, response, request, provider, target):
        if provider not in TRUST:
            raise GenesisError('Unknown timestamp trust policy')
        trust = TRUST[provider]
        folder = inside(self.bundle, 'timestamps/' + provider)
        root = inside(folder, 'root.crt')
        chain = inside(folder, 'chain.crt')
        if digest(read_bytes(root)) != trust['root_sha256'] or digest(read_bytes(chain)) != trust['chain_sha256']:
            raise GenesisError('Pinned timestamp certificate changed; independent trust review is required')
        read_bytes(response, MAX_RESPONSE)
        read_bytes(request, 8192)
        self._query(request, target)
        common = ['ts', '-verify', '-in', str(response), '-CAfile', str(root), '-untrusted', str(chain)]
        by_request = self._openssl([*common, '-queryfile', str(request)])
        by_data = self._openssl([*common, '-data', str(target)])
        if 'Verification: OK' not in by_request or 'Verification: OK' not in by_data:
            raise GenesisError('OpenSSL did not confirm both timestamp bindings')
        reply = self._openssl(['ts', '-reply', '-in', str(response), '-text'])
        match = re.search(r'^Time stamp: (.+)$', reply, re.M)
        if not match:
            raise GenesisError('Timestamp response has no certified issue time')
        try:
            issued = datetime.strptime(match.group(1).strip(), '%b %d %H:%M:%S %Y GMT').replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise GenesisError('Unsupported timestamp time format') from exc
        nonce = re.search(r'^Nonce: (.+)$', reply, re.M)
        serial = re.search(r'^Serial number: (.+)$', reply, re.M)
        return dict(provider=provider, name=trust['name'], verified=True,
                    issued_at=issued.isoformat().replace('+00:00', 'Z'),
                    target_sha256=digest(read_bytes(target)), response_sha256=digest(read_bytes(response)),
                    request_sha256=digest(read_bytes(request)), nonce=nonce.group(1) if nonce else '',
                    serial=serial.group(1) if serial else '', checked_at=utc_now(),
                    trust_scope=trust['trust_scope'], revocation='Not checked; no long-term qualification asserted',
                    identity='No founder identity or signature is established by this receipt')

    def verify(self):
        integrity = self.integrity()
        receipts = []
        if integrity['ok']:
            for row in self.manifest().get('receipts', []):
                try:
                    receipt = self._verify_timestamp(self.public_file(row['response']), self.public_file(row['request']),
                                                     row['provider'], self.public_file(CANONICAL))
                    receipt['scope'] = 'Shipped founding evidence'
                    receipts.append(receipt)
                except (OSError, ValueError) as exc:
                    receipts.append(dict(provider=row.get('provider'), verified=False, error=str(exc), scope='Shipped founding evidence'))
            for event in self.events():
                if event['type'] != 'timestamp.received':
                    continue
                payload = event['payload']
                try:
                    target = self.target(payload['target'])
                    receipt = self._verify_timestamp(self.object_file(payload['response']),
                                                     self.object_file(payload['request']), payload['provider'], target)
                    receipt.update(scope='Local evidence', target=payload['target'])
                    receipts.append(receipt)
                except (OSError, ValueError) as exc:
                    receipts.append(dict(provider=payload.get('provider'), verified=False, error=str(exc), scope='Local evidence'))
        events = self.events()
        return dict(schema='arc.genesis-verification/1', record_id=RECORD_ID, checked_at=utc_now(),
                    integrity=integrity, receipts=receipts,
                    timestamp_verified=integrity['ok'] and any(r.get('verified') and r['target_sha256'] == CANONICAL_SHA256 for r in receipts),
                    founder_execution='Not verified', founder_identity='Not verified',
                    recorded_genesis_utc=GENESIS_UTC, original_clock_independently_attested=False,
                    local_register=dict(events=len(events), chain='Consistent local hash chain; not independently sealed'))

    def _state_path(self, name):
        return inside(self.state, name)

    def _ensure_state(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.state.is_symlink():
            raise GenesisError('Concern state cannot be linked')
        if os.name != 'nt':
            self.state.chmod(0o700)

    def events(self):
        path = self._state_path('events.jsonl')
        if not path.exists():
            return []
        rows = []; previous = '0' * 64; identifiers = set()
        raw = read_bytes(path, 16 * 1024 * 1024)
        for line in raw.splitlines():
            row = strict_json(line)
            supplied = row.get('sha256')
            body = {k:v for k,v in row.items() if k != 'sha256'}
            if (body.get('previous') != previous or supplied != digest(canonical(body))
                    or body.get('sequence') != len(rows) + 1 or body.get('id') in identifiers
                    or body.get('record_id') != RECORD_ID):
                raise GenesisError('Concern register hash chain is damaged; no records were changed')
            instant(body['at']); identifiers.add(body['id'])
            previous = supplied; rows.append(row)
        return rows

    @contextmanager
    def _lock(self):
        self._ensure_state()
        path = self._state_path('write.lock')
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        stream = os.fdopen(fd, 'r+b')
        try:
            if os.name == 'nt':
                import msvcrt
                if path.stat().st_size == 0:
                    stream.write(b'\0'); stream.flush()
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise GenesisError('Concern register is busy; try again after its writer finishes') from exc
                try:
                    yield
                finally:
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise GenesisError('Concern register is busy; try again after its writer finishes') from exc
                try:
                    yield
                finally:
                    fcntl.flock(stream, fcntl.LOCK_UN)
        finally:
            stream.close()

    def append(self, kind, payload, actor):
        actor = text(actor, 'Recorded actor', 160)
        with self._lock():
            rows = self.events()
            row = dict(schema='arc.concern-event/1', record_id=RECORD_ID, sequence=len(rows) + 1,
                       id=uuid.uuid4().hex, type=kind, actor=actor, actor_identity='Local declaration; not identity-verified',
                       at=utc_now(), previous=rows[-1]['sha256'] if rows else '0' * 64, payload=payload)
            row['sha256'] = digest(canonical(row))
            updated = b''.join(canonical(r) + b'\n' for r in [*rows, row])
            if len(updated) > 16 * 1024 * 1024:
                raise GenesisError('Concern register reached its 16 MiB record limit; existing records were retained')
            atomic(self._state_path('events.jsonl'), updated)
            return row

    def _store_object(self, raw):
        if len(raw) > MAX_FILE:
            raise GenesisError('Evidence file is too large')
        key = digest(raw)
        self._ensure_state()
        path = self._state_path('objects/' + key)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists():
            if digest(read_bytes(path)) != key:
                raise GenesisError('Existing local evidence object changed')
        else:
            atomic(path, raw)
        return dict(sha256=key, bytes=len(raw))

    def object_file(self, row):
        key = row.get('sha256') if isinstance(row, dict) else row
        if not isinstance(key, str) or not re.fullmatch('[0-9a-f]{64}', key):
            raise GenesisError('Invalid evidence object identifier')
        path = self._state_path('objects/' + key)
        raw = read_bytes(path)
        if digest(raw) != key:
            raise GenesisError('Local evidence object changed')
        return path

    def execution_copy(self, path, actor, declared_date=''):
        self.require_integrity()
        path = Path(path)
        raw = read_bytes(path)
        if not raw.startswith(b'%PDF-'):
            raise GenesisError('Choose the PDF execution copy')
        if declared_date:
            instant(declared_date)
        payload = dict(document=self._store_object(raw), filename=path.name,
                       declared_execution_date=declared_date, signature='Not verified', identity='Not verified',
                       statement='Owner-supplied execution copy; receipt or filename does not prove signature')
        return self.append('execution.copy', payload, actor)

    def target(self, target='canonical'):
        if target == 'canonical':
            return self.public_file(CANONICAL)
        row = next((r for r in self.events() if r['id'] == target and r['type'] == 'execution.copy'), None)
        if row is None:
            raise GenesisError('Choose the canonical charter or a recorded execution copy')
        return self.object_file(row['payload']['document'])

    def make_request(self, destination, target='canonical'):
        self.require_integrity()
        destination = Path(destination)
        if destination.exists():
            raise GenesisError('Choose a new request filename; existing evidence will not be overwritten')
        with tempfile.TemporaryDirectory() as tmp:
            query = Path(tmp) / 'request.tsq'
            self._openssl(['ts', '-query', '-data', str(self.target(target)), '-sha256', '-cert', '-out', str(query)])
            raw = read_bytes(query, 8192)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(raw)
        return dict(path=str(destination), sha256=digest(raw), target=target, target_sha256=digest(read_bytes(self.target(target))))

    def import_receipt(self, response, request, provider, actor, target='canonical'):
        self.require_integrity()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            reply = read_bytes(response, MAX_RESPONSE); query = read_bytes(request, 8192)
            (folder / 'response.tsr').write_bytes(reply); (folder / 'request.tsq').write_bytes(query)
            verified = self._verify_timestamp(folder / 'response.tsr', folder / 'request.tsq', provider, self.target(target))
        event = self.append('timestamp.received', dict(provider=provider, target=target,
                            response=self._store_object(reply), request=self._store_object(query), verification=verified), actor)
        return event

    def issue_timestamp(self, provider, actor, target='canonical'):
        if provider not in TRUST:
            raise GenesisError('Unknown timestamp provider')
        self.require_integrity()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); request = folder / 'request.tsq'
            self.make_request(request, target)
            raw = read_bytes(request, 8192)
            req = urllib.request.Request(TRUST[provider]['endpoint'], data=raw,
                    headers={'Content-Type':'application/timestamp-query', 'User-Agent':'ARC-Ledger-Genesis/1.0'}, method='POST')
            try:
                with urllib.request.build_opener(NoRedirect()).open(req, timeout=25) as response:
                    body = response.read(MAX_RESPONSE + 1)
                    if response.status != 200 or response.headers.get_content_type() not in ('application/timestamp-reply', 'application/timestamp-response'):
                        raise GenesisError('Timestamp service did not return an RFC 3161 receipt')
                    if len(body) > MAX_RESPONSE:
                        raise GenesisError('Timestamp response exceeds its size limit')
            except OSError as exc:
                raise GenesisError('Timestamp service is unavailable; original evidence is unchanged') from exc
            reply = folder / 'response.tsr'; reply.write_bytes(body)
            return self.import_receipt(reply, request, provider, actor, target)

    def snapshot(self, sources):
        if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
            raise GenesisError('Choose 1–100 project source files')
        result = []
        for name in sorted(set(sources)):
            if any(part.startswith('.') for part in PurePosixPath(name).parts):
                raise GenesisError('Private state is not a registered source work')
            raw = read_bytes(inside(self.root, name))
            result.append(dict(path=name, sha256=digest(raw), bytes=len(raw)))
        return result

    def register_work(self, title, kind, sources, actor):
        self.require_integrity()
        return self.append('work.registered', dict(title=text(title, 'Work title', 200), kind=text(kind, 'Work kind', 80),
                            sources=self.snapshot(sources), status='Proposed'), actor)

    def register_rights(self, contributor, basis, scope, sources, instrument, actor):
        self.require_integrity()
        if basis not in ('Founder declaration', 'License', 'Assignment'):
            raise GenesisError('Choose a rights basis')
        raw = read_bytes(instrument)
        return self.append('rights.recorded', dict(contributor=text(contributor, 'Contributor', 200), basis=basis,
                           scope=text(scope, 'Rights scope'), sources=self.snapshot(sources),
                           instrument=self._store_object(raw), filename=Path(instrument).name,
                           clearance='Awaiting explicit owner review; instrument authenticity is not verified'), actor)

    def register_delegation(self, recipient, scope, limits, effective, expires, subdelegation, instrument, actor):
        self.require_integrity()
        start, end = instant(effective), instant(expires)
        if end <= start:
            raise GenesisError('Delegation expiry must follow its effective time')
        if type(subdelegation) is not bool:
            raise GenesisError('State whether subdelegation is permitted')
        return self.append('delegation.recorded', dict(recipient=text(recipient, 'Recipient', 200), scope=text(scope, 'Delegated scope'),
                           limits=text(limits, 'Approval limits'), effective=effective, expires=expires,
                           subdelegation=subdelegation, instrument=self._store_object(read_bytes(instrument)),
                           filename=Path(instrument).name, system_grant=False), actor)

    def revoke_delegation(self, identifier, reason, actor):
        if not any(r['id'] == identifier and r['type'] == 'delegation.recorded' for r in self.events()):
            raise GenesisError('Unknown recorded delegation')
        return self.append('delegation.revoked', dict(delegation=identifier, reason=text(reason, 'Revocation reason')), actor)

    def accept_work(self, identifier, rights, review_note, actor):
        self.require_integrity()
        rows = self.events()
        work = next((r for r in rows if r['id'] == identifier and r['type'] == 'work.registered'), None)
        if work is None:
            raise GenesisError('Choose a registered work')
        expected = work['payload']['sources']
        if self.snapshot([s['path'] for s in expected]) != expected:
            raise GenesisError('Work sources changed; register their current edition before acceptance')
        if not isinstance(rights, list) or not rights:
            raise GenesisError('Select the recorded written rights covering this source edition')
        covered = set()
        for identifier_ in rights:
            record = next((r for r in rows if r['id'] == identifier_ and r['type'] == 'rights.recorded'), None)
            if record is None:
                raise GenesisError('Unknown written-rights record')
            self.object_file(record['payload']['instrument'])
            covered.update((s['path'], s['sha256']) for s in record['payload']['sources'])
        if not {(s['path'], s['sha256']) for s in expected}.issubset(covered):
            raise GenesisError('Written-rights records do not cover every file in this work edition')
        return self.append('work.accepted', dict(work=identifier, rights=rights,
                           owner_review=text(review_note, 'Owner rights-review statement'),
                           scope='Concern register acceptance only; source-merging approvals remain separate'), actor)

    def registry(self, now=None):
        rows = self.events(); now = instant(now or utc_now())
        revoked = {r['payload']['delegation'] for r in rows if r['type'] == 'delegation.revoked'}
        accepted = {r['payload']['work'] for r in rows if r['type'] == 'work.accepted'}
        output = []
        for event in rows:
            if event['type'] not in ('work.registered', 'rights.recorded', 'delegation.recorded', 'execution.copy'):
                continue
            row = dict(event)
            if event['type'] == 'delegation.recorded':
                p = event['payload']
                self.object_file(p['instrument'])
                row['status'] = ('Revoked' if event['id'] in revoked else 'Not yet effective' if now < instant(p['effective'])
                                 else 'Expired' if now >= instant(p['expires']) else 'Recorded-current')
            elif event['type'] == 'work.registered':
                p = event['payload']
                try:
                    current = self.snapshot([s['path'] for s in p['sources']])
                    row['status'] = 'Source changed' if current != p['sources'] else 'Owner acceptance recorded' if event['id'] in accepted else 'Proposed'
                except (OSError, ValueError):
                    row['status'] = 'Source missing or unreadable'
            elif event['type'] == 'rights.recorded':
                self.object_file(event['payload']['instrument'])
                row['status'] = 'Written instrument recorded'
            else:
                self.object_file(event['payload']['document'])
                row['status'] = 'Execution copy recorded · signature unverified'
            output.append(row)
        return output

    def export(self, destination, include_local=False):
        destination = Path(destination)
        if destination.exists():
            raise GenesisError('Choose a new evidence archive name')
        report = self.verify()
        if not report['integrity']['ok']:
            raise GenesisError('Cannot export a sealed record while its original fingerprints fail')
        if not include_local:
            report = dict(report)
            report['receipts'] = [r for r in report['receipts'] if r.get('scope') == 'Shipped founding evidence']
            report['local_register'] = dict(included=False)
            report['timestamp_verified'] = any(r.get('verified') and r.get('target_sha256') == CANONICAL_SHA256 for r in report['receipts'])
        files = {'concern/genesis/' + name:self.public_file(name).read_bytes() for name in self.manifest()['files']}
        files['concern/genesis/record.json'] = read_bytes(inside(self.bundle, 'record.json'))
        files['verify_genesis.py'] = read_bytes(Path(__file__))
        files['VERIFICATION.json'] = json.dumps(report, indent=2, ensure_ascii=False).encode() + b'\n'
        if include_local:
            rows = self.events()
            files['.ledger/concern/events.jsonl'] = b''.join(canonical(r) + b'\n' for r in rows)
            for row in rows:
                for key in ('document', 'instrument', 'request', 'response'):
                    obj = row['payload'].get(key)
                    if isinstance(obj, dict) and 'sha256' in obj:
                        files['.ledger/concern/objects/' + obj['sha256']] = self.object_file(obj).read_bytes()
        if len(files) > 2000 or sum(len(raw) for raw in files.values()) > 128 * 1024 * 1024:
            raise GenesisError('This evidence selection exceeds the 128 MiB export limit')
        files['READ_ME.txt'] = ("ARC-GENESIS-0001 evidence copy\n\nVerify with Python 3.10+ and OpenSSL:\n"
            "  python verify_genesis.py --root . verify\n\nThe founding clock entry and independently certified receipt time are separate.\n"
            "A timestamp does not prove the Founder's identity or signature.\n"
            "Local register entries, if included, are declarations; a consistent hash chain is not an independent signature.\n").encode()
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'wb') as output:
            with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, raw in sorted(files.items()):
                    archive.writestr(name, raw)
        archive_hash = hashlib.sha256()
        with destination.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024 * 1024), b''):
                archive_hash.update(chunk)
        return dict(path=str(destination), files=len(files), included_local=include_local,
                    sha256=archive_hash.hexdigest(), timestamp_verified=report['timestamp_verified'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('verify'); commands.add_parser('charter'); commands.add_parser('register')
    request = commands.add_parser('request'); request.add_argument('destination'); request.add_argument('--target', default='canonical')
    export = commands.add_parser('export'); export.add_argument('destination'); export.add_argument('--include-local', action='store_true')
    receive = commands.add_parser('import-receipt'); receive.add_argument('response'); receive.add_argument('request')
    receive.add_argument('--provider', choices=sorted(TRUST), default='freetsa'); receive.add_argument('--actor', required=True); receive.add_argument('--target', default='canonical')
    args = parser.parse_args(argv)
    try:
        store = GenesisStore(args.root)
        if args.command == 'verify':
            result = store.verify()
        elif args.command == 'charter':
            print(store.charter()); return 0
        elif args.command == 'register':
            result = store.registry()
        elif args.command == 'request':
            result = store.make_request(args.destination, args.target)
        elif args.command == 'export':
            result = store.export(args.destination, args.include_local)
        else:
            result = store.import_receipt(args.response, args.request, args.provider, args.actor, args.target)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if args.command == 'verify' and (not result['integrity']['ok'] or not result['timestamp_verified']):
            return 1
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps(dict(error=str(exc)), ensure_ascii=False)); return 2


if __name__ == '__main__':
    raise SystemExit(main())
