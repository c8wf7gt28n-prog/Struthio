"""The four meters at the foot of the window are doors.

The owner, 13 November 2026: "How much of the system menu could we move into clickable: cpu/gpu/ram/text? Could we
eliminate the system menu if we got creative ... Brain room can probably move into system menu ... Full chat in Stacy
column can probably move into log".

All of it could, so the System menu is gone from the head. Each thing went behind the meter it is about, and what is about
no meter went to the place a person would look for it:

  CPU   Graphite's work on the processor: what runs and what waits, each with its niceness; Stop all jobs; the queue's
        order; background priority; the Agenda and the Work trail. (It is the System menu's own process list, whole:
        desktop_header_qt.NicePopup, which was always able to stand by itself.)
  GPU   what the graphics processor is for here: Stacy's model (the Brain room) and Graphite's services, On, Off, Restart.
  RAM   memory in use and swapping; and the way to Machine, where this computer is described.
  TXT   the text Stacy holds: the Full chat, and what she has in view (Context).

  Log out, Exit Graphite, Restart, Shut down    at the foot of the Work menu, the first menu, where a desktop keeps them.
  Game                                           among the programs, at the foot of Programs.
  What waits for you                             was already said in Stacy's pane ("Now: ... N waiting for you").

A click on a meter opens its card upward from the band; a click anywhere else puts it away. A card reads the computer when
it opens. Nothing here is a new operation: every word on a card calls what the System menu's row or the pane's link
called before.
"""
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from . import boss_theme as t

DOORS = {'CPU': 'Graphite’s work: what runs and waits, and Stop all jobs',
         'GPU': 'Stacy’s model and Graphite’s services',
         'RAM': 'Memory, and this computer',
         'TXT': 'The conversation, and what Stacy has in view'}


class MeterCard(QFrame):
    """A meter's card: a dark plate with a name, what the meter reads now in words, and the few words that go further."""

    def __init__(self, host, title):
        super().__init__(host, Qt.Popup);self.host = host;self.setObjectName('MeterCard')
        self.setStyleSheet(
            'QFrame#MeterCard {background:%s;border:1px solid %s;} QLabel {background:transparent;color:%s;} QLabel[role="name"] {color:%s;letter-spacing:1px;} '
            'QLabel[role="quiet"] {color:%s;} '
            'QPushButton {background:transparent;color:%s;border:1px solid %s;border-radius:0;padding:5px 12px;text-align:left;} '
            'QPushButton:hover {border:1px solid %s;color:%s;} QPushButton:focus {border:1px solid %s;} QPushButton:disabled {color:%s;border:1px solid transparent;}'
            % (t.RAISED, t.LINE_MID, t.TEXT, t.TEAL_TEXT, t.FAINT, t.TEXT, t.LINE, t.READY, t.TEAL_TEXT, t.AMBER_EDGE, t.FAINT))
        self.box = QVBoxLayout(self);self.box.setContentsMargins(14, 10, 14, 12);self.box.setSpacing(6);self.words = {}
        head = QLabel(title);head.setProperty('role', 'name');self.box.addWidget(head)

    def line(self, text, quiet=False):
        label = QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(True);label.setMinimumWidth(300);label.setMaximumWidth(420)
        if quiet:label.setProperty('role', 'quiet')
        self.box.addWidget(label);return label

    def word(self, words, does, tip='', row=None, enabled=True):
        """A word that goes somewhere: the card goes first, then the thing is done."""
        button = QPushButton(words);button.setCursor(Qt.PointingHandCursor);button.setToolTip(tip);button.setEnabled(bool(enabled))
        button.clicked.connect(lambda checked=False:(self.hide(), QTimer.singleShot(0, does)))
        (row if row is not None else self.box).addWidget(button);self.words[words] = button;return button

    def row(self, label=''):
        row = QHBoxLayout();row.setSpacing(6)
        if label:row.addWidget(QLabel(label))
        self.box.addLayout(row);return row


