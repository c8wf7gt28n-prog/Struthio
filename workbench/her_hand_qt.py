"""Her hand on the desk: a turn the owner starts in Talk, carried out one act at a time on the window's own thread.

Kasandra's hand, first slice ("Her door on the Field"). The owner says in Talk, in his own words, "trace Rail Demo bench readings
and put Rev A beside Rev B". hand_words finds the goals; the planner (planner.py over desk_ops.py) finds the fewest acts
from the window as it is now; HerHand carries them out through her door (desk_doers.run, door 'her'), reading the window
back after each act, keeping the read as a goal's evidence when it shows the goal, and planning again whenever the window
is not what the plan predicted. Nothing is written to the owner's records: the turn lives in the session as `her_plan`.

One timer tick does at most one thing: read and plan, show the ring where the next press lands, or one act. At least
PACE_MS (300 ms) pass between two acts, so the owner can follow; a scene may lower it.

What the owner sees and keeps in hand:
  her card      in her column: the goals with their state and a "seen" word that shows the evidence; the acts, numbered,
                each next, done, offered, waits for your Go ahead, refused or stopped; Stop, Go ahead, Put my window back,
                Continue; and a closing line ("Done in 5 acts; both are shown").
  the ring      HerPointer, an overlay mouse events pass through, draws a ring where her next press lands, 200 ms before
                it; with less motion it is held still.
  the dial      at Ask first the card lists the plan and waits: Go ahead (or hand.approve) authorises the moves up to the
                next goal, matched by each act's fingerprint; a touch or a plan that changes voids it, and the new acts are
                offered again. At Do and show and Free hand a desk-only turn runs: it is shown and can be put back.
  Stop          one flag per window: Stop on the card, hand.stop, the owner's touch. A touch is a press of the mouse, a key
                or a touch whose receiver is a QWindow (her own presses go to widgets, never to a window), unless it lands
                on her card; the wheel and the pointer's hover do not stop her, so the owner can scroll to read the card.
                She stops between presses, never halfway through a click (desk_doers.check_stop).
  put back      a plan back to the window as the turn found it (planner.put_back), navigation only, through her door.
  the hologram  state_changed says idle, thinking, acting, waits, stopped or finished; her picture shows them as at work,
                waits for you, stopped and done (kasandra_art).

Words she cannot settle alone (0.8.6 S7): her dictionary reads them over the Field's sheets, a phrase the owner kept first
(read as he kept it, no question, model calls: 0). Otherwise the licensed options make one brief (brief.py). With a model,
the brief is its one GOAL question through the turn contract (turns.ask, its deadline and record), and the answer is used
only when answer_check takes or trims it; her card then says "The model's pick, checked against your words · model calls:
1", with a fold of what was asked. With no model, a late answer (past the deadline, the top option is taken by default only
when it moves the window and the dial lets her) or a refused one, the same options are the owner's buttons, and his press
is his own approval. After either, she offers once to keep his words (phrases.py): only his press keeps them.

Budgets for a turn: 24 acts, 120 s not counting the owner's own time, 6 plans, 2 surprises in a row. A repeated move from
the same window stops the turn, with words. Changes are not hers in this slice: her door refuses them.
"""
import json
import threading
import time
import uuid

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QWindow
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import brief, desk_ops, goals as G, hand_words, phrases, planner, stacy_hand, turns
from .assistant_identity import named

PACE_MS = 300               # between two acts of hers, at least
RING_MS = 200               # her ring shows where the next press lands, this long before it
POLL_MS = 500               # a model job is polled this often
MOST_ACTS = 24
MOST_SECONDS = 120.0
MOST_PLANS = 6
MOST_SURPRISES = 2
MODEL_SECONDS = 60.0
PLAN_KEPT = 64 * 1024       # her_plan in the session, at most
STATES = ('idle', 'thinking', 'acting', 'waits', 'stopped', 'finished')
# her hand's state -> the hologram's state (hologram.STATE_LOOK): what her picture shows
HOLOGRAM = {'thinking': 'working', 'acting': 'working', 'waits': 'awaiting_approval', 'stopped': 'blocked', 'finished': 'completed'}
ROW_WORDS = {'next': 'next', 'done': 'done', 'offered': 'offered', 'waits': 'waits for your Go ahead', 'refused': 'refused', 'stopped': 'stopped', 'planned': ''}


class Turn:
    """One request of the owner's, from his words to the closing line."""

    def __init__(self, text, goal_list, word=''):
        self.id = uuid.uuid4().hex[:12];self.text = str(text);self.word = word or str(text)
        self.goals = list(goal_list);self.asked = True
        self.state = 'thinking';self.why = '';self.closing = ''
        self.started = time.monotonic();self.owner_time = 0.0;self.waiting_since = None
        self.count = 0;self.done = 0;self.offers = 0;self.plans = [];self.surprises = 0
        self.envelopes = [];self.rows = []          # the card's act rows: [{'step': planner.Step, 'state': ...}]
        self.plan = None;self.pending = None;self.pending_state = None
        self.authorised = [];self.offered = []      # fingerprints the owner's Go ahead authorised; the acts last offered
        self.done_keys = set();self.refused = {};self.dropped = set()
        self.snapshot = None;self.snapshot_digest = '';self.offer_digest = ''
        self.trail_before = 0;self.desk_trail_before = 0;self.trail_added = 0;self.desk_trail_added = 0
        self.model = None;self.putting_back = False;self.stopped_after = None;self.world = None

    def seconds(self):
        """Her own time in this turn: the owner's time (waiting for his Go ahead) is not counted."""
        waiting = (time.monotonic() - self.waiting_since) if self.waiting_since is not None else 0.0
        return time.monotonic() - self.started - self.owner_time - waiting


# -- the ring where her next press lands -----------------------------------------------------------------------------------------

class HerPointer(QWidget):
    """An overlay over the whole window that every mouse event passes through: a ring where her next press lands."""

    def __init__(self, host):
        super().__init__(host);self.host = host;self.at = None;self.since = 0.0;self.still = False
        self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setAttribute(Qt.WA_NoSystemBackground);self.setFocusPolicy(Qt.NoFocus)
        self.setObjectName('HerPointer')
        self._timer = QTimer(self);self._timer.setInterval(40);self._timer.timeout.connect(self.update)
        self.hide()

    def show_at(self, global_point, still=False):
        if global_point is None:self.clear();return
        self.setGeometry(self.host.rect());self.at = self.mapFromGlobal(global_point);self.since = time.monotonic();self.still = bool(still)
        self.raise_();self.show();self.update()
        if not self.still:self._timer.start()

    def clear(self):
        self._timer.stop();self.at = None;self.hide()

    def paintEvent(self, event):
        if self.at is None:return
        from . import boss_theme as bt
        grow = 0.0 if self.still else min(1.0, (time.monotonic() - self.since) / (RING_MS / 1000.0))
        radius = 9.0 + 5.0 * (1.0 - grow)          # it closes in on the place as the press nears; still, it is held at 9
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        colour = QColor(getattr(bt, 'TEAL', '#33cccc'));p.setPen(QPen(colour, 2.0));p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(self.at), radius, radius);p.end()


# -- the owner's touch ------------------------------------------------------------------------------------------------------------

class _Touch(QObject):
    """Installed on the application only while a turn runs: a press whose receiver is one of the window system's windows is
    the owner's (her own presses are sent to widgets)."""
    KINDS = (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.TouchBegin)

    def __init__(self, hand):
        super().__init__();self.hand = hand;self.trips = 0

    def eventFilter(self, watched, event):
        try:
            if event.type() in self.KINDS and isinstance(watched, QWindow):
                if not self.hand.on_card(event):
                    self.trips += 1;self.hand.touched()
        except RuntimeError:  # the window is closing
            pass
        return False


# -- her card -----------------------------------------------------------------------------------------------------------------------

