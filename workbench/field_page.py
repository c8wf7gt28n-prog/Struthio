"""The Field in the window: the overview page of the centre, and the way in and out of it.

    show_field(host)     put the Field in front of the workspace (F9, Arrange ▸ Field, or type "field" in the writing line)
                         its faces: W the work, P the programs (every program and room, as a shelf), N this computer's network
    open_on_work(host)   at launch: the Field first when the workspace has work, unless the owner chose "always Home"
    leave_field(host)    put the workspace back; every room opener reaches this through the window's _close_start()
    open_object(host, obj)   open the real editor for one sheet of the Field, through the room's own opener

The Field overlays the workspace as Home does and releases nothing: tabs, unsaved text and the docks stay as they were,
and Esc gives the keyboard back to whatever had it. It reads the workspace through Kernel.dispatch
(workbench/field_source.py) every time it is brought to the front: a sheet's state can change because a file changed on
disk, which no record of Graphite's notices, so a kept reading would lie. F9 while it is already in front reads nothing;
R reads again and asks once more for the records that could not be read.
Master specification, section 72: "A simple Open or Back action can accompany the transition."
"""
import re

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QApplication, QSizePolicy, QVBoxLayout, QWidget

from .field_model import Field
from .field_qt import FieldView
from .field_source import problems, read_field, read_network, read_programs

FACES = (('work', 'w'), ('programs', 'p'), ('network', 'n'))     # the programs face is shown as APPS (0.8.1; field_qt.FACE_WORDS)     # the faces of the Field and the key that shows each


class FieldPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName('FieldPage');self.setProperty('paperFunctionalInk', True)
        # Ignored both ways: the centre's stack takes the largest minimum of all its pages, and this one must never widen it.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout = QVBoxLayout(self);layout.setContentsMargins(0, 0, 0, 0);layout.setSpacing(0)
        self.view = FieldView(self);self.view.setMinimumSize(0, 0);self.view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.view)
        # The desk is seen as it was last seen: its size, or the whole of it. (The specification's "remember the view".)
        state = getattr(getattr(host, 'session', None), 'state', None)
        seen = state.get('field_zoom') if isinstance(state, dict) else None
        if seen:
            self.view.zoom = max(FieldView.ZOOM[0], min(FieldView.ZOOM[1], float(seen['zoom'])));self.view._fitted = bool(seen['whole']);self.view.auto_fit = False
        self._keep = QTimer(self);self._keep.setSingleShot(True);self._keep.setInterval(900)       # one write after the wheel has stopped turning
        self._keep.timeout.connect(lambda: self.host.session.save())

        def kept(zoom, whole):
            if isinstance(state, dict):
                state['field_zoom'] = {'zoom': round(float(zoom), 3), 'whole': bool(whole)};self._keep.start()
        self.view.on_zoom = kept

        def calm():      # the profile's "reduce motion": the desk then changes size at once
            from .document_qt import profile_of
            return bool(profile_of(self.host).get('reduce_motion'))
        self.view.still = calm
        self.view.opened.connect(lambda obj: open_object(self.host, obj))
        self.view.left.connect(lambda: back(self.host))
        self.view.face_chosen.connect(self.show_face)
        self.view.look_again.connect(lambda: self.refresh(force=True))
        self.view.stac_line.connect(lambda obj: stac_in_line(self.host, obj))
        self.view.stac_run.connect(lambda obj: stac_run(self.host, obj))
        self.view.do_asked.connect(lambda obj: do(self.host, obj))
        self.view.step_chosen.connect(lambda obj, n: take(self.host, obj, n))
        self.view.check_asked.connect(lambda: check_desk(self.host))
        self.view.go_asked.connect(lambda: go(self.host))
        self.view.trace_asked.connect(lambda obj: trace(self.host, obj))
        self.view.doubt_asked.connect(lambda obj: doubt(self.host, obj))
        self.view.brief_asked.connect(lambda: brief(self.host))
        self.view.reading_closed.connect(self._reading_closed)
        self.view.menu_asked.connect(self._menu)
        self.view.full_asked.connect(lambda obj: full_window(self.host, obj))
        self.steps = ();self.steps_of = ''      # the steps last offered, and the object they were offered for
        self.pending = None                     # what G runs: the Run of what waits in Talk for the owner's go
        self.star = None                        # what step 1 does when the steps are the desk's own (settle what can be settled)
        self.view.faces = FACES;self.face = self.view.face = 'work'
        self.problem = ''            # what the last reading could not read, in words
        self.unread = set()          # records that refused: not asked again until the owner looks again
        QApplication.instance().focusChanged.connect(self._keyboard_moved)

    def _menu(self):
        """A click on "Menu" at the foot: the selected sheet's own menu, as the Menu key and the right button open it."""
        from . import context_menu
        self.view.setFocus(Qt.OtherFocusReason)
        context_menu.open_at_focus(self.host)

    def _reading_closed(self):
        """The owner closed the page being read (Esc): what waited on it for a go is withdrawn from the keyboard too."""
        self.pending = None

    def _keyboard_moved(self, old, now):
        """While the Field is in front the keyboard is never left nowhere: when the writing strip (or anything else) gives it up
        without handing it on, it comes back to the Field, so the next arrow moves and Esc goes back."""
        try:
            if now is None and getattr(self.host, '_field_active', False) and self.view.isVisible() and self.host.isActiveWindow():
                self.view.setFocus(Qt.OtherFocusReason)
        except RuntimeError:         # the window is going away
            pass

    def minimumSizeHint(self):
        return QSize(0, 0)

    def sizeHint(self):
        return QSize(0, 0)

    def show_face(self, name):
        if name in dict(FACES) and name != self.face:
            self.face = self.view.face = name
            self.view.field.selected = ''          # another face holds other objects: start where that face starts
            self.refresh(force=True)

    def refresh(self, force=False, reading=None):
        """Read the workspace. `force` (R) also asks again for the records that could not be read last time. A reading that
        could not reach the records says so on the surface and in the status line; it never shows an empty workspace instead.
        `reading` is a (field, reader) pair just read by the caller (the launch), shown instead of reading twice."""
        host = self.host
        from .locations import program
        self.view.art_mode = host.session.state.get('desk_art', 'illustrated')     # Arrange ▸ Desk art: Illustrated, ASCII or Clean
        self.view.art_folder = program(host.root) / 'branding' / 'boss'
        self.view.texture = self.view.art_mode != 'clean'
        kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:
            self.problem = self.view.problem = 'Graphite\'s records are not available in this window'
            self.view.set_field(Field())
            host.statusBar().showMessage('Field · ' + self.problem, 9000);return
        from .engineering_kernel import operator
        principal = operator()
        if self.face == 'network':
            field, reader = read_network(kernel, principal)
        elif self.face == 'programs':      # the shelf: every program and room, each marked "in use" when its room is open
            field, reader = read_programs(kernel, principal, {type(host.tabs.widget(i)).__name__ for i in range(host.tabs.count())})
        else:
            if force:self.unread = set()
            field, reader = reading if reading is not None else read_field(kernel, principal, title='', skip=self.unread)
            self.unread |= set(reader.unread)
            if not field.title:field.title = host.root.name
        self.problem = self.view.problem = problems(reader)
        self.view.set_field(field)
        if self.problem:host.statusBar().showMessage('Field · ' + self.problem + ' · R looks again', 9000)
        elif host.statusBar().currentMessage().startswith('Field · '):host.statusBar().clearMessage()      # an earlier trouble that is over is no longer said


