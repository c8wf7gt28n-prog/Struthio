"""Kasandra's art (0.8.0): which still a surface shows, chosen by the state of the work beside it.

The owner's pack (branding/kasandra: catalog.json, art/, preview/) names eight stills, the places they fit (slots) and the
states each was made for. A surface says its slot and the state of what it shows; this module answers with a still:

    an exact match of slot and state (two or more: a turn the surface keeps, so the Office can alternate dusk and rain
    each time it is opened and keep its choice while it stays open) -> the catalog's default for that slot and state ->
    the quiet still -> nothing (the surface paints its plain ground).

A still is used only when its path stays inside the pack, it is a picture, and its bytes match the catalog's sha256 (a
changed or broken file is treated as missing, so the next still in the order is shown). Pictures are decoded at the size
they are shown at from the still decoded whole (the last three are kept), cropped to cover the place round the catalog's
focal point, and kept in a small cache keyed by (still, size, device pixel ratio). Each decode's time is kept
(`decodes()`), for the 35B campaign's Art-on/Clean runs.

`current_state(host)` reads the work as it stands: something waits for the owner's Approve -> awaiting_approval; the last
outcome failed less than 45 s ago -> blocked; Stacy is answering, a job runs, or a what-if is up -> working; the last
outcome succeeded less than 20 s ago -> completed; else idle. The surfaces ask again when they are painted.
"""
import hashlib
import json
import time
from collections import OrderedDict
from datetime import date
from pathlib import Path, PurePosixPath

SLOTS = ('office_banner', 'field_edge', 'worksheet_strip', 'assistant_rail')
STATES = ('idle', 'viewing', 'working', 'awaiting_approval', 'completed', 'blocked')
PICTURES = ('.webp', '.png', '.jpg', '.jpeg')
HOLD = {'completed': 20.0, 'blocked': 45.0}     # how long an outcome stays in the picture after it happened (seconds)
CACHE_SIZE = 16                                 # pictures kept at their shown size
SOURCES = 3                                     # stills kept decoded whole (about 6 MB each)
MAX_CATALOG = 256 * 1024                        # a catalog larger than this is not read
MAX_PICTURE = 16 * 1024 * 1024                  # nor a still larger than this

_catalogs = {}          # folder -> (mtime_ns, catalog or None)
_verified = {}          # path -> (mtime_ns, size, ok)
_images = OrderedDict() # (path, width, height, dpr*100, focal) -> QImage
_sources = OrderedDict()  # path -> QImage, the still decoded whole
_decodes = []           # (scene id, milliseconds, (width, height)), the last 64
_scales = []            # milliseconds for each scaling to a shown size, the last 64


def folder(root):
    from .locations import program
    return program(root) / 'branding' / 'kasandra'


def inside(base, relative):
    """The pack's file for a catalog path, or None: relative, no '..', no drive or backslash, a picture, inside the pack."""
    if not isinstance(relative, str) or not 0 < len(relative) < 200 or '\\' in relative or ':' in relative or '\x00' in relative:
        return None
    pure = PurePosixPath(relative)
    if pure.is_absolute() or '..' in pure.parts or pure.suffix.lower() not in PICTURES:
        return None
    path = Path(base, *pure.parts)
    try:
        if not path.resolve().is_relative_to(Path(base).resolve()):return None
    except (OSError, RuntimeError):
        return None
    return path


def _scene_ok(scene):
    try:
        fx, fy = scene['focal_point']
        return (isinstance(scene['id'], str) and 0 < len(scene['id']) <= 64 and scene['id'].replace('_', '').isalnum()
                and isinstance(scene['file'], str) and isinstance(scene.get('sha256'), str) and len(scene['sha256']) == 64
                and all(s in SLOTS for s in scene['slots']) and all(s in STATES for s in scene['states'])
                and 0.0 <= float(fx) <= 1.0 and 0.0 <= float(fy) <= 1.0)
    except (KeyError, TypeError, ValueError):
        return False


