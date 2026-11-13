"""The Log view: the working area above the lower band while the writing line is in Log mode (HATCH DESK D3; the owner,
2026-11-06: "Instead of log notes, let's have network ... a network traffic scanner or packet sniffer capability that the
agent can inspect", then "I meant log notes replaced with network").

Log follows one of two streams, chosen with two small tabs at its top (the choice is remembered, session `log_stream`):

  Events   Graphite's events: the activity journal (workbench/activity.py) read through Kernel.dispatch of ledger.activity
           and ledger.journal.status (observer reads, never recorded), in the Timeline's words (tail_words.readable), newest
           at the bottom with Follow latest. There are no notes: the notes feature was replaced by the network.
  Network  this computer's network as D5's capability observes it, read ONLY through Kernel.dispatch of D5's four
           operations (NETWORK_OPERATIONS): the interfaces with their receive and send rates, the open connections
           (protocol, local and remote address and port, state, the process when known) and, while a capture runs, the packet
           stream (time, interface, protocol, source -> destination, ports, length, TCP flags), newest at the bottom with
           Follow latest.

In Log mode the writing line filters the chosen stream: Enter applies the filter (Events: words; Network: the grammar below).
In the Network stream Ctrl+Enter starts a capture with that filter through network.capture.start: the owner's own action;
the first capture of a run asks first, saying exactly what is captured (headers only, this computer's interfaces, not
promiscuous, for how long, how many packets, the capture filter the tool receives) and that nothing leaves the computer.
Stop capture ends it (network.capture.stop; Master Stop also ends it, D5's tracked command). When capture is unavailable the
stream says why and how the owner can enable it, in D5's words; Graphite never offers sudo. When the capability refuses a
capture (its words, a filter it will not use), the refusal stays in the stream until the next capture or filter. Choosing an
entry in either stream pins it at the top with its details (it stays while the stream scrolls and refreshes); "Ask Stacy
about this" puts an assignment in the line with that entry as its context.

The Network filter grammar is D5's own (workbench/network_watch.py: parse_filter, matches, bpf), one grammar for the view and
the capability (D3-fix: the view once had its own, and hid rows the capability had returned for localhost, a service name, or
a state on packets). The owner's words go to network.observe, network.capture.read and network.capture.start as typed; the
view applies the same functions to what comes back, so it shows exactly what the capability's grammar selects:

  10.0.0.5  host 10.0.0.5  10.0.0.0/24  localhost     a host (an address, a network, localhost: 127.0.0.1 and ::1); a name
                                                       with a dot is never looked up, so it matches nothing and says so
  443  port 443  :443  10.0.0.5:443                   a port (1 to 65535), or a host and its port
  tcp udp icmp icmp6 arp ip ip6 ...                    a protocol word (tcp also matches tcp6)
  listen established time_wait ...                     a connection state (it narrows connections, not packets)
  proc firefox  firefox  ssh                           any other word: a process or user name, or a port's service name, in part
  Words of one kind widen (port 80 port 443: either); words of different kinds narrow (host 10.0.0.5 tcp: both).

capture_filter(text) is the capture-filter expression the capture tool receives for the words (D5's bpf) and every reason D5
would refuse them; process names and states are applied when the packets are read.

When a capture ends between two reads (its seconds or packets reached), one more read takes what it wrote last
(LogView.following), and a read that leaves packets behind (D5's 'rest') reads on.

For D4's right-click menu: entry_at(widget, point) is the entry under a point of the Log view (a dict with 'stream' 'events' or
'network' and, for the network, 'kind' 'connection' or 'packet'), focus(host, entry) puts the line in Log mode on that entry's
stream with the entry pinned (a network entry's stream filtered to its conversation), ask_about(host, entry) puts an
assignment about it in the line.
"""
from __future__ import annotations
import re
import time
from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

NETWORK_OPERATIONS = ('network.observe', 'network.capture.start', 'network.capture.stop', 'network.capture.read')
EVENT_OPERATIONS = ('ledger.activity', 'ledger.journal.status')
STREAMS = (('events', 'Events'), ('network', 'Network'))
HINTS = {'events': "words in Graphite's events  ·  Enter filters",
         'network': 'host 10.0.0.5 · port 443 · firefox · tcp  ·  Enter filters  ·  Ctrl+Enter captures with it'}
NOTES = {'events': "Graphite's own events; words and Enter filter them, choose one to pin it.",
         'network': 'A host, a port, a process or a protocol and Enter filter it; Ctrl+Enter captures headers.'}
CAPTURE_SECONDS = 60      # a capture's bound, in the confirmation's words (D5 bounds it again)
CAPTURE_PACKETS = 2000    # and its packet bound
MAX_ROWS = 1000           # the most rows a stream keeps (the oldest go first)
TAB_AIR = 8               # a stream tab's room each side of its word
WIDE = 140                # the Network page sets connections and packets side by side from this many characters wide
NOTE_LINES = 3            # the capture's note shows this many lines at most when the lists are one above the other (it scrolls)
NOTE_LINES_WIDE = 8       # and this many side by side, where the packets' column has the height
EVENTS_BACK = 200         # how many recent events the Events stream opens with
TICK_MS = 1000            # the view refreshes this often while the line is in Log mode
OBSERVE_EVERY = 2         # network.observe every this many ticks; capture.read every tick while a capture runs
READ_LIMIT = 200          # packets one network.capture.read asks for
READ_PAGES = 5            # reads a tick makes at most while D5 says more remain ('rest'); a capture's last read takes all
CODE = re.compile(r'^[A-Z][A-Z0-9]*_[A-Z0-9_]+:\s*')  # the capability's code word before its sentence (NETWORK_FILTER_REFUSED: ...)


# The grammar: D5's own (workbench/network_watch.py), one for the view and the capability ----------------------------------------

def _grammar():
    """D5's grammar module, read when first needed (it is pure: files are never read by these functions)."""
    from . import network_watch
    return network_watch


def parse_filter(text):
    """The owner's words for the Network stream as D5 reads them: {hosts, names, ports, protocols, states, words, errors, text}
    (network_watch.parse_filter). See the module note."""
    return _grammar().parse_filter(text)


def matches(entry, parts):
    """Whether a connection or packet entry passes the parsed filter, by D5's own rule (network_watch.matches): any word of a
    kind, every kind present; a name matches no address; a state narrows connections, not packets; a word is a process, user,
    interface, flag or a port's service name, in part."""
    if not parts:return True
    return _grammar().matches(entry, parts, packet=entry.get('kind') == 'packet')


