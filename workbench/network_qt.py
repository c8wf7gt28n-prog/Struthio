"""The network in the window (Graphite 1.0, K8): its state in the head, her network use in her column, her web reading
in the centre, and "look up …" from the writing line.

  the head          a small state word left of Apps, with a shape as well as a colour: ● online, ⊘ offline, ◌ not known,
                    ⇣ her fetch: <host> while she fetches. A click opens her web reading. The tooltip says why (NetworkManager,
                    or the system's routes where NetworkManager is not here).
  her column        one line under the progress line, shown when she uses the network: "⇣ her fetch: example.org"; "⊘ offline ·
                    a step needs the network" (an assignment blocked on it); "● online · “…” waits: try it now" with its one
                    press; "her last fetch: <host>" with "See it".
  her web reading   a page in the centre: the state; search words (yours only, shown before they are sent, with what was
                    left out and why, and where they would go: "Send these words to …", your press); an address ("Fetch the
                    page from …", your press); the pages kept in quarantine; the page chosen, as you see it (a withheld line
                    outlined, with why in words; what the page hides from a browser, outlined apart) and as the model reads it
                    (the doorway's fenced page, withheld lines replaced); its links as data (a link is put in the address box,
                    never fetched by a click).
  the writing line  "look up the regulator's datasheet", "search the web for …", "fetch <address>": web.lookup plans the step
                    from your words; she says the words it would send and where, or that the step is blocked because it needs
                    the network; one press sends (it authorises that step by its name and carries on).

The Web chooser in the foot is unchanged: it opens an address, or searches, in this computer's own browser; this is her
reading, quarantined, not your browsing. Every colour that means something also has a word or a shape; no key is named
in any of these words.
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QSizePolicy, QTextBrowser,
                               QToolButton, QVBoxLayout, QWidget)

from . import boss_theme as t
from . import network_governed as ng

WORDS = {
    'title': 'Her web reading',
    'lead': 'A page she fetches is kept in quarantine and read as data, never as instructions: a line written to an assistant '
            'is withheld from the model and shown to you outlined, with why. Search words are only the words you typed, shown '
            'before they are sent. Sending anything off this computer is your press, every time; a page from a site you granted '
            'may be fetched again under that grant.',
    'search': 'SEARCH WORDS (yours only)',
    'fetch': 'A PAGE BY ITS ADDRESS',
    'kept': 'KEPT IN QUARANTINE',
    'none_kept': 'No page is kept in quarantine yet.',
    'model': 'WHAT THE MODEL READS',
    'links': 'ITS LINKS (data: a link is fetched only by your press)',
    'send': 'Send these words to {host}',
    'get': 'Fetch the page from {host}',
    'no_words': 'Type the words to search for: only what you type is sent.',
    'no_address': 'Type an address (http or https).',
    'would_send': 'Would send “{words}” to {host}, and nothing else.',
    'would_get': 'Would ask {host} for this page, and nothing else.',
    'left_out': 'Left out: {left}.',
    'offline': 'Not now: {why}.',
    'fetching': 'Her fetch from {host} is under way…',
    'try_now': 'Try it now',
    'see_it': 'See it',
    'column_fetch': 'her fetch: {host}',
    'column_waits': '{word} · a step needs the network',
    'column_ready': '{word} · “{title}” waits for the network',
    'column_last': 'her last fetch: {host}',
    'column_failed': '{word} · her last fetch from {host} did not come: {why}',
    'put_address': 'Put it in the address box',
}
SHAPE_COLOUR = {'online': 'READY', 'offline': 'STOP', 'unknown': 'ERASED_QUIET', 'fetching': 'WIRE'}
REFRESH_MS = 3000


def say(key, **slots):
    return WORDS[key].format(**slots)


def _kernel(host):
    from .engine import engineering
    from .engineering_kernel import operator
    return engineering(host.root), operator()


def _root(host):
    try:return str(_kernel(host)[0].root)
    except Exception:  # noqa: BLE001
        return str(getattr(host, 'root', ''))


def colour_of(name):
    if t.LAUNCH and name == 'READY':return t.DAY_MARKS.get('HALT', t.READY)      # 1.0 P4: Day and Night
    if t.LAUNCH and name == 'WIRE':return t.DAY_MARKS.get('WIRE_WORDS', t.DAY_MARKS.get('WIRE', t.READY))      # 1.0 P4: the accent's words (4.5:1)
    return getattr(t, name, t.TEXT)


def reading(host, read=True):
    """The network's state for this window: read again when it is stale (a short local D-Bus read), else what was read."""
    root = _root(host)
    if read and ng.stale():
        try:return ng.state(root)
        except Exception:  # noqa: BLE001 - a state that cannot be read is said not known
            pass
    return ng.peek(root)