def catalog(base):
    """The pack's catalog, checked: scenes with a good shape only; None when the file is absent or unreadable. Read again
    when the file changes."""
    path = Path(base) / 'catalog.json'
    try:
        stat = path.stat()
    except OSError:
        return None
    known = _catalogs.get(str(base))
    if known and known[0] == stat.st_mtime_ns:return known[1]
    found = None
    try:
        if stat.st_size <= MAX_CATALOG:
            data = json.loads(path.read_text(encoding='utf-8'))
            scenes = [s for s in data.get('scenes', []) if isinstance(s, dict) and _scene_ok(s)] if isinstance(data, dict) else []
            defaults = data.get('default_by_state', {}) if isinstance(data, dict) else {}
            found = {'scenes': {s['id']: s for s in scenes},
                     'order': [s['id'] for s in scenes],
                     'defaults': {slot: {state: name for state, name in (states or {}).items() if state in STATES and isinstance(name, str)}
                                  for slot, states in (defaults if isinstance(defaults, dict) else {}).items()
                                  if slot in SLOTS and isinstance(states, dict)},
                     'quiet': data.get('quiet_fallback') if isinstance(data.get('quiet_fallback'), str) else None}
    except (OSError, ValueError, AttributeError, TypeError):
        found = None
    _catalogs[str(base)] = (stat.st_mtime_ns, found)
    return found


def usable(base, scene, check=True):
    """The still's file when it may be shown: inside the pack, present, and (check) its bytes match the catalog. Each file's
    check is done once and done again only if the file changes."""
    path = inside(base, scene.get('file'))
    if path is None:return None
    try:
        stat = path.stat()
    except OSError:
        return None
    if not check:return path
    key = str(path);known = _verified.get(key)
    if known and known[:2] == (stat.st_mtime_ns, stat.st_size):return path if known[2] else None
    ok = False
    try:
        if stat.st_size <= MAX_PICTURE:ok = hashlib.sha256(path.read_bytes()).hexdigest() == scene['sha256'].lower()
    except OSError:
        ok = False
    _verified[key] = (stat.st_mtime_ns, stat.st_size, ok)
    return path if ok else None


def eligible(base, slot, state):
    """The stills made for this slot and this state, in catalog order, whose files may be shown."""
    found = catalog(base)
    if not found:return []
    return [name for name in found['order'] if slot in found['scenes'][name]['slots'] and state in found['scenes'][name]['states']
            and usable(base, found['scenes'][name])]


def choose(base, slot, state, turn=0):
    """The still for a slot in a state: an exact match (turn picks among several), else the catalog's default for the slot
    and state, else the quiet still, else None."""
    found = catalog(base)
    if not found or slot not in SLOTS:return None
    names = eligible(base, slot, state)
    if names:return found['scenes'][names[int(turn) % len(names)]]
    for name in (found['defaults'].get(slot, {}).get(state), found['quiet']):
        scene = found['scenes'].get(name) if name else None
        if scene is not None and usable(base, scene):return scene
    return None


def suggestion(base, slot, state, offered_id, token, current_token):
    """A still a model named for this place: used only when it is one of the stills offered for this exact slot and state,
    and the token it was asked under still matches (a late answer for another view or job changes nothing)."""
    if token != current_token or not isinstance(offered_id, str):return None
    found = catalog(base)
    if not found or offered_id not in eligible(base, slot, state):return None
    return found['scenes'][offered_id]


def daily_turn(opened=0):
    """A turn that is the same all day and moves on each time a place is opened again."""
    return date.today().toordinal() + int(opened)


def cover(width, height, image_w, image_h, focal, zoom=1.0):
    """(scaled width, scaled height, left, top): the picture scaled to cover zoom x (width x height), and the width x height
    window of it that is shown, centred on the focal point as nearly as the picture's edges allow."""
    zoom = max(1.0, float(zoom))
    scale = max(width * zoom / max(1, image_w), height * zoom / max(1, image_h))
    sw, sh = max(width, round(image_w * scale)), max(height, round(image_h * scale))
    left = min(max(0, round(sw * float(focal[0]) - width / 2)), sw - width)
    top = min(max(0, round(sh * float(focal[1]) - height / 2)), sh - height)
    return sw, sh, left, top


def source(path, scene_id):
    """The still decoded whole, once, and kept (the last SOURCES of them): a window resized through many sizes then costs
    a scale for each, not a decode. (A WebP is decoded whole whatever size is asked of the reader.)"""
    from PySide6.QtGui import QImage, QImageReader
    key = str(path)
    if key in _sources:
        _sources.move_to_end(key);return _sources[key]
    started = time.perf_counter()
    reader = QImageReader(key);reader.setAutoTransform(False)
    image = reader.read()
    if image.isNull():return QImage()
    image = image.convertToFormat(QImage.Format_RGB32)
    _decodes.append((scene_id, round((time.perf_counter() - started) * 1000, 2), (image.width(), image.height())))
    del _decodes[:-64]
    _sources[key] = image
    while len(_sources) > SOURCES:_sources.popitem(last=False)
    return image


