"""Inspect self-contained SVG and hand reviewed work to Inkscape."""

from __future__ import annotations

import hashlib
import io
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from threading import Thread
from uuid import uuid4
from xml.etree import ElementTree as ET

from . import edit_storage, files_service, record_io


PREFIX = 'programs.inkscape.'
INSPECT = PREFIX + 'inspect'
EXPORT = PREFIX + 'export'
OPEN = PREFIX + 'open'
PATH = {**files_service.REL, 'minLength': 1}
BOUND = {'path': PATH, 'expected_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$', 'maxLength': 64}}
FIELDS = {
    INSPECT: ({'path': PATH}, ['path']),
    EXPORT: ({**BOUND, 'destination': PATH}, [*BOUND, 'destination']),
    OPEN: (BOUND, list(BOUND)),
}
SCOPES = {INSPECT: 'read', EXPORT: 'approve', OPEN: 'approve'}
SOURCE_LIMIT = 1024 * 1024
ELEMENT_LIMIT = 4096
DEPTH_LIMIT = 48
PNG_EDGE = 1024
PNG_LIMIT = 5 * 1024 * 1024
SVG = '{http://www.w3.org/2000/svg}'
INKSCAPE = '{http://www.inkscape.org/namespaces/inkscape}'
SODIPODI = '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}'
ELEMENTS = frozenset(
    'svg g defs title desc path rect circle ellipse line polyline polygon text tspan '
    'linearGradient radialGradient stop pattern'.split()
)
GEOMETRY = frozenset(
    'id class version width height viewBox preserveAspectRatio x y x1 y1 x2 y2 cx cy fx fy fr '
    'r rx ry d points transform textLength lengthAdjust dx dy rotate offset gradientUnits '
    'gradientTransform spreadMethod patternUnits patternContentUnits patternTransform'.split()
)
PRESENTATION = frozenset(
    'fill fill-opacity fill-rule stroke stroke-opacity stroke-width stroke-linecap stroke-linejoin '
    'stroke-miterlimit stroke-dasharray stroke-dashoffset opacity color stop-color stop-opacity '
    'font-family font-size font-style font-weight font-variant font-stretch letter-spacing word-spacing '
    'text-anchor dominant-baseline alignment-baseline baseline-shift paint-order display visibility '
    'shape-rendering vector-effect'.split()
)
META = frozenset(
    {INKSCAPE + key for key in ('version', 'label', 'groupmode')}
    | {SODIPODI + 'docname', '{http://www.w3.org/XML/1998/namespace}space'}
)
NAMEDVIEW = frozenset(
    {'id', 'pagecolor', 'bordercolor', 'borderopacity', 'showgrid', 'showguides', 'units'}
    | {INKSCAPE + key for key in (
        'current-layer', 'document-units', 'pageopacity', 'pageshadow', 'pagecheckerboard',
        'deskcolor', 'showpageshadow', 'showborder', 'window-maximized', 'window-x',
        'window-y', 'window-width', 'window-height', 'zoom', 'cx', 'cy',
    )}
)
LOCAL_PAINT = re.compile(r'url\(\s*#([A-Za-z_][A-Za-z0-9_.:-]*)\s*\)', re.IGNORECASE)
SAFE_WORDS = re.compile(r"""[\w \t.,%#+\-'"]+""")
SAFE_COLOR = re.compile(r'(?:rgb|rgba|hsl|hsla)\([\d.% ,+\-]+\)', re.IGNORECASE)
LENGTH = re.compile(r'(\d+(?:\.\d*)?|\.\d+)(px|mm|cm|in|pt|pc|q)?')
UNIT_PX = {None: 1, 'px': 1, 'mm': 96 / 25.4, 'cm': 96 / 2.54,
           'in': 96, 'pt': 96 / 72, 'pc': 16, 'q': 96 / 101.6}


class UnsupportedSVG(ValueError):
    """Valid XML with features outside the room's self-contained subset."""


class SVGTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.elements = 0
        self.depth = 0

    def start(self, tag, attributes):
        self.elements += 1
        self.depth += 1
        if self.elements > ELEMENT_LIMIT or self.depth > DEPTH_LIMIT:
            raise ValueError('The SVG exceeds the room’s element or nesting limit.')
        return super().start(tag, attributes)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)

    def doctype(self, name, pubid, system):
        raise ValueError('SVG document types and entities are unavailable in the vector room.')

    def pi(self, target, text):
        raise ValueError('SVG processing instructions are unavailable in the vector room.')


def _path(base, name, suffix, must_exist=True):
    if Path(name).suffix.lower() != suffix:
        raise ValueError(f'Choose a {suffix} path inside Graphite Files.')
    try:
        return record_io.project_path(base, name, must_exist=must_exist)
    except RuntimeError as error:
        raise ValueError('Choose a path without linked folders or files.') from error


