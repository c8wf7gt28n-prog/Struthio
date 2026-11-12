"""Create a review-only print proof from a selected local PNG."""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import PurePosixPath
import struct
import textwrap
from uuid import uuid4

from . import edit_storage, files_service, record_io


INSPECT = 'programs.print.inspect'
EXPORT = 'programs.print.export'
PAPERS = {'Letter': (612, 792), 'A4': (595.276, 841.89)}
PATH = {**files_service.REL, 'minLength': 1}
FIELDS = {
    INSPECT: ({'path': PATH}, ['path']),
    EXPORT: ({
        'path': PATH,
        'expected_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$', 'maxLength': 64},
        'destination': PATH,
        'title': {'type': 'string', 'minLength': 1, 'maxLength': 80},
        'paper': {'type': 'string', 'enum': list(PAPERS)},
    }, ['path', 'expected_sha256', 'destination', 'title', 'paper']),
}
SCOPES = {INSPECT: 'read', EXPORT: 'approve'}
PNG_LIMIT = 8 * 1024 * 1024
PIXEL_LIMIT = 4 * 1024 * 1024
EDGE_LIMIT = 4096
PNG_HEADER = b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR'
PNG_END = b'\0\0\0\0IEND\xaeB`\x82'


def _path(base, name, suffix, must_exist=True):
    if PurePosixPath(name).suffix.lower() != suffix:
        raise ValueError(f'Choose a {suffix} path inside Graphite Files.')
    try:
        return record_io.project_path(base, name, must_exist=must_exist)
    except RuntimeError as error:
        raise ValueError('Choose a path without linked folders or files.') from error


def _source(base, name):
    _path(base, name, '.png')
    with edit_storage.parent(base, name) as (folder, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=folder)
        try:
            data = io.BytesIO()
            identity = edit_storage.fingerprint_fd(fd, data, PNG_LIMIT)
        finally:
            os.close(fd)
    return data.getvalue(), identity


def _inspect(raw, name, identity):
    summary = {'state': 'UNSUPPORTED', 'path': name, 'sha256': identity['sha256'],
               'bytes': identity['bytes'], 'width': None, 'height': None,
               'tool': {'name': 'Graphite PDF proof', 'available': False}, 'print_ready': False}
    try:
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        from PySide6.QtGui import QImageReader
        from pypdf import PdfWriter  # noqa: F401  (report the writer's availability with the decoder's)
    except ImportError:
        return None, {**summary, 'state': 'TOOL_UNAVAILABLE',
                      'reason': 'Print Proof needs Graphite’s Qt PNG decoder and PDF writer.'}
    summary['tool']['available'] = True
    if len(raw) < 45 or not raw.startswith(PNG_HEADER) or not raw.endswith(PNG_END):
        return None, {**summary, 'reason': 'Choose a complete PNG image.'}
    width, height = struct.unpack_from('>II', raw, 16)
    summary.update(width=width, height=height)
    if not (0 < min(width, height) <= max(width, height) <= EDGE_LIMIT
            and width * height <= PIXEL_LIMIT):
        return None, {**summary, 'reason': 'The PNG exceeds the print proof’s pixel bounds.'}
    payload = QByteArray(raw)
    buffer = QBuffer(payload)
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer, QByteArray(b'png'))
    reader.setAutoDetectImageFormat(False)
    reader.setDecideFormatFromContent(False)
    image = reader.read()
    if image.isNull() or (image.width(), image.height()) != (width, height):
        return None, {**summary, 'reason': 'The PNG could not be decoded at its stated dimensions.'}
    return image, {**summary, 'state': 'READY', 'print_ready': True, 'reason': ''}


def _rgb(image):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColorSpace, QImage, QPainter

    if image.colorSpace().isValid():
        image.convertToColorSpace(QColorSpace(QColorSpace.NamedColorSpace.SRgb))
    result = QImage(image.width(), image.height(), QImage.Format.Format_RGB888)
    if result.isNull():
        raise ValueError('The PNG could not be prepared for a print proof.')
    result.fill(Qt.GlobalColor.white)
    painter = QPainter(result)
    try:
        painter.drawImage(0, 0, image)
    finally:
        painter.end()
    pixels = result.constBits()
    stride = result.bytesPerLine()
    return b''.join(pixels[at:at + image.width() * 3] for at in range(0, len(pixels), stride))


def _title(value):
    title = value.strip()
    if not title or len(title) > 80 or not title.isprintable():
        raise ValueError('Enter a one-line title of up to 80 printable characters.')
    try:
        title.encode('latin-1')
    except UnicodeEncodeError as error:
        raise ValueError('Use Latin-1 characters in the print proof title.') from error
    return title