def kind_of(r):
    return 'fetching' if r.get('fetching') else r['state']


def paint_shape(p, kind, x, cy, side, ink):
    """The state's shape: a filled dot (online), a ring with a stroke through it (offline), a dotted ring (not known), an
    arrow down (her fetch)."""
    p.save();p.setRenderHint(QPainter.Antialiasing)
    c = QColor(ink);r = side / 2.0;centre = QPointF(x + r, cy)
    if kind == 'online':
        p.setPen(Qt.NoPen);p.setBrush(c);p.drawEllipse(centre, r * 0.78, r * 0.78)
    elif kind == 'offline':
        pen = QPen(c, max(1.6, side * 0.14));p.setPen(pen);p.setBrush(Qt.NoBrush);p.drawEllipse(centre, r * 0.78, r * 0.78)
        p.drawLine(QPointF(centre.x() - r * 0.55, centre.y() + r * 0.55), QPointF(centre.x() + r * 0.55, centre.y() - r * 0.55))
    elif kind == 'fetching':
        pen = QPen(c, max(1.6, side * 0.14));pen.setCapStyle(Qt.RoundCap);p.setPen(pen)
        p.drawLine(QPointF(centre.x(), cy - r * 0.8), QPointF(centre.x(), cy + r * 0.6))
        path = QPainterPath();path.moveTo(centre.x() - r * 0.55, cy + r * 0.1);path.lineTo(centre.x(), cy + r * 0.75)
        path.lineTo(centre.x() + r * 0.55, cy + r * 0.1);p.setBrush(Qt.NoBrush);p.drawPath(path)
    else:
        pen = QPen(c, max(1.4, side * 0.12));pen.setStyle(Qt.DotLine);p.setPen(pen);p.setBrush(Qt.NoBrush);p.drawEllipse(centre, r * 0.72, r * 0.72)
    p.restore()


def words_of_state(r):
    if r.get('fetching'):return say('column_fetch', host=r['fetching'].get('host', ''))
    return r['word']


# ================================================================================================== the head
class NetWord(QToolButton):
    """The network's state word in the head, left of Apps: a shape and a word."""

    def __init__(self, host, parent=None):
        super().__init__(parent);self.host = host;self.scale = 1.0;self.r = None;self.shown = None
        self.setObjectName('NetWord');self.setCursor(Qt.PointingHandCursor);self.setAutoRaise(True);self.setFocusPolicy(Qt.TabFocus)
        self.setAttribute(Qt.WA_Hover, True);self.setProperty('paperFunctionalInk', True)
        self.clicked.connect(lambda checked=False: show(self.host))
        self.timer = QTimer(self);self.timer.setInterval(REFRESH_MS);self.timer.timeout.connect(self.refresh);self.timer.start()
        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        if getattr(self.host, '_closing', False):return
        r = reading(self.host)
        key = (kind_of(r), words_of_state(r), r['why'])
        self.r = r
        if key == self.shown:return
        width_before = self.need(max(24, self.height()))
        self.shown = key
        words = words_of_state(r)
        said = '%s. %s.' % (words[0].upper() + words[1:], r['why'][0].upper() + r['why'][1:] if r['why'] else '')
        self.setText(words);self.setAccessibleName('The network: ' + words);self.setToolTip(said + ' A click opens her web reading.')
        if self.need(max(24, self.height())) != width_before:
            top = self.parentWidget().parentWidget() if self.parentWidget() is not None else None
            d = getattr(self.host, 'desk', None)
            if top is not None and hasattr(top, 'place') and d is not None:QTimer.singleShot(0, lambda: top.place(getattr(self.host, 'desk', None)))
        self.update()

    def word_font(self):
        s = min(max(self.scale, 0.8), 1.4)
        if t.APPEARANCE == 'kasandra':f = QFont(t.DISPLAY);f.setPixelSize(max(13, round(15 * s)))
        elif t.LAUNCH:f = QFont(t.FACE);f.setPixelSize(max(13, round(15 * s)));f.setWeight(QFont.DemiBold)      # 1.0 P4: Day and Night
        else:f = QFont(t.MONO);f.setPixelSize(max(12, round(14 * s)))
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.6 * s)
        return f

    def side(self, height):
        return max(10.0, round(height * 0.34))

    def pad(self):
        return round(8 * min(max(self.scale, 0.8), 1.4))

    def need(self, height):
        fm = QFontMetricsF(self.word_font());side = self.side(height)
        text = self.text() or 'network not known'
        return round(side + side * 0.5 + max(fm.horizontalAdvance(text), fm.horizontalAdvance('offline')) + 2 * self.pad())

    def sizeHint(self):
        h = max(24, round(34 * self.scale));return QSize(self.need(h), h)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height();edge = max(2, round(2 * self.scale))
        if self.underMouse():p.fillRect(self.rect(), QColor(t.TEAL_SOFT));p.fillRect(0, h - edge, w, edge, QColor(t.READY))
        elif self.hasFocus():p.fillRect(self.rect(), QColor(t.AMBER_SOFT));p.fillRect(0, h - edge, w, edge, QColor(t.AMBER_EDGE))
        r = self.r or ng.peek(_root(self.host));kind = kind_of(r)
        side = self.side(h);x = self.pad();cy = h / 2.0
        paint_shape(p, kind, x, cy, side, colour_of(SHAPE_COLOUR[kind]))
        font = self.word_font();p.setFont(font);fm = QFontMetricsF(font)
        tx = x + side + side * 0.5;p.setPen(QColor(t.ERASED))
        rect = QRectF(tx, 0, max(0.0, w - tx - self.pad() / 2), h)
        p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(self.text(), Qt.ElideRight, rect.width()))
        p.end()


