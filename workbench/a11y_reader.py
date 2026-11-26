"""Reading other programs (Graphite 1.0, K7): the owner's visible programs read through accessibility (AT-SPI), read only.

The owner's paper, section 10: "Applications may expose documents, commands, accessibility information, or other integration
points. Kasandra should prefer those methods when they provide more precise information than visually interpreting a window"
... "Reading the actual value of a spreadsheet cell is an observation. Inferring that a visible button probably performs a
particular action is a hypothesis until its behavior is established." And: an unexpected dialog after an action is one of
the things her perception must reach far enough to notice.

What it reads, through AT-SPI 2's own D-Bus interfaces with PySide6's QtDBus (no pyatspi: on the owner's Debian only the
package at-spi2-core is needed):
  the bus        org.a11y.Bus.GetAddress on the session D-Bus gives the accessibility bus's address (D-Bus starts at-spi2-core's
                 bus launcher on that first call where it is installed); org.a11y.Status.IsEnabled says whether the session has
                 asked programs to show their insides (some wait for it: Firefox, Qt programs).
  the programs   the registry's root (org.a11y.atspi.Registry at /org/a11y/atspi/accessible/root) lists every program that shows
                 itself; each one's process comes from the accessibility bus (GetConnectionUnixProcessID).
  its windows    each program's top-level children: frames, windows, dialogs, alerts, with their names (a window's name is its
                 title), roles and states (active, modal, showing).
  the focus      the control with the focused state under the active window, looked for within bounds; its role and name
                 (never what is typed in a field: an editable field's contents and a password field are not read).
  a dialog       its title, what it says (its labels and static text: org.a11y.atspi.Accessible's names, org.a11y.atspi.Text),
                 its buttons' names (which is the default, which can be pressed now).
A window of the window list (S3, windows_x11) is matched to its accessible window by its program's process and its title.

READ ONLY. Every call goes through call(), which refuses any method not in READ_ONLY: never Action.DoAction, never
EditableText, never Component.GrabFocus, never a property Set. Nothing here presses a button, types, moves the focus of
another program or turns accessibility on (that is the session's setting, the owner's). In 1.0 she clicks nothing through
accessibility: what a button does is "not established", always.

BOUNDED. Each call waits at most CALL_MS; one reading at most BUDGET_MS and MAX_NODES accessible objects (a program that
answers slowly, or a window with thousands of objects, gives a partial reading that says it is partial, never a stall).

Without AT-SPI (not installed, not running, no session D-Bus, Windows, a Mac) every answer says why, in words ("I cannot
see inside that program: ..."), and she relies on the program's files and its windows: the window's title (S3) is still
observed, and what it means is inferred (K2's inferences).

RECEIPTS (K2, tools_registry): a reading is "observed" when read from the accessible tree (the tool accessibility.read, 21:
the active window, the focus, each dialog's words and buttons); what a dialog means ("possibly a Save changes? prompt") is
"inferred"; without AT-SPI the observation is "unavailable", with the reason. The registry's slot accessibility.read is
filled here, and K2's ACCESSIBILITY hook is set, so a look at the windows reads a prompt's buttons when it can.

HER STEPS (K1, assignments): DialogWatch looks, before one of her changes is sent and after its effect is checked, for a
dialog that appeared meanwhile in a program (a new dialog in the window list, or a new dialog in the accessible tree). Such a
step "needs review": its journal says "a dialog appeared while it ran", its receipts carry the dialog's words and buttons
(observed through accessibility) or its title alone (inferred, with why its inside could not be read), and her column shows
the words to the owner. She presses nothing in that dialog: it is the owner's to answer.

Kernel operations (registered in engineering_kernel and engineering_cli under "1.0 K7"; reads, observers):
  accessibility.status  {}                  read   whether she can see inside programs here, and why not
  accessibility.read    {window?, focus?}   read   the active window, its focused control and the dialogs open; or one window
                                                   (its id from windows.observe), as receipts (observed, inferred,
                                                   unavailable); a look, not kept (tools.use keeps it)

No floating point in anything checked: times are whole milliseconds; digests are compared as text.
"""
from __future__ import annotations

import os
import re
import sys
import threading
import time

from . import assignments as _asg

SCHEMA = 'graphite.accessibility/1'
TOOL = 'accessibility.read'
SOURCE = 'AT-SPI over D-Bus (at-spi2-core)'
PACKAGE = 'at-spi2-core'
BUS_SERVICE, BUS_PATH, BUS_IFACE, STATUS_IFACE = 'org.a11y.Bus', '/org/a11y/bus', 'org.a11y.Bus', 'org.a11y.Status'
REGISTRY, ROOT = 'org.a11y.atspi.Registry', '/org/a11y/atspi/accessible/root'
NULL_PATH = '/org/a11y/atspi/null'
ACCESSIBLE, APPLICATION, TEXT = 'org.a11y.atspi.Accessible', 'org.a11y.atspi.Application', 'org.a11y.atspi.Text'
PROPS, DBUS = 'org.freedesktop.DBus.Properties', 'org.freedesktop.DBus'
# The only methods the reader calls. Anything else (DoAction, SetText, GrabFocus, a property Set ...) is refused before it is sent.
READ_ONLY = frozenset({(BUS_IFACE, 'GetAddress'), (PROPS, 'Get'), (ACCESSIBLE, 'GetRoleName'), (ACCESSIBLE, 'GetRole'),
                       (ACCESSIBLE, 'GetState'), (ACCESSIBLE, 'GetChildren'), (TEXT, 'GetText'), (DBUS, 'GetConnectionUnixProcessID')})
