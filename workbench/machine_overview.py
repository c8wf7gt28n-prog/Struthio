"""Read-only observations of the computer this Ledger runs on, for the left-column Machine view.

Sources are /proc, /sys and os.statvfs only: no subprocess, no network, no device access beyond reading sysfs
attributes. Every item carries its source path and sampled time; a source that cannot be read is an honest
UNAVAILABLE state with its reason, never a guess or an animated placeholder. Lists are bounded and say so.

Basis: CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION. These are observations of the machine running Ledger
now; they qualify nothing about the owner's ThinkPad until read there. The ARC project hardware (F133, D213,
FPGAs, NOR, PCB) stays in hardware_nav under Work / Project; this module never describes it.
"""
from __future__ import annotations
import os
import re
import shutil
import time
from pathlib import Path, PurePosixPath
from . import host_observations

PROC = '/proc'
SYS = '/sys'
BASIS = 'CURRENT_LEDGER_HOST_NOT_OWNER_HOST_QUALIFICATION'
SCHEMA = 'ledger.machine/1'
SECTIONS = ('processor', 'memory', 'storage', 'connections', 'devices', 'tools')
TITLES = {'processor': 'Processor', 'memory': 'Memory', 'storage': 'Storage', 'connections': 'Connections',
          'devices': 'Devices', 'tools': 'Installed tools'}
# Bounds: how many like items a list may carry, how long one word may be, how much of one /proc file is read.
BOUND = 64
DISK_BOUND = 32
DISPLAY_BOUND = 16
PARTITION_BOUND = 16
TEXT_LIMIT = 160
READ_LIMIT = 256 * 1024
# Pseudo and memory-backed block devices are not storage; everything else under /sys/block is listed.
SKIP_BLOCK = ('loop', 'ram', 'zram')
# Mounts of these kinds are kernel plumbing, never a place work is kept.
PLUMBING = {'proc', 'sysfs', 'cgroup', 'cgroup2', 'devpts', 'mqueue', 'securityfs', 'debugfs', 'tracefs', 'pstore', 'bpf',
            'configfs', 'fusectl', 'hugetlbfs', 'autofs', 'binfmt_misc', 'rpc_pipefs', 'nsfs', 'efivarfs', 'selinuxfs', 'devtmpfs'}
TOOL_NAMES = {'math': 'LibreOffice (soffice)', 'cad': 'KiCad (kicad-cli)', 'kibot': 'KiBot', 'spice': 'ngspice', 'yosys': 'Yosys',
              'nextpnr': 'nextpnr (nextpnr-ecp5)', 'trellis': 'Project Trellis (ecppack)', 'surfer': 'Surfer',
              'icarus': 'Icarus Verilog (iverilog)', 'verilator': 'Verilator',
              'brain': 'llama.cpp runtime (pinned archive)', 'python-wasi': 'Python WASI runtime (pinned archive)'}
TOOL_SOURCES = {'brain': 'runtimes/llama.cpp/b11669/runtime.json · sha256 of the pinned archive',
                'python-wasi': 'runtimes/python-wasi/python-wasi.zip · installed wasmtime package'}

FIELDS = {'ledger.machine': ({'section': {'type': 'string', 'enum': list(SECTIONS)}}, [])}
SCOPES = {op: 'read' for op in FIELDS}


# ---------------------------------------------------------------- small, non-raising readers
def read_text(path, limit=READ_LIMIT):
    """(text, None) or (None, reason). Reads at most `limit` bytes; never raises."""
    try:
        with open(path, 'rb') as stream:
            raw = stream.read(limit)
        return raw.decode('utf-8', 'replace'), None
    except FileNotFoundError:
        return None, 'not present: ' + str(path)
    except OSError as exc:
        return None, 'unreadable: ' + str(path) + ' (' + type(exc).__name__ + ')'


def read_line(path):
    text, _ = read_text(path, 4096)
    return text.splitlines()[0].strip() if text else None


def read_int(path):
    line = read_line(path)
    try:
        return int(line, 0) if line is not None else None
    except ValueError:
        return None


def clip(value):
    return re.sub(r'\s+', ' ', str(value)).strip()[:TEXT_LIMIT]


def natural(value):
    return tuple((1, int(part)) if part.isdigit() else (0, part.casefold()) for part in re.split(r'(\d+)', str(value)))