def install_head(top):
    """shell2's head: the network's word left of Apps (1.0 K8)."""
    word = NetWord(top.host, top.first_row);top.net_word = word;word.show()
    return word


def place_head(top, x, h, gap, d):
    """shell2's head placement: the network's word to the left of Apps; returns the x the menus may reach."""
    word = getattr(top, 'net_word', None)
    if word is None:return x
    if getattr(top.host, 'net_meter', None) is not None:      # 1.0 D1: NET at the foot carries the state now (one place)
        if word.isVisible():word.hide()
        if word.timer.isActive():word.timer.stop()
        return x
    word.scale = min(d.scale, 1.4)
    tall = max(22, h - 2 * round(8 * min(d.scale, 1.4)));wide = word.need(tall)
    x -= wide;word.setGeometry(x, (h - tall) // 2, wide, tall);word.show();word.raise_()
    return x - gap


# ================================================================================================== her column
class ColumnLine(QWidget):
    """Her network use, one line in her column (shown only when she uses the network or a step waits for it)."""

    def __init__(self, column):
        super().__init__();self.column = column;self.host = column.host;self.press_call = None;self.shown = None
        from .her_column_qt import ink, px, row_label, small_button
        self.setObjectName('HerNetLine')
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(px(self.host, 6))
        self.shape = ShapeDot(self.host);row.addWidget(self.shape, 0, Qt.AlignVCenter)
        self.words = row_label(self.host, '', size=12);row.addWidget(self.words, 1)
        ink(self.words, px(self.host, 12), t.QUIET, 500, t.MONO);self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.button = small_button(self.host, say('try_now'), 'Your press: the step is authorised by its name and carried on')
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.button.clicked.connect(self.press);row.addWidget(self.button, 0);self.button.hide()
        self.hide()
        self.timer = QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh);self.timer.start()
        QTimer.singleShot(0, self.refresh)

    def refresh(self):
        if getattr(self.host, '_closing', False):return
        try:r = reading(self.host)
        except Exception:  # noqa: BLE001 - the column is whole without this line
            self.hide();return
        kernel, owner = _kernel(self.host)
        blocked = [row for row in (getattr(self.column, 'rows', None) or ()) if row.get('state_words') == ng.NEEDS]      # her column read them
        waiting = ng.waiting_on_network(kernel, owner, 4) if blocked and not r.get('fetching') else []
        last = r.get('last') or {}
        recent = last and (ng.now_ms() - int(last.get('at') or 0)) < ng.RECENT_MS
        kind, words, button, call, tip = kind_of(r), '', '', None, r['why']
        if r.get('fetching'):words = say('column_fetch', host=r['fetching'].get('host', ''))
        elif waiting:
            first = waiting[0]
            if r['state'] == 'online':
                words = say('column_ready', word=r['word'], title=first['title']);button = say('try_now');call = ('retry', first)
            else:
                words = say('column_waits', word=r['word']);tip = '“%s”: %s. Nothing was sent.' % (first['title'], first['reason'])
        elif recent:
            if last.get('ok'):
                words = say('column_last', word=r['word'], host=last.get('host', ''));button = say('see_it');call = ('see', last)
                if last.get('withheld') or last.get('hidden'):
                    tip = 'Kept in quarantine and read as data: %d line%s withheld from the model.' % (
                        last['withheld'] + last['hidden'], '' if last['withheld'] + last['hidden'] == 1 else 's')
            else:
                words = say('column_failed', word=r['word'], host=last.get('host', ''), why=last.get('why', ''))
        key = (kind, words, button)
        if not words:
            self.hide();self.shown = None;return
        self.press_call = call
        if key != self.shown:
            self.shown = key
            self.shape.set(kind);self.words.setText(words);self.words.setToolTip(tip);self.setAccessibleName('Her network use: ' + words)
            self.button.setText(button or say('see_it'));self.button.setVisible(bool(button))
        self.show()

    def press(self):
        call = self.press_call
        if not call:return
        if call[0] == 'see':
            tab = show(self.host)
            if call[1].get('id'):tab.choose(call[1]['id'])
            return
        if call[0] == 'retry':retry(self.host, call[1])


