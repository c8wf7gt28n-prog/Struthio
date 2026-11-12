"""Bounded ZIP inventory and V1 transport integrity. Never extracts or executes."""
from __future__ import annotations
import hashlib
import io
import re
import stat
import struct
import time
import zipfile
import zlib
from . import intake_files as files, record_store as records

VERSION = 'arc.package-inspection/1'
MAX_INPUT = 128 * 1024 * 1024
MAX_METADATA = 8 * 1024 * 1024
MAX_SECONDS = 20
METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def name(value):
    if len(value.encode('utf-8')) > 1024 or any(p.endswith((' ', '.')) for p in value.split('/')):
        raise ValueError('PACKAGE_NONPORTABLE_PATH')
    return files.portable(value)


def inspect_bytes(raw, filename, cancelled=lambda: False):
    result = {'schema': VERSION, 'sha256': digest(raw), 'bytes': len(raw), 'state': 'BLOCKED',
              'format': 'ZIP', 'encryption': 'NOT_ESTABLISHED', 'members': [], 'member_count': 0, 'issues': [],
              'transport': {'state': 'NOT_DECLARED', 'dependencies': 'NOT_DECLARED', 'missing': []},
              'accepted': 0, 'source_promotion': 'NOT_GRANTED', 'physical_qualification': False}
    start = time.monotonic()
    def check():
        if cancelled():raise ValueError('PACKAGE_INSPECTION_CANCELLED')
        if time.monotonic()-start > MAX_SECONDS:raise ValueError('PACKAGE_INSPECTION_TIME_LIMIT')
    try:
        if len(raw) > MAX_INPUT:raise ValueError('PACKAGE_INPUT_LIMIT')
        if not filename.lower().endswith('.zip'):
            result.update(state='UNSUPPORTED', format='OTHER')
            result['issues'] = ['PACKAGE_FORMAT_NOT_QUALIFIED_USE_INDIVIDUAL_FILE_INTAKE']
            return result
        # Bound central-directory allocation before asking ZipFile to parse it.
        end = raw.rfind(b'PK\x05\x06', max(0, len(raw)-65557))
        if end < 0 or len(raw)-end < 22:raise ValueError('PACKAGE_MALFORMED_ZIP')
        _, disk, central_disk, on_disk, count, central_size, offset, comment = struct.unpack_from('<4s4H2LH', raw, end)
        if disk or central_disk or on_disk != count:raise ValueError('PACKAGE_MULTIPART_NOT_QUALIFIED')
        if count == 65535 or offset == 0xffffffff or central_size == 0xffffffff:
            raise ValueError('PACKAGE_ZIP64_NOT_QUALIFIED')
        if count > files.MAX_FILES or central_size > MAX_METADATA:raise ValueError('PACKAGE_DIRECTORY_LIMIT')
        if end+22+comment != len(raw) or offset+central_size != end:raise ValueError('PACKAGE_MALFORMED_DIRECTORY')
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) != count:raise ValueError('PACKAGE_DIRECTORY_COUNT_MISMATCH')
            seen = {}; selected = []; total = 0
            for member in infos:
                check()
                if member.orig_filename != member.filename:raise ValueError('PACKAGE_NUL_PATH')
                canonical = name(member.filename.rstrip('/'))
                key = canonical.casefold()
                if key in seen:raise ValueError('PACKAGE_DUPLICATE_PATH')
                mode = stat.S_IFMT(member.external_attr >> 16)
                if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or (mode == stat.S_IFDIR and not member.is_dir()):
                    raise ValueError('PACKAGE_LINK_OR_SPECIAL_ENTRY')
                seen[key] = member.is_dir()
                if member.is_dir():continue
                if member.file_size > files.MAX_FILE or member.file_size > max(1,member.compress_size)*1000:
                    raise ValueError('PACKAGE_EXPANSION_LIMIT')
                total += member.file_size
                if total > files.MAX_BUNDLE:raise ValueError('PACKAGE_EXPANSION_LIMIT')
                selected.append((member,canonical))
            for key, directory in seen.items():
                if any('/'.join(key.split('/')[:i]) in seen and not seen['/'.join(key.split('/')[:i])]
                       for i in range(1,len(key.split('/')))):
                    raise ValueError('PACKAGE_FILE_DIRECTORY_COLLISION')
            if any(m.flag_bits & 1 or m.compress_type == 99 for m in infos):
                result.update(state='ENCRYPTED', encryption='PRESENT')
                result['issues'] = ['PACKAGE_ENCRYPTED_MEMBERS_NOT_QUALIFIED']
                return result
            result['encryption'] = 'NONE'
            if any(m.compress_type not in METHODS for m,_ in selected):
                result['state'] = 'UNSUPPORTED'
                result['issues'] = ['PACKAGE_COMPRESSION_NOT_QUALIFIED']
                return result
            if not selected:raise ValueError('PACKAGE_EMPTY')
            content = {}; actual_total = 0; record_total = 0
            for member,canonical in selected:
                check(); h = hashlib.sha256(); size = 0
                is_record = canonical == 'V1/catalog.json' or canonical.startswith('V1/decisions/')
                chunks = []
                with archive.open(member) as stream:
                    while chunk := stream.read(65536):
                        check(); size += len(chunk); actual_total += len(chunk)
                        if size > member.file_size or size > files.MAX_FILE or actual_total > files.MAX_BUNDLE:
                            raise ValueError('PACKAGE_ACTUAL_EXPANSION_LIMIT')
                        h.update(chunk)
                        if is_record:
                            record_total += len(chunk)
                            if record_total > MAX_METADATA:raise ValueError('PACKAGE_MANIFEST_LIMIT')
                            chunks.append(chunk)
                if size != member.file_size:raise ValueError('PACKAGE_MEMBER_SIZE_MISMATCH')
                result['members'].append({'name':canonical,'bytes':size,'sha256':h.hexdigest(),
                                          'compressed_bytes':member.compress_size})
                if is_record:content[canonical] = b''.join(chunks)
            result['members'].sort(key=lambda r:r['name'])
            result['inventory_sha256'] = digest(records.canonical(result['members']))
            result['expanded_bytes'] = actual_total
            result['transport'] = verify_v1(result['members'], content)
            result['state'] = 'READY' if result['transport']['state'] in ('NOT_DECLARED','VERIFIED') else 'BLOCKED'
            if result['state'] != 'READY':result['issues'].append('PACKAGE_TRANSPORT_MANIFEST_MISMATCH')
    except (ValueError, OSError, zipfile.BadZipFile, EOFError, NotImplementedError, RuntimeError, struct.error, zlib.error) as exc:
        code = str(exc)
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{1,100}', code):code = 'PACKAGE_CORRUPT_OR_MALFORMED'
        result['issues'] = [code]
        result['members'] = []
        if code.endswith('NOT_QUALIFIED'):result['state'] = 'UNSUPPORTED'
    result['member_count'] = len(result['members'])
    return result