def ordered(rows):
    """Comparable siblings in natural order of their label (digits by value, letters case-folded), ties by id."""
    return sorted(rows, key=lambda row: (natural(row['label']), row['id']))


def human(count):
    if count is None:
        return 'not observed'
    value = float(count)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'):
        if value < 1024 or unit == 'PiB':
            return ('%d %s' if unit == 'B' else '%.1f %s') % (value, unit)
        value /= 1024
    return str(count)


def item(ident, label, kind, source, clock, values=None, state='OBSERVED', reason=None):
    row = dict(id=ident, label=clip(label), kind=kind, state=state, source=source, sampled_at=clock(), values=values or {})
    if reason:
        row['reason'] = clip(reason)
    return row


def section(ident, clock, items=(), state=None, sources=(), notes=(), partial=False, order='natural'):
    rows = list(items)
    if state is None:
        state = 'OBSERVED' if rows else 'NONE'
    if partial and state == 'OBSERVED':
        state = 'PARTIAL'
    return dict(id=ident, title=TITLES[ident], state=state, items=rows, count=len(rows), sources=list(sources), notes=list(notes),
                partial=bool(partial), order=order, sampled_at=clock())


def unavailable(ident, clock, reason, sources=()):
    return section(ident, clock, [], 'UNAVAILABLE', sources, [clip(reason)])


def bounded(rows, limit):
    return rows[:limit], len(rows) > limit


# ---------------------------------------------------------------- processor
def cpu_fields(text):
    """Model name, core and thread counts from /proc/cpuinfo text (x86 and the ARM spellings)."""
    model = None; fallback = None; threads = 0; cores = None; sockets = set()
    for line in text.splitlines():
        key, _, value = line.partition(':')
        key = key.strip().lower(); value = value.strip()
        if key == 'processor' and value.isdigit():
            threads += 1
        elif key == 'model name' and value and model is None:
            model = value
        elif key in ('hardware', 'model') and value and not value.isdigit() and fallback is None:
            fallback = value  # ARM boards publish Hardware/Model words instead of a model name; x86 "model" is a bare number
        elif key == 'cpu cores' and cores is None and value.isdigit():
            cores = int(value)
        elif key == 'physical id' and value:
            sockets.add(value)
    model = model or fallback
    return dict(model=clip(model) if model else None, threads=threads or None, cores=cores,
                sockets=len(sockets) or None)


