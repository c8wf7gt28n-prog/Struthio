"""Optional BOSS ornament, separate from working documents and exported material."""
from functools import lru_cache
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QActionGroup, QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget
from . import boss_theme as t
from .locations import program

ART_MODES = ('illustrated', 'ascii', 'clean')
WORKSHOP_PLATE = 'Workshop in the rain.png'
CHARCOAL_PLATE = 'Workshop in charcoal.webp'
MIDNIGHT_PORTRAIT = 'Stacy after midnight.webp'
FACE_MARK = ('+------+', '| staC |', '+------+')
FACE = (0.262, 0.086, 0.488, 0.366)       # her face in that plate: left, top, width, height, as parts of the plate
MIDNIGHT_WORKSHOP = 'Workshop after midnight.webp'
ART_PLATES = (WORKSHOP_PLATE, 'RISC is good.png', 'Struthio rider.png',
              'Brain on Disk.png', 'City after dark.png')
BRACKET = ('           +-----+', '          /     /|', '         +-----+ |', '         |  o  | |',
           '   +-----+     | |', '  /  o         | +', ' +-------------+/', ' +-------------+')


@lru_cache(maxsize=2)
def workshop_plate(folder):
    return QImage(str(folder / 'plates' / WORKSHOP_PLATE))


def operator_crop(image):
    if image.isNull():
        return image
    crop = image.rect()
    crop.setCoords(round(image.width() * 0.54), 0, round(image.width() * 0.96), round(image.height() * 0.72))
    return image.copy(crop)


@lru_cache(maxsize=2)
def charcoal_workshop(folder):
    image = QImage(str(folder / 'plates' / CHARCOAL_PLATE))
    return workshop_plate(folder) if image.isNull() else image


@lru_cache(maxsize=4)
def midnight_plate(folder, scene='portrait'):
    name = MIDNIGHT_WORKSHOP if scene == 'workshop' else MIDNIGHT_PORTRAIT
    return QImage(str(folder / 'plates' / name))


def draw_plate(painter, target, image, vertical_focus, region=None):
    if image.isNull() or target.isEmpty():
        return
    region = QRectF(image.rect()) if region is None else region
    scale = max(target.width() / region.width(), target.height() / region.height())
    width, height = target.width() / scale, target.height() / scale
    source = QRectF(region.left() + (region.width() - width) / 2,
                    region.top() + (region.height() - height) * vertical_focus, width, height)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(target, image, source)


class WorkshopStrip(QWidget):
    """Keep the workshop in the strip and give Stacy the worksheet evidence rail."""
    def __init__(self, host):
        super().__init__()
        self.folder = program(host.root) / 'branding' / 'boss'
        self.setAccessibleName('Local worksheet and After Midnight workshop illustration')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(t.GROUND))
        font = QFont('IBM Plex Mono');font.setPixelSize(13);painter.setFont(font)
        painter.fillRect(13, 11, 7, 7, QColor(t.READY))
        painter.setPen(QColor(t.QUIET))
        painter.drawText(29, 18, '[ WORKSHEET · LOCAL WORKSPACE ]')
        target = QRectF(0, 28, self.width() - 1, self.height() - 33)
        image = midnight_plate(self.folder, 'workshop')
        if image.isNull():
            draw_plate(painter, target, charcoal_workshop(self.folder), 0.22)
        else:
            region = QRectF(0, 0, image.width() * 0.64, image.height())
            draw_plate(painter, target, image, 0.44, region)
        painter.setPen(QPen(QColor(t.LINE_STRONG), 1));painter.drawRect(target)
        painter.end()


