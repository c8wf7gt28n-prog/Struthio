"""A bounded view of FreeCAD's saved geometry and an explicit native handoff."""

from __future__ import annotations

from io import BytesIO
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from uuid import uuid4
import xml.etree.ElementTree as ET
import zipfile

from . import edit_storage, files_service, program_build, record_io


PREFIX = 'programs.freecad.'
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
SOURCE = {'path': PATH}
BOUND = {**SOURCE, 'expected_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}
OBJECT = {**BOUND, 'object': {'type': 'string', 'minLength': 1, 'maxLength': 240}}
FIELDS = {
    PREFIX + 'inspect': (SOURCE, ['path']),
    PREFIX + 'check': (OBJECT, list(BOUND)),
    PREFIX + 'export': ({**OBJECT, 'destination': PATH}, [*BOUND, 'destination']),
    PREFIX + 'open': (BOUND, list(BOUND)),
}
SCOPES = {op: 'read' if op.endswith('.inspect') else 'approve' for op in FIELDS}

MAX_SOURCE = 64 * 1024**2
MAX_XML = 4 * 1024**2
MAX_BREP = 32 * 1024**2
MAX_EXPANDED = 256 * 1024**2
MAX_ENTRIES = 4096
MAX_SHAPES = 250
TIMEOUT = 18
EXPORT_LIMIT = 64 * 1024**2
EMBEDDED_SCRIPT = ('.py', '.pyc', '.pyo', '.fcmacro', '.fcmac', '.pyd', '.so')

# The console reads a plain saved BREP from its private working directory.
# Opening the project itself could restore scripted objects and is a separate owner action.
CHECK_SCRIPT = '''
import FreeCAD as App
import json
from pathlib import Path
import Part
import resource

resource.setrlimit(resource.RLIMIT_FSIZE, (67108864, 67108864))
shape = Part.Shape()
shape.read('stored.brep')
if shape.isNull():
    raise ValueError('Empty stored shape')
box = shape.BoundBox
valid = shape.isValid()
if Path('export-request').is_file() and valid:
    shape.exportStep('geometry.step')
receipt = {
    'valid': valid,
    'dimensions_mm': [box.XLength, box.YLength, box.ZLength],
    'solids': len(shape.Solids),
    'version': '.'.join(App.Version()[:3]),
}
Path('check.json').write_text(json.dumps(receipt, allow_nan=False), encoding='utf-8')
'''


def _tools():
    editor = shutil.which('freecad') or shutil.which('FreeCAD')
    console = shutil.which('freecadcmd') or shutil.which('FreeCADCmd')
    return editor, console, {
        'name': 'FreeCAD',
        'available': editor is not None,
        'check_available': console is not None,
    }


def _source(base, name, sink=None):
    if PurePosixPath(name).suffix.lower() != '.fcstd':
        raise ValueError('Choose a FreeCAD .FCStd file from Files.')
    if any(part.startswith('.') for part in name.split('/')):
        raise ValueError('Choose a visible FreeCAD file from Files.')
    with edit_storage.parent(base, name) as (folder, leaf):
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        try:
            return edit_storage.fingerprint_fd(fd, sink, MAX_SOURCE)
        finally:
            os.close(fd)


def _xml(archive, name):
    document = archive.getinfo(name)
    if document.file_size > MAX_XML:
        raise ValueError('A FreeCAD XML document exceeds the room limit.')
    raw = archive.read(document).decode('utf-8-sig')
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', raw, re.I):
        raise ValueError('FreeCAD document declarations and external XML entities are unavailable.')
    return ET.fromstring(raw)


def _text(value, fallback):
    return ''.join(ch for ch in value if ch.isprintable())[:240] or fallback


def _details(archive, name):
    members = archive.infolist()
    if len(members) > MAX_ENTRIES or sum(item.file_size for item in members) > MAX_EXPANDED:
        raise ValueError('The expanded FreeCAD archive exceeds the room limit.')
    names = {item.filename for item in members}
    if len(names) != len(members):
        raise ValueError('The FreeCAD archive contains duplicate member names.')
    root = _xml(archive, 'Document.xml')
    if root.tag != 'Document' or root.find('Objects') is None:
        raise ValueError('The archive has no recognizable FreeCAD document.')
    objects = root.findall('./Objects/Object')
    shapes = {}
    for item in root.findall('./ObjectData/Object'):
        ident = item.get('name', '')
        part = item.find("./Properties/Property[@name='Shape'][@type='Part::PropertyPartShape']/Part")
        if part is None or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,239}', ident):
            continue
        entry = part.get('file', '')
        if (entry in names and PurePosixPath(entry).name == entry and entry.lower().endswith('.brp')
                and archive.getinfo(entry).file_size <= MAX_BREP):
            if ident in shapes or len(shapes) >= MAX_SHAPES:
                raise ValueError('The FreeCAD archive has duplicate or too many stored shapes.')
            shapes[ident] = entry
    label = root.find("./Properties/Property[@name='Label']/String")
    tip = root.find("./Properties/Property[@name='TipName']/String")
    fallback = PurePosixPath(name).stem
    views = [_xml(archive, 'GuiDocument.xml')] if 'GuiDocument.xml' in names else []
    script_types = (item.get('type', '') for tree in [root, *views] for item in tree.iter())
    opens = (not any('python' in value.casefold() for value in script_types)
             and not any(item.casefold().endswith(EMBEDDED_SCRIPT) for item in names)
             and not any(stat.S_ISLNK(info.external_attr >> 16) for info in members)
             and all('\\' not in item and ':' not in item and not any(ord(ch) < 32 for ch in item)
                     and all(part not in ('', '.', '..') for part in item.rstrip('/').split('/'))
                     for item in names))
    return shapes, {
        'label': _text(label.get('value', '') if label is not None else '', fallback),
        'document_version': _text(root.get('ProgramVersion', ''), 'Unknown'),
        'objects': len(objects),
        'shape_objects': len(shapes),
        'shape_names': list(shapes),
        'preferred_shape': tip.get('value') if tip is not None and tip.get('value') in shapes else None,
        'editor_safe': opens,
    }