CALL_MS = 500               # one call
BUDGET_MS = 3000            # one reading
MAX_NODES = 600             # accessible objects read in one reading
MAX_DEPTH = 16
MAX_APPS = 60
MAX_TOPS = 40               # top-level windows of one program
DIALOG_NODES = 240          # objects read inside one dialog
MAX_TEXT = 6                # lines of what a dialog says
MAX_LINE = 300
MAX_BUTTONS = 12
SETTLE_MS = 600             # after one of her changes, how long a dialog is given to appear before the look
AVAILABLE_MS = 3000         # how long the answer "can she see inside programs here?" is kept before it is asked again
# AT-SPI's states (AtspiStateType), as bits of GetState's two words.
ACTIVE, DEFUNCT, EDITABLE, ENABLED, FOCUSED, MODAL, SENSITIVE, SHOWING, VISIBLE, MANAGES, IS_DEFAULT = 1, 6, 7, 8, 12, 16, 24, 25, 30, 31, 39
# AT-SPI's roles (AtspiRole) the reader needs, by number, for a program that gives no role name.
ROLE_NUMBERS = {2: 'alert', 16: 'dialog', 19: 'file chooser', 23: 'frame', 29: 'label', 36: 'option pane', 40: 'password text',
                43: 'push button', 61: 'text', 62: 'toggle button', 69: 'window', 73: 'paragraph', 75: 'application', 83: 'heading',
                116: 'static'}
DIALOG_ROLES = frozenset({'dialog', 'alert', 'file chooser', 'option pane', 'color chooser', 'font chooser'})
BUTTON_ROLES = frozenset({'push button', 'toggle button', 'button'})
TEXT_ROLES = frozenset({'label', 'static', 'text', 'paragraph', 'heading', 'caption'})
PRIVATE_ROLES = frozenset({'password text'})
# What a dialog's words read like: a hint only (K2 keeps the same two patterns for a window's title).
SAVE_PROMPT = re.compile(r'save (the |your )?changes|unsaved|do you want to save|save before|keep (the )?current format|discard changes'
                         r'|close without saving|not (been )?saved|has been modified|changes will be lost|save document', re.I)
ERROR_PROMPT = re.compile(r'\berror\b|\bfailed\b|\bcannot\b|\bcan\'t\b|could not|\bwarning\b|not responding|\bcrash', re.I)


class Unavailable(Exception):
    """She cannot see inside programs here; str() is the plain reason."""


class OutOfTime(Exception):
    """The reading's bounds were reached: what was read is kept, and the reading says it is partial."""


class CallFailed(Exception):
    def __init__(self, name, message):
        super().__init__(message or name);self.name = name or '';self.message = message or name or 'it did not answer'


def _now_ms():
    return time.time_ns() // 1000000


def unseen(what='that program'):
    """Her sentence for an inside she cannot read."""
    return 'I cannot see inside %s' % what


def said_unavailable(reason, what='that program', whose='its'):
    return '%s: %s. I rely on %s files and %s windows.' % (unseen(what), str(reason).rstrip('.'), whose, whose)


def _button_name(name):
    """A button's name as it is shown: without a toolkit's mnemonic mark (no key is ever named on screen)."""
    name = re.sub(r'(?<![_~])[_~](?=\w)', '', str(name or ''), count=1)
    return name.replace('&&', '&').strip()


# ---------------------------------------------------------------- the buses

def why_not_platform(platform=None):
    platform = sys.platform if platform is None else platform
    if platform.startswith('win') or platform == 'cygwin':
        return 'Graphite reads other programs through AT-SPI, the accessibility of the Linux desktop, and Windows has none'
    if platform == 'darwin':
        return 'Graphite reads other programs through AT-SPI, the accessibility of the Linux desktop, and this Mac has none'
    return None


def plain(value):
    """A QtDBus answer as plain Python (S4's reader of QtDBus values: maps, arrays, structures, variants, object paths)."""
    from .machine_real import plain as _plain
    return _plain(value)


_LOCK = threading.RLock()
_BUS = {}                   # 'address', 'name', 'conn': the accessibility bus, once reached


def _session():
    try:
        from PySide6.QtDBus import QDBusConnection
    except Exception as exc:  # noqa: BLE001 - no QtDBus: she says so
        raise Unavailable("Qt's D-Bus module is not here (%s)" % str(exc)[:120]) from None
    conn = QDBusConnection.sessionBus()
    if not conn.isConnected():
        raise Unavailable('there is no session D-Bus here (%s), and AT-SPI is reached through it'
                          % (conn.lastError().message() or 'not connected').strip()[:120])
    return conn


def _raw_call(conn, service, path, iface, method, *args, timeout=CALL_MS):
    if (iface, method) not in READ_ONLY:
        raise PermissionError('READ_ONLY: %s.%s is not a reading; in 1.0 nothing is pressed or typed through accessibility' % (iface, method))
    from PySide6.QtDBus import QDBus, QDBusMessage
    message = QDBusMessage.createMethodCall(service, path, iface, method)
    if args:message.setArguments(list(args))
    reply = conn.call(message, QDBus.CallMode.Block, max(1, int(timeout)))
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        raise CallFailed(reply.errorName() or '', (reply.errorMessage() or '').strip()[:200])
    return [plain(v) for v in reply.arguments()]


def enabled():
    """Whether the session asked programs to show their insides (org.a11y.Status.IsEnabled); None when it cannot be read."""
    try:
        values = _raw_call(_session(), BUS_SERVICE, BUS_PATH, PROPS, 'Get', STATUS_IFACE, 'IsEnabled')
        return bool(values[0]) if values else None
    except Exception:  # noqa: BLE001 - unknown is said as unknown
        return None


