"""The right column's Work and Related blocks, and the driver that steps a running assignment between events (HATCH AGENT-01).

The driver is a QTimer, not a scheduler: every 250 ms it calls ``agent.step`` once for each assignment it was asked to
drive, lets the interface breathe between steps, and stops ticking when none is RUNNING. Nothing here starts a worker, a
model or a job; the one bounded step is a Kernel operation with the assignment's own principal. Closing Ledger and
Master Stop pause what is running (``pause_all``) and the Today page offers to resume it (``today_rows``).

HATCH AGENT-02: when the desktop talks to the Ledger service (``kernel.is_host_client``) and the owner's setting
agent.continue_when_closed is on, closing Ledger hands the running assignments to the service instead (``release_all``:
agent.release on each); the service's existing 5 s tick steps them (agent_loop.pump) and Today says what it did ("While
Ledger was closed, Slate took N steps on …"). A reopened window takes the work back (``adopt``: the desktop's own steps take
the lease, so the service stops stepping them). Master Stop still pauses everything, on both sides.

The Work block shows the five lines of ``agent.status`` (working on, doing now, found, needs you, inspect) for the
assignment that matters now, with Stop, Pause, Resume and Inspect as words in the lines. The Related block lists up to
five of the owner's own records that share the page's words (``ledger.related``: word match, no model), refreshed 1.5 s
after the page last changed, each with a dismiss mark; dismissed ids stay in the session state.

Every Kernel call here goes through ``call``/``call_write``, so an operation that is not filled yet (NotImplementedError
until its work item lands) or refused leaves an empty block and a word in the status line, never an exception.
"""
from __future__ import annotations
import time
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget
from .shell2 import QUIET, call, call_write, escape_text, open_destination, role, sentence

TICK_MS = 250                 # the driver: one step per RUNNING assignment per tick
BLOCK_MS = 4000               # the Work block's own refresh while nothing is being driven
RELATED_MS = 1500             # the Related block looks at the page this long after it last changed
RELATED_LIMIT = 5
DISMISSED_KEEP = 200
ACTIVE = ('READY', 'RUNNING')
STATE_WORDS = {'READY': 'ready', 'RUNNING': 'running', 'PAUSED': 'paused', 'WAITING': 'needs you', 'DONE': 'done', 'STOPPED': 'stopped', 'FAILED': 'could not finish'}
WORKING_ANSWER = 'Working on it: %s. Watch the Work lines above; Stop is there.'
CONTINUE_KEY = 'agent.continue_when_closed'       # AGENT-02: the owner's setting (settings_registry)
RELEASED_WORDS = 'Graphite closed · the Graphite service continues'
IN_SERVICE = 'in the Graphite service · '          # the doing-now prefix while the service holds the lease
ADOPT_MS = 1500                                   # a reopened window takes running work back this long after it opens
ADOPT_AGAIN = 3                                   # times adopt looks again when a desktop lease it skipped runs out
LEASE_MS = 20000                                  # agent_loop.LEASE_SECONDS, when a row does not say when its lease ends
CLOSED_WINDOW = 24 * 3600                         # Today mentions service steps on assignments updated this recently


# -- the Kernel calls, module-level so tests can hold them -----------------------------------------------------------------

def step_once(host, ident): return call_write(host, 'agent.step', {'id': ident})
def pause_one(host, ident, reason): return call_write(host, 'agent.pause', {'id': ident, 'reason': str(reason)[:300]})
def resume_one(host, ident): return call_write(host, 'agent.resume', {'id': ident})
def stop_one(host, ident, reason='Stop'): return call_write(host, 'agent.stop', {'id': ident, 'reason': str(reason)[:300]})
def release_one(host, ident): return call_write(host, 'agent.release', {'id': ident})
def summaries(host): return [r for r in ((call(host, 'agent.list') or {}).get('assignments') or []) if isinstance(r, dict) and r.get('id')]


def hosted(host):
    """True when this window's Kernel is the Ledger service (a host client), the only case where work can continue after it closes."""
    bridge = getattr(host, 'ledger_bridge', None)
    return bool(getattr(getattr(bridge, 'kernel', None), 'is_host_client', False))


def continue_setting(host):
    """The owner's setting as the Kernel stores it (ledger.settings.effective); False when it cannot be read, so closing pauses."""
    rows = (call(host, 'ledger.settings.effective', {'key': CONTINUE_KEY}) or {}).get('settings') or []
    row = next((r for r in rows if isinstance(r, dict) and r.get('key') == CONTINUE_KEY), None)
    return bool(row is not None and row.get('stored') is True)