def short_model(model):
    """The word the strip has room for: vendor noise, clock and graphics suffixes removed."""
    if not model:
        return ''
    text = re.sub(r'\((?:R|TM|tm|r)\)', '', str(model))
    text = re.sub(r'@\s*[\d.]+\s*[GM]Hz', '', text)
    text = re.sub(r'\b(?:CPU|Processor|with Radeon Graphics|w/ Radeon Graphics|[0-9]+-Core)\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip(' -·')
    return text[:28].rstrip() + ('…' if len(text) > 28 else '')


def cpu_model(proc=PROC):
    text, _ = read_text(Path(proc) / 'cpuinfo')
    return cpu_fields(text)['model'] if text else None


def processor(proc=PROC, clock=time.time):
    base = Path(proc)
    text, reason = read_text(base / 'cpuinfo')
    rows = []; notes = []; sources = [str(base / 'cpuinfo'), str(base / 'loadavg'), 'os.cpu_count()']
    if text is None:
        notes.append(reason)
    else:
        fields = cpu_fields(text)
        words = fields['model'] or 'Model name not published by the kernel'
        detail = [w for w in ((str(fields['cores']) + ' cores') if fields['cores'] else None,
                              (str(fields['threads']) + ' threads') if fields['threads'] else None,
                              (str(fields['sockets']) + ' sockets') if fields['sockets'] and fields['sockets'] > 1 else None) if w]
        rows.append(item('processor:model', words + (' · ' + ' · '.join(detail) if detail else ''), 'processor',
                         str(base / 'cpuinfo'), clock, fields, 'OBSERVED' if fields['model'] else 'PARTIAL'))
    online = os.cpu_count()
    rows.append(item('processor:online', ('%d logical processors available to Graphite' % online) if online else 'Logical processor count unavailable',
                     'processor_count', 'os.cpu_count()', clock, dict(online=online), 'OBSERVED' if online else 'UNAVAILABLE'))
    load = read_line(base / 'loadavg')
    parts = load.split() if load else []
    if len(parts) >= 4:
        try:
            one, five, fifteen = (float(parts[i]) for i in range(3)); runnable, total = (int(v) for v in parts[3].split('/'))
            rows.append(item('processor:load', 'Load average %s · %s · %s (1, 5, 15 min) · %d of %d tasks runnable' % (parts[0], parts[1], parts[2], runnable, total),
                             'load', str(base / 'loadavg'), clock, dict(one=one, five=five, fifteen=fifteen, runnable=runnable, tasks=total)))
        except ValueError:
            notes.append('loadavg could not be parsed')
    else:
        notes.append('load average unavailable: ' + str(base / 'loadavg'))
    state = 'UNAVAILABLE' if text is None and not online else None
    return section('processor', clock, rows, state, sources, notes, order='fixed')


# ---------------------------------------------------------------- memory
def meminfo(proc=PROC):
    text, reason = read_text(Path(proc) / 'meminfo')
    if text is None:
        return None, reason
    values = {}
    for line in text.splitlines():
        key, _, rest = line.partition(':')
        parts = rest.split()
        if parts and parts[0].isdigit():
            values[key.strip()] = int(parts[0]) * (1024 if len(parts) > 1 and parts[1] == 'kB' else 1)
    return values, None


def memory(proc=PROC, sys_root=SYS, clock=time.time):
    source = str(Path(proc) / 'meminfo')
    values, reason = meminfo(proc)
    if values is None:
        return unavailable('memory', clock, reason, [source])
    rows = []; notes = []
    sample = host_observations.memory() if proc == PROC else None
    if sample is None and 'MemTotal' in values and 'MemAvailable' in values and 0 <= values['MemAvailable'] <= values['MemTotal'] > 0:
        total = values['MemTotal']; available = values['MemAvailable']
        sample = dict(used=total - available, total=total, percent=round(100 * (total - available) / total))
    if sample:
        rows.append(item('memory:ram', 'RAM %s of %s in use (%d%%)' % (human(sample['used']), human(sample['total']), sample['percent']),
                         'ram', source + ':MemTotal,MemAvailable', clock, dict(sample, available=sample['total'] - sample['used'])))
    else:
        rows.append(item('memory:ram', 'RAM figures unavailable', 'ram', source, clock, {}, 'UNAVAILABLE', 'MemTotal/MemAvailable missing or inconsistent'))
    if 'SwapTotal' in values:
        total = values['SwapTotal']; free = values.get('SwapFree', 0)
        rows.append(item('memory:swap', ('Swap %s of %s in use' % (human(total - free), human(total))) if total else 'No swap configured',
                         'swap', source + ':SwapTotal,SwapFree', clock, dict(total=total, free=free, used=total - free)))
    ceiling = Path(sys_root) / 'fs/cgroup/memory.max'
    limit = read_line(ceiling)
    if limit and limit.isdigit():
        rows.append(item('memory:ceiling', 'Memory ceiling %s (this Graphite runs inside a cgroup limit)' % human(int(limit)), 'ceiling', str(ceiling), clock,
                         dict(limit=int(limit), current=read_int(ceiling.parent / 'memory.current'))))
    return section('memory', clock, rows, None, [source, str(ceiling)], notes, order='fixed')


# ---------------------------------------------------------------- storage
def unescape_mount(value):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), value)


def mounts(proc=PROC):
    """Every mount line, parsed; the caller decides which are storage. (rows, reason)."""
    text, reason = read_text(Path(proc) / 'mounts')
    if text is None:
        return None, reason
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        rows.append(dict(device=unescape_mount(parts[0]), mountpoint=unescape_mount(parts[1]), fstype=parts[2],
                         options=parts[3].split(','), readonly='ro' in parts[3].split(',')))
    return rows, None


def space(path):
    """Total and free bytes of the filesystem holding `path`, or None. os.statvfs only."""
    try:
        st = os.statvfs(str(path))
    except (OSError, ValueError, TypeError):
        return None
    return dict(total=st.f_frsize * st.f_blocks, free=st.f_frsize * st.f_bavail, source='os.statvfs(%s)' % path)


