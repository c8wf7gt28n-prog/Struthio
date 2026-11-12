"""Graphite's marks, painted with QPainter so they stay sharp at any size (HATCH GRAPHITE-01, the owner's design update of
2026-11-06; the references are branding/graphite/reference/).

  the sharpened point   two paper wedges converging to a point, a narrow gap between them, a short stroke past the tip
  mark_tile / icons     the point on a small graphite rounded tile: the window icon (and the head's mark until HATCH DESK D1a)
  paint_erased_mark     the point drawn pale, as if erased from a band's graphite shading: the System menu's symbol at the
                        far right of the head (HATCH DESK D1a)
  pointer               the window's pointer: the point's two facets aimed at 11 o'clock, the click at the tip (HATCH DESK D1b)
  startup_screen        GRAPHITE in spaced capitals under the point, on graphite ground, while the window is built
  Cat                   the unlabeled peeking cat in the lower band that opens the programs list: REST, HOVER, LIST OPEN,
                        SLEEPY

The cat's pose is a small pure state machine (CatPoses) over a table of pose numbers (POSES); a change of pose moves the
numbers in one short animation (MOVE_MS), or switches at once under Reduce motion. Colours: the shell2 palette, repeated here so
the startup screen needs no window code. HATCH DESK D2 (the owner, 2026-11-06): the cat is pale on the lower band, its
silhouette the workspace's full warm paper white (CAT_COAT), with graphite eye and paw details (CAT_DETAIL); the owner's
colours carry its state: pencil-yellow irises round graphite pupils on hover and while the programs list is open (CAT_IRIS,
the pose number `iris`; graphite eyes at rest), the nose and inner ears always a small soft eraser pink (CAT_NOSE), the
keyboard-focus mark eraser pink (CAT_FOCUS); asleep the eyes close and the yellow goes. The colours are named constants, so a
full pink cat is one swap (CAT_COAT = ERASER_MARK).
"""
from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QCursor, QFont, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

GRAPHITE, PAPER, PAPER_LIGHT, ERASER_MARK = '#504d46', '#f6f3eb', '#fffdf8', '#cba5a4'  # shell2.TEXT, GROUND, CARD, ERASER_MARK
PENCIL = '#d4b56a'  # pencil yellow: the active choice's mark (shell2.AMBER_EDGE, desk_qt.PENCIL)
ERASED = '#efeae0'  # paper as if erased from a band's graphite shading (desk_qt.ERASED, the bands' lettering)
# The cat's colours (HATCH DESK D2). The owner asked "Should the cat be white to stand out against the dark shading?" (yes) and
# "Do you think the cat should be eraser pink with yellow eyes?" (the recommendation below, approved: "Brilliant").
CAT_COAT = PAPER_LIGHT    # the silhouette: the workspace's full warm paper white, the brightest value in the band (9.1:1 on its
                          # mean tone, the lettering 7.7:1); never a cold #ffffff. A full pink cat is this one swap: ERASER_MARK
CAT_DETAIL = GRAPHITE     # the eyes at rest, the pupils, the closed eyes, the paws' outline and toes, the mouth
CAT_IRIS = PENCIL         # the irises round the graphite pupils on hover and while the programs list is open
CAT_NOSE = ERASER_MARK    # the nose and the inner ears, always: a small soft eraser pink
CAT_FOCUS = ERASER_MARK   # keyboard focus: the short mark under the cat
WORD = 'GRAPHITE'

# The sharpened point, in the boot mockup's own pixels (224 by 177 from its top-left wedge corner).
MARK_BOX = (224.0, 177.0)
UPPER = ((0, 0), (1, 90), (193, 140))      # the upper wedge: top-left, bottom-left, tip
LOWER = ((1, 106), (1, 172), (182, 144))   # the lower wedge, its tip a little short of the upper one: the gap closes there
STROKE = ((220, 138), (186, 177), 6.0)     # the short stroke past the tip
# Small sizes stay crisp, in device pixels: the gap at the wedges' wide end at least GAP_MIN (the two inner corners part;
# the tips still converge), the stroke at least STROKE_MIN wide, and left out where it would be shorter than STROKE_SHOWN
# (a dot there, not a stroke: only the 16 px icon). From about 64 px, and for the head's 44 px tile at device pixel ratio
# 2, the drawing is the mockup's own numbers.
GAP_MIN, STROKE_MIN, STROKE_SHOWN = 1.25, 1.2, 3.0
SMALL_TILE = 24   # device pixels: under it the tile's margin is 10%, not 15%, so the point keeps its room