def _pdf(image, title, paper, digest):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

    writer = PdfWriter()
    width, height = PAPERS[paper]
    page = writer.add_blank_page(width=width, height=height)

    def named(**fields):
        return DictionaryObject({NameObject('/' + key): NameObject('/' + value) for key, value in fields.items()})

    raster = DecodedStreamObject()
    raster.set_data(_rgb(image))
    raster.update(named(Type='XObject', Subtype='Image', ColorSpace='DeviceRGB'))
    raster[NameObject('/Width')] = NumberObject(image.width())
    raster[NameObject('/Height')] = NumberObject(image.height())
    raster[NameObject('/BitsPerComponent')] = NumberObject(8)
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({
            NameObject('/Mono'): named(Type='Font', Subtype='Type1', BaseFont='Courier', Encoding='WinAnsiEncoding'),
            NameObject('/Bold'): named(Type='Font', Subtype='Type1', BaseFont='Courier-Bold', Encoding='WinAnsiEncoding'),
        }),
        NameObject('/XObject'): DictionaryObject({NameObject('/Artwork'): writer._add_object(raster.flate_encode())}),
    })

    def text(words, x, y, size, font='Mono'):
        # Hexadecimal PDF strings keep user title bytes out of the instruction syntax.
        return f'BT /{font} {size} Tf {x:.2f} {y:.2f} Td <{words.encode("latin-1").hex()}> Tj ET'

    margin = 42
    content_width = width - 2 * margin
    title_lines = textwrap.wrap(title, width=int(content_width / (21 * .6)))
    label_y = height - 106 - 24 * (len(title_lines) - 1)
    image_top = label_y - 24
    image_bottom = 105
    scale = min(content_width / image.width(), (image_top - image_bottom) / image.height())
    draw_width, draw_height = image.width() * scale, image.height() * scale
    x = (width - draw_width) / 2
    y = (image_top + image_bottom - draw_height) / 2
    commands = [
        '0.11 0.15 0.13 rg',
        text('GRAPHITE / PRINT PROOF', margin, height - 43, 10, 'Bold'),
        text(paper.upper(), width - margin - len(paper) * 6, height - 43, 10),
        f'0.72 0.30 0.09 RG 1.1 w {margin} {height - 53} m {width - margin:.2f} {height - 53} l S',
    ]
    commands.extend(text(line, margin, height - 83 - 24 * index, 21, 'Bold')
                    for index, line in enumerate(title_lines))
    commands.extend([
        text('FIT-TO-PAGE REVIEW PROOF', margin, label_y, 10, 'Bold'),
        f'q {draw_width:.3f} 0 0 {draw_height:.3f} {x:.3f} {y:.3f} cm /Artwork Do Q',
        f'0.58 0.60 0.58 RG 0.45 w {x:.3f} {y:.3f} {draw_width:.3f} {draw_height:.3f} re S',
        text(f'SOURCE RASTER  {image.width()} x {image.height()} px', margin, 78, 9),
        text('SOURCE SHA-256', margin, 64, 9, 'Bold'),
        text(digest, margin, 50, 9),
        text('01 / 01', width - margin - 7 * 5.4, 50, 9),
    ])
    contents = DecodedStreamObject()
    contents.set_data('\n'.join(commands).encode('ascii'))
    page.replace_contents(contents.flate_encode())
    writer.add_metadata({'/Title': title, '/Producer': 'Graphite Print Proof'})
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _publish(base, destination, data):
    _path(base, destination, '.pdf', must_exist=False)
    with edit_storage.parent(base, destination) as (directory, leaf):
        stage = '.graphite-print-' + uuid4().hex
        fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            with edit_storage.parent(base, destination) as (current, _):
                if not os.path.samestat(os.fstat(current), os.fstat(directory)):
                    raise ValueError('The output folder changed during export.')
            try:
                edit_storage.rename_linux(directory, stage, leaf)
            except FileExistsError as error:
                raise ValueError('Choose a fresh PDF path. The existing file is unchanged.') from error
        finally:
            try:
                os.unlink(stage, dir_fd=directory)
            except FileNotFoundError:
                pass


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS or SCOPES[operation] not in principal.scopes:
        raise ValueError('Print Proof operation is outside the authorized scope.')
    if operation == EXPORT and (principal.identity != 'desktop-owner' or 'read' not in principal.scopes):
        raise ValueError('Saving a print proof needs desktop owner approval.')
    base = files_service.root(kernel, create=False).absolute()
    name = args['path']
    raw, identity = _source(base, name)
    digest = identity['sha256']
    if operation == EXPORT and args['expected_sha256'] != digest:
        raise ValueError('The PNG changed since inspection. Inspect it again.')
    image, inspected = _inspect(raw, name, identity)
    if operation == INSPECT:
        return inspected
    if not inspected['print_ready']:
        raise ValueError(inspected['reason'])
    destination = args['destination']
    if _path(base, destination, '.pdf', must_exist=False).exists():
        raise ValueError('Choose a fresh PDF path. The existing file is unchanged.')
    title = _title(args['title'])
    paper = args['paper']
    data = _pdf(image, title, paper, digest)
    _publish(base, destination, data)
    return {'state': 'EXPORTED', 'path': destination, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'paper': paper, 'source_sha256': digest,
            'width': inspected['width'], 'height': inspected['height']}
