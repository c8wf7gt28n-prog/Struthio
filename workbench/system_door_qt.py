"""The system door in her talk, her column, the line and Settings (Graphite 1.1 KS3). The door itself is system_door's.

Where it shows (the coordinator's note of 28 Nov):
  her talk      the ask line's words (shell2.SlateFace.ask calls asked() before her recipes): "install gimp", "restart cups",
                "set the time zone to Europe/Lisbon", "sudo apt install gimp" ... become one fixed action. She shows what the
                system will do (system.door.plan: what it pulls in, its size, what Undo does or that it cannot be undone, and "The
                system will ask for your password"), and waits. The press is yours; she says "Asking the system now" (the
                moment before the system's own prompt), the system asks you itself, and she says "Done and verified" only
                when the effect was read back; Undo is the inverse fixed action, through the same prompt.
  NEXT STEPS    "Install GIMP · asks for your password" while a plan waits; "Undo · Install GIMP · asks for your password".
  the line      line_rows(): "Install GIMP, asks for your password"; Enter shows what the system will do (nothing changes).
  Settings      This computer > System changes (show_page): whether the system's prompt can open, which services answer,
                the time zone, network time, the computer's name, the accounts, the door's record; each press there shows
                the plan in her talk, where the press that starts it is.

Every press is the owner's: dispatched with the owner's principal; the Kernel checks system.door.run's approve scope, refuses it in
her work, under a grant and under HALT. Nothing here starts a change on its own.
"""
from __future__ import annotations

from . import kas_voice as kv
from . import system_door as sd

SYNC = False                # tests: work on the window's thread instead of a worker
STATE = {}                  # id(host) -> {'offer': {...}, 'done': {...}, 'asking': title}
GO = {'package.install': 'Install', 'package.remove': 'Remove', 'package.update': 'Update', 'packages.refresh': 'Refresh',
      'service.start': 'Start', 'service.stop': 'Stop', 'service.restart': 'Restart', 'service.enable': 'Enable', 'service.disable': 'Disable',
      'time.zone': 'Set it', 'time.ntp': 'Turn it', 'time.set': 'Set it', 'host.name': 'Name it', 'user.add': 'Add it', 'user.realname': 'Set it'}


def _state(host):
    return STATE.setdefault(id(host), {})


def _later(host, fn, done, name='graphite-door'):
    """fn() off the window's thread, then done(result, error) on it (SYNC: at once)."""
    if SYNC:
        try:result, error = fn(), None
        except Exception as exc:  # noqa: BLE001
            result, error = None, exc
        done(result, error);return
    from .off_window import run_alone
    run_alone(fn, done, name=name)


def _call(host, op, args):
    """The owner's press or read, through the Kernel: a fresh Kernel on the workspace, the owner's principal."""
    from .engineering_kernel import Kernel, operator
    from .off_window import kernel_root
    root = kernel_root(host)
    if root is None:
        from .engine import engineering
        kernel = engineering(host.root)
    else:
        kernel = Kernel(root)
    return kernel.dispatch(op, args, operator())


def _why(answer, error=None):
    if error is not None:return str(error)[:300]
    answer = answer if isinstance(answer, dict) else {}
    return str((answer.get('error') or {}).get('message', 'refused')).split(': ', 1)[-1][:300]


def _column_soon(host):
    column = getattr(host, 'her_column', None)
    if column is None:return
    try:
        from . import floor
        floor.column_soon(column)
    except Exception:  # noqa: BLE001
        pass


def _add(bubble, widget):
    try:bubble.box.addWidget(widget)
    except Exception:  # noqa: BLE001 - a bubble without a box still says it
        pass


def _plain(text, name='DoorWords'):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text);label.setWordWrap(True);label.setObjectName(name)
    return label


def _lines(lines, most=10):
    from html import escape
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from . import boss_theme as bt
    label = QLabel();label.setObjectName('DoorLines');label.setWordWrap(True);label.setTextFormat(Qt.RichText)
    body = '<br>'.join(escape(l) for l in lines[:most])
    if len(lines) > most:body += '<br>… and %d more' % (len(lines) - most)
    label.setText('<span style="font-family:\'%s\';font-size:12px;color:%s;">%s</span>' % (bt.MONO, bt.QUIET, body))
    return label