def service_holds(row):
    """The assignment is being stepped by the Ledger service right now (its lease is live)."""
    return bool(row) and row.get('driver') == 'service' and bool(row.get('lease_live'))


def status(host, ident):
    rows = (call(host, 'agent.status', {'id': ident}) or {}).get('assignments') or []
    return next((r for r in rows if isinstance(r, dict)), None)


def words_of(item):
    """A claim, a reason or an inspect entry as words, whatever shape the row gives it."""
    if isinstance(item, str): return item
    if isinstance(item, dict):
        text = item.get('text') or item.get('reason') or item.get('label') or ''
        state = item.get('evidence_state')
        # The investigation's four evidence states in the owner's words: a finding from recorded steps is not yet independently checked.
        words = {'UNKNOWN': ' · recorded, not yet checked', 'REFUTED': ' · refuted', 'CONFLICT': ' · conflicting evidence', 'SUPPORTED': ' · checked', 'CONFIRMED': ' · checked'}
        return text + (words.get(str(state), ' · ' + str(state).lower().replace('_', ' ')) if state else '')
    return str(item)


# -- the driver ------------------------------------------------------------------------------------------------------------

class AgentDriver(QObject):
    """Steps the assignments it was asked to drive, one bounded step each per tick, and tells the Work blocks."""

    def __init__(self, host):
        super().__init__(host if isinstance(host, QObject) else None)
        self.host = host; self.active = []; self.busy = False; self.ticks = 0; self.states = {}; self.last_error = {}; self.handed = None
        self.adopt_tries = 0; self.adopt_wait = None   # AGENT-02: adopt looks again (at most ADOPT_AGAIN times) when a skipped lease runs out
        self.timer = QTimer(self); self.timer.setInterval(TICK_MS); self.timer.timeout.connect(self.tick)
        self.blocks = list(host.findChildren(WorkBlock)) if hasattr(host, 'findChildren') else []

    def running(self): return list(self.active)

    def start(self, ident):
        if ident not in self.active: self.active.append(ident)
        self.states.setdefault(ident, 'READY'); self.last_error.pop(ident, None)
        if not self.timer.isActive(): self.timer.start()
        self.refresh(); return True

    def tick(self):
        if self.busy or getattr(self.host, '_closing', False): return
        self.busy = True; changed = []
        try:
            for ident in list(self.active):
                r = step_once(self.host, ident)
                if not r.get('ok'):
                    self.last_error[ident] = (r.get('error') or {}).get('message', 'the step was refused'); self.active.remove(ident); continue
                result = r.get('result') or {}; assignment = result.get('assignment') or {}
                state = assignment.get('state'); self.states[ident] = state; changed.append(assignment)
                if state not in ACTIVE: self.active.remove(ident)
            self.ticks += 1
            if not self.active: self.timer.stop()
        finally: self.busy = False
        for assignment in changed: sync_pages(self.host, assignment)
        self.refresh()

    def pause_all(self, reason):
        """Everything RUNNING pauses with the reason (closing Ledger, Master Stop); the Today page offers to resume."""
        ids = list(self.active)
        for row in summaries(self.host):
            if row.get('state') == 'RUNNING' and row['id'] not in ids: ids.append(row['id'])
        paused = []
        for ident in ids:
            r = pause_one(self.host, ident, reason)
            if r.get('ok'): paused.append(ident); self.states[ident] = 'PAUSED'
            else: self.last_error[ident] = (r.get('error') or {}).get('message', 'not paused')
        self.active = []; self.timer.stop(); self.refresh(); return paused

    def release_all(self, reason=RELEASED_WORDS):
        """AGENT-02, closing Ledger with the setting on while the Ledger service runs: everything this window drives (and every
        RUNNING one) is handed to the service with agent.release; one that cannot be handed over is paused as before."""
        ids = list(self.active)
        for row in summaries(self.host):
            if row.get('state') == 'RUNNING' and row['id'] not in ids: ids.append(row['id'])
        released = []
        for ident in ids:
            r = release_one(self.host, ident)
            if r.get('ok'): released.append(ident); self.states[ident] = 'RUNNING'; continue
            self.last_error[ident] = (r.get('error') or {}).get('message', 'not handed over')
            p = pause_one(self.host, ident, 'Graphite closed')
            if p.get('ok'): self.states[ident] = 'PAUSED'
        self.handed = {'reason': str(reason), 'ids': released}
        self.active = []; self.timer.stop(); self.refresh(); return released

    def close_words(self):
        """What closing this window does with running work: 'release' (the service continues) or 'pause' (as AGENT-01)."""
        return 'release' if hosted(self.host) and continue_setting(self.host) else 'pause'

    def adopt(self):
        """AGENT-02: a window that talks to the Ledger service takes running work back (the desktop has priority): every RUNNING
        assignment no desktop lease holds is driven here from the next tick, whose step takes the lease. Nothing in a window
        with its own in-process Kernel (no service has been stepping anything there). Returns the ids taken.
        A live desktop lease is skipped: another window is driving it, or a window that ended without handing it over (a
        crash) left its lease behind. Adopt then looks again when the earliest such lease runs out (at most ADOPT_AGAIN times),
        so the reopened window takes the work back itself instead of leaving it to the Ledger service."""
        self.adopt_wait = None
        if getattr(self.host, '_closing', False) or not hosted(self.host): return []
        taken = []; leases = []
        for row in summaries(self.host):
            if row.get('state') != 'RUNNING' or row['id'] in self.active: continue
            if row.get('driver') == 'desktop' and row.get('lease_live'):   # another window, or a crashed one's lease
                leases.append(row.get('lease_until')); continue
            self.start(row['id']); taken.append(row['id'])
        if leases and self.adopt_tries < ADOPT_AGAIN:
            self.adopt_tries += 1; self.adopt_wait = adopt_delay(leases)
            QTimer.singleShot(self.adopt_wait, self, self.adopt)
        return taken

    def pause(self, ident, reason='Paused by you'):
        r = pause_one(self.host, ident, reason)
        if ident in self.active: self.active.remove(ident)
        if r.get('ok'): self.states[ident] = 'PAUSED'
        if not self.active: self.timer.stop()
        self.refresh(); return r

    def resume(self, ident):
        r = resume_one(self.host, ident)
        if r.get('ok'): self.start(ident)
        else: self.refresh()
        return r

    def stop(self, ident, reason='Stop'):
        r = stop_one(self.host, ident, reason)
        if ident in self.active: self.active.remove(ident)
        if r.get('ok'): self.states[ident] = 'STOPPED'
        if not self.active: self.timer.stop()
        self.refresh(); return r

    def refresh(self):
        for block in list(self.blocks):
            try: block.refresh()
            except RuntimeError: self.blocks.remove(block)   # the widget is gone


