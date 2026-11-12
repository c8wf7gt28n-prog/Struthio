"""Read-only, anonymous FTP through the host's curl, with a bounded Files handoff."""

import hashlib
import io
import os
import re
import shutil
import subprocess
from threading import Timer
import unicodedata
from urllib.parse import unquote_to_bytes, urlsplit
from uuid import uuid4

from . import edit_storage, files_service


PREFIX = 'programs.transfer.'
LIST_BYTES = 64 * 1024
LIST_ENTRIES = 256
DOWNLOAD_BYTES = 16 * 1024 * 1024
TRANSFER_SECONDS = 20
SFTP_REASON = 'SFTP needs a configured account and a trusted host key. Transfer does not configure those yet.'
URL = {'type': 'string', 'minLength': 1, 'maxLength': 2048}
FIELDS = {
    PREFIX + 'status': ({}, []),
    PREFIX + 'list': ({'url': URL}, ['url']),
    PREFIX + 'download': ({'url': URL, 'destination': files_service.REL}, ['url', 'destination']),
}
SCOPES = {operation: 'read' if operation.endswith('.status') else 'approve' for operation in FIELDS}


def ftp_curl():
    curl = shutil.which('curl')
    if not curl:
        return None, 'Install curl on this host to use FTP.'
    try:
        result = subprocess.run([curl, '--disable', '--version'], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, errors='replace', timeout=3, check=True)
    except (OSError, subprocess.SubprocessError):
        return None, 'Graphite could not check this host’s curl.'
    protocols = next((line.split()[1:] for line in result.stdout.splitlines() if line.startswith('Protocols:')), ())
    if 'ftp' not in protocols:
        return None, 'This host’s curl has no FTP support.'
    return curl, None


def ftp_url(value, directory):
    if not 1 <= len(value) <= URL['maxLength'] or any(not 33 <= ord(ch) <= 126 for ch in value):
        raise ValueError('Enter an exact FTP URL. Use percent escapes for spaces and non-ASCII characters.')
    if any(ch in value for ch in '\\?#{}') or re.search(r'%(?![0-9a-fA-F]{2})', value):
        raise ValueError('FTP URLs cannot contain a query, fragment, backslash, or malformed percent escape.')
    try:
        url = urlsplit(value)
        host, port = url.hostname, url.port
    except ValueError:
        raise ValueError('Enter a valid FTP host and port.') from None
    if '@' in url.netloc:
        raise ValueError('Transfer accepts anonymous FTP URLs without credentials.')
    if url.scheme == 'sftp':
        raise ValueError(SFTP_REASON)
    if url.scheme != 'ftp' or not host or port == 0:
        raise ValueError('Enter an exact ftp:// URL.')
    authority = r'(?:[a-zA-Z0-9.-]+|\[[a-fA-F0-9:.]+\])(?::[0-9]+)?'
    if not re.fullmatch(authority, url.netloc):
        raise ValueError('Enter a valid FTP host and port.')
    path = url.path or '/'
    decoded = unquote_to_bytes(path)
    if (any(byte < 32 or byte == 127 for byte in decoded) or b'\\' in decoded or
            b';type=' in decoded.lower() or any(segment in (b'.', b'..') for segment in decoded.split(b'/'))):
        raise ValueError('Use a direct FTP path without control characters, type overrides, or dot segments.')
    if directory and not path.endswith('/'):
        raise ValueError('A directory URL must end in /.')
    if not directory and decoded.endswith(b'/'):
        raise ValueError('A download URL must name a remote file.')
    return value if url.path else value + '/'