def connection():
    """The accessibility bus (QDBusConnection), reached once and kept; Unavailable with the reason when it cannot be."""
    why = why_not_platform()
    if why:raise Unavailable(why)
    with _LOCK:
        conn = _BUS.get('conn')
        if conn is not None and conn.isConnected():return conn
        session = _session()
        try:
            address = _raw_call(session, BUS_SERVICE, BUS_PATH, BUS_IFACE, 'GetAddress', timeout=4 * CALL_MS)
        except CallFailed as failed:
            if failed.name in ('org.freedesktop.DBus.Error.ServiceUnknown', 'org.freedesktop.DBus.Error.NameHasNoOwner',
                               'org.freedesktop.DBus.Error.NoServer', 'org.freedesktop.DBus.Error.Spawn.ExecFailed'):
                raise Unavailable('AT-SPI is not running on this computer: nothing answers as org.a11y.Bus on the session D-Bus. '
                                  'Debian has it as the package %s, in the 1.0 System set' % PACKAGE) from None
            raise Unavailable('AT-SPI did not give its bus (%s)' % failed.message[:160]) from None
        address = str((address or [''])[0] or '')
        if not address:raise Unavailable('AT-SPI gave no address for its bus')
        from PySide6.QtDBus import QDBusConnection
        if _BUS.get('name'):
            QDBusConnection.disconnectFromBus(_BUS['name'])
        _BUS['n'] = _BUS.get('n', 0) + 1
        name = 'graphite-k7-a11y-%d' % _BUS['n']
        conn = QDBusConnection.connectToBus(address, name)
        if not conn.isConnected():
            message = (conn.lastError().message() or 'not connected').strip()[:160]
            QDBusConnection.disconnectFromBus(name)
            raise Unavailable('the accessibility bus did not let Graphite in (%s)' % message)
        _BUS.update(address=address, name=name, conn=conn)
        return conn


def forget():
    """Reach the accessibility bus afresh on the next reading (after it was restarted, or for a stand-in)."""
    _SAID.clear()
    with _LOCK:
        if _BUS.get('name'):
            try:
                from PySide6.QtDBus import QDBusConnection
                QDBusConnection.disconnectFromBus(_BUS['name'])
            except Exception:  # noqa: BLE001
                pass
        for key in ('address', 'name', 'conn'):_BUS.pop(key, None)


# ---------------------------------------------------------------- one reading

class Reading:
    """One reading's connection and bounds: calls are counted and timed, and the reading says why it is partial."""

    def __init__(self, conn, budget_ms=BUDGET_MS, max_nodes=MAX_NODES):
        self.conn = conn;self.end = time.monotonic_ns() + budget_ms * 1000000;self.max_nodes = max_nodes
        self.nodes = 0;self.calls = 0;self.partial = [];self.pids = {}

    def left_ms(self):
        return (self.end - time.monotonic_ns()) // 1000000

    def call(self, service, path, iface, method, *args):
        left = self.left_ms()
        if left <= 0:raise OutOfTime('the reading took its whole time')
        self.calls += 1
        return _raw_call(self.conn, service, path, iface, method, *args, timeout=min(CALL_MS, left))

    def short(self, why):
        if why not in self.partial:self.partial.append(why)

    def node(self, ref):
        """{'ref', 'name', 'role', 'states'} of one accessible object; None when it is gone."""
        if self.nodes >= self.max_nodes:raise OutOfTime('it read as many objects as one reading may (%d)' % self.max_nodes)
        self.nodes += 1
        service, path = ref
        try:
            name = self.call(service, path, PROPS, 'Get', ACCESSIBLE, 'Name')
            states = self.call(service, path, ACCESSIBLE, 'GetState')
        except CallFailed as failed:
            if failed.name.endswith('NoReply'):
                self.short('a program did not answer in time');return None
            if failed.name.endswith(('UnknownObject', 'UnknownMethod', 'ServiceUnknown', 'Disconnected')):return None
            raise
        try:role = str((self.call(service, path, ACCESSIBLE, 'GetRoleName') or [''])[0] or '')
        except CallFailed:role = ''
        if not role:
            try:role = ROLE_NUMBERS.get(int((self.call(service, path, ACCESSIBLE, 'GetRole') or [0])[0] or 0), '')
            except (CallFailed, TypeError, ValueError):role = ''
        bits = set()
        for word, value in enumerate(list((states or [[]])[0] or [])[:2]):
            for i in range(32):
                if int(value) >> i & 1:bits.add(word * 32 + i)
        return {'ref': (service, path), 'name': str((name or [''])[0] or '').strip(), 'role': role.lower(), 'states': bits}

    def children(self, ref):
        service, path = ref
        try:found = (self.call(service, path, ACCESSIBLE, 'GetChildren') or [[]])[0] or []
        except CallFailed as failed:
            if failed.name.endswith('NoReply'):self.short('a program did not answer in time')
            return []
        out = []
        for item in found:
            if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] and item[1] and item[1] != NULL_PATH:
                out.append((str(item[0]), str(item[1])))
        return out

    def text(self, ref):
        service, path = ref
        try:return str((self.call(service, path, TEXT, 'GetText', 0, -1) or [''])[0] or '').strip()
        except CallFailed:return ''

    def pid(self, service):
        if service not in self.pids:
            try:self.pids[service] = int((self.call(DBUS, '/org/freedesktop/DBus', DBUS, 'GetConnectionUnixProcessID', service) or [0])[0] or 0) or None
            except (CallFailed, TypeError, ValueError):self.pids[service] = None
        return self.pids[service]


