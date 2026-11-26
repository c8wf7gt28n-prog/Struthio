"""Her model's runtime, current (1.0 M1): llama.cpp v1.0.0 (b12359) and its newer capabilities, put to work where they
help her, each an owner launch default the model check measures before it is proposed.

The owner, 26 Nov 2026: "to manipulate the LLM let's make sure we're using the latest and best technologies", and
"99 tokens per second, up and down... if possible" (reading and writing, on the ThinkPad with the 35B-A3B).

What v1.0.0 gives and how Graphite uses it (every one through the sealed launch line, brain_seal.ALLOWED):

    the model's own jinja template, thinking off   --jinja --reasoning off, always (measured here: the 4B answers
                                                    without thinking even when a request carries no template switch)
    flash attention                                 brain.flash_attn: auto (the runtime's own default, as before), on, off
    the KV cache's type                             brain.kv_type: f16 (as before), q8_0, f8_e4m3; a quantized V needs
                                                    flash attention, so off with a quantized type is refused
    load mode auto                                  brain.load_mode: none (a resident copy, as before), auto (mmap
                                                    where the device allows: no second copy of the weights beside the
                                                    integrated GPU's own; the model file must then stay unchanged,
                                                    which verify_resident already checks before every answer)
    multi-token prediction                          brain.mtp_draft: 0 (off) or the draft length, 1 to 8, from the
                                                    model's own MTP head (an "MTP GGUF": the head inside the one model
                                                    file); never a second model file (-md and --shard stay refused)
    the reading batch                               brain.batch: 64 (as before), 256, 512, 1024
    the host-memory prompt cache                    --cache-ram sized from the memory sum (resource_control) so every
                                                    kept prompt fits: PLAN's and READ's survive a priming round

Defaults stay as they were (safe); the model check's tuning stage (sweep) measures each on the owner's machine,
keeps only settings whose answer is identical to the plain run's at temperature 0, and proposes the best through
'Use the measured settings?' with Undo. The structured-output path: her kinds' answers are short lines her own GBNF
grammars bound exactly (stricter than a schema), so they stay; the one JSON answer (the chat's plan) keeps the server's
JSON-schema path, as before.

No floating point in anything checked: rates are whole tokens a second, sizes whole bytes, fractions exact.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from fractions import Fraction
from pathlib import Path

# -- the owner's machine and the files the first evening names (facts, read 26 Nov 2026) -----------------------------------
OWNER_MACHINE = {
    # The coordinator's correction (26 Nov 2026, from the label in the owner's photo): not a Radeon 780M.
    'model': 'ThinkPad E16 Gen 2 AMD', 'machine_type': '21M5',
    'processor': 'AMD Ryzen 7 7735HS (8 cores, 16 threads), as the console photos show',
    'graphics': 'Radeon 680M (RDNA2, gfx1035, 12 compute units), integrated: its memory is the system memory (GTT)',
    'memory': 'DDR5-4800, two SO-DIMMs, dual channel: about 77 GB/s at most, 60 to 70 in practice; 61 GiB seen',
    'expectations': ('Reading is bound by the 680M\'s compute; writing by memory bandwidth: the 35B-A3B at Q4 about 15 '
                     'to 30 tokens a second, more with multi-token prediction. Flash attention\'s fast matrix paths '
                     'are for RDNA3; on RDNA2 the Vulkan backend has a scalar path or none, so the sweep decides.'),
}
# The owner's model with its MTP head inside (Hugging Face API, lfs info, 26 Nov 2026; not downloaded here).
MTP_FILE_35B = {'repo': 'unsloth/Qwen3.6-35B-A3B-MTP-GGUF', 'file': 'Qwen3.6-35B-A3B-UD-Q4_K_M.gguf',
                'bytes': 22663387424, 'sha256': '0b21525e972670ed59e1812e170b27c26355381f0656ecc4e25617ece7dac58b',
                'without_head': {'repo': 'unsloth/Qwen3.6-35B-A3B-GGUF', 'file': 'Qwen3.6-35B-A3B-UD-Q4_K_M.gguf',
                                 'bytes': 22134528992}}
MTP_FILES_SMALL = {   # the same maker's small files with the head inside, for a rehearsal (not downloaded here)
    'Qwen3.5-4B-Q4_K_M.gguf': {'repo': 'unsloth/Qwen3.5-4B-MTP-GGUF', 'bytes': 2834975040,
                               'sha256': '3874209241c9a397e2f62cd3f70f80fd2dfbf0dfccb6838416bdb48a714e8630'},
    'Qwen3.5-2B-Q4_K_M.gguf': {'repo': 'unsloth/Qwen3.5-2B-MTP-GGUF', 'bytes': 1329851808,
                               'sha256': '18c92228fc1498a02506f64593f7cc8cc02f406f732a217c6ba99ad1254d4f0b'}}

# -- the launch settings -------------------------------------------------------------------------------------------------------
KV_BYTES = {'f16': Fraction(2), 'q8_0': Fraction(34, 32), 'f8_e4m3': Fraction(1)}   # bytes an element, exact
FLASH = ('auto', 'on', 'off')
LOAD_MODES = ('none', 'auto')
BATCHES = (64, 256, 512, 1024)
MTP_MOST = 8
DEFAULTS = {'flash_attn': 'auto', 'kv_type': 'f16', 'load_mode': 'none', 'mtp_draft': 0, 'batch': 64}
KEYS = tuple(DEFAULTS)


def settings(options):
    """The M1 launch settings from a launch's options, each checked; a missing one is its default (as before 1.0)."""
    options = options or {}
    out = {}
    for key, default in DEFAULTS.items():
        value = options.get(key, default)
        ok = {'flash_attn': value in FLASH, 'kv_type': value in KV_BYTES, 'load_mode': value in LOAD_MODES,
              'mtp_draft': type(value) is int and 0 <= value <= MTP_MOST, 'batch': value in BATCHES}[key]
        if not ok:raise ValueError('MODEL_LAUNCH_SETTING_INVALID: %s' % key)
        out[key] = value
    if out['kv_type'] != 'f16' and out['flash_attn'] == 'off':
        raise ValueError('MODEL_KV_TYPE_NEEDS_FLASH_ATTENTION: a %s KV cache needs flash attention on or auto' % out['kv_type'])
    return out


