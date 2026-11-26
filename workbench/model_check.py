"""Check her model on this machine: the model check kit (0.8.7, "Kas's mind with the model, interwoven"; slice A5, lane A).

One button in the Brain room (model_check_qt) and one command for the console:

    python -B -m workbench.model_check --model <file>            (or ./MODEL_CHECK.sh --model <file>)
    python -B -m workbench.model_check --model <file> --overnight    (and S7: the I05 arms and the full exam, on mains)
    python -B -m workbench.model_check --plan                         (the stages and their estimated times; starts nothing)

It uses Graphite's own launch path (brain.model.add and brain.model.use: prepare, the device probe, the memory rule,
the seal), fixed invented prompts with known answers, and an invented workspace of its own (a new Office under the run
folder, removed at the end). Nothing of the owner's is read except, if he allows it, his own paper, built by the Brain
room before the run and kept on this computer. It never changes a kernel setting, installs, downloads, or touches the
owner's workspace. Touching the desk pauses it (the Brain room puts a pause file in the run folder while the desk is in
use; a measurement the pause interrupted is taken again); it runs only on mains power (on battery it waits).

STAGES (design 6.1; the times are estimates, shown before it starts):
    S0  the machine, no model           Vulkan devices; the GPU's memory window (GTT) and VRAM and GTT in use; memory;
                                        power; kernel and Mesa; the model file's metadata (hybrid or not, the size of
                                        one checkpoint by the memory sum); the template digest; the memory rule. If the
                                        memory rule would refuse the load it stops here and names the setting to raise
                                        and by how much (nothing is changed)
    S1  first load and the seal         a first load (the disk cache dropped) and a warm load; resident and GTT memory
                                        against the computed budget; the seal (full on Vulkan, else the labelled
                                        fallback); the template's thinking switch; the model key
    S2  speeds                          reads of 300, 1,200 and 3,000 tokens; writes of 16, 64 and 256; batches of 64,
                                        256 and 512 (Vulkan only: each a fresh launch); 60 s of writing for heat; the
                                        grammar overhead (the same answer with and without its grammar)
    S2T tuning (1.0 M1)                 after S2's speeds, a sweep of the settings that matter on the Radeon (flash
                                        attention on and off; the KV cache f16, q8_0 and FP8; reading batches of 256,
                                        512 and 1,024; threads; full or partial offload on Vulkan; multi-token
                                        prediction and its draft length when the model file carries an MTP head), each
                                        a fresh launch, kept only when its answer is identical to the plain run's at
                                        temperature 0; the best against 'reads at 99 a second' and 'writes at 99 a
                                        second' (the owner's goal), how far off when not, and proposed with Undo; her
                                        clock starts from the measured rates; time-boxed (--tuning-seconds, 240)
    S3  reuse and Stop                  a kept choose turn: cache_n on second-round questions against the kept brief;
                                        one checkpoint's size measured by resident memory growth (the runtime does not
                                        log it at its default verbosity, and the seal forbids a verbose log); Stop
    S4  the desk                        stalls of the desk over 50 ms during a 3,000-token read (from the Brain room
                                        only: the room measures its own event loop and writes desk_stalls.json)
    S5  the short exam                  model_exam's papers, short form (twice on Vulkan: "agreed with itself on x of
                                        y"), plus the owner's own paper if he allowed it (results kept on this computer)
    SQ  optional: a quick model (1.0 M2) --quick FILE: a small model loaded beside hers through the same sealed start
                                        (both in the memory sum), both measured on her typical question, the small one's
                                        exam for the quick kinds (READ PLAN NEXT MARKS ASK) on its own key, and the split
                                        proposed: a kind for the quick model only where it passed and is faster
                                        (quick_model.pair_stage; its results reach the exam record from the Brain room)
    S6  optional                        another model (--also FILE): a read of 1,200 and a write of 64 (the 35B on the
                                        processor, or the 4B on the Radeon as plan B)
    S7  optional, overnight, on mains   the full exam, then the I05 arms through the shipped workbench.i05_arms --kit
                                        (the kit folder under tools is not shipped); the registration hash is checked
                                        before any arm runs

THE FILES (design 6.2): <run>/for-sending/model-check-<date>.json (graphite.model-check/1) and model-check-<date>.txt,
the card, under 50 KB. Numbers, pass and fail per stage (a stage that cannot run is "not run" with why), held or not per
prediction (K1 to K12), and the settings proposed. No path beyond the model's file name, no host or user name, no
workspace content, nothing from the owner's own paper but its count: privacy_scan() fails the run when any appears,
and then nothing is written for sending. Beside it, never for sending: exam_results.local.json (for the owner's
exam record) and own_results.local.json.

USE THE MEASURED SETTINGS? Each proposal is one owner launch default (ledger.settings: brain.backend and the rest),
applied only on his click (use_setting, through ledger.settings.set with the value he saw) and undone with Undo
(undo_setting, ledger.settings.undo: the exact previous record). What has no setting yet (loading the model when the
desk opens) is said as a finding with nothing to apply; 1.0 M1 made the reading batch and v1.0.0's capabilities settings. A proposal changes nothing until approved.

No floating point in anything checked: rates are whole tokens a second, times whole milliseconds, shares "x of y".
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

SCHEMA = 'graphite.model-check/1'
CARD_MOST = 50 * 1024
MIB = 1024 * 1024
GIB = 1024 * MIB
STAGES = (('S0', 'the machine, no model', 1, 1), ('S1', 'first load and the seal', 1, 3), ('S2', 'speeds', 6, 8),
          ('S2T', 'tuning: the settings that matter (1.0 M1)', 4, 5),
          ('S3', 'reuse and Stop', 2, 3), ('S4', 'the desk (from the Brain room)', 1, 1), ('S5', 'the short exam', 5, 10),
          ('SQ', 'optional: a quick model beside it (1.0 M2)', 4, 8),     # 1.0 M2: with --quick FILE
          ('S6', 'optional: another model', 3, 5), ('S7', 'optional, overnight, on mains: the full exam and the I05 arms', 60, 180))
AWAKE = ('S0', 'S1', 'S2', 'S2T', 'S3', 'S4', 'S5')
# 1.0 M1: the owner's machine is a ThinkPad E16 Gen 2 AMD (21M5) with a Radeon 680M (RDNA2), not a 780M: K3 expects the
# 680M's reading; K13 and K14 are the owner's goal, the best of the tuning stage (S2T), else S2's.
PREDICTIONS = {
    'K1': 'the GTT window is at least 28 GiB',
    'K2': 'first load 20 to 60 s; a warm load 8 to 25 s',
    'K3': 'a 1,200-token read at 100 to 300 tokens a second (the Radeon 680M)',
    'K4': 'writing 15 to 25 a second, at least 12 after 60 s of heat',
    'K5': 'batch 512 reads at least twice as fast as 64 on Vulkan',
    'K6': 'a kept choose turn under 1.6 s, every second-round cache_n at least the brief minus 4',
    'K7': 'one checkpoint 55 to 75 MiB, if the model is a hybrid',
    'K8': 'Stop answers within 2 s',
    'K9': 'the full seal works on Vulkan',
    'K10': 'the short exam: READ at least 22 of 24 single-step, CHOOSE clear cases right on turn 1 at least 7 of 8, STEER harm 0',
    'K11': 'no desk stall over 50 ms during a 3,000-token read',
    'K12': 'grammar overhead at most 15 % of the writing rate',
    'K13': 'reads at >= 99 tokens a second',
    'K14': 'writes at >= 99 tokens a second',
}
CONTENDED = 150                      # load average x 100 above which a stage's rates are marked contended (design 7.4)
FILLER = ('The Rail Demo bench supply gives twelve volts to the cable tray rail; its notes list the fuse, the connector and '
          'the length of each run. The Home Demo statement for November lists the rent, the water and the heating, each '
          'with its date. ')


# == plan, power, pause ==============================================================================================
def plan(overnight=False, also=False, quick=False):
    rows = [s for s in STAGES if s[0] in AWAKE or (s[0] == 'S6' and also) or (s[0] == 'S7' and overnight)
            or (s[0] == 'SQ' and quick)]      # 1.0 M2: the quick model beside it, when one is named
    return rows


def plan_text(overnight=False, also=False, quick=False):
    lines = ['Check her model on this machine: the stages and their estimated times.']
    for key, words, lo, hi in plan(overnight, also, quick):
        lines.append('  %s  %-62s %s' % (key, words, '%d min' % lo if lo == hi else '%d to %d min' % (lo, hi) if hi < 60 else
                                          '%d to %d h' % (lo // 60, hi // 60)))
    lines.append('The awake part, S0 to S5, takes about 20 to 30 minutes (estimated).')
    lines.append('It uses an invented workspace of its own; it never changes a kernel setting, installs, downloads or touches '
                 'your workspace. Touching the desk pauses it; it runs only on mains power.')
    return '\n'.join(lines)


def _read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def power(root='/sys/class/power_supply'):
    """{'on_mains': True, False or None (unknown), 'battery': bool}. A computer with no battery is on mains."""
    mains = None;battery = False;charging = None
    for d in sorted(Path(root).glob('*')) if Path(root).is_dir() else []:
        kind = _read(d / 'type')
        if kind == 'Mains':mains = bool(mains) or _read(d / 'online') == '1'
        elif kind == 'Battery':
            battery = True;status = _read(d / 'status')
            if status:charging = (charging or False) or status in ('Charging', 'Full', 'Not charging')
    if mains is None:mains = charging if battery else True
    return {'on_mains': mains, 'battery': battery}


class Gate:
    """Waits before each measurement while the desk is in use (the pause file) or the computer is on battery."""

    def __init__(self, pause_file=None, mains_only=True, say=print, sleep=time.sleep, power_of=power):
        self.pause_file = Path(pause_file) if pause_file else None;self.mains_only = mains_only
        self.say = say;self.sleep = sleep;self.power_of = power_of;self.paused_ms = 0;self.pauses = 0

    def why(self):
        if self.pause_file is not None and self.pause_file.exists():return 'the desk is in use'
        if self.mains_only and self.power_of()['on_mains'] is False:return 'the computer is on battery'
        return None

    def wait(self):
        why = self.why()
        if why is None:return 0
        began = time.monotonic();self.pauses += 1
        self.say('Paused: %s. I carry on when it is not.' % why)
        while self.why() is not None:self.sleep(5)
        waited = int((time.monotonic() - began) * 1000);self.paused_ms += waited
        return waited

    def measure(self, fn):
        """fn() between pauses; taken again once if a pause began while it ran. (value, disturbed)."""
        for attempt in (1, 2):
            self.wait();before = self.pauses
            value = fn()
            if self.why() is None and self.pauses == before:return value, False
        return value, True


# == the privacy scan ================================================================================================
PATH_LIKE = re.compile(r'(?:[A-Za-z]:\\[^\s"\']+|~[/\\][^\s"\']*|(?<![\w.:/-])/(?:[\w.@+-]+/)+[\w.@+-]*)')


def _identities():
    names = set();hosts = set()
    for get in (getpass.getuser, lambda: os.environ.get('USER'), lambda: os.environ.get('LOGNAME'),
                lambda: Path.home().name):
        try:
            v = get()
        except Exception:  # noqa: BLE001
            v = None
        if v and len(v) >= 2:names.add(v)
    for get in (socket.gethostname, platform.node, socket.getfqdn):
        try:
            v = get()
        except Exception:  # noqa: BLE001
            v = None
        if v and len(v) >= 2 and v not in ('localhost', 'localhost.localdomain'):hosts.add(v);hosts.add(v.split('.')[0])
    return names, hosts


def privacy_scan(text, *, model_name='', users=None, hosts=None, workspace=(), canaries=()):
    """What must not leave in `text`: a path (beyond the model's file name), a user name, a host name, the workspace, or
    a canary (the owner's own paper, his character file). Returns the findings, each with what was found and a masked
    excerpt; an empty list passes."""
    if users is None or hosts is None:
        found_users, found_hosts = _identities()
        users = found_users if users is None else users;hosts = found_hosts if hosts is None else hosts
    out = []
    for m in PATH_LIKE.finditer(text):
        out.append({'what': 'a path', 'at': m.group(0)[:3] + '...'})
    for kind, values in (('a user name', users), ('a host name', hosts)):
        for v in sorted(set(values or ()), key=len, reverse=True):
            if v and v != model_name and re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(v), text):
                out.append({'what': kind, 'at': v[:1] + '...'})
    for w in workspace or ():
        if w and str(w) in text:out.append({'what': 'the workspace', 'at': str(w)[:1] + '...'})
    for c in canaries or ():
        if c and c in text:out.append({'what': 'your own words', 'at': c[:1] + '...'})
    try:
        from . import voice_character
        if voice_character.private_in([model_name]):out.append({'what': 'a character file name', 'at': '...'})
    except ImportError:
        pass
    return out


# == the invented workspace ==========================================================================================
class Work:
    """A new Office of the kit's own, under the run folder; Graphite's own Kernel and launch path on it."""

    def __init__(self, base):
        self.base = Path(base);self.stack = contextlib.ExitStack();self.kernel = None;self.p = None

    def __enter__(self):
        from unittest.mock import patch
        from . import locations
        from .baseline import environment
        self.base.mkdir(parents=True, exist_ok=False)
        home = self.base / 'Home';home.mkdir();root = self.base / 'Office';profile = self.base / 'profile'
        self.stack.enter_context(patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home)}))
        self.stack.enter_context(patch.object(Path, 'home', return_value=home))
        from .engineering_kernel import Kernel, operator
        locations.office(root);self.kernel = Kernel(root);self.p = operator()
        return self

    def __exit__(self, *exc):
        try:
            self.stop()
        finally:
            self.stack.close()
            shutil.rmtree(self.base, ignore_errors=True)
        return False

    def invoke(self, op, args):
        from .problem_checks import invoke
        return invoke(self.kernel, op, args, self.p)

    def wait(self, job, seconds=600):
        until = time.monotonic() + seconds
        while self.kernel.record('jobs', job['id'])['state'] in ('Queued', 'Running') and time.monotonic() < until:time.sleep(0.2)
        result = self.invoke('brain.result', {'id': job['id']})
        if result['state'] != 'Completed':
            raise ValueError(_code(str((result.get('error') or {}).get('message') if isinstance(result.get('error'), dict)
                                       else result.get('error') or result.get('state'))))
        return result['result']

    def add(self, model):
        return self.wait(self.invoke('brain.model.add', {'path': str(Path(model).resolve()), 'managed_copy': False,
                                                         'origin': 'The model file named for the model check.'}))

    def use(self, model_id, options):
        began = time.monotonic()
        value = self.wait(self.invoke('brain.model.use', {'id': model_id, 'options': options}))
        return value, int((time.monotonic() - began) * 1000)

    def worker(self):
        from . import local_brain
        return local_brain.get(self.kernel, 'worker', {})

    def value(self, model_id):
        from . import local_brain
        return local_brain.model(self.kernel, model_id)

    def stop(self):
        if self.kernel is None:return
        from . import local_brain
        try:
            if local_brain.worker_live(self.worker()):local_brain.stop(self.kernel, 'MODEL_CHECK_FINISHED')
        except Exception:  # noqa: BLE001
            pass


def _code(text):
    """A reason without a path: the code before the first colon, or the text with paths masked."""
    text = str(text or '')
    head = text.split(':', 1)[0].strip()
    if re.fullmatch(r'[A-Z][A-Z0-9_]{3,}', head):return head + (': ' + PATH_LIKE.sub('<path>', text.split(':', 1)[1].strip())[:200]
                                                              if ':' in text else '')
    return PATH_LIKE.sub('<path>', text)[:240]


def _drop_cache(model):
    if hasattr(os, 'posix_fadvise'):
        with Path(model).open('rb') as stream:os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)


# == measurements ====================================================================================================
def _rate(n, ms):
    return int(n) * 1000 // int(ms) if n and ms else None


def _ms(t):
    return int(t) if isinstance(t, (int, float)) else None


def _loadavg():
    try:
        return int(float(Path('/proc/loadavg').read_text().split()[0]) * 100)
    except (OSError, ValueError, IndexError):
        return None


def amdgpu():
    """The Radeon's memory window and use, from the kernel's own files (no serial, no owner data)."""
    cards = []
    for dev in sorted(Path('/sys/class/drm').glob('card[0-9]*/device')):
        total = _read(dev / 'mem_info_gtt_total')
        if total is None:continue
        def n(name):
            v = _read(dev / name)
            return int(v) if v and v.isdigit() else None
        cards.append({'gtt_total': n('mem_info_gtt_total'), 'gtt_used': n('mem_info_gtt_used'), 'vram_total': n('mem_info_vram_total'),
                      'vram_used': n('mem_info_vram_used'), 'vendor': _read(dev / 'vendor')})
    return cards


def _gtt_used():
    return sum(c['gtt_used'] or 0 for c in amdgpu()) or None


def text_messages(port, target, nonce):
    """Invented messages of about `target` prompt tokens, unique by nonce (so nothing kept is re-used)."""
    def build(words):
        body = (FILLER * (words // len(FILLER.split()) + 1)).split()[:max(1, words)]
        return [{'role': 'system', 'content': 'Model check read %s. Answer with one word.' % nonce},
                {'role': 'user', 'content': ' '.join(body) + '\nSay done.'}]
    words = max(8, target * 3 // 4)
    m = build(words);n = port.count(m)
    if n and abs(n - target) * 20 > target:
        words = max(8, words * target // n);m = build(words)
    return m


def write_messages(nonce):
    return [{'role': 'system', 'content': 'Model check write %s.' % nonce},
            {'role': 'user', 'content': 'Write the whole numbers from 1 to 2000 in order, separated by single spaces. Write nothing else.'}]


def _complete(port, messages, answer_tokens, grammar=None, cancelled=None):
    return port.complete(messages, answer_tokens=answer_tokens, grammar=grammar, deadline_ms=0, cancelled=cancelled)


def read_speed(port, target, nonce):
    got = _complete(port, text_messages(port, target, nonce), 1)
    t = got.get('timings') or {}
    return {'tokens': t.get('prompt_n'), 'ms': _ms(t.get('prompt_ms')), 'per_second': _rate(t.get('prompt_n'), t.get('prompt_ms'))}


def write_speed(port, tokens, nonce, grammar=None):
    got = _complete(port, write_messages(nonce), tokens, grammar)
    t = got.get('timings') or {}
    return {'tokens': t.get('predicted_n'), 'ms': _ms(t.get('predicted_ms')),
            'per_second': _rate(t.get('predicted_n'), t.get('predicted_ms'))}


# == the stages ======================================================================================================
class Check:
    def __init__(self, args, say=print, progress=None):
        self.args = args;self.say = say;self.progress = progress or (lambda **kw: None)
        self.run = Path(args.out);self.report = None;self.gate = Gate(args.pause_file or self.run / 'pause', not args.allow_battery, say)
        self.model = Path(args.model) if args.model else None
        self.value = None;self.model_id = None;self.port = None;self.key = None;self.results_local = []

    # -- helpers --
    def stage(self, key, fn):
        began = time.monotonic();load = _loadavg()
        self.progress(stage=key, event='begins');self.say('%s · %s' % (key, dict((s[0], s[1]) for s in STAGES)[key]))
        try:
            got = fn()
        except Exception as exc:  # noqa: BLE001 - a stage that breaks is FAILED with its reason (no path), and the run goes on
            got = {'state': 'FAILED', 'why': _code(str(exc) or type(exc).__name__)}
        got.setdefault('state', 'PASSED')
        got['seconds'] = int(time.monotonic() - began);got['load_average_x100'] = load
        if load is not None and load > CONTENDED and got['state'] != 'NOT_RUN':got['contended'] = True
        self.report['stages'][key] = got
        self.progress(stage=key, event='ends', state=got['state'])
        self.say('   %s%s' % (got['state'].lower().replace('_', ' '), (': ' + got['why']) if got.get('why') else ''))
        return got

    def options(self, **extra):
        a = self.args
        out = {'context': a.context, 'threads': a.threads, 'backend': a.backend}
        if a.memory_mb:out['memory_mb'] = a.memory_mb
        out.update(extra)
        return out

    def live_port(self):
        from . import turns
        self.port = turns.LocalPort(self.work.worker(), self.work.kernel)
        return self.port

    # -- S0 --
    def s0(self):
        from . import brain_runtime, local_brain
        from .inference_hardware import snapshot
        from .resource_control import memory_shape, memory_sum, reclaimable, reserve_setting
        hw = snapshot();host = brain_runtime.host(profile=False)
        probe = brain_runtime.probe(self.work.kernel.root)
        cards = amdgpu()
        installed = hw.get('installed_packages') or {}
        mesa = installed.get('mesa-vulkan-drivers') if isinstance(installed, dict) else None
        registered = self.work.add(self.model);self.model_id = registered['model_id'];self.value = self.work.value(self.model_id)
        inspection = self.value['inspection'];shape = memory_shape(inspection)
        one = memory_sum(inspection, self.value['total_bytes'], self.args.context, 1, 0)
        from .runtime_tuning import OWNER_MACHINE
        runtime = brain_runtime.status(self.work.kernel.root)
        product = (hw.get('machine') or {}).get('product')
        out = {'expected': {**{k: OWNER_MACHINE[k] for k in ('model', 'machine_type', 'graphics', 'memory')},   # 1.0 M1
                            'this_is_it': bool(product and OWNER_MACHINE['machine_type'] in str(product))},
               'runtime': {'build': runtime.get('build'), 'source_commit': runtime.get('source_commit'),
                           'release': (runtime.get('pin') or {}).get('stable_release')},
               'machine': {'cpu': hw['cpu']['name'], 'logical_cpus': hw['cpu']['logical_cpus'], 'kernel': hw['kernel'],
                           'architecture': hw['architecture'], 'product': (hw.get('machine') or {}).get('product'),
                           'memory_total_bytes': host['total_ram_bytes'], 'memory_available_bytes': host['available_ram_bytes'],
                           'mesa': mesa, 'power': power()},
               'vulkan': {'state': probe.get('state'), 'devices': [d.get('name') for d in probe.get('devices') or []],
                          'seal_view': probe.get('network_seal'), 'reason': _code(probe.get('reason')) if probe.get('reason') else None},
               'gpu_memory': cards,
               'model': {'file': self.model.name, 'bytes': self.value['total_bytes'], 'file_set_id': self.model_id,
                         'architecture': inspection.get('architecture'), 'memory_shape': shape['kind'],
                         'checkpoint_bytes_computed': one.get('state') if shape['kind'] != 'DENSE' else None,
                         'template_sha256': hashlib.sha256(str(self.value.get('message_template') or '').encode()).hexdigest()}}
        self.report['model'] = out['model']
        try:
            config = local_brain.configuration(self.value, self.options(), self.work.kernel.root, reclaimable(self.work.kernel),
                                               reserve_setting(self.work.kernel))
        except ValueError as exc:
            out.update(state='FAILED', why=_code(str(exc)), stop=True, setting=self.setting_to_raise(str(exc)))
            return out
        out['memory_rule'] = {'backend': config['backend'], 'memory_mb': config['memory_mb'],
                              'estimate_bytes': config['estimated_peak_bytes'], 'checkpoints': config.get('checkpoints'),
                              'prompt_cache_mb': config.get('prompt_cache_mb')}
        from . import brain_cap      # 1.0 M1b: what the cap gives her, before loading, with the numbers
        cap = brain_cap.plan(self.value, self.options(), self.work.kernel.root, reclaimable(self.work.kernel), reserve_setting(self.work.kernel))
        out['memory_rule']['cap'] = {k: cap.get(k) for k in ('state', 'address_space_mb', 'full_mb', 'least_mb', 'room_mb')}
        if cap.get('words'):self.say('   ' + cap['words'])
        gtt = max((c['gtt_total'] or 0 for c in cards), default=0)
        if gtt and config['estimated_peak_bytes'] > gtt:
            out['gtt_short'] = {'need_mib': -(-config['estimated_peak_bytes'] // MIB), 'window_mib': gtt // MIB,
                                'words': ("The GPU's memory window is %s MiB; the model needs %s MiB there. The kernel setting that "
                                          "sets it is the amdgpu GTT size (amdgpu.gttsize, or ttm.pages_limit); it would need "
                                          "%s MiB more. I changed nothing." % ('{:,}'.format(gtt // MIB),
                                          '{:,}'.format(-(-config['estimated_peak_bytes'] // MIB)),
                                          '{:,}'.format(-(-(config['estimated_peak_bytes'] - gtt) // MIB))))}
        return out

    @staticmethod
    def setting_to_raise(message):
        nums = [int(n.replace(',', '')) for n in re.findall(r'(\d[\d,]*) MiB', message)]
        if 'MODEL_MEMORY_BUDGET_TOO_SMALL' in message and len(nums) >= 2:
            return {'setting': 'the memory cap (brain.memory_mb, "Host budget (MiB)")', 'by_mib': max(0, nums[1] - nums[0])}
        if 'AVAILABLE' in message and len(nums) >= 2:
            return {'setting': 'memory free for the model: close other Apps, or lower the foreground reserve', 'by_mib': max(0, nums[-2] - nums[-1])}
        return {'setting': 'see the reason', 'by_mib': None}

    # -- S1 --
    def s1(self):
        from . import local_brain, model_exam
        before = _gtt_used()
        _drop_cache(self.model)
        first, first_ms = self.work.use(self.model_id, self.options())
        worker = self.work.worker();cfg = worker.get('config') or {}
        out = {'backend': worker.get('backend'), 'requested_backend': self.args.backend, 'fallback_reason': _code(cfg.get('fallback_reason')) if cfg.get('fallback_reason') else None,
               'first_load_ms': int((worker.get('load_seconds') or 0) * 1000), 'first_activation_ms': first_ms,
               'estimate_bytes': cfg.get('estimated_peak_bytes'), 'memory_mb': cfg.get('memory_mb'),
               'resident_bytes': local_brain.usage(worker).get('rss_bytes'), 'gtt_used_before': before, 'gtt_used_after': _gtt_used(),
               'observed_gpu_layers': worker.get('observed_gpu_layers')}
        seal = worker.get('seal') or {}
        out['seal'] = {k: seal.get(k) for k in ('state', 'network', 'network_reason', 'transport', 'backend')}
        held = model_exam.key_for(worker);self.key = held['key']
        out['template_thinking'] = held['template'].get('thinking');out['model_key'] = held['key']
        self.report['model_key'] = held['key']
        local_brain.stop(self.work.kernel, 'MODEL_CHECK_WARM_LOAD')
        second, second_ms = self.work.use(self.model_id, self.options())
        worker = self.work.worker()
        out['warm_load_ms'] = int((worker.get('load_seconds') or 0) * 1000);out['warm_activation_ms'] = second_ms
        if self.key != model_exam.key_for(worker)['key']:out['key_changed_on_reload'] = True
        self.live_port()
        return out

    # -- S2 --
    def s2(self):
        out = {'reads': {}, 'writes': {}, 'batches': {}, 'heat': None, 'grammar': None}
        port = self.port
        for n in (300, 1200, 3000):
            out['reads'][str(n)], d = self.gate.measure(lambda n=n: read_speed(port, n, 'r%d-%d' % (n, time.time_ns())))
            if d:out['reads'][str(n)]['disturbed'] = True
        for n in (16, 64, 256):
            out['writes'][str(n)], d = self.gate.measure(lambda n=n: write_speed(port, n, 'w%d-%d' % (n, time.time_ns())))
        # heat: 60 s of writing
        def heat():
            began = time.monotonic();rows = []
            while time.monotonic() - began < 60:rows.append(write_speed(port, 256, 'h%d' % time.time_ns()))
            return {'first': rows[0]['per_second'], 'last': rows[-1]['per_second'], 'runs': len(rows),
                    'seconds': int(time.monotonic() - began)}
        out['heat'], _ = self.gate.measure(heat)
        # grammar overhead: the same answer with and without its grammar
        from . import grammars
        target = ' '.join(str(i) for i in range(1, 41))
        def overhead():
            free = write_speed(port, 160, 'g-free-%d' % time.time_ns())
            bound = write_speed(port, 160, 'g-bound-%d' % time.time_ns(), grammars.one_of([target]))
            pct = (free['per_second'] - bound['per_second']) * 100 // free['per_second'] if free['per_second'] and bound['per_second'] else None
            return {'without': free, 'with': bound, 'overhead_percent': pct}
        out['grammar'], _ = self.gate.measure(overhead)
        # batches: Vulkan only, each a fresh launch with the batch asked for
        if self.work.worker().get('backend') == 'VULKAN':
            from . import local_brain
            for b in (64, 256, 512):
                local_brain.stop(self.work.kernel, 'MODEL_CHECK_BATCH')
                self.work.use(self.model_id, self.options(batch=b));self.live_port()
                out['batches'][str(b)], _ = self.gate.measure(lambda b=b: read_speed(self.port, 1200, 'b%d-%d' % (b, time.time_ns())))
            local_brain.stop(self.work.kernel, 'MODEL_CHECK_BATCH')
            self.work.use(self.model_id, self.options());self.live_port()
        else:
            out['batches'] = {'state': 'NOT_RUN', 'why': 'batches are measured on the Radeon (Vulkan) only; this run is on the processor'}
        return out

    # -- S2T (1.0 M1) --
    def s2t(self):
        from . import runtime_tuning, tuning_rates
        try:
            out = runtime_tuning.sweep(self, int(getattr(self.args, 'tuning_seconds', 0) or runtime_tuning.SWEEP_SECONDS))
        finally:      # 1.0 M1b: its rates, out of this run's throwaway profile and beside the run, for her clock
            carried = tuning_rates.carry_out(self.run)
        out['rates_carried'] = carried
        return out

    # -- S3 --
    def s3(self):
        from . import brain_briefs, local_brain, turns
        kind = kit_kind();port = self.port
        out = {}
        primed = brain_briefs.prime_all(port, [kind])
        out['prime'] = [{k: r.get(k) for k in ('brief_tokens', 'prompt_n', 'cache_n', 'elapsed_ms')} for r in primed.get('primed') or []]
        ledger = turns.MemoryLedger()
        request = turns.TurnRequest(port=port, ledger=ledger, clock=turns.FixedClock(), switches={n: True for n in turns.SWITCHES},
                                    owner='check', foreground_turns=10, budget_ms=600000)
        turns_ = []
        for q, things in KIT_QUESTIONS:
            self.gate.wait()
            a = turns.ask(kind, {'things': things, 'question': q}, request)
            row = ledger.rows[a.turn] if a.turn in ledger.rows else {}
            tim = row.get('timings') or {};reuse = row.get('reuse') or {}
            turns_.append({'outcome': a.outcome, 'right': a.value == KIT_RIGHT[q], 'elapsed_ms': a.elapsed_ms,
                           'cache_n': tim.get('cache_n'), 'expected': reuse.get('expected'), 'prompt_n': tim.get('prompt_n')})
        out['turns'] = turns_
        second = turns_[1:]
        out['second_round_kept'] = all(isinstance(t['cache_n'], int) and isinstance(t['expected'], int) and t['cache_n'] >= t['expected'] - 4
                                       for t in second) if second else None
        times = sorted(t['elapsed_ms'] for t in second if isinstance(t['elapsed_ms'], int))
        out['kept_turn_ms'] = times[len(times) // 2] if times else None
        out['four_kind_slots'] = {'state': 'NOT_RUN', 'why': 'this release launches one slot; the four-kind-slot arm is a launch '
                                  'line Graphite does not make (design 6.4: tried only if reuse misses)'}
        out['checkpoint'] = self.checkpoint_growth()
        out['stop'] = self.stop_latency()
        return out

    def checkpoint_growth(self):
        """One checkpoint's size by resident memory growth: a long prompt read once (its pages touched), then four
        questions each extending the one before, so each adds one checkpoint and nothing else is cached."""
        from . import local_brain
        worker = self.work.worker();reuse = worker.get('reuse') or {}
        computed = (self.report.get('model') or {}).get('checkpoint_bytes_computed')
        if not reuse.get('checkpoints'):
            return {'state': 'NOT_RUN', 'why': 'this launch keeps no checkpoints (a dense model, or the memory rule chose reuse off)',
                    'computed_bytes': computed}
        port = self.port;nonce = 'c%d' % time.time_ns()
        base = text_messages(port, 1500, nonce)
        _complete(port, base, 1)
        rss = [local_brain.usage(worker).get('rss_bytes')]
        messages = [dict(m) for m in base]
        made = min(4, int(reuse['checkpoints']))
        for i in range(made):
            messages = messages + [{'role': 'assistant', 'content': 'done'}, {'role': 'user', 'content': 'And again, part %d. Say done.' % (i + 2)}]
            _complete(port, messages, 1)
            rss.append(local_brain.usage(worker).get('rss_bytes'))
        if None in rss:return {'state': 'NOT_RUN', 'why': 'resident memory is not readable here', 'computed_bytes': computed}
        growth = rss[-1] - rss[0]
        # The runtime does not log a checkpoint at its default verbosity (and the seal forbids a verbose log), so the
        # growth is counted in whole checkpoints of the computed size, and the size is that growth over that count;
        # the residual says how far the growth is from a whole number of them.
        count = max(1, (2 * growth + (computed or growth)) // (2 * (computed or growth))) if growth > 0 else 0
        per = growth // count if count else None
        residual = abs(growth - count * computed) * 100 // growth if computed and count and growth else None
        return {'method': 'resident memory growth of the worker over %d extending questions, counted in whole checkpoints of '
                          'the computed size' % made, 'growth_bytes': growth, 'checkpoints_counted': count,
                'per_checkpoint_bytes': per, 'residual_percent': residual, 'computed_bytes': computed,
                'steps_bytes': [b - a for a, b in zip(rss, rss[1:])],
                'note': 'an estimate, not an independent measure: the RAM prompt cache and the allocator also move resident memory'}

    def stop_latency(self):
        from . import turns
        port = self.port;flag = {'stop': False};seen = {}
        def go():
            try:
                _complete(port, write_messages('s%d' % time.time_ns()), 1024, cancelled=lambda: flag['stop'])
                seen['code'] = 'FINISHED'
            except turns.PortError as exc:
                seen['code'] = exc.code
            except turns.Late:
                seen['code'] = 'LATE'
            seen['end'] = time.monotonic()
        th = threading.Thread(target=go, daemon=True);th.start();time.sleep(2.5)
        t0 = time.monotonic();flag['stop'] = True;th.join(60)
        stop_ms = int((seen['end'] - t0) * 1000) if 'end' in seen else None
        t1 = time.monotonic();again = _complete(port, [{'role': 'user', 'content': 'Say ok.'}], 2)
        return {'stopped': seen.get('code'), 'stop_ms': max(0, stop_ms) if stop_ms is not None else None,
                'answers_again_ms': int((time.monotonic() - t1) * 1000), 'answered': bool(again.get('text') is not None)}

    # -- S4 --
    def s4(self):
        stalls = self.run / 'desk_stalls.json'
        if not self.args.from_room:
            return {'state': 'NOT_RUN', 'why': 'from the Brain room only: the console has no desk to watch'}
        stalls.unlink(missing_ok=True)
        self.progress(stage='S4', event='desk_read_begins')
        read = read_speed(self.port, 3000, 'd%d' % time.time_ns())
        self.progress(stage='S4', event='desk_read_ends')
        until = time.monotonic() + 10
        while not stalls.exists() and time.monotonic() < until:time.sleep(0.2)
        if not stalls.exists():return {'state': 'NOT_RUN', 'why': 'the Brain room did not report its stalls', 'read': read}
        got = json.loads(stalls.read_text(encoding='utf-8'))
        return {'read': read, 'longest_stall_ms': got.get('longest_ms'), 'stalls_over_50ms': got.get('over_50')}

    # -- S5 --
    def s5(self):
        from . import model_exam, turns
        papers, refused = model_exam.load_papers()
        own = None
        if self.args.own_items:
            items = json.loads(Path(self.args.own_items).read_text(encoding='utf-8'))
            own = model_exam.Paper(model_exam.OWN, None, {'schema': model_exam.SCHEMA_PAPER, 'paper': model_exam.OWN, 'version': 1,
                                   'kinds': sorted({i['kind'] for i in items}) or ['GOAL'], 'harm_rule': 'none'}, items, local=True)
            self.canaries = [json.dumps(i.get('inputs'), ensure_ascii=False)[:200] for i in items] + \
                [str(i.get('id')) for i in items]
        if not papers and own is None:
            return {'state': 'NOT_RUN', 'why': 'no exam papers in this build', 'refused': refused}
        clock = turns.default_clock(self.work.kernel)
        sitting = papers + ([own] if own else [])
        first = model_exam.sit(sitting, self.port, short=True, clock=clock, paused=self.gate.wait)
        out = {'papers': [p.ident for p in papers], 'refused': refused, 'exam_version': model_exam.exam_version(papers)}
        agreed = None
        if self.work.worker().get('backend') == 'VULKAN':
            second = model_exam.sit(papers, self.port, short=True, clock=clock, paused=self.gate.wait)
            agreed = model_exam.agreement(first, second)
        store = model_exam.MemoryStore()
        kinds = model_exam.record(store, self.key, model_exam.exportable(first))
        summary = model_exam.summarise(first)
        out.update(summary=summary, kinds=kinds, agreed='%d of %d' % agreed if agreed else None,
                   card=model_exam.card(summary, kinds, agreed), own_paper='asked %d' % summary.get(model_exam.OWN, {}).get('asked', 0)
                   if own else ('not asked' if not self.args.own_items else 'none'))
        self.results_local = first
        if not papers:out.update(state='NOT_RUN', why='only your own paper; no exam papers in this build')
        return out

    # -- SQ (1.0 M2) --
    def sq(self):
        """The quick model beside hers (--quick FILE): both measured on her typical question, the quick model's exam for the
        quick kinds on its own key, and the split proposed (quick_model.pair_stage). It is stopped at the end with hers."""
        from . import quick_model
        return quick_model.pair_stage(self)

    # -- S6 --
    def s6(self):
        if not self.args.also:return {'state': 'NOT_RUN', 'why': 'optional, and not asked (--also FILE)'}
        from . import local_brain
        local_brain.stop(self.work.kernel, 'MODEL_CHECK_OTHER_MODEL')
        other = self.work.add(self.args.also)
        options = self.options(backend=self.args.also_backend)
        _, ms = self.work.use(other['model_id'], options)
        port = self.live_port();worker = self.work.worker()
        out = {'file': Path(self.args.also).name, 'backend': worker.get('backend'), 'load_ms': int((worker.get('load_seconds') or 0) * 1000),
               'read_1200': read_speed(port, 1200, 'o%d' % time.time_ns()), 'write_64': write_speed(port, 64, 'o%d' % time.time_ns())}
        local_brain.stop(self.work.kernel, 'MODEL_CHECK_OTHER_MODEL_DONE')
        self.work.use(self.model_id, self.options());self.live_port()
        return out

    # -- S7 --
    def s7(self):
        if not self.args.overnight:return {'state': 'NOT_RUN', 'why': 'optional, overnight, and not asked (--overnight)'}
        if power()['on_mains'] is False:return {'state': 'NOT_RUN', 'why': 'on battery: the overnight part runs on mains only'}
        from . import i05_arms, local_brain, model_exam, turns
        out = {}
        papers, refused = model_exam.load_papers(sealed=False)
        if papers:
            full = model_exam.sit(papers, self.port, short=False, clock=turns.default_clock(self.work.kernel), paused=self.gate.wait)
            self.results_local = self.results_local + full
            out['full_exam'] = model_exam.summarise(full)
        else:
            out['full_exam'] = {'state': 'NOT_RUN', 'why': 'no exam papers in this build'}
        out['i05_registration'] = i05_arms.check_registration()
        local_brain.stop(self.work.kernel, 'MODEL_CHECK_OVERNIGHT')
        folder = self.run / 'overnight' / 'i05'
        cmd = [sys.executable, '-B', '-m', 'workbench.i05_arms', '--kit', '--model', str(self.model.resolve()), '--out', str(folder),
               '--repeats', str(self.args.i05_repeats), '--pause-file', str(self.gate.pause_file), '--mains-only']
        root = Path(__file__).resolve().parent.parent
        with (self.run / 'overnight' / 'i05.log').open('w', encoding='utf-8') as log:
            done = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        summary = folder / 'summary.json'
        out['i05'] = json.loads(summary.read_text(encoding='utf-8')) if summary.exists() else {'state': 'FAILED', 'exit': done.returncode}
        shutil.rmtree(folder / 'keep', ignore_errors=True)
        return out

    # -- the whole run --
    def go(self):
        from .version import VERSION
        self.run.mkdir(parents=True, exist_ok=True)
        if any(self.run.glob('for-sending/model-check-*.json')):raise SystemExit('This run folder has a report already; give a new one.')
        if not self.model or not self.model.is_file():raise SystemExit('--model must name an existing model file')
        if not self.args.allow_battery and power()['on_mains'] is False:
            raise SystemExit('The model check runs on mains power only. Plug the computer in and start it again.')
        self.say(plan_text(self.args.overnight, bool(self.args.also), bool(getattr(self.args, 'quick', None))))   # 1.0 M2: and SQ
        self.canaries = []
        today = datetime.date.today().isoformat()
        self.report = {'schema': SCHEMA, 'graphite': VERSION, 'date': today, 'stages': {}, 'model': {'file': self.model.name},
                       'predictions': {}, 'proposals': [], 'findings': [], 'not_tested_here': 'A model check, not a test.'}
        with Work(self.run / '.work') as self.work:
            s0 = self.stage('S0', self.s0)
            if s0.get('stop') or s0['state'] == 'FAILED':
                for key in ('S1', 'S2', 'S2T', 'S3', 'S4', 'S5', 'SQ', 'S6', 'S7'):     # 1.0 M2: SQ
                    self.report['stages'][key] = {'state': 'NOT_RUN', 'why': 'S0 stopped the run: ' + (s0.get('why') or '')}
            else:
                s1 = self.stage('S1', self.s1)
                if s1['state'] != 'PASSED':
                    for key in ('S2', 'S2T', 'S3', 'S4', 'S5', 'SQ', 'S6', 'S7'):     # 1.0 M2: SQ
                        self.report['stages'][key] = {'state': 'NOT_RUN', 'why': 'the model did not load: ' + (s1.get('why') or '')}
                else:
                    wanted = set((self.args.stages or ','.join(k for k, *_ in STAGES)).split(','))
                    for key, fn in (('S2', self.s2), ('S2T', self.s2t), ('S3', self.s3), ('S4', self.s4), ('S5', self.s5),
                                    ('SQ', self.sq), ('S6', self.s6), ('S7', self.s7)):     # 1.0 M2: SQ, the quick model beside it
                        if key in wanted:self.stage(key, fn)
                        else:self.report['stages'][key] = {'state': 'NOT_RUN', 'why': 'not asked in this run (--stages)'}
            from . import tuning_rates      # 1.0 M1b: every rate this run measured (the pair's too), carried out before its
            tuning_rates.carry_out(self.run)     # profile is removed with its workspace
        kept = tuning_rates.keep(self.run)      # 1.0 M1b: and kept in this computer's profile for her clock, console runs too
        if kept and kept.get('kept'):self.say(tuning_rates.words(kept))
        self.report['paused_ms'] = self.gate.paused_ms
        judge(self.report)
        return self.write()

    def write(self):
        report = self.report;card_text = card(report)
        blob = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
        found = privacy_scan(blob + '\n' + card_text, model_name=self.model.name, workspace=[str(self.run.resolve())],
                             canaries=getattr(self, 'canaries', []))
        if self.results_local:
            local = [r for r in self.results_local if not r.get('local')]
            (self.run / 'exam_results.local.json').write_text(json.dumps({'key': self.key, 'results': local}, indent=1) + '\n', encoding='utf-8')
            own = [r for r in self.results_local if r.get('local')]
            if own:(self.run / 'own_results.local.json').write_text(json.dumps({'key': self.key, 'results': own}, indent=1) + '\n', encoding='utf-8')
        if self.args.own_items:Path(self.args.own_items).unlink(missing_ok=True)
        if found:
            self.say('The privacy scan found what must not leave: %s. Nothing was written for sending.' % ', '.join(sorted({f['what'] for f in found})))
            return {'state': 'PRIVACY_SCAN_FAILED', 'found': found}
        if len(card_text.encode('utf-8')) > CARD_MOST:card_text = card_text.encode('utf-8')[:CARD_MOST - 64].decode('utf-8', 'ignore') + '\n(cut at 50 KB)\n'
        out = self.run / 'for-sending';out.mkdir(exist_ok=True)
        name = 'model-check-%s' % report['date']
        (out / (name + '.json')).write_text(blob + '\n', encoding='utf-8')
        (out / (name + '.txt')).write_text(card_text, encoding='utf-8')
        self.say(card_text)
        return {'state': 'WRITTEN', 'json': name + '.json', 'card': name + '.txt'}


# == the kept choose turn of S3 (an invented brief, registered on first use, never at import) ======================================
KIT_BRIEF = '\n'.join([
    'You help a desk on this computer find which numbered thing a question is about.',
    'The things are listed in the first user message, one per line, each with its number.',
    'The question is in the last user message. It may name a thing by its title, its kind, its revision or a word of its title.',
    'Answer with the number of the one thing the question is about, and nothing else.',
    'If the question names no listed thing, or more than one equally, answer 0.',
    'A newer revision is the one with the later letter: Rev B is newer than Rev A.',
    'Never answer with a number that is not listed. Never explain. Never add words.',
    'Examples, invented: Things: 1. Garden pump, Rev A  2. Garden pump, Rev B  3. Shed lease. Question: the newer pump. Answer: 2',
    'Things: 1. Garden pump, Rev A  2. Garden pump, Rev B  3. Shed lease. Question: the lease. Answer: 3',
    'Things: 1. Kitchen scale notes  2. Bike light datasheet. Question: how bright is the light. Answer: 2',
] * 4)
KIT_THINGS = ('Rail Demo bench supply datasheet, Rev B', 'Rail Demo bench supply datasheet, Rev A',
              'Home Demo lease, section 12 deposit', 'Rail Demo cable tray notes', 'Home Demo statement, November')
KIT_QUESTIONS = (('which is the newer bench supply', KIT_THINGS), ('the deposit clause of the lease', KIT_THINGS),
                 ('the older datasheet', KIT_THINGS), ('the November statement', KIT_THINGS))
KIT_RIGHT = {'which is the newer bench supply': 1, 'the deposit clause of the lease': 3, 'the older datasheet': 2,
             'the November statement': 5}


def kit_kind():
    from . import grammars, model_words, turns
    if 'KITCHOOSE' not in turns.KINDS:
        turns.register(turns.TurnKind(
            name='KITCHOOSE', version=1, switch='choosing', brief=lambda: KIT_BRIEF,
            stable=lambda i: '\n'.join('%d. %s' % (n, t) for n, t in enumerate(i['things'], 1)),
            last=lambda i: 'Question: ' + i['question'], grammar=lambda i: grammars.choice(len(i['things'])),
            caps=turns.Caps(new_tokens=1600, answer_tokens=4, deadline_ms=20000),   # a cold first question fits too
            parse=lambda said, i: model_words.option(said, len(i['things'])),
            check=lambda n, i: turns.Verdict('TAKEN', value=n, checks=(('range', True, str(n)),)),
            fallback=lambda i: turns.Fallback('ASK_OWNER', tuple(i['things'])), paper=''))
    return turns.KINDS['KITCHOOSE']


# == the predictions, the outcomes and the proposals ===============================================================
def _get(report, *path):
    v = report
    for p in path:
        v = v.get(p) if isinstance(v, dict) else None
    return v


def judge(report):
    """Held or not per prediction (None: not measured here, with why), the outcomes of design 6.4 that fired, and the
    settings proposed."""
    st = report['stages'];k = report['predictions']
    def put(key, held, measured, why=None):
        k[key] = {'prediction': PREDICTIONS[key], 'held': held, 'measured': measured, **({'why': why} if why else {})}
    gtt = max((c.get('gtt_total') or 0 for c in _get(report, 'stages', 'S0', 'gpu_memory') or []), default=0)
    put('K1', gtt >= 28 * GIB if gtt else None, '%s MiB' % '{:,}'.format(gtt // MIB) if gtt else None, None if gtt else 'no amdgpu memory window here')
    first, warm = _get(report, 'stages', 'S1', 'first_load_ms'), _get(report, 'stages', 'S1', 'warm_load_ms')
    put('K2', (20000 <= first <= 60000 and 8000 <= warm <= 25000) if first and warm else None,
        {'first_ms': first, 'warm_ms': warm})
    r1200 = _get(report, 'stages', 'S2', 'reads', '1200', 'per_second')
    put('K3', 150 <= r1200 <= 400 if r1200 else None, r1200)
    w64 = _get(report, 'stages', 'S2', 'writes', '64', 'per_second');hot = _get(report, 'stages', 'S2', 'heat', 'last')
    put('K4', (15 <= w64 <= 25 and hot is not None and hot >= 12) if w64 else None, {'writing': w64, 'after_heat': hot})
    b64, b512 = _get(report, 'stages', 'S2', 'batches', '64', 'per_second'), _get(report, 'stages', 'S2', 'batches', '512', 'per_second')
    put('K5', b512 >= 2 * b64 if b64 and b512 else None, {'64': b64, '512': b512}, None if b64 else 'batches are measured on Vulkan only')
    kept, ms = _get(report, 'stages', 'S3', 'second_round_kept'), _get(report, 'stages', 'S3', 'kept_turn_ms')
    put('K6', (bool(kept) and ms < 1600) if kept is not None and ms is not None else None, {'kept_turn_ms': ms, 'second_round_kept': kept})
    shape = _get(report, 'model', 'memory_shape');per = _get(report, 'stages', 'S3', 'checkpoint', 'per_checkpoint_bytes')
    residual = _get(report, 'stages', 'S3', 'checkpoint', 'residual_percent')
    put('K7', (55 * MIB <= per <= 75 * MIB and (residual is None or residual <= 10)) if shape == 'HYBRID' and per else None,
        {'per_checkpoint_mib': per // MIB if per else None, 'computed_mib': (_get(report, 'model', 'checkpoint_bytes_computed') or 0) // MIB or None},
        None if shape == 'HYBRID' else 'not a hybrid model')
    stop = _get(report, 'stages', 'S3', 'stop', 'stop_ms')
    put('K8', stop <= 2000 if stop is not None else None, stop)
    seal, backend = _get(report, 'stages', 'S1', 'seal', 'state'), _get(report, 'stages', 'S1', 'backend')
    put('K9', seal == 'SEALED' if backend == 'VULKAN' else None, {'seal': seal, 'backend': backend}, None if backend == 'VULKAN' else 'the model ran on the processor')
    summ = _get(report, 'stages', 'S5', 'summary') or {}
    single = _get(summ, 'READ', 'by_category', 'single');clear = _get(summ, 'CHOOSE', 'by_category', 'clear')
    steer = summ.get('STEER')
    if single and clear and steer:
        put('K10', single['right'] >= 22 and clear['right'] >= 7 and steer['harm'] == 0,
            {'read_single': '%d of %d' % (single['right'], single['asked']), 'choose_clear': '%d of %d' % (clear['right'], clear['asked']),
             'steer_harm': steer['harm']})
    else:
        put('K10', None, None, 'the papers it needs were not sat')
    longest = _get(report, 'stages', 'S4', 'longest_stall_ms')
    put('K11', longest <= 50 if longest is not None else None, longest, None if longest is not None else 'from the Brain room only')
    pct = _get(report, 'stages', 'S2', 'grammar', 'overhead_percent')
    put('K12', pct <= 15 if pct is not None else None, pct)
    # 1.0 M1: the owner's goal, from the tuning stage's best (else S2's 1,200-token read and 64-token write)
    from . import runtime_tuning
    best_read = _get(report, 'stages', 'S2T', 'best', 'read_per_second') or r1200
    best_write = _get(report, 'stages', 'S2T', 'best', 'write_per_second') or w64
    goal = runtime_tuning.GOAL
    put('K13', best_read >= goal if best_read else None, best_read, None if best_read else 'no read was measured')
    put('K14', best_write >= goal if best_write else None, best_write, None if best_write else 'no write was measured')
    findings, proposals = [], []
    if k['K1']['held'] is False:
        findings.append(_get(report, 'stages', 'S0', 'gtt_short', 'words') or 'The GPU memory window is too small; nothing was changed. '
                        'Plan B: the 4B on Vulkan, or the large model with its experts on the processor.')
    if backend == 'CPU' and _get(report, 'stages', 'S1', 'requested_backend') in ('AUTO', 'VULKAN') and _get(report, 'stages', 'S1', 'fallback_reason'):
        findings.append('Vulkan did not start the model; the processor did, as the start falls back.')
        proposals.append(proposal('brain.backend', 'CPU', 'Vulkan did not start the model here; the processor did.'))
    if backend == 'VULKAN' and seal:
        proposals.append(proposal('brain.backend', 'VULKAN', 'The model loaded and answered on the Radeon.'))
    if r1200 is not None and r1200 < 100:
        findings.append('Reads are under 100 tokens a second (%d): pages are read only when you ask, and long questions are cut.' % r1200)
    if _get(report, 'stages', 'S1', 'template_thinking') == 'IGNORED':
        findings.append("The model's chat template cannot switch thinking off: the template is refused, and the model is not trusted "
                        'until a template that does.')
    second = _get(report, 'stages', 'S3', 'turns') or []
    if second[1:] and all((t.get('cache_n') or 0) < 8 for t in second[1:]):
        findings.append('Prompt reuse did not help here (second-round cache near 0): reuse is reported as off.')
    if longest is not None and longest > 50:
        findings.append('The desk stalled for %d ms during a long read: short turns use a smaller batch while you work at the desk.' % longest)
    if first and first > 60000:
        findings.append('A first load took over a minute: loading her model when the desk opens is worth a setting (none yet).')
    if ms is not None and ms > 2000:
        findings.append('A kept choose turn took over 2 s: the small chooser moves up the list of what comes next.')
    if b64 and b512 and b512 >= 2 * b64:
        findings.append('Reading in batches of 512 is %s times faster than 64.' % _times(b512, b64))
        if not _get(report, 'stages', 'S2T', 'best', 'settings', 'batch'):      # 1.0 M1: the reading batch is a setting now
            proposals.append(proposal('brain.batch', 512, 'reading in batches of 512 was %s times faster than 64 here.' % _times(b512, b64)))
    if best_read or best_write:                                            # 1.0 M1: the owner's goal, said plainly
        findings.extend(runtime_tuning.goal_words(best_read, best_write))
    proposals.extend(runtime_tuning.proposals(_get(report, 'stages', 'S2T'), proposal))
    for kind, v in (_get(report, 'stages', 'S5', 'kinds') or {}).items():
        if v.get('state') == 'SWITCHED_OFF':findings.append(v['words'])
    report['findings'] = findings;report['proposals'] = [p for p in proposals if p]
    return report


def _times(a, b):
    tenths = a * 10 // b
    return '%d.%d' % (tenths // 10, tenths % 10)


def proposal(key, value, why):
    from .model_settings import OPTIONS
    if key not in OPTIONS:return None                    # only an owner launch default can be proposed
    return {'id': hashlib.sha256(('%s=%s' % (key, json.dumps(value))).encode()).hexdigest()[:12], 'key': key, 'to': value, 'why': why,
            'words': 'Set %s to %s: %s' % (key.split('.', 1)[1].replace('_', ' '), value, why)}


def card(report):
    """The plain card (the .txt), ending with "Her model on this machine: ..." (design 6.2)."""
    st = report['stages'];k = report['predictions']
    lines = ['Graphite %s · the model check · %s' % (report.get('graphite'), report.get('date')),
             'Model: %s%s' % (_get(report, 'model', 'file'), ' (a hybrid)' if _get(report, 'model', 'memory_shape') == 'HYBRID' else ''), '']
    for key, words, *_ in STAGES:
        s = st.get(key) or {'state': 'NOT_RUN', 'why': 'not reached'}
        lines.append('%s  %-45s %s%s%s' % (key, words[:45], s['state'].lower().replace('_', ' '), (': ' + s['why']) if s.get('why') else '',
                                           ' (contended)' if s.get('contended') else ''))
    lines += ['', 'Predictions (written before the run):']
    for key in PREDICTIONS:
        v = k.get(key) or {}
        held = {True: 'held', False: 'did not hold', None: 'not measured'}[v.get('held')]
        lines.append('%-4s %s: %s%s' % (key, held, PREDICTIONS[key], (' (%s)' % v['why']) if v.get('why') and v.get('held') is None else ''))
    exam = _get(report, 'stages', 'S5', 'card')
    if exam:lines += ['', 'The short exam:'] + ['  ' + l for l in exam]
    quick = _get(report, 'stages', 'SQ', 'card')        # 1.0 M2: the quick model beside it, and the split it proposes
    if quick:lines += ['', 'A quick model beside it:'] + ['  ' + l for l in quick]
    if report.get('findings'):lines += ['', 'What it found:'] + ['  ' + f for f in report['findings']]
    if report.get('proposals'):lines += ['', 'Use the measured settings? Each is yours to apply, with Undo:'] + ['  ' + p['words'] for p in report['proposals']]
    lines += ['', summary_line(report), '']
    return '\n'.join(lines)


def summary_line(report):
    parts = []
    first = _get(report, 'stages', 'S1', 'first_load_ms')
    if first:parts.append('loads in %d s' % (first // 1000))
    r = _get(report, 'stages', 'S2', 'reads', '1200', 'per_second')
    if r:parts.append('reads %d a second' % r)
    w = _get(report, 'stages', 'S2', 'writes', '64', 'per_second')
    if w:parts.append('writes %d a second' % w)
    best = _get(report, 'stages', 'S2T', 'best') or {}                    # 1.0 M1
    if best.get('settings') and best.get('read_per_second') and best.get('write_per_second'):
        parts.append('at its best settings reads %d and writes %d' % (best['read_per_second'], best['write_per_second']))
    ms = _get(report, 'stages', 'S3', 'kept_turn_ms')
    if ms is not None:parts.append('a question she has seen before: %d.%d s' % (ms // 1000, ms % 1000 // 100))
    gtt = max((c.get('gtt_total') or 0 for c in _get(report, 'stages', 'S0', 'gpu_memory') or []), default=0)
    need = _get(report, 'stages', 'S0', 'memory_rule', 'estimate_bytes')
    if gtt and need:
        parts.append('memory window %s GB, she needs %s: %s' % (_gb(gtt), _gb(need), 'fine' if need <= gtt else 'too small'))
    n = len(report.get('proposals') or [])
    parts.append('no change suggested' if not n else 'one change suggested' if n == 1 else '%d changes suggested' % n)
    return 'Her model on this machine: ' + '; '.join(parts) + '.'


def _gb(b):
    tenths = b * 10 // (1000 ** 3)
    return '%d.%d' % (tenths // 10, tenths % 10)


# == use the measured settings (the owner's hand, with Undo) ==========================================================
def current(kernel, key):
    from .model_settings import OPTIONS, preferences
    return preferences(kernel).get(OPTIONS['brain.' + key.split('.', 1)[1]])


def offered(kernel, report):
    """The proposals that would change something now (the same value is not offered)."""
    out = []
    for p in report.get('proposals') or ():
        try:
            if current(kernel, p['key']) != p['to']:out.append(p)
        except (KeyError, ValueError):
            continue
    return out


def use_setting(kernel, principal, p, seen):
    """Apply one proposal, on the owner's click: ledger.settings.set with the value he saw (refused if it changed since).
    Returns the change record (its id is what Undo needs)."""
    result = kernel.dispatch('ledger.settings.set', {'key': p['key'], 'value': p['to'], 'expected': seen}, principal)
    if not result.get('ok'):raise ValueError((result.get('error') or {}).get('message') or 'SETTING_NOT_APPLIED')
    return result['result']


def undo_setting(kernel, principal, change_id):
    """Undo: the exact previous record comes back (ledger.settings.undo)."""
    result = kernel.dispatch('ledger.settings.undo', {'id': change_id}, principal)
    if not result.get('ok'):raise ValueError((result.get('error') or {}).get('message') or 'SETTING_NOT_UNDONE')
    return result['result']


# == the command =====================================================================================================
def default_out():
    from .session import config_dir
    return config_dir() / 'model-check' / datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -B -m workbench.model_check', description='Check her model on this machine.')
    ap.add_argument('--model', type=Path, help='the model file (GGUF)')
    ap.add_argument('--out', type=Path, help='the run folder (default: under Graphite\'s own settings folder)')
    ap.add_argument('--plan', action='store_true', help='show the stages and their estimated times; start nothing')
    ap.add_argument('--overnight', action='store_true', help='also S7: the full exam and the I05 arms (hours, on mains)')
    ap.add_argument('--also', type=Path, help='S6: another model file (the 35B on the processor, or the 4B on the Radeon)')
    ap.add_argument('--also-backend', default='CPU', choices=['AUTO', 'CPU', 'VULKAN'])
    ap.add_argument('--quick', type=Path, help='SQ: a small model file to measure beside it, and the split to propose (1.0 M2)')
    ap.add_argument('--context', type=int, default=6144)
    ap.add_argument('--threads', type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument('--memory-mb', type=int, default=0, help='the memory cap (default Auto)')
    ap.add_argument('--backend', default='AUTO', choices=['AUTO', 'CPU', 'VULKAN'])
    ap.add_argument('--stages', help='a comma list of S2, S2T, S3 to S7 to run (S0 and S1 always run)')
    ap.add_argument('--tuning-seconds', type=int, default=0, help='the tuning stage\'s time box (default 240 s)')   # 1.0 M1
    ap.add_argument('--i05-repeats', type=int, default=3)
    ap.add_argument('--own-items', type=Path, help=argparse.SUPPRESS)        # the Brain room's own paper (kept local)
    ap.add_argument('--pause-file', type=Path, help=argparse.SUPPRESS)       # the Brain room's pause file
    ap.add_argument('--from-room', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--progress-json', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--allow-battery', action='store_true', help=argparse.SUPPRESS)   # a dry run where no mains can be read
    args = ap.parse_args(argv)
    if args.plan:print(plan_text(args.overnight, bool(args.also), bool(args.quick)));return 0     # 1.0 M2: and SQ
    if not args.model:ap.error('--model is needed (or --plan)')
    args.out = args.out or default_out()
    def progress(**kw):
        if args.progress_json:print('@@ ' + json.dumps(kw), flush=True)
    result = Check(args, say=lambda text: print(text, flush=True), progress=progress).go()
    progress(event='done', **{k: v for k, v in result.items() if k != 'found'})
    return 0 if result['state'] == 'WRITTEN' else 1


if __name__ == '__main__':
    raise SystemExit(main())