class HandCard(QFrame):
    """Her card for one turn, in her column. Its words are templates with the sheets' titles put in; it names no key and no
    font (it draws with the appearance's faces), calls the line language "a line", and the list of programs "Apps"."""

    def __init__(self, hand, turn):
        super().__init__();self.hand = hand;self.turn = turn;self.setObjectName('HerHandCard')
        self.box = QVBoxLayout(self);self.box.setContentsMargins(10, 9, 8, 9);self.box.setSpacing(6)
        self.head = self._label(named('My hand on the desk, for your words: “%s”.') % hand_words.plain(turn.text)[:200])
        self.goal_box = QVBoxLayout();self.goal_box.setSpacing(2);self.box.addLayout(self.goal_box)
        self.act_box = QVBoxLayout();self.act_box.setSpacing(2);self.box.addLayout(self.act_box)
        self.note = self._label('');self.note.hide()
        from .shell2 import button
        row = QHBoxLayout();row.setSpacing(8)
        self.go = button('Go ahead', 'stac', 'Let my hand make the moves listed as offered; touching the window stops it again')
        self.stop_button = button('Stop', 'quiet', 'Stop my hand before its next press')
        self.again = button('Continue', 'quiet', 'Let my hand go on from where the window is now')
        self.back = button('Put my window back', 'quiet', 'Back to what was in front, the selection and what was over the work when I started')
        self.undo = button('Undo my changes', 'quiet', 'Take back every change my hand made for these words, the latest first')      # 1.0 F1: one Undo
        self.go.setObjectName('HerHandGo');self.stop_button.setObjectName('HerHandStop');self.again.setObjectName('HerHandContinue');self.back.setObjectName('HerHandBack')
        self.undo.setObjectName('HerHandUndo')
        self.go.clicked.connect(lambda: hand.go_ahead(by_owner=True));self.stop_button.clicked.connect(lambda: hand.stop_for_good())      # 1.0 F1
        self.again.clicked.connect(hand.carry_on);self.back.clicked.connect(lambda: hand.put_back());self.undo.clicked.connect(lambda: hand.undo_changes())
        for b in (self.go, self.stop_button, self.again, self.back, self.undo):row.addWidget(b)
        row.addStretch(1);self.box.addLayout(row)
        self.closing = self._label('');self.closing.hide()
        self.refresh()

    def _label(self, text):
        label = QLabel(text);label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse);self.box.addWidget(label);return label

    def refresh(self):
        t = self.turn
        for box in (self.goal_box, self.act_box):
            while box.count():
                item = box.takeAt(0);w = item.widget()
                if w is not None:w.deleteLater()
        from .shell2 import sentence
        for g in t.goals:
            words = '%s  %s · %s' % (g.id, g.statement, g.words())
            if g.evidence and not g.persist:
                label = sentence('%s · {seen}' % words.replace('{', '(').replace('}', ')'), {'seen': ('seen', lambda g=g: self.show_evidence(g))})
            else:
                label = QLabel(words)
            label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.goal_box.addWidget(label)
        for n, row in enumerate(t.rows, 1):
            word = ROW_WORDS.get(row['state'], '')
            label = QLabel('%d  %s%s' % (n, row['step'].words(), (' · ' + word) if word else ''))
            label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.act_box.addWidget(label)
        state = t.state
        self.go.setVisible(state == 'waits' and bool(t.offered) and not t.authorised)
        paused = state == 'stopped' and not t.putting_back and t.stopped_after is not None and t.closing == ''      # 1.0 F1: stopped by you, waiting for your word
        self.stop_button.setVisible(state in ('thinking', 'acting') or paused)
        self.stop_button.setToolTip('Stop for good: your window goes back as it was (what is in front, the selection, the tabs, the scroll and your keyboard)'
                                    if paused else 'Stop my hand before its next press; then your window goes back as it was')
        self.again.setVisible(state == 'stopped' and not t.putting_back)
        self.back.setVisible(state in ('stopped', 'finished') and not paused and self.hand.snapshot is not None and t.done > 0)
        self.undo.setVisible(state in ('stopped', 'finished') and not t.putting_back and bool(self.hand.changes()))
        if t.why:self.note.setText(t.why);self.note.show()
        else:self.note.hide()
        if t.closing:self.closing.setText(t.closing);self.closing.show()

    def show_evidence(self, goal):
        ev = goal.evidence or {}
        said = '; '.join('%s is %s' % (p, json.dumps(v, ensure_ascii=False)) for p, v in (ev.get('paths') or {}).items())
        self.hand.say('%s: seen after act %d. The window said: %s.' % (goal.id, int(ev.get('act') or 0), said or 'nothing more'))


# -- the hand -------------------------------------------------------------------------------------------------------------------------