def _shown(node):
    """A top-level window that is on screen (or a program that does not say: then it is taken as shown)."""
    states = node['states']
    if DEFUNCT in states:return False
    return not states or VISIBLE in states or SHOWING in states


def _is_dialog(node):
    return node['role'] in DIALOG_ROLES or MODAL in node['states']


def registered(rd):
    """The programs on the accessibility bus, as the registry lists them; CallFailed when the registry does not answer."""
    found = (rd.call(REGISTRY, ROOT, ACCESSIBLE, 'GetChildren') or [[]])[0] or []
    return [(str(i[0]), str(i[1])) for i in found if isinstance(i, (list, tuple)) and len(i) == 2 and i[0] and i[1] and i[1] != NULL_PATH]


def programs(rd):
    """[{'name', 'pid', 'ref', 'tops': [node...]}]: the programs that show themselves, with their top-level windows (Graphite's
    own process left out: it is not "another program")."""
    out = []
    for ref in registered(rd)[:MAX_APPS]:
        try:
            if rd.pid(ref[0]) == os.getpid():continue
            app = rd.node(ref)
            if app is None:continue
            tops = []
            for child in rd.children(ref)[:MAX_TOPS]:
                top = rd.node(child)
                if top is not None and _shown(top):tops.append(top)
            out.append({'name': app['name'] or ref[0], 'pid': rd.pid(ref[0]), 'ref': ref, 'tops': tops})
        except OutOfTime as out_of_time:
            rd.short(str(out_of_time));break
        except CallFailed as failed:
            rd.short('a program did not answer (%s)' % failed.message[:80])
    return out


def _inside(rd, top):
    """What one window says: its title, its words (labels, static text; never a field's contents), its buttons."""
    words, buttons, fields, seen = [], [], 0, {top['name']}
    queue = [(top, 0)];complete = True;start = rd.nodes
    while queue:
        node, depth = queue.pop(0)
        if rd.nodes - start >= DIALOG_NODES:complete = False;rd.short('a window has more objects than are read for it');break
        if node is not top:
            role, name = node['role'], node['name']
            if role in BUTTON_ROLES:
                if name and len(buttons) < MAX_BUTTONS:
                    buttons.append({'name': _button_name(name)[:80], 'default': IS_DEFAULT in node['states'],
                                    'enabled': ENABLED in node['states'] or SENSITIVE in node['states'] or not node['states']})
                continue
            if role in PRIVATE_ROLES or (EDITABLE in node['states'] and role not in ('label', 'static')):
                fields += 1;continue                     # what is typed in a field is never read, a password above all
            if role in TEXT_ROLES:
                said = name or rd.text(node['ref'])
                for line in [x.strip() for x in said.splitlines() if x.strip()]:
                    if line not in seen and len(words) < MAX_TEXT:
                        seen.add(line);words.append(line[:MAX_LINE])
        if depth >= MAX_DEPTH or MANAGES in node['states']:continue
        try:
            for ref in rd.children(node['ref']):
                child = rd.node(ref)
                if child is not None:queue.append((child, depth + 1))
        except OutOfTime as out_of_time:
            complete = False;rd.short(str(out_of_time));break
    return {'title': top['name'][:300], 'role': top['role'], 'text': words, 'buttons': buttons, 'fields': fields,
            'modal': MODAL in top['states'], 'active': ACTIVE in top['states'], 'complete': complete}


def _focused(rd, top):
    """The control with the focus under the active window: its role and name (a field's contents are never read)."""
    queue = [(top, 0)];start = rd.nodes
    while queue:
        node, depth = queue.pop(0)
        if node is not top and FOCUSED in node['states']:
            private = node['role'] in PRIVATE_ROLES
            name = _button_name(node['name']) if node['role'] in BUTTON_ROLES else node['name']
            return {'role': node['role'], 'name': '' if private else name[:200], 'editable': EDITABLE in node['states']}
        if rd.nodes - start >= MAX_NODES // 2:rd.short('the focus was looked for in part of the window only');return None
        if depth >= MAX_DEPTH or MANAGES in node['states'] or (node is not top and node['states'] and SHOWING not in node['states']):continue
        for ref in rd.children(node['ref']):
            child = rd.node(ref)
            if child is not None:queue.append((child, depth + 1))
    return None


def _windows_rows():
    """The window list's rows (S3), when there is one: [{id, title, program, pid, dialog, graphite, ...}]."""
    try:
        from . import windows_x11
        watcher = windows_x11.shared()
        if not watcher.start():return []
        return [dict(r) for r in watcher.refresh().get('windows') or ()]
    except Exception:  # noqa: BLE001 - no window list: the accessible windows are named by their titles alone
        return []


def _match(row, apps):
    """The accessible window of a window-list row: same title, the program's own process first; else a title that holds the
    other. (app, top) or (None, None)."""
    title = str(row.get('title') or '').strip();pid = row.get('pid')
    if not title:return None, None
    pairs = [(app, top) for app in apps for top in app['tops']]
    for test in (lambda a, t: t['name'] == title and pid and a['pid'] == pid, lambda a, t: t['name'] == title,
                 lambda a, t: t['name'] and pid and a['pid'] == pid and (t['name'] in title or title in t['name'])):
        found = [(a, t) for a, t in pairs if test(a, t)]
        if found:
            if row.get('dialog'):found.sort(key=lambda p: not _is_dialog(p[1]))
            return found[0]
    return None, None


def _row_of(top, app, rows):
    """The window-list row of an accessible window (by its title, its program's process first), or None."""
    named = [r for r in rows if str(r.get('title') or '').strip() == top['name'] and top['name']]
    mine = [r for r in named if app['pid'] and r.get('pid') == app['pid']]
    return (mine or named or [None])[0]