def mtp_layers(inspection):
    """How many MTP layers the model file carries (its own head), from the GGUF metadata; 0 when none."""
    try:
        metadata = inspection['metadata'];architecture = inspection['architecture']
    except (KeyError, TypeError):
        return 0
    value = metadata.get(str(architecture) + '.nextn_predict_layers')
    return value if type(value) is int and value > 0 else 0


def launch_extra(config, backend):
    """What the M1 settings add to the launch line (local_brain.launch_arguments), every argument on the seal's list."""
    s = settings(config)
    line = ['--jinja', '--reasoning', 'off', '--flash-attn', s['flash_attn']]
    if s['kv_type'] != 'f16':line += ['--cache-type-k', s['kv_type'], '--cache-type-v', s['kv_type']]
    if s['mtp_draft'] and config.get('mtp_layers'):
        line += ['--spec-type', 'draft-mtp', '--spec-draft-n-max', str(s['mtp_draft'])]
    return line


def load_mode(config):
    return settings(config)['load_mode']


def kv_bytes(elements, kv_type='f16'):
    """Bytes for this many K or V elements of the type, rounded up to a whole byte (q8_0: 34 bytes a block of 32)."""
    total = Fraction(int(elements)) * KV_BYTES[kv_type]
    return -(-total.numerator // total.denominator)


# -- the host-memory prompt cache, sized from the memory sum --------------------------------------------------------------
# Measured here with v1.0.0 and the 4B: a cache entry is the prompt's KV and the context checkpoints the slot made while
# reading it (one ~830-token prompt: 226.8 MiB, four checkpoints of 50.25 MiB and 26 MiB of KV), and the slot's own
# prompt is saved into the cache before a new prompt is looked up. Kept prompts: one per kind primed at Ready (eleven,
# brain_clock.BUDGETS), PLAN's and READ's desks, and the slot's own save: fourteen. A smaller rung keeps four (PLAN,
# READ, the slot's save and one more), which still holds both desks through a priming round when they are primed last.
KEPT_PROMPTS = 14
KEPT_PROMPTS_FEW = 4
KEPT_TOKENS = 1024          # a kept prompt's tokens, at most (READ's brief and desk: about 1,050 on the 4B; PLAN's 463)


def cache_mb(state_bytes, kv_per_token, checkpoints, entries):
    """The RAM prompt cache, in whole MiB rounded up, that holds `entries` kept prompts: each its KV over KEPT_TOKENS and
    up to `checkpoints` recurrent states."""
    entry = int(kv_per_token) * KEPT_TOKENS + int(checkpoints) * int(state_bytes)
    return -(-entry * int(entries) // (1024 * 1024))


# -- the measured rates her clock starts from (her clock's stand-ins per model key) ---------------------------------------
def _rates_path():
    from .session import config_dir
    return config_dir() / 'model-check' / 'measured_rates.json'


def remember(key, read_per_second, write_per_second, settings_used, measured_on='model check, tuning stage'):
    """Keep the rates a model key was measured at (whole tokens a second), for her clock (brain_clock)."""
    if not key or not read_per_second or not write_per_second:return None
    path = _rates_path()
    try:
        held = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(held, dict):held = {}
    except (OSError, ValueError):
        held = {}
    held[str(key)] = {'read': int(read_per_second), 'write': int(write_per_second), 'settings': settings_used,
                      'at': int(time.time()), 'by': measured_on}
    if len(held) > 64:
        for old in sorted(held, key=lambda k: held[k].get('at') or 0)[:len(held) - 64]:held.pop(old)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp');tmp.write_text(json.dumps(held, indent=1, sort_keys=True), encoding='utf-8');os.replace(tmp, path)
    _MEASURED.clear()
    return held[str(key)]


_MEASURED: dict = {}


def measured(key):
    """(read, write) tokens a second as Fractions, measured for this model key by the model check; None when never."""
    if not key:return None
    try:stamp = _rates_path().stat().st_mtime_ns      # 1.0 M1b: rates kept by another process (the model check) are seen
    except (OSError, ImportError):stamp = None
    if _MEASURED.get(' stamp') != stamp:_MEASURED.clear();_MEASURED[' stamp'] = stamp
    if key not in _MEASURED:
        try:
            got = json.loads(_rates_path().read_text(encoding='utf-8')).get(str(key))
            _MEASURED[key] = (Fraction(int(got['read'])), Fraction(int(got['write']))) if got and got.get('read') and got.get('write') else None
        except (OSError, ValueError, TypeError, KeyError, ImportError):
            _MEASURED[key] = None
    return _MEASURED[key]


# -- the tuning sweep (the model check's stage S2T) ------------------------------------------------------------------------
GOAL = 99                       # the owner's: tokens a second, reading and writing
SWEEP_SECONDS = 240             # the time box: a few minutes, in the awake part
TYPICAL_NEW, TYPICAL_ANSWER = 300, 40        # her typical question: new tokens read, tokens written
PROSE = [{'role': 'system', 'content': 'You describe invented equipment plainly.'},
         {'role': 'user', 'content': 'Describe the Rail Demo bench supply, which gives twelve volts to a cable tray rail, '
                                     'and its fuse, in five short sentences.'}]


def typical_ms(read, write):
    """Her typical question's time in whole ms at these rates (lower is better): 300 tokens read, 40 written."""
    if not read or not write:return None
    return -(-TYPICAL_NEW * 1000 // int(read)) + -(-TYPICAL_ANSWER * 1000 // int(write))


def physical_cores():
    try:
        text = Path('/proc/cpuinfo').read_text()
        pairs = {(b.split('physical id')[1].split('\n')[0] if 'physical id' in b else '0',
                  b.split('core id')[1].split('\n')[0] if 'core id' in b else str(i)) for i, b in enumerate(text.split('\n\n')) if b.strip()}
        return len(pairs) or None
    except (OSError, IndexError):
        return None


def dimensions(check, backend, mtp):
    """What the sweep tries, one dimension at a time from the plain run, each kept only when identical and faster."""
    logical = os.cpu_count() or 1;physical = physical_cores() or max(1, logical // 2)
    current = check.args.threads
    dims = [('flash_attn', ['on', 'off']), ('kv_type', ['q8_0', 'f8_e4m3']), ('batch', [256, 512, 1024]),
            ('threads', [t for t in sorted({physical, logical}) if t != current and 1 <= t <= 32])]
    if backend == 'VULKAN':dims.append(('gpu_layers', [-1, 'half']))
    dims.append(('mtp_draft', [1, 2, 3] if mtp else []))
    return dims


def sweep(check, seconds=SWEEP_SECONDS):
    """The tuning stage: after S2's speeds, the settings that matter on the Radeon, each a fresh launch through Graphite's
    own path. Returns the stage record: every trial, the best, the two predictions' measurements and the proposals."""
    from . import local_brain, model_exam
    began = time.monotonic();rows = []
    worker = check.work.worker();backend = worker.get('backend') or 'CPU'
    value = check.work.value(check.model_id);mtp = mtp_layers(value['inspection'])
    sizes = (1200, 64) if backend == 'VULKAN' else (300, 24)       # the processor here: smaller, to fit the box
    blocks = int(value['inspection']['metadata'].get(str(value['inspection']['architecture']) + '.block_count') or 0)

    def over():
        return time.monotonic() - began > seconds

    def trial(label, extra):
        if over():
            rows.append({'label': label, 'settings': extra, 'state': 'NOT_RUN', 'why': 'the time box (%d s) was spent' % seconds})
            return None
        try:
            local_brain.stop(check.work.kernel, 'MODEL_CHECK_TUNING')
            _, load_ms = check.work.use(check.model_id, check.options(**extra, prime=False));port = check.live_port()
            from .model_check import read_speed
            read, _ = check.gate.measure(lambda: read_speed(port, sizes[0], 't%d' % time.time_ns()))
            got, _ = check.gate.measure(lambda: port.complete(PROSE, answer_tokens=sizes[1], grammar=None, deadline_ms=0))
            t = got.get('timings') or {}
            write = int(t['predicted_n']) * 1000 // int(t['predicted_ms']) if t.get('predicted_n') and t.get('predicted_ms') else None
            w = check.work.worker()
            row = {'label': label, 'settings': extra, 'state': 'MEASURED', 'load_ms': load_ms,
                   'read_per_second': read.get('per_second'), 'write_per_second': write,
                   'answer_sha256': hashlib.sha256((got.get('text') or '').encode()).hexdigest()[:16],
                   'draft': {k: t.get(k) for k in ('draft_n', 'draft_n_accepted') if t.get(k) is not None} or None,
                   'key': model_exam.key_for(w)['key'], 'backend': w.get('backend')}
            row['typical_ms'] = typical_ms(row['read_per_second'], write)
        except Exception as exc:  # noqa: BLE001 - a setting the runtime refuses is a row that says why
            from .model_check import _code
            row = {'label': label, 'settings': extra, 'state': 'REFUSED', 'why': _code(str(exc) or type(exc).__name__)}
        rows.append(row)
        return row

    plain = trial('plain', {})
    if not plain or plain['state'] != 'MEASURED':
        return {'state': 'FAILED', 'why': 'the plain run did not answer', 'trials': rows}
    best = dict(plain);chosen = {}
    remember(plain['key'], plain['read_per_second'], plain['write_per_second'], {})
    for dim, values in dimensions(check, backend, mtp):
        if not values:
            rows.append({'label': dim, 'state': 'NOT_RUN', 'why': 'the model file has no MTP head: an MTP GGUF carries one '
                         '(the first evening names the file)' if dim == 'mtp_draft' else 'nothing to try here'})
            continue
        for v in values:
            if dim == 'kv_type' and chosen.get('flash_attn') == 'off':
                rows.append({'label': '%s=%s' % (dim, v), 'state': 'NOT_RUN', 'why': 'a quantized KV cache needs flash attention'})
                continue
            v = max(1, blocks // 2) if v == 'half' else v
            row = trial('%s=%s' % (dim, v), {**chosen, dim: v, **({'flash_attn': 'on'} if dim == 'kv_type' and 'flash_attn' not in chosen else {})})
            if not row or row['state'] != 'MEASURED':continue
            row['identical'] = row['answer_sha256'] == plain['answer_sha256']
            if row['identical']:remember(row['key'], row['read_per_second'], row['write_per_second'], row['settings'])
            if row['identical'] and row['typical_ms'] is not None and row['typical_ms'] < best['typical_ms']:
                best = dict(row);chosen = dict(row['settings'])
    out = {'trials': rows, 'plain': {k: plain.get(k) for k in ('read_per_second', 'write_per_second', 'typical_ms')},
           'best': {'settings': chosen, **{k: best.get(k) for k in ('read_per_second', 'write_per_second', 'typical_ms', 'key')}},
           'sizes': {'read_tokens': sizes[0], 'write_tokens': sizes[1]}, 'seconds_box': seconds,
           'mtp_head_layers': mtp, 'identity': 'the same answer as the plain run at temperature 0 (its sha256), or not kept',
           'note': 'measured on this computer only; a fresh launch through the seal for each row'}
    out['goal'] = goal_words(best.get('read_per_second'), best.get('write_per_second'))
    # The best is the launch left running for the stages after this one? No: the stages after run on the plain launch.
    local_brain.stop(check.work.kernel, 'MODEL_CHECK_TUNING')
    check.work.use(check.model_id, check.options());check.live_port()
    return out


def goal_words(read, write):
    """The owner's 99 a second, said plainly: reached, or how far off."""
    def one(name, rate):
        if not rate:return '%s: not measured' % name
        if rate >= GOAL:return '%s at %d tokens a second: the goal of %d is reached' % (name, rate, GOAL)
        return '%s at %d tokens a second: %d short of %d (%d %% of it)' % (name, rate, GOAL - rate, GOAL, rate * 100 // GOAL)
    return [one('Reads', read), one('Writes', write)]


def proposals(stage, proposal):
    """'Use the measured settings?' rows for the best: each setting that differs from the plain launch, with the numbers."""
    best = (stage or {}).get('best') or {};plain = (stage or {}).get('plain') or {}
    out = []
    for key, value in sorted((best.get('settings') or {}).items()):
        if key == 'gpu_layers' and value == -1:continue
        why = ('measured here: reads %s and writes %s tokens a second against %s and %s, with the same answer' % (
            best.get('read_per_second'), best.get('write_per_second'), plain.get('read_per_second'), plain.get('write_per_second')))
        p = proposal('brain.' + key, value, why)
        if p:out.append(p)
    return out