def capture_filter(text):
    """(expression, errors): the capture-filter expression the capture tool receives for the owner's words (D5's bpf of D5's
    parse) and every reason D5 refuses them (a word it does not understand, a name it never looks up, a socket kind no capture
    selects). '' with no errors captures every packet; errors mean network.capture.start would capture nothing."""
    watch = _grammar();parts = watch.parse_filter(text)
    try:expression, errors = watch.bpf(parts)
    except ValueError as exc:return '', list(dict.fromkeys(list(parts['errors']) + [str(exc)]))
    return expression, list(dict.fromkeys(list(parts['errors']) + list(errors)))


def bpf(parts):
    """The parsed words as the capture-filter expression D5 writes for them (hosts, ports and protocols; process names and
    states are applied when the packets are read); '' when they select every packet or cannot be captured (capture_filter
    says why)."""
    try:return _grammar().bpf(parts)[0]
    except ValueError:return ''


def plain_words(message):
    """The capability's sentence without its code word (NETWORK_FILTER_REFUSED: names are not looked up ... -> names are ...)."""
    return CODE.sub('', str(message or '').strip())


def conversation(entry):
    """The filter that follows an entry's conversation: the far host and its port (a packet: the side with the lower port, the
    service's)."""
    if entry.get('kind') == 'packet':
        sport, dport = entry.get('sport'), entry.get('dport')
        far, port = (entry.get('src'), sport) if isinstance(sport, int) and isinstance(dport, int) and sport < dport else (entry.get('dst'), dport)
    else:far, port = entry.get('remote'), entry.get('rport')
    words = []
    if far and str(far) not in ('*', '0.0.0.0', '::'):words.append('host ' + str(far).strip('[]'))
    if port:words.append('port %s' % port)
    return ' '.join(words)


def rate(bits):
    """A rate in bits per second (the contract's rx_bps and tx_bps), as people read it: '0 bit/s', '12.3 kbit/s', '1.20 Mbit/s'."""
    try:bits = float(bits)
    except (TypeError, ValueError):return '–'
    for unit, size in (('Gbit/s', 1e9), ('Mbit/s', 1e6), ('kbit/s', 1e3)):
        if bits >= size:value = bits / size;return ('%.2f' if value < 10 else '%.1f' if value < 100 else '%.0f') % value + ' ' + unit
    return '%d bit/s' % round(bits)


def address(host, port):
    host = str(host if host not in (None, '') else '*')
    if ':' in host and not host.startswith('['):host = '[' + host + ']'
    return host + (':%s' % port if port not in (None, '', 0) else '')


def stamp(at, fraction=False):
    try:at = float(at)
    except (TypeError, ValueError):return '--:--:--'
    return time.strftime('%H:%M:%S', time.localtime(at)) + ('.%03d' % int((at % 1) * 1000) if fraction else '')


def connection_line(c):
    """A connection as one row: protocol, local -> remote, state, the process (and its id) when known."""
    who = c.get('process') or ''
    if who and c.get('pid'):who += ' %s' % c['pid']
    return '  '.join(x for x in (str(c.get('proto') or ''), address(c.get('local'), c.get('lport')) + ' → ' + address(c.get('remote'), c.get('rport')),
                                 str(c.get('state') or '').lower(), who) if x)


def packet_line(p):
    """A packet as one row: time, interface, protocol, source -> destination with their ports, length, TCP flags (the process,
    when known, is in its details)."""
    flags = ('[%s]' % p['flags']) if p.get('flags') else ''
    return ' '.join(x for x in (stamp(p.get('at'), True), str(p.get('iface') or ''), str(p.get('proto') or ''),
                                address(p.get('src'), p.get('sport')) + ' → ' + address(p.get('dst'), p.get('dport')),
                                '%s B' % p['length'] if p.get('length') not in (None, '') else '', flags) if x)


def event_line(e):
    from .tail_words import readable
    return stamp(e.get('at')) + '  ' + readable(e)


def details(entry):
    """The pinned entry's details as (name, value) rows, in reading order."""
    kind = entry.get('kind')
    if kind == 'event':
        e = entry.get('event') or {}
        keys = (('at', stamp(e.get('at'))), ('operation', e.get('operation')), ('state', e.get('state')), ('origin', e.get('origin')),
                ('detail', e.get('detail')), ('job', e.get('job_id')), ('event', e.get('id')), ('sequence', e.get('seq')))
    elif kind == 'connection':
        keys = (('protocol', entry.get('proto')), ('local', address(entry.get('local'), entry.get('lport'))), ('remote', address(entry.get('remote'), entry.get('rport'))),
                ('state', entry.get('state')), ('process', entry.get('process')), ('pid', entry.get('pid')), ('user', entry.get('user')))
    else:
        keys = (('time', stamp(entry.get('at'), True)), ('interface', entry.get('iface')), ('protocol', entry.get('proto')),
                ('source', address(entry.get('src'), entry.get('sport'))), ('destination', address(entry.get('dst'), entry.get('dport'))),
                ('length', entry.get('length')), ('TCP flags', entry.get('flags')), ('process', entry.get('process')), ('sequence', entry.get('seq')))
    return [(k, str(v)) for k, v in keys if v not in (None, '')]


def assignment_text(entry):
    """The words "Ask Stacy about this" puts in the line: the entry as the assignment's context, then room for the question."""
    kind = entry.get('kind')
    if kind == 'event':
        e = entry.get('event') or {}
        said = ' · '.join(str(x) for x in (stamp(e.get('at')), e.get('operation'), e.get('state'), e.get('detail')) if x)
        return 'About this Graphite event (%s): ' % said
    if kind == 'connection':
        who = ', %s' % entry['process'] + (' pid %s' % entry['pid'] if entry.get('pid') else '') if entry.get('process') else ''
        return 'About this network connection (%s %s → %s, %s%s): ' % (entry.get('proto') or '', address(entry.get('local'), entry.get('lport')),
                                                                        address(entry.get('remote'), entry.get('rport')), entry.get('state') or 'no state', who)
    flags = ', flags %s' % entry['flags'] if entry.get('flags') else ''
    return 'About this packet (%s %s %s %s → %s, %s bytes%s): ' % (stamp(entry.get('at'), True), entry.get('iface') or '', entry.get('proto') or '',
                                                                    address(entry.get('src'), entry.get('sport')), address(entry.get('dst'), entry.get('dport')),
                                                                    entry.get('length', '?'), flags)


