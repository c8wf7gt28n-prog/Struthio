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
FACE_MARK = ('+------+', '|  >_  |', '+------+')
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


def kasandra_still(painter, target, host, slot, state, turn=0, zoom=1.0, matte=True):
    """Draw Kasandra's still for this slot and state over target (kasandra_art.choose: exact, then default, then quiet).
    True when a still was drawn; with none, the target gets the plain panel ground when `matte`."""
    from . import kasandra_art as art
    base = art.folder(host.root)
    scene = art.choose(base, slot, state, turn)
    width, height = round(target.width()), round(target.height())
    try:dpr = painter.device().devicePixelRatioF()
    except AttributeError:
        dpr = 1.0
    image = art.picture(base, scene, width, height, dpr, zoom) if scene is not None else QImage()
    if image.isNull():
        if matte:painter.fillRect(target, QColor(t.PANEL))
        return False
    painter.drawImage(QRectF(target.left(), target.top(), width, height), image)
    return True


@lru_cache(maxsize=2)
def kasandra_wordmark(folder):
    """The owner's wordmark, "kasandra protocol" in circuit traces (branding/kasandra/wordmark.webp), or a null image when
    its bytes are not the recorded ones (kasandra_art.mark)."""
    from .kasandra_art import mark
    path = mark(folder, 'wordmark.webp')
    return QImage(str(path)) if path is not None else QImage()


def draw_wordmark(painter, area, host, height):
    """The wordmark at the foot-left of an area, `height` pixels tall, over a soft shade so it reads on any still."""
    from . import kasandra_art
    mark = kasandra_wordmark(kasandra_art.folder(host.root))
    if mark.isNull() or height < 18 or area.width() < 240:return False
    width = min(area.width() * 0.46, height * mark.width() / mark.height());height = width * mark.height() / mark.width()
    box = QRectF(area.left() + 20, area.bottom() - height - 14, width, height)
    clear = QColor(t.GROUND);clear.setAlpha(0);shade = QColor(t.GROUND);shade.setAlpha(150)
    fade = QLinearGradient(0, box.top() - 24, 0, area.bottom());fade.setColorAt(0, clear);fade.setColorAt(1, shade)
    painter.fillRect(QRectF(area.left(), box.top() - 24, box.right() + 40 - area.left(), area.bottom() - box.top() + 24), fade)
    painter.save();painter.setRenderHint(QPainter.SmoothPixmapTransform);painter.setOpacity(0.94);painter.drawImage(box, mark);painter.restore()
    return True


class WorkshopStrip(QWidget):
    """Keep the workshop in the strip and give Stacy the worksheet evidence rail."""
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.folder = program(host.root) / 'branding' / 'boss'
        self.setAccessibleName('Local worksheet and After Midnight workshop illustration' if t.APPEARANCE == 'graphite'
                               else 'Local worksheet, and utility wires over rooftops at dusk')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(t.GROUND))
        font = QFont(t.MONO);font.setPixelSize(13);painter.setFont(font)
        painter.fillRect(13, 11, 7, 7, QColor(t.READY))
        painter.setPen(QColor(t.QUIET))
        painter.drawText(29, 18, '[ WORKSHEET · LOCAL WORKSPACE ]')
        target = QRectF(0, 28, self.width() - 1, self.height() - 33)
        image = midnight_plate(self.folder, 'workshop')
        if t.APPEARANCE == 'kasandra':      # her wires and rooftops above the worksheet
            kasandra_still(painter, target, self.host, 'worksheet_strip', 'viewing')
        elif image.isNull():
            draw_plate(painter, target, charcoal_workshop(self.folder), 0.22)
        else:
            region = QRectF(0, 0, image.width() * 0.64, image.height())
            draw_plate(painter, target, image, 0.44, region)
        painter.setPen(QPen(QColor(t.LINE_MID), 1));painter.drawRect(target)
        painter.end()