def _args(got):
    return {'action': got['action'], 'target': got.get('target') or '', 'value': got.get('value') or ''}


# ---- the ask chain ----------------------------------------------------------------------------------------------------------
def asked(face, text):
    """shell2's ask chain: True when the words ask for one of the door's fixed actions, and she has answered."""
    try:got = sd.read_words(text)
    except Exception:  # noqa: BLE001 - a broken reading never stands in the way of the rest of her chain
        return False
    if got is None:return False
    face.thing = None;face.mine(text);show(face, got)
    return True


def show(face, got):
    """The plan, in her talk: what the system will do, and the press; or why it cannot be asked; or that nothing is to do."""
    host = face.host

    def planned(answer, error):
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(kv.say('door_refused', why=_sentence(_why(answer, error))));_column_soon(host);return
        p = answer['result']
        if p['nothing']:
            _state(host).pop('offer', None);face.say(kv.say('door_nothing', words=p['words']));_column_soon(host);return
        if not p['ok']:
            face.say(kv.say('door_not_ready', title=p['title'], why=p.get('why', '')));_column_soon(host);return
        offer(face, got, p)
    _later(host, lambda: _call(host, 'system.door.plan', _args(got)), planned, 'graphite-door-plan')


def _sentence(text):
    text = str(text or '').strip()
    text = (text[:1].upper() + text[1:]) if text else 'The door gave no reason'
    return text if text[-1:] in '.?' else text + '.'


def offer(face, got, p):
    """What the system will do, exactly, then the press. Nothing is asked of the system until the press."""
    from .shell2 import sentence
    host = face.host
    bubble = face.say(kv.say('door_plan', title=p['title']))
    if p.get('lines'):_add(bubble, _lines(p['lines']))
    _add(bubble, _plain(' '.join(x for x in (p['words'], p.get('undo') or '') if x)))
    _add(bubble, _plain(kv.say('door_asks', asks=p['asks']), 'DoorAsks'))
    state = _state(host);state['offer'] = {'got': got, 'plan': p, 'face': face};state.pop('done', None)
    verb = GO.get(p['action'], 'Do it') + ((' ' + p['target']) if p['action'] == 'time.ntp' else '')
    actions = {'go': (kv.say('door_go_word', verb=verb), lambda: run(face, got, p)), 'no': (kv.say('door_no_word'), lambda: cancel(face))}
    _add(bubble, sentence('{go}  ·  {no}', actions))
    _column_soon(host)
    return bubble


def cancel(face):
    host = face.host
    if _state(host).pop('offer', None) is not None:face.say(kv.say('door_cancelled'))
    _column_soon(host)


def run(face, got, p):
    """Your press: she says she is asking the system (its own prompt opens next), then system.door.run with the digest you saw."""
    host = face.host;state = _state(host)
    if state.get('asking'):face.say(kv.say('door_one_at_a_time'));return None
    state.pop('offer', None);state['asking'] = p['title']
    bubble = face.say(kv.say('door_asking', title=p['title']))
    _column_soon(host)

    def ran(answer, error):
        state.pop('asking', None)
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            why = _why(answer, error)
            if 'changed since you saw it' in why:
                face.say(kv.say('door_changed'));show(face, got);return
            face.say(kv.say('door_refused', why=_sentence(why)));_column_soon(host);return
        done(face, answer['result'])
    _later(host, lambda: _call(host, 'system.door.run', dict(_args(got), digest=p['digest'])), ran, 'graphite-door-run')
    return bubble