def filter_lines(filter_text):
    """The confirmation's last lines: the owner's words, the capture filter the capture tool receives for them (D5's own, so
    exactly what is selected), and what is applied only as the packets are read."""
    text = ' '.join(str(filter_text or '').split())
    if not text:return 'Filter: none. Every packet to and from this computer is captured.'
    expression, _ = capture_filter(text);parts = parse_filter(text)
    lines = ['Filter: ' + text, ('The capture tool selects: ' + expression) if expression else
             'The capture tool selects every packet: these words name no host, port or protocol.']
    if parts.get('words'):lines.append('Shown: only the packets matching %s (a process, user or service name, applied as the packets are read).' % ', '.join(parts['words']))
    if parts.get('states'):lines.append('A connection state (%s) narrows the connections, not the packets.' % ', '.join(parts['states']))
    return '\n'.join(lines)


def confirmation_words(filter_text, seconds=CAPTURE_SECONDS, packets=CAPTURE_PACKETS):
    """What the first capture of a run asks, exactly (the filter as the capture tool receives it: filter_lines)."""
    return ('Capture this computer\'s network traffic?\n\n'
            'Graphite records packet headers only: addresses, ports, protocol, length and TCP flags, never what the packets carry.\n'
            'It listens on this computer\'s own interfaces, not in promiscuous mode, so only traffic to and from this computer.\n'
            'It stops after %d seconds or %d packets, whichever comes first; Stop capture or Master Stop ends it sooner.\n'
            'Nothing leaves the computer: the headers stay here, for you and for Graphite during an assignment.\n\n%s'
            % (seconds, packets, filter_lines(filter_text)))


def unknown(response):
    """True when the capability's operation is not in this build (D5 not yet installed)."""
    message = str(((response or {}).get('error') or {}).get('message', ''))
    return 'Unknown operation' in message


# The view -------------------------------------------------------------------------------------------------------------------

class StreamTab(QPushButton):
    """One of Log's two small tabs, drawn as the panes' tabs are (pane_qt.PaneTab): the word in print, the chosen one in
    DemiBold with the short pencil-yellow mark under it, the eraser-pink mark under the one the pointer or the keyboard is on."""

    def __init__(self, word, parent=None):
        super().__init__(word, parent);self.setCheckable(True);self.setCursor(Qt.PointingHandCursor);self.setFlat(True)
        self.setObjectName('LogStreamTab');self.setAccessibleName('Log stream: ' + word);self.setAttribute(Qt.WA_Hover, True)
        self.toggled.connect(lambda *_:self.update())

    def bold(self):
        font = QFont(self.font());font.setWeight(QFont.DemiBold);return font

    def sizeHint(self):
        """Room for the word in its chosen weight (DemiBold, as the panes' tabs), so choosing a stream never moves the row."""
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.bold());return QSize(fm.horizontalAdvance(self.text()) + 2 * TAB_AIR + 2, fm.height() + 12)

    def minimumSizeHint(self):return self.sizeHint()

    def enterEvent(self, event):super().enterEvent(event);self.update()

    def leaveEvent(self, event):super().leaveEvent(event);self.update()

    def event(self, event):
        if event.type() in (QEvent.FontChange, QEvent.StyleChange, QEvent.Polish):self.updateGeometry()  # its room follows its word's size
        return super().event(event)

    def paintEvent(self, event):
        from .shell2 import QUIET, TEXT
        from .desk_qt import ERASER_MARK, MARK, PENCIL
        from PySide6.QtGui import QFontMetrics
        font = self.bold() if self.isChecked() else self.font()  # the chosen stream's word in DemiBold, as the panes' tabs
        p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing);p.setFont(font)
        p.setPen(QColor(TEXT if self.isChecked() else QUIET));p.drawText(self.rect().adjusted(0, 0, 0, -MARK), Qt.AlignCenter, self.text())
        fm = QFontMetrics(font);w = fm.horizontalAdvance(self.text());x = (self.width() - w) // 2
        from .boss_theme import READY
        colour = ERASER_MARK if self.hasFocus() else READY if self.underMouse() else PENCIL if self.isChecked() else None      # the keyboard's colour, the pointer's green, the chosen one
        if colour:p.fillRect(QRect(x, self.height() - MARK, w, MARK), QColor(colour))
        p.end()


def _list(name, mono=False):
    """A stream's list: compact rows, a long row cut at its end (its start, the time and the addresses, is what you read first; the
    whole row is its tooltip and the pinned details)."""
    from .shell2 import mono_font
    view = QListWidget();view.setObjectName(name);view.setFrameShape(QFrame.NoFrame);view.setUniformItemSizes(True)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);view.setTextElideMode(Qt.ElideRight);view.setFocusPolicy(Qt.ClickFocus)
    if mono:view.setFont(mono_font(13))
    return view


def default_dispatch(host):
    """The owner's reads and actions through the one dispatcher, Kernel.dispatch, with the owner's principal."""
    def dispatch(operation, arguments):
        from .engineering_kernel import CAPABILITIES, operator
        if operation not in CAPABILITIES:  # not in this build: no call (a refused call is recorded, and the view asks every second)
            return {'ok': False, 'error': {'code': 'NOT_IN_THIS_BUILD', 'message': 'Unknown operation: ' + operation}}
        kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:
            from .engine import engineering
            kernel = engineering(host.root)
        try:return kernel.dispatch(operation, arguments, operator())
        except Exception as exc:return {'ok': False, 'error': {'message': str(exc)}}
    return dispatch