def open_on_work(host):
    """At launch Graphite opens on the work: the Field in front when this workspace has anything to show. An empty workspace,
    or one whose records cannot be reached, stays where the launch left it (Home, or the page that was open); F9 is still
    there. Esc from this first Field goes back to that place, so "where I left off" is one key away."""
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or getattr(host, '_field_active', False):
        return None
    from .engineering_kernel import operator
    try:
        reading = read_field(kernel, operator(), title='')
    except Exception:  # noqa: BLE001 - a launch never fails because the overview could not be read
        return None
    if not reading[0].objects:
        return None
    return show_field(host, reading=reading)


def show_field(host, reading=None):
    """Bring the Field to the front. Coming from Home, Home is closed first so its folded panels return once. Asked for while
    it is already in front, it only takes the keyboard: nothing is read again and where the owner came from is kept."""
    page = getattr(host, 'field_page', None)
    if getattr(host, '_field_active', False) and page is not None:
        page.view.setFocus(Qt.OtherFocusReason);return page
    from_home = bool(getattr(host, '_home_active', False))
    focus = QApplication.focusWidget()
    if from_home:
        host._close_start()
    if page is None:
        page = host.field_page = FieldPage(host)
        host.central_stack.addWidget(page)
    host._field_active = True;host._field_from_home = from_home
    host._field_focus = focus if focus is not None and focus is not page.view else None
    host.central_stack.setCurrentWidget(page)
    # The Field has the whole centre: the bars that belong to the work step aside and come back exactly as they were.
    bars = [getattr(getattr(host, 'concern', None), 'context_strip', None), host.workspace_status, host.context_bar, host.doc_info]
    host._field_bars = [(bar, bar.isVisible()) for bar in bars if bar is not None]
    for bar, _ in host._field_bars:bar.hide()
    page.refresh(reading=reading)
    host.setWindowTitle('Field — Graphite')
    page.view.setFocus(Qt.OtherFocusReason)
    return page