def transfer(curl, url, sink, limit, directory=False):
    command = [curl, '--disable', '--silent', '--globoff', '--path-as-is', '--disallow-username-in-url',
               '--proto', '=ftp', '--proto-redir', '=ftp', '--max-redirs', '0', '--noproxy', '*',
               '--ftp-skip-pasv-ip', '--connect-timeout', '5', '--max-time', str(TRANSFER_SECONDS),
               '--user', 'anonymous:graphite@localhost']
    command += ['--list-only'] if directory else ['--max-filesize', str(limit)]
    command += ['--url', url]
    size = 0
    digest = hashlib.sha256()
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL) as process:
        watchdog = Timer(TRANSFER_SECONDS + 2, process.kill)
        watchdog.daemon = True
        watchdog.start()
        try:
            while chunk := process.stdout.read1(min(64 * 1024, limit - size + 1)):
                size += len(chunk)
                if size > limit:
                    raise ValueError('FTP transfer exceeded the Graphite size limit.')
                sink.write(chunk)
                digest.update(chunk)
            code = process.wait()
        finally:
            watchdog.cancel()
            if process.poll() is None:
                process.kill()
    if code == 63:
        raise ValueError('FTP transfer exceeded the Graphite size limit.')
    if code in (28, -9):
        raise ValueError('FTP transfer timed out.')
    if code:
        raise ValueError(f'FTP transfer did not finish (curl exit {code}).')
    return size, digest.hexdigest()


def list_directory(curl, url):
    with io.BytesIO() as output:
        transfer(curl, url, output, LIST_BYTES, directory=True)
        lines = output.getvalue().split(b'\n')
    entries = []
    seen = set()
    omitted = 0
    for line in lines:
        try:
            name = line.removesuffix(b'\r').decode('utf-8')
        except UnicodeDecodeError:
            omitted += 1
            continue
        if not name or name in ('.', '..') or name in seen:
            continue
        if len(name) > 255 or any(ch in '/\\' or unicodedata.category(ch).startswith('C') for ch in name):
            omitted += 1
            continue
        seen.add(name)
        if len(entries) < LIST_ENTRIES:
            entries.append({'name': name})
    return {'url': url, 'entries': entries, 'truncated': len(seen) > LIST_ENTRIES, 'omitted': omitted}


def download(kernel, curl, url, relative):
    if (any(part.startswith('.') for part in relative.split('/')) or
            any(unicodedata.category(ch).startswith('C') for ch in relative)):
        raise ValueError('Choose a fresh file name inside Files, with an existing parent folder.')
    try:
        edit_storage.relative(relative)
    except ValueError:
        raise ValueError('Choose a fresh file name inside Files, with an existing parent folder.') from None
    files_service.resolve(kernel, relative, must_exist=False)
    base = files_service.root(kernel).resolve()
    with edit_storage.parent(base, relative) as (folder, name):
        try:
            os.stat(name, dir_fd=folder, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('Choose a fresh Files path. Transfer never overwrites a file.')
        temporary = f'.transfer-{uuid4().hex}'
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=folder)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                size, digest = transfer(curl, url, stream, DOWNLOAD_BYTES)
                stream.flush()
                os.fsync(stream.fileno())
            with edit_storage.parent(base, relative) as (current_folder, _):
                if not os.path.samestat(os.fstat(folder), os.fstat(current_folder)):
                    raise ValueError('The destination folder changed during the transfer.')
            try:
                os.link(temporary, name, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
            except FileExistsError:
                raise ValueError('The destination appeared during the transfer. Its contents are unchanged.') from None
        finally:
            os.unlink(temporary, dir_fd=folder)
        os.fsync(folder)
    return {'state': 'RETRIEVED', 'url': url, 'path': relative, 'bytes': size, 'sha256': digest}


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS:
        raise ValueError('Unknown Transfer operation.')
    if SCOPES[operation] not in principal.scopes:
        raise ValueError('Transfer operation is outside the authorized scope.')
    curl, reason = ftp_curl()
    if operation == PREFIX + 'status':
        return {'available': bool(curl), 'ftp': bool(curl), 'sftp': False, 'reason': reason,
                'ftp_reason': reason, 'sftp_reason': SFTP_REASON, 'download_limit_bytes': DOWNLOAD_BYTES}
    directory = operation == PREFIX + 'list'
    url = ftp_url(args['url'], directory)
    if not curl:
        raise ValueError(reason)
    if directory:
        return list_directory(curl, url)
    return download(kernel, curl, url, args['destination'])