class HerHand(QObject):
    """Her hand on one window. host.her_hand."""
    state_changed = Signal(str)

    def __init__(self, host):
        super().__init__(host);self.host = host;self.turn = None;self.snapshot = None;self.snapshot_world = None
        self.stop_flag = False;self.pace_ms = PACE_MS;self.card = None;self.state = 'idle'
        self.timer = QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.tick)
        self.pointer = HerPointer(host);self.filter = _Touch(self);self._filtering = False
        self.state_changed.connect(self._hologram)
        self._full_stop = False;self._door_snap = None;self._last_back = None      # 1.0 F1: your Stop puts the window back; the window as it was

    # -- what the door asks ----------------------------------------------------------------------------------------------
    @property
    def turn_id(self):
        return self.turn.id if self.turn is not None else None

    def active(self):
        return self.turn is not None and self.turn.state in ('thinking', 'acting', 'waits')

    def in_turn(self, turn):
        """Her door runs only inside the turn she is in now, and only while it moves (or puts the window back)."""
        return turn is not None and turn is self.turn and (turn.state in ('thinking', 'acting') or turn.putting_back)

    def authorised(self, turn, name, args):
        """At Ask first: whether the owner's Go ahead authorised exactly this act, next in its order."""
        if turn is None or turn is not self.turn:return False
        if turn.putting_back:return True          # "Put my window back" is the owner's own word for those moves
        return bool(turn.authorised) and turn.authorised[0] == desk_ops.fingerprint(name, args)

    def offer_card(self):
        """Her card while it offers moves that wait for the owner's Go ahead, else None."""
        t = self.turn
        if t is not None and t.state == 'waits' and t.offered and not t.authorised and self.card is not None:return self.card
        return None

    # -- the state, and her picture ------------------------------------------------------------------------------------------
    def set_state(self, state, why=None):
        t = self.turn
        if t is not None:
            if t.state == 'waits' and state != 'waits' and t.waiting_since is not None:
                t.owner_time += time.monotonic() - t.waiting_since;t.waiting_since = None
            if state == 'waits' and t.waiting_since is None:t.waiting_since = time.monotonic()
            t.state = state
            if why is not None:t.why = why
        self.state = state
        self._filter(state in ('thinking', 'acting', 'waits'))
        self.keep()
        if self.card is not None:
            try:self.card.refresh()
            except RuntimeError:  # the card left with Talk's earlier exchanges
                self.card = None
        self.state_changed.emit(state)
        if state == 'stopped' and self.card is not None:QTimer.singleShot(0, self._door_buttons_seen)      # 1.0 F1: Continue and Stop in sight

    def _hologram(self, state):
        """Her picture follows her hand: thinking and acting are at work, waits waits for you, stopped and finished end."""
        from . import kasandra_art
        try:self.host._her_hand_state = state
        except Exception:  # noqa: BLE001 - a host that takes no attributes shows nothing
            return
        if state == 'finished':kasandra_art.note_outcome(self.host, True)
        elif state == 'stopped':kasandra_art.note_outcome(self.host, False)
        else:
            if state in ('thinking', 'acting', 'waits'):      # her hand moves again: an earlier stop or finish is over
                try:self.host._art_outcome = (None, 0.0)
                except Exception:  # noqa: BLE001
                    pass
            kasandra_art.nudge(self.host)

    def _filter(self, on):
        app = QApplication.instance()
        if app is None or on == self._filtering:return
        if on:app.installEventFilter(self.filter)
        else:app.removeEventFilter(self.filter)
        self._filtering = on

    def keep(self):
        """The turn as session state `her_plan` (never the owner's records), at most 64 KiB."""
        try:
            state = self.host.session.state
            value = self.record() if self.turn is not None else None
            text = json.dumps(value, ensure_ascii=False, default=str)
            if len(text.encode('utf-8')) > PLAN_KEPT:value = {k: value[k] for k in ('id', 'text', 'state', 'acts', 'why', 'closing')}
            state['her_plan'] = value
        except Exception:  # noqa: BLE001 - a session that cannot hold it is not worth stopping her hand
            pass

    def record(self):
        """The turn as the scenes read it (`turn.*`)."""
        t = self.turn
        if t is None:return {'state': 'idle'}
        changed = sorted({c for e in t.envelopes for c in (e.get('changed') or [])})
        kept = [g for g in t.goals if not g.persist]
        return {'id': t.id, 'text': t.text, 'state': t.state, 'why': t.why, 'closing': t.closing, 'acts': t.done, 'attempts': t.count,
                'offers': t.offers, 'plans': len(t.plans), 'plan_ms': [p['ms'] for p in t.plans], 'plan_how': [p['how'] for p in t.plans],
                'goals': [g.as_record() for g in t.goals], 'goals_open': sum(1 for g in kept if g.state != G.SEEN),
                'all_shown': bool(kept) and all(g.state == G.SEEN for g in kept),
                'doors': sorted({e.get('door') for e in t.envelopes}), 'changed': changed,
                'envelopes': [{k: e.get(k) for k in ('act', 'door', 'ok', 'by', 'changed', 'seconds')} | {'code': (e.get('error') or {}).get('code')} for e in t.envelopes],
                'trail_added': t.trail_added, 'desk_trail_added': t.desk_trail_added, 'stopped_after': t.stopped_after,
                'journal_stopped': sum(1 for e in t.envelopes if (e.get('error') or {}).get('code') == 'STOPPED'),
                'journal_offered': sum(1 for e in t.envelopes if (e.get('error') or {}).get('code') == 'OFFERED'),
                'desk_unchanged': bool(t.offer_digest) and t.offer_digest == t.snapshot_digest, 'seconds': round(t.seconds(), 3),
                # 0.8.7 W7: a turn in flight holds its thread and its holder; neither is a record (the session could not be saved)
                'model': {k: v for k, v in t.model.items() if k not in ('thread', 'holder')} if isinstance(t.model, dict) else t.model,
                'rows': [{'act': r['step'].act, 'args': r['step'].args, 'state': r['state']} for r in t.rows]}

    # -- reading the window ---------------------------------------------------------------------------------------------------
    def read(self):
        """read.desk, and the state and sheets a plan needs. read.desk lists at most 60 sheets; a plan may name any sheet
        of the desk, so her hand takes them all from the Field itself (and every sheet in sight)."""
        from dataclasses import replace
        from .desk_doers import field_objects, in_sight, read_desk
        desk = read_desk(self.host, 'all')
        state, world = desk_ops.abstract(desk)
        page = getattr(self.host, 'field_page', None)
        if page is not None and state.face == 'work':
            sheets = [desk_ops.Sheet(o['title'], o['kind'], o['sibling'], o['older']) for o in field_objects(page, page.view, None)]
            world = desk_ops.World(tuple(sheets));state = replace(state, in_sight=frozenset(in_sight(page.view, None)))
        return desk, state, world

    def world(self):
        """The Field's sheets: as read.desk lists them, else read from the records (a read; the window does not move)."""
        _, state, world = self.read()
        if world.sheets and state.face == 'work':return world      # the Apps and network faces list other things
        try:
            from .engineering_kernel import operator
            from .field_page import read_field, revision_sibling
            kernel = self.host.ledger_bridge.kernel
            field, _ = read_field(kernel, operator(), title='')

            class _View:
                pass
            view = _View();view.field = field;sheets = []
            for obj in field.objects:
                pair = revision_sibling(view, obj)
                sibling = None;older = False
                if pair:(_, a), (_, b) = pair;sibling = (b if a.id == obj.id else a).title;older = a.id == obj.id
                sheets.append(desk_ops.Sheet(obj.title, obj.kind, sibling, older))
            return desk_ops.World(tuple(sheets))
        except Exception:  # noqa: BLE001 - no records to read: no sheets to name
            return world

    def say(self, text):
        face = getattr(getattr(self.host, 'shell2', None), 'face', None)
        return face.say(text) if face is not None else None

    # -- a turn ---------------------------------------------------------------------------------------------------------------------
    def start(self, text, pairs, word='', origin='OWNER'):
        """A turn for these goals ([(template, params)] in the order said): the standing tidy goal ends it."""
        if self.active():self.stop('a new request');self.turn.state = 'stopped'
        goal_list = hand_words.goals_of([p for p in pairs if p[0] != 'tidy'], origin=origin)
        goal_list.append(G.tidy(len(goal_list) + 1))
        place = stacy_hand.level(self.host)
        for g in goal_list:      # a desk-only turn runs without a word of agreement at Do and show and Free hand (it can be put back)
            g.agreed = place in ('show', 'free');g.agreed_by = 'shown' if g.agreed else ''
        t = Turn(text, goal_list, word)
        t.basis = stacy_hand.basis_of(origin)       # 0.8.7 B1: goals the model picked (HER) carry basis model_pick to her door
        desk, state, world = self.read()
        t.world = world if (world.sheets and state.face == 'work') else self.world()
        t.snapshot = state;t.snapshot_digest = G.digest(desk)
        state_now = getattr(self.host.session, 'state', {})
        t.trail_before = len(state_now.get(stacy_hand.TRAIL) or []);t.desk_trail_before = len(state_now.get(stacy_hand.DESK_TRAIL) or [])
        self.turn = t;self.snapshot = state;self.snapshot_world = t.world;self.stop_flag = False
        self._door_begin(t)      # 1.0 F1
        self.card = HandCard(self, t)
        face = getattr(getattr(self.host, 'shell2', None), 'face', None)
        if face is not None:face.add(self.card)
        self.set_state('thinking')
        self.timer.start(0)
        return t

    def touched(self):
        """The owner's own press on the window: she stops before her next press; an offer is void."""
        t = self.turn
        if t is None:return
        if t.state == 'waits':
            if t.offered:
                t.offered = [];t.authorised = []
                for row in t.rows:
                    if row['state'] in ('offered', 'waits'):row['state'] = 'planned'
                self.set_state('waits', 'You touched the window, so what I offered is void; I read it again and offer what fits it now.')
                self.set_state('thinking');self.timer.start(self.pace_ms)
            return
        if t.state in ('thinking', 'acting'):self.stop('touch')

    def stop(self, why='owner'):
        """Stop before the next press (Stop on her card, hand.stop, Master Stop, the owner's touch)."""
        self.stop_flag = True
        t = self.turn
        if t is None:return
        self._door_stop(why)      # 1.0 F1: the door hears it (one stop rule): paused, or stopped by HALT
        self.pointer.clear()
        if t.state == 'waits':
            t.offered = [];t.authorised = [];t.stopped_after = t.done
            self.set_state('stopped', 'Stopped: nothing was done after your word.')
        # while she moves, the next press refuses (STOPPED) and the tick pauses the turn there

    def carry_on(self):
        """Continue from where the window is now."""
        t = self.turn
        if t is None or t.state != 'stopped':return
        from . import hand_door      # 1.0 F1: your Continue goes through the door (it calls this back, the door driving again)
        if hand_door.DOOR.hand == 'desk' and hand_door.DOOR.paused('desk'):
            hand_door.DOOR.carry_on('desk');return
        self.stop_flag = False;t.surprises = 0;t.pending = None
        self.set_state('thinking', '');self.timer.start(self.pace_ms)

    def go_ahead(self, by_owner=True):
        """The owner's Go ahead: exactly the acts offered, in their order."""
        t = self.turn
        if t is None or t.state != 'waits' or not t.offered:return 'nothing waits for your Go ahead.'
        t.authorised = list(t.offered);t.offered = [];self.stop_flag = False
        for row in t.rows:
            if row['state'] in ('offered', 'waits'):row['state'] = 'planned'
        self.set_state('thinking', '');self.timer.start(self.pace_ms)
        return 'my hand makes the moves it offered.'

    def finish(self, words=''):
        t = self.turn
        t.closing = words or G.closing(t.goals, t.done)
        self.pointer.clear();self.set_state('finished', '')
        self._door_finish(t.closing)      # 1.0 F1: your keyboard and its cursor given back; what she was asked to show stays

    def halt(self, why):
        """The turn stops with words (a budget, a repeat, a plan that cannot be made)."""
        t = self.turn
        t.stopped_after = t.done;self.pointer.clear()
        self.set_state('stopped', why)
        self._door_finish(why)      # 1.0 F1: she stopped herself: what was yours is given back

    def tick(self):
        t = self.turn
        if t is None or t.state not in ('thinking', 'acting'):return
        try:
            if t.pending is not None:self._act(t)
            else:self._think(t)
        except Exception as exc:  # noqa: BLE001 - her hand never raises into the window: it stops, with words
            self.halt('My hand stopped: %s.' % (str(exc)[:200] or type(exc).__name__))

    def _think(self, t):
        if t.done >= MOST_ACTS:return self.halt('I stopped at %d acts, my most for one request.' % MOST_ACTS)
        if t.seconds() > MOST_SECONDS:return self.halt('I stopped after two minutes of my own time on this request.')
        desk, state, world = self.read()
        world = world if (world.sheets and state.face == 'work') else t.world
        G.observe(t.goals, desk, t.done)
        done, missing = G.finished(t.goals, desk)
        if done:
            self._count_trails();return self.finish()
        open_list = G.open_goals(t.goals)
        fits = t.plan is not None and self._fits(t.plan, state, world, open_list)
        if len(t.plans) >= MOST_PLANS and not fits:
            return self.halt('I stopped: I had to plan this %d times, my most for one request.' % MOST_PLANS)
        if not fits:
            p = planner.plan(state, world, open_list, costs=desk_ops.costs(), avoid=tuple(t.dropped))
            t.plans.append({'ms': round(p.ms, 3), 'how': p.how, 'state': p.state, 'acts': len(p.steps), 'expansions': p.expansions})
            if p.state == 'HOLDS':return self.finish()
            if p.state != 'FOUND':return self.halt(p.words or planner.NONE_WORDS)
            if t.authorised:
                # A repair that only leaves out moves the owner already allowed (the whole desk came into sight, so the zoom
                # is not needed) keeps his word for the rest; a repair that changes the acts voids it, and the new acts are
                # offered again.
                end = p.segments[0] if p.segments else len(p.steps)
                wanted = [s.fingerprint() for s in p.steps[:end]];left = iter(t.authorised)
                t.authorised = wanted if all(any(fp == a for a in left) for fp in wanted) else []
            t.plan = p
            done_rows = [r for r in t.rows if r['state'] in ('done', 'refused')]
            t.rows = done_rows + [{'step': s, 'state': 'planned'} for s in p.steps]
        step = t.plan.steps[0]
        key = (state.key(), step.fingerprint())
        if key in t.done_keys:return self.halt('I was about to do “%s” again from the same place, so I stopped rather than go round.' % step.words().rstrip('.'))
        if stacy_hand.level(self.host) == 'ask' and not t.authorised and not t.putting_back:
            return self._offer(t, desk)
        nxt = next(r for r in t.rows if r['state'] == 'planned')
        nxt['state'] = 'next'
        t.pending = step;t.pending_state = state;t.pending_world = world
        self.set_state('acting')
        self.pointer.show_at(self.press_point(step), still=self.still())
        self.timer.start(RING_MS)

    def _fits(self, p, state, world, open_list):
        """Whether the rest of the plan still works from the window as read now: each act's precondition holds in turn
        and the goals hold at its end. An effect the plan did not predict is absorbed this way; one that breaks it makes
        a new plan."""
        if not p.steps:return False
        s = state
        for step in p.steps:
            op = desk_ops.OPS.get(step.act)
            if op is None or not op.pre(s, world, step.args):return False
            s = op.apply(s, world, step.args)
        return planner.satisfied(open_list, s)

    def _offer(self, t, desk):
        """At Ask first: the moves up to the next goal are offered on her card; the first is put to her door, which says
        OFFERED in the journal and does not run it. The window is not touched."""
        from .desk_doers import run
        end = t.plan.segments[0] if t.plan.segments else len(t.plan.steps)
        segment = t.plan.steps[:end]
        t.offered = [s.fingerprint() for s in segment];t.offers += 1
        rows = [r for r in t.rows if r['state'] == 'planned'][:len(segment)]
        for r in rows:r['state'] = 'offered'
        self.set_state('acting')      # her door takes the act inside the turn, and offers it
        envelope = run(self.host, segment[0].act, segment[0].args, door='her', turn=t, word=t.word)
        t.envelopes.append(envelope)
        t.offer_digest = G.digest(self.read()[0])
        self.set_state('waits', named('My hand is at Ask first: Go ahead lets me make the %d move%s offered; touching the window voids it.') % (len(segment), '' if len(segment) == 1 else 's'))

    def _act(self, t):
        from .desk_doers import run, settle
        step = t.pending;t.pending = None;self.pointer.clear()
        t.count += 1
        envelope = run(self.host, step.act, step.args, door='her', turn=t, word=t.word)
        t.envelopes.append(envelope)
        code = (envelope.get('error') or {}).get('code')
        row = next((r for r in t.rows if r['state'] == 'next'), None)
        stacy_hand.record_desk(self.host.session.state, step.act, step.args, envelope.get('words') or '', 'done' if envelope.get('ok') else (code or 'refused').lower(), t.id)
        if code == 'STOPPED':
            if row is not None:row['state'] = 'stopped'
            t.stopped_after = t.done;t.plan = None
            self._count_trails()
            self.set_state('stopped', named('You took the window back, so my hand stopped after %d act%s. Continue goes on from here; Stop puts your window back as it was.') % (t.done, '' if t.done == 1 else 's'))
            if self._full_stop:      # 1.0 F1: your Stop on her card: once she stopped between presses, the window goes back
                self._full_stop = False;QTimer.singleShot(0, self.put_back)
            return
        if t.authorised and t.authorised[0] == step.fingerprint():t.authorised.pop(0)
        if not envelope.get('ok'):
            if row is not None:row['state'] = 'refused'
            fp = step.fingerprint();t.refused[fp] = t.refused.get(fp, 0) + 1
            if t.refused[fp] >= 2:t.dropped.add(fp)       # refused twice in a turn: dropped for the rest of it
            t.plan = None                                  # a refusal is not a no-op: read again, and plan from what is there
        else:
            if row is not None:row['state'] = 'done'
            t.done += 1;t.done_keys.add((t.pending_state.key(), step.fingerprint()))
            settle(self.host, 20, 2)
            _, now, _ = self.read()
            predicted = desk_ops.OPS[step.act].apply(t.pending_state, t.pending_world, step.args) if step.act in desk_ops.OPS else now
            if desk_ops.agrees(step.act, predicted, now):
                t.surprises += 1;t.plan = None
                if t.surprises > MOST_SURPRISES:return self.halt('The window did not answer my acts as I expected, %d times in a row, so I stopped.' % t.surprises)
            else:
                t.surprises = 0
                t.plan.steps = t.plan.steps[1:];t.plan.segments = [n - 1 for n in t.plan.segments if n > 1]
        self._count_trails()
        self.set_state('thinking')
        self.timer.start(self.pace_ms)

    def _count_trails(self):
        t = self.turn;state = getattr(self.host.session, 'state', {})
        t.trail_added = max(0, len(state.get(stacy_hand.TRAIL) or []) - t.trail_before)
        t.desk_trail_added = max(0, len(state.get(stacy_hand.DESK_TRAIL) or []) - t.desk_trail_before)

    # -- putting the window back -----------------------------------------------------------------------------------------------
    def put_back(self):
        """Back to the window as the turn found it. 1.0 F1: through the door (hand_door) while her hand drives or is paused: your
        Stop; else at once (Put my window back after she finished)."""
        from . import hand_door
        door = hand_door.DOOR
        if self.turn is not None and door.hand == 'desk' and door.state in ('driving', 'paused'):
            self._last_back = None
            out = door.stop()
            if self._last_back is not None:return self._last_back
            t = self.turn;t.closing = out.get('words') or ''
            if self.card is not None:
                try:self.card.refresh()
                except RuntimeError:self.card = None
            return {'back': False, 'acts': 0, 'words': t.closing}
        return self._put_back_now()

    def _put_back_now(self):
        """Back to the window as the turn found it: a plan of navigation, run through her door now (at most 12 moves); then
        (1.0 F1) the tabs, the lists' selection, the scroll, the Field's size and your keyboard (hand_door_qt), read back."""
        from .desk_doers import run, settle
        t = self.turn;snap = self.snapshot
        if t is None or snap is None:return {'back': False, 'words': 'There is nothing to put back.'}
        self.timer.stop();self.pointer.clear()
        self.stop_flag = False;t.putting_back = True;t.pending = None
        self.set_state('acting', '')
        moved = 0;words = ''
        try:
            for _ in range(planner.BUDGET.depth):
                if self.stop_flag:words = 'You touched the window again, so I stopped putting it back.';break
                desk, state, world = self.read()
                world = world if (world.sheets and state.face == 'work') else (self.snapshot_world or t.world)
                if planner.back_to(state, snap) and not state.popups:break
                p = planner.put_back(state, world, snap)
                if p.state != 'FOUND' or not p.steps:break
                step = p.steps[0]
                self.pointer.show_at(self.press_point(step), still=True);settle(self.host, 20, 2);self.pointer.clear()
                envelope = run(self.host, step.act, step.args, door='her', turn=t, word='put my window back')
                t.envelopes.append(envelope);t.count += 1
                stacy_hand.record_desk(self.host.session.state, step.act, step.args, envelope.get('words') or '', 'done' if envelope.get('ok') else 'refused', t.id)
                if not envelope.get('ok'):words = envelope.get('words') or '';break
                moved += 1;settle(self.host, 20, 2)
        finally:
            t.putting_back = False
        qt = self._door_qt_restore()      # 1.0 F1: what a person puts back by hand: tabs, lists, scroll, the Field's size, the keyboard
        desk, state, _ = self.read()
        back = planner.back_to(state, snap)
        from . import hand_door_qt
        more = hand_door_qt.said(qt) if qt else ''
        whole = back and (qt is None or qt.get('back') is not False)
        said = ('The window is back as it was: %s%s.' % (self._where(snap), ('; ' + more) if more else '')) if whole else \
            ('I could not put it all back: %s' % (words or more or 'the window is not as it was'))
        t.closing = said;self._count_trails()
        self.set_state('finished' if back else 'stopped', '' if back else said)
        out = {'back': whole, 'acts': moved, 'words': said, 'surface': state.surface, 'selected': state.sel,
               'over': list(state.over) if state.over else None, 'snapshot': {'surface': snap.surface, 'selected': snap.sel, 'over': list(snap.over) if snap.over else None},
               'door_parts': dict((qt or {}).get('parts') or {}, desk={'back': back, 'words': self._where(snap) if back else (words or 'not as it was')})}
        self._last_back = out
        return out

    # -- 1.0 F1: the door (hand_door): one stop rule, the window as it was, your changes with one Undo ------------------------------
    def _door_begin(self, t):
        """Her hand takes Graphite's window: what is yours in it now is kept (hand_door_qt), and the door knows how to put it
        back and how to go on. Your new request settles an earlier pause as it stands."""
        from . import hand_door, hand_door_qt
        try:
            self._door_snap = hand_door_qt.snapshot(self.host)
        except Exception:  # noqa: BLE001 - a window that cannot be read is driven all the same; it is said not put back
            self._door_snap = None
        hand_door.DOOR.forget()
        kernel = getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)
        if kernel is not None:hand_door._KERNEL['kernel'] = kernel      # HALT's hold is read through it: nothing is put back while HALT holds
        try:hand_door.DOOR.begin('desk', t.text, snapshot=self._door_snap or {'kind': 'desk'}, restore=self._door_restore, carry=self.carry_on,
                                 program="Graphite's window", title=t.text)
        except hand_door.Paused:
            pass

    def _door_stop(self, why):
        from . import hand_door
        door = hand_door.DOOR
        if door.hand != 'desk':return
        if why == 'HALT':door.halted('desk')
        elif why in ('a new request', 'the scene ended'):door.leave('desk');door.forget()
        else:door.touched('desk', {'touch': 'a press of yours on the window', 'card': 'your Stop', 'owner': 'your Stop',
                                   'Master Stop': 'Master Stop'}.get(why, str(why)[:60]))

    def _door_finish(self, words):
        from . import hand_door
        if hand_door.DOOR.driving('desk'):
            try:hand_door.DOOR.finish(words)
            except Exception:  # noqa: BLE001 - giving back the keyboard never takes the window down
                pass

    def _door_restore(self, snap, parts):
        """The door's put back for Graphite's window: your Stop (every part) runs the whole put back; her own finish gives back
        your keyboard and its cursor."""
        from . import hand_door_qt
        if 'tabs' in parts or 'scroll' in parts:
            out = self._put_back_now()
            return {'back': out['back'], 'parts': out.get('door_parts') or {}, 'words': out['words']}
        got = hand_door_qt.restore(self.host, snap, hand_door_qt.FOCUS_PARTS)
        return {'back': got.get('back'), 'parts': got.get('parts') or {}, 'words': hand_door_qt.said(got)}

    def _door_qt_restore(self):
        from . import hand_door_qt
        if not self._door_snap:return None
        try:return hand_door_qt.restore(self.host, self._door_snap, ('tabs', 'lists', 'scroll', 'zoom', 'focus'), keep=(self.card,))
        except Exception as exc:  # noqa: BLE001
            return {'back': False, 'parts': {'window': {'back': False, 'words': str(exc)[:120]}}}

    def _door_buttons_seen(self):
        """Her card's Continue and Stop brought into sight in the exchange while she waits for your word."""
        face = getattr(getattr(self.host, 'shell2', None), 'face', None);card = self.card
        if face is None or card is None or getattr(face, 'scroll', None) is None:return
        try:
            shown = card.again if card.again.isVisibleTo(card) else card.stop_button
            face.scroll.ensureWidgetVisible(shown)
        except (AttributeError, RuntimeError):  # the card left with Talk's earlier exchanges
            pass

    def stop_for_good(self):
        """Your Stop on her card: she stops for good, and the window goes back as it was when she began (while she moves, once
        she has stopped between two presses)."""
        t = self.turn
        if t is None:return
        if t.state in ('thinking', 'acting'):
            self._full_stop = True;self.stop('card');return
        if t.state == 'waits':self.stop('card')
        if t.state in ('stopped', 'waits'):QTimer.singleShot(0, self.put_back)

    def changes(self):
        """Her changes in this turn that can be taken back, the latest first."""
        from . import hand_door
        t = self.turn
        if t is None:return []
        self._count_trails()
        return hand_door.changes_of(stacy_hand.trail(getattr(self.host.session, 'state', {}))[:t.trail_added])

    def undo_changes(self):
        """One Undo for the turn: every change of hers in it that can be taken back, the latest first, each by its own guarded
        Undo line (an Undo that no longer fits, because the thing changed since, is refused and said)."""
        from . import hand_door
        from .desk_doers import settle
        entries = self.changes();back = 0;left = 0;said = []
        for entry in entries:
            try:card = self.host.shell2.face.undo_entry(entry);settle(self.host, 20, 2)
            except Exception as exc:  # noqa: BLE001
                left += 1;said.append(str(exc)[:80]);continue
            now = next((e for e in stacy_hand.trail(self.host.session.state) if e.get('at') == entry.get('at') and e.get('line') == entry.get('line')), entry)
            if now.get('state') == 'undone':back += 1
            else:
                left += 1;said.append(getattr(getattr(card, 'text', None), 'text', lambda: '')().replace('\u200b', '')[:80])
        words = hand_door.undo_words(back, left, said)
        if self.turn is not None:
            self.turn.closing = words
            if self.card is not None:
                try:self.card.refresh()
                except RuntimeError:self.card = None
        return {'undone': back, 'left': left, 'words': words}

    def _where(self, snap):
        if snap.surface != 'field':return {'home': 'Today in front', 'workspace': 'your work in front'}.get(snap.surface, 'as it was')
        return 'the Field in front' + (', “%s” selected' % snap.sel if snap.sel else '') + (', nothing over the work' if not snap.over else '')

    # -- the GOAL turn: which goals did the owner mean (0.8.6 S7: the brief, the checker and the buttons) ------------------------
    def _kernel(self):
        from .engine import engineering
        from .engineering_kernel import operator
        return engineering(self.host.root), operator()

    def _kept(self, world):
        """The owner's kept phrases, pointed at the current revision where they follow it ([] when they cannot be read)."""
        try:
            kernel, p = self._kernel()
            return phrases.kept(kernel, p, world)
        except Exception:  # noqa: BLE001 - no phrasebook is read as an empty one: she asks, as before
            return []

    def ask_goal(self, text, word=''):
        """No single full match. Her dictionary reads the words over the Field's sheets: a phrase the owner kept is read as he
        kept it (no question, no model); otherwise the licensed options of the MEANING point make one brief. With a model
        loaded, the brief is its one GOAL question (turns.ask), and the answer is used only after answer_check takes it; with
        no model, or a late or refused answer, the very same options are the owner's buttons. No act runs on an answer that
        is not taken."""
        world = self.world()
        found, b = brief.desk(text, world, kept=self._kept(world))
        if found.get('route') == 'ASK' and b is None:      # 0.8.7 B4: an open point that is yours (which revision): her one question
            from . import one_question
            return self.ask_one(text, word, one_question.of_reading(found), found=found)
        if found.get('route') == 'KEPT':
            goals = (found['readings'][0] or {}).get('goals') or ()
            pairs = [(g['template'], dict(g['params'])) for g in goals]
            if not pairs:return False
            note = (found.get('phrase') or {}).get('note')
            if note:self.say(note)
            nt = self.start(text, pairs, word, origin='OWNER')
            nt.model = {'asked': False, 'kept': True, 'calls': 0}
            self.say('Read as you kept it · model calls: 0')
            return True
        if b is None:return self.read_words(text, word, found, world)       # 0.8.7 B3: the words her dictionary left unread
        t = Turn(text, [], word);t.brief = b;t.found = found
        t.cands = [o.goals() for o in b.options]
        t.model = {'asked': False, 'calls': 0, 'options': [o.words for o in b.options], 'brief': b.as_record()}
        self.turn = t;self.snapshot = None
        try:
            kernel, p = self._kernel()
            request = turns.request_for(kernel, p)
        except Exception:  # noqa: BLE001 - no model to reach is the no-model case
            request = None
        t.request = request                                 # 0.8.7 B4: the GOAL turn and her one question card share one request
        if request is None or request.port is None:
            return self._choose_in_words(t, 'No model is loaded, so which of these you meant is yours to choose:')
        t.model.update(asked=True, started=time.monotonic(), calls=1)
        holder = {}

        def run():
            try:holder['answer'] = turns.ask(brief.GOAL, b, request)
            except Exception as exc:  # noqa: BLE001 - a failed turn gives the buttons
                holder['error'] = str(exc)[:200]
        stop = self._stoppable(request)          # 0.8.7 W7: her clock's Stop reaches the turn
        thread = threading.Thread(target=run, name='her-goal-turn', daemon=True);thread.start()
        t.model['holder'] = holder;t.model['thread'] = thread
        self.set_state('thinking')
        self._clock(self.say(named('I am asking my model which of these you meant: %s.') % '; '.join(o.words for o in b.options)), request, thread, stop)
        QTimer.singleShot(POLL_MS, self.poll_goal)
        return True

    # == 0.8.7 B3 · read your words ===========================================================================================
    # Her dictionary read nothing of these words (or not a clause of them). With the owner's understanding switch on, the
    # model reads them once (understand.READ through turns.ask), the desk checks the reading part by part (understand_check),
    # and her card says "I took it as: ...", his words underlined and joined to what they were read as, with Do and Not that.
    # Her three guesses show at once, quietly, while it reads. Do starts the steps that are desk goals as his own (his press);
    # the other steps' acts go through the owner's door on his press, so a change still goes through her hand and asks.
    # Not that is remembered for these words (rule 8): the same reading becomes her question. Switched off: 0.8.6 exactly.
    def read_words(self, text, word, found, world):
        from . import reading, understand
        if not hasattr(self, 'not_that'):self.not_that = []
        if not understand.needed(found):return False
        try:
            kernel, p = self._kernel();request = turns.request_for(kernel, p)
        except Exception:  # noqa: BLE001 - no Kernel to reach: 0.8.6's way
            return False
        if not request.switch_on('understanding'):return False
        try:lex = reading.lexicon(kernel, p, world)
        except Exception:  # noqa: BLE001 - the desk's rows unreadable: the Field's titles alone
            lex = reading.Lexicon.of(world=world)
        _, state, _ = self.read()
        mine = understand.your_words(kernel, p, request)          # 0.8.7 B5: his agreed names and sayings, the dropped verbs
        i = understand.inputs(text, lex, found=found, selected=state.sel or '', refused=tuple(self.not_that), names=mine['names'],
                              dropped=mine['dropped'])
        i.agreed = dict(mine['agreed'])
        t = Turn(text, [], word);t.found = found;t.reading_inputs = i;t.model = {'asked': False, 'calls': 0, 'kind': 'READ'}
        t.request = request;t.model_key = mine.get('model_key')    # 0.8.7 B5: one card per request; the key his tally counts under
        self.turn = t;self.snapshot = None
        said = understand.by_sayings(i, mine['sayings'])          # 0.8.7 B5: a saying of his: read with no model call
        if said is not None:
            t.model.update(saying=(said.get('saying') or {}).get('id', ''));return self._read_card(t, said)
        if request.port is None or i.grammar is None:
            return self._read_card(t, {**understand._empty(i), 'fallback': understand.without_model(i)})
        holder = {}

        def run():
            try:holder['got'] = understand.ask(i, request)
            except Exception as exc:  # noqa: BLE001 - a failed turn gives her guesses
                holder['error'] = str(exc)[:200]
        stop = self._stoppable(request)          # 0.8.7 W7: her clock's Stop reaches the turn
        thread = threading.Thread(target=run, name='her-read-turn', daemon=True);thread.start()
        t.model.update(asked=True, calls=1, started=time.monotonic(), holder=holder, thread=thread)
        self.set_state('thinking')
        self._clock(self._read_buttons(t, 'I am asking my model how to read your words. Meanwhile, my own guesses:', understand.guesses(i)),
                    request, thread, stop)
        QTimer.singleShot(POLL_MS, self.poll_read)
        return True

    def poll_read(self):
        from . import understand
        t = self.turn
        if t is None or not t.model or not t.model.get('thread'):return
        if t.model['thread'].is_alive():
            QTimer.singleShot(POLL_MS, self.poll_read);return
        holder = t.model.pop('holder');t.model.pop('thread')
        got = holder.get('got') or {**understand._empty(t.reading_inputs), 'fallback': understand.without_model(
            t.reading_inputs, 'I could not ask my model (%s). Did you mean one of these?' % holder.get('error', 'no answer'))}
        t.model.update(outcome=got.get('outcome'), why=got.get('why'), turn=got.get('turn'), seconds=round(time.monotonic() - t.model['started'], 3))
        self._read_card(t, got)

    def _read_buttons(self, t, lead, options):
        from .shell2 import sentence
        card = self.say(lead)
        for n, words, found in options:
            pairs = [(g['template'], dict(g['params'])) for g in (found or {}).get('goals') or ()]
            label = sentence('{go}', {'go': ('%d  %s' % (n, words), lambda pairs=pairs: self.start(t.text, pairs, t.word, origin='OWNER'))})
            if card is not None:card.box.addWidget(label)
        return card

    def _read_card(self, t, got):
        """The READ card: "I took it as ..." with Do and Not that; or the one question; or her guesses with the reason."""
        from .shell2 import sentence
        from . import places
        t.understood = {k: got.get(k) for k in ('outcome', 'state', 'readings', 'question', 'refused', 'card')}
        if got.get('talk'):self.say(got['talk']);t.state = 'idle';self.set_state('idle');return False
        question = got.get('question')
        if question:                                     # 0.8.7 B5: an UNSETTLED step asks through B4's one question card
            try:one = understand_mod().as_one_question(got, t.text)
            except Exception:  # noqa: BLE001 - a question that cannot be built: B3's buttons below
                one = None
            if one is not None:return self.ask_one(t.text, t.word, one, t=t)
        if question:
            card = self.say(question['words'])
            for o in question['options']:
                pairs = [(g['template'], dict(g['params'])) for g in (o.get('reading') or {}).get('goals') or ()]
                if card is not None and pairs:
                    card.box.addWidget(sentence('{go}', {'go': ('%d  %s' % (o['n'], o['words']), lambda pairs=pairs: self.start(t.text, pairs, t.word, origin='OWNER'))}))
        elif got.get('card'):
            c = got['card'];card = self.say(c['text'])
            if card is not None:
                said = QLabel(c['html']);said.setTextFormat(Qt.RichText);said.setWordWrap(True);card.box.addWidget(said)
                mark = QLabel(c['mark']);mark.setWordWrap(True);card.box.addWidget(mark)
            readings = got.get('readings') or ()
            if not c['asks'] and readings and all(r.get('frame') == 'DESK' for r in readings) and stacy_hand.level(self.host) in ('show', 'free'):
                # a reading that only moves the window is done at Do and show (basis model_pick: B1's rule lets navigation
                # in the table run there, never a change); Not that puts the window back
                if card is not None:
                    card.box.addWidget(sentence('{not}', {'not': ('Not that', lambda: (self.put_back(), self._read_not(t, got)))}))
                    card.box.addWidget(self._words_buttons(t, got, remember=True))          # 0.8.7 B5: Remember (or Retire)
                return self._read_do(t, got, origin='HER') is not None
            if card is not None:
                card.box.addWidget(sentence('{do} · {not}', {'do': ('Do', lambda: (self._read_do(t, got), self._agree(t, got))),  # 0.8.7 B5: Do agrees
                                                             'not': ('Not that', lambda: self._read_not(t, got))}))
                if got.get('saying'):card.box.addWidget(self._words_buttons(t, got))     # 0.8.7 B5: Retire
        else:
            fb = got.get('fallback') or {}
            card = self._read_buttons(t, fb.get('lead') or '', fb.get('buttons') or ())
            if card is not None and fb.get('find'):
                def find():
                    kernel, p = self._kernel()
                    self.say(' '.join(places.find(kernel, p, fb['find'])['lines']))
                card.box.addWidget(sentence('{find}', {'find': (fb['find_words'], find)}))
        t.state = 'idle';self.set_state('idle')
        return True

    def _read_do(self, t, got, origin='OWNER'):
        """His press on Do (origin OWNER): the desk-goal steps start as his own; the other steps' acts go through the owner's
        door. At Do and show, a navigation-only reading starts at once on the model's reading (origin HER: model_pick)."""
        from .desk_doers import run
        pairs = [(g['template'], dict(g['params'])) for r in got.get('readings') or () if r.get('frame') == 'DESK' for g in r.get('goals') or ()]
        if origin == 'OWNER':
            for r in got.get('readings') or ():
                for name, args in r.get('acts') or ():run(self.host, name, args, door='owner', word=t.text)
        for r in got.get('readings') or ():          # 0.8.7 B8: a total is a read: the maths core's answer, with its receipt
            if r.get('route') == 'TOTAL':
                try:
                    done = understand_mod().total(r)
                    self.say(done['text'] + (' ' + done['receipt'][-1] if done.get('receipt') else ''))
                except Exception as exc:  # noqa: BLE001 - a total that cannot be worked out is said, never guessed
                    self.say('I could not add these up: %s' % str(exc)[:160])
        if pairs:return self.start(t.text, pairs, t.word, origin=origin)
        return None

    def _read_not(self, t, got):
        from . import reading
        key = reading.said_key(t.text)
        self.not_that += [(key, s['verb'], s['thing']) for s in got.get('steps') or () if s.get('state') == 'OK' and s.get('thing')]
        if got.get('saying'):                       # 0.8.7 B5: a saying's reading: nothing counts against the model
            self.say('Not that: I will not read these words this way again.');return
        verbs = [s['verb'] for s in got.get('steps') or () if s.get('state') == 'OK']
        try:                                        # 0.8.7 B5: no row; the verb's tally counts one correction
            kernel, p = self._kernel()
            done = kernel.dispatch('phrases.not_that', {'verbs': verbs, **({'model_key': t.model_key} if getattr(t, 'model_key', None) else {})}, p)
            self.say(done['result']['words'] if done.get('ok') else 'Not that: I will not read these words this way again.')
            for v in (done.get('result') or {}).get('dropped') or ():
                if v in verbs:self.say(phrases.WORDS['dropped'].format(verb=v))
        except Exception:  # noqa: BLE001 - the tally cannot be written: the session's Not that still holds
            self.say('Not that: I will not read these words this way again.')

    # -- 0.8.7 B5 · your words: Do, Remember or a click on her question agree; Retire takes a saying back ---------------------
    def _agree(self, t, got, tally=True):
        """His agreement (Do, Remember, his click on her question): phrases.agree makes one name row a step and one saying
        row; she says 'Remembered: “pull up where … came from” means Trace.' A saying's own card counts nothing for the model."""
        steps = got if isinstance(got, list) else understand_mod().agreed_steps(got.get('steps'))
        if not steps:return None
        tally = tally and not (isinstance(got, dict) and got.get('saying'))
        try:
            kernel, p = self._kernel()
            args = {'text': t.text, 'steps': steps, 'tally': bool(tally)}
            if getattr(t, 'model_key', None):args['model_key'] = t.model_key
            done = kernel.dispatch('phrases.agree', args, p)
        except Exception as exc:  # noqa: BLE001 - nothing remembered is better than a broken card
            self.say('I did not remember it: %s' % str(exc)[:160]);return None
        self.say(done['result']['words'] if done.get('ok') else 'I did not remember it: %s' % str((done.get('error') or {}).get('message'))[:160])
        return done

    def _retire(self, ident):
        try:
            kernel, p = self._kernel()
            done = kernel.dispatch('phrases.strike', {'id': ident}, p)
        except Exception as exc:  # noqa: BLE001
            self.say('I did not retire it: %s' % str(exc)[:160]);return None
        self.say(done['result']['words'] if done.get('ok') else 'I did not retire it: %s' % str((done.get('error') or {}).get('message'))[:160])
        return done

    def _words_buttons(self, t, got, remember=False):
        from .shell2 import sentence
        saying = (got.get('saying') or {}).get('id')
        if saying:return sentence('{retire}', {'retire': ('Retire this saying', lambda: self._retire(saying))})
        return sentence('{remember}', {'remember': ('Remember', lambda: self._agree(t, got))})

    def _read_answered(self, t, q, c, placed):
        """His answer to her one question about his words: the chosen reading runs beside the settled ones (his click:
        his own; the model's placing: model_pick, never a change of hers). His click agrees: its rows are made, no tally."""
        r = dict(c.reading);agree = r.pop('_agree', []);held = list(r.pop('_held', []));saying = r.pop('_saying', '');r.pop('_saying_words', None)
        origin = 'HER' if placed.basis == 'model_pick' else 'OWNER'
        if placed.words:self.say(placed.words)
        nt = self._read_do(t, {'readings': held + [r]}, origin=origin)
        if nt is not None:
            nt.model = dict(t.model or {}, chosen=c.n, by=placed.by);nt.question = q;nt.request = getattr(t, 'request', None)
        else:
            t.state = 'finished';self.set_state('finished')
        if origin == 'OWNER' and q.source == 'saying':
            from .shell2 import sentence
            others = [o.reading.get('_saying') for o in q.choices if o.n != c.n and o.reading.get('_saying')]
            card = self.say(phrases.WORDS['conflict_after'].format(sayings=' and '.join('“%s”' % (o.reading.get('_saying_words') or o.words) for o in q.choices)))
            if card is not None:
                for ident in dict.fromkeys(others + ([saying] if saying else [])):
                    words = next(('Retire “%s”' % (o.reading.get('_saying_words') or o.words) for o in q.choices if o.reading.get('_saying') == ident), 'Retire')
                    card.box.addWidget(sentence('{go}', {'go': (words, lambda ident=ident: self._retire(ident))}))
        elif origin == 'OWNER' and agree:
            self._agree(t, agree, tally=False)
        return nt
    # == end 0.8.7 B3 and B5 ==================================================================================================

    def ask_model(self, args):
        """brain.ask through the Kernel, with the owner's principal (kept for the half-build's own check)."""
        kernel, p = self._kernel()
        return kernel.dispatch('brain.ask', {**args, 'request_key': uuid.uuid4().hex}, p)

    def poll_goal(self):
        t = self.turn
        if t is None or not t.model or not t.model.get('thread') or t.goals:return
        if t.model['thread'].is_alive():
            QTimer.singleShot(POLL_MS, self.poll_goal);return
        holder = t.model.pop('holder');t.model.pop('thread')
        answer = holder.get('answer');elapsed = time.monotonic() - t.model['started']
        t.model.update(seconds=round(elapsed, 3))
        if answer is None:
            t.model['outcome'] = 'FAILED'
            return self._choose_in_words(t, 'I could not ask my model (%s), so which of these you meant is yours to choose:' % holder.get('error', 'no answer'))
        verdict = answer.verdict
        t.model.update(outcome=answer.outcome, why=answer.why, price_ms=answer.price_ms, deadline_ms=answer.deadline_ms,
                       raw=answer.said.for_check() if answer.said is not None else None, turn=answer.turn,
                       check=[list(c) for c in (verdict.checks if verdict is not None else ())])
        if answer.outcome == 'LATE':return self._late(t, elapsed)
        if answer.outcome not in ('TAKEN', 'TRIMMED') or not answer.by_model:
            lead = {'UNSETTLED': 'My model’s pick did not cover everything you asked, so which of these you meant is yours to choose:',
                    'NOT_SENT': 'I did not ask my model, so which of these you meant is yours to choose:'}.get(
                answer.outcome, 'My model’s answer did not fit your words, so I did not use it. Which of these did you mean?')
            return self._choose_in_words(t, lead)
        picks = list(answer.value or ())
        if not picks:
            t.state = 'finished';t.closing = 'None of these fits your words, so I leave the window as it is.'
            self.say(t.closing);self.set_state('finished');return
        opened = t.brief.option(picks[0]) if len(picks) == 1 else None
        if opened is not None and opened.reading.get('revision_open'):   # 0.8.7 B4: which revision stays yours: her one question
            from . import one_question
            return self.ask_one(t.text, t.word, one_question.of_revision_open(opened, t.text), t=t)
        pairs = [pair for n in picks for pair in t.cands[n - 1]]
        self._begin_from(t, pairs, 'HER')
        self._fold(t, self.say('The model’s pick, checked against your words · model calls: 1'))
        self._offer_keep(t, [t.brief.option(n) for n in picks])

    def _fold(self, t, card=None):
        """'What I asked the model': 0.8.7 A4, the mark line and the fold (model_marks_qt) of the stored turn, exactly: what
        she sent, what it answered (model-marked), what she checked, how long it took; and Forget this turn."""
        m = t.model or {}
        if getattr(t, 'brief', None) is None or not m.get('turn'):return
        from . import model_marks_qt
        if card is None:return
        model_marks_qt.mark_card(card, 'CHECKED')
        try:
            kernel, p = self._kernel()
            card.box.addWidget(model_marks_qt.Fold.for_turn(self.host, m['turn'], kernel, p))
        except Exception:  # noqa: BLE001 - a fold that cannot be read never takes her card down
            card.box.addWidget(model_marks_qt.Fold(None, None, 'it could not be read'))

    def _late(self, t, elapsed):
        """Past the deadline: the top option is taken by default only when it is a read or a move of the window (a change
        never is) and the move is hers now; otherwise the options are the owner's buttons."""
        t.model.update(seconds=round(elapsed, 3), late=True)
        top = t.brief.options[0] if t.brief is not None and t.brief.options else None
        if top is not None and top.acts in ('read', 'navigates') and stacy_hand.level(self.host) in ('show', 'free') and top.goals():
            t.model['default'] = top.words
            return self._begin_from(t, top.goals(), 'DEDUCED', default=True)
        self._choose_in_words(t, 'My model did not answer in time, so which of these you meant is yours to choose:')

    def _begin_from(self, t, pairs, origin, default=False):
        model = t.model
        nt = self.start(t.text, pairs, t.word, origin=origin)
        nt.model = model;nt.brief = getattr(t, 'brief', None);nt.found = getattr(t, 'found', None)
        if default:self.say('My model did not answer in time, so I took the first of these, which only moves the window: %s.' % model.get('default'))
        return nt

    def _choose_in_words(self, t, lead):
        """The brief's options as the owner's buttons, exactly (and "None of these"); nothing runs until he presses one. His
        press is his own approval; she then offers to keep his words. 0.8.7 B4: shown as her one question card (ask_one)."""
        if getattr(t, 'brief', None) is not None:
            from . import one_question
            return self.ask_one(t.text, t.word, one_question.of_brief(t.brief), t=t, lead=lead)
        from .shell2 import sentence
        card = self.say(lead)
        options = brief.buttons(t.brief) if getattr(t, 'brief', None) is not None else []
        t.buttons = options
        for n, words in options:
            if n:
                label = sentence('{go}', {'go': ('%d  %s' % (n, words), lambda n=n: self.choose(t, n))})
            else:
                label = sentence('{go}', {'go': (words, lambda: self.choose(t, 0))})
            if card is not None:card.box.addWidget(label)
        t.state = 'idle';self.set_state('idle')
        return True

    def choose(self, t, n):
        """The owner's press on one of the buttons (0: none of these)."""
        if n == 0:
            t.state = 'finished';t.closing = 'None of these, so I leave the window as it is.'
            self.say(t.closing);self.set_state('finished');return None
        option = t.brief.option(n)
        nt = self.start(t.text, option.goals(), t.word, origin='OWNER')
        nt.model = dict(t.model or {}, chosen=n, by='owner');nt.brief = t.brief;nt.found = t.found
        self._offer_keep(nt, [option])
        return nt

    def _offer_keep(self, t, options):
        """'Keep “pop … up” as trace?': once, after a pick the owner pressed or the checker took. A phrase is kept only by his
        press (phrases.keep, approve scope); it is never offered again once struck, nor when kept already."""
        options = [o for o in options if o is not None]
        if not options or getattr(t, 'found', None) is None:return None
        chosen = {'words': '; '.join(o.words for o in options),
                  'reading': {'frame': 'DESK', 'goals': [g for o in options for g in (o.reading.get('goals') or ())]}}
        try:
            kernel, p = self._kernel()
            offer = phrases.offer(kernel, p, t.text, chosen, t.found)
        except Exception:  # noqa: BLE001 - no offer is better than a broken card
            return None
        if offer is None:return None
        from .shell2 import sentence

        def keep(follows):
            got = kernel.dispatch('phrases.keep', {'text': t.text, 'chosen': chosen, 'follows': follows, 'shown': offer['words']}, p)
            self.say(got['result']['words'] if got.get('ok') else 'I did not keep it: %s' % str((got.get('error') or {}).get('message'))[:160])
        actions = {'keep': ('Keep it', lambda: keep('CURRENT'))};words = '{keep}'
        if offer['revision_titles']:
            actions = {'keep': ('Follow the current revision', lambda: keep('CURRENT')), 'stay': ('Stay on this one', lambda: keep('THIS_REVISION'))}
            words = '{keep} · {stay}'
        t.keep_offer = offer
        card = self.say(offer['question'])
        if card is not None:card.box.addWidget(sentence(words, actions))
        return offer

    # == 0.8.7 B4 · the one question (one_question.py): one card per request, on the buttons above ===========================
    def _request(self, t):
        """This owner request's TurnRequest (its one card, its model ceiling); one with no model when none can be made."""
        found = getattr(t, 'request', None)
        if found is None:
            try:
                kernel, p = self._kernel();found = turns.request_for(kernel, p)
            except Exception:  # noqa: BLE001 - no Kernel to reach: no model, and still one card
                found = turns.TurnRequest()
            t.request = found
        return found

    def ask_one(self, text, word, question, t=None, lead='', found=None):
        """Her one question card: the choices in her ranked order, Something else (a typed answer, read against these
        options only) and Leave it. A second question in the same request is never shown: she says cannot tell instead."""
        from PySide6.QtWidgets import QLineEdit
        from . import one_question as Q
        from .shell2 import sentence
        if question is None:return False
        if t is None:
            t = Turn(text, [], word);t.found = found;t.model = {'asked': False, 'calls': 0}
            self.turn = t;self.snapshot = None
        if not Q.card(question, self._request(t)):
            t.state = 'finished';self.say(Q.once_more(question));self.set_state('finished');return True
        t.question = question;t.answered = False;t.model = dict(t.model or {}, question=question.as_record())
        card = self.say(lead or question.words)
        if card is not None:
            for n, words in question.buttons():
                if n == Q.ELSE:continue
                said = words if n == Q.LEAVE else '%d  %s' % (n, words)
                card.box.addWidget(sentence('{go}', {'go': (said, lambda n=n: self._answered(t, Q.click(question, n)))}))
            typed = QLineEdit();typed.setObjectName('HerOneQuestionTyped')
            typed.setPlaceholderText('%s: %s' % (Q.BUTTONS['else'], Q.BUTTONS['typed']))
            typed.returnPressed.connect(lambda: self._typed(t, typed.text()))
            card.box.addWidget(typed)
        t.state = 'idle';self.set_state('idle')
        return True

    def _typed(self, t, typed):
        """A typed answer: placed by her fixed rules, else (no authority, a model loaded) the model's PICK off the window's
        thread; not placed: "please choose one of these", on the same card."""
        from . import one_question as Q
        q = getattr(t, 'question', None)
        if q is None or getattr(t, 'answered', False) or not str(typed).strip():return None
        placed = Q.place(q, typed)
        if placed is not None:return self._answered(t, placed)
        request = self._request(t)
        if q.authority or request.port is None:
            self.say(Q.not_placed(q, typed).words);return None
        holder = {}

        def run():
            try:holder['placed'] = Q.answer(q, typed, request)
            except Exception as exc:  # noqa: BLE001 - a failed turn leaves the buttons
                holder['error'] = str(exc)[:200]
        stop = self._stoppable(request)          # 0.8.7 W7: her clock's Stop reaches the turn
        thread = threading.Thread(target=run, name='her-pick-turn', daemon=True);thread.start()
        t.model['calls'] = int(t.model.get('calls') or 0) + 1
        self.set_state('thinking');self._clock(self.say(named('I am asking my model which of these your answer chooses.')), request, thread, stop)

        def poll():
            if thread.is_alive():QTimer.singleShot(POLL_MS, poll);return
            got = holder.get('placed')
            t.model['pick'] = got.as_record() if got is not None else {'error': holder.get('error')}
            if got is None or not got.placed:
                self.set_state('idle');self.say(Q.not_placed(q, typed).words);return
            self._answered(t, got)
        QTimer.singleShot(POLL_MS, poll)
        return None

    def _answered(self, t, placed):
        """The one answer: Leave it gives the read default or cannot tell; a choice starts its goals (the owner's click or
        words: his own approval; the model's placing: basis model_pick, so a change on it is never hers)."""
        from . import one_question as Q
        q = t.question
        if getattr(t, 'answered', False) or (self.turn is not t and getattr(self.turn, 'question', None) is not q):return None
        t.answered = True;t.model['answer'] = placed.as_record()
        if placed.n == Q.LEAVE:          # 0.8.7 W7: Leave it runs the reads it says it runs, and says only those
            ran = Q.runnable(q, Q.leave(q).take)
            left = Q.left_done(q, ran);t.model['left'] = left.as_record()
            t.state = 'finished';t.closing = left.words;self.say(left.words)
            pairs = [p for n in ran for p in q.choice(n).goals()]
            if pairs:                    # reads that decide nothing for him: the desk's default, a deduction, never his choice
                nt = self.start(t.text, pairs, t.word, origin='DEDUCED')
                nt.model = dict(t.model);nt.question = q;nt.request = getattr(t, 'request', None)
                return nt
            self.set_state('finished');return None
        c = q.choice(placed.n)
        if q.source in ('understand', 'saying'):return self._read_answered(t, q, c, placed)     # 0.8.7 B5: his words' question
        if placed.words:self.say(placed.words)
        if c.reading.get('revision_open'):          # a second question would be needed: never a second card
            t.state = 'finished';self.say(Q.once_more('REVISION'));self.set_state('finished');return None
        pairs = Q.goals_with(getattr(t, 'found', None) if q.source == 'reading' else None, q, c)
        if not pairs:                    # 0.8.7 W7: nothing here runs, so she says no read was done (Q.leave would claim one)
            t.state = 'finished';self.say(Q.left_done(q, ()).words);self.set_state('finished');return None
        nt = self.start(t.text, pairs, t.word, origin='HER' if placed.basis == 'model_pick' else 'OWNER')
        nt.model = dict(t.model, chosen=c.n, by=placed.by);nt.brief = getattr(t, 'brief', None);nt.found = getattr(t, 'found', None)
        nt.question = q;nt.request = getattr(t, 'request', None)
        more = Q.more_words(q)
        if more:self.say(more)
        if placed.basis != 'model_pick':self._offer_keep(nt, [c])
        return nt
    # == end 0.8.7 B4 =======================================================================================================

    # == 0.8.7 W7 · her clock's line under her card while a model turn runs (design 4.4) =====================================
    @staticmethod
    def _stoppable(request):
        """Her clock's Stop for this request, put on it before the turn's thread starts: {'pressed': bool}. A press is
        read by turns.ask (request.cancelled) and by the port's stream, which closes the turn."""
        stop = {'pressed': False}
        if request is None:return stop
        before = getattr(request, 'cancelled', None) or (lambda: False)
        request.cancelled = lambda: stop['pressed'] or bool(before())
        return stop

    def _clock(self, card, request, thread, stop=None):
        """'Asking the model: 2 s of about 3 · Stop' under her card while the turn runs: the seconds gone and her clock's
        price (brain_clock.asking_now, from the request's own running turn), set again four times a second; Stop closes
        the turn; the line goes when the turn ends. Returns the line, or None when there is no card."""
        if card is None or request is None or thread is None:return None
        import html as _html
        from . import brain_clock
        from .shell2 import sentence
        stop = stop if stop is not None else self._stoppable(request)
        actions = {'stop': ('Stop', lambda: stop.update(pressed=True))}
        line = sentence('', actions);line.setObjectName('HerClockLine');line.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        line.setAccessibleName('Her clock')
        try:card.box.addWidget(line)
        except (AttributeError, RuntimeError):return None
        timer = QTimer(line);timer.setInterval(250)

        def tick():
            try:
                if not thread.is_alive():timer.stop();line.hide();return
                said = 'Stopping' if stop['pressed'] else (brain_clock.asking_now(request) or 'Asking the model')
                sentence(_html.escape(said) + ('' if stop['pressed'] else ' · {stop}'), actions, label=line)
            except RuntimeError:  # the card left her column
                timer.stop()
        timer.timeout.connect(tick);timer.start();tick()
        return line
    # == end 0.8.7 W7 ========================================================================================================

    # -- where a press lands --------------------------------------------------------------------------------------------------
    def still(self):
        try:
            from .document_qt import profile_of
            return bool(profile_of(self.host).get('reduce_motion'))
        except Exception:  # noqa: BLE001
            return True

    def press_point(self, step):
        """Where the next act's press will land, as a global point (best effort; None: no ring)."""
        from . import desk_doers as D
        host = self.host
        try:
            if step.act == 'go.field':
                word = D.head_word(host, 'Arrange');return word.mapToGlobal(word.rect().center())
            page = getattr(host, 'field_page', None)
            if page is None:return None
            view = page.view
            if step.act == 'point.sheet':
                obj = D.find_sheet(view, step.args.get('title'));return view.mapToGlobal(D.sheet_point(view, obj.id).toPoint())
            if step.act in ('sheet.trace', 'sheet.compare'):
                obj = view.selected();return view.mapToGlobal(D.sheet_point(view, obj.id).toPoint()) if obj is not None else None
            if step.act == 'point.zoom':
                spot = next((box for box, k, _, said in view._hot if k == Qt.Key_Z), None)
                return view.mapToGlobal(spot.center().toPoint()) if spot is not None else None
            if step.act == 'sheet.close' and (view.revisions is not None or view.reading is not None):
                inner = view._rev_rect if view.revisions is not None else view._reading_rect(view._layout())
                at = D.beside(view, inner);return view.mapToGlobal(at.toPoint()) if at is not None else None
            if step.act == 'menu.close':return D.outside(host)
        except Exception:  # noqa: BLE001 - no ring is better than a wrong one
            return None
        return None

    def on_card(self, event):
        """Whether a press lands on her card (Go ahead, Stop, Put my window back are the owner's own presses on it)."""
        card = self.card
        if card is None:return False
        try:
            if not card.isVisible():return False
            if hasattr(event, 'globalPosition'):
                at = event.globalPosition().toPoint()
                return card.rect().contains(card.mapFromGlobal(at))
            focus = QApplication.focusWidget()
            return focus is not None and (focus is card or card.isAncestorOf(focus))
        except RuntimeError:
            return False


def understand_mod():
    """0.8.7 B5: understand.py, imported when her hand first reads his words."""
    from . import understand
    return understand


def hand(host):
    """host.her_hand, made the first time it is asked for."""
    found = getattr(host, 'her_hand', None)
    if found is None:
        found = HerHand(host)
        host.her_hand = found
    return found