class ArtPanel(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.art_folder = program(host.root) / 'branding' / 'boss'
        self.setObjectName('BossArt');self.setProperty('paperFunctionalInk', True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAccessibleName('Stacy in the After Midnight workshop')
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.refresh()

    def refresh(self):
        self.mode = self.host.session.state.get('desk_art', 'illustrated')
        self.setFixedHeight(self.plate_height())
        self.setVisible(self.mode != 'clean');self.update()

    def plate_height(self):
        if self.mode == 'illustrated':
            return min(368, max(112, self.width() // 3))
        return 0 if self.mode == 'clean' else 112

    def resizeEvent(self, event):
        height = self.plate_height()
        if self.height() != height:
            self.setFixedHeight(height)
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        if self.mode == 'illustrated':
            image = midnight_plate(self.art_folder, 'workshop')
            target = QRectF(0, 0, self.width(), self.height()-3)
            focus = 0.28
            if image.isNull():
                image = charcoal_workshop(self.art_folder)
                focus = 0.05
            if not image.isNull():
                draw_plate(p, target, image, focus)
            else:
                from PySide6.QtSvg import QSvgRenderer
                if not hasattr(self, '_art'):
                    self._art = QSvgRenderer(str(self.art_folder / 'night-signal.svg'), self)
                self._art.render(p, target)
        else:
            font = QFont('IBM Plex Mono');font.setPixelSize(12);p.setFont(font)
            p.setPen(QColor(t.QUIET))
            lines = ('// GRAPHITE  :  WORK IN PROGRESS',
                     '   [ evidence ]  [ methods ]  [ useful work ]',
                     '   / / /   a computer you can work beside   / / /',
                     '// your tools. your records. your machine.')
            for index, line in enumerate(lines):p.drawText(0, 22 + index * 22, line)
            p.setPen(QColor(t.AMBER_EDGE));p.drawText(max(0, self.width()-52), 25, '[>_]')
        p.end()


class PanelInk(QWidget):
    """Compact worksheet ornament. Its visibility follows the view and artwork preference."""
    def __init__(self, host, kind):
        super().__init__()
        self.host = host
        self.art_folder = program(host.root) / 'branding' / 'boss'
        self.kind = kind
        self.available = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Fixed if kind == 'face' else QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setAccessibleName({'portrait': 'Stacy in the worksheet evidence rail', 'bracket': 'ASCII bracket illustration',
                                'journal': 'Stacy in the research journal', 'face': 'Stacy, the assistant'}[kind])
        self.refresh()

    def set_available(self, available):
        if self.available != available:
            self.available = available
            self.refresh()

    def refresh(self):
        self.mode = self.host.session.state.get('desk_art', 'illustrated')
        visible = self.available and self.mode != 'clean'
        if self.kind == 'face':              # the assistant's face in Talk: a small still square beside her name, or nothing
            visible = visible and not midnight_plate(self.art_folder).isNull()
            self.setFixedWidth(self.plate_height() if visible else 0)
        self.setFixedHeight(self.plate_height() if visible else 0)
        self.setVisible(visible)
        self.update()

    def plate_height(self):
        if self.kind == 'portrait':
            return min(self.width(), max(130, self.host.height() - 500))
        if self.kind == 'face':              # follows the reading size, as the name beside it does
            return round(84 * float((getattr(self.host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0)
        return 116 if self.kind == 'journal' else 146

    def resizeEvent(self, event):
        if self.kind == 'portrait' and self.available and self.mode != 'clean':
            height = self.plate_height()
            if self.height() != height:self.setFixedHeight(height)
        super().resizeEvent(event)

    def face_region(self):
        image = midnight_plate(self.art_folder)
        return QRectF(image.width() * FACE[0], image.height() * FACE[1], image.width() * FACE[2], image.height() * FACE[3])

    def portrait(self):
        image = midnight_plate(self.art_folder)
        if self.kind == 'face':
            if not hasattr(self, '_face'):self._face = image.copy(self.face_region().toRect())
            return self._face
        if not image.isNull():
            return image
        if self.mode == 'illustrated':
            if not hasattr(self, '_charcoal_crop'):
                self._charcoal_crop = operator_crop(charcoal_workshop(self.art_folder))
            if not self._charcoal_crop.isNull():
                return self._charcoal_crop
        if not hasattr(self, '_fallback_portrait'):
            image = operator_crop(workshop_plate(self.art_folder))
            if image.isNull():
                name = 'journal-operator.webp' if self.kind == 'journal' else 'preview-operator.webp'
                image = QImage(str(self.art_folder / name))
            self._fallback_portrait = image
        return self._fallback_portrait

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.kind != 'bracket' and self.mode == 'illustrated':
            target = QRectF(self.rect())
            if self.kind == 'journal':
                target.setLeft(self.width() * 0.54)
                focus = 0.16 if not midnight_plate(self.art_folder).isNull() else 0.38
                draw_plate(painter, target, self.portrait(), focus)
                shade = QColor(t.GROUND)
                clear = QColor(shade);clear.setAlpha(0)
                fade_width = target.width() * 0.35
                fade = QLinearGradient(target.left(), 0, target.left() + fade_width, 0)
                fade.setColorAt(0, shade);fade.setColorAt(1, clear)
                painter.fillRect(QRectF(target.left(), 0, fade_width, target.height()), fade)
            elif self.kind == 'face':
                draw_plate(painter, target, self.portrait(), 0.5)
                painter.setPen(QPen(QColor(t.LINE_STRONG), 1));painter.setBrush(Qt.NoBrush)
                painter.drawRect(target.adjusted(0.5, 0.5, -0.5, -0.5))
            else:
                draw_plate(painter, target, self.portrait(), 0.24)
            painter.end()
            return
        font = QFont('IBM Plex Mono')
        font.setPixelSize(max(12, self.height() // 6) if self.kind == 'face' else 15 if self.kind == 'bracket' else 12 if self.kind == 'journal' else 8)
        painter.setFont(font)
        painter.setPen(QColor(t.TEXT if self.kind in ('bracket', 'face') else t.QUIET))
        metrics = QFontMetrics(font)
        if self.kind == 'face':              # the ASCII desk: her mark in plain characters, readable, not a picture squeezed into cells
            lines = FACE_MARK
        elif self.kind == 'bracket':
            lines = BRACKET
        elif self.kind == 'journal':
            if not hasattr(self, '_antenna'):
                try:
                    self._antenna = (program(self.host.root) / 'branding/boss/roof-antenna.txt').read_text(encoding='ascii').splitlines()
                except (OSError, UnicodeError):
                    self._antenna = []
            lines = self._antenna
        else:
            # Real character cells, sampled only when the display width changes.
            columns = min(60, max(1, self.width() // metrics.horizontalAdvance('M')))
            rows = min(32, max(1, self.height() // metrics.height()))
            key = (columns, rows)
            if key != getattr(self, '_character_size', None):
                image = self.portrait().scaled(columns, rows, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                ramp = ' .:-=+*#%@'
                self._characters = tuple(''.join(ramp[image.pixelColor(x, y).lightness() * len(ramp) // 256]
                                                 for x in range(columns)) for y in range(rows)) if not image.isNull() else ()
                self._character_size = key
            lines = self._characters
        width = metrics.horizontalAdvance(max(lines, key=len, default=''))
        x = max(0, self.width() - width - 20 if self.kind == 'journal' else (self.width() - width) // 2)
        top = max(0, (self.height() - len(lines) * metrics.height()) // 2) if self.kind == 'face' else 0
        for row, line in enumerate(lines):
            painter.drawText(x, top + metrics.ascent() + row * metrics.height(), line)
        painter.end()


def appearance_menu(host):
    menu = QMenu('Desk artwork', host)
    group = QActionGroup(menu);group.setExclusive(True)
    actions = {}
    for key, word in zip(ART_MODES, ('Illustrated', 'ASCII', 'Clean')):
        action = menu.addAction(word);action.setCheckable(True);group.addAction(action);actions[key] = action
        action.triggered.connect(lambda checked=False, mode=key:choose_art(host, mode))
    menu.addSeparator()
    menu.addMenu(host.idle_display.menu(menu))
    plates = QMenu('Art plates', menu)
    menu.addMenu(plates)
    folder = program(host.root) / 'branding' / 'boss' / 'plates'
    names = tuple(name for name in (MIDNIGHT_PORTRAIT, MIDNIGHT_WORKSHOP, CHARCOAL_PLATE)
                  if (folder / name).is_file()) + ART_PLATES
    for name in names:
        asset = folder / name
        action = plates.addAction(asset.stem)
        action.setEnabled(asset.is_file())
        action.triggered.connect(lambda checked=False, path=asset:host.open_in_viewer(path))
    def sync():
        mode = host.session.state.get('desk_art', 'illustrated')
        actions[mode].setChecked(True)
    menu.aboutToShow.connect(sync);sync()
    return menu


WAITS = 'waitsForOwner'        # on a button that applies a change when the owner presses it: it glows amber while it waits


def glows(host):
    """Whether this desk has glow: the Illustrated and ASCII desks do; the Clean desk has none, as it has no other ornament."""
    try:return host.session.state.get('desk_art', 'illustrated') != 'clean'
    except Exception:  # noqa: BLE001 - a host without a session (a check, a bare window): no ornament
        return False


def lamp(widget, colour, on=True, blur=14.0, alpha=0.85):
    """A still glow round a small widget: a drop shadow with no offset, in the colour given. For a button or a reading, never
    for a place that is typed in (it would be drawn through a picture at every blink of the cursor) and never for
    something large or scrolling."""
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    if bool(on) == (widget.graphicsEffect() is not None):return
    if on:
        glow = QGraphicsDropShadowEffect(widget);glow.setOffset(0, 0);glow.setBlurRadius(blur)
        ink = QColor(colour);ink.setAlphaF(alpha);glow.setColor(ink);widget.setGraphicsEffect(glow)
    else:
        widget.setGraphicsEffect(None)


def waits(button, host, yes=True):
    """A button that applies a change when the owner presses it waits for the owner, and what waits for the owner glows in
    amber: the Approve of a change put up in Talk is lit as the Field's Approve is. `yes` False when it has been pressed."""
    button.setProperty(WAITS, bool(yes));lamp(button, t.AMBER_EDGE, bool(yes) and button.isEnabled() and glows(host))


def choose_art(host, mode):
    if mode not in ART_MODES:return
    host.session.state['desk_art'] = mode;host.session.save()
    from . import pointer
    pointer.restyle(mode != 'clean')           # the pointer keeps its green on the Clean desk and drops its glow
    for kind in (ArtPanel, PanelInk):
        for panel in host.findChildren(kind):panel.refresh()
    field = getattr(host, 'field_page', None)      # the Field keeps Stacy's rail (or the ASCII mark, or nothing) in step
    if field is not None:
        field.view.art_mode = mode;field.view.texture = mode != 'clean';field.view.update()
    bar = getattr(host, 'type_bar', None)
    if bar is not None:
        bar.align();bar.update()                   # the writing line's lit edge follows the desk too
    from PySide6.QtWidgets import QPushButton
    for button in host.findChildren(QPushButton):  # every Approve that still waits
        if button.property(WAITS):lamp(button, t.AMBER_EDGE, button.isEnabled() and mode != 'clean')
    from .desktop_header_qt import DesktopMonitors
    for meters in host.findChildren(DesktopMonitors):meters.relight()      # the live readings glow, or not, with the desk
