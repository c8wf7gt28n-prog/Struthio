"""Graphite 1.0 S4 · The Machine, real: removable storage, power, the network, sound and screens, read from and changed
through the system's own services (PLAN_1.0.md, S4; the paper's section 2: "The owner needs access to removable storage,
audio, displays, wireless connections ... and power management without leaving Graphite").

  Storage   udisks2 (org.freedesktop.UDisks2) over QtDBus: the removable drives and their filesystems. Mount, Open in
            Files (the window's Browse tab), Unmount, Eject safely. "Safe to remove" is said only after it is: every
            filesystem of the drive read back as unmounted, then the drive powered off (or ejected) by udisks2 and read back.
  Power     UPower (org.freedesktop.UPower): the batteries and the mains. Read only (Lock, Suspend, Log out, Restart and
            Shut down are the System menu's, session_power).
  Network   NetworkManager (org.freedesktop.NetworkManager): its state, networking and Wi-Fi on or off, the Wi-Fi networks
            heard, Join and Disconnect. A network NetworkManager already knows is joined with its own saved connection; a
            new secured one with the password the owner types, handed straight to NetworkManager in the one call that adds
            the connection and kept by NetworkManager, never by Graphite (never written, logged or held after the call).
  Sound     PipeWire through wpctl (WirePlumber): the outputs, the volume and mute of the one in use, which one is in use.
  Screens   xrandr: the outputs, their modes, which is primary, one screen, mirror or extend.

Each section reads into a plain dict: key, title, available, why, source, sampled_at, short (the Machine tab's few words),
and its own rows. With its service absent the section is available=False and why says so in words, with what would make it
available ("not available on this computer, and why").

The bus: the real services are on the system D-Bus. bus='session' (or GRAPHITE_MACHINE_BUS=session in the environment) reads
them from the session bus instead, where stand-ins can sit; nothing else changes.

Every change here is a function the window calls on the owner's press: none is a Kernel operation (the model can dispatch
those), so no change is ever made on the model's word (1.0 S4; K3's grants may wrap them later). Each change returns
dict(ok, verified, said) and is "done" only when its effect is read back (ok and verified); the system's own permission
prompt (polkit) may ask first, so a change may wait for the owner. The reads (snapshot, and the Kernel's machine.state) change
nothing. No floating point in what is decided: a battery's or a volume's percent is read as decimal digits and kept as an int.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import warnings
from decimal import Decimal, ROUND_HALF_UP

SCHEMA = 'machine.state/1'
SECTIONS = ('storage', 'power', 'network', 'sound', 'screens')
TITLES = {'storage': 'Storage', 'power': 'Power', 'network': 'Network', 'sound': 'Sound', 'screens': 'Screens'}
TIMEOUT_MS = 1500           # a read: the service answers at once, or the section says it did not
ACT_TIMEOUT_MS = 120000     # a change: the system's own permission prompt may be waiting for the owner
JOIN_SECONDS = 45           # how long a Wi-Fi join may take before it is said to have failed
PROGRAMS = ('wpctl', 'xrandr')   # the only programs this module starts; argv only, never a shell, never sudo
NOT_HERE = 'Not available on this computer'

UDISKS = 'org.freedesktop.UDisks2'
UD_ROOT = '/org/freedesktop/UDisks2'
UD = 'org.freedesktop.UDisks2.'
UPOWER = 'org.freedesktop.UPower'
UP_ROOT = '/org/freedesktop/UPower'
NM = 'org.freedesktop.NetworkManager'
NM_ROOT = '/org/freedesktop/NetworkManager'
PROPS = 'org.freedesktop.DBus.Properties'
PACKAGES = {'storage': 'udisks2', 'power': 'upower', 'network': 'network-manager', 'sound': 'wireplumber (with pipewire)',
            'screens': 'x11-xserver-utils'}
SERVICES = {'storage': (UDISKS, 'udisks2'), 'power': (UPOWER, 'UPower'), 'network': (NM, 'NetworkManager')}


class Unavailable(Exception):
    """The service is not there to ask (no bus, not running, not installed): the section says so."""


class Refused(Exception):
    """The service answered, with an error: its own words are kept."""

    def __init__(self, name, message):
        super().__init__(message or name);self.name = name or '';self.message = message or name or 'refused'


# ---- QtDBus, plainly ------------------------------------------------------------------------------------------------------
def bus_kind(bus=None):
    kind = (bus or os.environ.get('GRAPHITE_MACHINE_BUS') or 'system').strip().lower()
    return 'session' if kind == 'session' else 'system'


def connection(bus=None):
    from PySide6.QtDBus import QDBusConnection
    kind = bus_kind(bus)
    conn = QDBusConnection.sessionBus() if kind == 'session' else QDBusConnection.systemBus()
    if not conn.isConnected():
        raise Unavailable('there is no %s D-Bus here (%s)' % (kind, (conn.lastError().message() or 'not connected').strip()[:160]))
    return conn


def plain(value):
    """A QtDBus answer as plain Python: dicts, lists, tuples, str, int, bool, float, bytes; object paths as str.

    PySide6 cannot choose QDBusArgument's reading beginMapEntry/endArray (they share their signature with the writing ones),
    so a map is read through copies: each entry is entered on a copy of the map's reader (a copy reads on from the same
    place), and the map's own reader steps over it. Nothing is ever left half read."""
    from PySide6.QtCore import QByteArray
    from PySide6.QtDBus import QDBusArgument, QDBusObjectPath, QDBusSignature, QDBusVariant
    if isinstance(value, QDBusVariant):return plain(value.variant())
    if isinstance(value, QDBusObjectPath):return value.path()
    if isinstance(value, QDBusSignature):return value.signature()
    if isinstance(value, QByteArray):return bytes(value.data())
    if isinstance(value, QDBusArgument):
        kind = value.currentType();E = QDBusArgument.ElementType
        if kind == E.MapType:
            out = {};value.beginArray()
            while not value.atEnd():
                entry = QDBusArgument(value);entry.beginArray()
                key = plain(entry.asVariant());out[key] = plain(entry.asVariant())
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore');value.asVariant()   # step over the entry just read
            return out
        if kind in (E.ArrayType, E.StructureType):
            out = [];value.beginArray()
            while not value.atEnd():out.append(plain(value.asVariant()))
            return out if kind == E.ArrayType else tuple(out)
        return plain(value.asVariant())
    if isinstance(value, dict):return {plain(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):return [plain(v) for v in value]
    return value


def call(service, path, interface, method, *args, bus=None, timeout=TIMEOUT_MS):
    """One method call; its answer's values as plain Python. Raises Unavailable (no bus, no service) or Refused."""
    from PySide6.QtDBus import QDBus, QDBusMessage
    conn = connection(bus)
    message = QDBusMessage.createMethodCall(service, path, interface, method)
    if args:message.setArguments(list(args))
    reply = conn.call(message, QDBus.CallMode.Block, int(timeout))
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        name = reply.errorName() or ''
        if name in ('org.freedesktop.DBus.Error.ServiceUnknown', 'org.freedesktop.DBus.Error.NameHasNoOwner', 'org.freedesktop.DBus.Error.NoServer'):
            raise Unavailable(reply.errorMessage() or name)
        raise Refused(name, (reply.errorMessage() or '').strip()[:300])
    return [plain(value) for value in reply.arguments()]


def first(values):
    return values[0] if values else None


def all_properties(service, path, interface, bus=None):
    return first(call(service, path, PROPS, 'GetAll', interface, bus=bus)) or {}


def get_property(service, path, interface, name, bus=None):
    return first(call(service, path, PROPS, 'Get', interface, name, bus=bus))


def set_property(service, path, interface, name, value, bus=None, timeout=ACT_TIMEOUT_MS):
    from PySide6.QtDBus import QDBusVariant
    return call(service, path, PROPS, 'Set', interface, name, QDBusVariant(value), bus=bus, timeout=timeout)


def object_path(path):
    from PySide6.QtDBus import QDBusObjectPath
    return QDBusObjectPath(path)


def settings_map(settings):
    """NetworkManager's connection settings (a{sa{sv}}) as one QtDBus argument: {group: {key: value}}; bytes stay bytes."""
    from PySide6.QtCore import QByteArray, QMetaType
    from PySide6.QtDBus import QDBusArgument
    argument = QDBusArgument()
    argument.beginMap(QMetaType.Type.QString, QMetaType.Type.QVariantMap)
    for group, values in settings.items():
        argument.beginMapEntry();argument.appendVariant(str(group))
        argument.appendVariant({str(k): (QByteArray(v) if isinstance(v, bytes) else v) for k, v in values.items()})
        argument.endMapEntry()
    argument.endMap()
    return argument


def present(service, bus=None):
    """'running', 'activatable' (D-Bus starts it on the first call, as udisks2 is on Debian) or why it is not there."""
    try:
        conn = connection(bus)
    except Unavailable as exc:
        return str(exc)
    try:
        if first(call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'NameHasOwner', service, bus=bus)):
            return 'running'
        names = first(call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'ListActivatableNames', bus=bus)) or []
    except (Unavailable, Refused) as exc:
        return 'the %s D-Bus did not answer (%s)' % (bus_kind(bus), str(exc)[:120])
    del conn
    return 'activatable' if service in names else None