def leave_field(host):
    """Put the workspace back in the centre. Safe to call when the Field is not showing."""
    if not getattr(host, '_field_active', False):
        return
    host._field_active = False
    host.central_stack.setCurrentWidget(host.workspace_split)
    for bar, shown in getattr(host, '_field_bars', ()):
        try:bar.setVisible(shown)
        except RuntimeError:pass
    host._field_bars = []
    host.update_document_info()


def back(host):
    """Esc: back to where the owner came from, Home or the work, with the keyboard where it was."""
    from_home = bool(getattr(host, '_field_from_home', False))
    focus = getattr(host, '_field_focus', None);host._field_focus = None
    leave_field(host)
    if from_home or host.tabs.count() == 0:
        host.show_start();return
    try:
        alive = focus is not None and focus.isVisible() and focus.window() is host
    except RuntimeError:             # the widget that had the keyboard is gone
        alive = False
    if alive:
        focus.setFocus(Qt.OtherFocusReason)
    elif host.tabs.currentWidget() is not None:
        tab = host.tabs.currentWidget()
        (tab.focusProxy() or tab).setFocus(Qt.OtherFocusReason)


def thing_of(host, obj):
    """One sheet as Stacy is told about it when the owner asks: its staC line, what the Field shows of it, and what its
    wires say feeds it and what it feeds. All of it is read from the records already; nothing is guessed."""
    field = host.field_page.view.field
    name = {o.id: o for o in field.objects}
    say = lambda o: '%s “%s”%s' % (o.kind, o.title, ' (%s)' % o.state if o.state else '')
    return {'title': obj.title, 'stac': obj.stac, 'kind': obj.kind, 'state': obj.state, 'lines': [str(line) for line in obj.lines],
            'fed_by': [say(name[l.source]) for l in field.links if l.target == obj.id and l.source in name],
            'feeds': [say(name[l.target]) for l in field.links if l.source == obj.id and l.target in name]}


def _talk(host):
    """Stacy's pane, brought to the front of the right column; the keyboard stays in the Field."""
    shell = getattr(host, 'shell2', None)
    if shell is None:return None
    face = shell.show_slate_face()
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):page.view.setFocus(Qt.OtherFocusReason)
    return face


def _waits(host, step):
    """Whether a step that changes something would wait for the owner's Approve, with Stacy's hand where it is now."""
    from . import stacy_hand
    from .field_do import call
    if step.more:return True                     # several changes for one go: they are put up together and wait
    try:operation, arguments = call(step.line)
    except Exception:  # noqa: BLE001 - a line that cannot be read waits
        return True
    return not stacy_hand.hers(stacy_hand.level(host), step.scope, operation, arguments)


def _shown_kind(host, step):
    """How a step is shown: 'read'; 'write', it changes something and waits for the owner; or 'does', it changes something
    and, with Stacy's hand where it is, she does it at once."""
    return step.kind if step.kind != 'write' or _waits(host, step) else 'does'


def _await_go(host, words, run):
    """Something waits in Talk for the owner's go. From the keyboard the go is G, and only G: a digit chooses a step and never
    approves one. The Field says what G would run for as long as it would; moving to another sheet, or Esc, withdraws it from
    the keyboard (the Run in Talk stays)."""
    page = host.field_page
    page.pending = run;page.view.go = words;page.view.update()


def go(host):
    """G: the owner's go for what waits."""
    page = host.field_page
    run, page.pending = page.pending, None
    page.view.go = '';page.view.update()
    if run is not None:run()
    if getattr(host, '_field_active', False):page.view.setFocus(Qt.OtherFocusReason)


def do(host, obj):
    """D: ask the records what can be done about this sheet. The steps show in the Field, numbered, and Stacy says them in
    Talk. Nothing runs by being offered."""
    from .engineering_kernel import operator
    from .field_do import steps_for
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or obj is None:return ()
    steps = steps_for(kernel, operator(), obj, page.view.field)
    page.steps = tuple(steps);page.steps_of = obj.id
    page.view.steps = tuple((step.words, _shown_kind(host, step)) for step in steps);page.view.update()
    face = _talk(host)
    if face is not None and steps:face.say_steps(obj.title, steps, lambda n, line=None, obj=obj:take(host, obj, n, line))
    if not steps:host.statusBar().showMessage('Field · the records offer nothing to do about %s' % obj.title, 6000)
    if steps:
        # The steps, where the eyes are and where the pointer can reach them: a light page whose rows are the steps. A click on
        # a row, or its digit, takes it; the page steps aside at any other key. A step that changes something says it waits.
        name = obj.title if len(obj.title) <= 56 else obj.title[:55].rstrip() + '…'
        rows = [('k', '%d\t%s%s%s' % (n + 1, step.words, ' · waits for your Approve' if step.kind == 'write' and _waits(host, step) else '', (' — ' + step.why) if step.why else '')) for n, step in enumerate(steps)]
        page.view.show_reading('What can be done about “%s”' % name, rows, '1 – %d  take a step      Esc  close      any other key moves on' % len(steps) if len(steps) > 1 else '1  take the step      Esc  close',
                               light=True)
        page.view.steps = tuple((step.words, _shown_kind(host, step)) for step in steps)       # showing the page does not withdraw what was just offered
        page.view.setFocus(Qt.OtherFocusReason)
    return page.steps