def picture(base, scene, width, height, dpr=1.0, zoom=1.0):
    """The still at the shown size (width x height logical pixels at dpr), cropped round its focal point; a null QImage when
    it cannot be read. `zoom` > 1 shows a closer window round the focal point (her face in a small square)."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QImage
    width, height = int(width), int(height)
    if scene is None or width < 2 or height < 2:return QImage()
    path = usable(base, scene)
    if path is None:return QImage()
    dpr = max(1.0, float(dpr or 1.0));zoom = max(1.0, float(zoom))
    pw, ph = max(2, round(width * dpr)), max(2, round(height * dpr))
    key = (str(path), pw, ph, round(zoom * 100), tuple(scene['focal_point']))
    if key in _images:
        _images.move_to_end(key);return _images[key]
    whole = source(path, scene['id'])
    if whole.isNull():return QImage()
    started = time.perf_counter()
    sw, sh, left, top = cover(pw, ph, whole.width(), whole.height(), scene['focal_point'], zoom)
    image = whole.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).copy(QRect(left, top, pw, ph))
    image.setDevicePixelRatio(dpr)
    _scales.append(round((time.perf_counter() - started) * 1000, 2));del _scales[:-64]
    _images[key] = image
    while len(_images) > CACHE_SIZE:_images.popitem(last=False)
    return image


# The owner's marks beside the stills (branding/kasandra/README.md lists each with its SHA-256): shown only when their
# bytes are these, the way a still is shown only when its bytes match the catalog.
MARKS = {
    'hologram.webp': 'b73f7108256ef7523b38bf6ba53478b62d90c8bcd3a3dec9d97b8d34913698ec',
    # the neon kp logo, the only kp mark (0.8.3): the owner's drawing, clean (tools/cut_kp_neon.py); Apps in the head
    'kp_neon.png': 'f3c6e5fb5cd0f2d61019187bae0d70771378fba5a6c7da27dd8d15d486fd2cc0',
    'wordmark.webp': '0a8d44e549b4c9904df11496fb81106c918680c4c84a268098067dc919deb1e6',
}
CROP = (80, 15, 608, 822)       # the hologram's figure in its 800 x 875 picture: its ink, the faint glitch lines left out
_cutouts = {}                   # path -> (QImage, glitch rows)


def mark(base, name):
    """The owner's mark `name` in the pack when its bytes are the recorded ones (MARKS), else None (checked once per change
    of the file, as a still is)."""
    if name not in MARKS:return None
    return usable(base, {'file': name, 'sha256': MARKS[name]})


def cutout(path):
    """Her hologram, cut to CROP, with its alpha (never source()'s RGB32: the picture's edges are clear), decoded once."""
    return _cut(path)[0]


def glitch_rows(path):
    """The rows of the cut (as shares of its height) where the picture's own glitch lines run: faint pixels (alpha 1 to 7)
    outside her ink, left of x 86 or right of x 681. A tear lands on one of them more often than not."""
    return _cut(path)[1]


def _cut(path):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QImageReader
    key = str(path)
    if key in _cutouts:return _cutouts[key]
    started = time.perf_counter()
    reader = QImageReader(key);reader.setAutoTransform(False)
    whole = reader.read()
    if whole.isNull():      # kept too: a picture that will not decode here is not read again for every frame
        _cutouts[key] = (QImage(), ());return _cutouts[key]
    whole = whole.convertToFormat(QImage.Format_ARGB32)
    _decodes.append(('hologram', round((time.perf_counter() - started) * 1000, 2), (whole.width(), whole.height())));del _decodes[:-64]
    x, y, w, h = CROP
    faint = bytes(1 if 1 <= a < 8 else 0 for a in range(256))
    rows = [];bpl = whole.bytesPerLine();bits = bytes(whole.constBits())
    for row in range(y, min(whole.height(), y + h)):
        line = bits[row * bpl:row * bpl + 4 * whole.width()]
        outside = line[3:4 * 86:4] + line[4 * 682 + 3::4]
        if 1 in outside.translate(faint):rows.append(round((row - y) / h, 4))
    image = whole.copy(QRect(x, y, w, h)).convertToFormat(QImage.Format_ARGB32_Premultiplied)
    _cutouts[key] = (image, tuple(rows))
    return _cutouts[key]


def decodes():
    """The last decodes: (still, milliseconds, (pixel width, pixel height)), and the last scalings to a shown size
    (milliseconds). For the campaign's Art-on/Clean comparison."""
    return list(_decodes)