def holder(path, rows):
    """The mount whose mountpoint is the longest prefix of `path`, or None."""
    if not rows or path is None:
        return None
    try:
        target = PurePosixPath(os.path.realpath(str(path)))
    except (OSError, ValueError):
        return None
    best = None
    for row in rows:
        point = PurePosixPath(row['mountpoint'])
        try:
            related = target == point or target.is_relative_to(point)
        except ValueError:
            related = False
        if related and (best is None or len(point.parts) > len(PurePosixPath(best['mountpoint']).parts)):
            best = row
    return best


def block_devices(sys_root=SYS, clock=time.time):
    base = Path(sys_root) / 'block'
    try:
        names = sorted((p.name for p in base.iterdir()), key=natural)
    except OSError as exc:
        return None, 'not present: ' + str(base) if isinstance(exc, FileNotFoundError) else 'unreadable: ' + str(base), False
    rows = []
    for name in names:
        if name.startswith(SKIP_BLOCK):
            continue
        folder = base / name
        sectors = read_int(folder / 'size')
        size = sectors * 512 if sectors is not None else None
        rotational = read_int(folder / 'queue/rotational')
        model = read_line(folder / 'device/model')
        vendor = read_line(folder / 'device/vendor')
        removable = read_int(folder / 'removable')
        readonly = read_int(folder / 'ro')
        try:
            partitions = sorted((p.name for p in folder.iterdir() if p.name.startswith(name) and (p / 'size').exists()), key=natural)
        except OSError:
            partitions = []
        partitions, more = bounded(partitions, PARTITION_BOUND)
        words = [name, human(size) if size is not None else 'size unavailable',
                 {0: 'solid state', 1: 'rotating'}.get(rotational, 'medium unknown')]
        if model:
            words.append(clip((vendor + ' ' if vendor and vendor.lower() not in model.lower() else '') + model))
        if removable:
            words.append('removable')
        if partitions:
            words.append('%d partitions' % len(partitions) + (' or more' if more else ''))
        rows.append(item('storage:device:' + name, ' · '.join(words), 'block_device', str(folder), clock,
                         dict(size=size, rotational=rotational, model=model, vendor=vendor, removable=removable, readonly=readonly,
                              partitions=partitions, partitions_bounded=more),
                         'OBSERVED' if size is not None else 'PARTIAL'))
    rows, more = bounded(rows, DISK_BOUND)
    return rows, None, more


def storage(proc=PROC, sys_root=SYS, program=None, workspace=None, clock=time.time):
    rows = []; notes = []; partial = False
    sources = [str(Path(sys_root) / 'block'), str(Path(proc) / 'mounts'), 'os.statvfs']
    table, reason = mounts(proc)
    if table is None:
        notes.append(reason); table = []
    # The two places Ledger lives, named first: where the program is and where the work is.
    for key, label, path in (('program', 'Graphite program folder', program), ('workspace', 'Workspace', workspace)):
        if path is None:
            continue
        mount = holder(path, table); free = space(path)
        words = label + ' · ' + str(path)
        if mount:
            words += ' · on ' + mount['device'] + ' at ' + mount['mountpoint']
        if free:
            words += ' · ' + human(free['free']) + ' free'
        rows.append(item('storage:path:' + key, words, 'ledger_path', 'os.statvfs + ' + str(Path(proc) / 'mounts'), clock,
                         dict(path=str(path), exists=Path(path).exists(), mountpoint=mount['mountpoint'] if mount else None,
                              device=mount['device'] if mount else None, fstype=mount['fstype'] if mount else None,
                              free=free['free'] if free else None, total=free['total'] if free else None),
                         'OBSERVED' if free else 'UNAVAILABLE', None if free else 'statvfs failed or the path does not exist'))
    devices, reason, more = block_devices(sys_root, clock)
    if devices is None:
        notes.append(reason)
    else:
        rows.extend(devices); partial = partial or more
        if not devices:
            notes.append('No block devices other than loop, ram and zram under ' + str(Path(sys_root) / 'block'))
    marked = {}
    for key, path in (('program folder', program), ('workspace', workspace)):
        mount = holder(path, table)
        if mount:
            marked.setdefault(mount['mountpoint'], []).append(key)
    real = [row for row in table if (row['device'].startswith('/dev/') and not row['device'].startswith('/dev/loop') and row['fstype'] not in PLUMBING)
            or row['mountpoint'] in marked]
    seen = set(); mount_rows = []
    for row in real:
        if row['mountpoint'] in seen:
            continue
        seen.add(row['mountpoint'])
        free = space(row['mountpoint'])
        roles = marked.get(row['mountpoint'], [])
        words = [row['mountpoint'], row['fstype'] + (' read-only' if row['readonly'] else ''),
                 (human(free['free']) + ' free of ' + human(free['total'])) if free else 'space unavailable', row['device']]
        if roles:
            words.append('holds the ' + ' and the '.join(roles))
        mount_rows.append(item('storage:mount:' + row['mountpoint'], ' · '.join(words), 'mount', str(Path(proc) / 'mounts') + ' + os.statvfs(' + row['mountpoint'] + ')', clock,
                              dict(mountpoint=row['mountpoint'], device=row['device'], fstype=row['fstype'], readonly=row['readonly'],
                                   free=free['free'] if free else None, total=free['total'] if free else None, holds=roles),
                              'OBSERVED' if free else 'PARTIAL', None if free else 'statvfs failed'))
    mount_rows, more = bounded(ordered(mount_rows), BOUND)
    partial = partial or more
    rows.extend(mount_rows)
    if table and not mount_rows:
        notes.append('No device-backed filesystems are mounted')
    state = 'UNAVAILABLE' if devices is None and not table and not rows else None
    return section('storage', clock, rows, state, sources, notes, partial, order='paths first, then disks and mounts naturally')


