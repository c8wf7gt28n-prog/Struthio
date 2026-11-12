"""The packet capture (HATCH DESK D5): the system's own capture tool, run as a tracked Kernel job, headers only.

The owner, 2026-11-06: "we should probably add a network traffic scanner or packet sniffer capability that the agent can
inspect." network_watch.py holds the pure parts (the filter, the capture filter, the pcap and pcapng parser, the availability
probe); this module starts, follows, stops and reads a capture. docs/NETWORK_01.md is the account in words.

How a capture runs (no new scheduler, store or process kind):
  network.capture.start  the owner's own action only (a principal with the approve scope: the desktop's Log view, its
                         confirmation, a typed operation line with its second Enter). Anyone else (an assignment's step, a
                         model's proposal, a phone) is refused with NETWORK_CAPTURE_NEEDS_OWNER and what they asked for is
                         kept as the capture's `proposal` for the owner to see and start. The owner's start checks the filter
                         (refused when any word is not understood), probes the tool (UNAVAILABLE with the reason and the
                         Debian steps when there is none or it may not capture), and submits the Kernel job tool
                         'network.capture' through Kernel.submit with the request key 'network-capture:<plan>' and the plan
                         in the job's 'network' options (authorize_job checks both again). Kernel.launch starts the ordinary
                         job worker, whose run_job calls run() below.
  run()                  in the job worker: spawn() starts the tool (the one function that does: an argv list, never a
                         shell, never the administrator; dumpcap -p -s 128 -c N -a duration:S -f <filter> -w -, or tcpdump -p -n -s 128
                         -c N -U -w - <filter>), reads its stream, keeps packet summaries in a bounded ring in memory
                         (RING) mirrored to .ledger/network/<job>.tsv (folder 0700, file 0600), names each packet's process
                         from the connection table (read again every OWNERS_SECONDS), and ends at the seconds or packet bound,
                         when the job is cancelled (Stop capture, Stop all jobs, Master Stop: jobs.cancel) or when work is held.
  network.capture.stop   cancels the job through jobs.cancel (the same path Master Stop takes); discard:true also deletes
                         the capture's file and the proposal.
  network.capture.read   the latest capture's packets after a sequence number, the filter applied here, bounded, the rest
                         counted. Sequence numbers rise across captures, so a cursor never meets an older capture's packets.
Only one capture is kept: the next start deletes the previous one's file once Kernel.submit has accepted the new one (a refused
start leaves it). Nothing is sent anywhere: the summaries stay in the workspace's private state, for the owner and for Graphite
during an assignment, and the capture job is a private record family (record_visibility.PRIVATE_FAMILIES 'network.'): only its
owner reads it, so a paired phone's jobs.list and jobs.get never show its filter, command or counts.
"""
from __future__ import annotations
import collections
import json
import os
import re
import select
import subprocess
import time
import uuid
from pathlib import Path

from . import network_watch as watch

JOB_TOOL = 'network.capture'
JOB_TOOLS = frozenset({JOB_TOOL})
SNAP = 128                    # bytes of each packet the tool passes on: the link, IP and transport headers and, after short headers,
                              # the first bytes of what the packet carries (74 for TCP over IPv4 on Ethernet), which the parser reads
                              # past and drops at once: summaries, the ring, its file and the job record hold header fields only