def _read(base, name):
    path = _path(base, name, '.svg')
    with edit_storage.parent(base, name) as (folder, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=folder)
        try:
            sink = io.BytesIO()
            identity = edit_storage.fingerprint_fd(fd, sink, SOURCE_LIMIT)
        finally:
            os.close(fd)
    return path, sink.getvalue(), identity


def _dimension(raw, fallback):
    if raw is None and fallback is not None:
        value = fallback
    else:
        match = LENGTH.fullmatch((raw or '').strip())
        if match is None:
            raise UnsupportedSVG('Set an absolute page width and height or supply a viewBox.')
        value = float(match[1]) * UNIT_PX[match[2]]
    if not math.isfinite(value) or not 0 < value <= 1_000_000:
        raise UnsupportedSVG('The SVG page dimensions are outside the room’s bounds.')
    return value


def _size(root):
    view_box = root.get('viewBox', '')
    try:
        dimensions = tuple(float(x) for x in re.split(r'[ ,\t\r\n]+', view_box.strip())) if view_box else ()
    except ValueError as error:
        raise UnsupportedSVG('Set a valid viewBox before rendering.') from error
    if dimensions and (len(dimensions) != 4 or not all(math.isfinite(x) for x in dimensions)
                       or min(dimensions[2:]) <= 0):
        raise UnsupportedSVG('Set a valid viewBox before rendering.')
    width = _dimension(root.get('width'), dimensions[2] if dimensions else None)
    height = _dimension(root.get('height'), dimensions[3] if dimensions else None)
    if max(width, height) / min(width, height) > PNG_EDGE:
        raise UnsupportedSVG('The page aspect ratio is too extreme for a bounded PNG.')
    return width, height


def _paint(key, value, references, inside_pattern):
    match = LOCAL_PAINT.fullmatch(value)
    if match and key in ('fill', 'stroke') and not inside_pattern:
        references.add(match[1])
    elif not (SAFE_WORDS.fullmatch(value) or SAFE_COLOR.fullmatch(value)):
        raise UnsupportedSVG('Use ordinary paint and font values or a local paint reference.')


def _style(value, references, inside_pattern):
    for declaration in value.split(';'):
        if not declaration.strip():
            continue
        name, _, setting = declaration.partition(':')
        key = name.strip().lower()
        if key not in PRESENTATION:
            raise UnsupportedSVG('This inline CSS property is outside the vector room’s supported subset.')
        _paint(key, setting.strip(), references, inside_pattern)


def _review_tree(root):
    references = set()
    paint_ids = set()
    identifiers = set()
    stack = [(root, None, False)]
    while stack:
        node, parent, inside_pattern = stack.pop()
        # An ordinary namedview controls editor zoom and guides. It has no PNG content.
        if (node.tag == SODIPODI + 'namedview' and parent is root and not len(node)
                and node.attrib.keys() <= NAMEDVIEW):
            continue
        tag = node.tag.removeprefix(SVG)
        if not node.tag.startswith(SVG) or tag not in ELEMENTS or (tag == 'svg' and node is not root):
            raise UnsupportedSVG(f'The vector room cannot render the {tag.rsplit("}", 1)[-1][:40]} element.')
        if tag == 'defs' and parent is not root:
            raise UnsupportedSVG('Keep paint definitions directly under the SVG root.')
        if tag == 'pattern' and (parent is None or parent.tag != SVG + 'defs'):
            raise UnsupportedSVG('Keep paint patterns inside the SVG definitions.')
        inside_pattern = inside_pattern or tag == 'pattern'
        ident = node.get('id')
        if ident:
            if ident in identifiers:
                raise UnsupportedSVG('SVG identifiers must be unique.')
            identifiers.add(ident)
            if tag in ('linearGradient', 'radialGradient', 'pattern'):
                paint_ids.add(ident)
        for key, value in node.attrib.items():
            if key in GEOMETRY or key in META:
                continue
            if key == 'style':
                _style(value, references, inside_pattern or tag in ('svg', 'defs'))
            elif key in PRESENTATION:
                _paint(key, value.strip(), references, inside_pattern or tag in ('svg', 'defs'))
            else:
                raise UnsupportedSVG('The SVG contains attributes outside the self-contained drawing subset.')
        stack.extend((child, node, inside_pattern) for child in node)
    if not references <= paint_ids:
        raise UnsupportedSVG('A paint reference points outside the SVG’s supported local definitions.')