def _dialog_view(app, top, inside, row):
    return {'window': (row or {}).get('id', ''), 'program': (row or {}).get('program') or app['name'], 'pid': app['pid'],
            'title': inside['title'], 'role': inside['role'], 'text': inside['text'], 'buttons': inside['buttons'],
            'fields': inside['fields'], 'modal': inside['modal'], 'complete': inside['complete'], 'graphite': bool((row or {}).get('graphite'))}


def _quoted(text, most=160):
    text = str(text or '').strip()
    return '“%s”' % (text if len(text) <= most else text[:most - 1] + '…')


def _closed(quoted):
    """A quotation that ends a sentence: a full stop after it unless the words inside already end one."""
    return quoted if quoted[-2:-1] in ('.', '?', '!', '…') else quoted + '.'


def dialog_words(d, lead=None, fields=True):
    """A dialog in words: where, its title, its buttons (the default marked), what it says (and, with `fields`, that a field's
    contents were not read)."""
    buttons = ', '.join(b['name'] + (' (the default)' if b.get('default') else '') + ('' if b.get('enabled', True) else ' (greyed out)')
                        for b in d.get('buttons') or ())
    parts = [(lead or 'A dialog in %s' % (d.get('program') or 'a program')) + ': ' + _closed(_quoted(d.get('title') or '(no title)'))]
    if buttons:parts.append('Buttons: %s.' % buttons)
    if d.get('text'):parts.append('It says: %s' % _closed(_quoted(' '.join(d['text']), 220)))
    if fields and d.get('fields'):parts.append('It has %s field%s; what is typed in it is not read.' % (d['fields'], '' if d['fields'] == 1 else 's'))
    return ' '.join(parts)


def meaning(d):
    """What a dialog probably is, from its title and its words ('' when nothing reads so): an inference, never established."""
    said = ' '.join([d.get('title') or ''] + list(d.get('text') or ()))
    if SAVE_PROMPT.search(said):return 'a "Save changes?" prompt'
    if ERROR_PROMPT.search(said):return 'an error or a warning'
    return ''


def status():
    """Whether she can see inside programs here, and why not: {'available', 'reason', 'words', 'enabled', 'programs'}."""
    out = {'schema': SCHEMA, 'tool': TOOL, 'source': SOURCE, 'read_only': True, 'available': False, 'reason': '', 'enabled': None,
           'programs': 0, 'words': ''}
    try:
        rd = Reading(connection(), budget_ms=1500)
        apps = registered(rd)
        out.update(available=True, programs=len(apps), enabled=enabled())
    except Unavailable as why:
        out.update(reason=str(why), words=said_unavailable(why, 'other programs here', 'their'))
        return out
    except (CallFailed, OutOfTime) as failed:
        forget()
        out.update(reason='the accessibility bus is here, but its registry does not answer (%s)' % str(failed)[:120])
        out['words'] = said_unavailable(out['reason'], 'other programs here', 'their')
        return out
    words = 'I can read inside the programs that show themselves to accessibility: %d do now.' % out['programs']
    if out['enabled'] is False:
        words += (' Accessibility is off in this session (org.a11y.Status), so some programs (Firefox and Qt programs among them) do '
                  'not show their insides until it is on; turning it on is your setting.')
    out['words'] = words
    return out


_SAID = {}                  # the last answer of available(), for AVAILABLE_MS: the registry's list asks it for every view


def available():
    """(whether the reader can be used here now, why not in words): the tool registry's slot asks this."""
    now = time.monotonic_ns() // 1000000
    if _SAID and now - _SAID['at'] < AVAILABLE_MS:return _SAID['answer']
    state = status()
    answer = (bool(state['available']), '' if state['available'] else state['words'])
    _SAID.update(at=now, answer=answer)
    return answer


def read(window=None, focus=True):
    """One reading: the active window, its focused control, the dialogs open; with `window` (an id of the window list), that
    window's inside as well. Never stalls past BUDGET_MS; a partial reading says so."""
    began = _now_ms()
    out = {'schema': SCHEMA, 'tool': TOOL, 'source': SOURCE, 'read_only': True, 'available': False, 'reason': '', 'complete': False,
           'programs': [], 'active': None, 'focused': None, 'dialogs': [], 'target': None, 'words': '', 'at': began}
    try:
        rd = Reading(connection())
    except Unavailable as why:
        out.update(reason=str(why), words=said_unavailable(why));return out
    rows = _windows_rows()
    try:
        apps = programs(rd)
    except (CallFailed, OutOfTime) as failed:
        forget()
        out.update(reason='the accessibility bus is here, but its registry does not answer (%s)' % str(failed)[:120])
        out['words'] = said_unavailable(out['reason']);return out
    out.update(available=True, programs=[{'name': a['name'], 'pid': a['pid'], 'windows': len(a['tops'])} for a in apps])
    try:
        for app in apps:
            for top in app['tops']:
                row = _row_of(top, app, rows)
                if row is not None and row.get('graphite'):continue        # Graphite's own windows are not "another program"
                if ACTIVE in top['states'] and out['active'] is None:
                    out['active'] = {'window': (row or {}).get('id', ''), 'program': (row or {}).get('program') or app['name'], 'pid': app['pid'],
                                     'title': top['name'][:300], 'role': top['role'], 'top': top}
                if _is_dialog(top):
                    out['dialogs'].append(_dialog_view(app, top, _inside(rd, top), row))
        if focus and out['active'] is not None:
            out['focused'] = _focused(rd, out['active']['top'])
        if window:
            wanted = next((r for r in rows if r.get('id') == str(window)), None)
            if wanted is None:
                out['target'] = {'window': str(window), 'found': False,
                                 'words': 'The window %s is not in the window list now%s.' % (window, '' if rows else ' (there is no window list here)')}
            else:
                app, top = _match(wanted, apps)
                if top is None:
                    out['target'] = {'window': wanted['id'], 'found': False, 'title': wanted.get('title', ''), 'program': wanted.get('program', ''),
                                     'words': said_unavailable('it does not show itself to accessibility (its window "%s" is not in the accessible '
                                                               'tree)' % str(wanted.get('title', ''))[:80])}
                else:
                    out['target'] = dict(_dialog_view(app, top, _inside(rd, top), wanted), found=True)
    except OutOfTime as out_of_time:
        rd.short(str(out_of_time))
    except CallFailed as failed:
        rd.short('a program did not answer (%s)' % failed.message[:80])
    if out['active'] is not None:out['active'].pop('top', None)
    out['complete'] = not rd.partial and all(d['complete'] for d in out['dialogs'])
    out['partial'] = list(rd.partial)
    out['calls'] = rd.calls;out['elapsed_ms'] = _now_ms() - began
    out['words'] = reading_words(out)
    return out