DEFAULT_SECONDS = 120
DEFAULT_PACKETS = 20000
MARGIN = 30                   # the job's runtime bound is the capture's seconds and this margin
RING = 5000                   # packet summaries kept, in memory and in the file
FLUSH_SECONDS = 0.5           # the ring's file is written this often while packets arrive
PROGRESS_SECONDS = 1.0        # and the job's progress (packets, sequence numbers) this often
POLL_SECONDS = 0.2            # how long the worker waits for the tool's output before it looks at the job again
OWNERS_SECONDS = 2.0          # the connection table (who holds which socket) is read again this often
STOP_GRACE = 2.0              # seconds the tool has to finish after it is asked to stop, before it is killed
READ_DEFAULT = 200
READ_LIMIT = 1000
STDERR_LIMIT = 8192
PROPOSAL_SECONDS = 3600       # a proposal older than this is no longer shown
FOLDER = 'network'            # under the workspace's private state (.ledger)
NEEDS_OWNER = 'NETWORK_CAPTURE_NEEDS_OWNER'
STOPPING = 'NETWORK_CAPTURE_STOPPING'
ACTIVE = ('Queued', 'Running')
PERMISSION_WORDS = ('permission', 'not permitted', 'operation not permitted', "don't have permission", 'not allowed')
OPTIONAL = ('flags', 'process', 'pid', 'direction')   # a packet summary's keys that are left out when unknown
START_GRACE = 60.0
INTERFACE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.:@-]{0,14}')   # an interface's name as Linux allows it, never an option            # a queued capture the worker has not claimed within this long no longer blocks a new start


class CaptureError(ValueError):
    pass


def availability():
    """Whether this session may capture (network_watch.probe): the one call tests patch to pretend a tool is installed."""
    return watch.probe()


# ---------------------------------------------------------------------------------------------------------------- private files

def folder(kernel):
    path = Path(kernel.state) / FOLDER
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != 'nt': os.chmod(path, 0o700)
    return path


def packets_path(kernel, ident):
    return folder(kernel) / (str(ident) + '.tsv')


def proposal_path(kernel):
    return folder(kernel) / 'proposal.json'


def write_private(path, text):
    """Write a file only this account can read (0600), atomically."""
    path = Path(path); temporary = path.with_name('.%s.%s.tmp' % (path.name, uuid.uuid4().hex[:8]))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream: stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except OSError: pass
        raise
    if os.name != 'nt': os.chmod(path, 0o600)


def append_private(path, text):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, 'a', encoding='utf-8') as stream: stream.write(text)


def remove(path):
    try: os.unlink(path); return True
    except FileNotFoundError: return False


def line_of(summary):
    return '%d\t%s\n' % (summary['seq'], json.dumps(summary, sort_keys=True, separators=(',', ':')))