def paint_mark(p, rect, ink=PAPER):
    """The sharpened point, centred in rect and as large as fits, in ink; at small sizes the gap and the stroke keep their
    least widths in device pixels (the painter's device transform includes the device pixel ratio)."""
    w, h = MARK_BOX;s = min(rect.width() / w, rect.height() / h)
    k = s * (math.sqrt(abs(p.deviceTransform().determinant())) or 1.0)  # device pixels per mockup pixel
    if k <= 0:return
    p.save();p.setRenderHint(QPainter.Antialiasing);p.translate(rect.center().x() - w * s / 2, rect.center().y() - h * s / 2);p.scale(s, s)
    p.setPen(Qt.NoPen);p.setBrush(QColor(ink))
    part = max(0.0, GAP_MIN / k - (LOWER[0][1] - UPPER[1][1])) / 2
    upper = (UPPER[0], (UPPER[1][0], UPPER[1][1] - part), UPPER[2]);lower = ((LOWER[0][0], LOWER[0][1] + part), LOWER[1], LOWER[2])
    for wedge in (upper, lower):p.drawPolygon(QPolygonF([QPointF(*point) for point in wedge]))
    (x1, y1), (x2, y2), width = STROKE
    if k * math.hypot(x2 - x1, y2 - y1) >= STROKE_SHOWN:
        p.setPen(QPen(QColor(ink), max(width, STROKE_MIN / k), Qt.SolidLine, Qt.FlatCap));p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    p.restore()


def paint_erased_mark(p, rect, ink=ERASED):
    """The sharpened point with no tile, in the bands' erased paper: drawn straight onto the graphite shading, as if rubbed
    out of it. The mark is as wide as rect and centred in it (its height is 177/224 of its width)."""
    paint_mark(p, rect, ink)


def mark_tile(px, dpr=1.0):
    """The point in paper on a graphite rounded tile, px logical pixels square."""
    pix = QPixmap(max(1, round(px * dpr)), max(1, round(px * dpr)));pix.setDevicePixelRatio(dpr);pix.fill(Qt.transparent)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(QColor(GRAPHITE))
    p.drawRoundedRect(QRectF(0, 0, px, px), px * .22, px * .22);m = px * (.15 if px * dpr >= SMALL_TILE else .10)
    paint_mark(p, QRectF(m, m, px - 2 * m, px - 2 * m));p.end();return pix


def mark_icon(px):
    """The tile at px for device pixel ratios 1 and 2 (the head's mark)."""
    icon = QIcon()
    for dpr in (1.0, 2.0):icon.addPixmap(mark_tile(px, dpr))
    return icon


def window_icon():
    """The window icon: the tile painted at 16 to 256 px."""
    icon = QIcon()
    for px in ICON_SIZES:icon.addPixmap(mark_tile(px))
    return icon


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def icon_files(folder):
    """The window icon's tile as files, for places that need a file and not a painter: graphite_icon_256.png (desktop
    entries) and graphite.ico (the Windows shortcut and its uninstall entry; one PNG-compressed image per size in
    ICON_SIZES). The program never reads them; run this again when the mark changes (needs a QGuiApplication):
        python -c "from PySide6.QtGui import QGuiApplication as A; a=A([]); from workbench import graphite_brand as g; g.icon_files('branding/graphite')"
    """
    import struct
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    folder = Path(folder);folder.mkdir(parents=True, exist_ok=True);blobs = []
    for px in ICON_SIZES:
        data = QByteArray();buf = QBuffer(data);buf.open(QIODevice.WriteOnly);mark_tile(px).toImage().save(buf, 'PNG');buf.close()
        blobs.append(bytes(data))
    offset = 6 + 16 * len(ICON_SIZES);entries = b''
    for px, blob in zip(ICON_SIZES, blobs):  # ICONDIRENTRY: width and height 0 mean 256
        entries += struct.pack('<BBBBHHII', px % 256, px % 256, 0, 0, 1, 32, len(blob), offset);offset += len(blob)
    (folder / 'graphite.ico').write_bytes(struct.pack('<HHH', 0, 1, len(ICON_SIZES)) + entries + b''.join(blobs))
    (folder / 'graphite_icon_256.png').write_bytes(blobs[-1])
    return [folder / 'graphite_icon_256.png', folder / 'graphite.ico']