# ---------------------------------------------------------------- connections
def interface_kind(folder, name, kind_number):
    if name == 'lo' or kind_number == 772:
        return 'loopback'
    if (folder / 'wireless').exists() or (folder / 'phy80211').exists():
        return 'wireless'
    physical = (folder / 'device').exists()
    if kind_number == 1:
        return 'ethernet' if physical else 'virtual'
    if kind_number in (65534, 776, 778, 823):
        return 'tunnel'
    return 'other (type %s)' % kind_number


def interfaces(sys_root=SYS, clock=time.time):
    base = Path(sys_root) / 'class/net'
    try:
        names = sorted((p.name for p in base.iterdir()), key=natural)
    except FileNotFoundError:
        return None, 'not present: ' + str(base), False
    except OSError:
        return None, 'unreadable: ' + str(base), False
    rows = []
    for name in names:
        folder = base / name
        operstate = read_line(folder / 'operstate') or 'unknown'
        carrier = read_int(folder / 'carrier')  # EINVAL while the link is down: honestly None
        kind = interface_kind(folder, name, read_int(folder / 'type'))
        word = operstate if not (operstate == 'up' and carrier == 0) else 'up, no carrier'
        rows.append(item('connections:' + name, '%s · %s · %s' % (name, kind, word), 'interface', str(folder), clock,
                         dict(operstate=operstate, carrier=carrier, kind=kind, mtu=read_int(folder / 'mtu'), addresses='NOT_READ')))
    rows, more = bounded(rows, BOUND)
    return rows, None, more


def network_up(sys_root=SYS):
    """True when a non-loopback interface is up with a carrier, False when none is, None when /sys/class/net is unreadable."""
    rows, reason, _ = interfaces(sys_root, time.time)
    if rows is None:
        return None, []
    up = [row['id'].split(':', 1)[1] for row in rows
          if row['values']['kind'] != 'loopback' and row['values']['operstate'] == 'up' and row['values']['carrier'] != 0]
    return bool(up), up


def connections(sys_root=SYS, clock=time.time):
    rows, reason, more = interfaces(sys_root, clock)
    source = str(Path(sys_root) / 'class/net')
    if rows is None:
        return unavailable('connections', clock, reason, [source])
    up = [row['id'].split(':', 1)[1] for row in rows if row['values']['kind'] != 'loopback' and row['values']['operstate'] == 'up' and row['values']['carrier'] != 0]
    notes = ['Addresses are not read; only each interface\'s kind and link state.',
             ('Up with a link: ' + ', '.join(up)) if up else 'No interface other than loopback is up with a link.']
    return section('connections', clock, ordered(rows), None, [source], notes, more)