class ShapeDot(QWidget):
    """The state's shape, alone (her column's line)."""

    def __init__(self, host):
        super().__init__();self.host = host;self.kind = 'unknown'
        from .her_column_qt import px
        side = px(host, 14);self.setFixedSize(side, side)

    def set(self, kind):
        if kind != self.kind:self.kind = kind;self.update()

    def paintEvent(self, event):
        p = QPainter(self);paint_shape(p, self.kind, 0, self.height() / 2.0, self.height(), colour_of(SHAPE_COLOUR[self.kind]));p.end()


def retry(host, waiting):
    """A step blocked on the network, tried again by your press: authorised by its name, then carried on (it is blocked
    again, with the reason, if the network is still down)."""
    from .her_column_qt import press as column_press
    done, why = column_press(host, 'assignment.plan', {'id': waiting['id'], 'authorise': [waiting['step']], 'expected_digest': waiting['digest']})
    column = getattr(host, 'her_column', None)
    if done is None:
        if column is not None:column.say_words('That press was refused: %s' % why)
        return
    call = {'operation': 'assignment.step', 'arguments': {'id': waiting['id'], 'until': 'end'}, 'words': 'Carry on'}
    if column is not None:column.carry(call, waiting.get('title', ''))
    else:_in_a_thread(host, call['operation'], call['arguments'])


def _in_a_thread(host, operation, arguments, then=None):
    """A send off the window's thread (a fresh Kernel on the same workspace); then(answer) back on the window's thread."""
    from .engineering_kernel import Kernel, operator
    root = _kernel(host)[0].root;result = {}

    def work():
        try:result['answer'] = Kernel(root).dispatch(operation, arguments, operator())
        except Exception as exc:  # noqa: BLE001
            result['answer'] = {'ok': False, 'error': {'message': str(exc)}}
    thread = threading.Thread(target=work, name='her-web-fetch', daemon=True);thread.start()

    def check():
        if thread.is_alive():QTimer.singleShot(300, check);return
        if then is not None:then(result.get('answer') or {})
    QTimer.singleShot(300, check)
    return thread