def verify_v1(members, content):
    """Self-consistency only. An imported approval claim never grants authority."""
    base = {'state':'NOT_DECLARED','dependencies':'NOT_DECLARED','missing':[],
            'authenticity':'UNSIGNED_CONTENT_INTEGRITY_ONLY'}
    if 'V1/catalog.json' not in content:return base
    try:
        manifest = records.strict(content['V1/catalog.json'])
        if manifest.get('schema') != 'arc.accepted-reference-catalog/1' or manifest.get('source_promotion') != 'NOT_GRANTED':
            raise ValueError('MANIFEST_SCHEMA')
        declared = manifest['files']
        if not isinstance(declared,dict) or len(declared) > files.MAX_FILES:raise ValueError('MANIFEST_FILES')
        actual = {r['name']:r for r in members}; expected = {'V1/catalog.json'}; decisions = {}
        for path,raw in content.items():
            if path == 'V1/catalog.json':continue
            receipt = records.strict(raw)
            if not re.fullmatch('[a-f0-9]{32}',receipt['item']) or path != 'V1/decisions/'+receipt['item']+'.json':
                raise ValueError('DECISION_IDENTITY')
            if receipt['id'] in decisions:raise ValueError('DECISION_DUPLICATE')
            decisions[receipt['id']] = (path,receipt)
        missing = []; dependency_issues = 0
        for path,row in declared.items():
            if type(row['bytes']) is not int or not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('MANIFEST_ENTRY')
            canonical = name(path)
            if canonical != path:raise ValueError('MANIFEST_NONCANONICAL_PATH')
            original = 'V1/originals/'+path; found = actual.get(original)
            if not found or found['sha256'] != row['sha256'] or found['bytes'] != row['bytes']:
                raise ValueError('MANIFEST_ORIGINAL_BYTES')
            decision_path, receipt = decisions[row['decision']]
            if receipt['input_sha256'] != row['sha256'] or receipt['decision'] != 'ACCEPTED':raise ValueError('DECISION_INPUT')
            expected.update((original,decision_path))
            for dep in receipt['assessment']['dependencies']:
                counterpart = declared.get(dep['path'])
                if not counterpart or counterpart['sha256'] != dep.get('sha256') or counterpart['decision'] != dep.get('decision'):
                    dependency_issues += 1
                    if len(missing) < 100:missing.append(dep['path'])
        if set(actual) != expected:raise ValueError('MANIFEST_EXACT_MEMBER_SET')
        return {**base,'state':'VERIFIED' if not dependency_issues else 'MISSING_DEPENDENCIES',
                'dependencies':'COMPLETE' if not dependency_issues else 'MISSING_OR_CHANGED',
                'missing':missing,'missing_count':dependency_issues,'declared_files':len(declared),
                'encryption_declared':manifest.get('encryption','NOT_DECLARED')}
    except (ValueError,KeyError,TypeError,AttributeError,RecursionError):
        return {**base,'state':'INVALID','dependencies':'NOT_ESTABLISHED'}