def scalings():
    return list(_scales)


def forget():
    """Drop every decoded picture and every check (a pack changed on disk, or a test)."""
    _images.clear();_sources.clear();_verified.clear();_catalogs.clear();_cutouts.clear()


# The state of the work --------------------------------------------------------

def note_outcome(host, ok):
    """An act came to an end: Approved and done (ok True) or refused, failed, stopped (ok False)."""
    try:host._art_outcome = ('completed' if ok else 'blocked', time.monotonic())
    except Exception:  # noqa: BLE001 - a host that takes no attributes: nothing to keep
        pass
    nudge(host)


def nudge(host):
    """Ask the surfaces that show the work's state to paint again now, not at their next tick."""
    for name in ('_kasandra_watchers',):
        for widget in list(getattr(host, name, ()) or ()):
            try:widget.update()
            except RuntimeError:  # its C++ side is gone
                pass
    field = getattr(host, 'field_page', None)
    try:
        if field is not None:field.view.update()
    except (AttributeError, RuntimeError):
        pass


def watch(host, widget):
    """A surface that shows the state of the work: painted again when an outcome is noted."""
    try:
        watchers = host.__dict__.setdefault('_kasandra_watchers', [])
        watchers[:] = [w for w in watchers if _alive(w)] + [widget]
    except Exception:  # noqa: BLE001 - a host that takes no attributes
        pass


def _alive(widget):
    try:
        widget.objectName();return True
    except RuntimeError:
        return False


def waiting(host):
    """Something waits for the owner: an enabled Approve that waits (boss_qt.WAITS) in Stacy's pane, or the Field's Go."""
    try:
        from PySide6.QtWidgets import QPushButton
        from .boss_qt import WAITS
        face = getattr(getattr(host, 'shell2', None), 'face', None)
        if face is not None and any(b.property(WAITS) and b.isEnabled() and b.isVisibleTo(face) for b in face.findChildren(QPushButton)):
            return True
        field = getattr(host, 'field_page', None)
        return bool(field is not None and getattr(field, 'pending', None) is not None)
    except Exception:  # noqa: BLE001 - a host without these parts waits for nothing
        return False


def working(host):
    try:
        shell = getattr(host, 'shell2', None)
        face = getattr(shell, 'face', None)
        if face is not None and getattr(face, 'job', None):return True
        if getattr(getattr(getattr(shell, 'top', None), 'equalizer', None), 'busy', False):return True
        view = getattr(getattr(host, 'field_page', None), 'view', None)
        return bool(view is not None and getattr(view, 'would', None))
    except Exception:  # noqa: BLE001
        return False


def current_state(host, now=None):
    """awaiting_approval > blocked (fresh) > working > completed (fresh) > idle."""
    if waiting(host):return 'awaiting_approval'
    now = time.monotonic() if now is None else now
    kind, at = getattr(host, '_art_outcome', (None, 0.0)) if isinstance(getattr(host, '_art_outcome', None), tuple) else (None, 0.0)
    fresh = kind in HOLD and now - at < HOLD[kind]
    if fresh and kind == 'blocked':return 'blocked'
    if working(host):return 'working'
    return 'completed' if fresh else 'idle'


def column_state(host, now=None):
    """The state her masthead and her hologram show: current_state, and while it is quiet but her column's Now line counts
    something waiting for the owner on the Agenda ("1 waiting for you"), awaiting_approval, so the word above it never says
    "quiet" (0.8.3 review). The stills keep current_state: their waiting hand is for an Approve that waits."""
    state = current_state(host, now)
    if state == 'idle':
        face = getattr(getattr(host, 'shell2', None), 'face', None)
        if int(getattr(face, 'agenda_waiting', 0) or 0) > 0:return 'awaiting_approval'
    return state


def in_force():
    """Whether Kasandra is the appearance this start is drawn in."""
    from . import boss_theme
    return boss_theme.APPEARANCE == 'kasandra'