def done(face, v):
    """The end, in her voice: done and verified (with Undo where the system allows), the prompt's no, HALT, a failure, or
    not verified. Every one says what was read back."""
    from .shell2 import sentence
    host = face.host;state = _state(host)
    checked = v.get('checked') or 'nothing'
    if v['state'] == 'done':said = kv.say('door_done', title=v['title'], checked=checked)
    elif v['state'] == 'refused at the prompt':said = kv.say('door_said_no', checked=checked)
    elif v['state'] == 'no prompt':said = kv.say('door_no_prompt', checked=checked)
    elif v['state'] == 'stopped by HALT':said = kv.say('door_halted', title=v['title'], checked=checked)
    elif v['state'] == 'failed':said = kv.say('door_failed', title=v['title'], why=_sentence(v.get('why')), checked=checked)
    else:said = '◆ ' + kv.say('not_verified', checked=checked)
    bubble = face.say(said)
    if v.get('can_undo'):
        state['done'] = {'run': v['run'], 'title': v['title'], 'face': face}
        _add(bubble, sentence('{undo}', {'undo': (kv.say('door_undo_word'), lambda: undo(face, v['run'], v['title']))}))
    _column_soon(host)
    return bubble


def undo(face, run_id, title):
    host = face.host;state = _state(host)
    if state.get('asking'):face.say(kv.say('door_one_at_a_time'));return
    state.pop('done', None);state['asking'] = 'Undo ' + title
    face.say(kv.say('door_undoing', title=title))

    def back(answer, error):
        state.pop('asking', None)
        if getattr(host, '_closing', False):return
        if error is not None or not (answer or {}).get('ok'):
            face.say(kv.say('door_undo_failed', title=title, why=_sentence(_why(answer, error))));_column_soon(host);return
        v = answer['result']
        if v['state'] == 'done':face.say(kv.say('door_undone', title=title, checked=v['checked']))
        elif v['state'] == 'refused at the prompt':face.say(kv.say('door_said_no', checked=v['checked'] or 'nothing'))
        else:face.say(kv.say('door_undo_failed', title=title, why=_sentence(v.get('why') or v.get('checked'))))
        _column_soon(host)
    _later(host, lambda: _call(host, 'system.door.undo', {'run': run_id}), back, 'graphite-door-undo')


# ---- her column's NEXT STEPS ---------------------------------------------------------------------------------------------
def next_steps(host):
    """What NEXT STEPS offers for the door: the plan that waits for your press; Undo of the last change."""
    state = STATE.get(id(host)) or {};out = []
    waiting = state.get('offer')
    if waiting:
        t = waiting['plan']['title']
        out.append({'words': '%s · %s' % (t, sd.asks_words(waiting['plan']['action'])), 'verb': t, 'object': sd.asks_words(waiting['plan']['action']),
                    'kind': 'system_door', 'act': 'run', 'title': t,
                    'tip': 'What the system will do is in Talk. Your press starts it; then the system asks for your password itself.'})
    finished = state.get('done')
    if finished:
        out.append({'words': 'Undo · %s · asks for your password' % finished['title'], 'verb': 'Undo', 'object': finished['title'],
                    'kind': 'system_door', 'act': 'undo', 'title': finished['title'],
                    'tip': 'The inverse fixed action, through the system’s own prompt, read back afterwards.'})
    return out


def take(host, step):
    """A press on a door's NEXT STEP: the same press as the word in her talk."""
    state = STATE.get(id(host)) or {}
    if step.get('act') == 'run' and state.get('offer'):
        o = state['offer'];run(o['face'], o['got'], o['plan']);return True
    if step.get('act') == 'undo' and state.get('done'):
        d = state['done'];undo(d['face'], d['run'], d['title']);return True
    return False


# ---- the line on the bar, and a press anywhere that proposes -------------------------------------------------------------
def _face(host):
    shell = getattr(host, 'shell2', None)
    if shell is None:return None
    try:shell.show_slate_face()
    except Exception:  # noqa: BLE001
        pass
    return getattr(shell, 'face', None)


def propose(host, got, words=None):
    """Her talk shows the plan of one fixed action (from the line, Settings or the command tool); nothing changes."""
    face = _face(host)
    if face is None:return False
    face.mine(words or sd.title(got['action'], got.get('target', ''), got.get('value', '')));show(face, got)
    return True