def _inspect(raw, name, identity, executable):
    tree = SVGTree()
    try:
        root = ET.fromstring(raw, parser=ET.XMLParser(target=tree))
    except (ET.ParseError, LookupError) as error:
        raise ValueError('This file is not a readable SVG document.') from error
    if root.tag != SVG + 'svg':
        raise ValueError('Choose a document with an SVG root element.')
    result = {'state': 'READY', 'path': name, 'sha256': identity['sha256'], 'bytes': identity['bytes'],
              'width': root.get('width'), 'height': root.get('height'), 'view_box': root.get('viewBox'),
              'elements': tree.elements, 'tool': {'name': 'Inkscape', 'available': bool(executable)},
              'render_ready': False, 'reason': ''}
    try:
        size = _size(root)
        result['width'], result['height'] = size
        _review_tree(root)
    except UnsupportedSVG as error:
        return root, {**result, 'state': 'UNSUPPORTED', 'reason': str(error)}
    if not executable:
        return root, {**result, 'state': 'TOOL_UNAVAILABLE', 'reason': 'Install Inkscape to render or edit this SVG.'}
    result['render_ready'] = True
    return root, result


def _render(executable, root, width, height):
    scale = min(1, PNG_EDGE / max(width, height))
    pixels = tuple(max(1, round(edge * scale)) for edge in (width, height))
    with tempfile.TemporaryDirectory(prefix='graphite-vector-') as scratch:
        temporary = Path(scratch)
        source = temporary / 'source.svg'
        output = temporary / 'render.png'
        # Re-serialize the reviewed XML so the renderer never sees a second reading of the source
        # or any original declaration. Omit the editor's non-drawing metadata from this export.
        for node in list(root):
            if node.tag == SODIPODI + 'namedview':
                root.remove(node)
        source.write_bytes(ET.tostring(root, encoding='utf-8', default_namespace=None))
        env = {**os.environ, 'INKSCAPE_PROFILE_DIR': str(temporary / 'profile'), 'XDG_CONFIG_HOME': scratch}
        command = [executable, f'--app-id-tag=Graphite{uuid4().hex}',
                   '--export-area-page', f'--export-width={pixels[0]}',
                   f'--export-height={pixels[1]}', f'--export-filename={output}', str(source)]
        try:
            result = subprocess.run(command, cwd=temporary, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12, check=False)
        except subprocess.TimeoutExpired as error:
            raise ValueError('Inkscape did not finish the bounded PNG render in time.') from error
        if result.returncode or not output.is_file() or output.stat().st_size > PNG_LIMIT:
            raise ValueError('Inkscape did not produce a bounded PNG.')
        data = output.read_bytes()
    if (len(data) < 45 or data[:16] != b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR'
            or data[-12:] != b'\0\0\0\0IEND\xaeB`\x82'):
        raise ValueError('Inkscape returned an unreadable PNG.')
    actual = struct.unpack('>II', data[16:24])
    if actual != pixels:
        raise ValueError('Inkscape returned unexpected PNG dimensions.')
    return data, actual


def _publish(base, name, data):
    with edit_storage.parent(base, name) as (directory, leaf):
        stage = '.vector-' + uuid4().hex
        fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            with edit_storage.parent(base, name) as (current, _):
                if not os.path.samestat(os.fstat(current), os.fstat(directory)):
                    raise ValueError('The output folder changed during export.')
            try:
                os.link(stage, leaf, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            except FileExistsError as error:
                raise ValueError('Choose a fresh PNG path. The existing file is unchanged.') from error
        finally:
            os.unlink(stage, dir_fd=directory)
        os.fsync(directory)


def _open_native(executable, path, name, digest):
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise ValueError('Open the Graphite desktop session to hand this file to Inkscape.')
    process = subprocess.Popen([executable, str(path)], cwd=path.parent, start_new_session=True,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if process.wait(timeout=0.15):
            raise ValueError('Inkscape refused the desktop handoff.')
    except subprocess.TimeoutExpired:
        Thread(target=process.wait, daemon=True).start()
    return {'state': 'STARTED', 'path': name, 'sha256': digest, 'pid': process.pid}


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS or SCOPES[operation] not in principal.scopes:
        raise ValueError('Vector operation is outside the authorized scope.')
    if operation != INSPECT and (principal.identity != 'desktop-owner' or 'read' not in principal.scopes):
        raise ValueError('A native vector action needs desktop owner approval.')
    base = files_service.root(kernel, create=False).absolute()
    name = args['path']
    path, raw, identity = _read(base, name)
    executable = shutil.which('inkscape')
    root, inspected = _inspect(raw, name, identity, executable)
    if operation == INSPECT:
        return inspected
    digest = identity['sha256']
    if args['expected_sha256'] != digest:
        raise ValueError('The SVG changed since inspection. Inspect it again.')
    if not inspected['render_ready']:
        raise ValueError(inspected['reason'])
    if operation == OPEN:
        return _open_native(executable, path, name, digest)
    destination = args['destination']
    if _path(base, destination, '.png', must_exist=False).exists():
        raise ValueError('Choose a fresh PNG path. The existing file is unchanged.')
    data, (width, height) = _render(executable, root, inspected['width'], inspected['height'])
    _publish(base, destination, data)
    return {'state': 'EXPORTED', 'path': destination, 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'source_sha256': digest, 'width': width, 'height': height}
