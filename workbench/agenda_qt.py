"""Slate's Agenda on the Desk, a one-line summary in Slate's panel, and the quiet runner that works through Next.

Every action is a word in a sentence (4.1). Everything goes through the Kernel's agenda.* operations; the runner calls
agenda.run_next, which runs one item with read-only authority and records what actually came back.
"""
from __future__ import annotations
from .text_prompts import writing_prompt
import threading
import time
from datetime import datetime
from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget
from .shell2 import LINE, QUIET, call, call_write, escape_text, role, sentence

NICE_NEXT = {'now': 'normal', 'normal': 'background', 'background': 'now'}
IDLE_AFTER = 120.0  # seconds without keyboard or mouse before background work may run
RUN_EVERY = 10_000


def when_words(stamp):
    if not stamp:return ''
    moment = datetime.fromtimestamp(stamp).astimezone()
    return moment.strftime('%a %d %b %H:%M ') + (moment.tzname() or '')


def quiet(text):
    label = QLabel(text);label.setWordWrap(True);label.setStyleSheet('color:%s' % QUIET);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    return label


class AgendaTab(QWidget):
    """Now, Next, Waiting for you, Suggested, Later, Done."""

    def __init__(self, host):
        super().__init__();self.host = host;self.nice = 'normal';self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # it reflows; it never scrolls sideways
        self.timer = QTimer(self);self.timer.setInterval(3000);self.timer.timeout.connect(self.reload)
        self.reload()

    def title(self):return 'Agenda'

    def inspector(self):
        from .shell2 import call
        view = call(self.host, 'agenda.view') or {};counts = view.get('counts') or {}
        rows = [(label, str(counts.get(key, 0))) for key, label in (('now', 'Now'), ('next', 'Next'), ('waiting', 'Waiting for you'), ('later', 'Later'), ('suggested', 'Suggested'))]
        watches = sum(1 for r in (view.get('later') or []) + (view.get('next') or []) if r.get('watch'))
        rows.append(('Watches', str(watches)))
        rules = view.get('rules', {})
        rows.append(('How it runs', 'one due item at a time, %s-only; up to %d suggestions; stops after %d rounds that find nothing new; nothing new starts without your say-so'
                     % (rules.get('authority', 'read'), rules.get('max_suggestions', 3), rules.get('quiet_limit', 2))))
        return 'Graphite\'s Agenda', rows

    def showEvent(self, event):super().showEvent(event);self.reload();self.timer.start()

    def hideEvent(self, event):super().hideEvent(event);self.timer.stop()

    def act(self, op, args):
        r = call_write(self.host, op, args)
        if not r.get('ok'):self.host.statusBar().showMessage((r.get('error') or {}).get('message', 'Not done'), 6000)
        self.reload();return r

    def add(self):
        text = self.entry.text().strip()
        if not text:return
        # staC runs as written; anything in plain words is a question for Slate, answered when his brain is running.
        program = text if text.startswith('@') or text.split()[0].lower() in ('library', 'desk', 'package', 'map', 'source', 'packet') else None
        if self.act('agenda.add', {'title': text[:400], 'nice': self.nice, **({'program': text} if program else {})}).get('ok'):self.entry.clear()

    def cycle_nice(self):
        self.nice = NICE_NEXT[self.nice];self.reload()

    def reload(self):
        view = call(self.host, 'agenda.view') or {'now': [], 'next': [], 'waiting': [], 'later': [], 'suggested': [], 'done': []}
        self.view = view
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(48, 32, 48, 24);box.setSpacing(18)
        box.addWidget(role(QLabel("Graphite's Agenda"), 'title'))
        lead = role(QLabel('What it is doing, what comes next and what it is waiting for. Nothing new starts without your say-so.'), 'lead')
        lead.setWordWrap(True);lead.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);box.addWidget(lead)
        row = QHBoxLayout();row.setSpacing(16)
        old = getattr(self, 'entry', None)
        self.entry = QLineEdit(old.text() if old is not None else '');writing_prompt(self.entry, 'Add something for Graphite to do next, in words or staC')
        self.entry.setAccessibleName('Add to Next');self.entry.returnPressed.connect(self.add);row.addWidget(self.entry, 1)
        row.addWidget(sentence('nice {nice}', {'nice': (self.nice, self.cycle_nice)}));box.addLayout(row)
        if not view['now'] and not view['next']:
            from .shell2 import pleasantry
            box.addWidget(pleasantry(QLabel('All quiet for now.'), self.host, 24))  # a pleasantry, in script
        self._empties = []  # empty sections are named together on one line at the foot, not each given a heading
        self.section(box, 'NOW', view['now'], self.now_row, 'Nothing is running.')
        self.section(box, 'NEXT · IN ORDER', view['next'], self.next_row, 'Nothing is next.', keep=6)
        self.section(box, 'WAITING FOR YOU', view['waiting'], self.waiting_row, 'Nothing is waiting for you.', keep=6)
        if view['suggested']:self.section(box, 'SUGGESTED BY GRAPHITE · NEXT STEPS', view['suggested'], self.suggested_row, '')
        self.section(box, 'LATER', view['later'], self.later_row, 'Nothing is scheduled.', keep=0, folded='%d scheduled')
        self.section(box, 'DONE', view['done'][:30], self.done_row, 'Nothing has finished yet.', keep=0, folded='%d finished')
        if self._empties:
            box.addWidget(quiet('Empty for now: ' + ' · '.join(self._empties) + '.'))
        # How it runs is said once, in the Context panel beside the Agenda; not repeated at the foot of this page.
        box.addStretch(1)
        focus = self.entry.hasFocus() if old is None else old.hasFocus()
        self.scroll.setWidget(page)  # a fresh page each time: nothing stale is left drawn
        if focus:self.entry.setFocus();self.entry.end(False)

    def section(self, box, title, rows, make, empty, keep=None, folded='%d more'):
        """Less scrolling: a long section shows its first rows and one line for the rest, until you open it."""
        opened = getattr(self, 'opened', set())
        if keep is not None and title not in opened and len(rows) > keep:
            more = len(rows) - keep
            words = (folded % more) if keep == 0 else ('and %d more' % more)
            box.addWidget(role(QLabel(title), 'section'))
            holder = QFrame();holder.setObjectName('AgendaRows');holder.setStyleSheet('QFrame#AgendaRows {border-top:1px solid %s;}' % LINE)
            col = QVBoxLayout(holder);col.setContentsMargins(0, 6, 0, 0);col.setSpacing(10)
            for i, r in enumerate(rows[:keep]):
                w = make(r, i)
                if r.get('program') and str(r['program']).startswith('@'):self.chainable(w, r['program'])
                col.addWidget(w)
            col.addWidget(sentence(escape_text(words) + '  ·  {show}', {'show': ('show them', lambda t=title:self.open_section(t))}))
            box.addWidget(holder);return
        if not rows and empty and hasattr(self, '_empties'):
            self._empties.append(title.split(' · ')[0].capitalize());return
        box.addWidget(role(QLabel(title), 'section'))
        holder = QFrame();holder.setStyleSheet('QFrame#AgendaRows {border-top:1px solid %s;}' % LINE);holder.setObjectName('AgendaRows')
        col = QVBoxLayout(holder);col.setContentsMargins(0, 6, 0, 0);col.setSpacing(10)
        if not rows and empty:col.addWidget(quiet(empty))
        for i, r in enumerate(rows):
            w = make(r, i)
            if r.get('program') and str(r['program']).startswith('@'):self.chainable(w, r['program'])
            col.addWidget(w)
        box.addWidget(holder)

    def open_section(self, title):
        self.opened = getattr(self, 'opened', set()) | {title};self.reload()

    def chainable(self, widget, program):
        """Right-click on an item that asks staC: carry on from its question as a chain."""
        from PySide6.QtCore import Qt
        def menu(point, w=widget, p=program):
            from PySide6.QtWidgets import QMenu
            from .chain_menu import fill
            m = QMenu(w);fill(m, self.host, p);m.exec(w.mapToGlobal(point))
        widget.setContextMenuPolicy(Qt.CustomContextMenu);widget.customContextMenuRequested.connect(menu)

    def line(self, title, detail=None, words=None):
        w = QWidget();col = QVBoxLayout(w);col.setContentsMargins(0, 0, 0, 0);col.setSpacing(3)
        head = QLabel(title);head.setWordWrap(True);col.addWidget(head)
        if detail or words:
            col.addWidget(sentence(escape_text(detail or '') + ('  ·  ' if detail and words else '') + (words[0] if words else ''), words[1] if words else {}))
            col.itemAt(1).widget().setStyleSheet('color:%s' % QUIET)
        return w

    def now_row(self, r, i):
        if r.get('kind') == 'job':return self.line(r['title'], 'a Kernel job, running')
        return self.line(r['title'], 'running now · nice ' + r['nice'], ('{cancel}', {'cancel': ('cancel', lambda r=r:self.act('agenda.cancel', {'id': r['id']}))}))

    def next_row(self, r, i):
        if r.get('kind') == 'job':return self.line(r['title'], 'a Kernel job, queued')
        detail = '%d · nice ' % (i + 1)
        words = {'nice': (r['nice'], lambda r=r:self.act('agenda.nice', {'id': r['id'], 'nice': NICE_NEXT[r['nice']]})),
                 'cancel': ('remove', lambda r=r:self.act('agenda.cancel', {'id': r['id']}))}
        text = detail.replace('nice ', 'nice {nice}')
        if r['state'] == 'PAUSED':words['pause'] = ('resume', lambda r=r:self.act('agenda.resume', {'id': r['id']}));text += '  ·  paused'
        else:words['pause'] = ('pause', lambda r=r:self.act('agenda.pause', {'id': r['id']}))
        if i:words['up'] = ('move up', lambda r=r, i=i:self.act('agenda.move', {'id': r['id'], 'position': i - 1}))
        extra = [r['reason']] if r.get('reason') else []
        if r['nice'] == 'background':extra.append('waits until the computer is idle')
        if r.get('origin') == 'slate':extra.append('Graphite suggested')
        w = QWidget();col = QVBoxLayout(w);col.setContentsMargins(0, 0, 0, 0);col.setSpacing(3)
        head = QLabel(r['title']);head.setWordWrap(True);col.addWidget(head)
        label = sentence(text + '  ·  {pause}' + ('  ·  {up}' if i else '') + '  ·  {cancel}' + ''.join('  ·  ' + escape_text(e) for e in extra), words)
        label.setStyleSheet('color:%s' % QUIET);col.addWidget(label)
        return w

    def waiting_row(self, r, i):
        if r.get('kind')=='work':
            from .continuing_work_qt import show
            return self.line(r['title'],r.get('reason') or r['state'],('{open}',{'open':('inspect assignment',lambda r=r:show(self.host,r['id']))}))
        if r.get('kind') == 'investigation':
            from .investigations_qt import show
            return self.line(r['title'], r.get('reason') or 'waiting for you', ('{open}', {'open': ('open', lambda r=r:show(self.host, r['id']))}))
        if r.get('kind') == 'job':return self.line(r['title'], 'a Kernel job · ' + (r.get('reason') or 'waiting'))
        if r.get('kind') == 'watch':
            return self.line(r['title'], r.get('reason'), ('{look}  ·  {seen}', {
                'look': ('see the answer now', lambda r=r:self.host.shell2.run_stac(r['program'])),
                'seen': ('seen it', lambda r=r:self.act('agenda.seen', {'id': r['id']}))}))
        if r.get('kind') == 'proposal':
            from .compare_qt import show as compare
            return self.line(r['title'], r.get('reason'), ('{look}  ·  {apply}  ·  {decline}', {
                'look': ('look at the change', lambda r=r:compare(self.host, path=r['path'], proposal=r['id'])),
                'apply': ('apply', lambda r=r:self.act('files.decide', {'id': r['id'], 'apply': True})),
                'decline': ('decline', lambda r=r:self.act('files.decide', {'id': r['id'], 'apply': False}))}))
        return self.line(r['title'], r.get('reason'))

    def suggested_row(self, r, i):
        return self.line(r['title'], 'new: ' + (r.get('why') or ''),
                         ('{add} · {no}', {'add': ('add to Next', lambda r=r:self.act('agenda.accept', {'id': r['id']})),
                                           'no': ('not now', lambda r=r:self.act('agenda.decline', {'id': r['id']}))}))

    def later_row(self, r, i):
        every = r.get('every')
        detail = (('watching every %g hours · ' if r.get('watch') else 'every %g hours · ') % (every / 3600) if every else 'once · ') + 'next ' + when_words(r.get('due')) + ' · nice ' + r['nice']
        if r.get('watch') and r.get('outcome'):detail += ' · last: ' + r['outcome'][:120]
        if r.get('missed'):detail += ' · missed %d, ran once on return' % r['missed']
        return self.line(r['title'], detail, ('{pause} · {cancel}', {'pause': ('pause', lambda r=r:self.act('agenda.pause', {'id': r['id']})),
                                                                     'cancel': ('remove', lambda r=r:self.act('agenda.cancel', {'id': r['id']}))}))

    def done_row(self, r, i):
        words = {'DONE': 'done', 'FAILED': 'could not run', 'CANCELLED': 'cancelled', 'STOPPED': 'stopped'}.get(r['state'], r['state'].lower())
        stamp = datetime.fromtimestamp(r['finished']).strftime('%H:%M') if r.get('finished') else ''
        return self.line(r['title'], ' · '.join(x for x in (stamp, words, r.get('reason') or '', (r.get('outcome') or '')[:160]) if x))


