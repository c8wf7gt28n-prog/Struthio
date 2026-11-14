"""The desk's lower writing band and its four input modes.

Assistant gives ordinary language to staC on Enter. Ctrl+Enter sends typed
staC through the console. Prefix `explain` to preview a plan. A leading slash
selects a Kernel operation. Terminal uses the account's configured shell.
Search opens workspace results. Log filters the Events or Network stream.

Assistant, Terminal, and Log have visible controls. Ctrl+K and a leading `?`
open Search. The saved mode keys also preserve older targets and histories.
The active mode supplies the field's accessible hint. `poem` is the placeholder.
"""
from __future__ import annotations
from . import boss_theme as _bt
from .assistant_identity import named
from .text_prompts import writing_prompt
from PySide6.QtCore import Qt, QTimer, QEvent, QSize
from PySide6.QtWidgets import QDockWidget, QWidget, QLabel, QPushButton
from .shell2 import button

STREAMS_WORDS = (('events', 'Events'), ('network', 'Network'))  # log_qt.STREAMS, without importing the view

# 0.5.3: the one line, and whom it is typed to. The owner: "I like the idea of one master typing line that I select whom
# I'm typing to ... terminal console open, communication with the assistant, a log, system log, network log, web
# search, system search, URL". All five stand to the left of the line now, by name: Stacy, Terminal, Search, Web, Log.
# (Search was reached only by a key or a leading ?; Web is new.) An address typed in any of them goes to Web by itself.
MODES = (('slate', 'Assistant'), ('shell', 'Terminal'), ('find', 'Search'), ('web', 'Web'), ('log', 'Log'))
TARGETS = MODES                                   # Preserve the mode keys used by existing callers.
PRIMARY_TARGETS = ('slate', 'shell', 'find', 'web', 'log')
SHOWN = {'slate': named('Stacy')}                        # the word on the strip where it is not the mode's own label
WEB_SEARCH = 'https://duckduckgo.com/?q='         # where words typed to Web are searched for: in the owner's own browser
ADDRESS_STARTS = ('http://', 'https://', 'www.')
# Endings that are a file's far more often than a site's: a bare name ending so is words, not an address.
FILE_ENDINGS = frozenset('txt md pdf py gd json csv tsv png jpg jpeg gif svg zip tar gz log sh c h cpp rs go js ts html htm css xml yml yaml toml ini cfg doc docx odt ods xls xlsx ppt tscn godot wav mp3 mp4'.split())
QUIET_TARGETS = ()                                # Find and Kernel were the quiet words; Kernel's home is Commands now
MAPPED = {'slate': 'slate', 'stac': 'slate', 'kernel': 'slate', 'shell': 'shell', 'find': 'find', 'web': 'web', 'log': 'log'}  # old targets -> modes
CONSOLE_PAGE = {'slate': 'stac', 'shell': 'shell', 'find': 'find', 'log': 'log'}  # the working area's page for each mode
JUMPS = {'@': 'stac', '/': 'kernel', '?': 'find', '$': 'shell'}  # a first character typed into an empty line
# 0.5.3: the hints say what to type and name no key (the owner, 13 November 2026: no key printed anywhere; every key still works).
HINTS = {'slate': 'ask in your own words, or type a line and the arrow runs it  ·  / runs an operation by name',
         'kernel': 'an operation by name: ' + 'files.list path=Slate  ·  help copies.review  ·  ops agenda',  # the example: an operation's real argument
         'find': 'files and their words, the cabinet, settings, commands and the Timeline',
         'shell': 'a command, in your Files folder',
         'web': 'an address to open, or words to search for, in your own browser',
         'log': "words in Graphite's events"}
SENDS = {'slate': named('Ask Stacy'), 'shell': 'Run it in the Terminal', 'find': 'Search the workspace', 'web': 'Open it in your browser', 'log': 'Filter the Log'}
READS = ('stac', 'inspect', 'word')      # what the line can be read as that the arrow runs itself, instead of asking
TIPS = {'slate': named('Stacy: ask in your own words, or type a line yourself'),
        'shell': 'Terminal: type to Debian through your configured shell, in your Files folder',
        'find': 'Search: files and their words across the workspace',
        'web': 'Web: an address is opened, and words are searched for, in this computer’s own browser. Graphite itself fetches nothing.',
        'log': "Log: follow Graphite's events or this computer's network above the line"}
CAP_SCALE_MAX = 1.4    # sizes that are not text follow the interface size up to this factor (desk_qt.SCALE_MAX)
NAV_RANGE = (160, 600) # session.py keeps the same bounds for the saved widths
SIM_RANGE = (160, 900)
FACTORY_RIGHT = 330    # the right column's shipped width before the desk (qt_app._apply_default_layout); with the left's 285, no owner's choice
NOTE_MS = 10000        # a status message is shown in the bar for at most this long; the destination hint returns
HATCH_ICON = 44        # UI-03: the egg's height on the Hatch tile at the default size; GRAPHITE-01: the cat's height, the same


# Pure arithmetic (tests_integrated/test_frame.py exercises these without a QApplication; the desk's own rules are
# workbench/desk_qt.py and tests_integrated/test_desk.py) -----------------------------------------------------------------

def hatch_icon_px(scale):
    """The cat's height: 44 px at 14 pt, scaled with the interface size up to 1.4 (62 px), never smaller."""
    return round(HATCH_ICON * min(max(float(scale), 1.0), CAP_SCALE_MAX))


def cat_tile(scale):
    """GRAPHITE-01: the cat's drawing on the menu button, (width, height): hatch_icon_px high, its own proportion wide."""
    from .graphite_brand import CAT_RATIO
    h = hatch_icon_px(scale);return round(h * CAT_RATIO), h


def centre_floor(scale):
    """The workspace's floor: 400 px at the default size, scaled with the interface up to 1.4 (desk_qt.centre_floor)."""
    from .desk_qt import centre_floor as floor
    return floor(scale)


def saved_width(value, bounds, default):
    """A saved column width, or the default when the profile has none in range."""
    low, high = bounds
    return value if type(value) is int and low <= value <= high else default