def take(host, obj, n, line=None):
    """Take one of the steps offered for this sheet. A read runs at once and Stacy shows its line and what the records
    answered. A step that changes something is put in Talk with its exact line and waits for the owner's Run; when it has
    run, the Field reads the records again."""
    page = host.field_page
    if page.steps_of == '*':                   # the desk's own step: it shows what it would change and asks; it runs nothing
        star, page.star = page.star, None
        page.steps = ();page.steps_of = '';page.view.steps = ();page.view.update()
        if n == 0 and star is not None:star()
        page.view.setFocus(Qt.OtherFocusReason)
        return None
    if obj is None or page.steps_of != obj.id or not 0 <= n < len(page.steps):return None
    if line is not None and page.steps[n].line != line:      # a word on an older list: that number is another step now, so nothing is taken
        face = _talk(host)
        if face is not None:face.say('That list is from before, and its steps have changed. Here they are as they stand now.')
        do(host, obj);return None
    if page.view.reading is not None and page.view.reading.get('light'):page.view.close_reading()      # the page that offered the steps has done its work
    step = page.steps[n];face = _talk(host)
    if face is None:return None
    if step.kind == 'read':
        card = face.answer_in_stac({'title': obj.title, 'stac': step.line, 'kind': obj.kind}, '%s, for “%s”:' % (step.words, obj.title))
    elif step.more:                            # a step that is several changes: put up together, named, for one go
        from .field_do import Step
        parts = [(obj, Step(getattr(step, 'words_first', step.words), 'write', step.line))] + [(obj, Step(words, 'write', line)) for words, line in step.more]
        done = lambda results, obj=obj:_after(host, obj, any(ok for _, ok, _ in results), None)
        card = face.say_plan(parts, done=done, title='For “%s”: %s. That is %d changes.' % (obj.title, step.words[:1].lower() + step.words[1:], len(parts)))
        _await_go(host, 'all %d changes, as listed in Talk' % len(parts), lambda:face.run_plan(card, done))
    else:
        done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
        card = face.stage(obj.title, step, done=done, asked=True, word='the step you took from my list')      # taking the step is the owner's word
        if card.ran is None:_await_go(host, step.words[:1].lower() + step.words[1:], lambda:face.run_staged(card, done))
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def _after(host, obj, ok, result):
    """A step changed something: the Field reads the records again. A page that took the place of the selected one (a
    calculation brought up to date) is the one selected now."""
    page = host.field_page;page.steps = ();page.steps_of = '';page.pending = None
    if not ok:
        page.view.steps = ();page.view.update();return
    page.refresh(force=True)
    made = (result or {}).get('document') if isinstance(result, dict) else None
    for ident in (('document:' + str(made.get('id'))) if isinstance(made, dict) and made.get('id') else '', obj.id):
        if ident and page.view.field.get(ident) is not None:
            page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe();break
    page.view.update()
    QTimer.singleShot(0, lambda:notice(host))      # with a free hand she looks over the desk after a change (nothing happens on the other places)