def load_packets(path, after=None):
    """The ring's summaries in sequence order (at most RING, the newest), those with seq <= after skipped before they are parsed."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as stream: lines = stream.read().splitlines()
    except FileNotFoundError: return []
    rows = {}
    for line in lines:
        number, _, text = line.partition('\t')
        try: seq = int(number)
        except ValueError: continue
        if after is not None and seq <= after: continue
        try: row = json.loads(text)
        except ValueError: continue
        if isinstance(row, dict): rows[seq] = row
    return [rows[k] for k in sorted(rows)[-RING:]]


# ---------------------------------------------------------------------------------------------------------------- the jobs

def captures(kernel):
    """Every capture job the Kernel keeps, newest first."""
    out = []
    with kernel.db() as db:
        for raw, in db.execute("SELECT payload FROM jobs WHERE payload LIKE ?", ('%"tool": "' + JOB_TOOL + '"%',)):
            try: row = json.loads(raw)
            except ValueError: continue
            if row.get('tool') == JOB_TOOL: out.append(row)
    out.sort(key=lambda j: (j.get('created') or 0), reverse=True)
    return out


def plan_of(job):
    return dict(((job.get('request_spec') or {}).get('network')) or {})


def worker_alive(job, clock=None):
    """A capture job still holds its place: queued a moment ago, or running in a worker that is still the one that claimed it."""
    clock = time.time() if clock is None else clock
    if job.get('state') == 'Queued': return clock - float(job.get('created') or 0) < START_GRACE
    if job.get('state') != 'Running': return False
    from .engineering_kernel import process_token
    pid = job.get('pid'); start = job.get('worker_start')
    if not pid: return False
    token = process_token(pid)
    return token is not None and (not start or token == start)


def live(kernel):
    """(running, stopping): the capture job that runs and is not asked to stop, and one asked to stop that has not ended."""
    running = stopping = None
    for job in captures(kernel):
        if job.get('state') not in ACTIVE or not worker_alive(job): continue
        if job.get('cancel'): stopping = stopping or job
        else: running = running or job
    return running, stopping


def latest(kernel):
    """The newest capture whose packets are kept (not discarded), or None."""
    for job in captures(kernel):
        if not (job.get('capture') or {}).get('discarded') and not job.get('discard'): return job
    return None


def may_read(job, principal):
    """The capture's packets follow its job record's own rule (a private family: its owner only), so a principal that may not
    read the record (a paired device, another identity, whatever its scopes) never reads the packets either."""
    from sdk.cli.arc1cli.record_visibility import job_readable
    return job_readable(job, principal.identity)


def update_job(kernel, ident, change):
    """Read, change and save one job record inside one write transaction (jobs.cancel's flag is never lost)."""
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM jobs WHERE id=?', (ident,)).fetchone()
        if row is None: raise CaptureError('The capture job is gone')
        job = json.loads(row[0]); change(job); kernel.save('jobs', job, db)
    return job


# ---------------------------------------------------------------------------------------------------------------- the state

def proposal(kernel, clock=None):
    clock = time.time() if clock is None else clock
    try: value = json.loads(proposal_path(kernel).read_text(encoding='utf-8'))
    except (OSError, ValueError): return None
    if not isinstance(value, dict) or clock - float(value.get('at') or 0) > PROPOSAL_SECONDS: return None
    return value


def ended_words(job):
    capture = job.get('capture') or {}
    return capture.get('outcome') or {'Completed': 'finished', 'Cancelled': 'stopped', 'Failed': 'could not capture'}.get(job.get('state'), str(job.get('state') or '').lower())


def state(kernel, found=None):
    """The capture as the contract gives it: {state 'IDLE'|'RUNNING'|'UNAVAILABLE', reason?, tool?, started?, packets?, filter?}
    and, beside them, the bounds, the job, the last capture's summary and an open proposal."""
    running, stopping = live(kernel)
    open_proposal = proposal(kernel)
    if running is not None:
        plan = plan_of(running); progress = running.get('capture') or {}
        out = {'state': 'RUNNING', 'tool': plan.get('tool'), 'started': progress.get('started') or running.get('started') or running.get('created'),
               'packets': int(progress.get('packets') or 0), 'filter': plan.get('filter') or '', 'expression': plan.get('bpf') or '',
               'interface': plan.get('interface'), 'seconds': plan.get('seconds'), 'limit': plan.get('packets'), 'snap': plan.get('snap', SNAP), 'job': running['id']}
        return out
    found = availability() if found is None else found
    out = {'state': 'UNAVAILABLE' if found.get('state') != 'AVAILABLE' else 'IDLE', 'tool': found.get('tool')}
    if out['state'] == 'UNAVAILABLE': out.update(reason=found.get('reason') or 'Capture is not available on this computer.', enable=list(found.get('enable') or []))
    last = latest(kernel)
    if last is not None:
        plan = plan_of(last); progress = last.get('capture') or {}
        out['last'] = {'job': last['id'], 'state': last.get('state'), 'outcome': ended_words(last), 'packets': int(progress.get('packets') or 0),
                       'started': progress.get('started') or last.get('started'), 'ended': progress.get('ended') or last.get('finished'),
                       'filter': plan.get('filter') or '', 'tool': plan.get('tool'), 'error': last.get('error') or ''}
        if (out['state'] == 'IDLE' and last.get('state') == 'Failed' and progress.get('permission')
                and progress.get('signature') == found.get('signature') and progress.get('groups') == sorted(os.getgroups())):
            # the tool looked able to capture but refused: say so until the tool or this session's groups change
            out.update(state='UNAVAILABLE', reason=permission_words(plan.get('tool') or found.get('tool'), last.get('error') or ''),
                       enable=[watch.RECONFIGURE, watch.join_step(login_name()), watch.RELOG])
    if stopping is not None: out['stopping'] = stopping['id']
    if open_proposal: out['proposal'] = open_proposal
    return out


def login_name():
    return watch.parse_passwd(watch.read_text(os.path.join(watch.ETC, 'passwd'), 1024 * 1024)[0]).get(os.geteuid()) or os.environ.get('USER')


def permission_words(tool, error):
    said = ' '.join(str(error or '').split())[:300]
    return ('%s is installed but refused to capture%s. To enable capture on Debian: %s; then %s; then %s. %s'
            % (tool or 'The capture tool', (' (“%s”)' % said) if said else '', watch.RECONFIGURE, watch.join_step(login_name()), watch.RELOG, watch.NEVER))


# ---------------------------------------------------------------------------------------------------------------- the command

def command(plan):
    """The capture tool's argv for a plan: a list (never a shell string), the tool by its absolute path (never through sudo or pkexec), headers
    only (-s SNAP), never promiscuous (-p), bounded by packets (-c) and, for dumpcap, by seconds (-a duration); tcpdump's seconds
    are kept by run(). The filter goes last, as one word, built only from canonical values by network_watch.bpf."""
    tool = plan.get('tool'); path = str(plan.get('path') or '')
    if tool not in watch.TOOLS or os.path.basename(path) != tool or not os.path.isabs(path): raise CaptureError('Not a capture tool Graphite runs: ' + path[:120])
    interface = str(plan.get('interface') or 'any'); seconds = int(plan['seconds']); packets = int(plan['packets'])
    expression = str(plan.get('bpf') or '')
    if not watch.BPF_SAFE.fullmatch(expression): raise CaptureError('The capture filter could not be written safely')
    if interface != 'any' and not INTERFACE.fullmatch(interface): raise CaptureError('Not an interface name: ' + interface[:20])
    if tool == 'dumpcap':
        argv = [path, '-q', '-i', interface, '-p', '-s', str(SNAP), '-c', str(packets), '-a', 'duration:%d' % seconds]
        if expression: argv += ['-f', expression]
        return argv + ['-w', '-']
    argv = [path, '-i', interface, '-p', '-n', '-s', str(SNAP), '-c', str(packets), '-U', '-w', '-']
    return argv + ([expression] if expression else [])


def spawn(argv):
    """The one function that starts a capture tool: its own session (so it is stopped as a group), no input, its output read by
    run(), a plain environment. Tests patch it; nothing in a test or check starts a real capture."""
    return subprocess.Popen(list(argv), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
                            start_new_session=os.name != 'nt', env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})