def place_above(card, anchor, host):
    """Above the meter, centred on it, and never outside the window."""
    card.adjustSize()
    at = anchor.mapToGlobal(QPoint(anchor.width() // 2 - card.width() // 2, -card.height() - 8))
    window = host.mapToGlobal(QPoint(0, 0))
    x = max(window.x() + 8, min(at.x(), window.x() + host.width() - card.width() - 8));y = max(window.y() + 8, at.y())
    card.move(x, y)


def cpu_card(host, anchor):
    """Graphite's work on the processor: the System menu's process list, standing by itself."""
    from .desktop_header_qt import NicePopup
    card = getattr(host, '_cpu_card', None)
    if card is None:
        card = host._cpu_card = NicePopup(host, anchor);card.title.setText('PROCESSOR · GRAPHITE’S WORK')
        if getattr(card, 'game', None) is not None:card.game.hide()      # the game is among the programs now
    card.refresh();return card


def gpu_card(host, anchor):
    from .host_observations import gpu
    from .shell2 import open_destination
    card = MeterCard(host, 'GRAPHICS · STACY’S MODEL AND GRAPHITE’S SERVICES')
    busy = gpu();card.line(('The graphics processor is %d%% busy.' % busy) if busy is not None else 'This graphics driver does not report how busy it is.')
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    if face is not None and face.model.text():card.line('Stacy ' + face.model.text() + '.', quiet=True)
    card.word('Brain room', lambda:open_destination(host, 'slate'), 'Choose, swap or stop Stacy’s model, on this computer')
    life = getattr(getattr(getattr(host, 'type_bar', None), 'hatch', None), 'lifecycle', None)
    if life is not None:
        try:life.refresh()
        except Exception:  # noqa: BLE001 - the card still says what is known
            pass
        state = dict(getattr(life, 'state', {}) or {});phase = state.get('phase');busy_now = phase in ('DRAINING', 'STOPPING', 'UNAVAILABLE')
        if state.get('summary'):card.line(str(state['summary']), quiet=True)
        row = card.row('Graphite services')
        from .system_menu_qt import CHOICES, CHOICE_TIPS
        for key, word in CHOICES:
            on = not busy_now and (key != 'On' or not state.get('admission_enabled') or state.get('work_held')) and not (key == 'Off' and phase == 'OFF')
            card.word(word, lambda key=key:life.request(key), CHOICE_TIPS[key], row=row, enabled=on)
        row.addStretch(1)
        details = getattr(host, 'a_host_service', None)
        if details is not None:card.word('Service details', details.trigger, 'What each of Graphite’s services is doing')
    return card


def ram_card(host, anchor):
    from .host_observations import memory
    from .pulse_qt import gb
    card = MeterCard(host, 'MEMORY · THIS COMPUTER')
    got = memory();card.line(('%s in use of %s (%d%%).' % (gb(got['used']), gb(got['total']), got['percent'])) if got else 'Memory in use is not reported here.')
    equalizer = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'equalizer', None)
    words = getattr(equalizer, 'words', {}) if equalizer is not None else {}
    for group, name in (('RAM', 'Swap'), ('SSD', 'Disks'), ('NET', 'Network')):
        said = words.get(group)
        if said:card.line('%s: %s.' % (name, said.partition('; ')[2] if group == 'RAM' and '; ' in said else said), quiet=True)

    def machine():
        bar = getattr(getattr(host, 'settings_navigator', None), 'bar', None)
        if bar is not None and len(getattr(bar, 'buttons', ())) > 1:bar.buttons[1].click()
    card.word('Machine', machine, 'This computer, described: its processor, graphics, disks and what Graphite found installed')
    return card


def txt_card(host, anchor):
    from .host_observations import snapshot
    card = MeterCard(host, 'TEXT · WHAT STACY HOLDS')
    txt = snapshot()['txt']
    card.line(('Her context is %d%% full.' % txt['percent']) if txt.get('percent') is not None else
              'How full her context is cannot be shown yet: the model’s runtime does not report it.')
    card.word('Full chat', host.open_clip, 'The whole conversation with Stacy, with /commands and providers')
    shell = getattr(host, 'shell2', None)
    if shell is not None:card.word('What she has in view', shell.show_context_face, 'Everything about what is open or selected: what “this” means to her')
    return card


CARDS = {'CPU': cpu_card, 'GPU': gpu_card, 'RAM': ram_card, 'TXT': txt_card}


def open_card(host, anchor, key):
    """Open a meter's card above it. Returns the card."""
    maker = CARDS.get(key)
    if maker is None:return None
    card = maker(host, anchor);place_above(card, anchor, host);card.show();host._meter_card = card
    return card
