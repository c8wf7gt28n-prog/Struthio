"""This computer's network, observed without privileges, and the words and bytes of a packet capture (HATCH DESK D5).

The owner, 2026-11-06: "Instead of log notes, let's have network. And we should probably add a network traffic scanner or
packet sniffer capability that the agent can inspect." The owner tails it in Log's Network stream (workbench/log_qt.py, D3);
the agent reads it in an assignment (profile_network.py). docs/NETWORK_01.md is the account in words.

Four Kernel operations (FIELDS, SCOPES, dispatch below; the capture's runner and its state are in network_capture.py):

  network.observe        read     {filter?} -> {interfaces, connections, capture, observed_at, filter, rest, ...}
  network.capture.start  execute  {filter?, interface?, seconds?, packets?} -> {capture}      the owner's own action only
  network.capture.stop   execute  {discard?} -> {capture}
  network.capture.read   read     {after?, filter?, limit?} -> {packets, next, capture, ...}

Observing (this module) reads files only: /proc/net/dev (bytes, packets, errors and drops per interface), /sys/class/net/<if>
(operstate, flags, ifindex), /proc/net/tcp, tcp6, udp and udp6 (every socket: addresses and ports in hex, the state, the
owner's uid and the socket's inode), /proc/<pid>/fd and /proc/<pid>/comm (which process holds which socket, for the processes
this account may read), /proc/net/fib_trie and /proc/net/if_inet6 (this computer's own addresses), /etc/services (port names)
and /etc/passwd (user names). It makes no DNS lookup and no network request of any kind, and never calls the system's name
services (getservbyport, getpwuid), which may ask a server on some systems: the files are parsed here. tests prove it with an
audit hook. Receive and send rates come from two looks kept between calls (in bits per second, as the Log view shows them);
the first look has none, and nothing here ever sleeps.

A socket held by a process this account cannot read is reported with process 'another user' (its uid's name from
/etc/passwd), never guessed; a socket no process holds (TIME_WAIT) has no process. A captured packet's process (owner_index,
attribute) comes from its whole conversation, or for UDP and a TCP handshake from the socket bound to its port; when different
programs hold sockets under the same key (a forking server, SO_REUSEPORT listeners) it has none: never the first one found.

The filter grammar (parse_filter, the same words as log_qt.parse_filter): a host (an address, a network such as 10.0.0.0/24,
'localhost', after host or net; a name is accepted but never looked up, so it matches nothing and says so; an address with a
zone, fe80::1%eth0, is refused), a port (443, port 443, :443, 10.0.0.5:443; ASCII digits), a protocol (tcp udp icmp icmp6 arp
ip ip6 tcp6 udp6 sctp igmp raw raw6, each meaning what the capture filter means: ip is every IPv4 packet), a connection state
(listen established time_wait ...), and any other plain word, a process or user name in part (proc firefox, or firefox). Words
of one kind widen, kinds narrow. Anything else (and, or, not, quotes, brackets, semicolons, $, backticks, the capture tools' own
words such as src, dst, portrange or gateway, a number with dots that is no address) is refused with words. The same parts
become a capture filter (bpf) built only from canonical values, never from the typed text.

The capture parser (CaptureReader, decode) reads the capture tool's stream incrementally: pcapng (dumpcap) or classic pcap
(tcpdump -w -), little- or big-endian, micro- or nanosecond, and decodes headers only (Ethernet with VLAN tags, Linux cooked
v1 and v2, raw IP, BSD loopback; IPv4, IPv6 with its extension headers, ARP; TCP flags, UDP, SCTP, ICMP). Malformed input
raises MalformedCapture with words; nothing beyond the header fields is kept.
"""
from __future__ import annotations
import ipaddress
import os
import re
import stat as stat_module
import struct
import sys
import time

PROC = '/proc'
SYS = '/sys'
ETC = '/etc'
SCHEMA = 'graphite.network/1'
CONNECTION_LIMIT = 500        # connections an observe returns at most (the rest are counted)
INTERFACE_LIMIT = 64
READ_LIMIT = 8 * 1024 * 1024  # bytes read of one /proc or /etc file at most
PROCESS_LIMIT = 8192          # process folders looked at for socket owners at most
TEXT_LIMIT = 120
FILTER_LIMIT = 300            # characters of a filter
TOKEN_LIMIT = 32              # words of a filter

TCP_STATES = {1: 'ESTABLISHED', 2: 'SYN_SENT', 3: 'SYN_RECV', 4: 'FIN_WAIT1', 5: 'FIN_WAIT2', 6: 'TIME_WAIT', 7: 'CLOSE',
              8: 'CLOSE_WAIT', 9: 'LAST_ACK', 10: 'LISTEN', 11: 'CLOSING', 12: 'NEW_SYN_RECV'}
UDP_STATES = {1: 'ESTABLISHED', 7: 'UNCONN'}  # a UDP socket the kernel keeps as TCP_CLOSE is an unconnected (bound) one
STATE_ORDER = ('ESTABLISHED', 'SYN_SENT', 'SYN_RECV', 'FIN_WAIT1', 'FIN_WAIT2', 'CLOSE_WAIT', 'LAST_ACK', 'CLOSING', 'LISTEN',
               'UNCONN', 'NEW_SYN_RECV', 'CLOSE', 'TIME_WAIT')
SOCKET_FILES = (('tcp', 'net/tcp'), ('tcp6', 'net/tcp6'), ('udp', 'net/udp'), ('udp6', 'net/udp6'))
ANOTHER_USER = 'another user'

PROTOCOLS = ('tcp', 'udp', 'icmp', 'icmp6', 'arp', 'ip', 'ip6', 'tcp6', 'udp6', 'sctp', 'igmp', 'raw', 'raw6')
STATES = ('listen', 'established', 'syn_sent', 'syn_recv', 'fin_wait1', 'fin_wait2', 'time_wait', 'close', 'close_wait',
          'last_ack', 'closing', 'unconn', 'new_syn_recv')
KEYWORDS = {'host': 'hosts', 'net': 'hosts', 'port': 'ports', 'proto': 'protocols', 'protocol': 'protocols', 'proc': 'words',
            'process': 'words', 'user': 'words', 'state': 'states'}
OPERATORS = ('and', 'or', 'not', '&&', '||', '!')
# Words of the capture tools' own filter language that are not Graphite's: alone they are refused with words, never read as a
# process name (which would drop them from the capture filter and capture more than was typed). After proc, process or user a
# word is a name whatever it is (proc less).
EITHER_END = ('src', 'dst')
CAPTURE_WORDS = ('portrange', 'gateway', 'ether', 'broadcast', 'multicast', 'less', 'greater', 'len', 'vlan', 'mpls', 'inbound',
                 'outbound', 'rarp', 'protochain', 'ifname', 'wlan', 'fddi', 'pppoed', 'pppoes', 'geneve')