def line_rows(text, host=None):
    """For line_finder: [(title, detail, do)] when the words ask for one of the door's actions; do() shows its plan."""
    try:got = sd.read_words(text)
    except Exception:  # noqa: BLE001
        return []
    if got is None:return []
    shown = '%s, %s' % (sd.title(got['action'], got.get('target', ''), got.get('value', '')), sd.asks_words(got['action']))
    return [(shown, kv.say('door_line_detail'), lambda: propose(host, got, ' '.join(str(text).split())))]


# ---- Settings > This computer > System changes ----------------------------------------------------------------------------
TITLE = 'System changes'


def _zones():
    try:
        with open(sd.ZONEINFO + '/zone1970.tab', encoding='utf-8') as f:
            return sorted({line.split('\t')[2].strip() for line in f if line.strip() and not line.startswith('#') and len(line.split('\t')) > 2} | {'UTC'})
    except OSError:
        return ['UTC']


def show_page(host):
    """Open (or bring forward) This computer's System changes page in the centre."""
    close = getattr(host, '_close_start', None)
    if callable(close):close()
    tabs = host.tabs
    for i in range(tabs.count()):
        widget = tabs.widget(i)
        if isinstance(widget, _room_class()):
            tabs.setCurrentIndex(i);widget.reload();return widget
    tab = _room_class()(host);tabs.addTab(tab, TITLE);tabs.setCurrentWidget(tab)
    return tab


_ROOM = None


