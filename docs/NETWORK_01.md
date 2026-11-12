# The network: observe, capture, and what the agent may read

November 7, 2026 · HATCH DESK D5 · the owner's direction of November 6: "Instead of log notes, let's have network. And we should
probably add a network traffic scanner or packet sniffer capability that the agent can inspect." and "I meant log notes replaced
with network."

Graphite can show what this computer is doing on the network: its interfaces and how fast they move, every open connection with
the program that holds it, and, when you start one, a short capture of packet headers. You follow it in the writing line's Log
mode, on the Network stream (`workbench/log_qt.py`, D3). The agent reads the same things during an assignment and may propose a
capture, which only you can start.

Capture only networks you own or may monitor. A capture never puts an interface in promiscuous mode, so it sees this computer's
own traffic and what the network sends to every machine on it (broadcast and multicast, such as other machines' ARP and mDNS);
an interface another program has already made promiscuous, or a bridge that carries virtual machines, carries more. The traffic
of other people on a shared network is still theirs.

## The four operations

Every action goes through the Kernel's one dispatcher (`Kernel.dispatch`), with the same scope checks as everything else. The
pure parts are in `workbench/network_watch.py`; the capture's runner, state and files in `workbench/network_capture.py`.

| Operation | Scope | Arguments | Returns |
|---|---|---|---|
| `network.observe` | read | `filter?` | `{interfaces, connections, capture, observed_at}` and `counts`, `rest`, `filter`, `notes`, `sources` |
| `network.capture.start` | execute, and the owner's own action | `filter?`, `interface?` (default `any`), `seconds?` (5 to 480, default 120), `packets?` (1 to 100,000, default 20,000) | `{capture, started, job?}` |
| `network.capture.stop` | execute | `discard?` | `{capture, stopped, discarded}` |
| `network.capture.read` | read | `after?`, `filter?`, `limit?` (1 to 1,000, default 200) | `{packets, next, capture, rest, missed, filter, job?}` |

The shapes D3 builds against:

- an interface: `{name, rx_bps, tx_bps, rx_bytes, tx_bytes, up}`, plus `state` (operstate), `index`, packets, errors and drops in
  each direction. Rates are in bits per second, from two looks kept between calls; the first look has none (`null`), and nothing
  ever sleeps inside a dispatch.
- a connection: `{proto, local, lport, remote, rport, state, pid?, process?, user?}`, plus `lservice` and `rservice` (the port's
  name from `/etc/services`). Conversations come first, then listening sockets, `TIME_WAIT` last.
- the capture: `{state: 'IDLE' | 'RUNNING' | 'UNAVAILABLE', reason?, tool?, started?, packets?, filter?}`, plus, while running,
  `expression` (the capture filter), `interface`, `seconds`, `limit`, `snap`, `job`; when unavailable, `enable` (the steps);
  when idle, `last` (the latest capture's outcome, packets and filter); `stopping` while a stop is being carried out; and
  `proposal` when someone other than the owner asked for a capture (see Consent).
- a packet: `{seq, at, iface, proto, src, sport, dst, dport, length, flags?, process?}`, plus `pid?` and `direction?` (in or out,
  when the link header says). `next` is the sequence number to pass as `after` next time; sequence numbers keep rising across
  captures, so an old cursor never meets new packets twice.

`network.observe` and `network.capture.read` are observers (`activity.OBSERVER_OPERATIONS`): the Log view polls them every second
or two, and reading is not an event in the journal. Starting and stopping are events like any other job's.

## What is observed, and how

Observing reads files only, without privileges:

- `/proc/net/dev`: bytes, packets, errors and drops per interface; `/sys/class/net/<if>/operstate`, `flags` and `ifindex`: up or
  down (an interface that says `unknown`, like the loopback, counts as up when its IFF_UP flag is set).
- `/proc/net/tcp`, `tcp6`, `udp` and `udp6`: every socket of this computer, its addresses and ports in hex (each 32-bit word in the
  host's byte order), its state (TCP states named; a bound UDP socket is `UNCONN`), its owner's uid and its inode. An IPv4-mapped
  IPv6 address (`::ffff:192.168.1.7`) is shown plainly as `192.168.1.7`.
- `/proc/<pid>/fd` and `/proc/<pid>/comm`: which process holds which socket, for the processes this account may read. A socket of
  another account's process is reported as `another user` with that account's name, never guessed; a socket no process holds
  (`TIME_WAIT`) has no process.
- `/etc/services` and `/etc/passwd` for port and user names, parsed as text: the system's name services (`getservbyport`,
  `getpwuid`) are never called, because on some systems they ask a server.
- `/proc/net/fib_trie` and `/proc/net/if_inet6` for this computer's own addresses (to name a captured packet's process).

No DNS lookup and no network request of any kind: `tests_integrated/test_network_watch.py` proves it with an audit hook that hears
every socket the interpreter makes, while observing a fake computer and this one.

The filter applies in Graphite (server side), and results are bounded: at most 500 connections and 64 interfaces, with
`rest.connections` counting what was left out.

## The filter

The same words work in Log's Network stream, for observing, for reading a capture and for starting one:

```
10.0.0.5   host 10.0.0.5   10.0.0.0/24   net 10.0.0.0/24   localhost    a host: an address or a network
443   port 443   :443   10.0.0.5:443   [::1]:22                         a port, or a host and its port
tcp udp icmp icmp6 arp ip ip6 tcp6 udp6 sctp igmp                      a protocol, as the capture filter means it
listen established time_wait ...                                       a connection state (does not narrow packets)
firefox   proc firefox   user owner                                    any other word: a process or user name, in part
```

A protocol word means the same for connections, packets and the capture filter: `ip` is every IPv4 packet and `ip6` every IPv6
one (ARP is neither); `tcp` and `udp` either version; `tcp6` and `udp6` TCP and UDP over IPv6, as on the wire (a tcp6 socket
talking to an IPv4 address, shown plainly, counts as `ip`); `icmp` is ICMP for IPv4 and `icmp6` for IPv6.

Words of one kind widen (`port 80 port 443`: either), kinds narrow (`host 10.0.0.5 tcp`: both). Anything else is refused with
words, never read as a process name: `and`, `or`, `not`, quotes, brackets, semicolons, `$`, backticks; the capture tools' own
words (`src` and `dst`, since a host or port matches either end; `portrange`, `gateway`, `ether`, `broadcast`, `multicast`,
`less`, `greater`, `len`, `vlan` and the like; `proc less` still names a program called less); protocols Graphite does not
select (`gre`, `esp`, `ah`, `ospf`, `pim`, `vrrp`, `igrp`); an address with a zone (`fe80::1%eth0`); a number with dots that is
no address (`1.2.3`); digits other than 0 to 9; a port outside 1 to 65535; more than 32 words or 300 characters. A name such as
`example.org` is accepted for observing but matches nothing and says so: Graphite never looks a name up, and a capture filter with
a name in it is refused, because compiling it would make the capture tool look it up.

`network_watch.bpf` writes the capture filter from the canonical values only (addresses through Python's `ipaddress` and checked
again, ports as integers, protocols from a fixed table), never from the typed text, and refuses anything outside `[a-z0-9 .:/()]`.
Process words and states are applied when the packets are read, and say so: the Log view's confirmation lists what the capture
tool selects and what is applied as the packets are read, and a proposal's words say the same.

## What a capture keeps, and never keeps

A capture runs the system's own capture tool as a tracked Kernel job (`network.capture`, run by the ordinary job worker, no new
scheduler or process kind):