# ---------------------------------------------------------------------------------------------------------------- the operations

def args_of(args):
    seconds = int(args.get('seconds', DEFAULT_SECONDS)); packets = int(args.get('packets', DEFAULT_PACKETS))
    interface = str(args.get('interface') or 'any'); text = ' '.join(str(args.get('filter') or '').split())
    return text, interface, seconds, packets


def propose(kernel, principal, text, interface, seconds, packets):
    """Keep what someone other than the owner asked for, so the owner sees it (capture.proposal) and may start it."""
    value = {'filter': text, 'interface': interface, 'seconds': seconds, 'packets': packets, 'by': principal.identity, 'at': time.time(),
             'words': proposal_words(text, interface, seconds, packets)}
    write_private(proposal_path(kernel), json.dumps(value, sort_keys=True))
    return value


def selection_words(text):
    """What a filter makes the capture tool select, and what is applied only as the packets are read, in the words the Log view's
    confirmation uses: '' for no filter, else ' (the capture tool selects ...; ... as the packets are read)'."""
    if not text: return ''
    parts = watch.parse_filter(text)
    try: expression, _ = watch.bpf(parts)
    except ValueError: expression = ''
    said = ['the capture tool selects ' + expression if expression else 'the capture tool selects every packet']
    if parts.get('words'): said.append('%s is applied as the packets are read' % ', '.join(parts['words']))
    if parts.get('states'): said.append('%s narrows connections, not packets' % ', '.join(parts['states']))
    return ' (' + '; '.join(said) + ')'