# ================================================================================================== the writing line
def asked(face, text):
    """The writing line: words that ask her to look something up on the web. web.lookup plans the step from your words;
    she says what it would send and where, or that it is blocked because it needs the network; one press sends."""
    if ng.reads_as(text) is None:return False
    from .shell2 import call_write, escape_text, sentence
    host = face.host
    face.thing = None;face.mine(text)
    answer = call_write(host, 'web.lookup', {'request': text})
    if not answer.get('ok'):
        face.say(str((answer.get('error') or {}).get('message', 'I could not plan that')).split(': ', 1)[-1]);return True
    v = answer['result'];G = v['assignment'];words = v['words']
    if words.get('kind') == 'search':
        said = 'Search words, from your words only: “%s”, to %s.' % (words['words'], words['host'])
        if words.get('left_out'):said += ' ' + say('left_out', left='; '.join('“%s”: %s' % (w['word'], w['why']) for w in words['left_out'][:3]))
        go_words = say('send', host=words['host'])
    else:
        said = 'The address you typed goes to %s, and nothing else.' % words['host']
        go_words = say('get', host=words['host'])
    if v['blocked']:
        lead = 'Step 1 of “%s” is blocked: %s. Nothing was sent. %s' % (G['title'], v['blocked'], said)
        go_words = say('try_now')
    else:
        lead = '“%s” waits for your press. %s Sending is your press, every time.' % (G['title'], said)
    bubble = face.say(lead)
    step = next((s for s in G['steps'] if s['key'] == v['step']), None)

    def go():
        if step is None:return
        retry(host, {'id': G['id'], 'step': step['key'], 'digest': G['plan_digest'], 'title': G['title']})
    actions = {'go': (go_words, go), 'page': (say('title'), lambda: show(host))}
    line = '{go}  ·  {page}'
    if words.get('kind') == 'search':
        def library(q=words['words']):
            from .library_qt import ask as ask_library
            ask_library(face, q)
        actions['library'] = ('Ask the Library instead', library);line = '{go}  ·  {library}  ·  {page}'
    try:bubble.box.addWidget(sentence(line, actions))
    except Exception:  # noqa: BLE001 - a bubble without a box still says it
        pass
    column = getattr(host, 'her_column', None)
    if column is not None:
        try:column.refresh(force=True)
        except Exception:  # noqa: BLE001
            pass
    _ = escape_text
    return True


