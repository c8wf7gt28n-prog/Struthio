"""Graphite 1.0 S5 · Graphite as the session's notification server (org.freedesktop.Notifications, spec 1.2, over QtDBus).

Programs say things ("download finished", "the battery is low") by calling org.freedesktop.Notifications on the session bus,
as notify-send does. In the dedicated session Graphite owns that name, so those calls arrive here:

  Notify(app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout) -> id
                          the notification is kept (the newest NOTES_KEPT), shown quietly by notify_qt (a toast at the foot
                          of her column that never takes the focus) and written to the activity journal, so Log keeps it
                          ("Notification from an app · “Rail Demo app”: Bench readings saved — Rev B is on disk"). A
                          replaces_id that is not 0 updates that notification and keeps its id.
  CloseNotification(id)   closes it; NotificationClosed(id, 3) is sent.
  GetCapabilities()       body, actions, persistence (they are kept in Log).
  GetServerInformation()  Graphite, Graphite, Graphite's version, 1.2.
  NotificationClosed(id, reason)   1 it expired, 2 you closed it, 3 the program closed it, 4 other (Graphite closed).
  ActionInvoked(id, action_key)    you pressed one of its actions (the "default" action: you pressed its words).

What a program sends is data, never an instruction: the words are shown as plain text (markup taken out, the length capped),
Kasandra does not act on them, and a program's name is always shown as the name it gave ("“…”"), so a program calling
itself Kasandra is never read as her. Nothing here sends anything out. An urgent notification (urgency 2) stays until you
close it; expire_timeout -1 is Graphite's own time (DEFAULT_SECONDS), 0 never. A "transient" notification is shown but
not kept in Log (the spec's word). A program that floods is kept to FLOOD_PER_MINUTE lines in Log a minute; the rest are
counted.

Whether Graphite serves: in the dedicated session (ARC_LEDGER_XSESSION=1), or wherever GRAPHITE_NOTIFICATIONS=1; never with
GRAPHITE_NOTIFICATIONS=0. Graphite never takes the name from a program that already holds it (another desktop's own
notifications go on as they were): it says who holds it. Without a session bus it says so. The name goes with Graphite's
process; the supervisor starts Graphite again and it takes the name again.
"""
from __future__ import annotations

import html
import os
import re
import time

NAME = 'org.freedesktop.Notifications'
PATH = '/org/freedesktop/Notifications'
SPEC = '1.2'
CAPABILITIES = ('body', 'actions', 'persistence')
DEFAULT_SECONDS = 8                # how long a notification shows when the program leaves it to Graphite (-1)
LONGEST_SECONDS = 60               # a program's own time is kept between 2 s and this
NOTES_KEPT = 200                   # the newest kept in memory (the Settings page's list); Log keeps them all
FLOOD_PER_MINUTE = 20              # lines in Log from one program in a minute; the rest are counted
SUMMARY_MOST, BODY_MOST, APP_MOST, ACTIONS_MOST = 200, 1000, 80, 6
REASONS = {1: 'expired', 2: 'closed by you', 3: 'closed by the app', 4: 'closed by Graphite'}
URGENCY = {0: 'low', 1: 'normal', 2: 'urgent'}
TAG = re.compile(r'<[^>]{0,200}>')
CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')


def wanted(environ=None):
    """(serve, why): whether Graphite should be the session's notification server here."""
    environ = os.environ if environ is None else environ
    said = str(environ.get('GRAPHITE_NOTIFICATIONS', '')).strip().lower()
    if said in ('0', 'off', 'no'):return False, 'Graphite does not show notifications here: GRAPHITE_NOTIFICATIONS is off.'
    if said in ('1', 'on', 'yes'):return True, ''
    if environ.get('ARC_LEDGER_XSESSION') == '1':return True, ''
    return False, ('Graphite shows notifications from apps in its own session (Graphite as the desktop). Here it was started '
                   'inside another desktop, which shows them itself.')


def plain(text, most):
    """A program's words as plain text: markup taken out, entities read, controls dropped, at most `most` characters."""
    text = TAG.sub('', str(text or ''))
    text = html.unescape(text)
    text = CONTROL.sub(' ', text).strip()
    return text if len(text) <= most else text[:most - 1].rstrip() + '…'


def number(value, default=0):
    try:return int(value)
    except (TypeError, ValueError):return default


def hint_words(hints):
    """The hints Graphite reads, as plain values (image data and anything else unknown is left out)."""
    out = {}
    for key in ('urgency', 'category', 'desktop-entry', 'transient', 'resident', 'suppress-sound'):
        value = (hints or {}).get(key)
        if value is None:continue
        if key == 'urgency':out[key] = max(0, min(2, number(value, 1)))
        elif key in ('transient', 'resident', 'suppress-sound'):out[key] = bool(value) if not isinstance(value, str) else value.lower() in ('1', 'true')
        elif isinstance(value, str):out[key] = plain(value, 80)
    return out


def clock(stamp):
    return time.strftime('%H:%M', time.localtime(stamp))