def fit_secondary(widths, room):
    """Explicit elision (before D1-fix; the band now sets its words smaller instead, TypeBar.fit_px): when the secondary
    words of a row fit the room they are whole; otherwise they share it equally. Returns the width allotted to each word."""
    widths = [int(w) for w in widths]
    if not widths:return []
    if sum(widths) <= room:return widths
    share = max(0, int(room) // len(widths))
    return [min(w, share) for w in widths]


def destination_hint(key, word=None, hint=None):
    """Combine the mode label with its instructions or the supplied detail."""
    mode = MAPPED.get(key, 'slate')
    hint_key = 'kernel' if key == 'kernel' else mode
    return (word or SHOWN.get(mode, dict(TARGETS)[mode])) + ' · ' + (hint or HINTS[hint_key])


NO_LOGIN = ('nologin', 'false')
OPTION_L = ('bash', 'zsh', 'sh', 'dash', 'ksh', 'mksh', 'fish', 'yash', 'posh')  # shells that take -l (a login shell's profile)


def configured_shell(login=None, environ=None, usable=None):
    """The shell the Shell mode types to: the account's login shell (the account database, what chsh sets: Debian's configured
    shell for this user), else $SHELL, else /bin/sh. A shell that refuses logins (nologin, false) or is not an executable file
    is passed over. login, environ and usable are for tests (the pwd entry's shell, the environment, an executable check)."""
    import os
    if login is None:
        try:
            import pwd
            login = pwd.getpwuid(os.getuid()).pw_shell
        except (ImportError, KeyError, OSError):login = ''
    environ = os.environ if environ is None else environ
    usable = usable or (lambda path:os.path.isfile(path) and os.access(path, os.X_OK))
    for path in (login, environ.get('SHELL', ''), '/bin/sh'):
        if path and os.path.basename(path) not in NO_LOGIN and usable(path):return path
    return '/bin/sh'


def shell_label(path):
    """The Shell mode's word: Bash only when the configured shell is bash itself (its file name is bash), otherwise Shell."""
    import os
    return 'Bash' if os.path.basename(str(path or '')) == 'bash' else 'Shell'


def shell_argv(path, text):
    """How the configured shell runs one line: a login shell's profile (-l) where the shell takes it, then -c and the line."""
    import os
    return [path] + (['-l'] if os.path.basename(path) in OPTION_L else []) + ['-c', text]


def stac_hint_kind(text):
    """Classify an explicit preview or a locally parsed staC line for the hint."""
    text = str(text or '').replace('​', '').strip()
    if not text or text[0] in '/?$':return None
    try:
        from sdk.cli.arc1cli import typed_pipeline
        if text.startswith('@'):
            from .stacy_language import source
            line, _ = source(text);typed_pipeline.parse(line);return 'stac'
        from .stac_bridge import compile_program, route_program
        operation, arguments = route_program(text, allow_inspection=True)
        if operation == 'stac.inspect':return 'inspect'
        if operation == 'stac.run':
            compile_program(arguments['program']);return 'stac'
        from .engineering_kernel import CAPABILITIES
        operation = typed_pipeline.parse(text)['call']['operation']
        if operation in CAPABILITIES and CAPABILITIES[operation] == 'read' and not operation.startswith('language.'):
            return 'stac'
    except Exception:
        return None


def parses_as_stac(text):
    """Whether Ctrl+Enter runs the line as a staC program."""
    return stac_hint_kind(text) == 'stac'


class ExpandButton(QPushButton):
    """The line's expand (the owner, 13 November 2026: "The type bar at the bottom needs a optional expand to show more
    data, like if I'm trying to use the terminal"). The room above the line always had three sizes (one line, half, tall)
    but their words were hidden and the only way to them was a menu. This is one control at the left end of the line that
    steps through them: one chevron up at rest (show more), two when half open (taller still), one down when tall (back to
    one line). What shows in the room is the page of whoever is being typed to: Stacy's answers, the Terminal's output,
    Search's results, or the Log with its own choice of stream at its top."""
    SAYS = ('Show more above the line', 'Taller still', 'Back to one line')
    SIZES = ('one line', 'half the window', 'tall')

    def __init__(self, bar):
        super().__init__(bar);self.bar = bar;self.level = -1;self.setObjectName('TypeExpand');self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus);self.setAttribute(Qt.WA_Hover, True);self.clicked.connect(self.step);self.say()

    def step(self):
        console = self.bar.console;console.set_size((int(console.size_level) + 1) % 3);self.say()

    def say(self):
        level = max(0, min(2, int(getattr(self.bar.console, 'size_level', 0) or 0)))
        if level == self.level:return
        self.level = level;self.setToolTip(self.SAYS[level]);self.setAccessibleName('The room above the line is %s. %s' % (self.SIZES[level], self.SAYS[level]));self.update()

    def paintEvent(self, event):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QPainter, QPen
        from .boss_theme import LINE, QUIET, READY
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);box = self.rect().adjusted(0, 0, -1, -1)
        over = self.underMouse() or self.hasFocus()
        p.setPen(QPen(QColor(READY if over else LINE), 1));p.setBrush(Qt.NoBrush);p.drawRect(box)
        pen = QPen(QColor(READY if over or self.level else QUIET), 1.8);pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen)
        cx = box.center().x() + 0.5;cy = box.center().y() + 0.5;w = min(6.0, box.width() / 3.2)
        def chevron(y, up=True):
            tip = y - 3.0 if up else y + 3.0;base = y + 2.0 if up else y - 2.0
            p.drawPolyline([QPointF(cx - w, base), QPointF(cx, tip), QPointF(cx + w, base)])
        if self.level == 0:chevron(cy)
        elif self.level == 1:chevron(cy - 3.5);chevron(cy + 3.5)
        else:chevron(cy, up=False)
        p.end()


