"""Apps: the owner's Struthio in the head's upper right, in both looks (0.8.6).

The owner, 20 November 2026, with his own picture of a Struthio (an ostrich drawn with circuit traces): the Struthio upper
right as the Apps button, "like a windows start menu". It is drawn crisp at the head's height: MARGIN above and below it in
the band, its width by its own shape, on whole pixels, from a copy drawn down smoothly once to the exact device pixels and
kept (no scaling at paint time, so its traces stay sharp). Its name for readers stays Apps, and its tip. The window's own
icon is unchanged; the neon kp logo stays in the program (kp_logo, branding/kasandra/kp_neon.png).

The file is the drawing on no ground (branding/struthio/struthio.png, cut by tools/cut_struthio.py from the owner's file),
shown only when its bytes are the recorded ones (SHA256); otherwise Apps is its words, '[#] Apps ▾'.

Light: a soft light behind it, added to the band (Screen), at the strength of the Glow dial, none on the Clean desk or at a
glow of 0; never laid over the drawing, so the drawing itself is always its own colours. When Apps opens it catches with
its menu (kp_logo's catch: menu_catch.CATCH_MS): its light surges and a cyan and a magenta ghost spread from it and settle
away; settled there are no ghosts, so its lines stay single. With Reduce motion, or the glow off, it is still.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter

NAME = 'struthio.png'
SHA256 = '217902d73e19e5f730faf882dc670b5fbf3a99fe04e3ec2dbad7ddcfc85de45b'
MARGIN = 4                 # px at 14 pt above and below the drawing in the head band
TALLEST = 52               # px at 14 pt: never taller than this, whatever the band
LIGHT = 0.12               # the soft light's strength per step of the Glow dial (Neon 3: 0.36)
BLUR = 6                   # how far the light reaches, px at 14 pt
GHOSTS = (('#83eaff', -1.0), ('#ff4fd8', 1.0))      # the catch's ghosts: cyan to the left, magenta to the right
SPREAD = 3.5               # px at 14 pt the ghosts stand away at the catch's start (none settled)
GHOST = 0.5                # the ghosts' strength at the catch's start

_images = {}               # path -> the drawing, decoded once
_drawn = {}                # (image key, w, h, dpr, scale) -> (drawing, light, mask, margin) at that size


def folder(root):
    from .locations import program
    return program(root) / 'branding' / 'struthio'


def image(root):
    """The drawing as a premultiplied image when its bytes are the recorded ones, else a null image."""
    from . import kasandra_art
    path = kasandra_art.usable(folder(root), {'file': NAME, 'sha256': SHA256})
    if path is None:return QImage()
    key = str(path)
    if key not in _images:
        found = QImage(key)
        _images[key] = found.convertToFormat(QImage.Format_ARGB32_Premultiplied) if not found.isNull() else QImage()
    return _images[key]


def height(band, scale=1.0):
    """The drawing's height in a head band `band` px tall: the band less MARGIN above and below, at most TALLEST."""
    return max(8, min(int(band) - 2 * round(MARGIN * scale), round(TALLEST * scale)))


def width(drawing, tall):
    """The drawing's width at `tall` px, by its own shape (whole pixels)."""
    if drawing is None or drawing.isNull() or drawing.height() <= 0:return 0
    return max(1, round(drawing.width() * tall / drawing.height()))


def _blur(picture, reach):
    if reach <= 1:return picture
    small = picture.scaled(max(1, round(picture.width() / reach)), max(1, round(picture.height() / reach)), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return small.scaled(picture.width(), picture.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def drawn(picture, w, h, dpr=1.0, scale=1.0):
    """(drawing, light, mask, margin): the drawing at w x h logical pixels, drawn down once to the device's pixels on a canvas
    with room round it for its light; kept for the next paint."""
    key = (picture.cacheKey(), int(w), int(h), round(dpr * 100), round(scale * 100))
    if key in _drawn:return _drawn[key]
    margin = max(1, round(BLUR * 1.5 * scale * dpr));pw, ph = max(1, round(w * dpr)), max(1, round(h * dpr))
    canvas = QImage(pw + 2 * margin, ph + 2 * margin, QImage.Format_ARGB32_Premultiplied);canvas.fill(0)
    p = QPainter(canvas);p.drawImage(margin, margin, picture.scaled(pw, ph, Qt.IgnoreAspectRatio, Qt.SmoothTransformation));p.end()
    mask = QImage(canvas.size(), QImage.Format_ARGB32_Premultiplied);mask.fill(0xffffffff)
    p = QPainter(mask);p.setCompositionMode(QPainter.CompositionMode_DestinationIn);p.drawImage(0, 0, canvas);p.end()
    made = (canvas, _blur(canvas, BLUR * scale * dpr), mask, margin / dpr)
    for layer in made[:3]:layer.setDevicePixelRatio(dpr)
    _drawn[key] = made
    while len(_drawn) > 8:_drawn.pop(next(iter(_drawn)))
    return made


def strengths(level, surge=0.0):
    """(light, ghost) at Glow `level` (0: none), `surge` 0 to 1 while it catches."""
    if level <= 0:return 0.0, 0.0
    caught = max(0.0, min(1.0, surge))
    return min(0.6, LIGHT * level * (1.0 + 0.8 * caught)), GHOST * caught


def paint(p, rect, picture, level, scale=1.0, surge=0.0):
    """The Struthio in `rect` (logical, whole pixels), its light behind it at Glow `level`, caught by `surge`. Returns the
    strengths used, for checks."""
    from .kp_logo import tinted
    dpr = p.device().devicePixelRatioF() if p.device() is not None else 1.0
    drawing, light, mask, margin = drawn(picture, rect.width(), rect.height(), dpr, scale)
    at = QPointF(round(rect.left()) - margin, round(rect.top()) - margin)
    used = strengths(level, surge)
    if used[0] > 0:
        p.save();p.setCompositionMode(QPainter.CompositionMode_Screen)      # light added to the band, never paint over it
        p.setOpacity(used[0]);p.drawImage(at, light)
        if used[1] > 0:
            p.setOpacity(used[1])
            for colour, side in GHOSTS:p.drawImage(at + QPointF(side * SPREAD * scale * surge, 0), tinted(mask, colour))
        p.restore()
    p.drawImage(at, drawing)
    return used


def rect_in(button, picture, scale=1.0):
    """Where the drawing stands in the Apps button: centred, its height by the button's (the band's), on whole pixels."""
    tall = height(button.height(), scale);wide = width(picture, tall)
    return QRectF((button.width() - wide) // 2, (button.height() - tall) // 2, wide, tall)