def absent_words(key, bus=None, said=None):
    """Why a D-Bus section is not available, in words, with the package that brings its service."""
    service, name = SERVICES[key]
    if said is None:
        said = '%s is not running on this computer (nothing answers as %s on the %s D-Bus)' % (name, service, bus_kind(bus))
    return '%s: %s. Debian has it as the package %s, in the 1.0 System set.' % (NOT_HERE, said, PACKAGES[key])


def section(key, source, **extra):
    out = dict(key=key, title=TITLES[key], available=True, why='', source=source, sampled_at=time.time(), short='', schema=SCHEMA)
    out.update(extra);return out


def unavailable(key, source, why, short='not available'):
    return section(key, source, available=False, why=why, short=short)


def absent(key, source, bus, here):
    """A D-Bus section whose service is not there: the row's few words and the page's sentence both say why."""
    name = SERVICES[key][1]
    if here is None:short = 'not available: %s is not running' % name
    elif here.startswith('there is no'):short = 'not available: no %s D-Bus' % bus_kind(bus)
    else:short = 'not available: %s did not answer' % name
    return unavailable(key, source, absent_words(key, bus, here), short)


def text_of(value):
    if isinstance(value, (bytes, bytearray)):return bytes(value).rstrip(b'\0').decode('utf-8', 'replace')
    return '' if value is None else str(value)


def percent(value):
    """A percent from a reading (UPower's double, wpctl's '0.40') as an int, through its decimal digits, never a float sum."""
    try:
        return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except Exception:  # noqa: BLE001 - a reading that is no number is no percent
        return None