# The pointer (HATCH DESK D1b) -----------------------------------------------------------------------------------------------
# The owner's brief: "Use the two facets of the Graphite mark for the pointer. Aim it at 11 o'clock, 30 degrees left of
# vertical, with the click at the tip." The two wedges of the mark (UPPER, LOWER; the stroke past the tip is left out, since
# nothing may lie beyond the click) are turned about the point so that the mark's own aim, the bisector of its two outer edges,
# points 30 degrees left of straight up, and scaled so the farthest corner is POINTER_REACH logical pixels from the tip. The
# tip is exactly the hotspot (whole logical pixels, so a whole device pixel at 1x and 2x): the click lands on the point, and
# the hotspot's pixel is the point's own first pixel, drawn in graphite. Graphite facets with a thin paper edge, so the
# pointer reads on paper and on the bands.

POINTER_AIM = 30.0       # degrees left of vertical: 11 o'clock
POINTER_REACH = 22.0     # logical px from the tip to the farthest corner of the facets
POINTER_EDGE = 1.0       # logical px of paper around the facets (and between them, along the gap)
POINTER_BOX = 32         # the cursor image, logical px square


def mark_aim():
    """The mark's own aim in its units (radians, y down): the bisector of its two outer edges at the point."""
    tip = UPPER[2]
    back_upper = math.atan2(UPPER[0][1] - tip[1], UPPER[0][0] - tip[0])                  # from the point back along the upper edge
    back_lower = math.atan2(LOWER[1][1] - LOWER[2][1], LOWER[1][0] - LOWER[2][0])         # from the lower tip back along its edge
    back = math.atan2(math.sin(back_upper) + math.sin(back_lower), math.cos(back_upper) + math.cos(back_lower))
    return back + math.pi


def pointer_shape(dpr=1.0, reach=POINTER_REACH, aim=POINTER_AIM):
    """The pointer as numbers: dict(polygons=[upper, lower] in logical px, tip, hotspot (whole logical px), size, aim) for a
    cursor image at device pixel ratio dpr. The tip is the hotspot itself (the corner of the hotspot's pixel, from which the
    facets open into it); every corner is at least POINTER_EDGE + 1 px inside the image."""
    dpr = float(dpr) or 1.0;tip = UPPER[2]
    turn = math.radians(-90.0 - float(aim)) - mark_aim()         # straight up is -90 degrees on screen (y down)
    corners = [point for wedge in (UPPER, LOWER) for point in wedge]
    k = float(reach) / max(math.hypot(x - tip[0], y - tip[1]) for x, y in corners)
    c, s = math.cos(turn), math.sin(turn)
    def place(point):
        dx, dy = point[0] - tip[0], point[1] - tip[1];return (k * (dx * c - dy * s), k * (dx * s + dy * c))
    wedges = [[place(point) for point in wedge] for wedge in (UPPER, LOWER)]
    margin = POINTER_EDGE + 1.0
    hot = (math.ceil(margin - min(x for w in wedges for x, _ in w)), math.ceil(margin - min(y for w in wedges for _, y in w)))
    at = (float(hot[0]), float(hot[1]))
    polygons = [[(x + at[0], y + at[1]) for x, y in wedge] for wedge in wedges]
    need = math.ceil(max(max(x for w in polygons for x, _ in w), max(y for w in polygons for _, y in w)) + margin)
    side = max(POINTER_BOX, need)
    return dict(polygons=polygons, tip=at, hotspot=hot, size=(side, side), aim=float(aim), dpr=dpr, reach=float(reach))


def pointer_angle(polygons):
    """The aim of drawn facets, in degrees left of straight up: the bisector of the two outer edges at the tip (the measure the
    test and the desk check use)."""
    (u0, _, tip), (_, l1, ltip) = polygons
    a = math.atan2(u0[1] - tip[1], u0[0] - tip[0]);b = math.atan2(l1[1] - ltip[1], l1[0] - ltip[0])
    fx, fy = -(math.cos(a) + math.cos(b)), -(math.sin(a) + math.sin(b))
    return math.degrees(math.atan2(-fx, -fy))