def log_words(note):
    """The line Log keeps (the program's name as the name it gave)."""
    body = (' — ' + note['body']) if note['body'] else ''
    urgent = ' (urgent)' if note['urgency'] == 2 else ''
    return '“%s”: %s%s%s' % (note['app'] or 'an app with no name', note['summary'] or '(no title)', body, urgent)


class Notes:
    """The notifications as Graphite keeps them, with no Qt: made, replaced, closed, an action pressed. Each change calls
    `changed(kind, note)` ('shown', 'replaced', 'closed', 'action'). The D-Bus side (Service) and the window (notify_qt) both
    use one Notes."""

    def __init__(self, log=None, clock_=time.time):
        self.log = log;self.now = clock_
        self.open = {};self.kept = [];self.next_id = 1;self.listeners = [];self.flood = {};self.counted = 0

    def listen(self, fn):
        self.listeners.append(fn)

    def _tell(self, kind, note):
        for fn in list(self.listeners):
            try:fn(kind, note)
            except Exception:  # noqa: BLE001 - a listener that broke never stops a program's notification
                continue

    def add(self, app, replaces_id, icon, summary, body, actions, hints, expire_timeout):
        replaces_id = number(replaces_id)
        hints = hint_words(dict(hints or {}))
        pairs = list(actions or [])
        acts = [(plain(pairs[i], 64), plain(pairs[i + 1], 40) or plain(pairs[i], 40)) for i in range(0, len(pairs) - 1, 2)][:ACTIONS_MOST]
        if replaces_id > 0:
            ident = replaces_id;self.next_id = max(self.next_id, ident + 1)
        else:
            ident = self.next_id;self.next_id += 1
        urgency = hints.get('urgency', 1)
        timeout = number(expire_timeout, -1)
        if urgency == 2:seconds = None                                           # urgent: until you close it
        elif timeout == 0:seconds = None
        elif timeout < 0:seconds = DEFAULT_SECONDS
        else:seconds = max(2, min(LONGEST_SECONDS, round(timeout / 1000)))
        note = dict(id=ident, app=plain(app, APP_MOST), icon=plain(icon, 200), summary=plain(summary, SUMMARY_MOST),
                    body=plain(body, BODY_MOST), actions=acts, urgency=urgency, urgency_words=URGENCY[urgency],
                    category=hints.get('category', ''), desktop_entry=hints.get('desktop-entry', ''),
                    transient=bool(hints.get('transient')), resident=bool(hints.get('resident')), seconds=seconds,
                    at=self.now(), closed=None, logged=False)
        replaced = ident in self.open
        self.open[ident] = note
        self.kept = [n for n in self.kept if n['id'] != ident] + [note]
        del self.kept[:-NOTES_KEPT]
        note['logged'] = self._log(note)
        self._tell('replaced' if replaced else 'shown', note)
        return ident

    def _log(self, note):
        """Into the activity journal (Log's Events), unless the program called it transient or floods."""
        if note['transient'] or self.log is None:return False
        minute = int(self.now() // 60);key = note['app'] or '?'
        count = self.flood.get(key)
        if count is None or count[0] != minute:count = [minute, 0]
        count[1] += 1;self.flood[key] = count
        if count[1] > FLOOD_PER_MINUTE:
            self.counted += 1;return False
        try:self.log(note)
        except Exception:  # noqa: BLE001 - Log that cannot be written never stops the notification being shown
            return False
        return True

    def close(self, ident, reason):
        note = self.open.pop(number(ident), None)
        if note is None:return None
        note['closed'] = REASONS.get(reason, REASONS[4]);note['closed_code'] = reason;note['closed_at'] = self.now()
        self._tell('closed', note)
        return note

    def action(self, ident, key):
        note = self.open.get(number(ident))
        if note is None:return None
        keys = [k for k, _ in note['actions']]
        if key not in keys and key != 'default':return None
        note['pressed'] = key
        self._tell('action', note)
        return note

    def recent(self, limit=20):
        return [dict(n) for n in reversed(self.kept[-limit:])]


# ---- the D-Bus side ---------------------------------------------------------------------------------------------------------
_CLASSES = []


def _server_class():
    """The exported object, made on first use (Qt is imported then): exactly the four methods and two signals of the spec,
    nothing else of Graphite's is reachable on the bus."""
    if _CLASSES:return _CLASSES[0]
    from PySide6.QtCore import ClassInfo, QObject, Signal, Slot
    from PySide6.QtDBus import QDBusMessage

    @ClassInfo({'D-Bus Interface': NAME})
    class Server(QObject):
        NotificationClosed = Signal('uint', 'uint')
        ActionInvoked = Signal('uint', str)

        def __init__(self, service):
            super().__init__();self.service = service

        @Slot(str, 'uint', str, str, str, 'QStringList', 'QVariantMap', int, result='uint')
        def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):  # noqa: N802 - the spec's names
            return self.service.notify(app_name, replaces_id, app_icon, summary, body, list(actions or []), dict(hints or {}), expire_timeout)

        @Slot('uint')
        def CloseNotification(self, ident):  # noqa: N802
            self.service.close(ident, 3)

        @Slot(result='QStringList')
        def GetCapabilities(self):  # noqa: N802
            return list(CAPABILITIES)

        @Slot(QDBusMessage)
        def GetServerInformation(self, message):  # noqa: N802
            message.setDelayedReply(True)
            reply = message.createReply();reply.setArguments(['Graphite', 'Graphite', version(), SPEC])
            self.service.bus.send(reply)

    _CLASSES.append(Server)
    return Server