def size_words(count):
    if not isinstance(count, int) or count <= 0:return ''
    for unit, step in (('TB', 10 ** 12), ('GB', 10 ** 9), ('MB', 10 ** 6), ('kB', 10 ** 3)):
        if count >= step:
            tenths = (count * 10 + step // 2) // step
            return '%d.%d %s' % (tenths // 10, tenths % 10, unit) if tenths < 1000 else '%d %s' % (tenths // 10, unit)
    return '%d bytes' % count


def duration_words(seconds):
    if not isinstance(seconds, int) or seconds <= 0:return ''
    minutes = (seconds + 30) // 60;hours, minutes = divmod(minutes, 60)
    return ('%d h %d min' % (hours, minutes)) if hours else ('%d min' % minutes)


def failure(exc, doing):
    """A change that did not happen, in words: the service's own words kept."""
    if isinstance(exc, Unavailable):return dict(ok=False, verified=False, said='%s: %s' % (doing, exc))
    if isinstance(exc, Refused):
        if exc.name.endswith(('NotAuthorized', 'NotAuthorizedCanObtain', 'NotAuthorizedDismissed', 'PermissionDenied', 'AccessDenied')):
            return dict(ok=False, verified=False, said='%s: the system did not allow it (%s).' % (doing, exc.message))
        return dict(ok=False, verified=False, said='%s: %s' % (doing, exc.message))
    return dict(ok=False, verified=False, said='%s: %s' % (doing, str(exc)[:300] or type(exc).__name__))


# ---- Storage: udisks2 -----------------------------------------------------------------------------------------------------
def storage(bus=None):
    source = 'udisks2 (%s) on the %s D-Bus' % (UDISKS, bus_kind(bus))
    here = present(UDISKS, bus)
    if here not in ('running', 'activatable'):
        return absent('storage', source, bus, here)
    try:
        objects = first(call(UDISKS, UD_ROOT, 'org.freedesktop.DBus.ObjectManager', 'GetManagedObjects', bus=bus)) or {}
    except (Unavailable, Refused) as exc:
        return absent('storage', source, bus, 'udisks2 did not answer (%s)' % str(exc)[:160])
    drives = []
    for path, faces in sorted(objects.items()):
        drive = faces.get(UD + 'Drive')
        if not drive:continue
        removable = bool(drive.get('Removable') or drive.get('MediaRemovable') or drive.get('Ejectable')
                         or drive.get('ConnectionBus') in ('usb', 'sdio', 'ieee1394'))
        if not removable:continue
        name = ' '.join(part for part in (text_of(drive.get('Vendor')).strip(), text_of(drive.get('Model')).strip()) if part) or 'Removable drive'
        volumes = []
        for block_path, block_faces in sorted(objects.items()):
            block = block_faces.get(UD + 'Block')
            if not block or block.get('Drive') != path or block.get('HintIgnore'):continue
            filesystem = block_faces.get(UD + 'Filesystem');encrypted = UD + 'Encrypted' in block_faces
            if filesystem is None and not encrypted:continue
            mounted = [text_of(point) for point in (filesystem or {}).get('MountPoints') or [] if text_of(point)]
            volumes.append(dict(id=block_path, device=text_of(block.get('PreferredDevice') or block.get('Device')),
                                label=text_of(block.get('IdLabel')).strip(), fs=text_of(block.get('IdType')), size=block.get('Size') or 0,
                                mounted=mounted, readonly=bool(block.get('ReadOnly')), encrypted=encrypted,
                                can_mount=filesystem is not None))
        drives.append(dict(id=path, name=name, size=drive.get('Size') or 0, bus=text_of(drive.get('ConnectionBus')),
                           can_power_off=bool(drive.get('CanPowerOff')), ejectable=bool(drive.get('Ejectable')),
                           media=bool(drive.get('MediaAvailable', True)), volumes=volumes))
    short = ('%d drive' % len(drives) + ('s' if len(drives) != 1 else '')) if drives else 'no removable drive'
    return section('storage', source, drives=drives, short=short)


def volume_words(volume):
    name = volume['label'] or volume['device'] or 'volume'
    parts = [name, (volume['fs'] or 'unknown').upper() if volume['fs'] else 'unformatted', size_words(volume['size'])]
    return ' · '.join(p for p in parts if p)


def _mount_points(block, bus):
    try:
        return [text_of(p) for p in (get_property(UDISKS, block, UD + 'Filesystem', 'MountPoints', bus=bus) or []) if text_of(p)]
    except (Unavailable, Refused):
        return None


def mount(block, bus=None):
    """Mount one filesystem (udisks2 chooses the place, under /media); done when its mount point is read back."""
    doing = 'Mounting did not happen'
    try:
        place = text_of(first(call(UDISKS, block, UD + 'Filesystem', 'Mount', {}, bus=bus, timeout=ACT_TIMEOUT_MS)))
    except (Unavailable, Refused) as exc:
        return failure(exc, doing)
    points = _mount_points(block, bus) or []
    if place and place in points:
        return dict(ok=True, verified=True, said='Mounted at %s (read back from udisks2).' % place, path=place)
    return dict(ok=True, verified=False, said='udisks2 said it mounted it at %s, but reading it back shows %s.' % (place or 'no place', ', '.join(points) or 'no mount point'), path=place)


PROGRAM_NAMES = {'soffice.bin': 'LibreOffice', 'soffice': 'LibreOffice', 'oosplash': 'LibreOffice', 'gimp': 'GIMP', 'firefox': 'Firefox',
                 'firefox-esr': 'Firefox', 'kicad': 'KiCad', 'blender': 'Blender', 'godot': 'Godot', 'evince': 'Document Viewer',
                 'eog': 'Image Viewer', 'vlc': 'VLC', 'bash': 'a terminal shell', 'python3': 'a Python program'}


def holders(places, proc='/proc'):
    """1.0 X4: the programs of this account that hold something under one of `places` open (a file, or their working folder),
    read from /proc: [(pid, program words)]. Only your own processes are looked at; Graphite's own process is left out."""
    roots = [str(p).rstrip('/') for p in places or () if p]
    if not roots:return []
    mine, me, found = os.getuid(), os.getpid(), []
    try:pids = [p for p in os.listdir(proc) if p.isdigit()]
    except OSError:return []
    for pid in pids:
        if int(pid) == me:continue
        try:
            if os.stat(os.path.join(proc, pid)).st_uid != mine:continue
            links = [os.readlink(os.path.join(proc, pid, 'cwd'))]
            fds = os.path.join(proc, pid, 'fd')
            links += [os.readlink(os.path.join(fds, fd)) for fd in os.listdir(fds)]
        except OSError:
            continue
        if any(link == root or link.startswith(root + '/') for link in links for root in roots):
            try:
                with open(os.path.join(proc, pid, 'comm'), encoding='utf-8', errors='replace') as f:comm = f.read().strip()
            except OSError:
                comm = ''
            found.append((int(pid), PROGRAM_NAMES.get(comm, comm or 'a program')))
    return found


def holders_words(places):
    """1.0 X4: '' or a sentence naming the programs that keep the drive busy ("LibreOffice (process 4242) has a file on it open")."""
    held = holders(places)
    if not held:return ''
    names = sorted({name for _, name in held})
    pids = ', '.join(str(pid) for pid, _ in held[:4])
    return '%s %s a file on it open (process %s): close it there first, then eject again. Nothing was forced.' % (
        ' and '.join(names), 'has' if len(names) == 1 else 'have', pids)


def unmount(block, bus=None):
    """Unmount one filesystem; done when udisks2 reads it back as mounted nowhere (every write to it is then finished)."""
    doing = 'Unmounting did not happen'
    try:
        before = _mount_points(block, bus) or []      # 1.0 X4: where it is, to name what keeps it busy if it is refused
    except Exception:  # noqa: BLE001
        before = []
    try:
        call(UDISKS, block, UD + 'Filesystem', 'Unmount', {}, bus=bus, timeout=ACT_TIMEOUT_MS)
    except (Unavailable, Refused) as exc:
        out = failure(exc, doing)
        held = holders_words(before) if isinstance(exc, Refused) else ''      # 1.0 X4: a busy drive names the program holding it
        if held:out['said'] = '%s: it is in use. %s' % (doing, held);out['held_by'] = [name for _, name in holders(before)];out['service_said'] = exc.message
        return out
    points = _mount_points(block, bus)
    if points == []:
        return dict(ok=True, verified=True, said='Unmounted (read back: mounted nowhere).')
    return dict(ok=True, verified=False, said='udisks2 answered, but it still reads as mounted at %s.' % (', '.join(points or []) or 'an unknown place'))


def eject(drive_id, bus=None):
    """Eject safely: unmount every filesystem of the drive (each read back), then power it off (or eject it) through udisks2.
    safe is True only when every filesystem reads back unmounted and the drive was powered off or ejected (or, for a drive
    that can do neither, when everything on it reads back unmounted): only then is "Safe to remove" said."""
    now = storage(bus)
    if not now['available']:return dict(ok=False, verified=False, safe=False, said=now['why'])
    drive = next((d for d in now['drives'] if d['id'] == drive_id), None)
    if drive is None:return dict(ok=False, verified=False, safe=False, said='That drive is no longer here: nothing was done.')
    steps = []
    for volume in drive['volumes']:
        if volume['mounted']:
            done = unmount(volume['id'], bus)
            steps.append(done['said'])
            if not done['verified']:
                return dict(ok=False, verified=False, safe=False, said='Not safe to remove yet: %s %s' % (volume_words(volume), done['said']))
    for volume in drive['volumes']:
        if volume['can_mount'] and _mount_points(volume['id'], bus):
            return dict(ok=False, verified=False, safe=False, said='Not safe to remove yet: %s is still mounted.' % volume_words(volume))
    method = 'PowerOff' if drive['can_power_off'] else 'Eject' if drive['ejectable'] else None
    if method is None:
        return dict(ok=True, verified=True, safe=True, said='Safe to remove: nothing on %s is mounted (read back), and every write to it is finished.' % drive['name'])
    try:
        call(UDISKS, drive_id, UD + 'Drive', method, {}, bus=bus, timeout=ACT_TIMEOUT_MS)
    except (Unavailable, Refused) as exc:
        out = failure(exc, 'Everything on it is unmounted, but %s did not happen' % ('powering it off' if method == 'PowerOff' else 'ejecting it'))
        out['safe'] = False;return out
    after = storage(bus)
    gone = after['available'] and not any(d['id'] == drive_id for d in after['drives'])
    word = 'powered it off' if method == 'PowerOff' else 'ejected it'
    return dict(ok=True, verified=True, safe=True, gone=gone,
                said='Safe to remove: everything on %s is unmounted (read back) and udisks2 %s%s.' % (
                    drive['name'], word, ' (it has left the list)' if gone else ''))


# ---- Power: UPower --------------------------------------------------------------------------------------------------------
KINDS = {1: 'mains', 2: 'battery', 3: 'UPS', 4: 'monitor', 5: 'mouse', 6: 'keyboard', 7: 'handheld', 8: 'phone', 9: 'media player',
         10: 'tablet', 11: 'computer', 12: 'gaming input', 13: 'pen', 17: 'headset', 18: 'speakers', 19: 'headphones'}
STATES = {1: 'charging', 2: 'discharging', 3: 'empty', 4: 'full', 5: 'waiting to charge', 6: 'waiting to discharge'}


def power(bus=None):
    source = 'UPower (%s) on the %s D-Bus' % (UPOWER, bus_kind(bus))
    here = present(UPOWER, bus)
    if here not in ('running', 'activatable'):
        return absent('power', source, bus, here)
    try:
        top = all_properties(UPOWER, UP_ROOT, UPOWER, bus=bus)
        paths = first(call(UPOWER, UP_ROOT, UPOWER, 'EnumerateDevices', bus=bus)) or []
        devices = []
        for path in paths:
            p = all_properties(UPOWER, path, UPOWER + '.Device', bus=bus)
            kind = KINDS.get(p.get('Type'), 'device')
            if kind == 'battery' and p.get('IsPresent') is False:continue
            devices.append(dict(id=path, kind=kind, supply=bool(p.get('PowerSupply')), percent=percent(p.get('Percentage')),
                                state=STATES.get(p.get('State'), ''), online=bool(p.get('Online')),
                                to_empty=int(p.get('TimeToEmpty') or 0), to_full=int(p.get('TimeToFull') or 0),
                                name=' '.join(x for x in (text_of(p.get('Vendor')).strip(), text_of(p.get('Model')).strip()) if x)))
    except (Unavailable, Refused) as exc:
        return absent('power', source, bus, 'UPower did not answer (%s)' % str(exc)[:160])
    batteries = [d for d in devices if d['kind'] == 'battery' and d['supply']]
    mains = [d for d in devices if d['kind'] == 'mains']
    on_battery = bool(top.get('OnBattery'))
    if batteries:
        b = batteries[0]
        short = 'battery %s %%%s' % (b['percent'] if b['percent'] is not None else '?', (', ' + b['state']) if b['state'] else '')
    else:
        short = 'on mains' if mains and any(m['online'] for m in mains) else 'no battery'
    return section('power', source, devices=devices, batteries=batteries, mains=mains, on_battery=on_battery, short=short)


def battery_words(device):
    words = ['%s %%' % device['percent'] if device['percent'] is not None else 'level unknown']
    if device['state']:words.append(device['state'])
    if device['state'] == 'discharging' and device['to_empty']:words.append('about %s left' % duration_words(device['to_empty']))
    if device['state'] == 'charging' and device['to_full']:words.append('full in about %s' % duration_words(device['to_full']))
    return ', '.join(words)


# ---- Network: NetworkManager ----------------------------------------------------------------------------------------------
NM_STATES = {0: 'unknown', 10: 'asleep', 20: 'disconnected', 30: 'disconnecting', 40: 'connecting', 50: 'connected to this place only',
             60: 'connected to this place only', 70: 'connected'}
DEVICE_KINDS = {1: 'wired', 2: 'Wi-Fi', 5: 'Bluetooth', 14: 'generic', 30: 'Wi-Fi P2P'}
DEVICE_STATES = {10: 'unmanaged', 20: 'unavailable', 30: 'disconnected', 40: 'preparing', 50: 'configuring', 60: 'needs a password',
                 70: 'getting an address', 80: 'checking', 90: 'waiting', 100: 'connected', 110: 'disconnecting', 120: 'failed'}
REASONS = {7: 'NetworkManager had no password for it', 8: 'the network did not accept the password, or dropped the connection',
           9: 'the Wi-Fi security settings could not be used', 10: 'the Wi-Fi security part of the system failed',
           11: 'the network did not answer in time', 53: 'the network is out of reach'}


def security(flags, wpa, rsn):
    both = (wpa or 0) | (rsn or 0)
    if both & 0x2200:return 'enterprise'
    if both & 0x400 and not both & 0x100:return 'WPA3'
    if both & 0x100:return 'WPA'
    if both & 0x1800:return 'open'
    if (flags or 0) & 0x1:return 'WEP'
    return 'open'


def strength_word(value):
    value = value if isinstance(value, int) else 0
    return 'strong' if value >= 75 else 'good' if value >= 50 else 'fair' if value >= 25 else 'weak'


def network(bus=None):
    source = 'NetworkManager (%s) on the %s D-Bus' % (NM, bus_kind(bus))
    here = present(NM, bus)
    if here not in ('running', 'activatable'):
        return absent('network', source, bus, here)
    try:
        top = all_properties(NM, NM_ROOT, NM, bus=bus)
        devices = []
        for path in first(call(NM, NM_ROOT, NM, 'GetDevices', bus=bus)) or []:
            d = all_properties(NM, path, NM + '.Device', bus=bus)
            kind = DEVICE_KINDS.get(d.get('DeviceType'))
            if kind not in ('wired', 'Wi-Fi'):continue
            row = dict(id=path, interface=text_of(d.get('Interface')), kind=kind, state=DEVICE_STATES.get(d.get('State'), 'unknown'),
                       state_number=d.get('State') or 0, networks=[])
            if kind == 'Wi-Fi':
                w = all_properties(NM, path, NM + '.Device.Wireless', bus=bus)
                active = w.get('ActiveAccessPoint') or '/'
                saved = {}
                for conn in d.get('AvailableConnections') or []:
                    try:
                        settings = first(call(NM, conn, NM + '.Settings.Connection', 'GetSettings', bus=bus)) or {}
                    except Refused:
                        continue
                    ssid = (settings.get('802-11-wireless') or {}).get('ssid')
                    if ssid:saved.setdefault(text_of(ssid), conn)
                heard = {}
                for ap in w.get('AccessPoints') or []:
                    try:
                        a = all_properties(NM, ap, NM + '.AccessPoint', bus=bus)
                    except Refused:
                        continue      # an access point that went between the list and the read
                    name = text_of(a.get('Ssid'))
                    if not name:continue      # a hidden network has no name to show
                    strength = int(a.get('Strength') or 0)
                    entry = dict(id=ap, ssid=name, strength=strength, strength_word=strength_word(strength),
                                 security=security(a.get('Flags'), a.get('WpaFlags'), a.get('RsnFlags')), active=ap == active,
                                 saved=saved.get(name), device=path)
                    held = heard.get(name)
                    if held is None or entry['active'] or (not held['active'] and strength > held['strength']):heard[name] = entry
                row['networks'] = sorted(heard.values(), key=lambda n: (not n['active'], -n['strength'], n['ssid'].casefold()))
                row['active_ssid'] = next((n['ssid'] for n in row['networks'] if n['active']), '')
            devices.append(row)
    except (Unavailable, Refused) as exc:
        return absent('network', source, bus, 'NetworkManager did not answer (%s)' % str(exc)[:160])
    state = NM_STATES.get(top.get('State'), 'unknown')
    enabled = bool(top.get('NetworkingEnabled', True));wifi = bool(top.get('WirelessEnabled'));switch = bool(top.get('WirelessHardwareEnabled', True))
    wifi_devices = [d for d in devices if d['kind'] == 'Wi-Fi']
    active = next((d['active_ssid'] for d in wifi_devices if d.get('active_ssid')), '')
    short = ('off' if not enabled else (state + (' (Wi-Fi %s)' % active if active else '')))
    return section('network', source, state=state, state_number=top.get('State') or 0, enabled=enabled, wifi=wifi, wifi_switch=switch,
                   devices=devices, wifi_devices=wifi_devices, short=short)


def set_networking(on, bus=None):
    doing = 'Networking was not turned %s' % ('on' if on else 'off')
    try:
        call(NM, NM_ROOT, NM, 'Enable', bool(on), bus=bus, timeout=ACT_TIMEOUT_MS)
        now = get_property(NM, NM_ROOT, NM, 'NetworkingEnabled', bus=bus)
    except (Unavailable, Refused) as exc:
        return failure(exc, doing)
    if bool(now) == bool(on):return dict(ok=True, verified=True, said='Networking is %s (read back from NetworkManager).' % ('on' if on else 'off'))
    return dict(ok=True, verified=False, said='NetworkManager answered, but networking still reads %s.' % ('on' if now else 'off'))


def set_wifi(on, bus=None):
    doing = 'Wi-Fi was not turned %s' % ('on' if on else 'off')
    try:
        set_property(NM, NM_ROOT, NM, 'WirelessEnabled', bool(on), bus=bus)
        now = get_property(NM, NM_ROOT, NM, 'WirelessEnabled', bus=bus)
        switch = get_property(NM, NM_ROOT, NM, 'WirelessHardwareEnabled', bus=bus)
    except (Unavailable, Refused) as exc:
        return failure(exc, doing)
    if bool(now) == bool(on):
        extra = '' if switch is not False else ' The Wi-Fi switch on this computer is off, so no network is heard until it is on.'
        return dict(ok=True, verified=True, said='Wi-Fi is %s (read back from NetworkManager).%s' % ('on' if on else 'off', extra))
    return dict(ok=True, verified=False, said='NetworkManager answered, but Wi-Fi still reads %s.' % ('on' if now else 'off'))


def scan(device, bus=None):
    try:
        call(NM, device, NM + '.Device.Wireless', 'RequestScan', {}, bus=bus, timeout=ACT_TIMEOUT_MS)
    except (Unavailable, Refused) as exc:
        return failure(exc, 'Looking for networks did not start')
    return dict(ok=True, verified=True, said='NetworkManager is listening for networks; the list fills as they answer.')


def _active_state(active, bus):
    try:
        return get_property(NM, active, NM + '.Connection.Active', 'State', bus=bus)
    except Refused:
        return 4      # the active connection went away: deactivated
    except Unavailable:
        return None


def _reason(device, bus):
    try:
        pair = get_property(NM, device, NM + '.Device', 'StateReason', bus=bus)
        number = pair[1] if isinstance(pair, (list, tuple)) and len(pair) > 1 else None
    except (Unavailable, Refused):
        number = None
    return REASONS.get(number, 'NetworkManager could not connect%s' % ((' (its reason %s)' % number) if number else ''))


def join(device, access_point, ssid, password=None, bus=None, seconds=JOIN_SECONDS, sleep=time.sleep, clock=time.monotonic):
    """Join a Wi-Fi network. A network NetworkManager has saved is activated with its saved connection; an open one is added
    as it is; a secured new one is added with the password the owner typed, passed once in that call and kept by
    NetworkManager (Graphite keeps no copy). Done only when NetworkManager reads back the connection as activated on that
    network. A connection this call added that then fails is taken away again (nothing half-made is left saved)."""
    now = network(bus)
    if not now['available']:return dict(ok=False, verified=False, said=now['why'])
    entry = next((n for d in now['wifi_devices'] if d['id'] == device for n in d['networks'] if n['ssid'] == ssid), None)
    if entry is None:return dict(ok=False, verified=False, said='%s is not heard here now: nothing was done.' % ssid)
    created = None;doing = 'Joining %s did not happen' % ssid
    try:
        if entry['saved']:
            active = first(call(NM, NM_ROOT, NM, 'ActivateConnection', object_path(entry['saved']), object_path(device),
                                object_path(access_point), bus=bus, timeout=ACT_TIMEOUT_MS))
        elif entry['security'] == 'open':
            created, active = call(NM, NM_ROOT, NM, 'AddAndActivateConnection', settings_map({}), object_path(device),
                                   object_path(access_point), bus=bus, timeout=ACT_TIMEOUT_MS)[:2]
        elif entry['security'] in ('WPA', 'WPA3'):
            if not password:return dict(ok=False, verified=False, said='%s is secured: type its password, then Join.' % ssid)
            key = 'sae' if entry['security'] == 'WPA3' else 'wpa-psk'
            settings = settings_map({'802-11-wireless-security': {'key-mgmt': key, 'psk': password}})
            password = None      # the words go to NetworkManager in this call and are kept nowhere here
            created, active = call(NM, NM_ROOT, NM, 'AddAndActivateConnection', settings, object_path(device),
                                   object_path(access_point), bus=bus, timeout=ACT_TIMEOUT_MS)[:2]
            del settings
        elif entry['security'] == 'enterprise':
            return dict(ok=False, verified=False, said='%s needs an organisation\'s sign-in (802.1X). Kas 1.0 does not set that up: use nmtui in the Terminal.' % ssid)
        else:
            return dict(ok=False, verified=False, said='%s uses WEP, an old security that is no longer safe. Kas does not join it.' % ssid)
    except (Unavailable, Refused) as exc:
        return failure(exc, doing)
    deadline = clock() + seconds;state = None
    while clock() < deadline:
        state = _active_state(active, bus)
        if state in (2, 4, None):break
        sleep(0.5)
    if state == 2:
        try:
            ap = get_property(NM, device, NM + '.Device.Wireless', 'ActiveAccessPoint', bus=bus) or '/'
            heard = text_of(get_property(NM, ap, NM + '.AccessPoint', 'Ssid', bus=bus)) if ap != '/' else ''
        except (Unavailable, Refused):
            heard = ''
        if heard == ssid:
            return dict(ok=True, verified=True, said='Joined %s (read back from NetworkManager). NetworkManager keeps its password, not Kas.' % ssid)
        return dict(ok=True, verified=False, said='NetworkManager reports a connection, but not on %s.' % ssid)
    why = _reason(device, bus) if state == 4 else 'it was still connecting after %d seconds' % seconds
    if created and state == 4:
        try:
            call(NM, created, NM + '.Settings.Connection', 'Delete', bus=bus, timeout=ACT_TIMEOUT_MS)
            why += '; the new connection was taken away again'
        except (Unavailable, Refused):
            pass
    return dict(ok=False, verified=False, said='Did not join %s: %s.' % (ssid, why))


def disconnect(device, bus=None, sleep=time.sleep):
    try:
        call(NM, device, NM + '.Device', 'Disconnect', bus=bus, timeout=ACT_TIMEOUT_MS)
        state = None
        for _ in range(10):
            state = get_property(NM, device, NM + '.Device', 'State', bus=bus)
            if state != 100:break
            sleep(0.3)
    except (Unavailable, Refused) as exc:
        return failure(exc, 'Disconnecting did not happen')
    if state != 100:return dict(ok=True, verified=True, said='Disconnected (read back: %s).' % DEVICE_STATES.get(state, 'not connected'))
    return dict(ok=True, verified=False, said='NetworkManager answered, but it still reads as connected.')


# ---- Programs: wpctl and xrandr -------------------------------------------------------------------------------------------
def where(program):
    if program not in PROGRAMS:raise ValueError('Kas runs only wpctl or xrandr here: %r' % (program,))
    return shutil.which(program)


def run(argv, timeout=8):
    """argv[0] is wpctl or xrandr, found on PATH; no shell, no terminal, never sudo. dict(ok, code, out, err)."""
    if not argv or argv[0] not in PROGRAMS or any(part in ('sudo', 'pkexec', 'su', 'doas') for part in argv):
        raise ValueError('Kas runs only wpctl or xrandr here: %r' % (argv,))
    path = where(argv[0])
    if path is None:return dict(ok=False, code=None, out='', err='%s is not installed on this computer' % argv[0])
    try:
        done = subprocess.run([path, *[str(a) for a in argv[1:]]], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return dict(ok=False, code=None, out='', err=str(exc)[:300])
    return dict(ok=done.returncode == 0, code=done.returncode, out=done.stdout or '', err=(done.stderr or '').strip()[-300:])


# ---- Sound: PipeWire through wpctl ----------------------------------------------------------------------------------------
DEFAULT_SINK = '@DEFAULT_AUDIO_SINK@'
SINK_LINE = re.compile(r'^[\s│]*(\*)?\s*(\d+)\.\s+(.*?)\s*(?:\[vol:\s*([\d.]+)(\s+MUTED)?\])?\s*$')
BRANCH = re.compile(r'^[\s│]*[├└]─\s*(.+?):\s*$')
VOLUME = re.compile(r'Volume:\s*(\d+(?:\.\d+)?)(\s*\[MUTED\])?')


def parse_sinks(text):
    """The Audio section's Sinks of `wpctl status`: [dict(id, name, default, percent, muted)]."""
    out = [];top = None;branch = None
    for raw in (text or '').splitlines():
        line = raw.rstrip()
        if not line.strip():continue
        if not line[0].isspace() and line[0] not in '│├└':
            top = line.strip();branch = None;continue
        found = BRANCH.match(line)
        if found:branch = found.group(1).strip();continue
        if top == 'Audio' and branch == 'Sinks':
            row = SINK_LINE.match(line)
            if row:
                out.append(dict(id=int(row.group(2)), name=row.group(3).strip(), default=bool(row.group(1)),
                                percent=percent(Decimal(row.group(4)) * 100) if row.group(4) else None, muted=bool(row.group(5))))
    return out


def volume_of(text):
    """'Volume: 0.40 [MUTED]' -> (40, True), through the decimal digits."""
    found = VOLUME.search(text or '')
    if not found:return None, None
    return percent(Decimal(found.group(1)) * 100), bool(found.group(2))


def sound():
    source = 'PipeWire through wpctl (WirePlumber)'
    if where('wpctl') is None:
        return unavailable('sound', source, '%s: wpctl (WirePlumber, the PipeWire session manager) is not installed. Debian has it as the package %s, in the 1.0 System set.' % (NOT_HERE, PACKAGES['sound']), 'not available: no wpctl')
    status = run(['wpctl', 'status'])
    if not status['ok']:
        return unavailable('sound', source, '%s: PipeWire is not answering in this session (wpctl: %s).' % (NOT_HERE, status['err'] or 'exit status %s' % status['code']),
                           'not available: PipeWire is not answering')
    sinks = parse_sinks(status['out'])
    level, muted = volume_of(run(['wpctl', 'get-volume', DEFAULT_SINK])['out']) if sinks else (None, None)
    current = next((s for s in sinks if s['default']), None)
    if not sinks:short = 'no output'
    elif muted:short = 'muted'
    else:short = '%s %%' % level if level is not None else 'volume unknown'
    return section('sound', source, sinks=sinks, current=current, percent=level, muted=bool(muted), short=short)


def set_volume(level):
    level = max(0, min(100, int(level)))
    done = run(['wpctl', 'set-volume', DEFAULT_SINK, '%d%%' % level])
    if not done['ok']:return dict(ok=False, verified=False, said='The volume did not change: %s' % (done['err'] or 'wpctl failed'))
    now, _ = volume_of(run(['wpctl', 'get-volume', DEFAULT_SINK])['out'])
    if now is not None and abs(now - level) <= 1:return dict(ok=True, verified=True, said='Volume %d %% (read back).' % now, percent=now)
    return dict(ok=True, verified=False, said='wpctl answered, but the volume reads %s.' % ('%d %%' % now if now is not None else 'nothing'))


def set_mute(on):
    done = run(['wpctl', 'set-mute', DEFAULT_SINK, '1' if on else '0'])
    if not done['ok']:return dict(ok=False, verified=False, said='Mute did not change: %s' % (done['err'] or 'wpctl failed'))
    _, muted = volume_of(run(['wpctl', 'get-volume', DEFAULT_SINK])['out'])
    if muted is not None and bool(muted) == bool(on):return dict(ok=True, verified=True, said=('Muted' if on else 'Sound on') + ' (read back).')
    return dict(ok=True, verified=False, said='wpctl answered, but it reads %s.' % ('muted' if muted else 'not muted'))


def set_output(sink_id):
    sink_id = int(sink_id)
    done = run(['wpctl', 'set-default', str(sink_id)])
    if not done['ok']:return dict(ok=False, verified=False, said='The output did not change: %s' % (done['err'] or 'wpctl failed'))
    sinks = parse_sinks(run(['wpctl', 'status'])['out'])
    chosen = next((s for s in sinks if s['default']), None)
    if chosen and chosen['id'] == sink_id:return dict(ok=True, verified=True, said='Sound plays through %s (read back).' % chosen['name'])
    return dict(ok=True, verified=False, said='wpctl answered, but the output in use reads %s.' % (chosen['name'] if chosen else 'none'))


# ---- Screens: xrandr ------------------------------------------------------------------------------------------------------
OUTPUT_LINE = re.compile(r'^(\S+) (connected|disconnected)( primary)?(?: (\d+)x(\d+)\+(\d+)\+(\d+))?')
MODE_LINE = re.compile(r'^\s+(\d+x\d+i?)\s+(.*)$')
NAME = re.compile(r'^[A-Za-z0-9_.-]{1,32}$')
MODE = re.compile(r'^\d{2,5}x\d{2,5}i?$')


def parse_outputs(text):
    """`xrandr --current` (or --query) -> [dict(name, connected, primary, active, width, height, x, y, modes:[dict(mode, rates, current, preferred)], current)]."""
    out = [];row = None
    for line in (text or '').splitlines():
        found = OUTPUT_LINE.match(line)
        if found:
            name, state, primary = found.group(1), found.group(2), bool(found.group(3))
            geometry = [int(found.group(i)) for i in range(4, 8)] if found.group(4) else None
            row = dict(name=name, connected=state == 'connected', primary=primary, active=geometry is not None,
                       width=geometry[0] if geometry else None, height=geometry[1] if geometry else None,
                       x=geometry[2] if geometry else None, y=geometry[3] if geometry else None, modes=[], current=None)
            out.append(row);continue
        mode = MODE_LINE.match(line)
        if mode and row is not None:
            rates = mode.group(2).split()
            entry = dict(mode=mode.group(1), rates=[r.rstrip('*+') for r in rates if r.rstrip('*+')],
                         current=any('*' in r for r in rates), preferred=any('+' in r for r in rates))
            row['modes'].append(entry)
            if entry['current']:row['current'] = entry['mode']
    return out


def arrangement(outputs):
    active = [o for o in outputs if o['active']]
    if len(active) <= 1:return 'one screen'
    places = {(o['x'], o['y']) for o in active}
    return 'mirror' if len(places) == 1 else 'extend'


def screens(environ=None):
    environ = os.environ if environ is None else environ
    source = 'xrandr on this session\'s X display'
    if not environ.get('DISPLAY'):
        return unavailable('screens', source, '%s: there is no X display in this session (DISPLAY is not set), so there are no screens to arrange.' % NOT_HERE, 'not available: no X display')
    if where('xrandr') is None:
        return unavailable('screens', source, '%s: xrandr is not installed. Debian has it in the package %s, in the 1.0 System set.' % (NOT_HERE, PACKAGES['screens']), 'not available: no xrandr')
    query = run(['xrandr', '--current'])      # what the X server holds now: no re-probe of the outputs on every reading
    if not query['ok']:
        return unavailable('screens', source, '%s: the X display did not answer xrandr (%s).' % (NOT_HERE, query['err'] or 'exit status %s' % query['code']),
                           'not available: the X display did not answer')
    outputs = parse_outputs(query['out'])
    connected = [o for o in outputs if o['connected']]
    how = arrangement(outputs)
    short = ('%d screens, %s' % (len(connected), how if how != 'one screen' else 'one on')) if len(connected) > 1 else (
        '%s %s' % (connected[0]['name'], connected[0]['current'] or 'off') if connected else 'none connected')
    return section('screens', source, outputs=outputs, connected=connected, arrangement=how, short=short)


def restore_args(outputs):
    """The xrandr words that put the arrangement read in `outputs` back (Keep or Go back after a change)."""
    args = []
    for o in outputs:
        if o['active'] and o['current']:
            args += ['--output', o['name'], '--mode', o['current'], '--pos', '%dx%d' % (o['x'], o['y'])] + (['--primary'] if o['primary'] else [])
        elif o['connected'] or o['active']:
            args += ['--output', o['name'], '--off']
    return args


def plan(change, outputs, name=None, mode=None):
    """The xrandr words for one change, checked against what was read: mode, primary, off, on, mirror, extend."""
    names = {o['name']: o for o in outputs}
    if name is not None and (not NAME.match(str(name)) or name not in names):raise ValueError('No screen called %r here.' % (name,))
    active = [o for o in outputs if o['active']];connected = [o for o in outputs if o['connected']]
    primary = next((o for o in active if o['primary']), active[0] if active else None)
    if change == 'mode':
        if not MODE.match(str(mode)) or mode not in [m['mode'] for m in names[name]['modes']]:raise ValueError('%s has no mode %r.' % (name, mode))
        return ['--output', name, '--mode', mode]
    if change == 'primary':return ['--output', name, '--primary']
    if change == 'off':
        if len(active) <= 1 and names[name]['active']:raise ValueError('%s is the only screen on: Kas never turns the last one off.' % name)
        return ['--output', name, '--off']
    if change == 'on':
        if not names[name]['connected']:raise ValueError('%s has nothing connected.' % name)
        return ['--output', name, '--auto'] + (['--right-of', primary['name']] if primary and primary['name'] != name else [])
    if change in ('mirror', 'extend'):
        if primary is None or len(connected) < 2:raise ValueError('Mirror and extend need two connected screens.')
        args = [];left = primary
        for o in connected:
            if o['name'] == primary['name']:continue
            if change == 'mirror':
                common = next((m['mode'] for m in o['modes'] if m['mode'] == primary['current']), None)
                args += ['--output', o['name']] + (['--mode', common] if common else ['--auto']) + ['--same-as', primary['name']]
            else:
                args += ['--output', o['name'], '--auto', '--right-of', left['name']];left = o
        return args
    raise ValueError('Unknown change to the screens: %r' % (change,))


def apply_screens(args, expect=None):
    """Run one xrandr change and read the screens back. expect(outputs) -> True when the change shows; done only then."""
    for part in args:
        if not (part.startswith('--') or NAME.match(part) or MODE.match(part) or re.match(r'^\d{1,5}x\d{1,5}$', part)):
            raise ValueError('Not an xrandr word Kas uses: %r' % (part,))
    done = run(['xrandr', *args])
    if not done['ok']:return dict(ok=False, verified=False, said='The screens did not change: %s' % (done['err'] or 'xrandr failed'))
    now = screens()
    if not now['available']:return dict(ok=True, verified=False, said='xrandr answered, but the screens could not be read back: ' + now['why'])
    seen = bool(expect(now['outputs'])) if expect else True
    return dict(ok=True, verified=seen, outputs=now['outputs'],
                said=('The screens changed (read back: %s).' % now['short']) if seen else 'xrandr answered, but reading the screens back does not show the change.')


def expectation(change, name=None, mode=None):
    """What reading the screens back must show after a change."""
    if change == 'mode':return lambda outs: any(o['name'] == name and o['current'] == mode for o in outs)
    if change == 'primary':return lambda outs: any(o['name'] == name and o['primary'] for o in outs)
    if change == 'off':return lambda outs: any(o['name'] == name and not o['active'] for o in outs)
    if change == 'on':return lambda outs: any(o['name'] == name and o['active'] for o in outs)
    if change in ('mirror', 'extend'):return lambda outs: arrangement(outs) == change
    return None


def change_screens(change, name=None, mode=None):
    """One change to the screens on the owner's press; returns the arrangement it replaced (before) so it can be put back."""
    now = screens()
    if not now['available']:return dict(ok=False, verified=False, said=now['why'])
    try:
        args = plan(change, now['outputs'], name, mode)
    except ValueError as exc:
        return dict(ok=False, verified=False, said=str(exc))
    out = apply_screens(args, expectation(change, name, mode));out['before'] = restore_args(now['outputs']);return out


def put_back(before):
    """Go back to an arrangement read before a change (its restore_args)."""
    if not before:return dict(ok=False, verified=False, said='Nothing to go back to.')
    wanted = {};name = None
    for i, part in enumerate(before):
        if part == '--output':name = before[i + 1];wanted[name] = None
        if part == '--mode' and name is not None:wanted[name] = before[i + 1]
    return apply_screens(before, lambda outs: all((o['current'] if o['active'] else None) == wanted.get(o['name']) for o in outs if o['name'] in wanted))


# ---- All of it ------------------------------------------------------------------------------------------------------------
READERS = {'storage': storage, 'power': power, 'network': network, 'sound': lambda bus=None: sound(), 'screens': lambda bus=None: screens()}


def read(key, bus=None):
    """One section; a reader that fails says so in its own words (never raises)."""
    try:
        return READERS[key](bus=bus)
    except Exception as exc:  # noqa: BLE001 - a broken reading is a section that says what went wrong, never a broken window
        return unavailable(key, TITLES[key], '%s: reading it failed here (%s: %s).' % (NOT_HERE, type(exc).__name__, str(exc)[:160]))


def snapshot(keys=None, bus=None):
    return {key: read(key, bus) for key in (keys or SECTIONS)}


# ---- The Kernel's read (1.0 S4): machine.state, for her observation; changes are never Kernel operations ---------------------
FIELDS = {'machine.state': ({'section': {'type': 'string', 'enum': list(SECTIONS)}}, [])}
SCOPES = {'machine.state': 'read'}


def dispatch(kernel, op, args, principal):
    if op != 'machine.state':raise ValueError('Unknown machine operation')
    keys = [args['section']] if args.get('section') else list(SECTIONS)
    sections = snapshot(keys)
    return {'schema': SCHEMA, 'bus': bus_kind(), 'sections': sections,
            'basis': 'observed now on the computer Kas runs on, through its own services; reading changed nothing'}