def proposal_words(text, interface, seconds, packets):
    return ('Graphite proposes capturing packet headers%s%s on %s for %d seconds (at most %s packets). Only you can start it: Log, '
            'Network, %sthen Capture… (or Ctrl+Enter in the line).' % (' with the filter “%s”' % text if text else '', selection_words(text),
                                                                      'every interface' if interface == 'any' else interface,
                                                                      seconds, '{:,}'.format(packets), ('type the filter “%s”, ' % text) if text else ''))


def next_seq(kernel):
    top = 0
    for job in captures(kernel):
        progress = job.get('capture') or {}
        top = max(top, int(progress.get('seq_last') or 0), int(plan_of(job).get('seq_first') or 1) - 1)
    return top + 1


def discard(kernel, job):
    """Delete a capture's packets (its file) and mark it discarded; a worker still running stops writing."""
    def change(row):
        row['discard'] = True; row.setdefault('capture', {})['discarded'] = time.time()
    try: update_job(kernel, job['id'], change)
    except CaptureError: pass
    return remove(packets_path(kernel, job['id']))


def start(kernel, args, principal):
    text, interface, seconds, packets = args_of(args)
    parts = watch.parse_filter(text)   # the words first, so a proposal is always one the owner could start as it stands
    if parts['errors']: raise CaptureError('NETWORK_FILTER_REFUSED: ' + '; '.join(parts['errors']) + '. Nothing was captured.')
    expression, errors = watch.bpf(parts)
    if errors: raise CaptureError('NETWORK_FILTER_REFUSED: ' + '; '.join(errors) + '. Nothing was captured.')
    if interface != 'any' and (not INTERFACE.fullmatch(interface) or interface not in set(watch.interface_indexes().values())):
        raise CaptureError('NETWORK_INTERFACE_UNKNOWN: this computer has no interface called %s. Nothing was captured.' % watch.clip(interface, 20))
    if 'approve' not in principal.scopes or principal.mode == 'Tutor':
        value = propose(kernel, principal, text, interface, seconds, packets)
        raise CaptureError(NEEDS_OWNER + ': a capture starts only by the owner’s own action; nothing was captured. ' + value['words'])
    running, stopping = live(kernel)
    if running is not None: return {'capture': state(kernel), 'started': False, 'reason': 'A capture is already running.'}
    if stopping is not None: raise CaptureError(STOPPING + ': the last capture is still stopping; try again in a moment.')
    found = availability()
    if found.get('state') != 'AVAILABLE': return {'capture': state(kernel, found), 'started': False}
    plan = {'plan': uuid.uuid4().hex, 'filter': text, 'bpf': expression, 'interface': interface, 'seconds': seconds, 'packets': packets, 'snap': SNAP,
            'tool': found['tool'], 'path': found['path'], 'signature': found.get('signature'), 'seq_first': next_seq(kernel)}
    command(plan)   # refuses a plan it could not run, before anything is queued
    goal = 'Capture packet headers%s for %d s (at most %d packets)' % ((' · ' + text) if text else '', seconds, packets)
    job = kernel.submit({'tool': JOB_TOOL, 'request_key': 'network-capture:' + plan['plan'], 'timeout': seconds + MARGIN, 'goal': goal,
                         'network': plan}, principal)
    # One capture is kept: the previous one is deleted only now that the new one is accepted. When Kernel.submit refuses (work
    # held after Master Stop, the job limit), the previous capture is still there to read.
    for previous in captures(kernel):
        if previous['id'] != job['id'] and not previous.get('discard'): discard(kernel, previous)
    remove(proposal_path(kernel))
    return {'capture': state(kernel, found), 'started': True, 'job': job['id']}


def authorize_job(kernel, tool, options, request_key, principal):
    """Kernel.submit's check for the capture job: only the owner, only the plan network.capture.start wrote."""
    if tool not in JOB_TOOLS: raise CaptureError('Not a capture job')
    if 'approve' not in principal.scopes or principal.mode == 'Tutor': raise CaptureError(NEEDS_OWNER + ': a capture starts only by the owner’s own action')
    if not isinstance(options, dict) or not options.get('plan') or request_key != 'network-capture:' + str(options.get('plan')):
        raise CaptureError('A capture is started with network.capture.start')
    check_plan(options)