# ================================================================================================== her web reading (the centre)
class WebTab(QWidget):
    """Her web reading: the state, search words, an address, the pages kept in quarantine, the page as you see it and as
    the model reads it, and its links as data."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        self.chosen = None;self.listed = None;self.busy = False
        from .shell2 import role
        outer = QHBoxLayout(self);outer.setContentsMargins(32, 22, 32, 16);outer.setSpacing(24)
        left = QVBoxLayout();left.setSpacing(10);right = QVBoxLayout();right.setSpacing(8)
        holder = QWidget();holder.setLayout(left);left.setContentsMargins(0, 0, 8, 0)
        scroll = QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setWidget(holder)      # never squeezed: it scrolls
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);scroll.setMaximumWidth(540);scroll.setMinimumWidth(270)
        outer.addWidget(scroll, 4);outer.addLayout(right, 6)
        left.addWidget(role(QLabel(say('title')), 'title'))
        lead = role(QLabel(say('lead')), 'lead');lead.setWordWrap(True);lead.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);left.addWidget(lead)
        state_row = QHBoxLayout();state_row.setSpacing(8)
        self.dot = ShapeDot(host);state_row.addWidget(self.dot, 0, Qt.AlignVCenter)
        self.state = QLabel();self.state.setWordWrap(True);self.state.setTextFormat(Qt.RichText)
        self.state.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);state_row.addWidget(self.state, 1)
        left.addLayout(state_row)
        left.addWidget(role(QLabel(say('search')), 'section'))
        self.words = QLineEdit();self.words.setPlaceholderText('words to search for');self.words.setAccessibleName('Search words')
        self.words.textChanged.connect(self.preview);left.addWidget(self.words)
        self.words_said = QLabel();self.words_said.setWordWrap(True);self.words_said.setTextFormat(Qt.PlainText)
        self.words_said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);left.addWidget(self.words_said)
        from .her_column_qt import small_button
        self.send = small_button(host, say('send', host='…'), 'Your press: these words, and nothing else, go to the search service', primary=True)
        self.send.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.send.clicked.connect(self.press_search);left.addWidget(self.send, 0, Qt.AlignLeft)
        left.addWidget(role(QLabel(say('fetch')), 'section'))
        self.address = QLineEdit();self.address.setPlaceholderText('https://…');self.address.setAccessibleName('A page’s address')
        self.address.textChanged.connect(self.preview);left.addWidget(self.address)
        self.address_said = QLabel();self.address_said.setWordWrap(True);self.address_said.setTextFormat(Qt.PlainText)
        self.address_said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);left.addWidget(self.address_said)
        self.get = small_button(host, say('get', host='…'), 'Your press: this address, and nothing else, goes to its site', primary=True)
        self.get.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.get.clicked.connect(self.press_get);left.addWidget(self.get, 0, Qt.AlignLeft)
        left.addWidget(role(QLabel(say('kept')), 'section'))
        self.pages = QVBoxLayout();self.pages.setSpacing(4);left.addLayout(self.pages)
        left.addStretch(1)
        self.heading = role(QLabel(''), 'item');self.heading.setWordWrap(True);self.heading.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        right.addWidget(self.heading)
        self.card = QLabel();self.card.setWordWrap(True);self.card.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);right.addWidget(self.card)
        self.view = QTextBrowser();self.view.setOpenLinks(False);self.view.setOpenExternalLinks(False);self.view.setAccessibleName('The page as you see it')
        self.view.setMinimumHeight(150);right.addWidget(self.view, 5)      # at your reading size (reading_preferences), as every page you read
        right.addWidget(role(QLabel(say('model')), 'section'))
        self.model = QPlainTextEdit();self.model.setReadOnly(True);self.model.setAccessibleName('The page as the model reads it')
        self.model.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.model.setMinimumHeight(84);right.addWidget(self.model, 2)
        right.addWidget(role(QLabel(say('links')), 'section'))
        self.links = QTextBrowser();self.links.setOpenLinks(False);self.links.setOpenExternalLinks(False);self.links.setAccessibleName('Its links, as data')
        self.links.anchorClicked.connect(self.put_link);self.links.setMinimumHeight(64);right.addWidget(self.links, 1)
        self.timer = QTimer(self);self.timer.setInterval(REFRESH_MS);self.timer.timeout.connect(self.reload)
        self.reload();self.preview()

    def title(self):return say('title')

    def showEvent(self, event):super().showEvent(event);self.reload();self.timer.start()

    def hideEvent(self, event):super().hideEvent(event);self.timer.stop()

    def note(self, words):
        try:self.host.statusBar().showMessage(words, 8000)
        except Exception:  # noqa: BLE001
            pass

    def r(self):
        return reading(self.host)

    def reload(self):
        from .shell2 import call, sentence
        r = self.r();kind = kind_of(r)
        self.dot.set(kind)
        self.state.setText('<b>%s</b> · %s' % (words_of_state(r), _esc(r['why'])))
        view = call(self.host, 'web.pages', {'limit': 12}) or {'pages': []}
        rows = view.get('pages') or []
        key = repr([(p['id'], p['withheld'], p['hidden']) for p in rows])
        if key != self.listed:
            self.listed = key
            while self.pages.count():
                item = self.pages.takeAt(0)
                if item.widget() is not None:item.widget().deleteLater()
            if not rows:self.pages.addWidget(QLabel(say('none_kept')))
            for p in rows:
                held = p['withheld'] + p['hidden']
                mark = ('▣ %d withheld' % held) if held else '□ nothing withheld'
                what = ('search: “%s”' % p['words']) if p['kind'] == 'search' else p['title']
                label = sentence('{open}<br><span style="color:%s">%s · %s · %s</span>' % (
                    t.QUIET, _esc(p['host']), time.strftime('%d %b, %H:%M', time.localtime(p['at'] // 1000)), mark),
                    {'open': (what[:90], lambda i=p['id']: self.choose(i))})
                label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.pages.addWidget(label)
            if self.chosen is None and rows:self.choose(rows[0]['id'])
        self.preview()

    def preview(self, *args):
        r = self.r();online = r['state'] == 'online' and not r.get('fetching')
        words = ng.words_of(self.words.text()) if self.words.text().strip() else None
        if words and words['words']:
            said = say('would_send', words=words['words'], host=words['host'])
            if words['left_out']:said += ' ' + say('left_out', left='; '.join('“%s”: %s' % (w['word'], w['why']) for w in words['left_out'][:3]))
            self.send.setText(say('send', host=words['host']))
        else:
            said = say('no_words');self.send.setText(say('send', host=ng.check_address(ng.search_address('x'))['host']))
        if not online:said += ' ' + (say('fetching', host=r['fetching']['host']) if r.get('fetching') else say('offline', why=ng.needs_words(r)))
        self.words_said.setText(said);self.send.setEnabled(bool(words and words['words']) and online and not self.busy)
        try:
            where = ng.check_address(self.address.text()) if self.address.text().strip() else None
            said = say('would_get', host=where['host']) if where else say('no_address')
            self.get.setText(say('get', host=where['host'] if where else '…'))
        except ValueError as why:
            where = None;said = str(why).split(': ', 1)[-1]
        if not online:said += ' ' + (say('fetching', host=r['fetching']['host']) if r.get('fetching') else say('offline', why=ng.needs_words(r)))
        self.address_said.setText(said);self.get.setEnabled(bool(where) and online and not self.busy)

    def press_search(self):
        words = ng.words_of(self.words.text())
        if not words['words']:return
        self.run('web.search', {'words': words['words'], 'typed': self.words.text()})

    def press_get(self):
        self.run('web.get', {'page': self.address.text().strip()})

    def run(self, op, args):
        if self.busy:return
        self.busy = True;self.preview()

        def then(answer):
            self.busy = False
            if answer.get('ok'):
                v = answer['result'];self.listed = None;self.reload();self.choose(v['id']);self.note(v.get('said', '')[:300])
            else:
                self.note(str((answer.get('error') or {}).get('message', 'Not done')).split(': ', 1)[-1][:300]);self.reload()
            self.preview()
        _in_a_thread(self.host, op, args, then)

    def choose(self, ident):
        from .shell2 import call
        v = call(self.host, 'web.page', {'id': ident})
        if not v:return
        self.chosen = ident
        what = ('Search: “%s”' % v['words']) if v['kind'] == 'search' else (v['title'] or v['host'])
        self.heading.setText(_esc(what))
        held = len(v['withheld']) + len(v['hidden'])
        self.card.setText('<span style="color:%s">%skept in quarantine, read as data · %s · %d bytes%s · digest %s… %s</span>' % (
            t.QUIET, '▣ %d withheld from the model · ' % held if held else '□ nothing withheld · ', _esc(v['by']),
            v['bytes'], '' if v['complete'] else ' (cut short)', v['sha256'][:12], '· read back intact' if v['intact'] else '· DOES NOT READ BACK'))
        self.card.setToolTip(v['quarantine'])
        self.view.setHtml(v['owner_html'])
        if held:QTimer.singleShot(120, self.to_withheld)      # after your reading size has been laid on the page
        self.model.setPlainText(v['model_page'] or '(the model reads nothing of this page: %s)' % (v['note'] or 'it is not text'))
        links = v.get('links') or []
        if links:
            self.links.setHtml(''.join('<p>%s<br><a href="%s">%s</a>%s</p>' % (
                _esc(l.get('text') or '(no words)'), _esc(l['address']), _esc(l['address'][:140]),
                ' <i>(hidden on the page)</i>' if l.get('hidden') else '') for l in links[:60]))
        else:self.links.setPlainText('No links.')

    def to_withheld(self):
        """The page scrolled so its first withheld line (outlined) stands in the middle of the view."""
        found = self.view.document().find('Not read to the model')
        if found.isNull():return
        found.clearSelection();self.view.setTextCursor(found);self.view.ensureCursorVisible()
        bar = self.view.verticalScrollBar();rect = self.view.cursorRect()
        bar.setValue(max(0, min(bar.maximum(), bar.value() + rect.top() - self.view.viewport().height() // 2)))

    def put_link(self, url):
        """A link is never fetched by a click: it goes to the address box, and fetching it is your press."""
        self.address.setText(url.toString());self.preview()
        self.note('The link is in the address box: it came from the page, not from you, so fetching it is your press.')


def _esc(text):
    from html import escape
    return escape(str(text or ''))


def show(host):
    """Open (or reuse) her web reading in the centre."""
    try:host._close_start()
    except Exception:  # noqa: BLE001
        pass
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, WebTab):host.tabs.setCurrentWidget(tab);tab.reload();return tab
    tab = WebTab(host);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab


def install_column(column):
    """Her column: the network line under the progress line (1.0 K8); her ACTIVE WORK's shape for a step that needs it."""
    try:
        from . import her_column_qt
        from . import state_words      # 1.0 D1: a step blocked on the network has the table's blocked shape (⊘ is NET's offline)
        her_column_qt.WORK_LOOK.setdefault(ng.NEEDS, (state_words.shape('blocked', '⊘'), 'STOP'))
    except Exception:  # noqa: BLE001
        pass
    column.net_line = ColumnLine(column)
    return column.net_line