class ArtPanel(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.art_folder = program(host.root) / 'branding' / 'boss'
        self.setObjectName('BossArt');self.setProperty('paperFunctionalInk', True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAccessibleName('Stacy in the After Midnight workshop' if t.APPEARANCE == 'graphite' else 'Kasandra in her office')
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.limit = None     # the most height Home can give the picture without scrolling (TodayPage.fit_art); None: no limit
        self.opened = 0       # Kasandra: the Office alternates its stills each time it is shown again, and keeps one while it is open
        self.refresh()

    def showEvent(self, event):
        self.opened += 1
        super().showEvent(event)

    def refresh(self):
        self.mode = self.host.session.state.get('desk_art', 'illustrated')
        self.setFixedHeight(self.plate_height())
        self.setVisible(self.mode != 'clean');self.update()

    LEAST = 96       # the shortest the picture gives way to, so that Home fits its window (TodayPage.fit_art)

    def plate_height(self):
        if self.mode == 'illustrated':
            full = min(368, max(112, self.width() // 3))
            return full if getattr(self, 'limit', None) is None else max(self.LEAST, min(full, int(self.limit)))
        return 0 if self.mode == 'clean' else 112

    def resizeEvent(self, event):
        height = self.plate_height()
        if self.height() != height:
            self.setFixedHeight(height)
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(t.LINE), 1));p.drawLine(0, self.height()-1, self.width(), self.height()-1)
        if self.mode == 'illustrated' and t.APPEARANCE == 'kasandra':
            from .kasandra_art import daily_turn
            area = QRectF(0, 0, self.width(), self.height()-3)
            kasandra_still(p, area, self.host, 'office_banner', 'idle', daily_turn(self.opened))
            draw_wordmark(p, area, self.host, min(88.0, area.height() * 0.26))      # the owner's wordmark, at the foot of her office
        elif self.mode == 'illustrated':
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
            font = QFont(t.MONO);font.setPixelSize(12);p.setFont(font)
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
                                'journal': 'Stacy in the research journal', 'face': 'Stacy, the assistant'}[kind]
                               if t.APPEARANCE == 'graphite' else {'portrait': 'Kasandra beside the worksheet', 'bracket': 'ASCII bracket illustration',
                                'journal': 'Kasandra in the research journal', 'face': 'Kasandra, the assistant'}[kind])
        if t.APPEARANCE == 'kasandra' and kind != 'bracket':      # her still follows the work: painted again when an act ends, and every two seconds
            from PySide6.QtCore import QTimer
            from . import kasandra_art
            kasandra_art.watch(host, self)
            self._state = None
            self._watch = QTimer(self);self._watch.setInterval(2000);self._watch.timeout.connect(self._follow);self._watch.start()
        self.refresh()

    def _follow(self):
        """Kasandra: paint again only when the state of the work has changed (a paint costs nothing else)."""
        if not self.isVisible():return
        from .kasandra_art import current_state
        state = current_state(self.host)
        if state != self._state:self._state = state;self.update()

    def kasandra_state(self):
        from .kasandra_art import current_state
        self._state = current_state(self.host)
        return self._state

    def set_available(self, available):
        if self.available != available:
            self.available = available
            self.refresh()

    def refresh(self):
        self.mode = self.host.session.state.get('desk_art', 'illustrated')
        visible = self.available and self.mode != 'clean'
        if self.kind == 'face':              # the assistant's face in Talk: a small still square beside her name, or nothing
            visible = visible and (t.APPEARANCE == 'kasandra' or not midnight_plate(self.art_folder).isNull())
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
        if t.APPEARANCE == 'kasandra' and self.kind != 'face':      # the ASCII rail samples her quiet still
            from . import kasandra_art as art
            base = art.folder(self.host.root);scene = art.choose(base, 'assistant_rail', 'idle')
            path = art.usable(base, scene) if scene is not None else None
            if path is not None:return art.source(path, scene['id'])
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
        if self.kind != 'bracket' and self.mode == 'illustrated' and t.APPEARANCE == 'kasandra':
            target = QRectF(self.rect())      # Kasandra at what the work is doing: notes while it runs, a hand by Enter while it waits for you
            if self.kind == 'journal':target.setLeft(self.width() * 0.54)
            kasandra_still(painter, target, self.host, 'assistant_rail', self.kasandra_state(), zoom=2.2 if self.kind == 'face' else 1.0)
            if self.kind == 'face':
                painter.setPen(QPen(QColor(t.LINE_MID), 1));painter.setBrush(Qt.NoBrush)
                painter.drawRect(target.adjusted(0.5, 0.5, -0.5, -0.5))
            painter.end()
            return
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
                painter.setPen(QPen(QColor(t.LINE_MID), 1));painter.setBrush(Qt.NoBrush)
                painter.drawRect(target.adjusted(0.5, 0.5, -0.5, -0.5))
            else:
                draw_plate(painter, target, self.portrait(), 0.24)
            painter.end()
            return
        font = QFont(t.MONO)
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
    glow = QMenu('Glow', menu);levels = QActionGroup(glow);levels.setExclusive(True);lit = {}
    for key, word, _ in t.GLOW_LEVELS:
        line = glow.addAction(word);line.setCheckable(True);levels.addAction(line);lit[key] = line
        line.triggered.connect(lambda checked=False, key=key:choose_glow(host, key))
    glow.aboutToShow.connect(lambda:lit.get(host.session.state.get('glow', t.GLOW_OPENS), lit[t.GLOW_OPENS]).setChecked(True))
    menu.addMenu(glow)
    looks = QMenu('Appearance', menu);kinds = QActionGroup(looks);kinds.setExclusive(True);looked = {}
    for key, word in t.APPEARANCES:      # the whole window: Graphite (pencil and amber) or Kasandra (indigo, her art follows the work)
        line = looks.addAction(word);line.setCheckable(True);kinds.addAction(line);looked[key] = line
        line.setToolTip(APPEARANCE_WORDS[key]);line.setStatusTip(APPEARANCE_WORDS[key])
        line.triggered.connect(lambda checked=False, key=key:choose_appearance(host, key))
    looks.aboutToShow.connect(lambda:looked.get(chosen_look(host), looked['graphite']).setChecked(True))
    menu.addMenu(looks)
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