def version():
    """Graphite's version as the kit's MANIFEST.json says it (GetServerInformation)."""
    try:
        import json
        from pathlib import Path
        said = json.loads((Path(__file__).resolve().parent.parent / 'MANIFEST.json').read_text(encoding='utf-8')).get('version')
        if isinstance(said, str) and re.fullmatch(r'[\w.+-]{1,32}', said):return said
    except (OSError, ValueError, AttributeError):pass
    return '1.0'


def _int(value):
    """A Qt enum or a number, as a number (PySide6's enums do not compare equal to ints)."""
    return int(getattr(value, 'value', value))


class Service:
    """Graphite on the session bus as org.freedesktop.Notifications: start() takes the name (never from a program that holds
    it), stop() gives it back. state: 'serving', 'elsewhere' (another program holds the name), 'no bus', 'off' (not wanted
    here), 'failed'; why: the plain words."""

    def __init__(self, notes=None, environ=None, bus=None):
        self.notes = notes or Notes();self.environ = environ;self.bus = bus;self.server = None
        self.state = 'off';self.why = '';self.owner = ''

    def start(self, force=False):
        serve, why = wanted(self.environ)
        if not serve and not force:
            self.state, self.why = 'off', why;return False
        from PySide6.QtDBus import QDBusConnection, QDBusConnectionInterface
        bus = self.bus or QDBusConnection.sessionBus();self.bus = bus
        if not bus.isConnected():
            self.state, self.why = 'no bus', ('There is no session bus here (%s), so programs cannot send notifications to '
                                              'Graphite.' % (' '.join((bus.lastError().message() or 'not connected').split())));return False
        face = bus.interface()
        held = face.isServiceRegistered(NAME)
        if held.isValid() and held.value():
            owner = face.serviceOwner(NAME)
            self.owner = owner.value() if owner.isValid() else ''
            pid = face.servicePid(NAME)
            pid = pid.value() if pid.isValid() else 0
            self.state, self.why = 'elsewhere', ('Another program already shows the notifications here (%s%s), so Graphite leaves '
                                                 'them to it.' % (program_of(pid) or 'bus name ' + self.owner, (', process %d' % pid) if pid else ''))
            return False
        self.server = _server_class()(self)
        if not bus.registerObject(PATH, self.server, QDBusConnection.ExportAllSlots | QDBusConnection.ExportAllSignals):
            self.state, self.why = 'failed', 'Graphite could not offer its notification object: ' + (bus.lastError().message() or 'refused')
            self.server = None;return False
        reply = face.registerService(NAME, QDBusConnectionInterface.DontQueueService, QDBusConnectionInterface.DontAllowReplacement)
        if not reply.isValid() or _int(reply.value()) != _int(QDBusConnectionInterface.ServiceRegistered):
            bus.unregisterObject(PATH);self.server = None
            self.state, self.why = 'elsewhere', 'Another program took the notifications name first, so Graphite leaves them to it.'
            return False
        self.state, self.why = 'serving', 'Graphite shows the notifications apps send in this session, and keeps them in Log.'
        return True

    def stop(self):
        if self.state != 'serving' or self.bus is None:return
        try:
            self.bus.unregisterService(NAME);self.bus.unregisterObject(PATH)
        except RuntimeError:  # the bus went with the application
            pass
        self.server = None;self.state, self.why = 'off', 'Graphite has closed.'

    # what the program asked
    def notify(self, app, replaces_id, icon, summary, body, actions, hints, expire_timeout):
        return self.notes.add(app, replaces_id, icon, summary, body, actions, hints, expire_timeout)

    def close(self, ident, reason):
        note = self.notes.close(ident, reason)
        if note is not None and self.server is not None:self.server.NotificationClosed.emit(int(note['id']), int(reason))
        return note

    # what you did
    def invoke(self, ident, key):
        """You pressed an action (or the notification's words: 'default'): ActionInvoked, then it closes (2) unless it is
        resident."""
        note = self.notes.action(ident, key)
        if note is None:return None
        if self.server is not None:self.server.ActionInvoked.emit(int(note['id']), str(key))
        if not note['resident']:self.close(note['id'], 2)
        return note

    def dismiss(self, ident):
        return self.close(ident, 2)

    def expire(self, ident):
        return self.close(ident, 1)

    def status(self):
        return dict(state=self.state, why=self.why, owner=self.owner, capabilities=list(CAPABILITIES), spec=SPEC,
                    shown=len(self.notes.kept), open=len(self.notes.open), not_logged=self.notes.counted)


def program_of(pid):
    """A process's program name from /proc (who holds the notifications name), or ''."""
    try:
        with open('/proc/%d/comm' % int(pid), encoding='utf-8') as f:return f.read().strip()[:40]
    except (OSError, ValueError, TypeError):
        return ''