def notice(host):
    """Free hand: "I kind of want her to be autonomous", noticing things (the owner, 13 November 2026). After a change made
    through her, Stacy checks the desk as C does and, for each thing that waits and has a step that brings it back to
    current without a decision of the owner's, takes that step herself: a calculation that stood on a changed number is
    worked again, a finding is compared with its changed source. She says what she noticed and what she did, each change
    is a line in her trail, and what needs the owner's judgment is left alone. One pass; on any other place of the dial,
    nothing."""
    from . import stacy_hand
    from .engineering_kernel import operator
    from .field_do import settling, sweep
    page = getattr(host, 'field_page', None);kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None);face = _talk(host)
    if page is None or kernel is None or face is None or stacy_hand.level(host) != 'free' or getattr(page, 'noticing', False):return None
    if page.face != 'work':return None
    page.noticing = True
    try:
        page.refresh(force=True)
        waiting, _ = sweep(kernel, operator(), page.view.field)
        plan = [(obj, step) for obj, step in settling(waiting) if not _waits(host, step)]
        if not plan:return None
        chosen = page.view.field.selected

        def done(results):
            # The Field reads again. A calculation worked again is a new page that takes the old one's place: if the old one
            # was selected, the new one is, so "this" still means the thing the owner was on.
            page.refresh(force=True)
            if chosen and page.view.field.get(chosen) is None:
                for (obj, _), (_, ok, result) in zip(plan, results):
                    made = result.get('document') if ok and isinstance(result, dict) else None
                    ident = 'document:' + str(made.get('id')) if isinstance(made, dict) and made.get('id') else ''
                    if obj.id == chosen and ident and page.view.field.get(ident) is not None:
                        page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe();break
            page.view.update()
        card = face.say_plan(plan, done=done, hers=True, word='what I noticed after the change',
                             title='I noticed %d thing%s that stood on what just changed.' % (len(plan), '' if len(plan) == 1 else 's'))
        face.run_plan(card, done)
        return card
    finally:
        page.noticing = False


THIS = re.compile(r'^(explain\s+)?this\b\s*(\|.*)?$', re.IGNORECASE | re.DOTALL)


def expand_this(host, text):
    """`this` at the start of a staC line is the sheet selected in the Field. Alone it is that sheet's own line; before a `|`
    it is the read that line starts with, so `this | pick … | select …` goes on from the same record the rail shows. The line
    is written out before it runs, so what ran is always visible. Text that does not start with `this` comes back unchanged;
    when there is nothing `this` could mean, ValueError says so in words."""
    found = THIS.match(str(text).strip())
    if not found:return text
    page = getattr(host, 'field_page', None);obj = page.view.selected() if page is not None else None
    if obj is None or not obj.stac:
        raise ValueError("“this” is the sheet selected in the Field, and nothing is selected there")
    lead = found.group(1) or '';rest = found.group(2)
    return lead + (obj.stac if rest is None else obj.stac.split(' | ', 1)[0] + ' ' + rest.strip())


def trace(host, obj):
    """T: where this comes from and what rests on it, hop by hop along the wires. Stacy reads it (field.trace, a staC line like
    any other) and shows the rows; with a model she then tells it in her own words."""
    from .field_do import js
    shell = getattr(host, 'shell2', None)
    if shell is None or obj is None:return None
    line = 'field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id)
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True,
                        'intro': 'Where “%s” comes from, farthest first, then what rests on it:' % obj.title}
    shell.ask('Where does “%s” come from, and what rests on it?' % obj.title)
    if getattr(host, '_field_active', False):host.field_page.view.setFocus(Qt.OtherFocusReason)


def doubt(host, obj):
    """X: cross-examine this for what a plausible result may hide. Exact questions are put to the records (field.doubt, a staC
    line like any other): what does not hold comes first, then what cannot be told, then what holds. With a model Stacy then
    says it in her own words. Nothing is changed."""
    from .field_do import js
    shell = getattr(host, 'shell2', None)
    if shell is None or obj is None:return None
    line = 'field.doubt %s | pick rows | select verdict,about,why' % js(id=obj.id)
    name = obj.title if len(obj.title) <= 44 else obj.title[:43].rstrip() + '…'
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True, 'whole': True, 'intro': 'Doubting “%s”, worst first:' % name}
    shell.ask('What could be wrong with “%s”?' % obj.title)
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):
        show_doubt(host, obj, line);page.view.setFocus(Qt.OtherFocusReason)


def show_doubt(host, obj, line):
    """The doubt, where the eyes are: over the work, at reading size, grouped by what was found. It is a light page: it
    steps aside at the next key that is not a reading key (an arrow moves on, D offers what can be done), and Esc closes
    it. Talk keeps the same answer as a card."""
    from .engineering_kernel import operator
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:return
    answer = kernel.dispatch('field.doubt', {'id': obj.id}, operator())
    if not answer.get('ok'):return
    rows = answer['result'].get('rows', ());sheet = []
    for verdict, heading in (('doubt', 'Does not hold'), ('cannot tell', 'Cannot tell'), ('note', 'Worth knowing'), ('holds', 'Holds')):
        found = [row for row in rows if row.get('verdict') == verdict]
        if found:
            sheet.append(('h', heading))
            sheet.extend(('b', '%s — %s' % (row['about'][:1].upper() + row['about'][1:], row['why'])) for row in found)
    worst = sum(1 for row in rows if row.get('verdict') == 'doubt')
    name = obj.title if len(obj.title) <= 60 else obj.title[:59].rstrip() + '…'
    page.view.show_reading('Doubting “%s”' % name, sheet or [('q', 'There is nothing I know how to doubt about this yet.')],
                           ('D  what can be done about it      ' if worst else '') + 'Esc  close      any other key moves on', line, light=True)