def pointer_pixmap(dpr=1.0):
    """The pointer drawn for device pixel ratio dpr (a pixmap of size * dpr device pixels, its ratio set)."""
    shape = pointer_shape(dpr);w, h = shape['size']
    pix = QPixmap(round(w * dpr), round(h * dpr));pix.setDevicePixelRatio(dpr);pix.fill(Qt.transparent)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
    polygons = [QPolygonF([QPointF(x, y) for x, y in wedge]) for wedge in shape['polygons']]
    edge = QPen(QColor(PAPER_LIGHT), 2 * POINTER_EDGE);edge.setJoinStyle(Qt.RoundJoin);p.setPen(edge);p.setBrush(QColor(PAPER_LIGHT))
    for polygon in polygons:p.drawPolygon(polygon)
    p.setPen(Qt.NoPen);p.setBrush(QColor(GRAPHITE))
    for polygon in polygons:p.drawPolygon(polygon)
    # The point's first device pixel, solid: a sharp point covers only a sliver of the pixel it starts in, which would draw
    # it pale; the hotspot's pixel is the tip, so it is graphite at 1x and 2x alike (crisp, and the click visibly on it).
    hx, hy = shape['hotspot'];p.setRenderHint(QPainter.Antialiasing, False);p.fillRect(QRectF(hx, hy, 1.0 / dpr, 1.0 / dpr), QColor(GRAPHITE))
    p.end();return pix


def pointer_cursor(dpr=1.0):
    """The window's pointer: the facets at dpr, the hotspot the tip (in logical px, as QCursor takes it)."""
    shape = pointer_shape(dpr);return QCursor(pointer_pixmap(dpr), *shape['hotspot'])


def use_pointer(window):
    """Set the pointer on a window: every widget that sets no cursor of its own shows it; text fields keep their I-beam,
    splitters their resize cursors, links their hand (each sets its own); the pane separators show the resize cursor while
    the pointer is over them (desk_qt.MirroredDrag.hover, which puts this pointer back after)."""
    dpr = window.devicePixelRatioF() if hasattr(window, 'devicePixelRatioF') else 1.0
    cursor = pointer_cursor(2.0 if dpr > 1.0 else 1.0);window.setCursor(cursor);window.setProperty('graphitePointer', True)
    return cursor


# The startup screen ---------------------------------------------------------------------------------------------------------

def startup_pixmap(dpr=1.0, size=(360, 320)):
    """Graphite ground, the point in paper, GRAPHITE in spaced capitals below it (the boot mockup)."""
    w, h = size;pix = QPixmap(round(w * dpr), round(h * dpr));pix.setDevicePixelRatio(dpr);pix.fill(QColor(GRAPHITE))
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
    paint_mark(p, QRectF(w * .17, h * .12, w * .66, h * .58))
    font = QFont('IBM Plex Sans');font.setWeight(QFont.Medium);font.setPixelSize(round(h * .095))
    font.setLetterSpacing(QFont.AbsoluteSpacing, h * .07);p.setFont(font);p.setPen(QColor(PAPER))
    room = QRectF(0, h * .76, w + h * .07, h * .16)  # the spacing after the last letter is given back so the word is centred
    p.drawText(room, Qt.AlignCenter, WORD);p.end();return pix


class _UntilAnotherWindow(QObject):
    """Closes the startup screen as soon as any other window is shown (the main window, or a dialog during the build,
    which must never sit under it)."""
    def __init__(self, splash):
        super().__init__(splash);self.splash = splash

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show and obj is not self.splash and obj.isWidgetType() and obj.isWindow():
            self.splash.close()
        return False


def startup_screen(app):
    """Show the startup screen until the first other window is shown; returns it, or None when anything fails (the start
    goes on without it). No fade: it appears and goes, so Reduce motion has nothing to stop."""
    try:
        from PySide6.QtWidgets import QSplashScreen
        plex = Path(__file__).resolve().parents[1] / 'branding' / 'fonts' / 'plex' / 'IBMPlexSans-Medium.ttf'
        if 'IBM Plex Sans' not in QFontDatabase.families() and plex.is_file():QFontDatabase.addApplicationFont(str(plex))
        screen = app.primaryScreen();splash = QSplashScreen(startup_pixmap(screen.devicePixelRatio() if screen else 1.0))
        splash.setObjectName('GraphiteStartup');splash.setAccessibleName(WORD + ' is starting');splash.setAttribute(Qt.WA_DeleteOnClose)
        app.installEventFilter(_UntilAnotherWindow(splash));splash.show();app.processEvents()
        return splash
    except Exception:  # noqa: BLE001 - a startup screen never stops the start
        return None