class TypeBar(QWidget):
    def __init__(self, host, box, console):
        super().__init__();self.host = host;self.box = box;self.console = console;self.setObjectName('TypeBar')
        self.setProperty('paperFunctionalInk', True);self._style_key = None;self._placing = False;self.px = None
        # The left slot: the cat, then Line · Half · Tall. No box layout: place() sets every position on whole pixels.
        self.left = QWidget(self);self.left.setObjectName('LowerLeftSlot')
        from .hatch_qt import HatchButton
        self.hatch = HatchButton(host);self.hatch.setParent(self.left)
        # Explore left the band (the owner's brief); the object stays for callers. Its routes: the menu's Explore the
        # workshop…, Tools ▸ Explore capabilities…, the right pane's Explore for the selected record.
        from .explore_qt import ExploreButton
        self.explore = ExploreButton(host);self.explore.setParent(self);self.explore.hide()
        self.words = {}  # each band word's whole word (D1-fix: no word is elided; they are set smaller in a narrow window)
        from .desk_qt import InkWord
        for level in (0, 1, 2):
            word = ('Line','Half','Tall')[level];b = console.sizes[level];b.setText(word);b.setParent(self.left);b.show()
            b.setAccessibleName('Console size: ' + word);self.words[b] = word;InkWord.install(b)
            b.setToolTip({'Line':'Console as one line', 'Half':'Console at half height', 'Tall':'Console tall'}[word])
        box.setParent(self);box.show();self._box_tip = box.toolTip()
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygon
        from .boss_theme import TERMINAL_GROUND
        arrow = QPixmap(24, 24)
        arrow.fill(Qt.transparent)
        painter = QPainter(arrow)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(TERMINAL_GROUND))
        painter.drawPolygon(QPolygon([QPoint(7, 4), QPoint(21, 12), QPoint(7, 20)]))
        painter.end()
        self.send = button('', 'primary')
        self.send.setParent(self)
        self.send.setObjectName('WritingSubmit')
        self.send.setIcon(QIcon(arrow));self.send.setIconSize(QSize(19, 19))
        self.send.setFocusPolicy(Qt.TabFocus)
        self.send.setAccessibleName('Submit writing line')
        self.send.setToolTip(SENDS['slate'])
        self.send.clicked.connect(self.submit_line)
        self.expand = ExpandButton(self)      # 0.7.0: the room above the line, opened and closed from the line itself
        # The context word (CM01): the active work context, in quiet lettering at the right end of the line.
        self.context = QLabel(box);self.context.setObjectName('TypeContext');self.context.setTextFormat(Qt.PlainText)
        self.context.setAttribute(Qt.WA_TransparentForMouseEvents);self.context.setFocusPolicy(Qt.NoFocus)
        self.context.setAlignment(Qt.AlignRight | Qt.AlignVCenter);self.context.setAccessibleName('Active work context')
        from .shell2 import QUIET
        self.context.setStyleSheet('QLabel#TypeContext {color:%s;background:transparent;border:0;padding:0;}' % QUIET)
        self.context_text = '';self.context.hide();box.installEventFilter(self)
        self.right = QWidget(self);self.right.setObjectName('LowerRightSlot')
        self.shell = configured_shell();self.labels = dict(TARGETS)
        self.targets = {}
        for key, _ in TARGETS:
            label = self.labels[key]
            word = SHOWN.get(key, label)       # 0.5.3: names alone (they were "Assistant", "[>_] Terminal", "[=] Log")
            b = button(word, 'filter');b.setParent(self.right);b.setCheckable(True);b.clicked.connect(lambda checked=False, k=key:self.set_target(k))
            b.setToolTip(TIPS[key] + ('' if key != 'shell' else ' (%s)' % self.shell));self.targets[key] = b;self.words[b] = word;InkWord.install(b)
            b.setAccessibleName('Writing line mode: ' + label);b.setProperty('arcPrimary', True);b.setProperty('hers', key == 'slate')
        self.hatch.hide()
        for control in console.sizes.values():control.hide()
        for key, control in self.targets.items():
            control.setParent(self.left);control.setVisible(key in PRIMARY_TARGETS)
        self.monitors = host.shell2.top.pulse_holder
        self.monitors.setParent(self.right);self.monitors.show()
        self.tips = {b:b.toolTip() for b in self.words}  # each word's own tooltip
        for chip in console.chips.values():chip.hide()  # the console's own page words: their place is now these modes
        console.hint.hide()
        self._note_timer = QTimer(self, singleShot=True, interval=NOTE_MS);self._note_timer.timeout.connect(self.expire_note)
        self.pane_owner = None;self.owner = {};self._requested = None;self.message = ''
        box.textChanged.connect(self.typed)
        state = host.session.state.get('type_target') if hasattr(host, 'session') else None
        self.set_target(MAPPED.get(state, 'slate'), focus=False)  # the remembered target, an old one mapped to its mode
        self.timer = QTimer(self, interval=500);self.timer.timeout.connect(self.align);self.timer.start()

    def sizeHint(self):return QSize(800, 60)

    def minimumSizeHint(self):return QSize(480, 60)

    def set_target(self, key, focus=True):
        """Choose a mode (an old target maps to its mode: MAPPED). kernel is Commands ▸ Run an operation…: Assignment with the
        / lead in the line. The working area shows the mode's page (CONSOLE_PAGE: Assignment the console's answers, Shell its
        output, Search its results, Log the Log view); choosing a mode never opens or closes it."""
        mode = MAPPED.get(key, 'slate');changed = mode != getattr(self, 'target', None)
        self.target = mode;self.host.type_target = mode
        for k, b in self.targets.items():
            if b.isChecked() != (k == mode):b.setChecked(k == mode)      # 0.5.3: Search has its own name on the strip; Stacy's no longer stands for it
            b.setAccessibleDescription('Current mode' if k == mode else '')
        if hasattr(self.host, 'session'):self.host.session.state['type_target'] = mode
        page = CONSOLE_PAGE.get(mode)      # Web has no page above the line: what it opens is in the browser
        if page is not None and self.console.mode != page and not (mode == 'slate' and self.console.mode in ('stac', 'kernel')):self.console.set_mode(page)
        if changed:
            popup = getattr(self.box, 'popup', None)
            if popup is not None:popup.hide()
        self.mode_hint(kernel=key == 'kernel')
        if key == 'kernel' and focus:
            text = self.box.text().strip()
            self.box.setText('/' + (text[1:] if text[:1] in JUMPS else text) if not text.startswith('/') else text)
            self.box.setFocus();self.box.end(False)
        elif focus:
            if self.box.text().strip() in JUMPS:self.box.clear()
            self.box.setFocus()
        self.refresh_context()

    def run_operation(self):
        """Commands ▸ Run an operation… (Alt+3, the Kernel word's key): the line in Assignment with the / lead; Tab completes an
        operation's name and arguments, Up and Down walk the operations' history, Enter runs it (an approve-scope operation asks
        for a second Enter), help NAME and ops WORD answer in the working area."""
        self.set_target('kernel')

    def search(self):
        """Ctrl+K: the line in Search, its words kept and selected (a lead character dropped), the results shown again."""
        box = self.box;text = box.text();rest = text[1:] if text[:1] in JUMPS else text
        self.set_target('find', focus=False)
        if rest != text:box.setText(rest)
        box.setFocus();box.selectAll()
        if rest.strip() and hasattr(box, 'update_results'):box.update_results(rest)

    def mode_hint(self, kernel=False):
        """The line's hint (its accessible description and tooltip; the placeholder stays poem): the mode's word and what to
        type there; Log's is its stream's grammar."""
        if self.message:return
        view = getattr(self.host, 'log_view', None)
        if self.target == 'log' and view is not None:hint = destination_hint('log', 'Log · ' + dict(STREAMS_WORDS).get(view.stream, ''), view.hint())
        elif self.target == 'shell':hint = destination_hint('shell', self.labels['shell'], HINTS['shell'] + ' (' + self.shell + ')')
        else:hint = destination_hint('kernel' if kernel or (self.target == 'slate' and self.box.text().startswith('/')) else self.target)
        writing_prompt(self.box, hint)

    @staticmethod
    def address_of(words):
        """The address these words are, with its scheme, or '' when they are words to search for."""
        import re
        words = words.strip()
        if not words or any(ch.isspace() for ch in words):return ''
        low = words.lower()
        if low.startswith(('http://', 'https://')):return words
        # The host is what stands before the first / ? or #, without a port. It is an address when it is localhost, an
        # IP number, a name ending in a local suffix, a name that begins www., or a dotted name whose last part is letters;
        # a bare file name (notes.txt, with nothing after it) is not. What is on this computer or this network is asked
        # for plainly (http), never sent to a search engine as words.
        host = re.split(r'[/?#]', words, maxsplit=1)[0];rest = words[len(host):]
        name, colon, port = host.partition(':')
        if colon and not port.isdigit():return ''
        name = name.lower()
        if not name or not re.fullmatch(r'[a-z0-9.\-]+', name) or name.startswith(('.', '-')) or '..' in name:return ''
        local = name == 'localhost' or re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}', name) is not None or name.endswith(('.local', '.lan', '.home', '.internal', '.localhost'))
        if local:return 'http://' + words
        last = name.rsplit('.', 1)[-1]
        if '.' not in name or not last.isalpha() or not 2 <= len(last) <= 24:return ''
        if name.startswith('www.') or colon or rest:return ('http://' if colon else 'https://') + words
        return '' if last in FILE_ENDINGS else 'https://' + words

    @staticmethod
    def plain_address(words):
        """With Stacy or Search lit, the address a line is when it can be nothing else: written with http:// or https://,
        beginning www., or naming this computer or the local network (localhost, an IP number, a .local name, a port).
        A bare dotted name (files.list, field.read) is a staC operation as often as a site, so it stays with whom it was
        typed to."""
        address = TypeBar.address_of(words);low = str(words or '').strip().lower()
        return address if address and (low.startswith(('http://', 'https://', 'www.')) or address.startswith('http://')) else ''

    def open_web(self, text):
        """Web: an address is opened, and words are searched for, in this computer's own browser. Graphite fetches nothing
        itself and keeps nothing of it; what leaves the computer leaves through the browser, at the owner's word."""
        from urllib.parse import quote_plus
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        words = text.strip()
        if not words:return False
        address = self.address_of(words);went = QDesktopServices.openUrl(QUrl(address or WEB_SEARCH + quote_plus(words)))
        if went:
            self.note(('Opened in your browser: ' + address) if address else ('Searching in your browser for: ' + words));self.box.clear()
        else:self.note('No browser answered on this computer. Programs shows what is installed.')
        return went

    def typed(self, text):
        """Update the Assistant hint and work context as the line changes."""
        # (0.5.3 switched to Web as soon as the line began with an address. Another reader showed what that did: a sentence
        # for Stacy that begins with an address was sent to a search engine. The name that is lit is never changed by
        # typing now; a line that is nothing but one address is opened when it is entered: eventFilter.)
        if self.target == 'web':
            popup = getattr(self.box, 'popup', None)
            if popup is not None and popup.isVisible():popup.hide()
        if self.target == 'slate':self.mode_hint();self.refresh_context()

    def ctrl_enter(self):
        """Ctrl+Enter sends Assistant's staC commands and explain previews to the console.
        A line led by / ? or $ runs on its page as Enter does.
        Log: in the Network stream a capture with the line's filter (log_qt.LogView.start_capture, the owner's own action,
        confirmed first), in Events the filter. True when it was handled."""
        from .shell2 import to_console
        text = self.box.text().replace('\u200b', '').strip();popup = getattr(self.box, 'popup', None)
        if self.target == 'log':
            view = getattr(self.host, 'log_view', None)
            if view is None:return True
            if view.stream == 'network':view.start_capture(text)
            else:view.apply_filter(text)
            self.refresh_context();return True
        if self.target != 'slate':return False
        if not text:return True
        try:                                  # the owner's own words, then `this` (the sheet selected in the Field): written out here, so what runs is what shows
            from .field_page import expand_this
            from .stac_words import written_out
            text = expand_this(self.host, written_out(self.host, text))
        except ValueError as exc:
            self.note(str(exc));return True
        if popup is not None:popup.hide()
        page = self.box.console_page(text)
        page = page if page in ('kernel', 'find', 'shell') else 'stac'
        if page == 'find':
            self.box.clear();to_console(self.host, 'find', text[1:].strip() if text.startswith('?') else text);return True
        to_console(self.host, page, text)
        if not getattr(self.console, 'pending_approval', None):self.box.clear()
        return True

    def log_enter(self):
        """Enter in Log mode: the chosen stream filtered by the line's words (the words stay in the line, so the filter shows)."""
        view = getattr(self.host, 'log_view', None)
        if view is not None:
            errors = view.apply_filter(self.box.text())
            if errors:self.host.statusBar().showMessage('Filter: ' + '; '.join(errors), 6000)
        self.refresh_context()

    def submit_line(self):
        """The arrow at the line's end. It does what its tip says: opens an address, filters the Log, and with Stacy chosen
        it runs a line that reads as staC (as Ctrl+Enter does) and gives any other line to her (as Enter does)."""
        if self.target == 'web' or (self.target in ('slate', 'find') and TypeBar.plain_address(self.box.text())):
            self.open_web(self.box.text())
        elif self.target == 'log':
            self.log_enter()
        elif self.target == 'slate' and getattr(self, 'context_kind', None) in READS and self.box.text().strip():
            self.ctrl_enter()
        elif self.box.text().strip():
            self.box.returnPressed.emit()

    def send_says(self):
        """The arrow's tip and colour: green while the line reads as staC and the arrow would run it, amber otherwise."""
        reads = self.target == 'slate' and getattr(self, 'context_kind', None) in READS
        tip = {'stac': 'Run this line', 'inspect': 'Show this plan', 'word': 'Do this to your words'}[self.context_kind] if reads else SENDS.get(self.target, SENDS['slate'])
        if self.send.toolTip() != tip:self.send.setToolTip(tip);self.send.setAccessibleDescription(tip)
        if bool(self.send.property('reads')) != reads:
            self.send.setProperty('reads', reads);self.send.style().unpolish(self.send);self.send.style().polish(self.send);self.send.update()

    def note(self, message):
        """Keep a status message visible beside the console while writing retains its invitation; no message lingers:
        after NOTE_MS the destination hint is back."""
        self.message = message or ''
        if message:writing_prompt(self.box, message)
        else:self.mode_hint()
        self.box.setToolTip(message or self._box_tip)
        self.console.hint.setTextFormat(Qt.PlainText)
        self.console.hint.setText(message or '')
        self.console.hint.setVisible(bool(message))
        if hasattr(self.console, 'quiet_foot'):self.console.quiet_foot()  # D1b: in Line the foot shows only a message
        if message:self._note_timer.start()
        else:self._note_timer.stop()

    def expire_note(self):
        bar = self.host.statusBar()
        if bar.currentMessage():bar.clearMessage()  # messageChanged('') brings note('') round
        else:self.note('')

    # -- the band ---------------------------------------------------------------------------------------------------------
    def band_style(self, scale, px=None):
        from .boss_theme import TERMINAL_GROUND, AMBER_TEXT, AMBER_EDGE, LINE, TEXT, QUIET, READY      # the line's edge at rest is the quiet one; amber when it has the keyboard
        from .shell2 import MONO
        px = max(11, round(15 * scale)) if px is None else int(px)
        key = (round(scale, 4), px)
        if key == self._style_key:return
        self._style_key = key;self.px = px
        self.setStyleSheet(
            'QWidget#TypeBar {background:transparent;border:0;} '
            'QWidget#TypeBar QPushButton {color:%s;background:transparent;border:0;padding:0;margin:0;font-size:%dpx;} '
            'QWidget#TypeBar QLineEdit#OneBox {background:%s;color:%s;placeholder-text-color:%s;border:1px solid %s;border-radius:0;padding:6px 12px;font-family:"%s";font-size:%dpx;} '
            'QWidget#TypeBar QLineEdit#OneBox:focus {border-color:%s;} '
            'QWidget#TypeBar QPushButton#WritingSubmit {background:%s;color:%s;border:1px solid %s;border-radius:0;text-align:center;} '
            'QWidget#TypeBar QPushButton#WritingSubmit:focus {background:%s;} '
            'QWidget#TypeBar QPushButton#WritingSubmit:hover {border:2px solid %s;} '      # under the pointer: the pointer's green edge
            'QWidget#TypeBar QPushButton#WritingSubmit[reads="true"] {background:%s;border:1px solid %s;} '      # the line reads as staC: the arrow is live
            'QWidget#TypeBar QLabel#TypeContext {font-size:%dpx;}'
            % (TEXT, px, TERMINAL_GROUND, TEXT, QUIET, LINE, MONO, px, AMBER_EDGE,
               AMBER_EDGE, TERMINAL_GROUND, AMBER_EDGE, AMBER_TEXT, READY, *((_bt.ROYAL, _bt.ROYAL) if _bt.APPEARANCE == 'kasandra' else (READY, READY)), px)
            + ('QWidget#TypeBar QPushButton#WritingSubmit[reads="true"] {color:%s;}' % _bt.ROYAL_INK if _bt.APPEARANCE == 'kasandra' else ''))      # Kasandra: a line it will run, in royal purple
        for b in list(self.targets.values()) + [self.box, self.context]:
            b.style().unpolish(b);b.style().polish(b)

    def rows(self):
        return ([self.targets[k] for k in PRIMARY_TARGETS], []), ([], [])

    def items(self):
        """Each slot's items left to right: (the cat, Line, Half, Tall) and (the targets)."""
        (lp, ls), (rp, rs) = self.rows();return lp + ls, rp + rs

    def font_at(self, px):
        """The band words' font at px (regular: the active choice is its mark, not bold)."""
        from PySide6.QtGui import QFont
        font = QFont(self.console.sizes[0].font());font.setPixelSize(int(px));font.setWeight(QFont.Normal);return font

    def cat_poses(self, outline=True):
        """The cat's drawn extent in its tile for every pose, in pixels (graphite_brand.cat_ink): {pose: (l, t, r, b)};
        outline=False: its pale coat alone, what the band shows (the cat is placed and paired by it, its button holds the rest)."""
        from PySide6.QtCore import QRectF
        from .graphite_brand import POSES, cat_ink
        self.hatch.fit();w, h = self.hatch.iconSize().width(), self.hatch.iconSize().height()
        return {pose:cat_ink(QRectF(0, 0, w, h), POSES[pose], outline) for pose in POSES}

    def ink_w(self, b, px):
        """An item's ink width: a word's at px, whole (desk_qt.ink_extent); the cat's at rest (its pale coat, what the band shows)."""
        import math
        from . import desk_qt
        if b is self.hatch:
            l, _, r, _ = self.cat_poses(False)['rest'];return math.ceil(r - l)
        return desk_qt.ink_width(self.font_at(px), self.words.get(b, b.text()))

    def slot_need(self, px, gap, scale):
        from . import desk_qt
        a = desk_qt.ink_air(scale);o = desk_qt.inset(scale)
        need = sum(self.ink_w(self.targets[k], px) + 2 * a for k in PRIMARY_TARGETS) + (len(PRIMARY_TARGETS) - 1) * int(gap) + 2 * o      # a gap between each pair (five names since 0.5.3)
        return max(need, self.monitors.minimumSizeHint().width() + 2 * o)

    def row_need(self, primary, secondary):
        """The width a row's items take at the band's size: their ink and air (recorded by check_head_ui)."""
        from . import desk_qt
        from .shell2 import scale_of
        a = desk_qt.ink_air(scale_of(self.host));px = getattr(self, 'px', None) or desk_qt.letter_px(scale_of(self.host))
        return sum(self.ink_w(b, px) + 2 * a for b in list(primary) + list(secondary))

    def slot_needs(self, scale, d=None):
        from . import desk_qt
        return self.slot_need(desk_qt.letter_floor(scale), 4, scale), self.slot_need(desk_qt.letter_px(scale), 6, scale)

    def fit_px(self, pane, scale):
        """The band words' size for panes `pane` wide: the largest from the controls' size down to the floor at which both
        slots hold every word whole with the gaps closed up (D1-fix: the reviews found Kernel and Find elided to K…)."""
        from . import desk_qt
        close = desk_qt.close_gap(scale)
        return desk_qt.fit_size(lambda px:self.slot_need(px, close, scale), int(pane), desk_qt.letter_px(scale), desk_qt.letter_floor(scale))

    def word_height(self):
        """One height for every band word and the writing line: the line of text plus desk_qt.WORD_CHROME."""
        from .desk_qt import word_height, line_px, letter_px
        from .shell2 import scale_of
        return word_height(line_px(getattr(self, 'px', None) or letter_px(scale_of(self.host))))

    def line_baseline(self):
        """The writing line's text baseline in its own box, as Qt places it (the style's contents rect, its vertical rule)."""
        from PySide6.QtWidgets import QStyle, QStyleOptionFrame
        option = QStyleOptionFrame();self.box.initStyleOption(option)
        r = self.box.style().subElementRect(QStyle.SE_LineEditContents, option, self.box);m = self.box.textMargins()
        r = r.adjusted(m.left(), m.top(), -m.right(), -m.bottom());fm = self.box.fontMetrics()
        return r.top() + (r.height() - fm.height() + 1) // 2 + fm.ascent()

    def place(self, d):
        if d is None or self._placing:return
        self._placing = True
        try:
            from . import desk_qt
            px = self.fit_px(d.pane, d.scale);self.band_style(d.scale, px)
            h, p, o = d.band, d.pane, d.inset
            wh = min(h - 12, self.word_height(), desk_qt.scaled(38, d.scale));y = (h - wh) // 2
            wide = d.width >= 1250
            monitor_min = self.monitors.minimumSizeHint().width() + 2 * o
            meter_slot = min(p, max(monitor_min, round(d.width * .14))) if wide else p
            self.left.setGeometry(0, 0, p, h);self.right.setGeometry(d.width - meter_slot, 0, meter_slot, h)
            line_left = max(p + o, round(d.width * .21)) if wide else p + o
            line_width = max(120, d.width - meter_slot - o - line_left)
            button_width = max(32, wh + 3);grip = max(26, round(wh * 0.8))      # the expand control stands at the line's left end, the arrow at its right
            self.expand.setGeometry(line_left, y, grip, wh);self.expand.say()
            self.box.setFixedSize(line_width - button_width - grip - 4, wh);self.box.move(line_left + grip + 4, y)
            self.send.setGeometry(line_left + line_width - button_width, y, button_width, wh)
            # 0.5.3: five names stand here (Search is shown; it was hidden and reached by a key). They take the slot's width
            # between its insets: the air between them is what is left over, shared, and never less than a little.
            widths = [self.ink_w(self.targets[key], px) + 8 for key in PRIMARY_TARGETS]
            spare = (p - 2 * o - sum(widths)) / max(1, len(widths) - 1);gap = max(2.0, min(10.0, spare));x = float(o)
            for key, width in zip(PRIMARY_TARGETS, widths):
                control = self.targets[key]
                control.setGeometry(round(x), y, width, wh);control.show()
                desk_qt.InkWord.place(control, 4, self.line_baseline());x += width + gap
            self.hatch.hide()
            for control in self.console.sizes.values():control.hide()
            self.monitors.setGeometry(o, 0, max(0, meter_slot - 2 * o), h);self.monitors.show()
        finally:self._placing = False
        self.place_context()

    def place_cat(self, ink_left, poses, h, coat=None):
        """The cat at rest has its first inked column at ink_left (the band's inset): its pale coat's, when given (coat, the
        rest pose without the paws' graphite outline, which is graphite on the graphite band; the integration of D2 and D3
        found the visible cat starting a pixel inside the last mode word's mirror); its button holds every pose whole, outline
        included (the hover tail reaches a little further left), its tile centred in the band's height (BAND_PAD above and below)."""
        import math
        rest = coat or poses['rest'];left = min(v[0] for v in poses.values());right = max(v[2] for v in poses.values())
        origin = ink_left - rest[0]  # the tile's left edge in the slot
        x = max(0, math.floor(origin + left) - 1);w = math.ceil(origin + right) + 1 - x
        self.hatch.cat_x = origin - x
        if self.hatch.width() != w or self.hatch.height() != h:self.hatch.setFixedSize(w, h)
        if self.hatch.pos().x() != x or self.hatch.pos().y() != 0:self.hatch.move(x, 0)
        self.hatch.update()

    def refit(self):
        """The band's height is the desk's (both bands equal in Line mode); before the desk exists, one line of words."""
        d = getattr(self.host, 'desk', None)
        if d is not None:self.place(d)

    def event(self, event):
        if event.type() in (QEvent.StyleChange, QEvent.FontChange):QTimer.singleShot(0, self.align)
        return super().event(event)

    def paintEvent(self, event):
        """Keep the mode, command, and instrument groups visually separate."""
        from PySide6.QtGui import QColor, QPainter
        from .boss_theme import LINE as LINE_STRONG      # the two ticks beside the line: the quiet ink, as the line's own edge at rest
        from .desk_qt import paint_band
        p = QPainter(self);paint_band(self, p)
        if self.box.width() > 0 and self.send.x() > self.box.x():
            for x in (self.box.x() - 9, self.send.geometry().right() + 9):
                p.fillRect(x, self.box.y(), 1, self.box.height(), QColor(LINE_STRONG))
        if self.box.width() > 0 and self.box.hasFocus():
            # The writing line has the keyboard: its amber edge is lit, above it and below it. One place on the desk holds
            # the keys at a time, and the amber light is there: here, or on the Field's selected sheet. Drawn on the band
            # inside the line's own columns (the band beside it is left as it is), and not on the Clean desk.
            from PySide6.QtCore import QLineF
            from PySide6.QtGui import QPen
            from .boss_qt import glows
            from .boss_theme import AMBER_EDGE
            if glows(self.host):
                r = self.box.geometry();p.setRenderHint(QPainter.Antialiasing)
                for away, width, alpha in ((5.0, 5.0, 0.07), (3.2, 3.2, 0.12), (1.6, 2.0, 0.2)):
                    ink = QColor(AMBER_EDGE);ink.setAlphaF(alpha);p.setPen(QPen(ink, width))
                    p.drawLine(QLineF(r.left() + 1, r.top() - away, r.right(), r.top() - away))
                    p.drawLine(QLineF(r.left() + 1, r.bottom() + 1 + away, r.right(), r.bottom() + 1 + away))
        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        d = getattr(self.host, 'desk', None)
        if d is not None and d.width != self.width() and not getattr(self.host, '_closing', False):QTimer.singleShot(0, self.align)  # a new window width: the desk again
        else:self.refit()

    def context_words(self):
        """The active work context: the selected cabinet record's label, else the current workspace's title, else Home."""
        host = self.host
        try:
            from .explore_qt import selected_record
            ident = selected_record(host)
        except Exception:ident = None
        if ident:
            page = getattr(host, 'cabinet_page', None);item = getattr(page, 'items', {}).get(ident) if page is not None else None
            node = item.data(0, Qt.UserRole) if item is not None else None
            if isinstance(node, dict) and node.get('label'):return str(node['label'])
            model = getattr(getattr(host, 'operations_panel', None), 'model', None)
            selection = (model or {}).get('selection') if isinstance(model, dict) else None
            if selection and selection.get('id') == ident and selection.get('label'):return str(selection['label'])
            return ident.split(':', 1)[-1]
        if getattr(host, '_home_active', False):return 'Home'
        tabs = getattr(host, 'tabs', None);current = tabs.currentWidget() if tabs is not None else None
        if current is None:return ''
        return str(current.property('ledgerTitle') or tabs.tabText(tabs.currentIndex()) or '')

    def refresh_context(self):
        """Show the line's staC action, current Log filter, or active work context."""
        kind, words = 'context', None
        view = getattr(self.host, 'log_view', None)
        if getattr(self, 'target', None) in ('find', 'web'):kind, words = 'context', ''
        elif getattr(self, 'target', None) == 'slate':
            written = self.box.text()
            try:
                from .field_page import expand_this
                from .stac_words import command, expand, known_to
                written = expand_this(self.host, command(written) or expand(known_to(self.host), written))
            except ValueError:pass
            kind = stac_hint_kind(written) or kind
            words = {'stac': 'runs as a line', 'inspect': 'a plan to look at'}.get(kind)
            if written.startswith(('/words.keep ', '/words.forget ')):      # a line about the owner's own words: it changes them, and says so
                kind, words = 'word', 'keeps this word' if written.startswith('/words.keep ') else 'forgets this word'
        elif getattr(self, 'target', None) == 'log' and view is not None:
            filtered = view.filters.get(view.stream, '')
            kind, words = 'log', view.summary() if self.console.size_level == 0 else (('filter · ' + filtered) if filtered else '')
        if words is None:words = self.context_words()
        if (kind, words) != (getattr(self, 'context_kind', None), self.context_text):
            self.context_text = words;self.context_kind = kind
            tip = {'stac': named('This reads as a line: the arrow runs it. To ask Stacy about it instead, say it in your own words.'),
                   'inspect': 'The arrow shows this plan without running it. Remove explain when you are ready to run it.',
                   'log': 'Log: ' + words + '\nThe stream above the line; Half or Tall shows it.' if words else 'Log'}.get(kind)
            self.context.setToolTip(tip or (('Active work context: ' + words + '\n' if words else '') + 'The selected cabinet record, else the current workspace.'))
            self.context.setAccessibleName({'stac': 'Runs as a line', 'inspect': 'Shows a plan',
                                            'log': 'Log summary'}.get(kind, 'Active work context'))
            self.context.setAccessibleDescription(words)
        self.send_says();self.place_context()

    def place_context(self):
        """The context word takes at most a third of the line (260 px at the default size), elided in the middle, clear of the
        line's own clear button; typed text keeps a right margin so it never runs under the word."""
        box = self.box;words = self.context_text;fm = self.context.fontMetrics();clear = 30
        from .shell2 import scale_of
        room = min(round(260 * scale_of(self.host)), box.width() // 3) if getattr(self, 'context_kind', None) != 'log' else box.width() // 2  # Log's summary: half
        text = fm.elidedText('· ' + words, Qt.ElideMiddle, room) if words else ''
        width = min(room, fm.horizontalAdvance(text) + 4) if text else 0
        if not text or width < fm.horizontalAdvance('· …') + 4:
            if self.context.isVisible():self.context.hide()
            if box.textMargins().right():box.setTextMargins(0, 0, 0, 0)
            return
        if self.context.text() != text:self.context.setText(text)
        self.context.setFixedSize(width, max(10, box.height() - 4));self.context.move(box.width() - width - clear, 2)
        if box.textMargins().right() != width + clear - 4:box.setTextMargins(0, 0, width + clear - 4, 0)
        if not self.context.isVisible():self.context.show()

    def eventFilter(self, watched, event):
        if watched is self.box and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ControlModifier):
            if self.target == 'web':
                self.open_web(self.box.text());return True      # Web: Enter opens it in the browser
            if self.target in ('slate', 'find') and TypeBar.plain_address(self.box.text()):
                self.open_web(self.box.text());return True      # with Stacy or Search lit, a line that is one address and nothing else is opened; words stay with whom they were typed to
        if watched is self.box and event.type() == QEvent.Resize:self.place_context()
        if watched is self.box and event.type() in (QEvent.FocusIn, QEvent.FocusOut):self.update()      # the lit edge comes and goes with the keyboard
        return super().eventFilter(watched, event)

    def floors(self):
        """Both panes' width as the desk last laid it out: [P, P] (None before the first pass). The two floors of the old
        asymmetric columns are one width now."""
        d = getattr(self.host, 'desk', None)
        return [d.pane, d.pane] if d is not None else [None, None]

    def repolish(self):
        """Words styled before the bar joined the window keep stale metrics (a primary word measured 80 px, the plain button
        minimum, until the next restyle); polishing them in place gives the desk their true widths from the start."""
        from PySide6.QtWidgets import QAbstractButton
        for b in [self.hatch, self.box] + list(self.targets.values()) + [self.console.sizes[i] for i in (0, 1, 2)]:
            b.style().unpolish(b);b.style().polish(b)
            if isinstance(b, QAbstractButton):b.updateGeometry()

    def order_keys(self):
        """Forward Tab from the centre: the tab bar, Pin / Unpin, then the whole lower band (the cat first), then the System
        menu's symbol in the head, whose list holds Stop as its first row (ACC-01, V-11; UI-03)."""
        (lp, ls), (rp, rs) = self.rows();chain = lp + ls + [self.box] + rp + rs
        previous = getattr(getattr(self.host, 'tabs', None), 'pin_button', None)
        for w in chain:
            if previous is not None:QWidget.setTabOrder(previous, w)
            previous = w
        nice = getattr(getattr(getattr(self.host, 'shell2', None), 'top', None), 'nice', None)
        stop = getattr(self.host, 'master_stop_button', None)
        after = nice if nice is not None else stop
        if after is not None:QWidget.setTabOrder(previous, after)

    def align(self):
        """The desk, laid out again: one width for both panes, both bands' height and every band word in its column
        (desk_qt.apply). The owner's width is the last drag of either separator or the Workspace setting."""
        for corner in (Qt.BottomLeftCorner, Qt.BottomRightCorner):  # the band keeps the whole foot, whatever reset the corners
            if self.host.corner(corner) != Qt.BottomDockWidgetArea:self.host.setCorner(corner, Qt.BottomDockWidgetArea)
        host = self.host;nav = getattr(host, 'nav_dock', None)
        if nav is None or getattr(host, '_closing', False):return
        # The Workspace setting layout.navigator_width is the owner's word for both panes; a change to it counts.
        requested = getattr(getattr(host, 'ledger_bridge', None), '_layout_requested', {}).get('layout.navigator_width')
        if requested != self._requested:
            if self._requested is not None and isinstance(requested, int):self.pane_owner = requested
            self._requested = requested
        from .desk_qt import apply
        d = apply(host)
        self.owner = {nav:d.pane, getattr(host, 'sim_dock', None):d.pane} if self.pane_owner is not None else {}
        try:
            from .snug import fit_all
            fit_all(host)  # pages that overflow by a little are framed to fit, not scrolled
        except Exception:pass
        self.refresh_context()


