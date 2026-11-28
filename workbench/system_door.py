"""The system door (Graphite 1.1 KS3): software, services, time, the computer's name and users, changed through the
system's own services and their own permission prompt, with the owner present. One fixed action per prompt; never under a
standing grant; never as her own step.

The owner's reversal 8 (PLAN_1.1.md section 6): "Outside your home: never" for Kas becomes "system changes through the
system's own prompt, the owner present". Her rules do not move: the model proposes, the desk disposes. Every action here is
one of the fixed ACTIONS below, validated first, shown first (what the system will do, what it pulls in and its size, that
the system will ask for your password, and what Undo does or that it cannot be undone), started only by the owner's press
(system.door.run, approve scope, with the digest of what was shown), then asked again by the system's own prompt (polkit, through
the session's permission prompt agent: lxpolkit in the dedicated session; the password is typed there, never into Graphite),
and verified after by reading the system's own state back. HALT refuses to start one and cancels a PackageKit transaction
that is still waiting (when PackageKit lets it).

Each action goes to the service Debian 13 has for it, which asks through polkit by itself; there is no shell, no sudo, no
pkexec and no helper of Graphite's:

  software   PackageKit (org.freedesktop.PackageKit): install, remove or update one named package, refresh the lists, list
             updates. Validated by Resolve; shown by a SIMULATE transaction (what it pulls in) and GetDetails (sizes).
  services   systemd (org.freedesktop.systemd1): start, stop, restart, enable, disable one named unit; its state; its journal
             (journalctl, a fixed argv: the journal has no D-Bus reader). Validated by LoadUnit (LoadState).
  time       timedated (org.freedesktop.timedate1): the time zone (validated against /usr/share/zoneinfo), network time on or
             off, the clock (only with network time off).
  name       hostnamed (org.freedesktop.hostname1): the computer's name.
  users      accountsservice (org.freedesktop.Accounts): add a standard account, set an account's real name. Never a
             password: the door has no action for one.

The bus is system_bus's own client (DBUS_SYSTEM_BUS_ADDRESS when set). offer(argv) maps a root command line (sudo apt install
gimp, systemctl restart cups, timedatectl set-timezone ...) to its fixed action, for the command tool (KS2) to hand over:
"that is the system door".

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.1 KS3):
  system.door.plan   read      what the action will do, validated and simulated; nothing changes, nothing is asked
  system.door.run    approve   the owner's press: the plan again, the same digest, then the service (its own prompt), then verified
  system.door.undo   approve   the owner's press on Undo: the inverse fixed action, through the same prompt, verified
  system.door.runs   read      the door's record, newest first
  system.door.read   read      a read the door offers: the updates, a unit's state and journal, the time, the name, the accounts
  system.door.state  read      which services answer here, whether a prompt can open, and the readings Settings shows
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import pwd
import re
import shlex
import subprocess
import time
import uuid

from . import system_bus as sb

# ---- the services ---------------------------------------------------------------------------------------------------------
PK, PK_PATH, PK_TX = 'org.freedesktop.PackageKit', '/org/freedesktop/PackageKit', 'org.freedesktop.PackageKit.Transaction'
SD, SD_PATH, SD_MGR, SD_UNIT = 'org.freedesktop.systemd1', '/org/freedesktop/systemd1', 'org.freedesktop.systemd1.Manager', 'org.freedesktop.systemd1.Unit'
TD, TD_PATH = 'org.freedesktop.timedate1', '/org/freedesktop/timedate1'
HN, HN_PATH = 'org.freedesktop.hostname1', '/org/freedesktop/hostname1'
AC, AC_PATH, AC_USER = 'org.freedesktop.Accounts', '/org/freedesktop/Accounts', 'org.freedesktop.Accounts.User'
SERVICES = {'software': (PK, 'PackageKit', 'packagekit'), 'services': (SD, 'systemd', 'systemd'), 'time': (TD, 'timedated', 'systemd'),
            'name': (HN, 'hostnamed', 'systemd'), 'users': (AC, 'the accounts service', 'accountsservice')}

# PackageKit's enums (pk-enum.h): bitfields are 1 << value
FILTER_NONE, FILTER_INSTALLED, FILTER_NOT_INSTALLED, FILTER_NEWEST, FILTER_ARCH = 1 << 1, 1 << 2, 1 << 3, 1 << 16, 1 << 18
ONLY_TRUSTED, SIMULATE = 1 << 1, 1 << 2
INSTALLED, AVAILABLE, UPDATING, INSTALLING, REMOVING, OBSOLETING, REINSTALLING, DOWNGRADING = 1, 2, 11, 12, 13, 15, 19, 20
EXIT_SUCCESS, EXIT_CANCELLED = 1, 3
PK_NOT_AUTHORIZED, PK_DEPS, PK_SYSTEM_PACKAGE = 48, 13, 20
SAID_NO = ('org.freedesktop.DBus.Error.AccessDenied', 'org.freedesktop.PolicyKit1.Error.NotAuthorized',
           'org.freedesktop.PolicyKit1.Error.Cancelled', 'org.freedesktop.Accounts.Error.PermissionDenied',
           'org.freedesktop.DBus.Error.AuthFailed')
NO_PROMPT = ('org.freedesktop.DBus.Error.InteractiveAuthorizationRequired',)
GONE = ('org.freedesktop.DBus.Error.ServiceUnknown', 'org.freedesktop.DBus.Error.NameHasNoOwner', 'org.freedesktop.DBus.Error.NoServer',
        'org.freedesktop.DBus.Error.Spawn.ServiceNotFound', 'org.freedesktop.DBus.Error.Disconnected')

PROMPT_SECONDS = 300         # a call that may show the system's prompt waits this long for the owner
INSTALL_SECONDS = 3600       # a PackageKit transaction (a download and an install) may take this long
UNIT_SECONDS = 90            # a unit's job is followed this long
ZONEINFO = '/usr/share/zoneinfo'
UNIT_DIRS = ('/etc/systemd/system', '/run/systemd/system', '/usr/lib/systemd/system', '/lib/systemd/system')
RUNS_MOST = 50

PACKAGE = re.compile(r'^[a-z0-9][a-z0-9+.-]{1,99}$')
UNIT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9:_.\\@-]{0,120}\.(service|socket|timer|path)$')
ZONE = re.compile(r'^(?:[A-Za-z][A-Za-z0-9_+-]*/){0,2}[A-Za-z0-9][A-Za-z0-9_+-]*$')
HOST = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
LOGIN = re.compile(r'^[a-z][a-z0-9_-]{0,30}$')
REAL = re.compile(r'^[^\x00-\x1f:,=\\]{1,64}$')
# What the door never stops, restarts or disables (it would end the session, the door itself or the computer's start), and
# packages it never removes (the session and the door); the services say no to most of these themselves, the door first.
KEPT_UNITS = re.compile(r'^(dbus|dbus-broker|polkit|systemd-[a-z-]+|display-manager|lightdm|gdm3?|sddm|getty@.*|user@.*|'
                        r'user-runtime-dir@.*|packagekit|accounts-daemon|graphite.*)\.(service|socket)$')
KEPT_PACKAGES = frozenset(('graphite', 'graphite-session', 'graphite-desktop', 'packagekit', 'polkitd', 'lxpolkit', 'dbus', 'dbus-daemon',
                           'dbus-bin', 'systemd', 'systemd-sysv', 'apt', 'dpkg', 'libc6', 'sudo', 'fluxbox', 'xserver-xorg', 'xserver-xorg-core',
                           'python3', 'base-files', 'init', 'login', 'passwd', 'accountsservice', 'network-manager'))
RESERVED_LOGINS = frozenset(('root', 'admin', 'administrator', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 'mail', 'news', 'uucp',
                             'proxy', 'www-data', 'backup', 'list', 'irc', 'nobody', 'systemd', 'messagebus', 'polkitd', 'sudo', 'adm',
                             'staff', 'users', 'kasandra', 'graphite'))
# How a package reads on screen (invented examples of a Windows hand's apps); any other package by its own name
PRETTY = {'gimp': 'GIMP', 'vlc': 'VLC', 'inkscape': 'Inkscape', 'libreoffice': 'LibreOffice', 'firefox-esr': 'Firefox ESR',
          'thunderbird': 'Thunderbird', 'gparted': 'GParted', 'audacity': 'Audacity', 'krita': 'Krita', 'blender': 'Blender',
          'git': 'Git', 'cups': 'CUPS', 'htop': 'htop', 'gnome-disk-utility': 'Disks', 'transmission-gtk': 'Transmission',
          'keepassxc': 'KeePassXC', 'shotwell': 'Shotwell', 'evince': 'Evince', 'mpv': 'mpv', 'ffmpeg': 'FFmpeg', '7zip': '7-Zip'}

# One fixed action each: (verb, what the target is, the service, whether it changes)
ACTIONS = {
    'package.install': ('Install', 'package', 'software'), 'package.remove': ('Remove', 'package', 'software'),
    'package.update': ('Update', 'package', 'software'), 'packages.refresh': ('Refresh', None, 'software'),
    'service.start': ('Start', 'unit', 'services'), 'service.stop': ('Stop', 'unit', 'services'),
    'service.restart': ('Restart', 'unit', 'services'), 'service.enable': ('Enable', 'unit', 'services'),
    'service.disable': ('Disable', 'unit', 'services'), 'time.zone': ('Set the time zone', 'zone', 'time'),
    'time.ntp': ('Turn network time', 'switch', 'time'), 'time.set': ('Set the clock', 'clock', 'time'),
    'host.name': ('Name this computer', 'host', 'name'), 'user.add': ('Add the account', 'login', 'users'),
    'user.realname': ('Set the real name', 'login', 'users')}
READS = ('updates', 'service', 'time', 'name', 'users')


class Refused(ValueError):
    """A refusal in words: CODE: what and why. Nothing was asked and nothing changed."""


class SaidNo(Exception):
    """The system's own prompt was cancelled or refused (or no prompt could open)."""

    def __init__(self, why, prompt=True):
        super().__init__(why);self.prompt = prompt