def check_plan(options):
    """The plan is what network.capture.start wrote: its capture filter is the one its words make, its bounds hold, its command
    can be built. The worker checks it again before the tool starts."""
    if not isinstance(options, dict): raise CaptureError('A capture is started with network.capture.start')
    parts = watch.parse_filter(options.get('filter') or '')
    expression, errors = watch.bpf(parts)
    if parts['errors'] or errors or expression != options.get('bpf'): raise CaptureError('The capture filter does not match its words')
    if not 5 <= int(options.get('seconds') or 0) <= 480 or not 1 <= int(options.get('packets') or 0) <= 100000 or int(options.get('snap') or 0) != SNAP:
        raise CaptureError('The capture is outside its bounds')
    command(options)


def stop(kernel, args, principal):
    running, stopping = live(kernel)
    stopped = None
    for job in (running, stopping):
        if job is None or job.get('cancel'): continue
        r = kernel.dispatch('jobs.cancel', {'id': job['id']}, principal)
        if not r.get('ok'): raise CaptureError((r.get('error') or {}).get('message') or 'The capture could not be stopped')
        stopped = job['id']
    discarded = False
    if args.get('discard'):
        for job in captures(kernel):
            if not may_read(job, principal): continue
            if not job.get('discard'): discarded = discard(kernel, job) or discarded
            else: discarded = remove(packets_path(kernel, job['id'])) or discarded
        discarded = remove(proposal_path(kernel)) or discarded
    return {'capture': state(kernel), 'stopped': stopped, 'discarded': discarded}


def read(kernel, args, principal):
    parts = watch.parse_filter(args.get('filter', ''))
    after = args.get('after'); limit = min(int(args.get('limit', READ_DEFAULT)), READ_LIMIT)
    capture = state(kernel); job = latest(kernel)
    out = {'packets': [], 'next': after, 'capture': capture, 'rest': 0, 'missed': 0, 'filter': {'text': parts['text'], 'errors': parts['errors']}}
    if job is None or not may_read(job, principal): return out
    rows = load_packets(packets_path(kernel, job['id']), after)
    if rows and after is not None and rows[0]['seq'] > after + 1 and after + 1 >= int(plan_of(job).get('seq_first') or 1):
        out['missed'] = rows[0]['seq'] - after - 1   # older than the ring keeps: they fell out before this read
    taken = []; last = after
    for row in rows:
        if len(taken) >= limit:
            out['rest'] += 1 if watch.matches(row, parts, packet=True) else 0; continue
        last = row['seq']
        if watch.matches(row, parts, packet=True): taken.append(row)
    out.update(packets=taken, next=last, job=job['id'])
    return out


# ---------------------------------------------------------------------------------------------------------------- the worker

class Owners:
    """Who holds which socket, read again every OWNERS_SECONDS: names each packet's process when the table knows it."""

    def __init__(self, reader=None, clock=time.monotonic):
        self.reader = reader or (lambda: (watch.connections()[0], watch.local_addresses()))
        self.clock = clock; self.at = None; self.index = watch.owner_index(()); self.local = set()

    def refresh(self, force=False):
        now = self.clock()
        if not force and self.at is not None and now - self.at < OWNERS_SECONDS: return
        self.at = now
        try: rows, local = self.reader()
        except Exception: return
        self.index = watch.owner_index(rows); self.local = set(local or ())

    def name(self, packet):
        self.refresh()
        return watch.attribute(packet, self.index, self.local)