def install(host, box, console):
    bar = TypeBar(host, box, console)
    dock = QDockWidget(host);dock.setObjectName('TypeDock');dock.setTitleBarWidget(QWidget());dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
    dock.setWidget(bar);host.setCorner(Qt.BottomLeftCorner, Qt.BottomDockWidgetArea);host.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
    host.addDockWidget(Qt.BottomDockWidgetArea, dock);dock.show()
    host.type_bar = bar;host.type_dock = dock;bar.refit()  # one line, never a slab; the height is the desk's band (desk_qt.band_height)
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    if face is not None:  # Slate's own composer: its place is the bar now
        face.input.hide()
        if getattr(face, 'input_hint', None) is not None:face.input_hint.hide()
    # The old status line repeated the path (workspace), the top row (brain) and Needs a project. It is hidden; its one
    # live job, short messages ("Saved as…"), now shows in the bar itself while the bar is empty.
    status = host.statusBar();status.setSizeGripEnabled(False);status.setFixedHeight(0);status.hide();status.messageChanged.connect(bar.note)  # zero height: out of sight whoever shows it
    bar.order_keys()
    from .desk_qt import MirroredDrag
    host.desk_drag = MirroredDrag(host)  # either separator moves both panes (HATCH DESK D1a)
    def seed():  # both panes start at the owner's saved width (one width now: the left's, else the right's); align lays out the desk
        bar.repolish();nav, side = getattr(host, 'nav_dock', None), getattr(host, 'sim_dock', None)
        if nav is not None and side is not None:
            from .desk_qt import saved_pane
            L = host.session.layout if hasattr(host, 'session') else {}
            left, right = saved_width(L.get('navigator_width'), NAV_RANGE, None), saved_width(L.get('simulator_width'), SIM_RANGE, None)
            from .presentation_preferences import DEFAULTS
            factory = left == DEFAULTS['navigator_width'] and right in (None, FACTORY_RIGHT)  # the old shipped pair is no owner's choice
            bar.pane_owner = None if factory else saved_pane(left if left is not None else right)
            bar._requested = getattr(getattr(host, 'ledger_bridge', None), '_layout_requested', {}).get('layout.navigator_width')
        bar.align()
    # After the other parts' zero-timers (the older shells' fixed proportions), so the saved width is the last word.
    QTimer.singleShot(0, lambda:QTimer.singleShot(0, seed))
    return bar
