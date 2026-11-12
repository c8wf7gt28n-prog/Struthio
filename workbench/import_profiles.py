"""Reviewed folder/ZIP import profiles. Copy in, never execute or move originals."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import uuid
import zipfile
from . import edit_storage as store, project_desk as records, working_copies as copies, files_service

PROFILES = ('MIXED', 'NOTES', 'CODE', 'TABLES', 'ENGINEERING')
CONFIGS = frozenset({'.gitignore', '.gitattributes', '.editorconfig', '.clang-format', '.clang-tidy'})
LOCKFILES = frozenset({'Cargo.lock', 'poetry.lock', 'uv.lock', 'Pipfile.lock', 'package-lock.json', 'pnpm-lock.yaml'})
NOTES = frozenset({'.txt', '.md', '.rst', '.pdf', '.docx', '.odt'})
CODE = frozenset({'.c', '.h', '.cc', '.cpp', '.hpp', '.py', '.rs', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.json', '.toml', '.yaml', '.yml', '.sh', '.cmake', '.mk', '.v', '.sv'}) | NOTES
TABLES = frozenset({'.csv', '.tsv', '.xlsx', '.ods', '.json', '.yaml', '.yml'})
ENGINEERING = CODE | TABLES | frozenset({'.kicad_pcb', '.kicad_sch', '.kicad_pro', '.sch', '.pcb', '.step', '.stp', '.stl', '.obj', '.dxf', '.svg', '.gbr', '.gerber', '.drl', '.spice', '.cir', '.lib'})
DEFAULT_LIMITS = {'files': 2000, 'total_bytes': 512 * 1024 * 1024, 'file_bytes': 64 * 1024 * 1024}
LIMITS = {'type': 'object', 'additionalProperties': False, 'properties': {
    'files': {'type': 'integer', 'minimum': 1, 'maximum': 5000},
    'total_bytes': {'type': 'integer', 'minimum': 1, 'maximum': 2 * 1024 * 1024 * 1024},
    'file_bytes': {'type': 'integer', 'minimum': 1, 'maximum': store.MAX_FILE}}, 'required': list(DEFAULT_LIMITS)}
FIELDS = {
    'imports.preview': ({'source': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
        'profile': {'type': 'string', 'enum': list(PROFILES)}, 'limits': LIMITS}, ['source', 'profile']),
    'imports.get': ({'id': records.ID}, ['id']),
    'imports.accept': ({'id': records.ID, 'expected_digest': {'type': 'string', 'minLength': 64, 'maxLength': 64},
        'for_slate': {'type': 'boolean'}}, ['id', 'expected_digest']),
}
SCOPES = {op: 'read' if op == 'imports.get' else 'approve' for op in FIELDS}
SENSITIVE = re.compile(rb'-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----|\bAKIA[A-Z0-9]{16}\b|(?im:^\s*(?:password|api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"\x27]?[^\s\"\x27]{8,})')


def eligibility(rel, profile):
    store.relative(rel); parts = rel.split('/'); name = parts[-1]; lower = name.casefold()
    if any(p in ('.git', '.hg', '.svn') for p in parts): return 'OPTIONAL_HISTORY_NOT_INCLUDED'
    if any(p in files_service.MACHINE_NAMES or p in ('build', 'dist', 'target') for p in parts[:-1]): return 'CACHE_OR_BUILD_PRODUCT'
    if lower in ('id_rsa', 'id_ed25519', 'credentials', 'credentials.json', 'secrets.json', '.netrc', '.npmrc', '.pypirc') or lower.startswith('.env') or Path(lower).suffix in ('.key', '.pem', '.p12', '.pfx', '.kdbx'):
        return 'CREDENTIAL_OR_PRIVATE_KEY'
    if lower.endswith('.gguf'): return 'OPTIONAL_MODEL_NOT_INCLUDED'
    if any(p.startswith('.') for p in parts[:-1]) or (name.startswith('.') and not (profile in ('CODE', 'MIXED', 'ENGINEERING') and name in CONFIGS)):
        return 'HIDDEN_NOT_IN_REVIEWED_CONFIG_SET'
    if (Path(lower).suffix in files_service.MACHINE_SUFFIXES and name not in LOCKFILES and not (profile == 'ENGINEERING' and Path(lower).suffix == '.lib')) or lower in files_service.MACHINE_NAMES: return 'CACHE_OR_BUILD_PRODUCT'
    if profile != 'MIXED':
        allowed = {'NOTES': NOTES, 'CODE': CODE, 'TABLES': TABLES, 'ENGINEERING': ENGINEERING}[profile]
        if Path(lower).suffix not in allowed and name not in CONFIGS | LOCKFILES and lower not in ('readme', 'license', 'licence', 'makefile', 'cmakelists.txt'):
            return 'OUTSIDE_SELECTED_PROFILE'
    return None


def sensitive_stream(stream, maximum):
    sha = hashlib.sha256(); size = 0; tail = b''; sensitive = False
    while True:
        block = stream.read(1048576)
        if not block: break
        size += len(block)
        if size > maximum: raise ValueError('File exceeds import byte bound')
        if SENSITIVE.search(tail + block): sensitive = True
        tail = block[-512:]; sha.update(block)
    return sha.hexdigest(), size, sensitive


def folder_scan(root, profile, limits, kernel=None):
    """Hash all included bytes, preserving empty directories; never follow links."""
    entries = []; directories = []; files = {}; total = 0; visited = 0; duplicates = {}
    with store.directory(root): pass
    for folder, dirs, names in os.walk(root, followlinks=False):
        here = Path(folder); keep_dirs = []
        for name in sorted(dirs):
            rel = (here / name).relative_to(root).as_posix(); visited += 1
            if visited > 20000: raise ValueError('Import traversal bound reached; choose a smaller folder')
            try: reason = eligibility(rel + '/placeholder.txt', profile)
            except ValueError: reason = 'UNSAFE_NAME'
            if (here / name).is_symlink(): reason = 'LINK_NOT_FOLLOWED'
            if reason in ('OUTSIDE_SELECTED_PROFILE',): reason = None
            if reason: entries.append({'path': rel + '/', 'state': 'EXCLUDED', 'reason': reason})
            else: keep_dirs.append(name); directories.append(rel)
        dirs[:] = keep_dirs
        for name in sorted(names):
            rel = (here / name).relative_to(root).as_posix(); visited += 1
            if visited > 20000: raise ValueError('Import traversal bound reached; choose a smaller folder')
            info = os.lstat(here / name); reason = None
            try: reason = eligibility(rel, profile)
            except ValueError: reason = 'UNSAFE_NAME'
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: reason = 'LINK_OR_SPECIAL_FILE'
            if info.st_size > limits['file_bytes']: reason = 'OVERSIZED_FILE'
            if reason:
                entries.append({'path': rel, 'state': 'EXCLUDED', 'reason': reason}); continue
            try:
                fd = store.open_file(root, rel)
                with os.fdopen(fd, 'rb') as stream: sha, size, sensitive = sensitive_stream(stream, limits['file_bytes'])
                # Independent descriptor check ensures the view was not replaced mid-read.
                measured = store.inspect_file(root, rel, limits['file_bytes'])
                if not measured or measured['sha256'] != sha or measured['bytes'] != size: raise ValueError('File changed during import')
                if sensitive: entries.append({'path': rel, 'state': 'EXCLUDED', 'reason': 'SENSITIVE_CONTENT'}); continue
                if kernel:
                    kept = store.keep_file(kernel, root, rel, limits['file_bytes'])
                    if kept['sha256'] != sha: raise ValueError('File changed during import capture')
                total += size
                if len(files) + 1 > limits['files'] or total > limits['total_bytes']: raise ValueError('Included files exceed the reviewed import limits')
                value = {'sha256': sha, 'bytes': size, 'mode': measured['mode']}
                files[rel] = value
                entries.append({'path': rel, 'state': 'INCLUDED', **value, 'duplicate_of': duplicates.get(sha)})
                duplicates.setdefault(sha, rel)
            except PermissionError: entries.append({'path': rel, 'state': 'UNREADABLE', 'reason': 'READ_PERMISSION'})
    collision_check(files, directories)
    return {'files': files, 'directories': sorted(directories), 'entries': entries, 'bytes': total}


def collision_check(files, dirs):
    names = list(files) + list(dirs)
    if len({p.casefold() for p in names}) != len(names): raise ValueError('Archive/project has duplicate or case-colliding paths')
    for name in files:
        if any('/'.join(name.split('/')[:i]) in files for i in range(1, len(name.split('/')))):
            raise ValueError('A file is used as a parent directory')


def archive_scan(source, profile, limits, kernel=None):
    entries = []; files = {}; directories = set(); total = 0; seen = set(); duplicates = {}
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > 20000: raise ValueError('Archive member limit reached')
        for member in members:
            rel = member.filename.rstrip('/') if member.is_dir() else member.filename
            store.relative(rel)
            if rel.casefold() in seen: raise ValueError('Duplicate or case-colliding archive member')
            seen.add(rel.casefold())
            mode = member.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR) or member.flag_bits & 1:
                raise ValueError('Links, special or encrypted archive members are refused')
            if member.is_dir():
                reason = eligibility(rel + '/placeholder.txt', profile)
                if reason not in (None, 'OUTSIDE_SELECTED_PROFILE'): entries.append({'path': rel + '/', 'state': 'EXCLUDED', 'reason': reason})
                else: directories.add(rel)
                continue
            reason = eligibility(rel, profile)
            if member.file_size > limits['file_bytes']: reason = 'OVERSIZED_FILE'
            if member.file_size > max(1048576, member.compress_size * 200): raise ValueError('Archive expansion ratio exceeds 200')
            if reason: entries.append({'path': rel, 'state': 'EXCLUDED', 'reason': reason}); continue
            with archive.open(member) as stream: sha, size, sensitive = sensitive_stream(stream, min(limits['file_bytes'], member.file_size))
            if size != member.file_size: raise ValueError('Archive member size mismatch')
            if sensitive: entries.append({'path': rel, 'state': 'EXCLUDED', 'reason': 'SENSITIVE_CONTENT'}); continue
            total += size
            if len(files) + 1 > limits['files'] or total > limits['total_bytes']: raise ValueError('Archive expansion exceeds reviewed limits')
            if kernel:
                with archive.open(member) as stream: kept, count = store.keep_stream(kernel, stream, limits['file_bytes'])
                if kept != sha or count != size: raise ValueError('Archive member changed during capture')
            files[rel] = {'sha256': sha, 'bytes': size, 'mode': stat.S_IMODE(mode) & 0o777 or 0o644}
            entries.append({'path': rel, 'state': 'INCLUDED', **files[rel], 'duplicate_of': duplicates.get(sha)})
            duplicates.setdefault(sha, rel)
            for i in range(1, len(rel.split('/'))): directories.add('/'.join(rel.split('/')[:i]))
    collision_check(files, sorted(directories))
    return {'files': files, 'directories': sorted(directories), 'entries': entries, 'bytes': total}


def source_place(kernel, source):
    # Reuse the existing owner-selected external-source boundary. Reviewed
    # configuration children are a new profile capability; roots stay ordinary.
    path = copies.allowed_place(kernel, source)
    with store.directory(path if path.is_dir() else path.parent): pass
    if path.is_symlink(): raise ValueError('Source links are not followed')
    if not path.is_dir() and (not path.is_file() or path.stat().st_size > store.MAX_FILE): raise ValueError('Choose a folder or ZIP up to 256 MiB')
    if path.is_file() and path.suffix.casefold() != '.zip': raise ValueError('Archive imports currently support ZIP; select a folder for other sources')
    return path


def scan_source(kernel, source, profile, limits, capture=False):
    path = source_place(kernel, source)
    if path.is_dir(): return folder_scan(path, profile, limits, kernel if capture else None), None
    identity = store.inspect_file(path.parent, path.name)['sha256']
    value = archive_scan(path, profile, limits, kernel if capture else None)
    if store.inspect_file(path.parent, path.name)['sha256'] != identity: raise ValueError('Archive changed while being read')
    return value, identity


def preview(kernel, args, principal):
    limits = args.get('limits', dict(DEFAULT_LIMITS))
    value, archive_sha = scan_source(kernel, args['source'], args['profile'], limits)
    result = {'schema': 'arc.import-preview/1', 'id': uuid.uuid4().hex, 'owner': principal.identity, 'created': time.time(),
        'source': str(source_place(kernel, args['source'])), 'source_kind': 'ZIP' if archive_sha else 'FOLDER',
        'archive_sha256': archive_sha, 'profile': args['profile'], 'limits': limits, **value,
        'extraction': 'ORIGINAL_BYTES_COPIED_NO_EXECUTION', 'rules': 'arc.import-profile/1'}
    result['content_digest'] = records.digest(result)
    with kernel.db() as db: return store.put(db, principal.identity, 'import', result)


def manifest(value):
    return {'schema': 'arc.copies-folder/1', 'files': {rel: {'sha': f['sha256'], 'size': f['bytes'], 'mode': f['mode'], 'mtime': 0} for rel, f in value['files'].items()},
        'skipped': [(e['path'], e.get('reason')) for e in value['entries'] if e['state'] != 'INCLUDED'],
        'profile': value['profile'], 'limits': value['limits'], 'directories': value['directories']}


def write_tree(kernel, destination, value):
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    for rel in value['directories']:
        with store.parent(destination, rel + '/.parent', create=True): pass
    for rel, info in value['files'].items():
        from . import work_trail
        if work_trail.execution_held(kernel): raise ValueError('Work is held; the private import stage was not published')
        with store.parent(destination, rel, create=True) as (fd, name):
            out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                with (copies.store(kernel) / info['sha256']).open('rb') as source, os.fdopen(out, 'wb', closefd=False) as target:
                    shutil.copyfileobj(source, target, 1048576); target.flush(); os.fsync(out)
                os.fchmod(out, info['mode'] & 0o777); os.fsync(out); os.fsync(fd)
            finally: os.close(out)


def accept(kernel, args, principal):
    with kernel.db() as db: value = store.get(db, principal.identity, 'import', args['id'])
    if args['expected_digest'] != value['content_digest']: raise ValueError('Import preview digest changed')
    if not value['files']: raise ValueError('There are no included files to import')
    with store.lock(kernel, value['id']):
        with kernel.db() as db: prior = db.execute('SELECT copy,work,state FROM edit_accepts WHERE preview=?', (value['id'],)).fetchone()
        if prior and prior[2] == 'DONE':
            from .change_sets import describe_workspace
            return describe_workspace(kernel, prior[0], principal)
        measured, sha = scan_source(kernel, value['source'], value['profile'], value['limits'], capture=True)
        if measured['files'] != value['files'] or measured['directories'] != value['directories'] or sha != value['archive_sha256']:
            raise ValueError('Import source changed; make and review a new preview')
        ident = prior[0] if prior else uuid.uuid4().hex
        basename = Path(value['source']).stem[:100] or 'Imported project'
        work = prior[1] if prior else 'Working copies/' + basename + '-' + ident[:8]
        store.relative(work)
        with kernel.db() as db:
            if not prior: db.execute('INSERT INTO edit_accepts VALUES(?,?,?,?)', (value['id'], ident, work, 'PREPARED'))
        destination = files_service.root(kernel) / work; destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not destination.exists():
            stage = destination.parent / ('.import-' + ident)
            if stage.exists(): shutil.rmtree(stage)  # unpublished, owned scratch only
            write_tree(kernel, stage, value)
            from . import work_trail
            if work_trail.execution_held(kernel): raise ValueError('Work is held; the private import stage was retained without publication')
            with store.directory(destination.parent) as fd: store.rename_linux(fd, stage.name, destination.name)
        current = folder_scan(destination, value['profile'], value['limits'])
        if current['files'] != value['files']: raise ValueError('Published import differs; retain it for recovery and inspect it')
        base = store.keep_bytes(kernel, json.dumps(manifest(value), sort_keys=True).encode())
        meta = {'schema': 'arc.profiled-copy/1', 'id': ident, 'copy': ident, 'owner': principal.identity, 'created': time.time(),
            'preview': value['id'], 'profile': value['profile'], 'limits': value['limits'], 'source_kind': value['source_kind'],
            'original_update': 'OWNER_PUBLISH_ONLY' if value['source_kind'] == 'FOLDER' else 'SAVE_AS_NEW_ONLY_ARCHIVE_NOT_REWRITTEN'}
        with copies.opened(kernel) as db:
            db.execute('INSERT INTO copies(id,owner,source,base,base_size,base_mtime,base_mode,work,for_slate,state,revision,created,updated,kind) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ident, principal.identity, value['source'], base, len(value['files']), 0, 0o700, work, int(args.get('for_slate', False)), 'WORKING', 0, time.time(), time.time(), 'folder'))
            store.put(db, principal.identity, 'workspace', meta)
            db.execute("UPDATE edit_accepts SET state='DONE' WHERE preview=?", (value['id'],))
        from .change_sets import describe_workspace
        return describe_workspace(kernel, ident, principal)


def _dispatch(kernel, op, args, principal):
    if op == 'imports.preview': return preview(kernel, args, principal)
    if op == 'imports.accept': return accept(kernel, args, principal)
    with kernel.db() as db: return store.get(db, principal.identity, 'import', args['id'])


def dispatch(kernel, op, args, principal):
    try: return _dispatch(kernel, op, args, principal)
    except (zipfile.BadZipFile, NotImplementedError, RecursionError) as exc:
        raise ValueError('Archive or profile cannot be processed safely: ' + type(exc).__name__) from None