def _room_class():
    global _ROOM
    if _ROOM is not None:return _ROOM
    from PySide6.QtWidgets import QComboBox, QFrame, QLineEdit, QScrollArea, QVBoxLayout, QWidget
    from .machine_room_qt import card, press, row, word, words

    class DoorRoom(QWidget):
        """The page: read off the window's thread (system.door.state, system.door.runs); each press shows a plan in her talk."""

        def __init__(self, host):
            super().__init__();self.host = host;self.key = 'door';self.data = None;self.fields = {}      # key: navigation_qt keeps Settings on this row
            self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True);self.setAccessibleName('Settings: ' + TITLE)
            outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
            self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll)
            self.draw();self.reload()

        def title(self):return TITLE

        def settings_row(self):return 'system:door'

        def inspector(self):
            return TITLE, [(TITLE, 'through the system’s own prompt')]

        def reload(self):
            def read():
                return dict(state=_call(self.host, 'system.door.state', {}), runs=_call(self.host, 'system.door.runs', {'limit': 8}))

            def landed(value, error):
                if getattr(self.host, '_closing', False):return
                self.data = value if error is None else dict(error=str(error));self.draw()
            _later(self.host, read, landed, 'graphite-door-page')

        def ask(self, action, key=None, target='', value=''):
            if key:target = self.fields[key].currentText() if isinstance(self.fields[key], QComboBox) else self.fields[key].text()
            if key == 'login':value = self.fields['real'].text()
            got = dict(action=action, target=str(target).strip(), value=str(value).strip())
            if action != 'packages.refresh' and not got['target']:return
            propose(self.host, got)

        def field(self, key, hint, text=''):
            edit = QLineEdit(text);edit.setPlaceholderText(hint);edit.setAccessibleName(hint);self.fields[key] = edit
            return edit

        def draw(self):
            data = self.data or {};self.fields = {}
            page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(14)
            box.addWidget(words(TITLE, 'title'))
            box.addWidget(words('SETTINGS / THIS COMPUTER / ' + TITLE.upper(), 'quiet'))
            box.addWidget(words('Software, services, date and time, this computer’s name and accounts. Each change is one fixed action: '
                                'Kas shows what the system will do, your press starts it, and the system asks for your password '
                                'in its own prompt. It is read back before it is called done.', 'quiet'))
            st = (data.get('state') or {}).get('result') or {}
            if data.get('error') or (data.get('state') and not data['state'].get('ok')):
                frame, inner = card();inner.addWidget(word('not read', 'stop'))
                inner.addWidget(words(data.get('error') or _why(data.get('state'))));box.addWidget(frame)
            agent = st.get('agent') or {}
            frame, inner = card();inner.addWidget(words('Permission prompts', 'section'))
            inner.addLayout(row(word('ready' if agent.get('running') else 'none', 'live' if agent.get('running') else 'stop'),
                                words(agent.get('words') or ('Reading…' if not st else '')), stretch_at=1))
            for key, s in (st.get('services') or {}).items():
                inner.addLayout(row(word('answers' if s['answers'] else 'absent', 'live' if s['answers'] else 'wait'), words(s['words']), stretch_at=1))
            box.addWidget(frame)
            frame, inner = card();inner.addWidget(words('Software', 'section'))
            inner.addLayout(row(self.field('package', 'A Debian package, for example gimp'),
                                press('Install…', lambda: self.ask('package.install', 'package')), press('Remove…', lambda: self.ask('package.remove', 'package')),
                                press('Update…', lambda: self.ask('package.update', 'package')), press('Refresh the lists…', lambda: self.ask('packages.refresh')),
                                stretch_at=0))
            box.addWidget(frame)
            frame, inner = card();inner.addWidget(words('Services', 'section'))
            inner.addLayout(row(self.field('unit', 'A service, for example cups'),
                                *[press(v + '…', lambda a='service.' + v.lower(): self.ask(a, 'unit')) for v in ('Start', 'Stop', 'Restart', 'Enable', 'Disable')],
                                stretch_at=0))
            box.addWidget(frame)
            t = st.get('time') or {}
            frame, inner = card();inner.addWidget(words('Date and time', 'section'))
            zones = QComboBox();zones.setEditable(True);zones.addItems(_zones());zones.setCurrentText(t.get('zone') or '');self.fields['zone'] = zones
            zones.setAccessibleName('Time zone')
            inner.addLayout(row(words('Time zone ' + (t.get('zone') or 'not read')), zones, press('Set the time zone…', lambda: self.ask('time.zone', 'zone')), stretch_at=1))
            ntp = t.get('ntp');switch = 'off' if ntp else 'on'
            inner.addLayout(row(word('network time on' if ntp else 'network time off', 'live' if ntp else 'quiet'),
                                words(('Synchronised' if t.get('synced') else 'Not synchronised yet') if ntp else 'The clock keeps its own time.'),
                                press('Turn it %s…' % switch, lambda: self.ask('time.ntp', target=switch), enabled=bool(t)), stretch_at=1))
            box.addWidget(frame)
            n = st.get('name') or {}
            frame, inner = card();inner.addWidget(words('This computer’s name', 'section'))
            inner.addLayout(row(words(n.get('name') or 'not read'), self.field('host', 'A new name, for example tern-lab'),
                                press('Rename…', lambda: self.ask('host.name', 'host')), stretch_at=1))
            box.addWidget(frame)
            frame, inner = card();inner.addWidget(words('Accounts', 'section'))
            for a in st.get('accounts') or []:
                inner.addLayout(row(word('account'), words('%s · %s' % (a['login'], a['real'] or 'no real name')), stretch_at=1))
            login = self.field('login', 'Account name, for example ana');login.setMinimumWidth(260)
            inner.addLayout(row(login, self.field('real', 'Real name, for example Ana Tern'),
                                press('Add a standard account…', lambda: self.ask('user.add', 'login')), stretch_at=1))
            inner.addWidget(words('The door never sets another person’s password.', 'quiet'))
            box.addWidget(frame)
            runs = ((data.get('runs') or {}).get('result') or {}).get('runs') or []
            frame, inner = card();inner.addWidget(words('What the door did, newest first', 'section'))
            if not runs:inner.addWidget(words('Nothing yet.', 'quiet'))
            for r in runs:
                tone = 'live' if r['state'] == 'done' and r['verified'] else ('quiet' if r['undone'] else 'stop')
                state = 'undone' if r['undone'] else ('done' if r['state'] == 'done' else r['state'])
                inner.addLayout(row(word(state, tone), words('%s · %s' % (r['title'], r['checked'] or '')), stretch_at=1))
            box.addWidget(frame)
            box.addStretch(1)
            old = self.scroll.takeWidget();self.scroll.setWidget(page)
            if old is not None:old.deleteLater()

    _ROOM = DoorRoom
    return _ROOM