def reading_words(r):
    if not r.get('available'):return r.get('words') or said_unavailable(r.get('reason') or 'it is not here')
    parts = ['Read through accessibility: %d program%s show%s %s.' % (len(r['programs']), '' if len(r['programs']) == 1 else 's',
                                                                       's' if len(r['programs']) == 1 else '', 'itself' if len(r['programs']) == 1 else 'themselves')]
    a = r.get('active')
    parts.append(('The active window: %s (%s).' % (_quoted(a['title'], 100), a['program'])) if a else 'No window of theirs is active.')
    f = r.get('focused')
    if f:parts.append('Its focused control: %s%s.' % (f['role'] or 'a control', (' ' + _quoted(f['name'], 80)) if f['name'] else ''))
    dialogs = [d for d in r.get('dialogs') or () if not d.get('graphite')]
    if dialogs:parts.append('Dialogs open: %s.' % '; '.join('%s in %s' % (_quoted(d['title'], 90), d['program']) for d in dialogs[:4]))
    if r.get('partial'):parts.append('Partly read: %s.' % '; '.join(r['partial'][:2]))
    return ' '.join(parts)


def inside(window):
    """K2's ACCESSIBILITY hook: one window of the window list read inside. {'available', 'reason', 'title', 'text', 'buttons'}."""
    reading = read(window=(window or {}).get('id'), focus=False)
    if not reading['available']:return {'available': False, 'reason': reading['reason'] or reading['words']}
    target = reading.get('target') or {}
    if not target.get('found'):return {'available': False, 'reason': 'it does not show itself to accessibility'}
    return {'available': True, 'reason': '', 'title': target['title'], 'text': list(target['text']),
            'buttons': [b['name'] for b in target['buttons']], 'program': target['program'], 'complete': target['complete']}


def dialog_keys():
    """The dialogs open now in the accessible tree, by their objects ({(service, path): (program, title)}); {} without AT-SPI."""
    try:rd = Reading(connection(), budget_ms=1500)
    except Unavailable:return None
    out = {}
    try:
        for app in programs(rd):
            for top in app['tops']:
                if _is_dialog(top):out[top['ref']] = (app['name'], top['name'])
    except (CallFailed, OutOfTime):
        pass
    return out


# ---------------------------------------------------------------- receipts (K2)

def _registry():
    from . import tools_registry
    return tools_registry


def reading_digest(r):
    return _asg.digest({'active': [(r.get('active') or {}).get(k) for k in ('program', 'title')], 'focused': r.get('focused'),
                        'dialogs': [[d['program'], d['title'], d['text'], [b['name'] for b in d['buttons']]] for d in r.get('dialogs') or ()],
                        'target': [(r.get('target') or {}).get(k) for k in ('title', 'text')]})


def receipts(r, owner='', **more):
    """A reading as receipts: unavailable (with why); or the reading observed, each dialog's words and buttons observed, and what a
    dialog probably is inferred, each following the one it rests on."""
    tr = _registry()
    target = r.get('target') or {}
    obj = ('window:' + target['window']) if target.get('window') else 'accessibility'
    if not r.get('available'):
        return [tr.receipt(TOOL, TOOL, obj, 'unavailable', 'unavailable', False, r.get('words') or said_unavailable(r.get('reason')),
                           basis='the accessibility reader says why', owner=owner, detail={'reason': str(r.get('reason') or '')[:300]}, **more)]
    a = r.get('active') or {}
    place = {'window': target.get('window') or a.get('window', ''), 'title': target.get('title') or a.get('title', ''),
             'program': target.get('program') or a.get('program', '')}
    main = tr.receipt(TOOL, TOOL, obj, 'observed', 'observed', bool(r.get('complete')), r.get('words', ''), revision=reading_digest(r),
                      place=place, basis='the accessible tree (AT-SPI), read now', owner=owner,
                      detail={'focused': r.get('focused'), 'dialogs': len(r.get('dialogs') or ()), 'partial': r.get('partial') or []}, **more)
    made = [main]
    shown = list(r.get('dialogs') or ())
    if target.get('found') and not any(d['title'] == target['title'] and d['program'] == target['program'] for d in shown):shown.insert(0, target)
    for d in shown:
        if d.get('graphite'):continue
        made.extend(dialog_receipts(d, owner=owner, follows=main['id'], **more))
    return made