# The cat ---------------------------------------------------------------------------------------------------------------------

IDLE_MS = 90000   # a stretch without input to the program, with the list closed, before the cat gets sleepy
MOVE_MS = 150     # one pose change (the owner: brief, tied to interaction)
# Each pose as numbers: head drop, pupils x and y (-1 … 1 of their room), eyelid (1 open, 0 closed), tail (0 tucked, 1 the
# question-mark curl), right paw (0 on the ground, 1 lifted), iris (0 graphite eyes, 1 pencil-yellow irises: HATCH DESK D2).
FIELDS = ('drop', 'look_x', 'look_y', 'lid', 'tail', 'paw', 'iris')
POSES = {'rest': (0.0, 0.0, -0.25, 1.0, 0.0, 0.0, 0.0),     # eyes forward, both paws down, tail tucked away, graphite eyes
         'hover': (0.0, -0.8, 0.05, 1.0, 1.0, 0.0, 1.0),    # a quick side-eye in yellow; the tail curls like a question mark
         'open': (0.0, 0.6, -0.65, 1.0, 0.0, 1.0, 1.0),     # tail dropped out of sight, right paw lifted, yellow eyes up at the list
         'sleepy': (9.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)}     # settled a little lower, eyes closed, the yellow gone
CAT_BOX = QRectF(-104, -4, 208, 108)  # the drawing's own units: ear tips at 0, the edge at 100
CAT_RATIO = CAT_BOX.width() / CAT_BOX.height()


class CatPoses:
    """The pose from three facts, pure: the menu open wins, then sleep, then the pointer. Each call returns the pose."""
    def __init__(self):self.over = self.open = self.asleep = False

    def pose(self):
        return 'open' if self.open else 'sleepy' if self.asleep else 'hover' if self.over else 'rest'

    def enter(self):self.over = True;self.asleep = False;return self.pose()      # hover wakes it into the side-eye

    def leave(self):self.over = False;return self.pose()

    def menu(self, shown, over=None):
        """The menu opened (from any pose, sleep included: one click) or closed (rest or hover by the pointer's position)."""
        self.open = bool(shown);self.asleep = False
        if over is not None:self.over = bool(over)
        return self.pose()

    def idle(self):
        if not self.open:self.asleep = True  # only while the menu is closed
        return self.pose()

    def wake(self):self.asleep = False;return self.pose()


def blend(a, b, t):return tuple(x + (y - x) * t for x, y in zip(a, b))


def _lerp(a, b, t):return a + (b - a) * t


