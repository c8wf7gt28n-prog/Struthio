"""Inspect local messages and prepare files for review in the Graphite workbench."""

from email import policy
from email.errors import MessageError
from email.message import EmailMessage
from email.parser import BytesParser
import hashlib
from itertools import islice
import os
import re
import shutil
import stat
import subprocess
from threading import Thread
import uuid

from . import edit_storage, files_service, record_io


MAX_MESSAGE = 16 * 1024 * 1024
MAX_BODY = 24_000
MAX_PARTS = 256
MAX_ATTACHMENTS = 32
MAX_HEADER = 1_024
MESSAGE_ID = re.compile(r'<[^<>\s\x00-\x1f\x7f]+@[^<>\s\x00-\x1f\x7f]+>')
TRANSFER_ENCODINGS = {'7bit', '8bit', 'binary', 'base64', 'quoted-printable'}
PATH = {**files_service.REL, 'minLength': 1}
BOUND_SOURCE = {
    'path': PATH,
    'expected_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64},
}
SOURCE = {**BOUND_SOURCE, 'destination': PATH}
FIELDS = {
    'programs.mail.inspect': ({'path': PATH}, ['path']),
    'programs.mail.extract': (
        {**SOURCE, 'index': {'type': 'integer', 'minimum': 0, 'maximum': MAX_ATTACHMENTS - 1}},
        [*SOURCE, 'index'],
    ),
    'programs.mail.draft': (
        {**SOURCE, 'body': {'type': 'string', 'minLength': 1, 'maxLength': MAX_BODY}},
        [*SOURCE, 'body'],
    ),
    'programs.mail.open': (BOUND_SOURCE, list(BOUND_SOURCE)),
}
SCOPES = {op: 'read' if op == 'programs.mail.inspect' else 'approve' for op in FIELDS}


def _path(base, name, must_exist=True):
    try:
        return record_io.project_path(base, name, must_exist=must_exist)
    except RuntimeError as error:
        raise ValueError('MAIL_LINKED_PATH') from error