def dialog_receipts(d, owner='', follows='', lead=None, **more):
    """One dialog read through accessibility: observed (its title, words and buttons), then what it probably is, inferred."""
    tr = _registry()
    obj = 'window:' + d['window'] if d.get('window') else 'accessibility:' + str(d.get('program') or 'a program')[:60]
    place = {'window': d.get('window', ''), 'title': d.get('title', ''), 'program': d.get('program', '')}
    seen = tr.receipt(TOOL, TOOL, obj, 'observed', 'observed', bool(d.get('complete')), dialog_words(d, lead) + ' Read through accessibility.',
                      revision=_asg.digest([d.get('title'), d.get('text'), [b['name'] for b in d.get('buttons') or ()]]), place=place,
                      basis='its accessible tree (AT-SPI), read now', owner=owner, follows=follows,
                      detail={'text': list(d.get('text') or ()), 'buttons': list(d.get('buttons') or ()), 'fields': d.get('fields', 0)}, **more)
    out = [seen]
    kind = meaning(d)
    if kind:
        out.append(tr.receipt(TOOL, TOOL, obj, 'inferred', 'inferred', False,
                              'Possibly %s in %s: its title and its words read so. What its buttons do is not established; nothing was pressed.'
                              % (kind, d.get('program') or 'a program'), revision=seen['revision'], place=place,
                              basis='its words, read through accessibility', owner=owner, follows=seen['id'], detail={'kind': kind}, **more))
    return out


def observation_of(result):
    """K1's observation of an accessibility.read step (and tools.use's): observed, with what each dialog probably is as K2's
    inferences (so its receipts are written with the step's journal row)."""
    if not (result or {}).get('available'):
        raise _asg.NotVerified(str((result or {}).get('words') or said_unavailable((result or {}).get('reason') or 'it is not here'))[:400])
    target = result.get('target') or {};a = result.get('active') or {}
    inferences = []
    for d in [d for d in result.get('dialogs') or () if not d.get('graphite')][:8]:
        kind = meaning(d)
        if not kind:continue
        inferences.append({'kind': kind, 'window': d.get('window') or '', 'title': d['title'][:200], 'program': d['program'], 'dialog': True,
                           'basis': 'its words, read through accessibility', 'read_inside': True,
                           'words': ('Possibly %s in %s. %s What its buttons do is not established; nothing was pressed.'
                                     % (kind, d['program'], dialog_words(d, 'Read through accessibility')))[:600]})
    return {'object': ('window:' + target['window']) if target.get('window') else 'accessibility', 'revision': reading_digest(result),
            'by': 'accessibility', 'complete': bool(result.get('complete')), 'how': 'observed',
            'window': target.get('window') or a.get('window', ''), 'title': (target.get('title') or a.get('title') or '')[:200],
            'program': target.get('program') or a.get('program') or '', 'words': str(result.get('words') or '')[:600],
            'dialogs': [{'title': d['title'][:200], 'program': d['program'], 'buttons': [b['name'] for b in d['buttons']]}
                        for d in (result.get('dialogs') or ())[:6]], 'inferences': inferences}


class AccessibilityRead(_asg.Check):
    """accessibility.read: a reading of the accessible tree is its own observation (read now); what a dialog means is inferred.
    Programs move all the time, so a reading is never re-checked later: it is of its moment."""
    kind = 'accessibility';effect = 'nothing (a read)';standin_ms = 800;repeatable = True
    how = 'the accessible tree (AT-SPI), read now; what a dialog means is marked inferred'
    expected = "the active program's window, its focused control and the dialogs open, as the programs show them"

    def prepare(self, kernel, read_, arguments):
        ok, why = available()
        if not ok:raise _asg.Blocked(why)
        return {}

    def find(self, kernel, read_, arguments, prepared):
        return None

    def verify(self, kernel, read_, arguments, result, prepared, step):
        return observation_of(result)

    def still(self, kernel, read_, step):
        return ''


# ---------------------------------------------------------------- her steps (K1): a dialog that appeared while one ran