# ---------------------------------------------------------------- devices
def usb_devices(sys_root=SYS, clock=time.time):
    base = Path(sys_root) / 'bus/usb/devices'
    try:
        names = sorted((p.name for p in base.iterdir()), key=natural)
    except FileNotFoundError:
        return None, 'not present: ' + str(base), False
    except OSError:
        return None, 'unreadable: ' + str(base), False
    rows = []
    for name in names:
        folder = base / name
        if ':' in name or not (folder / 'idVendor').exists():
            continue  # interfaces and non-device entries
        vendor = read_line(folder / 'idVendor'); product_id = read_line(folder / 'idProduct')
        product = read_line(folder / 'product'); maker = read_line(folder / 'manufacturer')
        speed = read_line(folder / 'speed'); klass = read_line(folder / 'bDeviceClass')
        words = [product or ('USB device %s:%s' % (vendor, product_id))]
        if maker and (not product or maker.lower() not in product.lower()):
            words.insert(0, maker)
        if klass == '09':
            words.append('hub')
        if speed:
            words.append(speed + ' Mb/s')
        rows.append(item('devices:usb:' + name, ' · '.join(words), 'usb', str(folder), clock,
                         dict(bus=read_int(folder / 'busnum'), device=read_int(folder / 'devnum'), vendor_id=vendor, product_id=product_id,
                              product=product, manufacturer=maker, speed_mbps=speed, device_class=klass)))
    rows, more = bounded(rows, BOUND)
    return rows, None, more


def input_devices(proc=PROC, clock=time.time):
    path = Path(proc) / 'bus/input/devices'
    text, reason = read_text(path)
    if text is None:
        return None, reason, False
    rows = []; name = None; handlers = None; index = 0
    for line in text.splitlines() + ['']:
        if line.startswith('N: Name='):
            name = line.partition('=')[2].strip().strip('"')
        elif line.startswith('H: Handlers='):
            handlers = line.partition('=')[2].split()
        elif not line.strip() and name is not None:
            kinds = [k for k in ('kbd', 'mouse', 'js') if any(h.startswith(k) for h in (handlers or []))]
            words = name + (' · ' + ', '.join({'kbd': 'keyboard', 'mouse': 'pointer', 'js': 'joystick'}[k] for k in kinds) if kinds else '')
            rows.append(item('devices:input:%d' % index, words, 'input', str(path), clock, dict(name=clip(name), handlers=(handlers or [])[:8])))
            index += 1; name = None; handlers = None
    rows, more = bounded(rows, BOUND)
    return rows, None, more or len(text.encode('utf-8', 'replace')) >= READ_LIMIT


def displays(sys_root=SYS, clock=time.time):
    base = Path(sys_root) / 'class/drm'
    try:
        names = sorted((p.name for p in base.iterdir() if '-' in p.name and p.name.startswith('card')), key=natural)
    except FileNotFoundError:
        return None, 'not present: ' + str(base), False
    except OSError:
        return None, 'unreadable: ' + str(base), False
    rows = []
    for name in names:
        folder = base / name
        status = read_line(folder / 'status')
        if status is None:
            continue
        connector = name.split('-', 1)[1]
        mode = read_line(folder / 'modes') if status == 'connected' else None
        enabled = read_line(folder / 'enabled')
        words = [connector, status] + ([mode] if mode else []) + (['enabled'] if enabled == 'enabled' else [])
        rows.append(item('devices:display:' + name, ' · '.join(words), 'display', str(folder), clock,
                         dict(connector=connector, status=status, mode=mode, enabled=enabled, adapter=name.split('-', 1)[0])))
    rows, more = bounded(rows, DISPLAY_BOUND)
    return rows, None, more


def devices(proc=PROC, sys_root=SYS, clock=time.time):
    rows = []; notes = []; partial = False; readable = 0
    for title, reader, source in (('USB', lambda: usb_devices(sys_root, clock), str(Path(sys_root) / 'bus/usb/devices')),
                                  ('Input', lambda: input_devices(proc, clock), str(Path(proc) / 'bus/input/devices')),
                                  ('Display connectors', lambda: displays(sys_root, clock), str(Path(sys_root) / 'class/drm'))):
        found, reason, more = reader()
        if found is None:
            notes.append(title + ': ' + reason)
            continue
        readable += 1; partial = partial or more
        if not found:
            notes.append(title + ': none detected under ' + source)
        rows.extend(ordered(found))
    sources = [str(Path(sys_root) / 'bus/usb/devices'), str(Path(proc) / 'bus/input/devices'), str(Path(sys_root) / 'class/drm')]
    state = 'UNAVAILABLE' if not readable else None
    return section('devices', clock, rows, state, sources, notes, partial, order='USB, then input, then displays; each naturally')


