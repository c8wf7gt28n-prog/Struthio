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

Budgets for a turn: 24 acts, 120 s not counting the owner's own time, 6 plans, 2 surprises in a row. A repeated move from
the same window stops the turn, with words. Changes are not hers in this slice: her door refuses them.
"""
import json
import time
import uuid

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QWindow
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import desk_ops, goals as G, hand_words, planner, stacy_hand
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
        self.go.setObjectName('HerHandGo');self.stop_button.setObjectName('HerHandStop');self.again.setObjectName('HerHandContinue');self.back.setObjectName('HerHandBack')
        self.go.clicked.connect(lambda: hand.go_ahead(by_owner=True));self.stop_button.clicked.connect(lambda: hand.stop('card'))
        self.again.clicked.connect(hand.carry_on);self.back.clicked.connect(lambda: hand.put_back())
        for b in (self.go, self.stop_button, self.again, self.back):row.addWidget(b)
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
        self.stop_button.setVisible(state in ('thinking', 'acting'))
        self.again.setVisible(state == 'stopped' and not t.putting_back)
        self.back.setVisible(state in ('stopped', 'finished') and self.hand.snapshot is not None and t.done > 0)
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
                'model': t.model, 'rows': [{'act': r['step'].act, 'args': r['step'].args, 'state': r['state']} for r in t.rows]}

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
        desk, state, world = self.read()
        t.world = world if (world.sheets and state.face == 'work') else self.world()
        t.snapshot = state;t.snapshot_digest = G.digest(desk)
        state_now = getattr(self.host.session, 'state', {})
        t.trail_before = len(state_now.get(stacy_hand.TRAIL) or []);t.desk_trail_before = len(state_now.get(stacy_hand.DESK_TRAIL) or [])
        self.turn = t;self.snapshot = state;self.snapshot_world = t.world;self.stop_flag = False
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
        self.pointer.clear()
        if t.state == 'waits':
            t.offered = [];t.authorised = [];t.stopped_after = t.done
            self.set_state('stopped', 'Stopped: nothing was done after your word.')
        # while she moves, the next press refuses (STOPPED) and the tick pauses the turn there

    def carry_on(self):
        """Continue from where the window is now."""
        t = self.turn
        if t is None or t.state != 'stopped':return
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

    def halt(self, why):
        """The turn stops with words (a budget, a repeat, a plan that cannot be made)."""
        t = self.turn
        t.stopped_after = t.done;self.pointer.clear()
        self.set_state('stopped', why)

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
            return self.set_state('stopped', named('You took the window back, so my hand stopped after %d act%s. Continue goes on from here; Put my window back returns it as it was.') % (t.done, '' if t.done == 1 else 's'))
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
        """Back to the window as the turn found it: a plan of navigation, run through her door now (at most 12 moves)."""
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
        desk, state, _ = self.read()
        back = planner.back_to(state, snap)
        said = ('The window is back as it was: %s.' % self._where(snap)) if back else ('I could not put it all back: %s' % (words or 'the window is not as it was'))
        t.closing = said;self._count_trails()
        self.set_state('finished' if back else 'stopped', '' if back else said)
        return {'back': back, 'acts': moved, 'words': said, 'surface': state.surface, 'selected': state.sel,
                'over': list(state.over) if state.over else None, 'snapshot': {'surface': snap.surface, 'selected': snap.sel, 'over': list(snap.over) if snap.over else None}}

    def _where(self, snap):
        if snap.surface != 'field':return {'home': 'Today in front', 'workspace': 'your work in front'}.get(snap.surface, 'as it was')
        return 'the Field in front' + (', “%s” selected' % snap.sel if snap.sel else '') + (', nothing over the work' if not snap.over else '')

    # -- the GOAL turn: which goals did the owner mean ----------------------------------------------------------------------------
    def ask_goal(self, text, word=''):
        """No single full match: the model is asked one small question (pick mode), or, with no model, the owner is shown
        the goals as words he can choose. No act runs on an answer that is not valid."""
        world = self.world();cands = hand_words.candidates(text, world)
        if not cands:return False
        t = Turn(text, [], word);t.model = {'asked': False, 'candidates': [hand_words.ask_words(*c) for c in cands]}
        t.cands = cands;self.turn = t;self.snapshot = None
        from .shell2 import call
        brain = call(self.host, 'brain.status') or {}
        if brain.get('state') != 'READY':
            self._choose_in_words(t, 'No model is loaded, so I cannot settle which you meant. Choose one:');return True
        r = self.ask_model({'message': hand_words.pick_message(text, cands), 'mode': 'pick', 'picks': len(cands) + 1})
        if not r.get('ok'):
            self._choose_in_words(t, 'I could not ask my model (%s). Choose one:' % str((r.get('error') or {}).get('message'))[:120]);return True
        t.model.update(asked=True, job=r['result']['id'], started=time.monotonic())
        self.set_state('thinking');self.say(named('I am asking my model which of my goals on the desk you meant.'))
        QTimer.singleShot(POLL_MS, self.poll_goal)
        return True

    def ask_model(self, args):
        """brain.ask through the Kernel, with the owner's principal (the job's answer is read by poll_goal)."""
        from .engine import engineering
        from .engineering_kernel import operator
        return engineering(self.host.root).dispatch('brain.ask', {**args, 'request_key': uuid.uuid4().hex}, operator())

    def poll_goal(self):
        t = self.turn
        if t is None or not t.model or not t.model.get('job') or t.goals:return
        from .shell2 import call
        job = call(self.host, 'jobs.get', {'id': t.model['job']}) or {}
        elapsed = time.monotonic() - t.model['started']
        if job.get('state') not in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):
            if elapsed > MODEL_SECONDS:return self._late(t, elapsed)
            QTimer.singleShot(POLL_MS, self.poll_goal);return
        result = (call(self.host, 'brain.result', {'id': t.model['job']}) or {}).get('result') or {}
        metrics = result.get('metrics') or {}
        t.model.update(seconds=round(elapsed, 3), prompt_tokens=(metrics.get('usage') or {}).get('prompt_tokens') or metrics.get('prompt_tokens_measured'),
                       output_tokens=(metrics.get('usage') or {}).get('completion_tokens'), state=job.get('state'))
        proposal = result.get('proposal') or {}
        if job.get('state') != 'Completed' or 'pick' not in proposal:
            t.model['valid'] = False
            return self._choose_in_words(t, 'I could not settle what you meant: my model did not answer with goals I offered. Choose one:')
        t.model.update(valid=True, pick=list(proposal['pick']))
        if not proposal['pick']:
            t.state = 'finished';t.closing = 'None of my goals on the desk fits that, so I leave the window as it is.'
            self.say(t.closing);self.set_state('finished');return
        self._begin_from(t, [t.cands[n - 1] for n in proposal['pick']], 'HER')

    def _late(self, t, elapsed):
        """Past the deadline: the top goal is taken by default when it only reads or moves the window and the move is hers
        now; a change never is. Otherwise the goals are shown as words to choose."""
        from .shell2 import call
        try:call(self.host, 'jobs.cancel', {'id': t.model['job']})
        except Exception:  # noqa: BLE001
            pass
        t.model.update(seconds=round(elapsed, 3), late=True)
        top = t.cands[0]
        if stacy_hand.level(self.host) in ('show', 'free') and top[0] in ('traced', 'shown', 'side_by_side', 'tidy'):
            t.model['default'] = hand_words.ask_words(*top)
            return self._begin_from(t, [top], 'DEDUCED', default=True)
        self._choose_in_words(t, 'I could not settle what you meant in time. Choose one:')

    def _begin_from(self, t, pairs, origin, default=False):
        model = t.model
        nt = self.start(t.text, pairs, t.word, origin=origin)
        nt.model = model
        if default:self.say('My model did not answer in time, so I took the first of my goals: %s.' % model.get('default'))

    def _choose_in_words(self, t, lead):
        """The deterministic goals, as words the owner can choose; nothing runs until he does."""
        from .shell2 import sentence
        card = self.say(lead)
        for n, pair in enumerate(t.cands[:8], 1):
            label = sentence('{go}', {'go': ('%d  %s' % (n, hand_words.ask_words(*pair)), lambda pair=pair: self.start(t.text, [pair], t.word))})
            if card is not None:card.box.addWidget(label)
        t.state = 'idle';self.set_state('idle')
        return True

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


def hand(host):
    """host.her_hand, made the first time it is asked for."""
    found = getattr(host, 'her_hand', None)
    if found is None:
        found = HerHand(host)
        host.her_hand = found
    return found