class LogView(QWidget):
    """The Log view (see the module note). dispatch(operation, arguments) -> the Kernel's response is the one way it reads and
    acts; tests give it a fake."""

    def __init__(self, host, dispatch=None):
        super().__init__();self.host = host;self.setObjectName('LogView');self.setAccessibleName('Log: Events and Network')
        self.dispatch = dispatch or default_dispatch(host)
        state = getattr(getattr(host, 'session', None), 'state', {}) if host is not None else {}
        self.stream = state.get('log_stream') if state.get('log_stream') in dict(STREAMS) else 'events'
        self.filters = {'events': '', 'network': ''};self.parts = parse_filter('');self.pinned = None;self.confirmed = False
        self.cursor = None;self.packet_cursor = None;self.capture = {};self.observed = None;self.problem = None;self.ticks = 0
        self.interfaces_seen = [];self.connections_seen = [];self.captured = False
        self.following = False   # a capture was running at the last look: when it is seen ended, one more read takes its last packets
        self.refusal = None      # the capability's words when it refused the owner's capture; shown until the next capture or filter
        self.reported = []       # the filter's errors as the capability reported them (observe's and read's result['filter'])
        self.rest = 0            # connections the capability matched beyond what it returns
        from .shell2 import KeyedWords, button, sentence
        column = QVBoxLayout(self);column.setContentsMargins(0, 0, 0, 0);column.setSpacing(4)
        head = QHBoxLayout();head.setSpacing(6);head.setContentsMargins(0, 0, 0, 0)
        self.tabs = {}
        for key, word in STREAMS:
            tab = StreamTab(word, self);tab.clicked.connect(lambda checked=False, k=key:self.choose(k, remember=True));self.tabs[key] = tab;head.addWidget(tab)
        self.filter_words = QLabel('');self.filter_words.setObjectName('LogFilter');self.filter_words.setWordWrap(True);head.addSpacing(12);head.addWidget(self.filter_words, 1)
        self.follow = QCheckBox('Follow latest');self.follow.setObjectName('LogFollow');self.follow.setChecked(True);head.addWidget(self.follow)
        column.addLayout(head)
        # The capture's state and its two words live over the packets (they are the packets' own): Capture… and Stop capture.
        self.capture_words = QLabel('');self.capture_words.setObjectName('LogCaptureState');self.capture_words.setWordWrap(True)
        self.start_button = button('Capture…', 'quiet');self.start_button.setObjectName('LogCaptureStart');self.start_button.clicked.connect(lambda:self.start_capture(self.filters['network']))
        self.stop_button = button('Stop capture', 'quiet');self.stop_button.setObjectName('LogCaptureStop');self.stop_button.clicked.connect(self.stop_capture)
        self.note = KeyedWords(host, wrap=True);self.note.setObjectName('LogNote');column.addWidget(self.note)  # a note you may skip: the script, its keys printed
        # The pinned entry: it stays at the top while the stream below scrolls and refreshes.
        self.pin_frame = QFrame();self.pin_frame.setObjectName('LogPinned');pin = QVBoxLayout(self.pin_frame);pin.setContentsMargins(10, 6, 10, 6);pin.setSpacing(2)
        self.pin_title = QLabel('');self.pin_title.setObjectName('LogPinnedLine');self.pin_title.setTextFormat(Qt.PlainText);self.pin_title.setWordWrap(True)
        self.pin_details = QLabel('');self.pin_details.setObjectName('LogPinnedDetails');self.pin_details.setTextFormat(Qt.PlainText);self.pin_details.setWordWrap(True)
        self.pin_actions = sentence('{ask}  ·  {unpin}', {'ask': ('Ask Stacy about this', lambda:self.ask()), 'unpin': ('Unpin', lambda:self.unpin())})
        self.pin_actions.setObjectName('LogPinnedActions')
        for w in (self.pin_title, self.pin_details, self.pin_actions):pin.addWidget(w)
        self.pin_frame.hide();column.addWidget(self.pin_frame)
        self.stack = QStackedWidget();column.addWidget(self.stack, 1)
        self.events = _list('LogEvents')
        try:
            from .shell2 import TimelineDelegate
            self.events.setItemDelegate(TimelineDelegate(self.events))
        except ImportError:pass
        self.stack.addWidget(self.events)
        net = QWidget();net.setObjectName('LogNetwork');box = QVBoxLayout(net);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(4)
        self.interfaces = QLabel('');self.interfaces.setObjectName('LogInterfaces');self.interfaces.setTextFormat(Qt.PlainText);self.interfaces.setWordWrap(True)
        box.addWidget(self.interfaces)
        from PySide6.QtWidgets import QBoxLayout
        self.lists = lists = QBoxLayout(QBoxLayout.LeftToRight);lists.setSpacing(12)  # side by side when wide, else one above the other
        left = QVBoxLayout();left.setSpacing(2);self.connections_head = QLabel('CONNECTIONS');self.connections_head.setObjectName('LogSection');left.addWidget(self.connections_head)
        self.connections = _list('LogConnections', mono=True);left.addWidget(self.connections, 1)
        right = QVBoxLayout();right.setSpacing(2);self.packets_head = QLabel('PACKETS');self.packets_head.setObjectName('LogSection')
        over = QHBoxLayout();over.setSpacing(10);over.addWidget(self.packets_head);over.addWidget(self.capture_words, 1)
        for w in (self.start_button, self.stop_button):over.addWidget(w)
        right.addLayout(over)
        self.capture_note = QLabel('');self.capture_note.setObjectName('LogCaptureNote');self.capture_note.setWordWrap(True);self.capture_note.setTextFormat(Qt.PlainText)
        # The integration of the desk items: one above the other (a narrow window, a large text size) the capture's reason (five
        # lines when capture is unavailable) was given two and cut; it sits in its own quiet scroll, as tall as its words up to a
        # few lines there and whole by scrolling, so the lists keep their room (fit_note).
        self.note_area = QScrollArea();self.note_area.setObjectName('LogCaptureNoteArea');self.note_area.setWidgetResizable(True)
        self.note_area.setFrameShape(QFrame.NoFrame);self.note_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.note_area.setWidget(self.capture_note)
        self.note_area.viewport().setAutoFillBackground(False);self.capture_note.setAutoFillBackground(False)
        right.addWidget(self.note_area);self.packets = _list('LogPackets', mono=True);right.addWidget(self.packets, 1)
        right.addStretch(0)  # with no packet list (capture unavailable) the packets' words keep to the top, under their head
        lists.addLayout(left, 1);lists.addLayout(right, 1);box.addLayout(lists, 1)
        self.stack.addWidget(net);self.network_page = net
        for view in (self.events, self.connections, self.packets):
            view.itemClicked.connect(self.chose);view.itemActivated.connect(self.chose)
            view.verticalScrollBar().sliderPressed.connect(lambda:self.follow.setChecked(False));view.viewport().installEventFilter(self)
        self.follow.toggled.connect(lambda on:self.scroll_latest() if on else None)
        self.style_view()
        self.timer = QTimer(self, interval=TICK_MS);self.timer.timeout.connect(self.tick)
        self.choose(self.stream, remember=False, read=False)

    # -- look ----------------------------------------------------------------------------------------------------------------
    def style_view(self):
        """The view's look; the network rows in Plex Mono at 13 px at 14 pt, following the interface size (the window's sheet
        sizes every list, so the face and size are set here, where they win)."""
        from .shell2 import CARD, LINE, QUIET, RAISED, TEXT, MONO, scale_of
        mono = max(11, round(13 * scale_of(self.host))) if self.host is not None and hasattr(self.host, 'session') else 13
        if getattr(self, '_mono_px', None) == mono:return
        self._mono_px = mono
        if hasattr(self, 'lists'):QTimer.singleShot(0, self.arrange)  # the rows' new size can change the lists' direction
        self.setStyleSheet(
            'QWidget#LogView {background:transparent;} '
            'QPushButton#LogStreamTab {padding:0 %(air)dpx;margin:0;border:0;background:transparent;min-width:0;min-height:0;} '
            'QListWidget#LogEvents, QListWidget#LogConnections, QListWidget#LogPackets {background:%(card)s;border:1px solid %(line)s;border-radius:4px;color:%(text)s;} '
            'QListWidget#LogEvents::item, QListWidget#LogConnections::item, QListWidget#LogPackets::item {padding:1px 6px;} '
            'QListWidget#LogEvents::item:selected, QListWidget#LogConnections::item:selected, QListWidget#LogPackets::item:selected {background:%(raised)s;color:%(text)s;} '
            'QFrame#LogPinned {background:%(raised)s;border:1px solid %(line)s;border-left:3px solid %(pencil)s;border-radius:4px;} '
            'QLabel#LogPinnedLine {color:%(text)s;font-weight:600;} QLabel#LogPinnedDetails {color:%(quiet)s;} '
            'QLabel#LogSection {color:%(quiet)s;letter-spacing:1px;} QLabel#LogFilter, QLabel#LogCaptureState {color:%(quiet)s;} '
            'QLabel#LogInterfaces, QLabel#LogCaptureNote {color:%(text)s;} '
            'QCheckBox#LogFollow {color:%(quiet)s;} '
            "QListWidget#LogConnections, QListWidget#LogPackets, QLabel#LogPinnedDetails {font-family:'%(mono)s';font-size:%(px)dpx;}"
            % dict(card=CARD, line=LINE, text=TEXT, quiet=QUIET, raised=RAISED, pencil='#d4b56a', air=TAB_AIR, mono=MONO, px=mono))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and event.angleDelta().y() > 0:self.follow.setChecked(False)  # reading back stops following
        return super().eventFilter(obj, event)

    # -- the stream ----------------------------------------------------------------------------------------------------------
    def choose(self, stream, remember=True, read=True):
        """Show a stream; remember it for the next start when the owner chose it; read it now unless read is False."""
        if stream not in dict(STREAMS):return
        self.stream = stream
        for key, tab in self.tabs.items():tab.setChecked(key == stream);tab.setAccessibleDescription('Current stream' if key == stream else '')
        self.stack.setCurrentIndex(0 if stream == 'events' else 1)
        self.note.explain(NOTES[stream])
        if self.pinned is not None and self.pinned.get('stream') != stream:self.unpin()
        if remember and getattr(self.host, 'session', None) is not None:
            self.host.session.state['log_stream'] = stream
            try:self.host.session.save()
            except Exception:pass
        self.show_filter();self.show_capture()
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None and getattr(bar, 'target', None) == 'log':bar.mode_hint()
        if read:self.refresh(force=True)

    def hint(self):
        return HINTS[self.stream]

    def apply_filter(self, text):
        """Enter in the line: the chosen stream filtered by the words (Events: words; Network: the grammar)."""
        text = str(text or '').strip();self.filters[self.stream] = text
        if self.stream == 'network':
            self.parts = parse_filter(text);self.packet_cursor = None;self.packets.clear();self.reported = [];self.refusal = None
        else:self.cursor = None;self.events.clear()
        self.show_filter();self.refresh(force=True)
        return self.filter_errors() if self.stream == 'network' else []

    def filter_errors(self):
        """What the capability says it could not use of the Network filter: the errors its own grammar gives for the words
        (parse_filter) and those it reported with its last answer (result['filter']['errors']), once each."""
        return list(dict.fromkeys(list(self.parts.get('errors') or []) + list(self.reported)))

    def show_filter(self):
        text = self.filters[self.stream]
        words = ('filter · ' + text) if text else ''
        errors = self.filter_errors() if self.stream == 'network' and text else []
        if errors:words += '  (' + '; '.join(errors) + ')'
        self.filter_words.setText(words);self.filter_words.setToolTip(self.hint())

    def take_reported(self, result):
        """The filter's errors the capability reported with an answer for the current words."""
        said = (result or {}).get('filter') if isinstance(result, dict) else None
        if not isinstance(said, dict):return
        if ' '.join(str(said.get('text') or '').split()) != ' '.join(self.filters['network'].split()):return
        reported = [str(e) for e in said.get('errors') or []]
        if reported != self.reported:self.reported = reported;self.show_filter()

    def tick(self):
        if getattr(self.host, '_closing', False):return
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None and getattr(bar, 'target', None) != 'log':return  # it reads nothing while the line is elsewhere
        self.refresh()

    def refresh(self, force=False):
        self.ticks += 1
        if self.stream == 'events':self.refresh_events(force)
        else:self.refresh_network(force)
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None and getattr(bar, 'target', None) == 'log':bar.refresh_context()

    def refresh_events(self, force=False):
        query = self.filters['events']
        if self.cursor is None:
            status = self.dispatch('ledger.journal.status', {})
            head = int(((status or {}).get('result') or {}).get('head') or 0) if (status or {}).get('ok') else 0
            self.cursor = str(max(0, head - EVENTS_BACK));self.events.clear()
        for _ in range(5):
            args = {'after': self.cursor, 'limit': 200}
            if query:args['query'] = query
            r = self.dispatch('ledger.activity', args)
            if not (r or {}).get('ok'):self.problem = ((r or {}).get('error') or {}).get('message', 'the journal could not be read');break
            result = r['result'];self.problem = None
            self.add_events(result.get('events', []))
            self.cursor = str(result.get('cursor') or self.cursor)
            if not result.get('has_more'):break
        if not self.events.count():
            item = QListWidgetItem('No events match that.' if query else 'No events recorded yet.');item.setFlags(Qt.NoItemFlags);self.events.addItem(item)

    def add_events(self, events):
        from .tail_words import in_flight
        if not events:return
        open_requests = in_flight(events);added = False
        if self.events.count() == 1 and not self.events.item(0).data(Qt.UserRole):self.events.clear()
        last = self.events.item(self.events.count() - 1).text() if self.events.count() else None
        for e in events:
            if e.get('state') == 'REQUEST_RECEIVED' and e.get('correlation_id') not in open_requests:continue  # its completion line says it
            line = event_line(e)
            if line == last:continue
            last = line;item = QListWidgetItem(line)
            item.setData(Qt.UserRole, dict(stream='events', kind='event', id=e.get('id'), line=line, event=e));self.events.addItem(item);added = True
        while self.events.count() > MAX_ROWS:self.events.takeItem(0)
        if added and self.follow.isChecked():self.events.scrollToBottom()

    def network(self, operation, arguments):
        """The Network stream's one door: D5's four operations through the Kernel's dispatcher, nothing else."""
        if operation not in NETWORK_OPERATIONS:raise ValueError('The Network stream reads only ' + ', '.join(NETWORK_OPERATIONS))
        return self.dispatch(operation, arguments)

    def refresh_network(self, force=False):
        text = self.filters['network'];args = {'filter': text} if text else {}
        if force or self.observed is None or self.ticks % OBSERVE_EVERY == 0:
            r = self.network('network.observe', args)
            if (r or {}).get('ok'):
                self.problem = None;self.observed = r['result'];self.capture = dict(self.observed.get('capture') or {})
                self.rest = int(((self.observed.get('rest') or {}).get('connections') or 0)) if isinstance(self.observed.get('rest'), dict) else 0
                self.take_reported(self.observed)
                self.show_interfaces(self.observed.get('interfaces') or []);self.show_connections(self.observed.get('connections') or [])
            else:
                self.observed = {};self.capture = {'state': 'UNAVAILABLE', 'reason': self.reason(r)};self.show_interfaces([]);self.show_connections([])
                self.problem = self.capture['reason']
        running = self.capture.get('state') == 'RUNNING'
        if running or self.following or (force and self.captured and self.capture.get('state') != 'UNAVAILABLE'):
            # while a capture runs; once more when it is seen ended (its last packets: D3-fix, they were lost when the capture
            # ended between two reads); and, after one, again when the filter changes
            self.read_packets(last=not running)
        self.following = self.capture.get('state') == 'RUNNING'
        self.show_capture()

    def reason(self, response):
        if unknown(response):return 'The network capability is not in this build yet, so there is nothing to observe.'
        return plain_words(((response or {}).get('error') or {}).get('message') or 'The network could not be read.')

    def read_packets(self, last=False):
        """network.capture.read from the cursor, page after page while the capability says more remain (READ_PAGES a tick;
        all of them when last, the read after a capture ended)."""
        text = self.filters['network']
        for _ in range(CAPTURE_PACKETS // READ_LIMIT + 2 if last else READ_PAGES):
            args = {'limit': READ_LIMIT}
            if self.packet_cursor is not None:args['after'] = self.packet_cursor
            if text:args['filter'] = text
            r = self.network('network.capture.read', args)
            if not (r or {}).get('ok'):self.problem = self.reason(r);self.capture_note.setText(self.problem);self.capture_note.show();self.fit_note();return
            result = r['result'] or {};before = self.packet_cursor;self.packet_cursor = result.get('next', self.packet_cursor);self.captured = True
            if result.get('capture'):self.capture = dict(result['capture'])
            self.take_reported(result);self.add_packets(result.get('packets') or [])
            if not result.get('rest') or self.packet_cursor == before:break

    def show_interfaces(self, interfaces):
        self.interfaces_seen = list(interfaces)
        if not interfaces:self.interfaces.setText('');self.interfaces.setVisible(False);return
        words = []
        for i in interfaces:
            words.append('%s%s  ↓ %s  ↑ %s' % (i.get('name', '?'), '' if i.get('up', True) else ' (down)', rate(i.get('rx_bps')), rate(i.get('tx_bps'))))
        self.interfaces.setText('INTERFACES   ' + '   ·   '.join(words));self.interfaces.setVisible(True)

    def show_connections(self, connections):
        rows = [dict(c, stream='network', kind='connection') for c in connections]
        rows = [c for c in rows if matches(c, self.parts)]
        self.connections_seen = rows
        bar = self.connections.verticalScrollBar();old = bar.value();key = self.pinned_key();current = None
        self.connections.setUpdatesEnabled(False);self.connections.clear()
        for c in rows[-MAX_ROWS:]:
            line = connection_line(c);item = QListWidgetItem(line);c['line'] = line;item.setData(Qt.UserRole, c);item.setToolTip(line);self.connections.addItem(item)
            if key is not None and self.key_of(c) == key:current = item
        if not rows:
            item = QListWidgetItem('No connections match that filter.' if self.filters['network'] else ('No open connections.' if self.observed else ''));item.setFlags(Qt.NoItemFlags)
            if item.text():self.connections.addItem(item)
        self.connections.setUpdatesEnabled(True)
        if current is not None:self.connections.setCurrentItem(current)
        bar.setValue(old)
        self.connections_head.setText('CONNECTIONS · %d' % len(rows) + (' of %d' % (len(rows) + self.rest) if self.rest else ''))

    def add_packets(self, packets):
        added = False
        if self.packets.count() == 1 and not self.packets.item(0).data(Qt.UserRole):self.packets.clear()
        for p in packets:
            entry = dict(p, stream='network', kind='packet')
            if not matches(entry, self.parts):continue
            line = packet_line(entry);entry['line'] = line;item = QListWidgetItem(line);item.setData(Qt.UserRole, entry);item.setToolTip(line)
            self.packets.addItem(item);added = True
        while self.packets.count() > MAX_ROWS:self.packets.takeItem(0)
        if added and self.packets.isHidden():self.packets.show();self.fit_note()  # packets to show: the list is back
        if added and self.follow.isChecked():self.packets.scrollToBottom()
        self.packets_head.setText('PACKETS · %d' % sum(1 for i in range(self.packets.count()) if self.packets.item(i).data(Qt.UserRole)))

    def show_capture(self):
        """The capture's state in the head row and above the packets: idle (Capture… or Ctrl+Enter; a capture Graphite proposed
        in an assignment, in D5's words, for the owner to start), running (Stop capture), refused (the capability's words, until
        the next capture or filter: D3-fix, they were overwritten at once), unavailable with the reason and how to enable it,
        in the capability's words (never sudo)."""
        network = self.stream == 'network';state = str(self.capture.get('state') or ('IDLE' if self.observed else ''))
        running = state == 'RUNNING';unavailable = state == 'UNAVAILABLE'
        self.start_button.setVisible(network and state == 'IDLE');self.stop_button.setVisible(network and running)
        self.follow.setVisible(True)
        if not network:self.capture_words.setText('');return
        if running:
            started = self.capture.get('started');took = ' · %ds' % max(0, int(time.time() - float(started))) if isinstance(started, (int, float)) else ''
            words = 'Capturing%s · %s packets%s' % ((' on ' + str(self.capture['tool'])) if self.capture.get('tool') else '', self.capture.get('packets', 0), took)
            note = 'Capturing packet headers%s.' % ((' with the filter ' + str(self.capture['filter'])) if self.capture.get('filter') else '')
        elif unavailable:
            words = 'Capture unavailable';note = str(self.capture.get('reason') or 'Capture is not available on this computer.')
        elif state == 'IDLE' and self.refusal:
            words = 'Not captured';note = self.refusal
        elif state == 'IDLE':
            proposal = self.capture.get('proposal') if isinstance(self.capture.get('proposal'), dict) else None
            words = 'Capture idle'
            note = str(proposal.get('words')) if proposal and proposal.get('words') else 'No capture is running. Ctrl+Enter in the line, or Capture…, captures packet headers with the filter.'
        else:words = '';note = self.problem or ''
        self.capture_words.setText(words);self.capture_note.setText(note);self.capture_note.setVisible(bool(note))
        # Where capture is unavailable and nothing was captured, no packet can come: the empty list gives its room to the reason
        # and the connections (the integration found the reason cut where the lists stand one above the other).
        shown = any(self.packets.item(i).data(Qt.UserRole) for i in range(self.packets.count()))
        empty = network and unavailable and not self.captured and not shown
        if self.packets.isHidden() != empty:self.packets.setVisible(not empty)
        self.fit_note()

    def scroll_latest(self):
        for view in (self.events, self.packets):view.scrollToBottom()

    # -- capture -------------------------------------------------------------------------------------------------------------
    def start_capture(self, text=None):
        """Ctrl+Enter in the Network stream (or Capture…): the owner's own capture, with the line's filter. The first of a run
        asks first. Returns the capability's response, or None when nothing was started."""
        text = self.filters['network'] if text is None else str(text).strip()
        if self.stream != 'network':self.choose('network', remember=True)
        if text != self.filters['network']:self.apply_filter(text)
        if self.capture.get('state') == 'UNAVAILABLE':self.show_capture();return None  # the reason is shown; nothing to offer
        if self.capture.get('state') == 'RUNNING':return None
        _, errors = capture_filter(text)
        if errors:  # the capability's own grammar refuses these words: nothing to confirm, nothing started; its words shown
            self.refusal = 'Nothing was captured: ' + '; '.join(plain_words(e) for e in errors) + '.';self.show_capture();return None
        if not self.confirmed:
            answer = QMessageBox.question(self.window() if self.window() is not None else None, 'Capture network traffic', confirmation_words(text),
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:return None
            self.confirmed = True
        args = {'seconds': CAPTURE_SECONDS, 'packets': CAPTURE_PACKETS}
        if text:args['filter'] = text
        r = self.network('network.capture.start', args);result = ((r or {}).get('result') or {}) if (r or {}).get('ok') else {}
        if (r or {}).get('ok') and result.get('started', True) is not False:  # started (a contract answer without 'started' has)
            self.capture = dict(result.get('capture') or {});self.packet_cursor = None;self.packets.clear();self.captured = True;self.refusal = None
            self.following = self.capture.get('state') == 'RUNNING'
        elif (r or {}).get('ok'):  # answered without starting: one is running already, capture is unavailable, or its words why
            self.capture = dict(result.get('capture') or self.capture)
            if self.capture.get('state') not in ('RUNNING', 'UNAVAILABLE'):self.refusal = plain_words(result.get('reason') or 'The capture did not start.')
        elif unknown(r):self.capture = {'state': 'UNAVAILABLE', 'reason': self.reason(r)}
        else:self.refusal = self.reason(r)  # refused: the capability's words stay (show_capture shows them, D3-fix)
        self.show_capture();return r

    def stop_capture(self):
        r = self.network('network.capture.stop', {});self.refusal = None
        if (r or {}).get('ok'):self.capture = dict((r['result'] or {}).get('capture') or {})
        if self.captured and self.capture.get('state') != 'UNAVAILABLE':self.read_packets(last=True)  # what was captured before the stop
        self.following = self.capture.get('state') == 'RUNNING'
        self.show_capture();return r

    # -- pinning -------------------------------------------------------------------------------------------------------------
    @staticmethod
    def key_of(entry):
        if entry is None:return None
        if entry.get('kind') == 'event':return ('event', entry.get('id'))
        if entry.get('kind') == 'packet':return ('packet', entry.get('seq'), entry.get('at'))
        return ('connection', entry.get('proto'), entry.get('local'), entry.get('lport'), entry.get('remote'), entry.get('rport'))

    def pinned_key(self):return self.key_of(self.pinned)

    def chose(self, item):
        entry = item.data(Qt.UserRole) if item is not None else None
        if entry:self.pin(entry)

    def pin(self, entry):
        """Pin an entry at the top with its details; it stays while the stream scrolls and refreshes."""
        self.pinned = dict(entry)
        self.pin_title.setText(entry.get('line') or (event_line(entry['event']) if entry.get('kind') == 'event' else connection_line(entry) if entry.get('kind') == 'connection' else packet_line(entry)))
        rows = details(entry);self.pin_details.setText('   '.join('%s %s' % kv for kv in rows))
        follow = {'ask': ('Ask Stacy about this', lambda:self.ask()), 'unpin': ('Unpin', lambda:self.unpin())}
        if entry.get('stream') == 'network' and conversation(entry):
            follow['follow'] = ('Follow this conversation', lambda e=dict(entry):self.follow_conversation(e))
            from .shell2 import sentence
            sentence('{ask}  ·  {follow}  ·  {unpin}', follow, self.pin_actions)
        else:
            from .shell2 import sentence
            sentence('{ask}  ·  {unpin}', follow, self.pin_actions)
        self.pin_frame.setAccessibleName('Pinned ' + {'event': 'event', 'connection': 'connection', 'packet': 'packet'}.get(entry.get('kind'), 'entry'))
        self.pin_frame.show();self.note.hide()  # the pin takes the note's place: the stream keeps its room

    def unpin(self):
        self.pinned = None;self.pin_frame.hide();self.note.show()

    def ask(self, entry=None):
        entry = entry or self.pinned
        if entry is not None:ask_about(self.host, entry)

    def follow_conversation(self, entry):
        text = conversation(entry);bar = getattr(self.host, 'type_bar', None)
        if bar is not None:bar.box.setText(text)
        self.apply_filter(text)

    def entry_at(self, global_point):
        """The entry under a point (global coordinates): a row of a stream, or the pinned entry; None elsewhere."""
        if self.pin_frame.isVisible() and self.pin_frame.rect().contains(self.pin_frame.mapFromGlobal(global_point)):return dict(self.pinned) if self.pinned else None
        for view in (self.events, self.connections, self.packets):
            if not view.isVisible():continue
            local = view.viewport().mapFromGlobal(global_point)
            if view.viewport().rect().contains(local):
                item = view.itemAt(local);entry = item.data(Qt.UserRole) if item is not None else None
                return dict(entry) if entry else None
        return None

    # -- the line's summary (Line mode) --------------------------------------------------------------------------------------
    def summary(self):
        """One line for the band's quiet words while the working area is closed (Line)."""
        if self.stream == 'events':
            last = next((self.events.item(i).text() for i in range(self.events.count() - 1, -1, -1) if self.events.item(i).data(Qt.UserRole)), None)
            return 'Events · ' + (last or 'nothing recorded yet')
        if self.problem and not self.observed:return 'Network · ' + self.problem
        rates = '  '.join('%s ↓ %s ↑ %s' % (i.get('name', '?'), rate(i.get('rx_bps')), rate(i.get('tx_bps'))) for i in self.interfaces_seen if i.get('name') != 'lo')
        state = str(self.capture.get('state') or 'IDLE')
        capture = {'RUNNING': 'capturing · %s packets' % self.capture.get('packets', 0), 'IDLE': 'capture idle', 'UNAVAILABLE': 'capture unavailable'}.get(state, state.lower())
        return ' · '.join(x for x in ('Network', rates, '%d connections' % len(self.connections_seen), capture) if x)

    def resizeEvent(self, event):
        """Connections and packets side by side when the area is wide (WIDE characters of the rows' face for both), else one
        above the other, so a row keeps its addresses whole in a narrow window or at a large text size."""
        super().resizeEvent(event);self.arrange()

    def arrange(self):
        """The lists' direction for the view's width and the rows' face as it is now (after a resize, a show or a restyle)."""
        from PySide6.QtWidgets import QBoxLayout
        self.packets.ensurePolished()
        wide = self.width() >= WIDE * self.packets.fontMetrics().horizontalAdvance('0')
        direction = QBoxLayout.LeftToRight if wide else QBoxLayout.TopToBottom
        if self.lists.direction() != direction:self.lists.setDirection(direction)
        self.fit_note()

    def fit_note(self):
        """The capture's reason as tall as its words (NOTE_LINES at most when the lists are one above the other, NOTE_LINES_WIDE
        side by side), the rest reached by its own scroll; hidden with the note."""
        from PySide6.QtWidgets import QBoxLayout
        stacked = self.lists.direction() == QBoxLayout.TopToBottom
        stretch = 0 if stacked and self.packets.isHidden() else 1  # one above the other with no packet list: the connections take the rest
        if self.lists.stretch(1) != stretch:self.lists.setStretch(1, stretch)
        note = self.capture_note;area = self.note_area;shown = bool(note.text()) and not note.isHidden()
        if area.isHidden() == shown:area.setVisible(shown)
        if not shown:return
        width = max(1, (area.viewport().width() if area.width() > 1 else self.width() // (2 if self.lists.direction() == QBoxLayout.LeftToRight else 1)))
        lines = NOTE_LINES_WIDE if self.lists.direction() == QBoxLayout.LeftToRight else NOTE_LINES
        need = note.heightForWidth(width);cap = lines * note.fontMetrics().lineSpacing() + 2
        height = min(need, cap) if need > 0 else note.sizeHint().height()
        if area.height() != height or area.minimumHeight() != height:area.setFixedHeight(height)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if need > cap else Qt.ScrollBarAlwaysOff)

    def showEvent(self, event):
        super().showEvent(event);self.style_view();self.arrange()
        for tab in self.tabs.values():tab.ensurePolished();tab.updateGeometry()  # sized at the window's current text size
        self.refresh(force=True)


# For the writing line and D4's right-click menu ---------------------------------------------------------------------------------

def view_of(host):
    return getattr(host, 'log_view', None)


def entry_at(widget, point):
    """The entry under `point` (in `widget`'s coordinates) in the Log view, or None: a dict with 'stream' ('events' or
    'network') and, for the network, 'kind' ('connection' or 'packet'), with the entry's own fields."""
    if widget is None:return None
    view = widget if isinstance(widget, LogView) else None
    parent = widget
    while view is None and parent is not None:
        parent = parent.parentWidget()
        if isinstance(parent, LogView):view = parent
    if view is None:return None
    return view.entry_at(widget.mapToGlobal(point if isinstance(point, QPoint) else QPoint(*point)))


def focus(host, entry):
    """Put the writing line in Log mode on the entry's stream with the entry pinned; a network entry's stream is filtered to its
    conversation (the filter is put in the line too, so the owner sees and can change it). Opens the working area at Half
    when it was one line."""
    view = view_of(host);bar = getattr(host, 'type_bar', None)
    if view is None or not entry:return None
    if bar is not None:bar.set_target('log', focus=False)
    view.choose(entry.get('stream', 'events'), remember=True)
    console = getattr(host, 'console', None)
    if console is not None and console.size_level == 0:console.set_size(1)
    if entry.get('stream') == 'network':
        text = conversation(entry)
        if bar is not None:bar.box.setText(text)
        view.apply_filter(text)
    view.pin(entry)
    if bar is not None:bar.box.setFocus()
    return view


def ask_about(host, entry):
    """"Ask Stacy about this": the line in Assignment mode with the entry as the assignment's context, the cursor after it."""
    bar = getattr(host, 'type_bar', None)
    if bar is None or not entry:return None
    bar.set_target('slate', focus=False);bar.box.setText(assignment_text(entry));bar.box.setFocus();bar.box.end(False)
    return bar.box.text()


def install(host, console):
    """The Log view in the console's place above the band (the working area): shown in Log mode at Half and Tall."""
    if getattr(host, 'log_view', None) is not None:return host.log_view
    view = LogView(host);host.log_view = view
    console.layout().insertWidget(0, view);view.hide();view.timer.start()
    return view