# ---------------------------------------------------------------- installed tools
def tools(root=None, clock=time.time):
    from . import capability_catalog, locations
    root = Path(root) if root is not None else locations.PACKAGE
    rows = []
    for family in sorted(set(capability_catalog.NATIVE) | {'brain', 'python-wasi'}):
        command = capability_catalog.NATIVE.get(family)
        try:
            found = capability_catalog.native(root, family)
        except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError) as exc:
            found = {'state': 'UNAVAILABLE', 'reason': type(exc).__name__, 'command': command}
        path = None
        if command:
            try:
                path = shutil.which(command)
            except (OSError, ValueError, TypeError):
                path = None
        state = found.get('state')
        word = {'DETECTED': ('on PATH' if command else 'pinned archive verified'), 'MISSING': ('not found on PATH' if command else 'not installed'),
                'INVALID': 'invalid', 'INCOMPATIBLE': 'incompatible with this host', 'UNASSESSED': 'not assessed'}.get(state, 'unavailable')
        label = TOOL_NAMES.get(family, family) + ' · ' + word
        source = TOOL_SOURCES.get(family, 'PATH lookup for %s (shutil.which, nothing run)' % command)
        rows.append(item('tools:' + family, label, 'tool', source, clock,
                         dict(family=family, state=state, reason=found.get('reason'), command=command, path=path, version=found.get('version'),
                              licence=found.get('licence'), compatibility=found.get('compatibility'), measured='NOTHING_RUN'),
                         'OBSERVED' if state in ('DETECTED', 'MISSING') else 'PARTIAL', found.get('reason') if state not in ('DETECTED', 'MISSING') else None))
    return section('tools', clock, ordered(rows), None, ['PATH lookup (shutil.which)', 'capability_catalog.native'],
                   ['Presence only: no tool was started and no version was measured. Qualification is not assessed on this host.'])


# ---------------------------------------------------------------- the whole observation
def observe(section=None, program=None, workspace=None, proc=PROC, sys_root=SYS, clock=time.time):
    if section is not None and section not in SECTIONS:
        raise ValueError('Unknown machine section')
    builders = {'processor': lambda: processor(proc, clock), 'memory': lambda: memory(proc, sys_root, clock),
                'storage': lambda: storage(proc, sys_root, program, workspace, clock), 'connections': lambda: connections(sys_root, clock),
                'devices': lambda: devices(proc, sys_root, clock), 'tools': lambda: tools(program, clock)}
    wanted = (section,) if section else SECTIONS
    sections = []
    for name in wanted:
        try:
            sections.append(builders[name]())
        except (OSError, ValueError, TypeError, KeyError) as exc:  # a reader must never take the view down with it
            sections.append(unavailable(name, clock, 'reader failed: ' + type(exc).__name__))
    kernel_source = str(Path(proc) / 'sys/kernel')
    return dict(schema=SCHEMA, sampled_at=clock(), basis=BASIS,
                host=dict(kernel=read_line(Path(proc) / 'sys/kernel/osrelease'), hostname=read_line(Path(proc) / 'sys/kernel/hostname'), source=kernel_source),
                program_folder=str(program) if program is not None else None, workspace=str(workspace) if workspace is not None else None,
                sections=sections, sources=[proc, sys_root, 'os.statvfs'],
                limits=dict(items_per_list=BOUND, disks=DISK_BOUND, displays=DISPLAY_BOUND, partitions=PARTITION_BOUND, text=TEXT_LIMIT, bytes_read_per_file=READ_LIMIT),
                sort_rule='Comparable siblings in natural order of their label (digits by value, letters case-folded); descriptive lines keep their stated order.',
                distinct_from='hardware_nav: the ARC project hardware under Work / Project is design material, not this host.',
                model_calls=0, network_calls=0, native_invocations=0, subprocesses=0,
                notice='Observations of the computer Graphite runs on now. Nothing here qualifies the owner host, runs a tool or changes a setting.')


def dispatch(kernel, operation, args, principal):
    from . import locations
    return observe(section=args.get('section'), program=locations.PACKAGE, workspace=kernel.root)