def show(host):
    """Open (or reuse) the Agenda tab."""
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, AgendaTab):host.tabs.setCurrentWidget(tab);tab.reload();return tab
    tab = AgendaTab(host);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab


def summary(host):
    """One line for Slate's panel: what he is doing now, and what needs you."""
    view = call(host, 'agenda.view')
    if not view:return None
    now = view['now'][0]['title'] if view['now'] else None
    counts = view.get('counts', {})
    parts = ['Now: ' + escape_text(now[:80]) if now else 'Nothing running']
    if counts.get('next'):parts.append('%d next' % counts['next'])
    if counts.get('waiting'):parts.append('{waiting}')
    return '  ·  '.join(parts) + '  ·  {open}', counts.get('waiting', 0)


class Runner(QObject):
    """Works through Next quietly: one item at a time, off the window's thread, with read-only authority."""

    def __init__(self, host):
        super().__init__(host);self.host = host;self.last_input = time.time();self.busy = False;self.result = None;self.pulse_busy=False;self.last_pulse=0
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
        self.timer = QTimer(self);self.timer.setInterval(RUN_EVERY);self.timer.timeout.connect(self.tick);self.timer.start()
        self.pulse_timer=QTimer(self);self.pulse_timer.setInterval(2000);self.pulse_timer.timeout.connect(self.pulse);self.pulse_timer.start()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel):self.last_input = time.time()
        return False

    def pulse(self):
        if self.pulse_busy or getattr(self.host,'_closing',False) or time.time()-self.last_input>3 or time.time()-self.last_pulse<3:return
        self.pulse_busy=True;self.last_pulse=time.time()
        def work():
            try:
                from .engine import engineering
                from .engineering_kernel import operator
                from .resource_control import touch
                touch(engineering(self.host.root),operator().identity)
            except (OSError,ValueError):pass
            finally:self.pulse_busy=False
        threading.Thread(target=work,name='graphite-foreground',daemon=True).start()

    def idle(self):return time.time() - self.last_input >= IDLE_AFTER

    def tick(self):
        if self.busy or getattr(self.host, '_closing', False):return
        self.busy = True;idle = self.idle()

        def work():
            from .engine import engineering
            from .engineering_kernel import operator
            try:
                kernel = engineering(self.host.root)
                view = kernel.dispatch('agenda.view', {}, operator())  # a quiet read: the Timeline only hears about real work
                counts = (view.get('result') or {}).get('counts') or {}
                clock = time.time();value = view.get('result') or {}
                ours = [r for r in value.get('now', []) if r.get('kind') != 'job'] + [  # only what is due: nothing is logged while items wait
                    r for r in value.get('next', []) if r.get('kind') != 'job' and r.get('state') == 'NEXT' and (not r.get('due') or r['due'] <= clock or (r.get('reason') or '').startswith('Missed '))
                    and (r.get('nice') != 'background' or idle)]
                self.result = kernel.dispatch('agenda.run_next', {'idle': idle}, operator()) if counts and ours else None
            except Exception as exc:self.result = {'ok': False, 'error': {'message': str(exc)}}
            finally:self.busy = False
        threading.Thread(target=work, name='ledger-agenda', daemon=True).start()


def install(host):
    if getattr(host, 'agenda_runner', None) is None:host.agenda_runner = Runner(host)
    return host.agenda_runner