def brief(host):
    """B: the desk written up as one page, from the records. It is a page, so it is shown as one: over the work, at reading
    size, to scroll. Keeping it as a page is a change, so that waits for the owner's go (G here, or Run in Talk), and the
    go keeps exactly the desk that was shown. No model writes any of it; the staC line that reads it is under the page."""
    from .engineering_kernel import operator
    from .field_do import Step, op
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work' or not page.view.field.objects:return None
    answer = kernel.dispatch('field.brief', {}, operator())
    if not answer.get('ok'):
        host.statusBar().showMessage('Field · the brief could not be read: %s' % str((answer.get('error') or {}).get('message'))[:160], 9000);return None
    made = answer['result'];lines = made['lines'];title = lines[0]['text'] if lines else 'The brief'
    style = {'head': 'q', 'title': 'h', 'foot': 'q'}
    page.view.show_reading(title, [(style.get(line['part'], 'b'), line['text']) for line in lines[1:]],
                           'G  keep it as a page      ↑ ↓  read on      Esc  close', 'field.brief | pick lines | select text')
    step = Step('Keep the brief as a page', 'write', op('field.brief.keep', shown=made['fingerprint']),
                'a page in Documents and on the Field, to edit, export or print; when the desk changes it says so, and a later brief takes its place', 'execute')

    def done(ok, result):
        page.steps = ();page.steps_of = '';page.pending = None
        page.view.close_reading()
        if not ok:
            host.statusBar().showMessage('Field · the brief was not kept; B reads the desk again', 9000);page.view.update();return
        page.refresh(force=True)
        kept = (result or {}).get('document') if isinstance(result, dict) else None
        ident = 'document:' + str(kept.get('id')) if isinstance(kept, dict) and kept.get('id') else ''
        if ident and page.view.field.get(ident) is not None:
            page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe()
        page.view.update()

    face = _talk(host)
    if face is not None:                       # Talk holds the change itself, with its line and its Run; the page is read in the Field
        card = face.stage(title, step, done=done)
        run = lambda: face.run_staged(card, done)
    else:
        card = None
        def run():
            r = kernel.dispatch('field.brief.keep', {'shown': made['fingerprint']}, operator())
            done(bool(r.get('ok')), r.get('result') if r.get('ok') else None)
    _await_go(host, 'keep the brief as a page', run)
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def stage_set(host, obj, cell, value, word=''):
    """“Set B3 to 300”, asked of Stacy with a sheet (or a calculation, which stands for its sheet) selected: the change is
    put up with its exact line and waits for Approve, and meanwhile the Field marks what it would move, as a what-if does.
    Approving saves the sheet through the same operation the owner's own edit uses; then the records are read again."""
    from .engineering_kernel import operator
    from .field_do import Step, op
    from .field_ripple import cells_named
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None);face = _talk(host)
    if kernel is None or face is None:return None
    sheet, _ = cells_named(kernel, operator(), obj)
    got = kernel.dispatch('office.get', {'id': sheet}, operator()) if sheet else {'ok': False}
    if not got.get('ok'):
        face.say('I cannot read the sheet that number is on, so I have not put a change up.');return None
    held = ((got['result']['document'].get('sheets') or [{}])[0].get('cells') or {}).get(cell) or {}
    title = str(got['result']['document'].get('title') or 'the sheet');unit = str(held.get('unit') or '').strip()
    words = 'Set %s to %s%s' % (cell, value, ' ' + unit if unit else '')
    show_would(host, 'office:' + str(sheet), {cell: value}, '%s = %s' % (cell, value), lead='if approved: set ')
    step = Step(words, 'write', op('field.set', id='office:' + str(sheet), cell=cell, value=value, expected_revision=got['result']['revision']),
                '%s says %s%s now. The sheet is saved with the new value and everything worked from it waits for a recheck; the Field marks what would move' % (
                    cell, held.get('value'), ' ' + unit if unit else ''), 'execute')
    done = lambda ok, result, obj=obj:_after(host, obj, ok, result)
    card = face.stage(title, step, done=done, asked=True, word=word)      # asked of her: it follows her hand (done at once, or waiting)
    if card.ran is None:_await_go(host, '%s on “%s”' % (words[:1].lower() + words[1:], title), lambda:face.run_staged(card, done))
    elif card.ran is False:                    # she tried at once and it was refused: nothing would move, so nothing is marked
        page.view.would = {};page.view.would_said = '';page.view.update()
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def show_would(host, ident, setting, said, lead='what if '):
    """A what-if, shown on the Field: the sheets that would move carry what they would say, in amber, until Esc or the next
    reading. The same read Stacy shows in Talk (field.ripple); a refusal marks nothing."""
    from .engineering_kernel import operator
    from .field_ripple import marks
    page = getattr(host, 'field_page', None);kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if page is None or kernel is None:return {}
    answer = kernel.dispatch('field.ripple', {'id': ident, 'set': setting}, operator())
    page.view.would = marks(answer['result']) if answer.get('ok') else {}
    page.view.would_said = (lead + said) if page.view.would else ''
    page.view.update()
    return page.view.would