def adopt_delay(leases, now=None):
    """Milliseconds until the earliest skipped desktop lease has run out, plus one driver tick; LEASE_MS + ADOPT_MS when no
    row says when its lease ends. Never less than one tick nor more than LEASE_MS + ADOPT_MS."""
    now = time.time() if now is None else now
    ends = [float(v) for v in leases if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not ends: return LEASE_MS + ADOPT_MS
    return int(min(max(TICK_MS, (min(ends) - now) * 1000 + TICK_MS), LEASE_MS + ADOPT_MS))


def install(host):
    if getattr(host, 'agent_driver', None) is None:
        host.agent_driver = AgentDriver(host)
        QTimer.singleShot(ADOPT_MS, host.agent_driver, host.agent_driver.adopt)   # AGENT-02: reopening Ledger takes the work back
    return host.agent_driver


# -- the page follows Slate's edits -------------------------------------------------------------------------------------------

def document_tabs(host):
    tabs = getattr(host, 'tabs', None)
    if tabs is None: return []
    return [tabs.widget(i) for i in range(tabs.count()) if hasattr(tabs.widget(i), 'sync') and getattr(tabs.widget(i), 'document_id', None)]


def sync_pages(host, assignment=None):
    """After a step: an open page whose document the assignment works on shows the saved revision (an appended paragraph
    lands through the page's undo stack, owner decision 4)."""
    context = (assignment or {}).get('context') if isinstance((assignment or {}).get('context'), dict) else {}
    wanted = context.get('document') if context else None
    for tab in document_tabs(host):
        if wanted and tab.document_id != wanted: continue
        try: tab.sync()
        except RuntimeError: continue


# -- the assignment route from the typing strip ----------------------------------------------------------------------------

def assign_from_page(host, tab, text):
    """A request a profile fits, typed while a document is open, becomes an assignment on that document and the driver
    starts it; the answer is Slate's sentence. None when no profile fits (the model path is next) or no page is open.
    AGENT-02 (WI-C): a profile whose needs do not include 'document' (files_about: “find files about pellets”) takes the
    request with no page open, or on any tab, with context {}; a profile that needs the page (numbers_on_page) still does."""
    document = getattr(tab, 'document_id', None)
    if not text or not str(text).strip(): return None
    try:
        from . import agent_loop
        profile = agent_loop.request_profile(text)
    except NotImplementedError: return None      # WI-A not landed yet: the request goes on to the model path
    except Exception: return None
    if not profile: return None
    known = getattr(agent_loop, 'REGISTRY', {}).get(profile)
    page = 'document' in tuple(getattr(known, 'needs', ('document',)) if known is not None else ('document',))   # unknown: as before, a page
    if page and not document: return None
    if profile not in getattr(agent_loop, 'PROFILES', ()): profile = 'auto'
    if page and hasattr(tab, 'flush'):
        try: tab.flush()                           # the page is saved first, so the assignment reads the owner's words
        except Exception: pass
    r = call_write(host, 'agent.assign', {'request': str(text)[:2000], 'profile': profile, 'context': {'document': document} if page else {}})
    if not r.get('ok'): return 'I could not take that on: ' + (r.get('error') or {}).get('message', 'the assignment was refused')
    assignment = (r.get('result') or {}).get('assignment') or {}; ident = assignment.get('id')
    if assignment.get('state') == 'WAITING' and assignment.get('reason'): return 'I cannot start that yet: ' + str(assignment['reason'])
    driver = getattr(host, 'agent_driver', None)
    if driver is not None and ident: driver.start(ident)
    return WORKING_ANSWER % (assignment.get('request') or str(text).strip())


# -- Today -------------------------------------------------------------------------------------------------------------------

def resume_from_today(host, ident):
    driver = getattr(host, 'agent_driver', None)
    r = driver.resume(ident) if driver is not None else resume_one(host, ident)
    if not r.get('ok'):
        if hasattr(host, 'statusBar'): host.statusBar().showMessage('Could not resume: ' + (r.get('error') or {}).get('message', ''), 8000)
        return r
    row = status(host, ident) or {}
    document = next((i.get('id') for i in (row.get('inspect') or []) if isinstance(i, dict) and i.get('kind') == 'document'), None)
    if document: open_destination(host, 'documents:' + document)
    shell = getattr(host, 'shell2', None)
    if shell is not None and hasattr(shell, 'show_slate_face'): shell.show_slate_face()
    return r


def closed_words(row):
    """AGENT-02: what the Ledger service did while Ledger was closed, or None (no service steps, or not in the last 24 hours).
    A paused one says why, as AGENT-01's paused row does (“Master Stop”, “The Ledger service stopped”)."""
    steps = int(row.get('service_steps') or 0)
    if steps <= 0 or time.time() - float(row.get('updated') or 0) > CLOSED_WINDOW: return None
    request = row.get('request') or row.get('working_on') or 'an assignment'; state = row.get('state') or ''
    words = 'While Graphite was closed, it took %d step%s on “%s” · now %s' % (steps, '' if steps == 1 else 's', str(request)[:80],
                                                                               STATE_WORDS.get(state, state.lower()))
    reason = (row.get('paused_reason') or row.get('reason') or '') if state == 'PAUSED' else ''
    return words + (' (' + str(reason)[:120] + ')' if reason else '')


def today_rows(host):
    """(text, where, fn) rows for Today's Waiting card: paused assignments with a resume word, and ones that need you. AGENT-02:
    an assignment the Ledger service stepped in the last 24 hours says so instead, with inspect (resume when it waits or is
    paused)."""
    out = []
    for row in summaries(host):
        request = row.get('request') or row.get('working_on') or 'an assignment'
        words = closed_words(row)
        if words:
            if row.get('state') in ('PAUSED', 'WAITING'): out.append((words, 'resume', lambda *_, i=row['id']: resume_from_today(host, i)))
            else: out.append((words, 'inspect', lambda *_, i=row['id']: inspect_assignment(host, i)))
            continue
        if row.get('state') == 'PAUSED':
            reason = row.get('paused_reason') or row.get('reason') or ''
            out.append(('Graphite paused: ' + str(request)[:80] + (' (' + str(reason) + ')' if reason else ''), 'resume', lambda *_, i=row['id']: resume_from_today(host, i)))
        elif row.get('state') == 'WAITING':
            out.append(('Graphite needs you: ' + str(request)[:80], 'assignment', lambda *_, i=row['id']: inspect_assignment(host, i)))
    return out


def inspect_assignment(host, ident):
    row = status(host, ident) or {}
    investigation = row.get('investigation') or next((i.get('id') for i in (row.get('inspect') or []) if isinstance(i, dict) and i.get('kind') == 'investigation'), None)
    if investigation:
        from .investigations_qt import show
        return show(host, investigation)
    return open_destination(host, 'investigations')


# -- the Work block ----------------------------------------------------------------------------------------------------------

class WorkBlock(QWidget):
    """Working on · Doing now · Found · Needs you · Inspect, from agent.status; Stop, Pause, Resume and Inspect are words."""
    KEYS = (('working_on', 'Working on'), ('doing_now', 'Doing now'), ('found', 'Found'), ('needs_you', 'Needs you'), ('inspect', 'Inspect'))

    def __init__(self, host):
        super().__init__(); self.host = host; self.setObjectName('WorkBlock'); self.current = None; self.stale = []; self.seen = None
        box = QVBoxLayout(self); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(3)
        self.head = role(QLabel('WORK'), 'section'); box.addWidget(self.head)
        self.lines = {}
        for key, name in self.KEYS:
            label = role(QLabel(), 'quiet'); label.setWordWrap(True); label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            label.setAccessibleName('Work · ' + name); box.addWidget(label); self.lines[key] = label
        self.timer = QTimer(self); self.timer.setInterval(BLOCK_MS); self.timer.timeout.connect(self.refresh); self.timer.start()
        driver = getattr(host, 'agent_driver', None)
        if driver is not None and self not in driver.blocks: driver.blocks.append(self)
        self.hide()

    def refresh(self):
        if getattr(self.host, '_closing', False): return None
        parent = self.parentWidget()
        if parent is not None and not parent.isVisible() and self.current is None and not self.timer.isActive(): return None
        rows = summaries(self.host)
        if not rows: self.current = None; self.hide(); return None
        driver = getattr(self.host, 'agent_driver', None); active = set(driver.running()) if driver is not None else set()
        rows.sort(key=lambda r: (r['id'] in active, r.get('updated') or 0), reverse=True)
        row = status(self.host, rows[0]['id']) or rows[0]
        moved = self.seen != (row.get('id'), row.get('updated'), row.get('state'))
        self.seen = (row.get('id'), row.get('updated'), row.get('state')); self.current = row
        self.render(row); self.show()
        if moved and driver is not None and row.get('id') not in active: sync_pages(self.host, row)   # a step ran elsewhere (agent.run)
        return row

    def render(self, row):
        state = row.get('state') or ''; ident = row.get('id'); word = STATE_WORDS.get(state, state.lower())
        driver = getattr(self.host, 'agent_driver', None); error = (driver.last_error.get(ident) if driver is not None else None)
        sentence('<b>Working on</b> · ' + escape_text(row.get('working_on') or row.get('request') or '') + ' · ' + escape_text(word), {}, self.lines['working_on'])
        doing = row.get('doing_now') or row.get('reason') or ('finished' if state == 'DONE' else '')
        if service_holds(row): doing = IN_SERVICE + doing   # AGENT-02: the Ledger service is stepping it, not this window
        if error: doing = (doing + ' · ' if doing else '') + 'the driver stopped: ' + error
        sentence('<b>Doing now</b> · ' + escape_text(doing or '—'), {}, self.lines['doing_now'])
        found = [words_of(f) for f in (row.get('found') or [])]
        shown = found if len(found) <= 3 else [found[-1], 'and %d more on the investigation sheet' % (len(found) - 1)]   # AGENT-02: one finding per file would fill the column
        sentence('<b>Found</b> · ' + (escape_text(' · '.join(shown)) if found else 'nothing yet'), {}, self.lines['found'])
        needs = [words_of(n) for n in (row.get('needs_you') or [])]
        if state == 'WAITING' and row.get('reason') and row['reason'] not in needs: needs.append(row['reason'])
        actions = {}; parts = [escape_text(n) for n in needs if n]
        self.stale = stale_conditions(self.host, row)
        for i, card in enumerate(self.stale):
            key = 'recheck%d' % i; actions[key] = ('recheck', lambda c=card['id']: recheck(self.host, c))
            parts.append(('A result on the page is stale' if card.get('state') == 'STALE' else 'A result paragraph on the page was removed') + ' · {%s}' % key)
        sentence('<b>Needs you</b> · ' + (' · '.join(parts) if parts else 'nothing'), actions, self.lines['needs_you'])
        words = {}; pieces = []
        for i, item in enumerate(row.get('inspect') or []):
            if not isinstance(item, dict) or not item.get('id'): continue
            key = 'i%d' % i; words[key] = (item.get('label') or item.get('kind') or 'record', lambda it=item: self.inspect(it)); pieces.append('{%s}' % key)
        if not pieces and row.get('investigation'):
            words['inv'] = ('investigation', lambda it={'kind': 'investigation', 'id': row['investigation']}: self.inspect(it)); pieces.append('{inv}')
        controls = []
        if state in ACTIVE: controls = [('stop', 'Stop'), ('pause', 'Pause')]
        elif state == 'PAUSED': controls = [('resume', 'Resume'), ('stop', 'Stop')]
        elif state == 'WAITING': controls = [('stop', 'Stop')]
        for key, label in controls: words[key] = (label, lambda k=key, i=ident: self.control(k, i)); pieces.append('{%s}' % key)
        sentence('<b>Inspect</b> · ' + (' · '.join(pieces) if pieces else '—'), words, self.lines['inspect'])

    def control(self, key, ident):
        driver = getattr(self.host, 'agent_driver', None)
        if driver is None: driver = install(self.host)
        if key == 'stop': r = driver.stop(ident, 'Stop')
        elif key == 'pause': r = driver.pause(ident, 'Paused by you')
        else: r = driver.resume(ident)
        if not r.get('ok') and hasattr(self.host, 'statusBar'): self.host.statusBar().showMessage((r.get('error') or {}).get('message', 'Not done'), 6000)
        self.refresh(); return r

    def inspect(self, item):
        kind = item.get('kind'); ident = item.get('id')
        if kind == 'investigation':
            from .investigations_qt import show
            return show(self.host, ident)
        if kind == 'document': return open_destination(self.host, 'documents:' + ident)
        if kind == 'condition':
            card = (call(self.host, 'conditions.get', {'id': ident}) or {}).get('condition') or {}
            if hasattr(self.host, 'statusBar'):
                result = card.get('result') or {}
                self.host.statusBar().showMessage('Condition card · %s · %s' % (card.get('state', '?'), result.get('text') or ''), 10000)
            if card.get('document'): return open_destination(self.host, 'documents:' + card['document'])
            return None
        return open_destination(self.host, 'investigations')


def stale_conditions(host, row):
    """The condition cards an assignment points at that no longer hold (STALE or BROKEN); [] when none can be read."""
    out = []
    for item in (row or {}).get('inspect') or []:
        if not isinstance(item, dict) or item.get('kind') != 'condition' or not item.get('id'): continue
        card = (call(host, 'conditions.get', {'id': item['id']}) or {}).get('condition') or {}
        if card.get('state') in ('STALE', 'BROKEN'): out.append({'id': item['id'], 'state': card['state'], 'document': card.get('document')})
        if len(out) >= 5: break
    return out


def recheck(host, ident):
    """The recheck word in the right column: the page that shows the document does the recheck (its undo stack); else the Kernel alone."""
    for tab in document_tabs(host):
        if hasattr(tab, 'recheck') and ident in (getattr(tab, 'stale_ids', None) or []): return tab.recheck([ident])
    r = call_write(host, 'conditions.recheck', {'id': ident})
    if hasattr(host, 'statusBar'):
        host.statusBar().showMessage(('Rechecked · ' + str((r.get('result') or {}).get('words') or '')) if r.get('ok') else 'Not rechecked: ' + (r.get('error') or {}).get('message', ''), 8000)
    if r.get('ok'): sync_pages(host)
    return r


# -- the Related block ---------------------------------------------------------------------------------------------------------

class RelatedBlock(QWidget):
    """Up to five of the owner's own records that share the page's words, as words to select; a dismiss mark per row."""

    def __init__(self, host):
        super().__init__(); self.host = host; self.setObjectName('RelatedBlock'); self.key = None; self.rows = []; self.searched = {}; self._state = {}
        box = QVBoxLayout(self); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(3)
        self.head = role(QLabel('RELATED'), 'section'); self.head.setToolTip('Your own records that share this page’s words · word match, no model'); box.addWidget(self.head)
        self.list = QVBoxLayout(); self.list.setContentsMargins(0, 0, 0, 0); self.list.setSpacing(3); box.addLayout(self.list)
        self.timer = QTimer(self); self.timer.setInterval(RELATED_MS); self.timer.timeout.connect(self.poll); self.timer.start()
        self.hide()

    # the page --------------------------------------------------------------------------------------------------------------
    def page(self):
        host = self.host
        if getattr(host, '_home_active', False) or getattr(host, '_closing', False): return None
        tabs = getattr(host, 'tabs', None); tab = tabs.currentWidget() if tabs is not None else None
        return tab if tab is not None and hasattr(tab, 'related_text') and getattr(tab, 'document_id', None) else None

    def poll(self):
        tab = self.page()
        if tab is None:
            if self.key is not None: self.key = None; self.set_rows([])
            return None
        try: text = tab.related_text()
        except RuntimeError: return None
        key = (tab.document_id, hash(text))
        if key == self.key: return None
        self.key = key; return self.query(text, tab.document_id)

    refresh = poll

    def query(self, text, document=None):
        text = str(text or '')
        if len(text.split()) < 2: self.set_rows([]); return []
        value = call(self.host, 'ledger.related', {'text': text[:40000], 'limit': 10, **({'exclude': ['document:' + document]} if document else {})})
        rows = [r for r in ((value or {}).get('related') or []) if isinstance(r, dict) and r.get('id')]
        self.searched = (value or {}).get('searched') or {}
        self.set_rows(rows); return rows

    # dismissed ids ---------------------------------------------------------------------------------------------------------
    def state(self):
        session = getattr(self.host, 'session', None); state = getattr(session, 'state', None)
        return state if isinstance(state, dict) else self._state

    def dismissed(self):
        ids = self.state().get('related_dismissed')
        return [i for i in ids if isinstance(i, str)] if isinstance(ids, list) else []

    def dismiss(self, ident):
        ids = [i for i in self.dismissed() if i != ident] + [ident]
        self.state()['related_dismissed'] = ids[-DISMISSED_KEEP:]
        session = getattr(self.host, 'session', None)
        if session is not None and hasattr(session, 'save'):
            try: session.save()
            except (OSError, ValueError, TypeError): pass
        self.render(); return ids

    def visible_rows(self, rows=None):
        gone = set(self.dismissed())
        return [r for r in (self.rows if rows is None else rows) if r['id'] not in gone][:RELATED_LIMIT]

    # drawing ----------------------------------------------------------------------------------------------------------------
    def set_rows(self, rows):
        self.rows = list(rows or []); self.render()

    def render(self):
        while self.list.count():
            item = self.list.takeAt(0)
            if item.widget() is not None: item.widget().deleteLater()
        shown = self.visible_rows()
        if not shown: self.hide(); return []
        for row in shown:
            note = str(row.get('kind') or '') + (' · ' + ', '.join(str(w) for w in (row.get('words') or [])[:3]) if row.get('words') else '')
            label = sentence('{open} <span style="color:%s">· %s</span>  {dismiss}' % (QUIET, escape_text(note)),
                             {'open': (str(row.get('label') or row['id']), lambda r=row: self.open(r)), 'dismiss': ('×', lambda i=row['id']: self.dismiss(i))})
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred); label.setAccessibleName('Related · ' + str(row.get('label') or row['id'])); self.list.addWidget(label)
        self.show(); return shown

    def open(self, row):
        """A document opens; anything else is selected and revealed in the cabinet, so the owner stays on the page."""
        host = self.host; ident = row['id']; route = row.get('open') or ''
        if row.get('kind') == 'document' or route.startswith('documents:'): return open_destination(host, route or ('documents:' + ident.split(':', 1)[1]))
        navigation = getattr(host, 'navigation_controller', None); page = getattr(host, 'cabinet_page', None); found = False
        try:
            if navigation is not None: found = bool(navigation.reveal_record(ident, refresh=True))
            elif page is not None: page.select(ident, reveal=True); found = ident in getattr(page, 'items', {})
        except (RuntimeError, AttributeError, KeyError): found = False
        if found:
            if hasattr(host, 'statusBar'): host.statusBar().showMessage('Selected in the cabinet: ' + str(row.get('label') or ident), 6000)
            return page
        if route: return open_destination(host, route)
        return None