class DialogWatch:
    """assignments.DIALOG_WATCH: mark() before one of her changes is sent, notice() after its effect is checked, keep() in the
    transaction of the step's journal row. Reads only; it presses nothing."""
    settle_ms = SETTLE_MS

    def mark(self, kernel, step):
        if (step or {}).get('scope') == 'read':return None
        token = {'at_ns': time.monotonic_ns(), 'seq': None, 'a11y': None}
        try:
            from . import windows_x11
            watcher = windows_x11.shared()
            if watcher.start():
                look = watcher.observe()
                if look.get('available'):token['seq'] = int(look['seq'])
        except Exception:  # noqa: BLE001 - no window list: the accessible tree alone is watched
            token['seq'] = None
        keys = dialog_keys()
        token['a11y'] = None if keys is None else sorted([list(k) for k in keys])
        return token if token['seq'] is not None or token['a11y'] is not None else None

    def notice(self, kernel, step, token):
        if not token:return None
        wait_ms = self.settle_ms - (time.monotonic_ns() - token['at_ns']) // 1000000
        if wait_ms > 0:time.sleep(wait_ms / 1000)
        found = []
        if token.get('seq') is not None:
            try:
                from . import windows_x11
                look = windows_x11.shared().observe(token['seq'])
                open_now = {w['id']: w for w in look.get('windows') or ()}
                for event in look.get('events') or ():
                    row = open_now.get(event.get('window'))
                    if row is None or row.get('graphite') or any(f['window'] == row['id'] for f in found):continue
                    if event.get('event') == 'a new dialog appeared' or (event.get('event') == 'a new window appeared'
                                                                         and (SAVE_PROMPT.search(row['title']) or ERROR_PROMPT.search(row['title']))):
                        found.append({'window': row['id'], 'title': row['title'], 'program': row['program'], 'row': row})
            except Exception:  # noqa: BLE001 - a window list that fails now leaves the accessible tree's look
                pass
        if token.get('a11y') is not None:
            before = {tuple(k) for k in token['a11y']}
            now = dialog_keys() or {}
            for key, (program, title) in now.items():
                if key in before or any(f['title'] == title for f in found):continue
                found.append({'window': '', 'title': title, 'program': program, 'row': None})
        if not found:return None
        return self._words(found[:4])

    def _words(self, found):
        tr = _registry()
        lines, dialogs, made = [], [], []
        for f in found:
            row = f['row']
            seen = None
            if row is not None:
                reading = read(window=row['id'], focus=False)
                target = reading.get('target') or {}
                if reading.get('available') and target.get('found'):seen = target
                why = reading.get('reason') or ('it does not show itself to accessibility' if reading.get('available') else '')
            else:
                reading = read(focus=False)
                seen = next((d for d in reading.get('dialogs') or () if d['title'] == f['title'] and d['program'] == f['program']), None)
                why = reading.get('reason') or ''
            if seen is not None:
                lead = 'In %s, a dialog appeared while it ran, and I pressed nothing' % seen['program']
                lines.append(dialog_words(seen, lead, fields=False) + ' It is yours to answer.')
                dialogs.append({'title': seen['title'], 'program': seen['program'], 'window': seen.get('window', ''), 'read': 'accessibility',
                                'text': seen['text'], 'buttons': [b['name'] for b in seen['buttons']]})
                made.extend(dialog_receipts(seen, lead=lead))
            else:
                kind = meaning({'title': f['title']})
                said = ('In %s, a dialog appeared while it ran, and I pressed nothing: %s %s: its words and buttons were not read%s. It '
                        'is yours to answer.' % (f['program'] or 'a program', _closed(_quoted(f['title'])), unseen('that program') + (' (%s)' % str(why).rstrip('.')[:160] if why else ''),
                                              ('; by its title it is possibly %s' % kind) if kind else ''))
                lines.append(said)
                dialogs.append({'title': f['title'], 'program': f['program'], 'window': f['window'], 'read': 'title only', 'why': str(why)[:200]})
                made.append(tr.receipt('windows.observe', 'windows.observe', 'window:' + f['window'] if f['window'] else 'windows', 'inferred', 'inferred', False,
                                       said, revision=f['window'], place={'window': f['window'], 'title': f['title'], 'program': f['program']},
                                       basis='its window title (the window list); its inside could not be read', detail={'kind': kind, 'why': str(why)[:200]}))
        return {'words': ' '.join(lines)[:900], 'dialogs': dialogs, 'receipts': made}

    def keep(self, db, value, step, noticed, seq):
        """The notice's receipts, linked to the step and its journal row, following the step's verified receipt when there is one."""
        tr = _registry()
        tr.ensure(db)
        last = db.execute("SELECT id FROM tool_receipts WHERE assignment=? AND step=? AND status IN ('verified','not verified') "
                          "ORDER BY at DESC, rowid DESC LIMIT 1", (value['id'], step['key'])).fetchone()
        follows = last[0] if last else ''
        for n, item in enumerate(noticed.get('receipts') or ()):
            item.update(owner=str(value.get('owner') or '')[:200], assignment=value['id'], step=step['key'],
                        journal=seq if type(seq) is int else None, at=tr._now_ms() + n)   # kept now, after the step's own receipts
            if not item.get('follows'):item['follows'] = follows
            tr.keep(db, item)


# ---------------------------------------------------------------- the Kernel's operations (1.0 K7)

WINDOW = {'type': 'string', 'minLength': 3, 'maxLength': 20}
FIELDS = {'accessibility.status': ({}, []),
          'accessibility.read': ({'window': WINDOW, 'focus': {'type': 'boolean'}}, [])}
SCOPES = {'accessibility.status': 'read', 'accessibility.read': 'read'}
OBSERVERS = tuple(FIELDS)


def dispatch(kernel, op, args, principal):
    if op == 'accessibility.status':return status()
    if op == 'accessibility.read':
        reading = read(window=args.get('window'), focus=args.get('focus', True))
        reading['receipts'] = receipts(reading, owner=principal.identity)
        reading['kept'] = False
        return reading
    raise ValueError('Unknown accessibility operation')


# ---------------------------------------------------------------- joined to K1 and K2

def _join():
    """The tool registry's slot accessibility.read filled, K2's ACCESSIBILITY hook set, K1's dialog watch set. Guarded: what is
    not here is left as it is."""
    try:
        _asg.TOOL_WORDS.setdefault('accessibility', 'accessibility')
        if 'DIALOG_SEEN' not in _asg.EFFECT_ENTRIES:_asg.EFFECT_ENTRIES = tuple(_asg.EFFECT_ENTRIES) + ('DIALOG_SEEN',)
        _asg.SAYS.setdefault('DIALOG_SEEN', 'a dialog appeared while it ran')
        if hasattr(_asg, 'DIALOG_WATCH'):_asg.DIALOG_WATCH = DialogWatch()
    except Exception:  # noqa: BLE001 - the assignments keep their own words
        pass
    try:
        from . import tools_registry
    except Exception:  # noqa: BLE001 - K2 is not in this Graphite
        return False
    try:
        tools_registry.fill(TOOL, available=available, operations=('accessibility.read',), callable='workbench.a11y_reader:read',
                            check=AccessibilityRead())
        tools_registry.ACCESSIBILITY = inside
    except Exception:  # noqa: BLE001 - a slot shaped otherwise is left for the coordinator
        return False
    return True


JOINED = _join()