APPEARANCE_WORDS = {'graphite': 'Graphite: pencil, paper and amber, as it has always been',
                    'kasandra': 'Kasandra: indigo, a typewriter face for headings, and her art following the state of the work'}


def chosen_look(host):
    """The appearance the session keeps for the next start (what is in force now is boss_theme.APPEARANCE)."""
    try:value = host.session.state.get('appearance', t.APPEARANCE)
    except Exception:  # noqa: BLE001 - a host without a session: what is in force
        value = t.APPEARANCE
    return value if value in dict(t.APPEARANCES) else 'graphite'


def choose_appearance(host, key, ask=True):
    """Keep the appearance for the next start, and offer to start again now. The colours are read once, when Graphite
    starts (every page is built in them), so a change cannot be put in force in a running window."""
    if key not in dict(t.APPEARANCES):return False
    host.session.state['appearance'] = key;host.session.save()
    word = dict(t.APPEARANCES)[key]
    if key == t.APPEARANCE:
        host.statusBar().showMessage(word + ' is the appearance in use.', 5000);return True
    if ask:
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(host, 'Appearance', word + ' is used from the next start. Start Graphite again now? '
                                'It saves this window first.') == QMessageBox.Yes:
            from .shell2 import relaunch
            relaunch(host, host.root, drop=('GRAPHITE_APPEARANCE',));return True
    host.statusBar().showMessage(word + ' is used from the next start.', 7000)
    return True


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
        level = t.glow()
        glow = QGraphicsDropShadowEffect(widget);glow.setOffset(0, 0);glow.setBlurRadius(blur * (0.6 + 0.4 * level))
        ink = QColor(colour);ink.setAlphaF(min(1.0, alpha * (0.85 + 0.15 * level)));glow.setColor(ink);widget.setGraphicsEffect(glow)
    else:
        widget.setGraphicsEffect(None)


def waits(button, host, yes=True):
    """A button that applies a change when the owner presses it waits for the owner, and what waits for the owner glows in
    amber: the Approve of a change put up in Talk is lit as the Field's Approve is. `yes` False when it has been pressed."""
    button.setProperty(WAITS, bool(yes));lamp(button, t.OWNER, bool(yes) and button.isEnabled() and glows(host))
    if t.APPEARANCE == 'kasandra':      # her hand goes to Enter at once (and leaves it), not at the next look
        from .kasandra_art import nudge
        nudge(host)


def set_glow(host):
    """Put the session's choice of glow in force (boss_theme.GLOW). Called when a window starts and when the choice changes."""
    try:chosen = host.session.state.get('glow', t.GLOW_OPENS)
    except Exception:  # noqa: BLE001 - a host without a session: what the desk opens with
        chosen = t.GLOW_OPENS
    t.GLOW[0] = next((level for key, _, level in t.GLOW_LEVELS if key == chosen), dict((k, v) for k, _, v in t.GLOW_LEVELS)[t.GLOW_OPENS])
    stage = getattr(host, 'hologram', None)
    if stage is not None:stage.wake_or_sleep()
    return t.GLOW[0]


def choose_glow(host, key):
    if key not in [k for k, _, _ in t.GLOW_LEVELS]:return
    from PySide6.QtWidgets import QPushButton
    host.session.state['glow'] = key;host.session.save();set_glow(host)
    for button in host.findChildren(QPushButton):       # a lamp is made at one strength: made again at the new one
        if button.property(WAITS):
            lamp(button, t.OWNER, False);lamp(button, t.OWNER, button.isEnabled() and glows(host))
    choose_art(host, host.session.state.get('desk_art', 'illustrated'))     # everything that glows is drawn again
    for widget in host.findChildren(QWidget):QWidget.update(widget)      # (a list or a tree has an update of its own that wants a row)


def choose_art(host, mode):
    if mode not in ART_MODES:return
    host.session.state['desk_art'] = mode;host.session.save()
    from . import pointer
    pointer.restyle(mode != 'clean')           # the pointer keeps its green on the Clean desk and drops its glow
    for kind in (ArtPanel, PanelInk):
        for panel in host.findChildren(kind):panel.refresh()
    stage = getattr(host, 'hologram', None)      # her hologram: shown, in characters, or put away with the desk's art
    if stage is not None:stage.place_now();stage.update()
    field = getattr(host, 'field_page', None)      # the Field keeps Stacy's rail (or the ASCII mark, or nothing) in step
    if field is not None:
        field.view.art_mode = mode;field.view.texture = mode != 'clean';field.view.update()
    bar = getattr(host, 'type_bar', None)
    if bar is not None:
        bar.align();bar.update()                   # the writing line's lit edge follows the desk too
    from PySide6.QtWidgets import QPushButton
    for button in host.findChildren(QPushButton):  # every Approve that still waits
        if button.property(WAITS):lamp(button, t.OWNER, button.isEnabled() and mode != 'clean')
    from .desktop_header_qt import DesktopMonitors
    for meters in host.findChildren(DesktopMonitors):meters.relight()      # the live readings glow, or not, with the desk