OTHER_PROTOCOLS = ('gre', 'esp', 'ah', 'ospf', 'pim', 'vrrp', 'igrp')   # named in packets, not selected by Graphite's filter
WORD = re.compile(r'[A-Za-z0-9][A-Za-z0-9._+@-]{0,63}')
NAME = re.compile(r'[A-Za-z0-9-]{1,63}(\.[A-Za-z0-9-]{1,63})+')
BPF_PROTOCOLS = {'tcp': 'tcp', 'udp': 'udp', 'icmp': 'icmp', 'icmp6': 'icmp6', 'arp': 'arp', 'ip': 'ip', 'ip6': 'ip6',
                 'tcp6': 'ip6 and tcp', 'udp6': 'ip6 and udp', 'sctp': 'sctp', 'igmp': 'igmp'}
BPF_SAFE = re.compile(r'[a-z0-9 .:/()]*')
CANONICAL_HOST = re.compile(r'[0-9a-f.:/]{2,49}')   # what ipaddress writes for an address or a network: nothing else is a host
NO_NAMES = 'names are not looked up (Graphite makes no DNS request): %s; give its address'
NO_ZONE = 'not a host: %s (an address with a zone after %% is not taken: give the address alone)'

FIELDS_FILTER = {'type': 'string', 'maxLength': FILTER_LIMIT}
FIELDS = {
    'network.observe': ({'filter': FIELDS_FILTER}, []),
    'network.capture.start': ({'filter': FIELDS_FILTER,
                               'interface': {'type': 'string', 'pattern': '^[A-Za-z0-9_][A-Za-z0-9_.:@-]{0,14}$', 'maxLength': 15},
                               'seconds': {'type': 'integer', 'minimum': 5, 'maximum': 480},
                               'packets': {'type': 'integer', 'minimum': 1, 'maximum': 100000}}, []),
    'network.capture.stop': ({'discard': {'type': 'boolean'}}, []),
    'network.capture.read': ({'after': {'type': 'integer', 'minimum': 0}, 'filter': FIELDS_FILTER,
                              'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000}}, []),
}
SCOPES = {'network.observe': 'read', 'network.capture.start': 'execute', 'network.capture.stop': 'execute',
          'network.capture.read': 'read'}
OBSERVERS = ('network.observe', 'network.capture.read')  # polled by the Log view; reading is not an event


# ---------------------------------------------------------------------------------------------------------------- small readers

def read_text(path, limit=READ_LIMIT):
    """(text, None) or (None, reason). Never raises."""
    try:
        with open(path, 'rb') as stream:
            return stream.read(limit).decode('utf-8', 'replace'), None
    except FileNotFoundError:
        return None, 'not present: ' + str(path)
    except OSError as exc:
        return None, 'unreadable: %s (%s)' % (path, type(exc).__name__)


def read_line(path):
    text, _ = read_text(path, 4096)
    return text.splitlines()[0].strip() if text and text.splitlines() else None


def clip(value, limit=TEXT_LIMIT):
    return ' '.join(str(value).split())[:limit]


# ---------------------------------------------------------------------------------------------------------------- interfaces

def parse_dev(text):
    """/proc/net/dev as rows: name, rx/tx bytes, packets, errors and drops."""
    rows = []
    for line in (text or '').splitlines():
        if ':' not in line: continue
        name, _, numbers = line.partition(':')
        name = name.strip(); values = numbers.split()
        if not name or len(values) < 16: continue
        try: v = [int(x) for x in values[:16]]
        except ValueError: continue
        rows.append({'name': name, 'rx_bytes': v[0], 'rx_packets': v[1], 'rx_errors': v[2], 'rx_drops': v[3],
                     'tx_bytes': v[8], 'tx_packets': v[9], 'tx_errors': v[10], 'tx_drops': v[11]})
    return rows


def interface_state(name, sys_root=SYS):
    """(up, operstate, ifindex): up when the kernel says 'up', or 'unknown' with the IFF_UP flag (the loopback reads so)."""
    folder = os.path.join(sys_root, 'class', 'net', name)
    oper = read_line(os.path.join(folder, 'operstate'))
    flags = read_line(os.path.join(folder, 'flags'))
    index = read_line(os.path.join(folder, 'ifindex'))
    try: flag_up = bool(int(flags, 0) & 1) if flags else None
    except ValueError: flag_up = None
    up = True if oper == 'up' else (bool(flag_up) if oper in ('unknown', None) and flag_up is not None else (False if oper else None))
    try: index = int(index) if index else None
    except ValueError: index = None
    return up, oper, index


def interface_indexes(sys_root=SYS):
    """{ifindex: name} from /sys/class/net (the capture's Linux cooked v2 header carries the index)."""
    out = {}
    try: names = sorted(os.listdir(os.path.join(sys_root, 'class', 'net')))
    except OSError: return out
    for name in names[:INTERFACE_LIMIT * 4]:
        _, _, index = interface_state(name, sys_root)
        if index is not None: out[index] = name
    return out


_SAMPLES = {}  # {key: {interface: (time, rx_bytes, tx_bytes)}}: the previous look, kept between calls (never a sleep)


def rates(rows, now, previous):
    """Each row with rx_bps and tx_bps (bits per second) from the previous look; None on the first look, after a counter reset
    or when no time passed. Returns (rows, the look to keep)."""
    keep = {}; out = []
    for row in rows:
        before = (previous or {}).get(row['name']); rx = tx = None
        if before is not None:
            seconds = now - before[0]; d_rx = row['rx_bytes'] - before[1]; d_tx = row['tx_bytes'] - before[2]
            if seconds > 0 and d_rx >= 0 and d_tx >= 0:
                rx = round(d_rx * 8 / seconds, 1); tx = round(d_tx * 8 / seconds, 1)
        keep[row['name']] = (now, row['rx_bytes'], row['tx_bytes'])
        out.append(dict(row, rx_bps=rx, tx_bps=tx))
    return out, keep


def interfaces(proc_root=PROC, sys_root=SYS, now=None, memory=None):
    """The interfaces as the contract gives them ({name, rx_bps, tx_bps, rx_bytes, tx_bytes, up} and the counters), and why
    when /proc/net/dev cannot be read. memory is the dict that keeps the previous look (default: this process's)."""
    text, reason = read_text(os.path.join(proc_root, 'net', 'dev'))
    if text is None: return [], reason
    now = time.time() if now is None else now
    store = _SAMPLES if memory is None else memory; key = (proc_root, sys_root)
    rows, keep = rates(parse_dev(text)[:INTERFACE_LIMIT], now, store.get(key))
    store[key] = keep
    for row in rows:
        up, oper, index = interface_state(row['name'], sys_root)
        row.update(up=up, state=oper, index=index)
    return rows, None


# ---------------------------------------------------------------------------------------------------------------- sockets

def decode_address(text, byteorder=None):
    """A /proc/net address in hex as people write it: 0100007F -> 127.0.0.1; 32 hex digits -> IPv6, an IPv4-mapped one
    (::ffff:1.2.3.4) shown plainly as 1.2.3.4. The kernel writes each 32-bit word in the host's byte order."""
    order = byteorder or sys.byteorder; raw = bytes.fromhex(text)
    if len(raw) == 4:
        return str(ipaddress.IPv4Address(raw[::-1] if order == 'little' else raw))
    if len(raw) == 16:
        words = b''.join((raw[i:i + 4][::-1] if order == 'little' else raw[i:i + 4]) for i in range(0, 16, 4))
        address = ipaddress.IPv6Address(words)
        return str(address.ipv4_mapped) if address.ipv4_mapped is not None else str(address)
    raise ValueError('not an address: ' + text)


def parse_sockets(text, proto, byteorder=None):
    """One /proc/net/{tcp,tcp6,udp,udp6} file as rows: proto, local, lport, remote, rport, state, uid, inode. A line that does not
    read is skipped (counted by the caller through the difference)."""
    rows = []; states = TCP_STATES if proto.startswith('tcp') else UDP_STATES
    for line in (text or '').splitlines()[1:]:
        parts = line.split()
        if len(parts) < 10: continue
        try:
            local, lport = parts[1].split(':'); remote, rport = parts[2].split(':')
            state = int(parts[3], 16)
            rows.append({'proto': proto, 'local': decode_address(local, byteorder), 'lport': int(lport, 16),
                         'remote': decode_address(remote, byteorder), 'rport': int(rport, 16),
                         'state': states.get(state, 'STATE_%02X' % state), 'uid': int(parts[7]), 'inode': int(parts[9])})
        except (ValueError, IndexError):
            continue
    return rows


def socket_owners(inodes, proc_root=PROC, limit=PROCESS_LIMIT):
    """{inode: (pid, process name)} for the wanted socket inodes, found in /proc/<pid>/fd of the processes this account may read,
    and how many process folders could not be read. Stops once every inode is found."""
    wanted = {i for i in inodes if i}; found = {}; unreadable = 0
    if not wanted: return found, unreadable
    try: pids = sorted((int(n) for n in os.listdir(proc_root) if n.isdigit()))[:limit]
    except OSError: return found, unreadable
    for pid in pids:
        folder = os.path.join(proc_root, str(pid), 'fd')
        try: fds = os.listdir(folder)
        except OSError: unreadable += 1; continue
        name = None
        for fd in fds:
            try: target = os.readlink(os.path.join(folder, fd))
            except OSError: continue
            if not target.startswith('socket:['): continue
            try: inode = int(target[8:-1])
            except ValueError: continue
            if inode in wanted and inode not in found:
                if name is None: name = read_line(os.path.join(proc_root, str(pid), 'comm')) or str(pid)
                found[inode] = (pid, clip(name, 64))
        if len(found) == len(wanted): break
    return found, unreadable


def parse_passwd(text):
    """{uid: login name} from /etc/passwd's text (parsed here: the system's name service may ask a server)."""
    out = {}
    for line in (text or '').splitlines():
        parts = line.split(':')
        if len(parts) >= 3 and parts[2].isdigit(): out.setdefault(int(parts[2]), parts[0])
    return out


def parse_services(text):
    """{(port, 'tcp'|'udp'): name} from /etc/services' text (parsed here, never getservbyport)."""
    out = {}
    for line in (text or '').splitlines():
        line = line.split('#', 1)[0].split()
        if len(line) < 2 or '/' not in line[1]: continue
        port, _, proto = line[1].partition('/')
        if port.isdigit() and proto in ('tcp', 'udp', 'sctp'): out.setdefault((int(port), proto), line[0])
    return out


def local_addresses(proc_root=PROC):
    """This computer's own addresses: /proc/net/fib_trie's '/32 host LOCAL' entries and /proc/net/if_inet6. Files only."""
    out = set(); text, _ = read_text(os.path.join(proc_root, 'net', 'fib_trie'), 1024 * 1024); last = None
    for line in (text or '').splitlines():
        stripped = line.strip()
        if stripped.startswith('|--'): last = stripped[3:].strip()
        elif '/32 host LOCAL' in stripped and last: out.add(last)
    text, _ = read_text(os.path.join(proc_root, 'net', 'if_inet6'), 256 * 1024)
    for line in (text or '').splitlines():
        parts = line.split()
        if parts and len(parts[0]) == 32:
            try: out.add(str(ipaddress.IPv6Address(bytes.fromhex(parts[0]))))
            except ValueError: pass
    return out


def connections(proc_root=PROC, etc=ETC, byteorder=None, uid=None):
    """Every socket of this computer's network namespace as the contract's connection rows ({proto, local, lport, remote, rport,
    state, pid?, process?, user?} and the ports' names), and notes for what could not be read."""
    notes = []; rows = []
    for proto, name in SOCKET_FILES:
        text, reason = read_text(os.path.join(proc_root, name))
        if text is None:
            if not reason.startswith('not present'): notes.append(reason)   # tcp6/udp6 are absent where IPv6 is off
            continue
        rows += parse_sockets(text, proto, byteorder)
    owners, unreadable = socket_owners([r['inode'] for r in rows], proc_root)
    users = parse_passwd(read_text(os.path.join(etc, 'passwd'), 1024 * 1024)[0])
    services = parse_services(read_text(os.path.join(etc, 'services'), 1024 * 1024)[0])
    me = os.geteuid() if uid is None else uid
    out = []
    for r in rows:
        row = {k: r[k] for k in ('proto', 'local', 'lport', 'remote', 'rport', 'state')}
        family = r['proto'].rstrip('6')
        for side, port in (('lservice', r['lport']), ('rservice', r['rport'])):
            if port and (port, family) in services: row[side] = services[(port, family)]
        if r['inode'] in owners:
            row['pid'], row['process'] = owners[r['inode']]; row['user'] = users.get(r['uid'], str(r['uid']))
        elif r['inode']:
            row['user'] = users.get(r['uid'], str(r['uid']))
            if r['uid'] != me: row['process'] = ANOTHER_USER   # its process folder is not this account's to read: never guessed
        out.append(row)
    if unreadable: notes.append('%d processes belong to another user; their sockets say "%s"' % (unreadable, ANOTHER_USER))
    out.sort(key=lambda c: (STATE_ORDER.index(c['state']) if c['state'] in STATE_ORDER else len(STATE_ORDER),
                            str(c.get('process') or '~'), c['proto'], c['remote'], c['rport'], c['local'], c['lport']))
    return out, notes


UNSPECIFIED = ('0.0.0.0', '::', None, '')
AMBIGUOUS = ('', None)   # more than one program holds sockets under one key: the packet's program is not known, never guessed


def _hold(table, key, owner):
    """Keep one key's owner: the same program and process again changes nothing; the same program in another process keeps the
    program's name without a pid (which process is not known); another program makes the key AMBIGUOUS."""
    before = table.get(key)
    if before is None or before == owner: table[key] = owner
    elif before is AMBIGUOUS or before[0] != owner[0]: table[key] = AMBIGUOUS
    else: table[key] = (owner[0], None)


def owner_index(rows):
    """The connection rows as an index for naming a packet's process, at three levels, each kept apart:
      pair   {(proto, local, lport, remote, rport): owner}  a connected socket, by its whole conversation;
      exact  {(proto, local, lport): owner}                 an unconnected socket bound to one of this computer's addresses;
      wild   {(proto, lport): owner}                        an unconnected socket bound to every address (0.0.0.0 or ::).
    owner is (process, pid), (process, None) when one program holds the key in several processes, or AMBIGUOUS when different
    programs do (a forking server's children, SO_REUSEPORT listeners such as mDNS on udp 5353): never the first one found.
    tcp6 and udp6 sockets count as tcp and udp (an IPv6 socket may also take IPv4, whose addresses read plainly)."""
    index = {'pair': {}, 'exact': {}, 'wild': {}}
    for row in rows or []:
        name = row.get('process'); proto = str(row.get('proto') or '').rstrip('6')
        if not name or proto not in ('tcp', 'udp') or not row.get('lport'): continue
        owner = (name, row.get('pid')); local = row.get('local')
        if row.get('remote') not in UNSPECIFIED or row.get('rport'):
            _hold(index['pair'], (proto, local, row['lport'], row.get('remote'), row.get('rport')), owner)
        elif local in UNSPECIFIED: _hold(index['wild'], (proto, row['lport']), owner)
        else: _hold(index['exact'], (proto, local, row['lport']), owner)
    return index


def _side(index, proto, here, there, own, handshake):
    """The owner of the socket at one end (here) of a packet: its conversation first; then, for UDP or a TCP handshake (a
    connection that is not one yet belongs to its listener), the socket bound to here's address, then to every address when
    here is this computer's. An AMBIGUOUS level ends the search for this end: a less exact level would be a guess."""
    levels = [index['pair'].get((proto, here[0], here[1], there[0], there[1]))]
    if proto == 'udp' or handshake:
        levels.append(index['exact'].get((proto, here[0], here[1])))
        if own: levels.append(index['wild'].get((proto, here[1])))
    for hit in levels:
        if hit is AMBIGUOUS: return None
        if hit is not None: return hit
    return None


def attribute(packet, index, local=()):
    """(process, pid) of the socket on this computer's side of a TCP or UDP packet when the connection table knows it, the
    sender's first when both ends are this computer's; (process, None) when one program holds it in several processes; None
    otherwise, and whenever different programs could hold it (never guessed)."""
    proto = str(packet.get('proto') or '').rstrip('6')
    if proto not in ('tcp', 'udp') or not isinstance(index, dict): return None
    handshake = 'S' in str(packet.get('flags') or '')
    src = (packet.get('src'), packet.get('sport')); dst = (packet.get('dst'), packet.get('dport'))
    for here, there in ((src, dst), (dst, src)):
        address = here[0]; own = address in local or str(address).startswith('127.') or address == '::1'
        hit = _side(index, proto, here, there, own, handshake)
        if hit is not None: return hit
    return None


# ---------------------------------------------------------------------------------------------------------------- the filter

def _host(token):
    """(canonical host, is_name) or (None, False): an address, a network (CIDR), 'localhost', or a name with a dot. ASCII only;
    an address with a zone (fe80::1%eth0) is not one; the canonical form is checked, so a host is always safe to write."""
    t = token.strip('[]')
    if not t.isascii() or '%' in t: return None, False
    try:
        value = str(ipaddress.ip_network(t, strict=False)) if '/' in t else str(ipaddress.ip_address(t))
        return (value, False) if CANONICAL_HOST.fullmatch(value) else (None, False)
    except ValueError: pass
    if t.lower() == 'localhost': return 'localhost', False
    if NAME.fullmatch(t) and not re.fullmatch(r'[0-9.]+', t): return t.lower(), True
    return None, False


def _port(token):
    t = token[1:] if token.startswith(':') else token
    if re.fullmatch(r'[0-9]{1,5}', t) and 1 <= int(t) <= 65535: return int(t)
    return None


def parse_filter(text):
    """The owner's words as {hosts, names, ports, protocols, states, words, errors, text}. See the module note. Never raises;
    what it does not understand is in errors, word for word."""
    out = dict(hosts=[], names=[], ports=[], protocols=[], states=[], words=[], errors=[], text=' '.join(str(text or '').split()))
    if len(out['text']) > FILTER_LIMIT:
        out['errors'].append('the filter is longer than %d characters' % FILTER_LIMIT); out['text'] = out['text'][:FILTER_LIMIT]
    tokens = out['text'].split()
    if len(tokens) > TOKEN_LIMIT:
        out['errors'].append('the filter has more than %d words' % TOKEN_LIMIT); tokens = tokens[:TOKEN_LIMIT]

    def add(kind, value):
        if value not in out[kind]: out[kind].append(value)

    def host(value):
        if '%' in value and _host(value.split('%', 1)[0])[0] is not None:
            out['errors'].append(NO_ZONE % clip(value, 60)); return True
        found, is_name = _host(value)
        if found is None: return False
        if found == 'localhost': add('hosts', '127.0.0.1'); add('hosts', '::1')
        elif is_name: add('names', found); out['errors'].append(NO_NAMES % found)
        else: add('hosts', found)
        return True

    i = 0
    while i < len(tokens):
        token = tokens[i]; low = token.lower(); i += 1
        if low in KEYWORDS:
            if i >= len(tokens): out['errors'].append('“%s” needs a word after it' % clip(token, 40)); break
            kind = KEYWORDS[low]; value = tokens[i]; i += 1; vlow = value.lower()
            if kind == 'hosts':
                if not host(value): out['errors'].append('not a host: ' + clip(value, 60))
            elif kind == 'ports':
                port = _port(value)
                if port is None: out['errors'].append('not a port (1 to 65535): ' + clip(value, 60))
                else: add('ports', port)
            elif kind == 'protocols':
                if vlow in PROTOCOLS: add('protocols', vlow)
                else: out['errors'].append('not a protocol Graphite knows: ' + clip(value, 60))
            elif kind == 'states':
                if vlow in STATES: add('states', vlow)
                else: out['errors'].append('not a connection state: ' + clip(value, 60))
            elif WORD.fullmatch(value): add('words', vlow)
            else: out['errors'].append('not a name Graphite accepts: ' + clip(value, 60))
            continue
        if low in OPERATORS:
            out['errors'].append('“%s” is not part of the filter: words of one kind widen, of different kinds narrow' % clip(token, 10)); continue
        if low in EITHER_END:
            out['errors'].append('“%s” is not part of the filter: a host or a port matches either end of a conversation' % low); continue
        if low in CAPTURE_WORDS:
            out['errors'].append('“%s” is a capture-filter word Graphite’s filter does not take: it takes hosts, ports, protocols, '
                                 'states and names (proc %s for a program of that name)' % (low, low)); continue
        if low in OTHER_PROTOCOLS:
            out['errors'].append('“%s” is a protocol Graphite’s filter does not select: it selects %s' % (low, ' '.join(BPF_PROTOCOLS))); continue
        port = _port(token)
        if port is not None: add('ports', port); continue
        if low in PROTOCOLS: add('protocols', low); continue
        if low in STATES: add('states', low); continue
        pair = re.fullmatch(r'\[([0-9A-Fa-f:.]+)\]:([0-9]{1,5})|([0-9.]+|[A-Za-z0-9.-]+):([0-9]{1,5})', token)
        if pair:
            address = pair.group(1) or pair.group(3); number = _port(pair.group(2) or pair.group(4))
            if number is not None and _host(address)[0] is not None:
                host(address); add('ports', number); continue
        if host(token): continue
        if re.fullmatch(r'[0-9]+', token): out['errors'].append('not a port (1 to 65535): ' + clip(token, 60)); continue
        if re.fullmatch(r'[0-9.]+', token): out['errors'].append('not an address: ' + clip(token, 60)); continue
        if WORD.fullmatch(token): add('words', low); continue
        out['errors'].append('not part of the filter: ' + clip(token, 60))
    return out


def _host_match(wanted, value):
    if value in (None, ''): return False
    value = str(value).strip('[]').lower()
    if '/' in wanted:
        try: return ipaddress.ip_address(value) in ipaddress.ip_network(wanted, strict=False)
        except ValueError: return False
    try: return ipaddress.ip_address(value) == ipaddress.ip_address(wanted)
    except ValueError: return value == wanted


def family(entry, packet=False):
    """4 or 6: the IP version an entry travels in, as a capture sees it (its addresses; an IPv4-mapped socket's read plainly as
    IPv4), or None (ARP, a link without IP, a header too short to say)."""
    proto = str(entry.get('proto') or '').lower()
    if proto == 'arp': return None
    if proto in ('ip', 'ip6'): return 4 if proto == 'ip' else 6
    for key in (('src', 'dst') if packet else ('local', 'remote')):
        try: return ipaddress.ip_address(str(entry.get(key) or '').strip('[]')).version
        except ValueError: continue
    return None


def _proto_match(wanted, entry, packet=False):
    """A protocol word as the capture filter means it (BPF_PROTOCOLS), for packets and connections alike: ip and ip6 are every
    IPv4 or IPv6 packet (ARP is neither); tcp and udp either version; tcp6 and udp6 TCP and UDP over IPv6; icmp is ICMP for
    IPv4 and icmp6 for IPv6; the others by their own name."""
    proto = str(entry.get('proto') or '').lower(); base = proto[:-1] if proto in ('tcp6', 'udp6') else proto
    if wanted in ('ip', 'ip6'): return family(entry, packet) == (4 if wanted == 'ip' else 6)
    if wanted in ('tcp', 'udp'): return base == wanted
    if wanted in ('tcp6', 'udp6'): return base == wanted[:-1] and family(entry, packet) == 6
    return proto == wanted


def matches(entry, parts, packet=False):
    """Whether a connection (or, with packet=True, a packet) passes the parsed filter: any word of a kind, every kind present.
    A name (never looked up) matches no address. A packet has no connection state, so states do not narrow packets."""
    if not parts: return True
    if packet: hosts, ports = (entry.get('src'), entry.get('dst')), (entry.get('sport'), entry.get('dport'))
    else: hosts, ports = (entry.get('local'), entry.get('remote')), (entry.get('lport'), entry.get('rport'))
    if (parts.get('hosts') or parts.get('names')) and not any(_host_match(h, v) for h in parts.get('hosts', []) for v in hosts): return False
    if parts.get('ports') and not any(p == v for p in parts['ports'] for v in ports): return False
    if parts.get('protocols') and not any(_proto_match(p, entry, packet) for p in parts['protocols']): return False
    if parts.get('states') and not packet and str(entry.get('state') or '').lower() not in parts['states']: return False
    if parts.get('words'):
        said = ' '.join(str(entry.get(k) or '') for k in ('process', 'user', 'state', 'iface', 'flags', 'lservice', 'rservice')).lower()
        if not any(w in said for w in parts['words']): return False
    return True


def bpf(parts):
    """(capture-filter expression, errors): the hosts, ports and protocols as a capture filter for dumpcap or tcpdump, built only
    from canonical values (addresses through ipaddress, ports as integers, protocols from a fixed table). Process words and states
    are applied when the packets are read. A name is refused: compiling it would make the capture tool look it up."""
    errors = list(parts.get('errors') or [])
    groups = []
    if parts.get('hosts'):
        words = []
        for h in parts['hosts']:
            if '/' in h: words.append('net ' + str(ipaddress.ip_network(h, strict=False)))
            else: words.append('host ' + str(ipaddress.ip_address(h)))
        groups.append(words)
    if parts.get('ports'): groups.append(['port %d' % int(p) for p in parts['ports'] if 1 <= int(p) <= 65535])
    protocols = []
    for p in parts.get('protocols') or []:
        if p in BPF_PROTOCOLS: protocols.append(BPF_PROTOCOLS[p])
        else: errors.append('“%s” is a kind of socket, not a packet protocol a capture can select' % p)
    if protocols: groups.append(protocols)
    groups = [g for g in groups if g]

    def group(g):  # words of one kind widen (or); a word that is itself two words (ip6 and tcp) keeps its brackets among others
        if len(g) == 1: return g[0]
        inner = ' or '.join('(%s)' % w if ' and ' in w else w for w in g)
        return '(%s)' % inner if len(groups) > 1 else inner
    expression = ' and '.join(group(g) for g in groups)
    if not BPF_SAFE.fullmatch(expression): raise ValueError('the capture filter could not be written safely')  # never: built from canonical values
    return expression, list(dict.fromkeys(errors))


# ---------------------------------------------------------------------------------------------------------------- availability

CAP_NET_ADMIN = 12
CAP_NET_RAW = 13
TOOLS = ('dumpcap', 'tcpdump')
SEARCH = ('/usr/bin', '/usr/sbin', '/bin', '/sbin', '/usr/local/bin', '/usr/local/sbin')
INSTALL = ('as the administrator, apt install wireshark-common, and answer Yes when it asks whether non-superusers should be '
           'able to capture packets')
RECONFIGURE = 'as the administrator, dpkg-reconfigure wireshark-common, and answer Yes: non-superusers may capture packets'
RELOG = 'log out and in again, so the session carries the wireshark group'
NEVER = ('Graphite only explains: it never runs these commands, never asks for the administrator’s password and never changes '
         'the system’s permissions.')


def join_step(login):
    """The step that puts this account in the wireshark group, with the account's own login name."""
    return 'as the administrator, usermod -aG wireshark %s' % (login if login and NAME_SAFE.fullmatch(login) else '<your login>')


NAME_SAFE = re.compile(r'[a-z_][a-z0-9_.-]{0,31}\$?')


def debian_steps(login=None):
    """How the owner enables capture without root on Debian, in order (Debian's wireshark-common: dumpcap with file
    capabilities for the members of the wireshark group)."""
    return [INSTALL, join_step(login), RELOG]


DEBIAN_STEPS = tuple(debian_steps())


def file_capabilities(raw):
    """The permitted capability bits of a security.capability attribute (vfs_cap_data v1, v2 or v3), or 0."""
    if not raw or len(raw) < 8: return 0
    magic = struct.unpack_from('<I', raw, 0)[0]; revision = magic & 0xFF000000
    low = struct.unpack_from('<I', raw, 4)[0]
    high = struct.unpack_from('<I', raw, 12)[0] if revision in (0x02000000, 0x03000000) and len(raw) >= 16 else 0
    return low | (high << 32)


def find_tool(name, path_text=None, exists=os.path.exists):
    """The first place the tool is installed (the PATH, then the usual system folders), whether or not this account may run it."""
    folders = [p for p in (path_text if path_text is not None else os.environ.get('PATH', '')).split(os.pathsep) if p] + list(SEARCH)
    for folder in dict.fromkeys(folders):
        candidate = os.path.join(folder, name)
        if exists(candidate): return candidate
    return None


def group_members(text, name):
    """(gid, members) of a group in /etc/group's text, or (None, ())."""
    for line in (text or '').splitlines():
        parts = line.split(':')
        if len(parts) >= 4 and parts[0] == name:
            try: return int(parts[2]), tuple(m for m in parts[3].split(',') if m)
            except ValueError: return None, ()
    return None, ()


def probe(path_text=None, euid=None, groups=None, login=None, etc=ETC, exists=os.path.exists, access=os.access,
          getxattr=None, stat=os.stat):
    """Whether this session can capture, without starting anything: {state 'AVAILABLE'|'UNAVAILABLE', tool, path, reason,
    enable [steps], signature}. dumpcap is preferred (Debian's wireshark-common: non-superuser capture through file capabilities
    for the wireshark group), then tcpdump (when the owner gave it capture capabilities), or either when Graphite runs as root.
    The reason is in plain words with how the owner can enable capture on Debian."""
    euid = os.geteuid() if euid is None else euid
    groups = set(os.getgroups() if groups is None else groups)
    getxattr = getxattr or (lambda p: os.getxattr(p, 'security.capability'))
    if login is None:   # the login name from /etc/passwd's text, never the system's name service
        login = parse_passwd(read_text(os.path.join(etc, 'passwd'), 1024 * 1024)[0]).get(euid) or os.environ.get('USER') or 'you'
    found = {name: find_tool(name, path_text, exists) for name in TOOLS}
    steps_all = debian_steps(login); join = join_step(login)
    if not any(found.values()):
        return {'state': 'UNAVAILABLE', 'tool': None, 'path': None, 'enable': steps_all,
                'reason': 'No capture tool is installed (Graphite captures through dumpcap or tcpdump). To enable capture on Debian: '
                          + '; then '.join(steps_all) + '. ' + NEVER, 'signature': None}
    verdicts = []
    for name in TOOLS:
        path = found[name]
        if not path: continue
        try: info = stat(path)
        except OSError as exc: verdicts.append((name, path, False, '%s is installed but could not be examined (%s).' % (name, type(exc).__name__), [], None)); continue
        signature = '%s:%d:%d:%o' % (path, int(info.st_mtime), info.st_size, info.st_mode)
        try: bits = file_capabilities(getxattr(path))
        except OSError: bits = 0
        capable = bool(bits & (1 << CAP_NET_RAW)) or (bool(info.st_mode & stat_module.S_ISUID) and info.st_uid == 0) or euid == 0
        runnable = access(path, os.X_OK)
        if runnable and capable:
            verdicts.append((name, path, True, '', [], signature)); continue
        if name == 'dumpcap':
            gid, members = group_members(read_text(os.path.join(etc, 'group'), 1024 * 1024)[0], 'wireshark')
            if not runnable and gid is not None and login in members and gid not in groups:
                reason = ('dumpcap is installed and you are in the wireshark group, but this session started before you joined it: '
                          + RELOG + '.')
                steps = [RELOG]
            elif not runnable:
                reason = 'dumpcap is installed, but this account may not run it: ' + join + '; then ' + RELOG + '.'
                steps = [join, RELOG]
            else:
                reason = ('dumpcap is installed without permission to capture (non-superuser capture was not allowed when it was installed): '
                          + RECONFIGURE + '; then ' + join + '; then ' + RELOG + '.')
                steps = [RECONFIGURE, join, RELOG]
        else:
            reason = ('tcpdump is installed but may capture only as the administrator, and Graphite never runs as the administrator. '
                      'For capture without the administrator, install wireshark-common (' + '; then '.join(steps_all) + '), or give tcpdump '
                      'capture capabilities yourself (as the administrator, setcap cap_net_raw,cap_net_admin=eip ' + path + ').')
            steps = list(steps_all)
        verdicts.append((name, path, False, reason, steps, signature))
    usable = [v for v in verdicts if v[2]]
    if usable:
        name, path, _, _, _, signature = usable[0]
        return {'state': 'AVAILABLE', 'tool': name, 'path': path, 'reason': '', 'enable': [], 'signature': signature}
    name, path, _, reason, steps, signature = verdicts[0]
    return {'state': 'UNAVAILABLE', 'tool': name, 'path': path, 'reason': reason + ' ' + NEVER, 'enable': steps, 'signature': signature}


# ---------------------------------------------------------------------------------------------------------------- capture bytes

class MalformedCapture(ValueError):
    """The capture tool's stream is not pcap or pcapng, or a block of it is damaged."""


PCAPNG_SHB = 0x0A0D0D0A
BYTE_ORDER_MAGIC = 0x1A2B3C4D
PCAP_MAGICS = {b'\xd4\xc3\xb2\xa1': ('<', 1e-6), b'\xa1\xb2\xc3\xd4': ('>', 1e-6),
               b'\x4d\x3c\xb2\xa1': ('<', 1e-9), b'\xa1\xb2\x3c\x4d': ('>', 1e-9)}
MAX_BLOCK = 256 * 1024        # a block or record larger than this is damaged (the capture's snap length is about 128 bytes)
MAX_INTERFACES = 256


def _resolution(value):
    return 2.0 ** -(value & 0x7F) if value & 0x80 else 10.0 ** -value


class CaptureReader:
    """An incremental reader of a capture stream (pcapng or classic pcap, chosen by its first bytes). feed(bytes) returns the
    frames completed so far as dicts {iface, linktype, at, caplen, length, data}; a damaged stream raises MalformedCapture."""

    def __init__(self):
        self.buffer = bytearray(); self.kind = None; self.endian = '<'; self.unit = 1e-6
        self.linktype = None; self.interfaces = []; self.frames = 0

    def feed(self, data):
        self.buffer += data; out = []
        while True:
            frame = self._next()
            if frame is None: break
            if frame is not False: out.append(frame); self.frames += 1
        return out

    def _next(self):
        b = self.buffer
        if self.kind is None:
            if len(b) < 4: return None
            if struct.unpack_from('<I', b, 0)[0] == PCAPNG_SHB: self.kind = 'pcapng'
            elif bytes(b[:4]) in PCAP_MAGICS: self.kind = 'pcap'
            else: raise MalformedCapture('the capture tool sent something that is neither pcap nor pcapng')
        return self._pcapng() if self.kind == 'pcapng' else self._pcap()

    def _pcap(self):
        b = self.buffer
        if self.linktype is None:
            if len(b) < 24: return None
            self.endian, self.unit = PCAP_MAGICS[bytes(b[:4])]
            major, _minor = struct.unpack_from(self.endian + 'HH', b, 4)
            if major != 2: raise MalformedCapture('a pcap stream of version %d, not 2' % major)
            self.linktype = struct.unpack_from(self.endian + 'I', b, 20)[0] & 0x0FFFFFFF
            self.interfaces = [{'name': None, 'linktype': self.linktype, 'unit': self.unit}]
            del b[:24]; return False
        if len(b) < 16: return None
        sec, frac, caplen, length = struct.unpack_from(self.endian + 'IIII', b, 0)
        if caplen > MAX_BLOCK: raise MalformedCapture('a pcap record claims %d bytes' % caplen)
        if frac >= (1000000000 if self.unit < 1e-6 else 1000000): raise MalformedCapture('a pcap record has an impossible time')
        if len(b) < 16 + caplen: return None
        data = bytes(b[16:16 + caplen]); del b[:16 + caplen]
        return {'iface': 0, 'linktype': self.linktype, 'at': sec + frac * self.unit, 'caplen': caplen, 'length': max(length, caplen), 'data': data}

    def _pcapng(self):
        b = self.buffer
        if len(b) < 12: return None
        kind = struct.unpack_from('<I', b, 0)[0]
        if kind == PCAPNG_SHB:
            magic = bytes(b[8:12])
            if magic == struct.pack('<I', BYTE_ORDER_MAGIC): self.endian = '<'
            elif magic == struct.pack('>I', BYTE_ORDER_MAGIC): self.endian = '>'
            else: raise MalformedCapture('a pcapng section header without its byte-order mark')
        e = self.endian
        kind, total = struct.unpack_from(e + 'II', b, 0)
        if total < 12 or total % 4 or total > MAX_BLOCK: raise MalformedCapture('a pcapng block of %d bytes' % total)
        if len(b) < total: return None
        if struct.unpack_from(e + 'I', b, total - 4)[0] != total: raise MalformedCapture('a pcapng block whose two lengths differ')
        body = bytes(b[8:total - 4]); del b[:total]
        if kind == PCAPNG_SHB:
            if len(body) < 16: raise MalformedCapture('a pcapng section header that is too short')
            self.interfaces = []; return False
        if kind == 1:  # interface description
            if len(body) < 8: raise MalformedCapture('a pcapng interface description that is too short')
            linktype, _reserved, _snap = struct.unpack_from(e + 'HHI', body, 0)
            name = None; unit = 1e-6; at = 8
            while at + 4 <= len(body):
                code, size = struct.unpack_from(e + 'HH', body, at); at += 4
                if code == 0: break
                if at + size > len(body): raise MalformedCapture('a pcapng option runs past its block')
                value = body[at:at + size]; at += (size + 3) // 4 * 4
                if code == 2: name = value.split(b'\0', 1)[0].decode('utf-8', 'replace')[:32]
                elif code == 9 and size >= 1: unit = _resolution(value[0])
            if len(self.interfaces) >= MAX_INTERFACES: raise MalformedCapture('more interfaces than a capture of this computer has')
            self.interfaces.append({'name': name, 'linktype': linktype, 'unit': unit}); return False
        if kind in (6, 2):  # enhanced packet; the obsolete packet block
            if kind == 6:
                if len(body) < 20: raise MalformedCapture('a pcapng packet block that is too short')
                index, high, low, caplen, length = struct.unpack_from(e + 'IIIII', body, 0); start = 20
            else:
                if len(body) < 20: raise MalformedCapture('a pcapng packet block that is too short')
                index, _drops, high, low, caplen, length = struct.unpack_from(e + 'HHIIII', body, 0); start = 20
            if index >= len(self.interfaces): raise MalformedCapture('a packet names interface %d, which the capture never described' % index)
            if start + caplen > len(body): raise MalformedCapture('a packet claims more bytes than its block holds')
            iface = self.interfaces[index]
            return {'iface': index, 'linktype': iface['linktype'], 'at': ((high << 32) | low) * iface['unit'], 'caplen': caplen,
                    'length': max(length, caplen), 'data': body[start:start + caplen]}
        if kind == 3:  # simple packet: interface 0, no time
            if len(body) < 4 or not self.interfaces: raise MalformedCapture('a simple packet block without an interface')
            length = struct.unpack_from(e + 'I', body, 0)[0]; data = body[4:4 + min(length, len(body) - 4)]
            return {'iface': 0, 'linktype': self.interfaces[0]['linktype'], 'at': None, 'caplen': len(data), 'length': length, 'data': data}
        return False  # statistics, name resolution and custom blocks: nothing to keep

    def interface_name(self, index):
        try: return self.interfaces[index]['name']
        except (IndexError, TypeError): return None


IP_PROTOCOLS = {1: 'icmp', 2: 'igmp', 6: 'tcp', 17: 'udp', 47: 'gre', 50: 'esp', 51: 'ah', 58: 'icmp6', 89: 'ospf', 103: 'pim',
                112: 'vrrp', 132: 'sctp'}
TCP_FLAGS = ((0x01, 'F'), (0x02, 'S'), (0x04, 'R'), (0x08, 'P'), (0x10, '.'), (0x20, 'U'), (0x40, 'E'), (0x80, 'W'))
DIRECTIONS = {0: 'in', 1: 'in', 2: 'in', 3: 'other', 4: 'out'}
VLAN = (0x8100, 0x88A8, 0x9100)


def tcp_flags(byte):
    """TCP flags as tcpdump writes them: S, S., ., P., F., R ..."""
    return ''.join(letter for bit, letter in TCP_FLAGS if byte & bit) or 'none'


def _ipv4(data, at, out):
    if len(data) < at + 20 or data[at] >> 4 != 4: out['proto'] = 'ip'; return
    ihl = (data[at] & 0x0F) * 4; number = data[at + 9]
    out['src'] = str(ipaddress.IPv4Address(data[at + 12:at + 16])); out['dst'] = str(ipaddress.IPv4Address(data[at + 16:at + 20]))
    first = (struct.unpack_from('!H', data, at + 6)[0] & 0x1FFF) == 0
    _transport(data, at + max(ihl, 20), number, first, out, six=False)


def _ipv6(data, at, out):
    if len(data) < at + 40 or data[at] >> 4 != 6: out['proto'] = 'ip6'; return
    number = data[at + 6]
    out['src'] = str(ipaddress.IPv6Address(data[at + 8:at + 24])); out['dst'] = str(ipaddress.IPv6Address(data[at + 24:at + 40]))
    at += 40; first = True
    for _ in range(8):  # extension headers: hop-by-hop, routing, destination options, fragment, authentication
        if number in (0, 43, 60) and len(data) >= at + 2: number, at = data[at], at + (data[at + 1] + 1) * 8
        elif number == 44 and len(data) >= at + 8: first = (struct.unpack_from('!H', data, at + 2)[0] >> 3) == 0; number, at = data[at], at + 8
        elif number == 51 and len(data) >= at + 2: number, at = data[at], at + (data[at + 1] + 2) * 4
        else: break
    _transport(data, at, number, first, out, six=True)


def _transport(data, at, number, first, out, six):
    name = IP_PROTOCOLS.get(number, 'ip-proto-%d' % number)
    out['proto'] = name + ('6' if six and name in ('tcp', 'udp') else '')
    if not first or name not in ('tcp', 'udp', 'sctp') or len(data) < at + 4: return
    out['sport'], out['dport'] = struct.unpack_from('!HH', data, at)
    if name == 'tcp' and len(data) >= at + 14: out['flags'] = tcp_flags(data[at + 13])


def _arp(data, at, out):
    out['proto'] = 'arp'
    if len(data) >= at + 28 and struct.unpack_from('!H', data, at + 2)[0] == 0x0800 and data[at + 4] == 6 and data[at + 5] == 4:
        out['src'] = str(ipaddress.IPv4Address(data[at + 14:at + 18])); out['dst'] = str(ipaddress.IPv4Address(data[at + 24:at + 28]))


def _ethertype(data, at, kind, out):
    if kind == 0x0800: _ipv4(data, at, out)
    elif kind == 0x86DD: _ipv6(data, at, out)
    elif kind == 0x0806: _arp(data, at, out)
    else: out['proto'] = 'ether-0x%04x' % kind


def decode(frame, names=None, interface=None):
    """A frame's header fields as a packet summary {at, iface, proto, src, sport, dst, dport, length, flags?, direction?}: header
    fields only, never what the packet carries. names maps a Linux cooked v2 interface index to its name; interface is the
    name the capture's own description gave (pcapng), else the interface the capture was asked for."""
    data = frame.get('data') or b''; kind = frame.get('linktype')
    out = {'at': frame.get('at'), 'iface': interface, 'proto': None, 'src': None, 'sport': None, 'dst': None, 'dport': None,
           'length': frame.get('length')}
    try:
        if kind == 1:  # Ethernet, with up to two VLAN tags
            if len(data) < 14: out['proto'] = 'ether'; return out
            ether = struct.unpack_from('!H', data, 12)[0]; at = 14
            for _ in range(2):
                if ether in VLAN and len(data) >= at + 4: ether = struct.unpack_from('!H', data, at + 2)[0]; at += 4
            _ethertype(data, at, ether, out)
        elif kind == 113:  # Linux cooked v1
            if len(data) < 16: out['proto'] = 'sll'; return out
            out['direction'] = DIRECTIONS.get(struct.unpack_from('!H', data, 0)[0])
            _ethertype(data, 16, struct.unpack_from('!H', data, 14)[0], out)
        elif kind == 276:  # Linux cooked v2: the interface's index travels with every packet
            if len(data) < 20: out['proto'] = 'sll2'; return out
            index = struct.unpack_from('!I', data, 4)[0]
            if names and index in names: out['iface'] = names[index]
            out['direction'] = DIRECTIONS.get(data[10])
            _ethertype(data, 20, struct.unpack_from('!H', data, 0)[0], out)
        elif kind in (101, 228, 229, 12, 14):  # raw IP
            if data and data[0] >> 4 == 6: _ipv6(data, 0, out)
            elif data: _ipv4(data, 0, out)
        elif kind in (0, 108):  # BSD loopback (host order) and OpenBSD loop (network order)
            if len(data) < 4: out['proto'] = 'loop'; return out
            family = struct.unpack_from('!I' if kind == 108 else ('<I' if sys.byteorder == 'little' else '>I'), data, 0)[0]
            if family == 2: _ipv4(data, 4, out)
            elif family in (10, 24, 28, 30): _ipv6(data, 4, out)
            else: out['proto'] = 'loop'
        else: out['proto'] = 'link-%s' % kind
    except (struct.error, ValueError, IndexError):
        out['proto'] = out['proto'] or 'damaged'
    if out.get('direction') is None: out.pop('direction', None)
    return out


# ---------------------------------------------------------------------------------------------------------------- the operations

def observe(kernel=None, args=None, proc_root=PROC, sys_root=SYS, etc=ETC, now=None, memory=None, capture=None):
    """network.observe: the interfaces with their rates, the connections with their processes (filtered here, bounded, the
    rest counted), the capture's state, and what could not be read. Files only; no request of any kind."""
    args = args or {}; now = time.time() if now is None else now
    parts = parse_filter(args.get('filter', ''))
    rows, reason = interfaces(proc_root, sys_root, now, memory)
    found, notes = connections(proc_root, etc)
    if reason: notes.insert(0, 'interfaces: ' + reason)
    if rows and all(r['rx_bps'] is None for r in rows): notes.append('rates appear from the second look')
    matched = [c for c in found if matches(c, parts)]
    if capture is None:
        from . import network_capture
        try: capture = network_capture.state(kernel) if kernel is not None else {'state': 'IDLE'}
        except (OSError, ValueError) as exc:   # the capture's state could not be read: observing goes on, and says why
            capture = {'state': 'IDLE'}; notes.append('capture: ' + clip(exc))
    by_state = {}
    for c in found: by_state[c['state']] = by_state.get(c['state'], 0) + 1
    return {'schema': SCHEMA, 'observed_at': now, 'interfaces': rows, 'connections': matched[:CONNECTION_LIMIT],
            'rest': {'connections': max(0, len(matched) - CONNECTION_LIMIT)}, 'capture': capture,
            'counts': {'connections': len(found), 'matched': len(matched), 'by_state': by_state},
            'filter': {'text': parts['text'], 'errors': parts['errors']}, 'notes': notes,
            'sources': ['/proc/net/dev', '/sys/class/net', '/proc/net/tcp', '/proc/net/tcp6', '/proc/net/udp', '/proc/net/udp6',
                        '/proc/<pid>/fd', '/etc/services', '/etc/passwd']}


def dispatch(kernel, operation, args, principal):
    if operation == 'network.observe': return observe(kernel, args)
    if operation in FIELDS:
        from . import network_capture
        return network_capture.dispatch(kernel, operation, args, principal)
    raise ValueError('Unknown network operation')