```
dumpcap -q -i any -p -s 128 -c PACKETS -a duration:SECONDS [-f FILTER] -w -
tcpdump -i any -p -n -s 128 -c PACKETS -U -w - [FILTER]
```

- an argument list, never a shell; the tool by its absolute path, never through sudo or pkexec; `-p`: the interface is never
  put in promiscuous mode (see the first section for what it still sees);
- `-s 128`: at most 128 bytes of each packet leave the tool, enough for the link, IP and transport headers. After short headers
  those bytes include the start of what the packet carries: 74 bytes for TCP over IPv4 on Ethernet (128 - 14 - 20 - 20), 86 for
  UDP (128 - 14 - 20 - 8). They pass through the job worker's memory once: Graphite's parser reads only the header fields (time,
  interface, protocol, addresses, ports, length, TCP flags, direction) and drops the rest at once, so the summaries, the ring, its
  file and the job record never hold what packets carry;
- bounded by seconds and packets (the tool's own bounds, and the runner's: tcpdump has no time bound of its own);
- the stream is pcapng from dumpcap or pcap from tcpdump, read incrementally by `network_watch.CaptureReader` (both byte orders,
  micro- and nanosecond times; Ethernet with VLAN tags, Linux cooked v1 and v2, raw IP, BSD loopback; IPv4, IPv6 with extension
  headers, ARP; TCP, UDP, SCTP, ICMP). Damaged input ends the capture with words, never a guess.