def _shape(archive, shapes, name):
    if name is None and len(shapes) == 1:
        name = next(iter(shapes))
    if name not in shapes:
        raise ValueError('Select one stored FreeCAD shape to check or export.')
    data = archive.read(shapes[name])
    if b'DBRep_DrawableShape' not in data[:128] and b'CASCADE Topology' not in data[:128]:
        raise ValueError('The selected FreeCAD shape has no recognized BREP header.')
    return name, data


def _native(console, directory, brep, export):
    (directory / 'stored.brep').write_bytes(brep)
    script = directory / 'geometry.py'
    script.write_text(CHECK_SCRIPT, encoding='utf-8')
    if export:
        (directory / 'export-request').touch()
    env = {**os.environ, 'XDG_CONFIG_HOME': str(directory / 'config'),
           'XDG_DATA_HOME': str(directory / 'data'), 'PYTHONNOUSERSITE': '1'}
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    command = [console, '--console', '--safe-mode', '--user-cfg', str(directory / 'user.cfg'),
               '--system-cfg', str(directory / 'system.cfg')]
    try:
        process = subprocess.run(
            command, cwd=directory, env=env,
            input=b"exec(compile(open('geometry.py', 'rb').read(), 'geometry.py', 'exec'))\n",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f'FreeCAD geometry check exceeded {TIMEOUT} seconds.') from exc
    receipt = directory / 'check.json'
    if process.returncode != 0 or not receipt.is_file() or receipt.stat().st_size > 4096:
        raise ValueError('FreeCAD could not read this stored shape.')
    result = json.loads(receipt.read_text(encoding='utf-8'))
    if (type(result.get('valid')) is not bool or type(result.get('solids')) is not int
            or not isinstance(result.get('version'), str)
            or not isinstance(result.get('dimensions_mm'), list) or len(result['dimensions_mm']) != 3
            or not all(type(value) in (int, float) and math.isfinite(value) and value >= 0
                       for value in result['dimensions_mm'])):
        raise ValueError('FreeCAD returned an invalid geometry receipt.')
    return result


def _step_target(base, relative):
    if PurePosixPath(relative).suffix.lower() not in ('.step', '.stp'):
        raise ValueError('Enter a new .step or .stp file path in Files.')
    path = record_io.project_path(base, relative, must_exist=False)
    if path.exists():
        raise ValueError('Choose a fresh Files path for the STEP export.')
    with edit_storage.parent(base, relative) as (folder, _):
        return os.fstat(folder)