def _read_message(base, name):
    path = _path(base, name)
    if path.suffix.lower() != '.eml':
        raise ValueError('MAIL_EML_REQUIRED')
    with edit_storage.parent(base, name) as (directory, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_MESSAGE:
                raise ValueError('MAIL_SOURCE_SIZE_OR_TYPE')
            raw = stream.read(MAX_MESSAGE + 1)
            after = os.fstat(stream.fileno())
    if len(raw) > MAX_MESSAGE or len(raw) != before.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise ValueError('MAIL_SOURCE_CHANGED_DURING_READ')
    if not raw:
        raise ValueError('MAIL_EMPTY_MESSAGE')
    return raw


def _header(message, name):
    value = str(message.get(name, ''))
    return ' '.join(value.split())[:MAX_HEADER]


def _attachments(message):
    # Treat an attached email or multipart document as one item, without inspecting its descendants.
    pending = [message]
    count = 0
    attachments = []
    while pending:
        part = pending.pop()
        count += 1
        if count > MAX_PARTS:
            raise ValueError('MAIL_MIME_PART_LIMIT')
        if part.get_content_disposition() == 'attachment' or part.get_filename() is not None:
            if len(attachments) >= MAX_ATTACHMENTS:
                raise ValueError('MAIL_ATTACHMENT_LIMIT')
            encodings = part.get_all('Content-Transfer-Encoding', ['7bit'])
            encoding = str(encodings[0]).strip().lower()
            content = part.get_payload(decode=True) if len(encodings) == 1 and encoding in TRANSFER_ENCODINGS else None
            if part.defects:
                content = None
            attachments.append(({
                'index': len(attachments),
                'name': part.get_filename('unnamed attachment')[:MAX_HEADER],
                'content_type': part.get_content_type(),
                'bytes': len(content) if content is not None else None,
                'extractable': content is not None,
            }, content))
        elif part.is_multipart():
            pending.extend(reversed(list(islice(part.iter_parts(), MAX_PARTS + 1))))
    return attachments


def _body(message):
    part = message.get_body(preferencelist=('plain',))
    if part is None:
        state = 'HTML_ONLY' if message.get_body(preferencelist=('html',)) else 'NO_PLAIN_TEXT'
        return {'body': '', 'body_state': state, 'body_truncated': False}
    payload = part.get_payload(decode=True)
    encoding = part.get_content_charset() or 'ascii'
    try:
        value = payload.decode(encoding, errors='replace') if payload is not None else ''
    except (LookupError, UnicodeError):
        value = payload.decode('utf-8', errors='replace')
    return {'body': value[:MAX_BODY], 'body_state': 'PLAIN_TEXT', 'body_truncated': len(value) > MAX_BODY}


def _reply(source, body):
    if not isinstance(body, str) or not body.strip() or len(body) > MAX_BODY or '\x00' in body:
        raise ValueError('MAIL_REPLY_TEXT_REQUIRED')
    recipients = source.get_all('Reply-To') if 'Reply-To' in source else source.get_all('From', [])
    if len(recipients) != 1:
        raise ValueError('MAIL_REPLY_RECIPIENT_UNAVAILABLE')
    address_header = recipients[0]
    addresses = getattr(address_header, 'addresses', ())
    if (not addresses or len(addresses) > 10 or address_header.defects
            or any(not address.username or not address.domain for address in addresses)):
        raise ValueError('MAIL_REPLY_RECIPIENT_UNAVAILABLE')
    draft = EmailMessage(policy=policy.SMTP)
    draft['To'] = addresses
    subject = _header(source, 'Subject')
    draft['Subject'] = subject if subject.casefold().startswith('re:') else 'Re: ' + (subject or '(no subject)')
    message_id = _header(source, 'Message-ID')
    if MESSAGE_ID.fullmatch(message_id):
        draft['In-Reply-To'] = message_id
        ancestors = MESSAGE_ID.findall(_header(source, 'References'))[-10:]
        draft['References'] = ' '.join(dict.fromkeys([*ancestors, message_id]))
    draft['X-Unsent'] = '1'
    draft.set_content(body)
    return draft.as_bytes(), str(draft['To']), str(draft['Subject'])


def _publish(base, name, content):
    _path(base, name, must_exist=False)
    with edit_storage.parent(base, name) as (directory, leaf):
        staged = '.graphite-mail-' + uuid.uuid4().hex
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(staged, leaf, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        except FileExistsError as error:
            raise ValueError('MAIL_DESTINATION_ALREADY_EXISTS') from error
        finally:
            os.unlink(staged, dir_fd=directory)
        os.fsync(directory)
    return {'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}


def _tool(executable):
    return {'name': 'Thunderbird', 'available': executable is not None,
            'reason': '' if executable else 'Install Thunderbird to open this message in the full mail program.'}


def _open_native(base, name, digest):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise ValueError('Open the Graphite desktop session to hand this file to Thunderbird.')
    executable = shutil.which('thunderbird')
    tool = _tool(executable)
    if executable is None:
        raise ValueError(tool['reason'])
    path = _path(base, name)
    process = subprocess.Popen([executable, '-file', str(path)], cwd=path.parent,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        if process.wait(timeout=0.15):
            raise ValueError('Thunderbird rejected the file handoff.')
    except subprocess.TimeoutExpired:
        Thread(target=process.wait, daemon=True).start()
    # A launcher may pass the file to a Thunderbird window that is already running.
    return {'state': 'STARTED', 'pid': process.pid, 'path': name, 'sha256': digest, 'tool': tool}


def dispatch(kernel, op, args, principal):
    if SCOPES[op] not in principal.scopes:
        raise ValueError('MAIL_SCOPE_REQUIRED')
    if op == 'programs.mail.open' and (principal.identity != 'desktop-owner' or 'read' not in principal.scopes):
        raise ValueError('Opening Thunderbird requires desktop owner approval.')
    base = files_service.root(kernel, create=False).absolute()
    if base.is_symlink():
        raise ValueError('MAIL_LINKED_PATH')
    raw = _read_message(base, args['path'])
    digest = hashlib.sha256(raw).hexdigest()
    if op != 'programs.mail.inspect' and args['expected_sha256'] != digest:
        raise ValueError('MAIL_SOURCE_CHANGED: inspect the source again')
    if op == 'programs.mail.open':
        return _open_native(base, args['path'], digest)
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
        if op == 'programs.mail.draft':
            if not args['destination'].lower().endswith('.eml'):
                raise ValueError('MAIL_DRAFT_EML_REQUIRED')
            content, recipient, subject = _reply(message, args['body'])
            return {'state': 'DRAFT_SAVED', 'to': recipient, 'subject': subject, 'source_sha256': digest,
                    **_publish(base, args['destination'], content)}
        attachments = _attachments(message)
        if op == 'programs.mail.extract':
            index = args['index']
            if type(index) is not int or not 0 <= index < len(attachments):
                raise ValueError('MAIL_ATTACHMENT_INDEX_UNAVAILABLE')
            _, content = attachments[index]
            if content is None:
                raise ValueError('MAIL_ATTACHMENT_ENCODING_UNSUPPORTED')
            return {'state': 'EXTRACTED', 'source_sha256': digest,
                    **_publish(base, args['destination'], content)}
        return {
            'schema': 'graphite.programs.mail/1', 'state': 'READY', 'path': args['path'], 'sha256': digest,
            'subject': _header(message, 'Subject'), 'from': _header(message, 'From'),
            'to': _header(message, 'To'), 'date': _header(message, 'Date'),
            'message_id': _header(message, 'Message-ID'), **_body(message),
            'attachments': [metadata for metadata, _ in attachments], 'tool': _tool(shutil.which('thunderbird')),
        }
    except (MessageError, RecursionError, UnicodeError) as error:
        raise ValueError('MAIL_MIME_UNREADABLE') from error