Each packet's process is named from the connection table, read again every two seconds while the capture runs, and only when the
table knows the socket on this computer's side (`network_watch.owner_index` and `attribute`):

- first by the whole conversation (protocol, both addresses and both ports), so two connections to the same local port, such as
  a forking server's children, are told apart;
- then, for UDP and for a TCP handshake (a connection that is not one yet belongs to its listener), by the socket bound to the
  packet's local address and port, or to every address when the address is this computer's;
- when different programs hold sockets under the same key (SO_REUSEPORT listeners, such as avahi and a browser on udp 5353), the
  packet has no process; when one program holds it in several processes, the program is named without a pid. Never the first
  one found. When both ends are this computer's, the sender's program is named.

The summaries are kept in a ring of the newest 5,000 in the worker's memory, mirrored to `.ledger/network/<job>.tsv` in the
workspace's private state (folder mode 0700, file mode 0600). Only one capture is kept: the next start deletes the previous one's
file once Kernel.submit has accepted the new capture (a refused start, for example while work is held after Master Stop, leaves
the previous one readable), and Stop with discard (`network.capture.stop {discard: true}`) deletes it at once.

Nothing leaves the computer: the operations are in `stacy_control.CLOUD_PRIVATE`, so a cloud provider can neither see nor
propose them; the phone link's operation list does not include them; the capture job is a private record family
(`record_visibility.PRIVATE_FAMILIES` holds `network.`), so only its owner reads it and a paired phone's `jobs.list` and `jobs.get`
never show its filter, command, interface or counts; the files under `.ledger` are outside every file operation; and no capture
file is ever sent.

## Ending a capture

A capture ends at its packet or seconds bound, when the tool finishes, or when it is stopped: Stop capture in Log's Network stream
(`network.capture.stop`), Stop all jobs and Master Stop (both cancel every job through `jobs.cancel`, and Master Stop also holds
work, which the runner obeys). The tool is asked to finish, then killed if it does not within two seconds; what it had already
captured is kept. A capture is never paused or resumed (`jobs.pause` and `jobs.resume` refuse it): start a new one. If the worker
itself dies, the Kernel's recovery stops the recorded tool by its process identity, as it does for every tracked tool.

## Permissions on Debian

When no tool is installed, or the one installed may not capture, the capture's state is `UNAVAILABLE` with the reason in plain
words and the steps in `enable`. The reasons:

- no capture tool: install `wireshark-common` as the administrator (`apt install wireshark-common`, or
  `bash INSTALL_DEBIAN.sh --network-capture`), answer Yes when it asks whether non-superusers should be able to capture packets,
  add yourself to the `wireshark` group (`usermod -aG wireshark <you>`), log out and in again;
- dumpcap installed without capture permission: `dpkg-reconfigure wireshark-common` and answer Yes, then the group, then log out
  and in;
- dumpcap not runnable by this account: join the `wireshark` group and log out and in; already in the group in `/etc/group` but
  not in this session's groups: log out and in again;
- tcpdump without capture capabilities: install wireshark-common as above, or give tcpdump the capabilities yourself
  (`setcap cap_net_raw,cap_net_admin=eip /usr/sbin/tcpdump`, as the administrator);
- the tool looked able but refused at run time ("You don't have permission to capture on that device"): the same words, until the
  tool or this session's groups change.

The probe (`network_watch.probe`) decides without starting anything, from the tool's place, whether this account may run it and
its file capabilities (`security.capability`, CAP_NET_RAW). Graphite only explains: it never runs these commands, never asks for
the administrator's password and never changes the system's permissions. The reasons do not offer sudo: a step reads "as the
administrator, ...", which on a minimal Debian may be root's own shell. The Debian installer's optional `--network-capture`
installs the package and prints the remaining steps word for word as Graphite gives them (`network_watch.RECONFIGURE`,
`join_step` with your login, `RELOG`; `docs/MINIMAL_DEBIAN_INSTALL_01.md` lists the same); it does not change groups either.

