"""Build and verify local handoff ZIPs from exact, explicitly reviewed Files."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat
import struct
import uuid
import zipfile

from . import edit_storage, files_service, record_io


PREFIX = 'programs.delivery.'
INSPECT, BUILD, VERIFY = (PREFIX + action for action in ('inspect', 'build', 'verify'))
PROFILE = 'graphite.delivery/1'
MANIFEST = 'GRAPHITE-MANIFEST.json'
MAX_FILES = 16
MAX_BYTES = 64 * 1024 * 1024
MAX_MANIFEST = 32 * 1024
MAX_ARCHIVE = MAX_BYTES + 256 * 1024
PORTABLE_MODE = (stat.S_IFREG | 0o644) << 16
PATH = {**files_service.REL, 'minLength': 1}
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'minLength': 64, 'maxLength': 64}
REVIEW = {'type': 'object', 'properties': {'path': PATH, 'sha256': SHA},
          'required': ['path', 'sha256'], 'additionalProperties': False}
FIELDS = {
    INSPECT: ({'paths': {'type': 'array', 'items': PATH, 'minItems': 1, 'maxItems': MAX_FILES}}, ['paths']),
    BUILD: ({'entries': {'type': 'array', 'items': REVIEW, 'minItems': 1, 'maxItems': MAX_FILES},
             'destination': PATH}, ['entries', 'destination']),
    VERIFY: ({'path': PATH}, ['path']),
}
SCOPES = {INSPECT: 'read', BUILD: 'approve', VERIFY: 'read'}


def _visible_path(path):
    edit_storage.relative(path)
    if len(path.encode('utf-8')) > 1000 or any(not char.isprintable() or char in '<>"|?*' for char in path):
        raise ValueError('Use a printable, portable Files path.')
    if any(files_service.machine(Path(part)) or len(part.encode('utf-8')) > 240 for part in path.split('/')):
        raise ValueError('Choose visible Files paths without machine or private entries.')
    return path


def _members(paths):
    if not 1 <= len(paths) <= MAX_FILES:
        raise ValueError(f'Choose between 1 and {MAX_FILES} files for delivery.')
    names = set()
    prefixes = {MANIFEST.casefold(): (MANIFEST, False)}
    for path in paths:
        _visible_path(path)
        parts = path.split('/')
        for size in range(1, len(parts) + 1):
            spelling = '/'.join(parts[:size])
            key = spelling.casefold()
            entry = (spelling, size < len(parts))
            if key in prefixes and (prefixes[key] != entry or not entry[1]):
                raise ValueError('Selected paths collide with each other or the reserved delivery manifest.')
            prefixes[key] = entry
        names.add(path)
    return sorted(names)


def _zip_path(path):
    _visible_path(path)
    if Path(path).suffix.casefold() != '.zip':
        raise ValueError('Choose a .zip path inside Files.')
    return path


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def _read_file(base, path):
    with edit_storage.parent(base, path) as (folder, name):
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
        fd = os.open(name, flags, dir_fd=folder)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError('Choose regular Files entries without filesystem links.')
            with os.fdopen(fd, 'rb', buffering=0, closefd=False) as stream:
                yield stream
            with edit_storage.parent(base, path) as (current, leaf):
                at_path = os.stat(leaf, dir_fd=current, follow_symlinks=False)
            if _signature(before) != _signature(at_path) or _signature(before) != _signature(os.fstat(fd)):
                raise ValueError('A selected Files entry changed while it was being read. Review it again.')
        finally:
            os.close(fd)


def _selected(base, paths, archive=None, expected=None):
    entries = []
    remaining = MAX_BYTES
    for path in paths:
        with _read_file(base, path) as source:
            if archive is None:
                data = edit_storage.fingerprint_fd(source.fileno(), maximum=remaining)
            else:
                with archive.open(_zip_member(path), 'w') as member:
                    data = edit_storage.fingerprint_fd(source.fileno(), member, maximum=remaining)
        if expected is not None and data['sha256'] != expected[path]:
            raise ValueError(f'{path} changed since inspection. Review the selected files again.')
        remaining -= data['bytes']
        entries.append({'path': path, 'bytes': data['bytes'], 'sha256': data['sha256']})
    return entries, MAX_BYTES - remaining


def _zip_member(path):
    member = zipfile.ZipInfo(path)
    member.create_system = 3
    member.external_attr = PORTABLE_MODE
    return member


def _manifest(entries):
    return record_io.canonical({'schema': PROFILE, 'entries': entries})


def _valid_sha(digest):
    return isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest) is not None


def _manifest_entries(raw):
    value = record_io.strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'schema', 'entries'} or value['schema'] != PROFILE:
        raise ValueError('The archive has no supported Graphite delivery manifest.')
    entries = value['entries']
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise ValueError('The delivery manifest has an invalid file count.')
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) != {'path', 'bytes', 'sha256'}
                or not isinstance(entry['path'], str) or not _valid_sha(entry['sha256'])
                or type(entry['bytes']) is not int or not 0 <= entry['bytes'] <= MAX_BYTES):
            raise ValueError('The delivery manifest has invalid file records.')
    paths = [entry['path'] for entry in entries]
    if paths != _members(paths) or sum(entry['bytes'] for entry in entries) > MAX_BYTES or raw != _manifest(entries):
        raise ValueError('The delivery manifest is not canonical or exceeds the delivery limit.')
    return entries


def _verify_archive(stream, size):
    try:
        # Bound the directory before zipfile creates one ZipInfo per record.
        if size < 22:
            raise ValueError('The delivery ZIP is truncated.')
        stream.seek(-22, os.SEEK_END)
        end = stream.read(22)
        marker, disk, directory_disk, disk_count, count, length, start, comment = struct.unpack('<4s4H2LH', end)
        if (marker != b'PK\x05\x06' or disk or directory_disk or comment or count != disk_count
                or not 2 <= count <= MAX_FILES + 1 or length > (MAX_FILES + 1) * 1046
                or start + length + 22 != size):
            raise ValueError('The ZIP directory exceeds the supported delivery layout.')
        with zipfile.ZipFile(stream, 'r') as archive:
            members = archive.infolist()
            if archive.comment or len(members) != count:
                raise ValueError('The ZIP does not have a supported delivery layout.')
            header = members[-1]
            if header.filename != MANIFEST or header.file_size > MAX_MANIFEST:
                raise ValueError('The ZIP does not end with a bounded Graphite delivery manifest.')
            offset = 0
            directory_bytes = 0
            for member in members:
                if (member.filename != member.orig_filename or member.flag_bits & ~0x800
                        or member.compress_type != zipfile.ZIP_STORED or member.compress_size != member.file_size
                        or member.extra or member.comment or member.external_attr != PORTABLE_MODE
                        or member.create_system != 3 or member.header_offset != offset):
                    raise ValueError('The ZIP contains unsupported members or metadata.')
                name_bytes = len(member.filename.encode('utf-8'))
                offset += 30 + name_bytes + member.file_size
                directory_bytes += 46 + name_bytes
            if offset + directory_bytes + 22 != size:
                raise ValueError('The ZIP contains bytes outside its delivery records.')
            entries = _manifest_entries(archive.read(header))
            if [entry['path'] for entry in entries] != [member.filename for member in members[:-1]]:
                raise ValueError('The ZIP members do not match the delivery manifest.')
            for entry, member in zip(entries, members[:-1]):
                if entry['bytes'] != member.file_size:
                    raise ValueError(f"Delivery size mismatch for {entry['path']}.")
                digest = hashlib.sha256()
                with archive.open(member) as source:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        digest.update(block)
                if digest.hexdigest() != entry['sha256']:
                    raise ValueError(f"Delivery checksum mismatch for {entry['path']}.")
            return entries
    except (zipfile.BadZipFile, UnicodeError, EOFError, RuntimeError, NotImplementedError) as error:
        raise ValueError('The ZIP or delivery manifest is damaged or unsupported.') from error


def _build(base, reviewed, destination):
    paths = _members([entry['path'] for entry in reviewed])
    expected = {entry['path']: entry['sha256'] for entry in reviewed}
    if not all(_valid_sha(digest) for digest in expected.values()):
        raise ValueError('Inspect each selected file to obtain its exact SHA-256 before building.')
    with edit_storage.parent(base, _zip_path(destination)) as (folder, name):
        try:
            os.stat(name, dir_fd=folder, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Choose a fresh destination for the delivery ZIP.')
        stage = '.graphite-delivery-' + uuid.uuid4().hex
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(stage, flags, 0o600, dir_fd=folder)
        try:
            with os.fdopen(fd, 'w+b', buffering=0) as output:
                with zipfile.ZipFile(output, 'w', allowZip64=False) as archive:
                    entries, _ = _selected(base, paths, archive=archive, expected=expected)
                    archive.writestr(_zip_member(MANIFEST), _manifest(entries))
                output.flush()
                os.fsync(output.fileno())
                size = os.fstat(output.fileno()).st_size
                if size > MAX_ARCHIVE:
                    raise ValueError('The delivery ZIP exceeds its size limit.')
                if _verify_archive(output, size) != entries:
                    raise ValueError('The built delivery failed its manifest readback.')
                output.seek(0)
                identity = edit_storage.fingerprint_fd(output.fileno(), maximum=MAX_ARCHIVE)
            with edit_storage.parent(base, destination) as (current, _):
                if not os.path.samestat(os.fstat(current), os.fstat(folder)):
                    raise ValueError('The destination folder changed during delivery.')
            try:
                os.link(stage, name, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
            except FileExistsError as error:
                raise ValueError('The destination appeared during delivery. Choose a new ZIP path.') from error
        finally:
            os.unlink(stage, dir_fd=folder)
        os.fsync(folder)
    return {'state': 'EXPORTED', 'path': destination, 'bytes': identity['bytes'],
            'sha256': identity['sha256'], 'member_count': len(entries)}


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS or SCOPES[operation] not in principal.scopes:
        raise ValueError('Delivery operation is outside the authorized scope.')
    base = files_service.root(kernel, create=False).absolute()
    if operation == INSPECT:
        entries, total = _selected(base, _members(args['paths']))
        return {'state': 'READY', 'entries': entries, 'bytes': total}
    if operation == BUILD:
        return _build(base, args['entries'], args['destination'])
    path = _zip_path(args['path'])
    with _read_file(base, path) as source:
        identity = edit_storage.fingerprint_fd(source.fileno(), maximum=MAX_ARCHIVE)
        entries = _verify_archive(source, identity['bytes'])
    return {'state': 'VERIFIED', 'path': path, 'bytes': identity['bytes'], 'sha256': identity['sha256'],
            'entries': entries, 'member_count': len(entries)}