class Recorder:
    """The ring: summaries in memory (at most RING) and the file that mirrors them, appended and compacted."""

    def __init__(self, path, first):
        self.path = Path(path); self.ring = collections.deque(maxlen=RING); self.pending = []; self.lines = 0; self.seq = int(first)
        self.packets = 0; self.bytes = 0; self.first = int(first); self.closed = False

    def add(self, summary):
        summary = {k: v for k, v in summary.items() if v is not None or k not in OPTIONAL}
        summary['seq'] = self.seq; self.seq += 1; self.packets += 1; self.bytes += int(summary.get('length') or 0)
        self.ring.append(summary); self.pending.append(summary)
        return summary

    def flush(self):
        if self.closed or not self.pending: return
        if self.lines + len(self.pending) > 2 * RING:
            write_private(self.path, ''.join(line_of(s) for s in self.ring)); self.lines = len(self.ring)
        else:
            append_private(self.path, ''.join(line_of(s) for s in self.pending)); self.lines += len(self.pending)
        self.pending = []

    def close(self, discard=False):
        if discard:
            self.pending = []; self.closed = True; remove(self.path)
        else: self.flush()

    def progress(self):
        return {'packets': self.packets, 'bytes': self.bytes, 'seq_first': self.first, 'seq_last': self.seq - 1 if self.packets else None}


def summarize(frame, reader, names, plan, owners):
    """One frame as the summary the contract gives (header fields only) with its process when the connection table knows it."""
    interface = reader.interface_name(frame.get('iface')) or plan.get('interface')
    summary = watch.decode(frame, names, interface)
    if isinstance(summary.get('at'), float): summary['at'] = round(summary['at'], 6)
    if owners is not None:
        owner = owners.name(summary)
        if owner: summary['process'], summary['pid'] = owner
    return summary


def end_process(proc, grace=STOP_GRACE):
    """Ask the tool to finish (it writes what it holds and exits), then kill it if it does not."""
    if proc.poll() is not None: return proc.returncode
    try: proc.terminate()
    except OSError: pass
    try: return proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try: proc.kill()
        except OSError: pass
        return proc.wait(timeout=grace)