def cat_paths(params):
    """The cat's parts in CAT_BOX units for one set of pose numbers: body (head, ears and shoulders), the two eyes as
    (centre, radius, lid) and pupils' offset, the tail path (None when tucked), the two paws as (centre, radius), the inner
    ears, the nose and the mouth (HATCH DESK D2), and the iris number. Six-number poses (before D2) read as graphite eyes."""
    drop, look_x, look_y, lid, tail, paw = params[:6];iris = params[6] if len(params) > 6 else 0.0
    def Y(y):return y + drop * (100 - y) / 100.0  # the head settles; the shoulders stay on the ground
    body = QPainterPath(QPointF(-61, 100))
    for c1, c2, end in (((-61, 75), (-57, 60), (-56, 45)), ((-56, 30), (-54, 6), (-46, 2)), ((-43, -0.5), (-41, 0.5), (-39, 3)),
                        ((-32, 11), (-22, 22), (-14, 24.5)), ((-5, 23.5), (5, 23.5), (14, 24.5)), ((22, 22), (32, 11), (39, 3)),
                        ((41, 0.5), (43, -0.5), (46, 2)), ((54, 6), (56, 30), (56, 45)), ((57, 60), (61, 75), (61, 100))):
        body.cubicTo(QPointF(c1[0], Y(c1[1])), QPointF(c2[0], Y(c2[1])), QPointF(end[0], Y(end[1])))
    body.closeSubpath()
    eyes = [(QPointF(x, Y(64.5)), 12.7, lid) for x in (-24.5, 24.5)]
    pupil = QPointF(look_x * 7.4, look_y * 7.4)
    curl = None
    if tail > 0.02:
        def T(x, y):return QPointF(x, 100 - (100 - y) * tail)  # the curl rises from behind the left paw
        curl = QPainterPath(T(-85, 102))
        for c1, c2, end in (((-89, 82), (-80, 68), (-74, 60)), ((-67, 52), (-61, 44), (-64, 36)),
                            ((-66, 28), (-73, 24), (-80, 26)), ((-87, 28), (-92, 35), (-91, 42))):
            curl.cubicTo(T(*c1), T(*c2), T(*end))
    paws = [(QPointF(-72, 89.5), 19.8), (QPointF(_lerp(72, 75, paw), _lerp(89.5, 64, paw)), _lerp(19.8, 14.5, paw))]
    ears = [QPolygonF([QPointF(k * x, Y(y)) for x, y in ((-50.5, 25.0), (-44.5, 7.5), (-29.0, 18.5))]) for k in (1, -1)]
    nose = QPainterPath(QPointF(-5.2, Y(74.6)));nose.lineTo(QPointF(5.2, Y(74.6)));nose.quadTo(QPointF(1.4, Y(80.8)), QPointF(0, Y(80.8)))
    nose.quadTo(QPointF(-1.4, Y(80.8)), QPointF(-5.2, Y(74.6)));nose.closeSubpath()
    mouth = QPainterPath(QPointF(-6.0, Y(83.0)));mouth.quadTo(QPointF(-3.0, Y(86.6)), QPointF(0, Y(83.2)));mouth.quadTo(QPointF(3.0, Y(86.6)), QPointF(6.0, Y(83.0)))
    return dict(body=body, eyes=eyes, pupil=pupil, tail=curl, paws=paws, paw=paw, ears=ears, nose=nose, mouth=mouth, iris=float(iris))


GROUND = 100.0  # the line the cat sits on, in CAT_BOX units: nothing of it is drawn below (D1-fix: the cat sits whole inside
                # its tile, and the tile inside the band; the ledge it used to peek over is gone, keyboard focus a mark under it)
FOCUS_MARK = ((-62.0, 101.8), (62.0, 101.8), 4.0)  # keyboard focus: a short eraser-pink mark under the cat, inside CAT_BOX
DETAIL = 2.6    # the graphite details' line in CAT_BOX units (about one pixel at the 44 px cat): the paws' outline, the toes
TAIL = 10.0     # the tail's stroke in CAT_BOX units


def cat_transform(rect):
    """(scale, dx, dy): CAT_BOX units into rect (bottom-aligned, centred, as large as fits), as paint_cat draws."""
    s = min(rect.width() / CAT_BOX.width(), rect.height() / CAT_BOX.height())
    return s, rect.center().x() - CAT_BOX.center().x() * s, rect.bottom() - CAT_BOX.bottom() * s


def cat_extent(params, outline=True):
    """The cat's drawn extent in CAT_BOX units for one pose, (left, top, right, bottom): the body, the paws with their
    graphite outline (HATCH DESK D2: half of DETAIL outside the paw), the lifted arm, the tail's round stroke, none of it below
    GROUND. Every pose's lies inside CAT_BOX: the tile is the room for every pose, whole.
    outline=False is the pale coat alone, what the graphite band shows of the cat: each paw's coat inside its graphite outline
    (the outline is drawn centred on the paw's edge, so half of DETAIL of the paw is graphite too). The integration of D2 and D3:
    the outline is graphite on the graphite band, about a pixel nobody sees, so the cat is placed and paired by its coat, as the
    band words are by their visible ink; the room (CAT_BOX, the button) keeps the outline."""
    from PySide6.QtGui import QPainterPathStroker
    parts = cat_paths(params);r = parts['body'].boundingRect();half = DETAIL / 2.0 if outline else -DETAIL / 2.0
    for centre, radius in parts['paws']:r = r.united(QRectF(centre.x() - radius - half, centre.y() - radius - half, 2 * (radius + half), 2 * (radius + half)))
    if parts['tail'] is not None:
        stroker = QPainterPathStroker();stroker.setWidth(TAIL);stroker.setCapStyle(Qt.RoundCap);stroker.setJoinStyle(Qt.RoundJoin)
        r = r.united(stroker.createStroke(parts['tail']).boundingRect())
    return r.left(), r.top(), r.right(), min(r.bottom(), GROUND)