def full_window(host, obj):
    """F on the shelf: this program in its full window. A program with a window of its own is started on a file, through its
    own operation and with the owner's go, so F says what can be done with it (its files, and Open … in … for each); when
    there is exactly one file to open, that step is put up at once. A room of Graphite's own has no other window: it says so."""
    from .field_do import NATIVE
    key = (obj.target or {}).get('key') if isinstance(obj.target, dict) else None
    if key not in NATIVE:
        host.statusBar().showMessage('Field · %s is a room of Graphite’s own: Enter opens it' % obj.title, 7000);return None
    steps = do(host, obj)
    opens = [n for n, step in enumerate(steps) if step.kind == 'write' and step.words.startswith('Open ')]
    if len(opens) == 1:return take(host, obj, opens[0])
    if not opens:host.statusBar().showMessage('Field · %s opens a file; none of its files is in Files yet' % obj.title, 7000)
    return None


def check_desk(host):
    """C: check the desk. Everything is read again; findings are checked against their sources without marking anything;
    Stacy says what waits and why, each with the step that would settle it, and lists the reads she made."""
    from .engineering_kernel import operator
    from .field_do import settling, sweep
    page = host.field_page;kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None or page.face != 'work':return None
    page.refresh(force=True)
    waiting, lines = sweep(kernel, operator(), page.view.field)
    face = _talk(host)
    if face is None:return None
    def go(obj):
        if page.view.field.get(obj.id) is None:return
        page.view.field.select(obj.id);page.view._reveal_pending = True;page.view._describe();page.view.update();do(host, obj)
    plan = settling(waiting)
    answer = kernel.dispatch('field.doubt', {}, operator())      # the same check also cross-examines everything: what a plausible result may hide
    doubts = [row for row in (answer['result']['rows'] if answer.get('ok') else ()) if row['verdict'] == 'doubt']
    if answer.get('ok'):lines.append('field.doubt | pick rows | select title,verdict,about,why')
    def settle():
        # The changes go up together for one Run; when they have run the desk is checked again, and that check is the answer.
        done = lambda results:check_desk(host)
        mine = settles_hers                        # when every change is hers, "settle what I can" is done, not put up
        card = face.say_plan(plan, done=done, hers=mine, word='settle what you can' if mine else '')
        if mine:face.run_plan(card, done)
        else:_await_go(host, 'all %d changes, as listed in Talk' % len(plan) if len(plan) > 1 else 'the change, as listed in Talk', lambda:face.run_plan(card, done))
        page.view.setFocus(Qt.OtherFocusReason)
    def look(ident):
        obj = page.view.field.get(ident)
        if obj is None:return
        page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe();page.view.update();doubt(host, obj)
    settles_hers = bool(plan) and all(not _waits(host, step) for _, step in plan)      # said where it is offered: the step is shown as one she does, or one that asks
    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle, doubts, look, hers=settles_hers)
    page.steps = ();page.steps_of = '';page.pending = None;page.star = None
    if plan:                                   # the desk's own step, numbered 1: it puts the changes up; G then gives the go
        words = 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's')
        page.steps = (words,);page.steps_of = '*';page.star = settle
        page.view.steps = ((words, 'does' if settles_hers else 'write'),);page.view.update()
    # The same answer where the eyes are: a light page over the work. It steps aside at the next key, so 1 settles and A
    # goes to the next thing that waits exactly as they do without it. Talk keeps the card, with its links.
    count = len(page.view.field.objects);sheet = [('q', 'I read the desk: %d thing%s, each from its record. Nothing is changed.' % (count, '' if count == 1 else 's'))]
    sheet.append(('h', 'Waits for you' if waiting else 'Nothing waits for you'))
    for obj, why, steps in waiting[:12]:
        first = next((step for step in steps if step.settles), None) or next((step for step in steps if step.kind == 'write'), None)
        sheet.append(('b', '“%s” — %s%s' % (obj.title, why, ('. Next: ' + first.words[:1].lower() + first.words[1:]) if first else '')))
    if len(waiting) > 12:sheet.append(('q', '… and %d more: A goes to each in turn.' % (len(waiting) - 12)))
    if doubts:
        sheet.append(('h', 'Looks right, and I doubt it'))
        sheet.extend(('b', '“%s” — %s: %s' % (row['title'], row['about'], row['why'])) for row in doubts[:8])
        if len(doubts) > 8:sheet.append(('q', '… and %d more: X on a sheet doubts it.' % (len(doubts) - 8)))
    elif answer.get('ok'):
        sheet.append(('h', 'Nothing I doubt'));sheet.append(('q', 'By the questions I have. They are few: this is not a proof.'))
    keys = (['1  settle what I can (%d change%s)' % (len(plan), '' if len(plan) == 1 else 's')] if plan else []) + (['A  the next that waits'] if waiting else []) + ['Esc  close']
    page.view.show_reading('The desk, checked', sheet, '      '.join(keys), 'field.read | pick waiting | select kind,title,state', light=True)
    if plan:page.view.steps = ((words, 'does' if settles_hers else 'write'),)      # showing the page describes the sheet again; the desk's own step stays offered
    page.view.setFocus(Qt.OtherFocusReason)
    return card