def run(kernel, ident, clock=time.monotonic):
    """The capture job in the Kernel's job worker. Never raises: the job ends Completed (a bound reached or the tool finished),
    Cancelled (stopped: Stop capture, Stop all jobs, Master Stop, held work) or Failed (with the tool's own words)."""
    from . import work_trail
    from .engineering_kernel import process_token
    job = kernel.record('jobs', ident); plan = plan_of(job)
    recorder = Recorder(packets_path(kernel, ident), plan.get('seq_first') or 1)
    reader = watch.CaptureReader(); owners = Owners(); proc = None; errors = bytearray()
    began = clock(); started = time.time(); outcome = None; state_name = 'Completed'; error = ''; permission = False; discarded = False
    last_flush = last_note = began; last_look = None

    def note(change):
        def apply(row):
            capture = dict(row.get('capture') or {}); capture.update(recorder.progress()); capture.update(started=started, tool=plan.get('tool'),
                                                                                                         interface=plan.get('interface'), filter=plan.get('filter') or '')
            row['capture'] = capture; change(row)
        return update_job(kernel, ident, apply)

    def take(data):
        for frame in reader.feed(data):
            recorder.add(summarize(frame, reader, names, plan, owners))
            if recorder.packets >= int(plan['packets']): return True
        return False

    names = {}
    try:
        if job.get('tool') != JOB_TOOL: raise CaptureError('Not a capture job')
        check_plan(plan)
        found = availability()
        if found.get('state') != 'AVAILABLE' or found.get('tool') != plan.get('tool') or found.get('path') != plan.get('path'):
            raise CaptureError(found.get('reason') or 'The capture tool changed since the capture was asked for; start it again.')
        names = watch.interface_indexes(); argv = command(plan)
        proc = spawn(argv)
        note(lambda row: row.update(tool_pid=getattr(proc, 'pid', None), tool_start=process_token(proc.pid) if getattr(proc, 'pid', None) else None,
                                    current_operation='capturing packet headers', argv=list(argv)))
        streams = [s for s in (proc.stdout, proc.stderr) if s is not None]
        for stream in streams: os.set_blocking(stream.fileno(), False)
        open_streams = list(streams)
        while open_streams:
            now = clock()
            if last_look is None or now - last_look >= POLL_SECONDS:
                last_look = now; current = kernel.record('jobs', ident)
                if current.get('discard'): discarded = True
                if current.get('cancel') or work_trail.execution_held(kernel):
                    outcome = 'stopped' if current.get('cancel') else 'stopped: work is held'; state_name = 'Cancelled'; break
            if now - began >= int(plan['seconds']): outcome = 'reached %d seconds' % int(plan['seconds']); break
            ready, _, _ = select.select(open_streams, [], [], POLL_SECONDS)
            full = False
            for stream in ready:
                data = os.read(stream.fileno(), 65536)
                if not data: open_streams.remove(stream); continue
                if stream is proc.stderr:
                    if len(errors) < STDERR_LIMIT: errors += data[:STDERR_LIMIT - len(errors)]
                    continue
                full = take(data) or full
            if full: outcome = 'reached {:,} packets'.format(int(plan['packets'])); break
            if recorder.pending and clock() - last_flush >= FLUSH_SECONDS:
                if not discarded: recorder.flush()
                last_flush = clock()
            if clock() - last_note >= PROGRESS_SECONDS: note(lambda row: None); last_note = clock()
            if proc.stdout not in open_streams: break
        code = end_process(proc)
        # what the tool wrote before it stopped (bounded): a stop keeps the packets already on their way
        if proc.stdout is not None and not discarded:
            deadline = clock() + STOP_GRACE
            while clock() < deadline and recorder.packets < int(plan['packets']):
                try: data = os.read(proc.stdout.fileno(), 65536)
                except (BlockingIOError, InterruptedError): break
                except OSError: break
                if not data or take(data): break
        if proc.stderr is not None:
            try: errors += (os.read(proc.stderr.fileno(), STDERR_LIMIT) or b'')[:max(0, STDERR_LIMIT - len(errors))]
            except OSError: pass
        said = ' '.join(errors.decode('utf-8', 'replace').split())
        if outcome is None:
            if code not in (0, None) and recorder.packets == 0:
                state_name = 'Failed'; permission = any(w in said.lower() for w in PERMISSION_WORDS)
                error = '%s stopped with status %s%s' % (plan.get('tool'), code, (': ' + said[-400:]) if said else '')
                outcome = 'could not capture'
            elif recorder.packets >= int(plan['packets']): outcome = 'reached {:,} packets'.format(int(plan['packets']))
            elif clock() - began >= int(plan['seconds']) - 1: outcome = 'reached %d seconds' % int(plan['seconds'])
            else: outcome = 'the capture tool finished'
    except watch.MalformedCapture as exc:
        state_name = 'Failed'; error = 'The capture tool sent damaged data: %s' % exc; outcome = 'could not read the capture'
    except Exception as exc:
        state_name = 'Failed'; error = ' '.join(str(exc).split())[:600] or type(exc).__name__; outcome = 'could not capture'
    finally:
        if proc is not None:
            try: end_process(proc)
            except Exception: pass
            for stream in (proc.stdout, proc.stderr):
                try:
                    if stream is not None: stream.close()
                except Exception: pass
        try: discarded = discarded or bool(kernel.record('jobs', ident).get('discard'))
        except Exception: pass
        try: recorder.close(discard=discarded)
        except OSError as exc:
            if state_name != 'Failed': state_name, error = 'Failed', 'The packet summaries could not be kept: %s' % exc

        def finish(row):
            capture = row.setdefault('capture', {})
            capture.update(ended=time.time(), outcome=outcome or state_name.lower(), permission=permission, signature=plan.get('signature'),
                           groups=sorted(os.getgroups()), damaged=bool(error and 'damaged' in error))
            if discarded: capture['discarded'] = capture.get('discarded') or time.time()
            row.update(state=state_name, finished=time.time(), error=error, current_operation='finished: ' + (outcome or state_name.lower()))
        try: note(finish)
        except Exception: pass


def dispatch(kernel, operation, args, principal):
    if operation == 'network.capture.start': return start(kernel, args, principal)
    if operation == 'network.capture.stop': return stop(kernel, args, principal)
    if operation == 'network.capture.read': return read(kernel, args, principal)
    raise ValueError('Unknown capture operation')