# ---- small words ----------------------------------------------------------------------------------------------------------
def pretty(name):
    return PRETTY.get(str(name), str(name))


def size_words(n):
    n = int(n or 0)
    if n >= 1 << 30:return '%.1f GB' % (n / (1 << 30))
    if n >= 1 << 20:return '%.1f MB' % (n / (1 << 20))
    if n >= 1 << 10:return '%d KB' % (n // (1 << 10))
    return '%d bytes' % n


def listing(names, most=6):
    names = list(names)
    if len(names) <= most:return ', '.join(names)
    return '%s and %d more' % (', '.join(names[:most]), len(names) - most)


def plural(n, one, many=None):
    return '%d %s' % (n, one if n == 1 else (many or one + 's'))


def title(action, target='', value=''):
    """The action's name as she says it: Install GIMP, Restart cups.service, Set the time zone to Europe/Lisbon."""
    verb, kind, _ = ACTIONS[action]
    if kind == 'package':return '%s %s' % (verb, pretty(target))
    if kind == 'unit':return '%s %s' % (verb, target)
    if action == 'packages.refresh':return 'Refresh the software lists'
    if action == 'time.zone':return 'Set the time zone to %s' % target
    if action == 'time.ntp':return 'Turn network time %s' % target
    if action == 'time.set':return 'Set the clock to %s' % target
    if action == 'host.name':return 'Name this computer “%s”' % target
    if action == 'user.add':return 'Add the account “%s”' % target
    return 'Set the real name of “%s” to “%s”' % (target, value)


def asks_words(action):
    """What the row in the line says about the prompt."""
    return 'asks for your password'


# ---- the bus, and what the services answer -------------------------------------------------------------------------------
class System:
    """One action's talk with the system's services: one connection, opened when first needed."""

    def __init__(self, halt=None, addr=None):
        self.halt = halt;self.addr = addr;self._bus = None

    @property
    def bus(self):
        if self._bus is None:self._bus = sb.Bus(self.addr)
        return self._bus

    def close(self):
        if self._bus is not None:self._bus.close();self._bus = None

    def call(self, dest, path, iface, member, sig='', args=(), interactive=False, timeout=None):
        return self.bus.call(dest, path, iface, member, sig, args, interactive=interactive,
                             timeout=timeout or (PROMPT_SECONDS if interactive else sb.TIMEOUT))

    def prop(self, dest, path, iface, name):
        return self.bus.get(dest, path, iface, name)

    def props(self, dest, path, iface):
        return self.bus.get_all(dest, path, iface)

    # -- PackageKit
    def transaction(self, method, sig='', args=(), interactive=False, seconds=None):
        """One PackageKit transaction: its Package, Details and ErrorCode signals and its exit, gathered until Finished.
        HALT (self.halt) cancels it while PackageKit allows."""
        path = self.call(PK, PK_PATH, PK, 'CreateTransaction')[0]
        self.bus.listen(path=path)
        self.call(PK, path, PK_TX, 'SetHints', 'as', (['locale=C.UTF-8', 'interactive=%s' % ('true' if interactive else 'false'),
                                                        'background=false'],))
        self.call(PK, path, PK_TX, method, sig, args, interactive=interactive)
        out = dict(packages=[], details=[], errors=[], exit=None, cancelled=False, path=path)
        deadline = time.monotonic() + (seconds or (INSTALL_SECONDS if interactive else 120))
        while True:
            if self.halt is not None and not out['cancelled'] and self.halt():
                try:self.call(PK, path, PK_TX, 'Cancel')
                except sb.BusError:
                    pass
                out['cancelled'] = True
            try:m = self._signal(path, min(deadline, time.monotonic() + 1.0))
            except TimeoutError:
                if time.monotonic() >= deadline:raise
                continue
            if m.member == 'Package':out['packages'].append(dict(info=m.body[0], id=m.body[1], summary=m.body[2]))
            elif m.member == 'Details':out['details'].append(dict(m.body[0]))
            elif m.member == 'ErrorCode':out['errors'].append(dict(code=m.body[0], text=m.body[1]))
            elif m.member == 'Finished':
                out['exit'] = m.body[0];return out

    def _signal(self, path, deadline):
        bus = self.bus
        for i, m in enumerate(bus.waiting):
            if m.path == path:return bus.waiting.pop(i)
        while True:
            m = bus.read(deadline)
            if m.kind == sb.SIGNAL and m.path == path:return m
            if m.kind == sb.SIGNAL:bus.waiting.append(m)

    def resolve(self, name, flags=FILTER_NONE):
        got = self.transaction('Resolve', 'tas', (flags, [name]))
        _pk_failed(got)
        return [dict(p, **split_id(p['id'])) for p in got['packages'] if split_id(p['id'])['name'] == name]

    def details(self, ids):
        if not ids:return {}
        got = self.transaction('GetDetails', 'as', (list(ids),))
        return {d.get('package-id'): d for d in got['details']}

    # -- systemd
    def unit(self, name):
        path = self.call(SD, SD_PATH, SD_MGR, 'LoadUnit', 's', (name,))[0]
        p = self.props(SD, path, SD_UNIT)
        try:file_state = self.call(SD, SD_PATH, SD_MGR, 'GetUnitFileState', 's', (name,))[0]
        except sb.BusError:
            file_state = p.get('UnitFileState') or ''
        return dict(path=path, id=p.get('Id') or name, description=p.get('Description') or '', load=p.get('LoadState') or '',
                    active=p.get('ActiveState') or '', sub=p.get('SubState') or '', file=file_state or '',
                    entered=int(p.get('ActiveEnterTimestamp') or 0))


def split_id(package_id):
    parts = (str(package_id).split(';') + ['', '', '', ''])[:4]
    return dict(name=parts[0], version=parts[1], arch=parts[2], data=parts[3])


def _pk_failed(got, doing=''):
    """A transaction that did not end in success, in words (SaidNo for the prompt's no)."""
    if got['exit'] == EXIT_SUCCESS:return
    errors = got['errors']
    if any(e['code'] == PK_NOT_AUTHORIZED or 'authenticat' in e['text'].lower() or 'authoriz' in e['text'].lower() for e in errors):
        raise SaidNo('the system’s prompt was cancelled or refused')
    if got['cancelled'] or got['exit'] == EXIT_CANCELLED:raise Refused('DOOR_CANCELLED: HALT cancelled it before PackageKit began')
    why = '; '.join(e['text'].strip().rstrip('.') for e in errors if e['text'].strip()) or 'PackageKit gave no reason'
    raise Refused('DOOR_SOFTWARE: %s%s' % (doing, why[:300]))


def _bus_words(exc, service='software'):
    """A bus failure as a refusal in words."""
    _, name, package = SERVICES[service]
    if isinstance(exc, TimeoutError):return 'DOOR_TIMEOUT: %s did not answer in time' % name
    if exc.name in GONE:
        if exc.name == 'org.freedesktop.DBus.Error.NoServer':return 'DOOR_NO_BUS: there is no system bus here, so the system cannot be asked'
        return 'DOOR_NO_SERVICE: %s is not answering on this computer (Debian’s package “%s” has it)' % (name, package)
    return 'DOOR_REFUSED: %s said: %s' % (name, (exc.text or exc.name)[:300])


# ---- the permission prompt ------------------------------------------------------------------------------------------------
def prompt_agent():
    try:
        from . import polkit_agent
        return polkit_agent.agent()
    except Exception as exc:  # noqa: BLE001
        return dict(running=False, name=None, pid=None, words='Could not tell whether a permission prompt can open: %s' % exc)


# ---- validating and planning ----------------------------------------------------------------------------------------------
def unit_name(text):
    name = str(text or '').strip()
    if name and '.' not in name.rsplit('@', 1)[-1]:name += '.service'
    return name


def unit_known(text, dirs=None):
    """Whether a unit file of that name is on this computer (a look at the unit folders; the line and her words use it)."""
    name = unit_name(text)
    if not UNIT.match(name):return False
    base = name.split('@', 1)[0] + '@.' + name.rsplit('.', 1)[1] if '@' in name else name
    return any(os.path.exists(os.path.join(d, n)) for d in (dirs or UNIT_DIRS) for n in {name, base})


def zone_file(zone, base=None):
    """The zone's own file in /usr/share/zoneinfo when it is a real zone (a TZif file), else None."""
    base = base or ZONEINFO;zone = str(zone)
    if not ZONE.match(zone) or zone.split('/')[0] in ('posix', 'right'):return None
    path = os.path.join(base, zone)
    try:
        if not os.path.isfile(path):return None
        with open(path, 'rb') as f:return path if f.read(4) == b'TZif' else None
    except OSError:
        return None


def zone_spelled(text, base=None):
    """A zone as the owner wrote it, in its own spelling (europe/lisbon -> Europe/Lisbon), or the text when none matches."""
    base = base or ZONEINFO;parts = str(text or '').strip().split('/');where = base;out = []
    for part in parts:
        try:names = os.listdir(where)
        except OSError:
            return str(text).strip()
        hit = next((n for n in names if n.lower() == part.lower()), None)
        if hit is None:return str(text).strip()
        out.append(hit);where = os.path.join(where, hit)
    return '/'.join(out)


def _validate(action, target, value):
    if action not in ACTIONS:raise Refused('DOOR_UNKNOWN: the door has no action “%s”' % action)
    kind = ACTIONS[action][1];target = str(target or '').strip();value = str(value or '').strip()
    if kind == 'package':
        target = target.lower()
        if not PACKAGE.match(target):raise Refused('DOOR_NAME: “%s” is not a Debian package name' % target)
        if action == 'package.remove' and target in KEPT_PACKAGES:
            raise Refused('DOOR_KEPT: “%s” keeps this session or the door itself working, so the door does not remove it' % target)
    elif kind == 'unit':
        target = unit_name(target)
        if not UNIT.match(target):raise Refused('DOOR_NAME: “%s” is not a service name' % target)
        if action in ('service.stop', 'service.restart', 'service.disable') and KEPT_UNITS.match(target):
            raise Refused('DOOR_KEPT: %s keeps this session or the door itself working, so the door does not %s it'
                          % (target, ACTIONS[action][0].lower()))
    elif kind == 'zone':
        target = zone_spelled(target)
        if not zone_file(target):raise Refused('DOOR_ZONE: there is no time zone “%s” in %s' % (target, ZONEINFO))
    elif kind == 'switch':
        target = {'true': 'on', 'yes': 'on', '1': 'on', 'false': 'off', 'no': 'off', '0': 'off'}.get(target.lower(), target.lower())
        if target not in ('on', 'off'):raise Refused('DOOR_SWITCH: network time is turned on or off')
    elif kind == 'clock':
        _clock(target)
    elif kind == 'host':
        target = target.lower()
        if not HOST.match(target) or target in ('localhost',):
            raise Refused('DOOR_NAME: “%s” cannot be a computer’s name: letters, digits and hyphens, at most sixty-three' % target)
    elif kind == 'login':
        if not LOGIN.match(target):raise Refused('DOOR_NAME: “%s” cannot be an account name: small letters, digits, - and _' % target)
        if value and not REAL.match(value):raise Refused('DOOR_NAME: a real name has no colon, comma or control character')
        if action == 'user.realname' and not value:raise Refused('DOOR_NAME: say the real name')
    return target, value


def _clock(text):
    """A time the owner gave (HH:MM today, or YYYY-MM-DD HH:MM), as microseconds since the epoch in local time."""
    text = str(text or '').strip()
    for fmt in ('%H:%M', '%Y-%m-%d %H:%M'):
        try:got = datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == '%H:%M':got = datetime.datetime.combine(datetime.date.today(), got.time())
        if not 2020 <= got.year <= 2100:break
        return int(time.mktime(got.timetuple())) * 1_000_000
    raise Refused('DOOR_CLOCK: “%s” is not a time: say 14:30, or 2026-11-28 14:30' % text)


def _digest(plan):
    shown = {k: plan.get(k) for k in ('action', 'target', 'value', 'words', 'lines', 'basis')}
    return hashlib.sha256(json.dumps(shown, sort_keys=True, default=str).encode()).hexdigest()


def plan(action, target='', value='', system=None):
    """system.door.plan: the action validated and shown, nothing changed and nothing asked: dict(ok, nothing, title, words, lines,
    asks, can_undo, undo, digest, basis). ok False with `why` when it cannot be asked (no such package, no service, no prompt)."""
    target, value = _validate(action, target, value)
    own = system is None;system = system or System()
    base = dict(action=action, target=target, value=value, title=title(action, target, value), ok=True, nothing=False, lines=[],
                asks='The system will ask for your password.', can_undo=False, undo='', basis={})
    try:
        out = PLANS[ACTIONS[action][2]](system, action, target, value, base)
    except sb.BusError as exc:
        out = dict(base, ok=False, why=_bus_words(exc, ACTIONS[action][2]).split(': ', 1)[1])
    except TimeoutError as exc:
        out = dict(base, ok=False, why=_bus_words(exc, ACTIONS[action][2]).split(': ', 1)[1])
    except OSError as exc:
        out = dict(base, ok=False, why='the system bus failed: %s' % (exc.strerror or exc))
    except Refused as exc:
        out = dict(base, ok=False, why=str(exc).split(': ', 1)[-1])
    finally:
        if own:system.close()
    if out['ok'] and not out['nothing']:
        agent = prompt_agent()
        out['prompt'] = agent.get('words', '')
        if not agent.get('running'):out.update(ok=False, why=agent.get('words') or 'no permission prompt can open here', no_prompt=True)
    out['digest'] = _digest(out)
    return out


def _plan_software(s, action, target, value, base):
    if action == 'packages.refresh':
        return dict(base, words='This will fetch the newest lists of software from Debian’s archive. Nothing is installed or removed.',
                    undo='Nothing to take back: only the lists change.', lines=[], asks='The system may ask for your password.')
    name = target
    found = s.resolve(name)
    installed = [p for p in found if p['info'] == INSTALLED]
    available = [p for p in found if p['info'] == AVAILABLE]
    if action == 'package.install':
        if installed:
            return dict(base, nothing=True, words='%s is installed already (version %s).' % (pretty(name), installed[0]['version']))
        if not available:raise Refused('DOOR_NO_PACKAGE: Debian’s archive here has no package called “%s”. Check the name' % name)
        pick = available[-1]
        sim = s.transaction('InstallPackages', 'tas', (SIMULATE, [pick['id']]))
        _pk_failed(sim, 'PackageKit could not plan it: ')
        return _shown(s, base, pick, sim, 'install')
    if action == 'package.remove':
        if not installed:return dict(base, nothing=True, words='%s is not installed, so there is nothing to remove.' % pretty(name))
        pick = installed[0]
        sim = s.transaction('RemovePackages', 'tasbb', (SIMULATE, [pick['id']], False, False))
        if sim['exit'] != EXIT_SUCCESS and any(e['code'] in (PK_DEPS, PK_SYSTEM_PACKAGE) for e in sim['errors']):
            raise Refused('DOOR_NEEDED: other installed software needs %s, so removing it alone is refused' % pretty(name))
        _pk_failed(sim, 'PackageKit could not plan it: ')
        return _shown(s, base, pick, sim, 'remove')
    # update
    if not installed:raise Refused('DOOR_NOT_INSTALLED: %s is not installed. Install it instead' % pretty(name))
    ups = s.transaction('GetUpdates', 't', (FILTER_NONE,))
    _pk_failed(ups)
    mine = [p for p in ups['packages'] if split_id(p['id'])['name'] == name]
    if not mine:
        return dict(base, nothing=True, words='%s is up to date (version %s), as far as the last refresh of the lists says.'
                    % (pretty(name), installed[0]['version']))
    pick = dict(mine[0], **split_id(mine[0]['id']));pick['from'] = installed[0]['version']
    sim = s.transaction('UpdatePackages', 'tas', (SIMULATE, [pick['id']]))
    _pk_failed(sim, 'PackageKit could not plan it: ')
    return _shown(s, base, pick, sim, 'update')


def _shown(s, base, pick, sim, how):
    """What the simulate said, in lines and a sentence: what it pulls in, what else changes, the sizes; and Undo's words."""
    name = pick['name']
    adds = [dict(p, **split_id(p['id'])) for p in sim['packages'] if p['info'] in (INSTALLING, REINSTALLING) and split_id(p['id'])['name'] != name]
    ups = [dict(p, **split_id(p['id'])) for p in sim['packages'] if p['info'] in (UPDATING, DOWNGRADING) and split_id(p['id'])['name'] != name]
    gone = [dict(p, **split_id(p['id'])) for p in sim['packages'] if p['info'] in (REMOVING, OBSOLETING) and split_id(p['id'])['name'] != name]
    details = s.details([pick['id']] + [p['id'] for p in adds + ups]) if how != 'remove' else s.details([pick['id']])
    download = sum(int(d.get('download-size') or 0) for d in details.values())
    disk = sum(int(d.get('size') or 0) for i, d in details.items() if i in [pick['id']] + [p['id'] for p in adds])
    lines = ['%s %s · %s' % (p['name'], p['version'], p.get('summary') or '') for p in [pick] + adds]
    lines += ['%s → %s (updated with it)' % (p['name'], p['version']) for p in ups]
    lines += ['%s %s (removed with it)' % (p['name'], p['version']) for p in gone]
    summary = (details.get(pick['id']) or {}).get('summary') or pick.get('summary') or ''
    if how == 'install':
        words = 'This will install %s %s%s' % (name, pick['version'], (' (%s)' % summary) if summary else '')
        words += (' and %s it needs: %s.' % (plural(len(adds), 'package'), listing(p['name'] for p in adds))) if adds else ', which needs nothing more.'
        undo = 'Undo removes it%s.' % (' and the packages it pulled in' if adds else '')
    elif how == 'remove':
        words = 'This will remove %s %s from this computer. Your own files and settings in your home stay.' % (name, pick['version'])
        undo = 'Undo installs it again from Debian’s archive.'
    else:
        words = 'This will update %s from %s to %s' % (name, pick.get('from', ''), pick['version'])
        words += (', with %s: %s.' % (plural(len(adds), 'new package'), listing(p['name'] for p in adds))) if adds else '.'
    if ups:words += ' It also updates %s.' % listing(p['name'] for p in ups)
    if gone:words += ' It also removes %s.' % listing(p['name'] for p in gone)
    if download:words += ' Download %s.' % size_words(download)
    if disk and how == 'install':words += ' About %s on disk.' % size_words(disk)
    out = dict(base, words=words, lines=lines, can_undo=how in ('install', 'remove'), undo=undo if how != 'update' else '',
               basis=dict(id=pick['id'], name=name, version=pick['version'], adds=[p['id'] for p in adds], ups=[p['id'] for p in ups],
                          gone=[p['id'] for p in gone], download=download, disk=disk))
    if how == 'update':out['undo'] = 'This cannot be undone: Debian does not offer the old version back.'
    return out


def _plan_services(s, action, target, value, base):
    u = s.unit(target)
    if u['load'] == 'not-found':raise Refused('DOOR_NO_UNIT: there is no service called %s on this computer' % target)
    if u['load'] == 'masked' and action in ('service.start', 'service.restart', 'service.enable'):
        raise Refused('DOOR_MASKED: %s is masked: the system keeps it from starting' % target)
    name = u['id'];desc = (' (%s)' % u['description']) if u['description'] else ''
    now = '%s, %s' % (u['active'], u['sub']) if u['sub'] and u['sub'] != u['active'] else u['active']
    running = u['active'] in ('active', 'reloading', 'activating')
    basis = dict(unit=name, active=u['active'], file=u['file'], entered=u['entered'])
    verb = action.split('.')[1]
    if verb == 'start' and running:return dict(base, nothing=True, words='%s%s is running already (%s).' % (name, desc, now), basis=basis)
    if verb == 'stop' and not running:return dict(base, nothing=True, words='%s%s is not running (%s).' % (name, desc, now), basis=basis)
    if verb == 'enable' and u['file'] in ('enabled', 'enabled-runtime', 'alias'):
        return dict(base, nothing=True, words='%s starts with the computer already.' % name, basis=basis)
    if verb == 'enable' and u['file'] in ('static', 'indirect', 'generated', 'transient'):
        raise Refused('DOOR_STATIC: %s is %s: it starts when another part of the system wants it, so it cannot be enabled on its own' % (name, u['file']))
    if verb == 'disable' and u['file'] in ('disabled', ''):
        return dict(base, nothing=True, words='%s does not start with the computer already.' % name, basis=basis)
    if verb == 'disable' and u['file'] in ('static', 'indirect', 'generated', 'transient', 'masked'):
        raise Refused('DOOR_STATIC: %s is %s, so it cannot be disabled on its own' % (name, u['file']))
    words = {'start': 'This will start %s%s. It is %s now.' % (name, desc, now),
             'stop': 'This will stop %s%s. It is %s now; what uses it stops working until it starts again.' % (name, desc, now),
             'restart': 'This will restart %s%s: stop it, then start it again. It is %s now.' % (name, desc, now),
             'enable': 'This will make %s%s start with the computer from the next start. It is %s now; enabling does not start it.' % (name, desc, now),
             'disable': 'This will stop %s%s starting with the computer. It keeps running until it is stopped.' % (name, desc)}[verb]
    undo = {'start': 'Undo stops it again.', 'stop': 'Undo starts it again.', 'enable': 'Undo disables it again.',
            'disable': 'Undo enables it again.', 'restart': 'A restart cannot be undone; it only restarted.'}[verb]
    return dict(base, title=title(action, name), target=name, words=words, can_undo=verb != 'restart', undo=undo, basis=basis,
                lines=['%s · %s · %s' % (name, now, 'starts with the computer' if u['file'] in ('enabled', 'enabled-runtime') else (u['file'] or 'no unit file'))])


def _plan_time(s, action, target, value, base):
    p = s.props(TD, TD_PATH, TD)
    zone, ntp, can_ntp = p.get('Timezone') or '', bool(p.get('NTP')), bool(p.get('CanNTP'))
    basis = dict(zone=zone, ntp=ntp)
    if action == 'time.zone':
        if target == zone:return dict(base, nothing=True, words='The time zone is %s already.' % zone, basis=basis)
        words = 'This will set the time zone to %s (it is %s now).' % (target, zone or 'not set')
        try:
            from zoneinfo import ZoneInfo
            words += ' The clock will read %s instead of %s.' % (datetime.datetime.now(ZoneInfo(target)).strftime('%H:%M'),
                                                                  datetime.datetime.now(ZoneInfo(zone)).strftime('%H:%M') if zone else '…')
        except Exception:  # noqa: BLE001 - the zone's clock is a courtesy; the zone file itself was checked
            pass
        return dict(base, words=words, can_undo=True, undo='Undo sets it back to %s.' % zone, basis=basis)
    if action == 'time.ntp':
        if not can_ntp:raise Refused('DOOR_NO_NTP: this computer has no network time service (Debian’s package “systemd-timesyncd” has it)')
        if (target == 'on') == ntp:return dict(base, nothing=True, words='Network time is %s already.' % target, basis=basis)
        words = ('This will keep the clock right from the network (systemd-timesyncd).' if target == 'on'
                 else 'This will stop setting the clock from the network; it keeps the time you or the hardware give it.')
        return dict(base, words=words, can_undo=True, undo='Undo turns it %s again.' % ('off' if target == 'on' else 'on'), basis=basis)
    if ntp:raise Refused('DOOR_NTP_ON: network time is on, so the system sets the clock itself. Turn network time off first')
    when = _clock(target)
    basis['to'] = when
    return dict(base, words='This will set the clock to %s.' % target, basis=basis,
                undo='This cannot be undone: the clock runs on from the time you give.')


def _plan_name(s, action, target, value, base):
    p = s.props(HN, HN_PATH, HN)
    old = p.get('StaticHostname') or p.get('Hostname') or ''
    if target == old:return dict(base, nothing=True, words='This computer is called “%s” already.' % old, basis=dict(old=old))
    return dict(base, words='This will name this computer “%s” (it is “%s” now). Apps already open keep the old name until they '
                            'start again; /etc/hosts still names the old one.' % (target, old), can_undo=True,
                undo='Undo names it “%s” again.' % old, basis=dict(old=old))


def _account(s, login):
    try:path = s.call(AC, AC_PATH, AC, 'FindUserByName', 's', (login,))[0]
    except sb.BusError as exc:
        if exc.name in GONE:raise
        return None
    p = s.props(AC, path, AC_USER)
    return dict(path=path, login=p.get('UserName') or login, real=p.get('RealName') or '', uid=int(p.get('Uid') or 0),
                standard=int(p.get('AccountType') or 0) == 0)


def _passwd(login):
    try:return pwd.getpwnam(login)
    except KeyError:
        return None


def own_login():
    return pwd.getpwuid(os.getuid()).pw_name


def _plan_users(s, action, target, value, base):
    s.prop(AC, AC_PATH, AC, 'DaemonVersion')      # the service answers (else: not installed)
    have = _account(s, target)
    if action == 'user.add':
        if target in RESERVED_LOGINS or have is not None or _passwd(target) is not None:
            raise Refused('DOOR_TAKEN: the name “%s” is taken on this computer. Pick another' % target)
        real = (' (%s)' % value) if value else ''
        return dict(base, words='This will add a standard account “%s”%s with its own home folder. It has no password yet, so nobody '
                                'can log in to it until its owner sets one. I never set another person’s password.' % (target, real),
                    can_undo=True, undo='Undo removes the account again; its home folder stays.', basis=dict(login=target, real=value))
    if have is None:raise Refused('DOOR_NO_ACCOUNT: there is no account “%s” on this computer' % target)
    if have['real'] == value:return dict(base, nothing=True, words='The real name of “%s” is “%s” already.' % (target, value))
    return dict(base, words='This will set the real name of “%s” to “%s” (it is “%s” now).' % (target, value, have['real'] or 'empty'),
                can_undo=True, undo='Undo sets it back to “%s”.' % have['real'], basis=dict(login=target, old=have['real']),
                asks='The system may ask for your password.' if target == own_login() else 'The system will ask for your password.')


PLANS = {'software': _plan_software, 'services': _plan_services, 'time': _plan_time, 'name': _plan_name, 'users': _plan_users}


# ---- doing, verifying, undoing --------------------------------------------------------------------------------------------
def _ask(fn):
    """A service call that may show the system's prompt: its no as SaidNo."""
    try:return fn()
    except sb.BusError as exc:
        if exc.name in SAID_NO:raise SaidNo('the system’s prompt was cancelled or refused') from exc
        if exc.name in NO_PROMPT:raise SaidNo('no permission prompt could open, so the system could not ask you', prompt=False) from exc
        raise


def _installed(s, name):
    return {p['version']: p for p in s.resolve(name, FILTER_INSTALLED) if p['info'] == INSTALLED}


def _settle(s, unit, want, before=0, seconds=None):
    """A unit followed until its job settles (or the time is up): its last reading."""
    deadline = time.monotonic() + (seconds or UNIT_SECONDS)
    while True:
        u = s.unit(unit)
        busy = u['active'] in ('activating', 'deactivating', 'reloading') or (want == 'restart' and u['entered'] <= before and u['active'] == 'active')
        if not busy or time.monotonic() >= deadline:return u
        time.sleep(0.5)


def do(s, p):
    """The fixed action itself (the system's own prompt shows here). Raises SaidNo, Refused or BusError."""
    action, target, b = p['action'], p['target'], p['basis']
    if action == 'packages.refresh':
        _pk_failed(_ask(lambda: s.transaction('RefreshCache', 'b', (False,), interactive=True)));p['refreshed'] = True
    elif action == 'package.install':
        _pk_failed(_ask(lambda: s.transaction('InstallPackages', 'tas', (ONLY_TRUSTED, [b['id']]), interactive=True)))
    elif action == 'package.remove':
        _pk_failed(_ask(lambda: s.transaction('RemovePackages', 'tasbb', (0, [b['id']], False, False), interactive=True)))
    elif action == 'package.update':
        _pk_failed(_ask(lambda: s.transaction('UpdatePackages', 'tas', (ONLY_TRUSTED, [b['id']]), interactive=True)))
    elif action in ('service.start', 'service.stop', 'service.restart'):
        member = {'service.start': 'StartUnit', 'service.stop': 'StopUnit', 'service.restart': 'RestartUnit'}[action]
        _ask(lambda: s.call(SD, SD_PATH, SD_MGR, member, 'ss', (target, 'replace'), interactive=True))
    elif action == 'service.enable':
        _ask(lambda: s.call(SD, SD_PATH, SD_MGR, 'EnableUnitFiles', 'asbb', ([target], False, False), interactive=True))
    elif action == 'service.disable':
        _ask(lambda: s.call(SD, SD_PATH, SD_MGR, 'DisableUnitFiles', 'asb', ([target], False), interactive=True))
    elif action == 'time.zone':
        _ask(lambda: s.call(TD, TD_PATH, TD, 'SetTimezone', 'sb', (target, True), interactive=True))
    elif action == 'time.ntp':
        _ask(lambda: s.call(TD, TD_PATH, TD, 'SetNTP', 'bb', (target == 'on', True), interactive=True))
    elif action == 'time.set':
        _ask(lambda: s.call(TD, TD_PATH, TD, 'SetTime', 'xbb', (_clock(target), False, True), interactive=True))
    elif action == 'host.name':
        _ask(lambda: s.call(HN, HN_PATH, HN, 'SetStaticHostname', 'sb', (target, True), interactive=True))
    elif action == 'user.add':
        _ask(lambda: s.call(AC, AC_PATH, AC, 'CreateUser', 'ssi', (target, p.get('value') or '', 0), interactive=True))
    elif action == 'user.realname':
        acct = _account(s, target)
        if acct is None:raise Refused('DOOR_NO_ACCOUNT: there is no account “%s” on this computer' % target)
        _ask(lambda: s.call(AC, acct['path'], AC_USER, 'SetRealName', 's', (p.get('value') or '',), interactive=True))


def verify(s, p, when=None, quick=False):
    """Whether the effect is there, read back from the system itself: (verified, what was checked)."""
    action, target, b = p['action'], p['target'], p['basis']
    if action == 'packages.refresh':
        done = bool(p.get('refreshed'))
        return done, 'PackageKit finished the refresh and said success' if done else 'the lists were not refreshed'
    if action in ('package.install', 'package.update'):
        have = _installed(s, b['name'])
        if b['version'] in have:return True, '%s %s is installed (PackageKit read it back)' % (b['name'], b['version'])
        return False, '%s is %s' % (b['name'], ('at %s' % ', '.join(have)) if have else 'not installed')
    if action == 'package.remove':
        have = _installed(s, b['name'])
        return (not have), ('%s is no longer installed (PackageKit read it back)' % b['name']) if not have else '%s is still installed' % b['name']
    if action.startswith('service.'):
        verb = action.split('.')[1]
        u = _settle(s, target, verb, b.get('entered', 0), 2 if quick else None)
        if verb in ('start', 'restart'):
            ok = u['active'] == 'active' and (verb == 'start' or u['entered'] > b.get('entered', 0))
            return ok, '%s is %s%s' % (u['id'], u['active'], (' (%s)' % u['sub']) if u['sub'] else '') + (', started again' if ok and verb == 'restart' else '')
        if verb == 'stop':return u['active'] in ('inactive',), '%s is %s' % (u['id'], u['active'])
        want = 'enabled' if verb == 'enable' else 'disabled'
        return u['file'] == want, '%s is %s (its unit file state)' % (u['id'], u['file'] or 'without a unit file')
    if action == 'time.zone':
        zone = s.prop(TD, TD_PATH, TD, 'Timezone')
        return zone == target, 'the time zone is %s (timedated read it back)' % zone
    if action == 'time.ntp':
        deadline = time.monotonic() + 5
        while True:
            ntp = bool(s.prop(TD, TD_PATH, TD, 'NTP'))
            if ntp == (target == 'on') or time.monotonic() >= deadline:break
            time.sleep(0.5)
        return ntp == (target == 'on'), 'network time is %s (timedated read it back)' % ('on' if ntp else 'off')
    if action == 'time.set':
        now = int(s.prop(TD, TD_PATH, TD, 'TimeUSec'));want = _clock(target) + int(((time.time() - (when or time.time()))) * 1e6)
        ok = abs(now - want) < 120_000_000
        return ok, 'the clock reads %s' % time.strftime('%H:%M', time.localtime(now / 1e6))
    if action == 'host.name':
        name = s.prop(HN, HN_PATH, HN, 'StaticHostname')
        return name == target, 'this computer is called “%s” (hostnamed read it back)' % name
    if action == 'user.add':
        acct = _account(s, target);entry = _passwd(target)
        ok = acct is not None and acct['standard'] and entry is not None
        if ok:return True, 'the account “%s” is there, standard, number %d, home %s' % (target, entry.pw_uid, entry.pw_dir)
        return False, 'the account “%s” is %s' % (target, 'not there' if acct is None else ('not a standard account' if not acct['standard'] else 'not in the system’s list of users'))
    if action == 'user.realname':
        acct = _account(s, target)
        real = acct['real'] if acct else ''
        return real == p.get('value'), 'the real name of “%s” is “%s” (the accounts service read it back)' % (target, real)
    return False, 'nothing checked'


def inverse(p):
    """Undo's own fixed action: (action, target, value, basis) put back from what the run recorded."""
    action, target, b = p['action'], p['target'], p['basis']
    if action == 'package.install':return 'package.uninstall', target, '', b
    if action == 'package.remove':return 'package.reinstall', target, '', b
    pairs = {'service.start': 'service.stop', 'service.stop': 'service.start', 'service.enable': 'service.disable', 'service.disable': 'service.enable'}
    if action in pairs:return pairs[action], target, '', b
    if action == 'time.zone':return 'time.zone', b['zone'], '', b
    if action == 'time.ntp':return 'time.ntp', 'off' if target == 'on' else 'on', '', b
    if action == 'host.name':return 'host.name', b['old'], '', b
    if action == 'user.add':return 'user.delete', target, '', b
    if action == 'user.realname':return 'user.realname', target, b['old'], b
    raise Refused('DOOR_NO_UNDO: this one cannot be undone')


def undo_do(s, back):
    """Undo's action through the same prompt; returns the plan-shaped dict that verify() reads."""
    action, target, value, b = back
    if action == 'package.uninstall':
        ids = []
        for pid in [b['id']] + list(b.get('adds') or []):
            name = split_id(pid)['name']
            ids += [p['id'] for p in s.resolve(name, FILTER_INSTALLED) if p['info'] == INSTALLED]
        if not ids:raise Refused('DOOR_NOTHING: %s is not installed any more' % b['name'])
        _pk_failed(_ask(lambda: s.transaction('RemovePackages', 'tasbb', (0, ids, False, False), interactive=True)), 'not removed: ')
        return dict(action='package.remove', target=target, basis=dict(b, name=b['name']))
    if action == 'package.reinstall':
        found = [p for p in s.resolve(b['name']) if p['info'] == AVAILABLE]
        if not found:raise Refused('DOOR_NO_PACKAGE: Debian’s archive here no longer offers %s' % b['name'])
        _pk_failed(_ask(lambda: s.transaction('InstallPackages', 'tas', (ONLY_TRUSTED, [found[-1]['id']]), interactive=True)))
        return dict(action='package.install', target=target, basis=dict(b, id=found[-1]['id'], version=found[-1]['version']))
    if action == 'user.delete':
        acct = _account(s, target)
        if acct is None:raise Refused('DOOR_NOTHING: the account “%s” is not there any more' % target)
        _ask(lambda: s.call(AC, AC_PATH, AC, 'DeleteUser', 'xb', (acct['uid'], False), interactive=True))
        return dict(action='user.delete', target=target, basis=b)
    p = dict(action=action, target=target, value=value, basis=dict(b, entered=s.unit(target)['entered'] if action.startswith('service.') else 0))
    do(s, p)
    return p


def undo_verify(s, p):
    if p['action'] == 'user.delete':
        acct = _account(s, p['target']);gone = acct is None and _passwd(p['target']) is None
        return gone, ('the account “%s” is gone; its home folder stays' % p['target']) if gone else 'the account “%s” is still there' % p['target']
    return verify(s, p)


# ---- the Kernel's operations ----------------------------------------------------------------------------------------------
def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS door_runs(id TEXT PRIMARY KEY, owner TEXT, action TEXT, target TEXT, value TEXT, title TEXT,
                  at INTEGER, state TEXT, verified INTEGER, checked TEXT, plan TEXT, undone INTEGER, undo_state TEXT)''')


def _record(kernel, principal, p, state, verified, checked):
    from . import files_service
    ident = uuid.uuid4().hex
    with files_service.opened(kernel) as db:
        ensure(db)
        db.execute('INSERT INTO door_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)', (ident, principal.identity, p['action'], p['target'], p.get('value', ''),
                   p['title'], time.time_ns() // 1_000_000, state, 1 if verified else 0, checked, json.dumps(p, default=str)))
    return ident


def _gate(kernel, principal, what):
    from . import halt_gate, home_reach as hr
    if hr.in_her_work(principal):
        raise Refused('DOOR_YOUR_PRESS: “%s” changes the system, so it runs on your press only: never as a step of mine and never '
                      'under a standing grant' % what)
    if halt_gate.held(kernel):raise Refused('DOOR_HALT: HALT holds my work. Press RESUME first; nothing was asked')


def run(kernel, action, target, value, digest, principal, system=None):
    """system.door.run: your press. The plan is made again and must be the one you saw; then the service asks you through its own
    prompt; then the effect is read back. Recorded either way."""
    from . import halt_gate
    target_v, value_v = _validate(action, target, value)
    _gate(kernel, principal, title(action, target_v, value_v))
    own = system is None;system = system or System(halt=lambda: halt_gate.held(kernel))
    try:
        p = plan(action, target, value, system)
        if p['digest'] != digest:raise Refused('DOOR_PLAN_CHANGED: what the system would do changed since you saw it, so nothing was asked. Look at it again')
        if not p['ok']:raise Refused('DOOR_NOT_READY: %s' % p.get('why', 'it cannot be asked now'))
        if p['nothing']:raise Refused('DOOR_NOTHING: %s' % p['words'])
        at = time.time();state = 'done';why = ''
        try:do(system, p)
        except SaidNo as exc:
            state = 'refused at the prompt' if exc.prompt else 'no prompt';why = str(exc)
        except Refused as exc:
            state = 'stopped by HALT' if str(exc).startswith('DOOR_CANCELLED') else 'failed';why = str(exc).split(': ', 1)[-1]
        except (sb.BusError, TimeoutError) as exc:
            state = 'failed';why = _bus_words(exc, ACTIONS[action][2]).split(': ', 1)[1]
        try:verified, checked = verify(system, p, at, quick=state != 'done')
        except (sb.BusError, TimeoutError, Refused) as exc:
            verified, checked = False, 'could not read it back: %s' % str(exc).split(': ', 1)[-1]
        if state != 'done' and verified:state = 'done'      # the effect is there after all: said as it is
        if state == 'done' and not verified:state = 'not verified'
        if state not in ('done', 'not verified'):verified = False
        ident = _record(kernel, principal, p, state, verified, checked)
        return dict(run=ident, action=action, target=p['target'], value=p.get('value', ''), title=p['title'], state=state, verified=verified,
                    checked=checked, why=why, can_undo=bool(p['can_undo'] and state == 'done'), undo=p['undo'])
    finally:
        if own:system.close()


def load_run(kernel, ident):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db);row = db.execute('SELECT * FROM door_runs WHERE id=?', (ident,)).fetchone()
    if row is None:raise Refused('DOOR_UNKNOWN_RUN: no such change')
    return {k: row[k] for k in row.keys()}


def undo(kernel, ident, principal, system=None):
    """system.door.undo: your press on Undo: the inverse fixed action, through the same prompt, read back."""
    from . import files_service, halt_gate
    row = load_run(kernel, ident)
    if row['undone']:raise Refused('DOOR_UNDONE: already taken back')
    p = json.loads(row['plan'])
    if row['state'] != 'done' or not p.get('can_undo'):raise Refused('DOOR_NO_UNDO: “%s” cannot be undone' % row['title'])
    _gate(kernel, principal, 'Undo ' + row['title'])
    own = system is None;system = system or System(halt=lambda: halt_gate.held(kernel))
    try:
        state = 'done';why = ''
        try:
            back = undo_do(system, inverse(p))
            verified, checked = undo_verify(system, back)
        except SaidNo as exc:
            state, why, verified, checked = 'refused at the prompt', str(exc), False, 'nothing changed'
        except Refused as exc:
            state, why, verified, checked = 'failed', str(exc).split(': ', 1)[-1], False, ''
        except (sb.BusError, TimeoutError) as exc:
            state, why, verified, checked = 'failed', _bus_words(exc, ACTIONS[p['action']][2]).split(': ', 1)[1], False, ''
        if state == 'done' and not verified:state = 'not verified'
        if state == 'done':
            with files_service.opened(kernel) as db:
                ensure(db);db.execute('UPDATE door_runs SET undone=?, undo_state=? WHERE id=?', (time.time_ns() // 1_000_000, state, ident))
        return dict(run=ident, title=row['title'], state=state, verified=verified, checked=checked, why=why)
    finally:
        if own:system.close()


def runs(kernel, limit=20):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        rows = db.execute('SELECT id, action, target, value, title, at, state, verified, checked, undone, plan FROM door_runs ORDER BY at DESC LIMIT ?',
                          (int(limit),)).fetchall()
    out = []
    for r in rows:
        d = {k: r[k] for k in r.keys() if k != 'plan'}
        d['can_undo'] = bool(json.loads(r['plan']).get('can_undo') and r['state'] == 'done' and not r['undone'])
        out.append(d)
    return {'runs': out}


def journal(unit, lines=12):
    """A unit's last journal lines (journalctl, a fixed argv, no shell): the journal has no reader on the bus."""
    import shutil
    program = shutil.which('journalctl', path='/usr/bin:/bin')
    if program is None:return dict(lines=[], words='journalctl is not on this computer')
    try:
        done = subprocess.run([program, '--unit=' + unit, '--lines=%d' % int(lines), '--no-pager', '--output=short-iso', '--quiet'],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15, env={'LC_ALL': 'C', 'PATH': '/usr/bin:/bin'})
    except (OSError, subprocess.SubprocessError) as exc:
        return dict(lines=[], words='journalctl did not answer: %s' % exc)
    got = [l for l in done.stdout.splitlines() if l.strip()][-int(lines):]
    return dict(lines=got, words='' if got else 'The journal shows you nothing of it; your account may not read the system’s journal.')


def read(what, target='', system=None):
    """system.door.read: what the door can tell without asking anything."""
    if what not in READS:raise Refused('DOOR_UNKNOWN: the door reads updates, a service, the time, the name or the accounts')
    own = system is None;s = system or System()
    try:
        if what == 'updates':
            got = s.transaction('GetUpdates', 't', (FILTER_NONE,));_pk_failed(got)
            rows = [dict(split_id(p['id']), kind=p['info'], summary=p['summary']) for p in got['packages']]
            return dict(updates=rows, words='%s waiting, as far as the last refresh of the lists says.' % plural(len(rows), 'update'))
        if what == 'service':
            name = unit_name(target)
            if not UNIT.match(name):raise Refused('DOOR_NAME: “%s” is not a service name' % name)
            u = s.unit(name);u.pop('path', None)
            return dict(unit=u, journal=journal(u['id']))
        if what == 'time':
            p = s.props(TD, TD_PATH, TD)
            return dict(zone=p.get('Timezone') or '', ntp=bool(p.get('NTP')), can_ntp=bool(p.get('CanNTP')), synced=bool(p.get('NTPSynchronized')))
        if what == 'name':
            p = s.props(HN, HN_PATH, HN)
            return dict(name=p.get('StaticHostname') or p.get('Hostname') or '', pretty=p.get('PrettyHostname') or '')
        return dict(accounts=accounts())
    except (sb.BusError, TimeoutError) as exc:
        raise Refused(_bus_words(exc, {'updates': 'software', 'service': 'services', 'time': 'time', 'name': 'name', 'users': 'users'}[what])) from exc
    finally:
        if own:s.close()


def accounts(s=None):
    """The people's accounts on this computer: the accounts service's own list when it answers, else /etc/passwd (numbers
    1000 to 59999 with a login shell)."""
    if s is not None:
        try:
            out = []
            for path in s.call(AC, AC_PATH, AC, 'ListCachedUsers')[0]:
                p = s.props(AC, path, AC_USER)
                out.append(dict(login=p.get('UserName') or '', real=p.get('RealName') or '', uid=int(p.get('Uid') or 0), home='',
                                standard=int(p.get('AccountType') or 0) == 0))
            return sorted(out, key=lambda a: a['uid'])
        except (sb.BusError, TimeoutError):
            pass
    out = []
    for e in pwd.getpwall():
        if 1000 <= e.pw_uid < 60000 and not e.pw_shell.endswith(('nologin', 'false')):
            out.append(dict(login=e.pw_name, real=e.pw_gecos.split(',')[0], uid=e.pw_uid, home=e.pw_dir))
    return sorted(out, key=lambda a: a['uid'])


def state(system=None):
    """system.door.state: which of the services answer here, whether the system's prompt can open, and what Settings shows."""
    own = system is None;s = system or System();out = dict(agent=prompt_agent(), services={})
    try:
        for key, (dest, name, package) in SERVICES.items():
            try:
                if key == 'software':s.prop(PK, PK_PATH, PK, 'VersionMajor')
                elif key == 'services':s.prop(SD, SD_PATH, SD_MGR, 'Version')
                elif key == 'time':out['time'] = read('time', system=s)
                elif key == 'name':out['name'] = read('name', system=s)
                else:s.prop(AC, AC_PATH, AC, 'DaemonVersion')
                out['services'][key] = dict(answers=True, name=name, words='%s answers' % name)
            except (sb.BusError, TimeoutError, Refused) as exc:
                why = str(exc) if isinstance(exc, Refused) else _bus_words(exc, key)
                out['services'][key] = dict(answers=False, name=name, words=why.split(': ', 1)[-1])
                if isinstance(exc, sb.BusError) and exc.name == 'org.freedesktop.DBus.Error.NoServer':
                    for rest in SERVICES:out['services'].setdefault(rest, dict(answers=False, name=SERVICES[rest][1], words=out['services'][key]['words']))
                    break
        out['accounts'] = accounts(s if out['services'].get('users', {}).get('answers') else None)
        return out
    finally:
        if own:s.close()


ACTION_ARG = {'type': 'string', 'enum': sorted(ACTIONS)}
TARGET = {'type': 'string', 'maxLength': 200}
VALUE = {'type': 'string', 'maxLength': 200}
DIGEST = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
RUN_ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
FIELDS = {
    'system.door.plan': ({'action': ACTION_ARG, 'target': TARGET, 'value': VALUE}, ['action']),
    'system.door.run': ({'action': ACTION_ARG, 'target': TARGET, 'value': VALUE, 'digest': DIGEST}, ['action', 'digest']),
    'system.door.undo': ({'run': RUN_ID}, ['run']),
    'system.door.runs': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': RUNS_MOST}}, []),
    'system.door.read': ({'what': {'type': 'string', 'enum': list(READS)}, 'target': TARGET}, ['what']),
    'system.door.state': ({}, []),
}
SCOPES = {'system.door.plan': 'read', 'system.door.run': 'approve', 'system.door.undo': 'approve', 'system.door.runs': 'read', 'system.door.read': 'read', 'system.door.state': 'read'}


def dispatch(kernel, op, args, principal):
    if op == 'system.door.plan':return plan(args['action'], args.get('target', ''), args.get('value', ''))
    if op == 'system.door.run':return run(kernel, args['action'], args.get('target', ''), args.get('value', ''), args['digest'], principal)
    if op == 'system.door.undo':return undo(kernel, args['run'], principal)
    if op == 'system.door.runs':return runs(kernel, args.get('limit') or 20)
    if op == 'system.door.read':return read(args['what'], args.get('target', ''))
    if op == 'system.door.state':return state()
    raise ValueError('DOOR_UNKNOWN_OPERATION')


# ---- the owner's words and command lines: which fixed action they ask for ------------------------------------------------
_N = r'([A-Za-z0-9][A-Za-z0-9+.-]+)'
_U = r'([A-Za-z0-9][A-Za-z0-9:_.@-]*)'
_P = r'(?:please\s+)?'
_Q = r'["“”\']?'
_END = r'(?:\s+please)?\s*[.]?$'
NOT_THINGS = frozenset(('it', 'this', 'that', 'them', 'everything', 'all', 'updates', 'computer', 'the', 'a', 'an', 'my', 'system',
                        'session', 'graphite', 'kas', 'kasandra', 'model', 'terminal', 'line', 'recipe', 'work', 'over', 'again'))
WORDS = (
    (re.compile(_P + r'install\s+(?:the\s+)?(?:package\s+|app\s+)?' + _N + r'(?:\s+(?:package|app))?' + _END, re.I), 'package.install'),
    (re.compile(_P + r'(?:uninstall|remove\s+(?:the\s+)?(?:package|app))\s+(?:the\s+)?' + _N + r'(?:\s+(?:package|app))?' + _END, re.I), 'package.remove'),
    (re.compile(_P + r'remove\s+(?:the\s+)?' + _N + r'\s+(?:package|app)' + _END, re.I), 'package.remove'),
    (re.compile(_P + r'(?:update|upgrade)\s+(?:the\s+)?(?:package\s+|app\s+)?' + _N + r'(?:\s+(?:package|app))?' + _END, re.I), 'package.update'),
    (re.compile(_P + r'(?:refresh|update|reload)\s+the\s+(?:software|package)\s+lists?' + _END, re.I), 'packages.refresh'),
    (re.compile(_P + r'(start|stop|restart|enable|disable)\s+(?:the\s+)?(?:service\s+)?' + _U + r'(?:\s+service)?(?:\s+(?:at|on)\s+(?:boot|startup))?' + _END, re.I), 'service'),
    (re.compile(_P + r'(?:set|change|switch)\s+(?:the\s+|my\s+)?(?:time\s*zone|timezone)\s+to\s+([A-Za-z_]+(?:/[A-Za-z0-9_+-]+){0,2})' + _END, re.I), 'time.zone'),
    (re.compile(_P + r'turn\s+(on|off)\s+(?:the\s+)?(?:network\s+time|ntp|automatic\s+time|time\s+sync\w*)' + _END, re.I), 'time.ntp'),
    (re.compile(_P + r'turn\s+(?:the\s+)?(?:network\s+time|ntp|automatic\s+time)\s+(on|off)' + _END, re.I), 'time.ntp'),
    (re.compile(_P + r'set\s+the\s+(?:time|clock)\s+to\s+(\d{1,2}:\d{2}|\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})' + _END, re.I), 'time.set'),
    (re.compile(_P + r'(?:rename\s+(?:this\s+|the\s+|my\s+)?computer|(?:set|change)\s+(?:the\s+|this\s+|my\s+)?(?:computer(?:’s|\'s)?\s+name|'
                r'computer\s+name|host\s*name)|name\s+(?:this|the|my)\s+computer)\s+(?:to\s+)?' + _Q + r'([A-Za-z0-9-]+)' + _Q + _END, re.I), 'host.name'),
    (re.compile(_P + r'(?:add|create|make)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:standard\s+)?(?:user|account|user\s+account)\s+(?:called\s+|named\s+|for\s+)?'
                + _Q + r'([a-z][a-z0-9_-]*)' + _Q + r'(?:\s+(?:called|named|for|with\s+the\s+(?:real|full)\s+name)\s+' + _Q + r'([^"“”\']+?)' + _Q + r')?' + _END, re.I), 'user.add'),
    (re.compile(_P + r'(?:set|change)\s+my\s+(?:real|full)\s+name\s+to\s+' + _Q + r'([^"“”\']+?)' + _Q + _END, re.I), 'user.realname.mine'),
    (re.compile(_P + r'(?:set|change)\s+the\s+(?:real|full)\s+name\s+of\s+([a-z][a-z0-9_-]*)\s+to\s+' + _Q + r'([^"“”\']+?)' + _Q + _END, re.I), 'user.realname'),
)
ROOT_PROGRAMS = ('sudo', 'pkexec', 'doas', 'apt', 'apt-get', 'aptitude', 'systemctl', 'service', 'timedatectl', 'hostnamectl', 'adduser',
                 'useradd', 'chfn')


def read_words(text, units=None):
    """The owner's words (or a root command line) as one fixed action: dict(action, target, value) or None. A service is
    read from words only when a unit file of that name is on this computer ("restart cups"), so "start the model" is not."""
    words = ' '.join(str(text or '').split())
    if not words:return None
    first = words.split(' ', 1)[0]
    if first in ROOT_PROGRAMS:
        try:return offer(shlex.split(words))
        except ValueError:
            return None
    for pattern, action in WORDS:
        m = pattern.match(words)
        if not m:continue
        if action == 'service':
            verb, name = m.group(1).lower(), m.group(2)
            if name.lower() in NOT_THINGS or not unit_known(name, units):return None
            return dict(action='service.' + verb, target=unit_name(name), value='')
        if action in ('package.install', 'package.remove', 'package.update'):
            if m.group(1).lower() in NOT_THINGS:return None
            return dict(action=action, target=m.group(1).lower(), value='')
        if action == 'user.realname.mine':return dict(action='user.realname', target=own_login(), value=m.group(1).strip())
        if action in ('user.add', 'user.realname'):
            return dict(action=action, target=m.group(1).lower(), value=(m.group(2) or '').strip())
        if action == 'time.ntp':return dict(action=action, target=m.group(1).lower(), value='')
        if action == 'packages.refresh':return dict(action=action, target='', value='')
        return dict(action=action, target=m.group(1), value='')
    return None


def _offered(action, target='', value='', line=None):
    out = dict(action=action, target=target, value=value, title=title(action, target, value), asks=asks_words(action))
    out['words'] = 'That is the system door: %s, through the system’s own prompt. It shows what it will do first.' % out['title']
    if line is not None:out['line'] = line
    return out


def offer(argv):
    """For the command tool (KS2): a root command line, as argv, mapped to the door's fixed action (an offer: action, target,
    value, title, asks, words, line), or None when it is not one of them. One package or one unit only: one action per prompt."""
    argv = [str(a) for a in (argv or ())]
    line = ' '.join(shlex.quote(a) for a in argv)
    while argv and argv[0] in ('sudo', 'pkexec', 'doas'):
        argv = argv[1:]
        while argv and argv[0].startswith('-'):
            if argv[0] in ('-u', '--user', '-g', '--group', '-s', '--shell', '-i', '--login', '-c'):return None      # another user, or a shell
            argv = argv[1:]
    if not argv:return None
    prog, rest = os.path.basename(argv[0]), argv[1:]
    plain = [a for a in rest if not a.startswith('-')]
    flags = [a for a in rest if a.startswith('-')]
    if prog in ('apt', 'apt-get', 'aptitude'):
        if any(f not in ('-y', '--yes', '-q', '--quiet', '--assume-yes', '--only-upgrade', '--no-install-recommends') for f in flags):return None
        if not plain:return None
        verb, names = plain[0], plain[1:]
        if verb == 'update' and not names:return _offered('packages.refresh', line=line)
        if len(names) != 1 or not PACKAGE.match(names[0].lower()):return None
        name = names[0].lower()
        if verb == 'install':return _offered('package.update' if '--only-upgrade' in flags else 'package.install', name, line=line)
        if verb == 'remove':return _offered('package.remove', name, line=line)
        if verb in ('upgrade', 'full-upgrade', 'dist-upgrade') and '--no-install-recommends' not in flags:return _offered('package.update', name, line=line)
        return None
    if prog in ('systemctl', 'service'):
        if prog == 'service' and len(plain) == 2:plain = [plain[1], plain[0]]
        if any(f not in ('-q', '--quiet', '--no-block') for f in flags) or len(plain) != 2:return None
        verb, unit = plain
        if verb not in ('start', 'stop', 'restart', 'enable', 'disable') or not UNIT.match(unit_name(unit)):return None
        return _offered('service.' + verb, unit_name(unit), line=line)
    if prog == 'timedatectl' and not flags and plain:
        if plain[0] == 'set-timezone' and len(plain) == 2:return _offered('time.zone', plain[1], line=line)
        if plain[0] == 'set-ntp' and len(plain) == 2 and plain[1].lower() in ('true', 'false', 'yes', 'no', 'on', 'off', '1', '0'):
            return _offered('time.ntp', 'on' if plain[1].lower() in ('true', 'yes', 'on', '1') else 'off', line=line)
        if plain[0] == 'set-time' and len(plain) == 2:return _offered('time.set', plain[1], line=line)
        return None
    if prog == 'hostnamectl' and not flags and len(plain) == 2 and plain[0] in ('set-hostname', 'hostname'):
        return _offered('host.name', plain[1].lower(), line=line)
    if prog == 'adduser' and len(plain) == 1 and all(f in ('--disabled-password',) for f in flags):
        return _offered('user.add', plain[0], line=line)
    if prog == 'adduser' and len(rest) == 3 and rest[0] in ('--comment', '--gecos'):
        return _offered('user.add', rest[2], rest[1], line=line)
    if prog == 'useradd' and len(plain) == 1 and all(f in ('-m', '--create-home') for f in flags):
        return _offered('user.add', plain[0], line=line)
    if prog == 'chfn' and len(rest) in (2, 3) and rest[0] == '-f':
        return _offered('user.realname', rest[2] if len(rest) == 3 else own_login(), rest[1], line=line)
    return None