def _publish(base, relative, expected_folder, output):
    if not output.is_file() or output.stat().st_size > EXPORT_LIMIT:
        raise ValueError('FreeCAD did not produce a bounded STEP file.')
    with output.open('rb', buffering=0) as source:
        if not source.read(32).startswith(b'ISO-10303-21;'):
            raise ValueError('FreeCAD did not produce a bounded STEP file.')
        source.seek(0)
        with edit_storage.parent(base, relative) as (folder, name):
            if not os.path.samestat(expected_folder, os.fstat(folder)):
                raise ValueError('The destination folder changed during the export.')
            staged = '.graphite-step-' + uuid4().hex
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            fd = os.open(staged, flags, mode=0o600, dir_fd=folder)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    value = edit_storage.fingerprint_fd(source.fileno(), stream, EXPORT_LIMIT)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(staged, name, src_dir_fd=folder, dst_dir_fd=folder, follow_symlinks=False)
                except FileExistsError as exc:
                    raise ValueError('The destination appeared during export. Choose a fresh Files path.') from exc
            finally:
                os.unlink(staged, dir_fd=folder)
            os.fsync(folder)
    return {'path': relative, 'bytes': value['bytes'], 'sha256': value['sha256']}


def dispatch(kernel, operation, args, principal):
    if operation not in FIELDS or SCOPES[operation] not in principal.scopes:
        raise ValueError('FreeCAD operation is outside the authorized scope.')
    action = operation.rsplit('.', 1)[-1]
    if action != 'inspect' and (principal.identity != 'desktop-owner' or 'read' not in principal.scopes):
        raise ValueError('A FreeCAD native action needs desktop owner approval.')
    base = files_service.root(kernel, create=False).absolute()
    name = args['path']
    content = BytesIO()
    binding = _source(base, name, content)
    digest = binding['sha256']
    if action != 'inspect' and digest != args['expected_sha256']:
        raise ValueError('The selected file changed. Inspect it again before starting a FreeCAD action.')
    editor, console, tool = _tools()
    result = {'path': name, 'sha256': digest, 'bytes': binding['bytes'], 'tool': tool}
    try:
        with zipfile.ZipFile(content) as archive:
            shapes, metadata = _details(archive, name)
            if action in ('check', 'export'):
                selected, brep = _shape(archive, shapes, args.get('object'))
    except (zipfile.BadZipFile, KeyError, RuntimeError, ET.ParseError, UnicodeError, NotImplementedError) as exc:
        raise ValueError('The FreeCAD archive or its document data is unreadable.') from exc
    if action == 'inspect':
        return {'state': 'READY' if editor or console else 'TOOL_UNAVAILABLE', **result, **metadata}
    if action == 'open':
        if not editor:
            raise ValueError('The FreeCAD editor is unavailable on this host.')
        if not metadata['editor_safe']:
            raise ValueError('This document declares scripted objects or embedded scripts. Graphite can inspect its stored geometry.')
        path = record_io.project_path(base, name)
        if _source(base, name)['sha256'] != digest:
            raise ValueError('The source changed before handoff. Inspect it again.')
        return {'state': 'STARTED', **result,
                'pid': program_build._start([editor, '--safe-mode', str(path)], path.parent)}
    if not console:
        raise ValueError('The FreeCAD console is unavailable on this host.')
    destination = args.get('destination')
    if action == 'export':
        folder = _step_target(base, destination)
    with tempfile.TemporaryDirectory(prefix='graphite-freecad-') as scratch:
        directory = Path(scratch)
        geometry = _native(console, directory, brep, action == 'export')
        checked = {'state': 'CHECKED', **result, 'object': selected, 'shapes': 1, **geometry}
        if action == 'check':
            return checked
        if not geometry['valid']:
            raise ValueError('FreeCAD found invalid geometry. STEP export needs a valid shape.')
        if _source(base, name)['sha256'] != digest:
            raise ValueError('The source changed during export. Inspect it again.')
        return {**checked, 'state': 'EXPORTED', 'source': name, 'source_sha256': digest,
                **_publish(base, destination, folder, directory / 'geometry.step')}