## Consent

Starting a capture is the owner's own action: `network.capture.start` proceeds only for a principal with the approve scope, which
is the desktop owner (Log's Network stream with its confirmation, which says exactly what is captured; a typed operation line with
its second Enter; Run on a proposal card in Conversation). Kernel.submit checks it again for the job (`network_capture.authorize_job`:
the owner, the request key `network-capture:<plan>`, the plan's filter, bounds and command), and the worker checks the plan once
more before the tool starts. `jobs.submit` cannot start a capture: its schema has no capture options.

Anyone else is refused with `NETWORK_CAPTURE_NEEDS_OWNER` and nothing is captured: an assignment's step (its principal holds read
and execute, never approve), a model's proposal run with a narrowed principal, a phone. What they asked for is kept as the
capture's `proposal` (filter, interface, seconds, packets, who and when; `.ledger/network/proposal.json`, mode 0600) so you can see
it; your next start, or Stop with discard, clears it.

## The agent's access

During an assignment the agent may call `network.observe` and `network.capture.read` freely (read scope). Tool selection
(`workbench/tool_selection.py`) offers the network family for words such as network, traffic, connection, port, packet,
bandwidth, listening, sniff, capture; the family lists its reads first (observe, then capture.read), then its controls.

The assignment profile `network_talk` (`workbench/profile_network.py`) answers plain questions such as "What is talking to the
network?", "which programs are using the internet", "what ports are open" or "capture the traffic on port 443" (explicit words
choose it, never a model; a request about files still goes to files_about):

1. `network.observe` (with the request's ports, addresses or protocol as the filter): one finding per program with open
   conversations, one for what listens;
2. `network.capture.read`: the latest capture's busiest conversations, when there is one;
3. only when the request asks for a capture and there is none to read: `network.capture.start` with the request's filter for 60
   seconds and 2,000 packets. The Kernel refuses it and keeps the proposal; the assignment waits, and Needs you says what Graphite
   proposes and how to start it (Log, Network, the filter, Capture…). Resume then reads what you captured, or writes the page
   without a capture. When capture is unavailable on this computer, that is a question with the reason instead of a proposal;
4. `documents.create`: the findings page "What is talking to the network" (who talks to whom, what listens, the interfaces, the
   capture's busiest conversations, and that nothing was sent anywhere).

## Limits

- Not promiscuous: this computer's own traffic and what the network sends to every machine (broadcast, multicast); on a
  switched network little else arrives, but an interface already promiscuous, or a bridge for virtual machines, carries more.
- Headers only are kept, but up to 128 bytes of each packet reach the job worker, which drops all but the header fields at once.
- `any` (the default interface) captures every interface; the interface name per packet is known when the link header carries it
  (Linux cooked v2, pcapng's interface description), otherwise it reads `any`.
- A process is named only for this account's processes; others are `another user`. A packet's process comes from the connection
  table at that moment: a connection that opened and closed between two looks has none, a TCP packet of a connection the table
  does not know yet has none for up to two seconds, and a socket key shared by different programs has none.
- One capture at a time, one kept. The ring holds the newest 5,000 summaries; a reader that falls behind is told how many it
  `missed`.
- Names are never looked up: addresses stay addresses.
- No capture tool was available where this was built: the capture is tested with fixture bytes and a stand-in tool; a real
  dumpcap or tcpdump run, and the owner's machine, remain to be tried.

## Files and tests

`workbench/network_watch.py` (readers, parsers, filter, translator, probe, the pcap and pcapng parser, observe),
`workbench/network_capture.py` (the job's runner, start, stop, read, the state and its files), `workbench/profile_network.py`
(the assignment), the Kernel registration in `workbench/engineering_kernel.py` (the four operations, the job tool
`network.capture`, Kernel.submit's check, the run_job branch, pause and resume refused), `workbench/engineering_cli.py` (the
argument schemas) and `sdk/cli/arc1cli/record_visibility.py` (`network.` among the private record families);
`tests_integrated/test_network_watch.py` in the focused set.

Registry additions (docs/GRAPHITE_0.1_REGISTRY.json): the operations `network.observe`, `network.capture.start`,
`network.capture.stop`, `network.capture.read`; the job tool `network.capture`; and `network_talk` in `agent.assign`'s profile
choices. No setting was added.