def stac_in_line(host, obj):
    """S: the object's staC line in the writing strip, in Assignment, for the owner to read or change. Nothing runs; Ctrl+Enter
    there runs it. The Field stays where it is."""
    from .context_menu import inspect_in_line
    return inspect_in_line(host, obj.stac)


def stac_run(host, obj):
    """Shift+Enter: run the object's staC line through its normal path (the working area's staC page, through Kernel.dispatch).
    It is a read; a refusal is said as one. The Field stays in front and the answer opens beside it in the working area."""
    from .context_menu import Refused, run_stac
    try:
        ran = run_stac(host, obj.stac)
    except Refused as exc:
        host.statusBar().showMessage('Field · %s' % exc, 9000);return None
    page = getattr(host, 'field_page', None)
    if page is not None and getattr(host, '_field_active', False):
        page.view.setFocus(Qt.OtherFocusReason)        # the keyboard stays in the Field: the next arrow moves, the next Shift+Enter asks again
    return ran


def open_network(host, words):
    """Detail for the network face is the Log's Network stream, filtered to the chosen thing: the writing line goes to Log, the
    stream to Network, and the filter is the words the Log's own grammar takes (a host, a port, a program name)."""
    leave_field(host)
    bar = getattr(host, 'type_bar', None)
    if bar is None:
        return None
    bar.set_target('log')
    console = getattr(host, 'console', None)
    if console is not None and hasattr(console, 'set_size') and getattr(console, 'size_level', 1) == 0:
        console.set_size(1)                        # a one-line strip shows no stream: open it to half
    log = getattr(host, 'log_view', None)
    if log is not None and hasattr(log, 'choose'):
        log.choose('network')
        if words and hasattr(log, 'apply_filter'):log.apply_filter(words)
    return log


def open_object(host, obj):
    """Open the real page for one object of the Field, through its room's own opener. Whatever the opener did (a new tab, or a
    tab that was already there), the Field steps aside so the page is what the owner sees."""
    target = getattr(obj, 'target', None) or {}
    kind = target.get('kind') if isinstance(target, dict) else None
    opened = None
    try:
        if kind == 'office':
            from .office_qt import open_office
            opened = open_office(host, target['id'])
        elif kind == 'document':
            from .document_qt import show
            opened = show(host, target['id'])
        elif kind == 'investigation':
            from .investigations_qt import show
            opened = show(host, target['id'])
        elif kind == 'pdf':
            from .pdf_qt import open_pdf
            opened = open_pdf(host, target['namespace'], target['item'], target.get('sha256'), int(target.get('page_index', 0)))
        elif kind == 'network':
            return open_network(host, target.get('filter', ''))
        elif kind == 'program':            # the programs list's own opening: the room, through the existing view factories
            from .explore_qt import open_instrument
            opened = open_instrument(host, target['entry'])
        elif kind == 'job':
            from .context_menu import show_job
            opened = show_job(host, target['id'])
        else:
            host.statusBar().showMessage('Field · %s has no page of its own to open yet' % obj.title, 6000);return None
    except (ValueError, OSError, KeyError) as exc:
        reason = str(exc).strip().strip('\'"').replace('_', ' ').lower()[:120]
        host.statusBar().showMessage('Field · %s could not be opened%s' % (obj.title, ' (%s)' % reason if reason else ''), 9000)
        return None
    if opened is not None:
        leave_field(host)            # an opener that found its tab already open does not call the window's _close_start itself
    return opened