def cat_ink(rect, params, outline=True):
    """The cat's drawn extent for one pose in rect's pixels, (left, top, right, bottom) (cat_extent through cat_transform);
    outline=False: its pale coat alone, by which the band places and pairs it."""
    s, dx, dy = cat_transform(rect);l, t, r, b = cat_extent(params, outline)
    return dx + l * s, dy + t * s, dx + r * s, dy + b * s


def mix(a, b, t):
    """Colour a moved t of the way to colour b (the iris going yellow with the pose's animation)."""
    a, b = QColor(a), QColor(b);t = min(1.0, max(0.0, float(t)))
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t), round(a.blue() + (b.blue() - a.blue()) * t))


def paint_cat(p, rect, params, coat=None, detail=None, edge=None):
    """The cat in rect (bottom-aligned, centred, as large as fits), sitting whole on its ground (nothing below GROUND): HATCH DESK
    D2, its silhouette in CAT_COAT (pale on the band), its eyes and paws in CAT_DETAIL graphite, the irises CAT_IRIS by the pose's
    iris number (graphite at rest, pencil yellow on hover and while the list is open; closed and without colour asleep), the nose
    and inner ears CAT_NOSE; with keyboard focus a short mark under it in the colour given (CAT_FOCUS, eraser pink)."""
    s, dx, dy = cat_transform(rect)
    parts = cat_paths(params);coat = QColor(CAT_COAT if coat is None else coat);detail = QColor(CAT_DETAIL if detail is None else detail)
    p.save();p.setRenderHint(QPainter.Antialiasing)
    p.translate(dx, dy);p.scale(s, s)
    p.setClipRect(QRectF(CAT_BOX.left(), CAT_BOX.top(), CAT_BOX.width(), GROUND - CAT_BOX.top()))  # it sits on its ground
    if parts['tail'] is not None:  # behind the body: the question-mark curl, no dot
        p.setPen(QPen(coat, TAIL, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush);p.drawPath(parts['tail'])
    p.setPen(Qt.NoPen);p.setBrush(coat);p.drawPath(parts['body'])
    p.setBrush(QColor(CAT_NOSE))
    for ear in parts['ears']:p.drawPolygon(ear)
    p.drawPath(parts['nose'])
    line = QPen(detail, DETAIL, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(QPen(detail, DETAIL * 0.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush);p.drawPath(parts['mouth'])
    iris = mix(detail, CAT_IRIS, parts['iris'])
    for centre, r, lid in parts['eyes']:
        if lid > 0.2:
            eye = QPainterPath();eye.addEllipse(centre, r, r * lid)
            p.setPen(Qt.NoPen);p.setBrush(iris);p.drawPath(eye)
            p.save();p.setClipPath(eye, Qt.IntersectClip);at = centre + parts['pupil']
            p.setBrush(detail);p.drawEllipse(at, 5.4, 7.4)                              # the graphite pupil
            p.setBrush(coat);p.drawEllipse(at + QPointF(-2.4, -3.0), 2.0, 2.0)           # a glint, so graphite eyes still look
            p.restore()
            p.setPen(line);p.setBrush(Qt.NoBrush);p.drawPath(eye)                       # the graphite rim round a yellow iris
        else:  # closed: a graphite lid line, the yellow gone
            lid_line = QPainterPath(centre + QPointF(-r * 0.86, -1.5));lid_line.quadTo(centre + QPointF(0, r * 0.62), centre + QPointF(r * 0.86, -1.5))
            p.setPen(QPen(detail, DETAIL * 1.25, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush);p.drawPath(lid_line)
    (left, lr), (right, rr) = parts['paws'];lifted = parts['paw']
    def paw(centre, radius, outline=True):
        p.setBrush(coat);p.setPen(line if outline else Qt.NoPen);p.drawEllipse(centre, radius, radius)
        p.setPen(line)                                                                  # two toes: three soft pads
        for k in (-1, 1):
            x = centre.x() + k * radius * 0.3;p.drawLine(QPointF(x, centre.y() + radius * 0.22), QPointF(x, centre.y() + radius * 0.66))
    paw(left, lr)
    if lifted > 0.02:  # the arm rises from the ground to the lifted paw, one piece with the body
        arm = QPainterPath(QPointF(56, 100));arm.lineTo(right + QPointF(-rr * .8, rr * .3));arm.lineTo(right + QPointF(rr * .9, rr * .2));arm.lineTo(QPointF(76, 100));arm.closeSubpath()
        p.setPen(Qt.NoPen);p.setBrush(coat);p.drawPath(arm)
    paw(right, rr)
    p.setClipping(False)
    if edge:
        (x1, y1), (x2, y2), width = FOCUS_MARK;p.setPen(QPen(QColor(edge), width, Qt.SolidLine, Qt.RoundCap));p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    p.restore()


def pose_pixmap(pose, height=220, dpr=1.0):
    """One pose drawn large on the band's graphite shading, where the cat lives (captures and the reference comparison)."""
    from .desk_qt import grain_tile
    from PySide6.QtGui import QBrush
    w = round(height * CAT_RATIO);pix = QPixmap(round(w * dpr), round(height * dpr));pix.setDevicePixelRatio(dpr)
    p = QPainter(pix);p.fillRect(QRectF(0, 0, w, height), QBrush(grain_tile()));paint_cat(p, QRectF(0, 0, w, height), POSES[pose]);p.end();return pix


INPUT = (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.Wheel, QEvent.TouchBegin)


class Cat(QObject):
    """The cat on its button: the pose machine, one short animation per change (none under Reduce motion), and the
    inactivity timer, restarted by any input to the program while the menu is closed. Input elsewhere never wakes a
    sleeping cat (movement stays tied to interaction with it); the pointer on it, the menu, or keyboard focus does."""
    def __init__(self, button, reduce_motion=lambda:False, idle_ms=IDLE_MS):
        super().__init__(button);self.button = button;self.reduce_motion = reduce_motion
        self.poses = CatPoses();self.pose = 'rest';self.params = self._from = self._to = POSES['rest']
        self.animation = QVariantAnimation(self);self.animation.setStartValue(0.0);self.animation.setEndValue(1.0)
        self.animation.setDuration(MOVE_MS);self.animation.setEasingCurve(QEasingCurve.OutCubic);self.animation.valueChanged.connect(self.step)
        self.idle = QTimer(self);self.idle.setSingleShot(True);self.idle.setInterval(idle_ms);self.idle.timeout.connect(lambda:self.show(self.poses.idle()))
        button.setMouseTracking(True)  # a pointer parked on a sleeping cat wakes it when it moves
        from PySide6.QtCore import QCoreApplication
        if QCoreApplication.instance() is not None:QCoreApplication.instance().installEventFilter(self)
        self.idle.start()

    def show(self, pose):
        """Move to pose: at once under Reduce motion, else one MOVE_MS animation from wherever the cat is now."""
        if pose == self.pose:return
        self.pose = pose;self._to = POSES[pose];self.animation.stop()
        if self.reduce_motion():self.params = self._to;self.button.update()
        else:self._from = self.params;self.animation.start()

    def step(self, t):self.params = self._to if t >= 1 else blend(self._from, self._to, float(t));self.button.update()

    def over(self):return self.button.rect().contains(self.button.mapFromGlobal(QCursor.pos()))

    def enter(self):self.show(self.poses.enter())

    def leave(self):self.show(self.poses.leave())

    def menu(self, shown):
        self.show(self.poses.menu(shown, None if shown else self.over()))
        if shown:self.idle.stop()
        else:self.idle.start()

    def wake(self):self.show(self.poses.wake())

    def eventFilter(self, obj, event):
        if event.type() in INPUT:
            if not self.poses.open:self.idle.start()
            if self.poses.asleep and obj is self.button and event.type() == QEvent.MouseMove:self.show(self.poses.enter())
        return False

    def paint(self, p, rect, focus=False):paint_cat(p, rect, self.params, edge=CAT_FOCUS if focus else None)
