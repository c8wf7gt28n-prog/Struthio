"""Graphite 1.0 M2 · a quick model beside her model, for 99 tokens a second (the owner, 26 Nov 2026: "The goal is 99 tokens
per second, up and down....if possible").

Reading at 99 tokens a second is likely for the 35B-A3B on the Radeon 680M; writing at 99 is not (its memory bandwidth bounds
the 35B's writing to some 20 to 30 a second). Her questions are short (20 to 60 tokens of answer over kept prompts), so the
way to 99 writing is a second, small model for the quick kinds (QUICK_KINDS: READ, PLAN, NEXT, MARKS, ASK), held beside her
model, memory allowing. Her model keeps every other kind (wording, utilities, talk) and every quick kind the small one has
not earned.

THE RULE. A quick kind is answered by the quick model only when all of these hold (decide(), in this order; the first that
fails keeps the kind on her model and is the reason the Brain room shows):
    offered       the split offers it (brain.quick_split): every quick kind once a quick model is loaded; one Undo puts
                  every kind back on her model (offered: none), and "Use the quick model again" offers them again
    loaded        a quick model is running beside a running model of hers
    a paper       the kind has an exam paper (model_exam's papers); PLAN has none yet, so no model can pass it
    examined      A5's exam record on the QUICK model's key says EXAMINED for the kind: 19 of its last 20 right, harm 0
                  (model_exam.view); not yet examined, switched off or changed keeps it on her model, in A5's words
    measured      her clock has rates for both keys: the model check's pair measurement (runtime_tuning.remember) or three
                  turns of each model's own
    faster        her clock prices the kind's typical question (TYPICAL) lower on the quick model's key than on hers
Then the row reads "passed its exam for READ on this key, 2.1x faster". Nothing here makes a model trusted: every answer is
still checked by its kind's checker before anything uses it (turns.ask), whichever model gave it.

THE PAIR. The quick model is launched as a brain.activate job with the launch option slot "quick" (local_brain.OPTIONS),
through the same sealed path as hers (local_brain.start_server: the file's hash, the memory rule, the seal check, its own
private socket or loopback port), into its own worker slot (brain.quick_worker), with its own selection (brain.quick_selection)
and its own kept prompts (brain.quick_kept: QuickStore, its quick kinds' briefs and desks primed at Ready, never her model's).
It never replaces her model: no handover, no credit for her model's memory. The memory sum counts both: the quick model's
budget is its own estimate (the reuse ladder, resource_control) and must fit in what is left beside her model's budget and
the foreground reserve (plan_launch, then admission and model_room, where resource_control._view counts the quick worker
like hers). When both do not fit, the quick model is not loaded and the Brain room says why, with the numbers
(brain.quick_refused). It answers only beside her model: with her model stopped, no kind goes to it.

THE TURN. turns.request_for asks routes() once per owner request: {kind: QuickPort} for the kinds the rule gives the quick
model; turns.ask takes request.port_for(kind) (the quick port, or the request's own). Her clock prices each kind on the model
that answers it (the port's key), her line while it runs says "Asking the quick model", and the turn's record names the
model that answered (its 'model' and 'key'). Forget: a quick model that may hold a forgotten turn is stopped at once (its
memory goes with it) and is loaded again only by the owner.

THE MODEL CHECK. Its stage SQ (model_check --quick FILE; the Brain room passes the quick model it has) loads the quick model
beside hers, measures both on her typical question (300 tokens read, 40 written), sits the quick model's exam for the quick
kinds (at most 24 items a kind, interleaved over the papers; a kind with fewer items than the window sits them twice, and an
answer that changes is A5's CHANGED), and proposes the split ("Let the quick model answer NEXT and READ?", Use it and Undo in
the Brain room). Its results go into this computer's exam record and her clock's measured rates only from the Brain room
(keep_pair), never into the file for sending beyond counts. The speeds measured in the build container mean nothing for the
ThinkPad.

No floating point: rates are whole tokens a second, times whole milliseconds, ratios in whole tenths.
"""
from __future__ import annotations

import json
import time
import uuid

QUICK_KINDS = ('READ', 'PLAN', 'NEXT', 'MARKS', 'ASK')
SLOT = 'quick_worker'                  # local_brain's settings row brain.quick_worker
SELECTION = 'quick_selection'          # brain.quick_selection
SPLIT = 'quick_split'                  # brain.quick_split: {'offered': [...], 'previous': [...], 'at', 'by'}
REFUSED = 'quick_refused'              # brain.quick_refused: why the last load was refused, with its numbers
KEPT = 'quick_kept'                    # brain.quick_kept: the quick worker's kept prompts (brain_briefs' form)
MIB = 1024 * 1024
HEADROOM_MB = 2048                     # the quick model's cap: its rung's estimate and at least this much above it, or half
# of it. On the processor the worker's guard caps its address space (RLIMIT_AS), and the address space runs past the memory
# sum's estimate: measured here with the 2B at 4,096 tokens, 3,012 MiB at Ready against 2,334 MiB for the rung with two
# checkpoints and 256 MiB of cache (some 930 MiB above it before any cache is filled), 4,107 MiB after 70 exam questions on
# the rung for every kept prompt (3,942 MiB). Caps of 2,590 and 3,999 MiB stopped it (the second priming read; std::bad_alloc
# after some 60 questions), each time because local_brain.configuration took a larger rung than the cap was made for; it now
# takes the rung whose estimate and slack fit the cap (cap_mb), so the cap and the rung agree. On the Radeon the guard
# watches resident memory only.
EXAM_MOST = 24                         # items a kind sits in the pair stage (interleaved over the papers)
# Her typical question of each quick kind (new tokens read, tokens written): brain_clock.BUDGETS' typical sizes; PLAN's are
# K4b's measured second turn (about 120 new over a kept menu) and its answer cap.
TYPICAL = {'READ': (60, 24), 'PLAN': (120, 48), 'NEXT': (150, 8), 'MARKS': (700, 140), 'ASK': (30, 48)}
THINGS = {'READ': 'read your requests', 'PLAN': 'plan your objectives', 'NEXT': 'choose my next step', 'MARKS': 'read pages',
          'ASK': 'find the line that answers'}
SCOPE_WORDS = 'The speeds measured on this computer say nothing about another computer.'


# == the records =====================================================================================================
def _get(kernel, key, default=None):
    from . import local_brain
    return local_brain.get(kernel, key, default)


def _put(kernel, key, value, state=None, db=None):
    from . import local_brain
    return local_brain.put(kernel, key, value, state, db)


def big_worker(kernel):
    """Her model's worker when it runs the selected model, else None."""
    from . import local_brain
    worker = _get(kernel, 'worker', {}) or {};selection = _get(kernel, 'selection', {}) or {}
    if local_brain.worker_live(worker) and worker.get('model_id') == selection.get('model_id'):return worker
    return None


def quick_worker(kernel):
    """The quick model's worker when it runs its selection, else None."""
    from . import local_brain
    worker = _get(kernel, SLOT, {}) or {};selection = _get(kernel, SELECTION, {}) or {}
    if local_brain.worker_live(worker) and worker.get('model_id') == selection.get('model_id'):return worker
    return None


def name_of(kernel, model_id):
    """A model's name as her column says it (the weights file without its quantisation): 'Qwen3.5 2B'."""
    import re
    if not model_id:return None
    try:
        from . import local_brain
        value = local_brain.model(kernel, model_id)
    except (ValueError, KeyError, TypeError):
        return str(model_id)[:12]
    name = next((f['name'] for f in value.get('files') or () if f.get('role') == 'weights'), str(model_id)[:12])
    return re.sub(r'(?i)[-_.]?(q\d.*|f16|bf16)?\.gguf$', '', name).replace('-', ' ')


# == its own kept prompts ============================================================================================
def _store_class():
    from . import brain_briefs

    class QuickStore(brain_briefs.SettingsStore):
        """brain_briefs' kept prompts for the quick worker, in their own row (brain.quick_kept): the quick model keeps its own
        primed prompts, and her model's are never overwritten by it."""
        key = KEPT

        def load(self, worker):
            held = _get(self.kernel, self.key, {}) or {}
            return held if held.get('worker') == brain_briefs.identity(worker) else brain_briefs.empty(worker)

        def update(self, worker, change):
            from . import local_brain
            with self.kernel.db() as db:
                db.execute('BEGIN IMMEDIATE')
                held = local_brain.get(self.kernel, self.key, {}, db) or {}
                value = held if held.get('worker') == brain_briefs.identity(worker) else brain_briefs.empty(worker)
                out = change(value)
                local_brain.put(self.kernel, self.key, value, db=db)
            return out
    return QuickStore


def store(kernel):
    return _store_class()(kernel)


def forget_pending(kernel, worker):
    try:
        return bool(store(kernel).load(worker).get('forget'))
    except Exception:  # noqa: BLE001 - nothing to read: nothing marked
        return False


def _port_class():
    from . import turns

    class QuickPort(turns.LocalPort):
        """The quick model's worker as a turn port: LocalPort's calls, its own kept prompts (QuickStore). quick is True, so
        her line while it answers says so."""
        quick = True

        def __init__(self, worker, kernel=None):
            super().__init__(worker, kernel)
            if kernel is not None:self.store = store(kernel)

        def live(self):
            from . import local_brain
            return local_brain.worker_live(self.worker) and not (self.kernel is not None and forget_pending(self.kernel, self.worker))

        def not_live_reason(self):
            return 'FORGETTING' if self.kernel is not None and forget_pending(self.kernel, self.worker) else 'NO_MODEL'
    return QuickPort


def port(kernel, worker=None):
    """A QuickPort on the running quick model (or the worker given), or None."""
    worker = worker or quick_worker(kernel)
    return _port_class()(worker, kernel) if worker else None


# == the split: which quick kinds are offered to it (Undo puts every kind back) ======================================
def offered(kernel):
    """The quick kinds the split offers the quick model: all of them until the owner's Undo."""
    held = _get(kernel, SPLIT, None)
    if not isinstance(held, dict):return list(QUICK_KINDS)
    return [k for k in QUICK_KINDS if k in (held.get('offered') or ())]


def set_split(kernel, kinds=None, undo=False, again=False, by='owner'):
    """Undo: every kind back on her model (the offer before it is kept, for "Use the quick model again"). again: the offer
    before the Undo, or every quick kind. kinds: exactly these (the model check's proposal, used by the owner)."""
    before = offered(kernel);held = _get(kernel, SPLIT, None) or {}
    if undo:
        if not before:raise ValueError('QUICK_NOTHING_TO_UNDO: every kind is on her model already')
        value = {'offered': [], 'previous': before, 'at': time.time(), 'by': by, 'undone': True}
    elif again:
        value = {'offered': list(held.get('previous') or QUICK_KINDS), 'previous': before, 'at': time.time(), 'by': by}
    else:
        if kinds is None:raise ValueError('QUICK_SPLIT_UNSAID: say the kinds, Undo, or again')
        unknown = [k for k in (kinds or ()) if k not in QUICK_KINDS]
        if unknown:raise ValueError('QUICK_KIND_UNKNOWN: ' + ', '.join(unknown))
        value = {'offered': [k for k in QUICK_KINDS if k in (kinds or ())], 'previous': before, 'at': time.time(), 'by': by}
    _put(kernel, SPLIT, value, 'QUICK_SPLIT_UNDONE' if undo else 'QUICK_SPLIT_SET')
    return value


# == her clock on each model =========================================================================================
def _ratio(big_ms, quick_ms):
    tenths = int(big_ms) * 10 // max(1, int(quick_ms))
    return '%d.%dx' % (tenths // 10, tenths % 10)


def seconds(ms):
    ms = max(0, int(ms))
    return '%d.%d s' % (ms // 1000, ms % 1000 // 100)


def measured(clock, key):
    """True when her clock has rates of this key's own: the model check's (runtime_tuning.measured) or three turns each of
    reading and writing seen on it. The stand-ins (the 4B's quiet rates) are not a measurement."""
    if not key:return False
    try:
        from . import runtime_tuning
        if runtime_tuning.measured(key):return True
    except Exception:  # noqa: BLE001
        pass
    from .brain_clock import LEAST
    reads = sum(len(v) for slot, v in (getattr(clock, 'read', None) or {}).items() if slot[0] == key)
    writes = sum(len(v) for slot, v in (getattr(clock, 'write', None) or {}).items() if slot[0] == key)
    return reads >= LEAST and writes >= LEAST


def price(clock, key, kind):
    """Her clock's price of the kind's typical question on this key, in whole ms."""
    new, answer = TYPICAL[kind]
    return int(clock.price_ms(key, kind, new, answer, 50))


# == the rule ========================================================================================================
_PAPER_KINDS = {}


def paper_kinds():
    """The kinds the exam papers ask (model_exam), read once per process."""
    if 'kinds' not in _PAPER_KINDS:
        try:
            from . import model_exam
            papers, _ = model_exam.load_papers()
            _PAPER_KINDS['kinds'] = frozenset(i.get('kind') for p in papers for i in p.items)
        except Exception:  # noqa: BLE001 - no papers: no kind can pass
            _PAPER_KINDS['kinds'] = frozenset()
    return _PAPER_KINDS['kinds']


def _row(kind, model, why, words, **extra):
    return {'kind': kind, 'model': model, 'why': why, 'words': words, 'thing': THINGS.get(kind, kind.lower()), **extra}


def decide(kind, *, offer, big_key, quick_key, exam, clock, quick_name='the quick model', big_name='her model'):
    """Which model answers this kind, and why: a row {kind, model: 'quick' | 'big', why, words, price_ms, other_ms}.
    exam: {kind: model_exam.view} on the quick key (or None); clock: her clock."""
    if big_key is None:
        return _row(kind, 'big', 'NO_MODEL', 'her model is not running, so neither model answers it')
    priced = {'price_ms': price(clock, big_key, kind)}      # her clock, on the model that answers it
    if kind not in offer:
        return _row(kind, 'big', 'PUT_BACK', 'you put it back on %s (Undo)' % big_name, **priced)
    if quick_key is None:
        return _row(kind, 'big', 'NO_QUICK_MODEL', 'no quick model is running beside %s' % big_name, **priced)
    if kind not in paper_kinds():
        return _row(kind, 'big', 'NO_PAPER', '%s has no exam paper yet, so no model can pass it; %s keeps it' % (kind, big_name), **priced)
    held = (exam or {}).get(kind)
    if not held:
        return _row(kind, 'big', 'NOT_EXAMINED', '%s has not sat its exam for %s on this key' % (quick_name, kind), **priced)
    state, reason = held.get('state'), held.get('reason')
    if state == 'SWITCHED_OFF':
        return _row(kind, 'big', 'EXAM_SWITCHED_OFF', '%s failed its exam for %s on this key: %d of %d right%s' % (
            quick_name, kind, held.get('right', 0), held.get('n', 0), ', %d harmful' % held['harm'] if held.get('harm') else ''), exam=held, **priced)
    if state != 'EXAMINED':
        if reason == 'CHANGED':
            words = 'the same question got another answer from %s on this key; it sits its exam for %s again' % (quick_name, kind)
        elif reason == 'TOO_FEW':
            words = '%s has %d of the %d answers its exam for %s needs on this key' % (quick_name, held.get('n', 0), 20, kind)
        else:
            words = '%s got %d of its last %d right in its exam for %s on this key (19 needed)' % (quick_name, held.get('right', 0), held.get('n', 0), kind)
        return _row(kind, 'big', 'EXAM_NOT_PASSED', words, exam=held, **priced)
    if not (measured(clock, quick_key) and measured(clock, big_key)):
        return _row(kind, 'big', 'NOT_MEASURED', 'passed its exam for %s on this key, but the two models have not been measured '
                    'side by side on this computer' % kind, exam=held, **priced)
    quick_ms = price(clock, quick_key, kind);big_ms = priced['price_ms']
    if quick_ms >= big_ms:
        return _row(kind, 'big', 'NOT_FASTER', 'passed its exam for %s on this key, but it is not faster here (about %s against %s)' % (
            kind, seconds(quick_ms), seconds(big_ms)), exam=held, price_ms=big_ms, other_ms=quick_ms)
    return _row(kind, 'quick', 'PASSED_AND_FASTER', 'passed its exam for %s on this key, %s faster' % (kind, _ratio(big_ms, quick_ms)),
                exam=held, price_ms=quick_ms, other_ms=big_ms)


def _key(worker):
    from . import model_exam
    return model_exam.key_for(worker)['key'] if worker else None


def _exam(kernel, key, exam_store=None):
    if not key:return {}
    from . import model_exam
    try:
        return model_exam.states(exam_store or model_exam.KernelStore(kernel), key)
    except Exception:  # noqa: BLE001 - an unreadable record: nothing examined
        return {}


def rows(kernel, clock=None, big=None, quick=None, exam_store=None):
    """Every quick kind's row (decide), for the Brain room, the status and the routes."""
    from . import brain_clock
    clock = clock if clock is not None else brain_clock.clock(kernel)
    big = big if big is not None else big_worker(kernel)
    quick = quick if quick is not None else (quick_worker(kernel) if big else None)
    try:
        big_key = _key(big)
    except Exception:  # noqa: BLE001 - a worker that cannot be asked its template: her model only
        big_key = None
    try:
        quick_key = _key(quick)
    except Exception:  # noqa: BLE001
        quick_key = None
    exam = _exam(kernel, quick_key, exam_store)
    quick_name = name_of(kernel, quick.get('model_id')) if quick else 'the quick model'
    big_name = name_of(kernel, big.get('model_id')) if big else 'her model'
    offer = offered(kernel)
    out = [decide(k, offer=offer, big_key=big_key, quick_key=quick_key, exam=exam, clock=clock, quick_name=quick_name,
                  big_name=big_name) for k in QUICK_KINDS]
    for r in out:
        r['answered_by'] = quick_name if r['model'] == 'quick' else big_name
    return out, {'big_key': big_key, 'quick_key': quick_key, 'big_name': big_name, 'quick_name': quick_name if quick else None}


def routes(kernel, big_port, clock=None):
    """For turns.request_for: {kind: QuickPort} for the kinds the rule gives the quick model now. Never raises."""
    try:
        quick = quick_worker(kernel)
        if quick is None or big_port is None or not offered(kernel):return {}
        found, _ = rows(kernel, clock, big=big_port.worker, quick=quick)
        given = [r['kind'] for r in found if r['model'] == 'quick']
        if not given:return {}
        p = port(kernel, quick)
        return {k: p for k in given}
    except Exception:  # noqa: BLE001 - the quick model is for speed; her model answers every kind without it
        return {}


# == the memory sum for the pair =====================================================================================
def _mib(n):
    return '{:,} MiB'.format(int(n))


def pair_sum(kernel, big=None, quick=None):
    """The memory sum with both models in it, in whole MiB: each model's budget, estimate and resident memory, the reserve,
    and what is free beyond them (resource_control's one rule)."""
    from . import brain_runtime, local_brain, resource_control
    host = brain_runtime.host(profile=False)
    with kernel.db() as db:view = resource_control._view(kernel, db, host)
    out = {'reserve_mb': view['policy']['reserve_bytes'] // MIB, 'available_mb': (host.get('available_ram_bytes') or 0) // MIB,
           'total_mb': (host.get('total_ram_bytes') or 0) // MIB, 'free_beyond_mb': view['headroom_bytes'] // MIB}
    for name, worker in (('big', big), ('quick', quick)):
        if not worker:continue
        cfg = worker.get('config') or {}
        out[name] = {'budget_mb': int(cfg.get('memory_mb') or 0), 'estimate_mb': -(-int(cfg.get('estimated_peak_bytes') or 0) // MIB),
                     'resident_mb': (local_brain.usage(worker).get('rss_bytes') or 0) // MIB, 'context': worker.get('context')}
    parts = []
    if out.get('big'):parts.append("her model's budget %s" % _mib(out['big']['budget_mb']))
    if out.get('quick'):parts.append("the quick model's %s" % _mib(out['quick']['budget_mb']))
    if parts:
        out['words'] = 'The memory sum counts both: %s, with the %s reserve; %s is free beyond them.' % (
            ' and '.join(parts), _mib(out['reserve_mb']), _mib(out['free_beyond_mb']))
    return out


def cap_mb(estimate_bytes):
    """The quick model's memory cap in whole MiB: its estimate, rounded up, and the larger of HEADROOM_MB and half of it."""
    need = -(-int(estimate_bytes) // MIB)
    return need + max(HEADROOM_MB, need // 2)


def plan_launch(kernel, value, options=None):
    """The quick model's launch options beside her running model: her model's context, threads and backend unless asked
    otherwise, and a memory cap of its own estimate (the best reuse rung that fits) and HEADROOM_MB, which must fit in what
    is free beside her model's budget and the foreground reserve. Raises ValueError QUICK_* with the numbers, in words."""
    from . import brain_runtime, local_brain, resource_control, runtime_tuning
    big = big_worker(kernel)
    if big is None:raise ValueError('QUICK_NEEDS_HER_MODEL: load her model first; the quick model answers only beside it')
    if value.get('id') == big.get('model_id'):raise ValueError('QUICK_IS_HER_MODEL: choose another model for the quick one')
    cfg = big.get('config') or {}
    opts = {k: cfg[k] for k in ('context', 'threads') if isinstance(cfg.get(k), int)}
    opts['backend'] = cfg.get('requested_backend') or cfg.get('backend') or 'CPU'
    allowed = set(local_brain.OPTIONS['properties']) - {'model_id', 'slot', 'memory_mb', 'message', 'max_tokens', 'mode', 'conversation'}
    opts.update({k: v for k, v in (options or {}).items() if k in allowed})
    tuned = runtime_tuning.settings(opts)
    head = runtime_tuning.mtp_layers(value['inspection']) if tuned['mtp_draft'] else 0
    context = int(opts.get('context') or 2048)
    ladder = resource_control.reuse_ladder(value['inspection'], value['total_bytes'], context, tuned['kv_type'], head)
    host = brain_runtime.host(profile=False)
    with kernel.db() as db:view = resource_control._view(kernel, db, host)
    room = view['headroom_bytes']
    chosen = None
    for term in ladder:
        need = cap_mb(term['estimate'])
        if need * MIB <= room:chosen = (term, need);break
    pair = pair_sum(kernel, big)
    if chosen is None:
        need = cap_mb(ladder[-1]['estimate'])
        raise ValueError('QUICK_MODEL_DOES_NOT_FIT: the quick model needs %s at %s tokens; beside her model (its budget %s) and '
                         'the %s reserve, %s is free' % (_mib(need), '{:,}'.format(context), _mib((pair.get('big') or {}).get('budget_mb', 0)),
                                                         _mib(pair['reserve_mb']), _mib(room // MIB)))
    opts.update(memory_mb=chosen[1], slot='quick', model_id=value['id'])
    return opts, {**pair, 'quick_need_mb': chosen[1], 'quick_checkpoints': chosen[0].get('checkpoints'),
                  'quick_cache_mb': chosen[0].get('cache_mb')}


def refusal_words(text):
    code, _, rest = str(text).partition(': ')
    if code.startswith('QUICK_') and rest:return rest[:1].upper() + rest[1:] + '.'
    if 'MODEL_MEMORY_BUDGET_TOO_SMALL' in code or 'MEMORY' in code:return 'Both models do not fit in memory: ' + (rest or code) + '.'
    return (rest or code)[:300]


# == load, stop ======================================================================================================
def use(kernel, args, principal):
    """brain.quick.use: load a registered model beside her running model (a brain.activate job, slot quick). When both do not
    fit it is not loaded, and why is kept for the Brain room."""
    from . import local_brain
    value = local_brain.model(kernel, args['id'])
    try:
        opts, pair = plan_launch(kernel, value, args.get('options'))
        job = local_brain.submit(kernel, 'brain.activate', {'request_key': args.get('request_key') or 'brain-quick:' + uuid.uuid4().hex},
                                 principal, opts)
    except ValueError as exc:
        why = refusal_words(exc)
        held = {'model_id': value['id'], 'name': name_of(kernel, value['id']), 'why': why, 'code': str(exc).split(':', 1)[0], 'at': time.time()}
        _put(kernel, REFUSED, held, 'QUICK_NOT_LOADED')
        return {'state': 'NOT_LOADED', 'why': why, 'code': held['code']}
    _put(kernel, REFUSED, None)
    return {'state': 'QUEUED', 'job': job, 'job_id': job['id'], 'pair': pair}


def after_start(kernel, worker, cancelled=None):
    """The quick worker's own kept prompts, at Ready: its quick kinds' briefs, and READ's and PLAN's desks as they stand
    (brain_briefs, through a QuickPort, so they are kept in brain.quick_kept). Never raises."""
    from . import brain_briefs, turns
    out = {'primed': [], 'failed': [], 'desks': [], 'readback': None}
    try:
        p = port(kernel, worker)
        brain_briefs.kinds_to_prime()
        kinds = [turns.KINDS[k] for k in QUICK_KINDS if k in turns.KINDS]
        primed = brain_briefs.prime_all(p, kinds, cancelled)
        out['primed'] = [r['kind'] for r in primed['primed']];out['failed'] = primed['failed']
        desks = brain_briefs.open_desks(kernel, p, cancelled)
        out['desks'] = [{k: d.get(k) for k in ('kind', 'state', 'tokens', 'why') if d.get(k) is not None} for d in desks]
        back = brain_briefs.readback(worker)
        p.store.update(worker, lambda v: v.__setitem__('readback', back));out['readback'] = back
    except Exception as exc:  # noqa: BLE001 - priming is for speed
        out['failed'].append({'kind': '*', 'why': type(exc).__name__})
    return out


def run_job(kernel, job, options, value):
    """The brain.activate job with slot quick (local_brain.run_model_job hands it here): start the quick model beside hers
    through the same sealed start, probe it, keep it in its own slot and prime its own kinds. Her model is never stopped."""
    from . import local_brain
    from .resource_control import reserve_setting
    ident = job['id']
    if big_worker(kernel) is None:raise ValueError('QUICK_NEEDS_HER_MODEL: load her model first; the quick model answers only beside it')
    config = local_brain.configuration(value, options, kernel.root, 0, reserve_setting(kernel))
    local_brain.control_claim(kernel, ident)
    worker = None
    try:
        old = _get(kernel, SLOT, {}) or {}
        if old:stop_worker(kernel, old, 'QUICK_REPLACED')
        try:
            worker = local_brain.start_server(kernel, value, config, ident, slot=SLOT)
        except Exception as exc:
            if 'MEMORY' in str(exc):
                _put(kernel, REFUSED, {'model_id': value['id'], 'name': name_of(kernel, value['id']), 'why': refusal_words(exc),
                                       'code': str(exc).split(':', 1)[0], 'at': time.time()}, 'QUICK_NOT_LOADED')
            raise
        sample = local_brain.completion(worker, [{'role': 'user', 'content': 'Reply with the word ready.'}], 8)
        if not sample['text'].strip():raise ValueError('MODEL_PROBE_RETURNED_NO_TEXT')
        local_brain.verify_resident(value, worker)
        config = worker['config']
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            local_brain.check_job(kernel, ident, db)
            _put(kernel, SELECTION, {'model_id': value['id'], 'config': config, 'activated': time.time(), 'owner': job['owner']},
                 'QUICK_ACTIVATED', db)
            _put(kernel, SLOT, worker, 'QUICK_READY', db)
            _put(kernel, REFUSED, None, db=db)
        primed = after_start(kernel, worker, cancelled=lambda: local_brain.cancelled(kernel, ident))
        if not local_brain.worker_live(worker):      # stopped while its prompts were primed: said, with what its log says
            why = _stopped_why(worker)
            _put(kernel, REFUSED, {'model_id': value['id'], 'name': name_of(kernel, value['id']), 'why': why,
                                   'code': 'QUICK_STOPPED_AT_START', 'at': time.time()}, 'QUICK_NOT_LOADED')
            raise ValueError('QUICK_STOPPED_AT_START: ' + why)
        held = worker;worker = None
        return {'status': 'QUICK_ACTIVATED', 'model_id': value['id'], 'slot': SLOT, 'kept_briefs': primed,
                'seal': {k: (held.get('seal') or {}).get(k) for k in ('state', 'network', 'transport', 'digest')},
                'load_seconds': held.get('load_seconds'), 'memory_sum': config.get('memory_sum'), 'cloud_calls': 0}
    finally:
        if worker:
            stop_worker(kernel, worker, 'QUICK_LOAD_FAILED')
            if ((_get(kernel, SELECTION, {}) or {}).get('model_id')) == value['id']:_put(kernel, SELECTION, None)
        _put(kernel, 'control', {})


def _stopped_why(worker, when='while its prompts were primed'):
    from pathlib import Path
    try:
        with (Path(worker['key_file']).parent / 'runtime.log').open('rb') as stream:
            stream.seek(max(0, stream.seek(0, 2) - 65536));tail = stream.read().decode('utf-8', 'replace')
    except (OSError, KeyError, TypeError):
        tail = ''
    if 'GRAPHITE_HOST_MEMORY_LIMIT' in tail:return 'it stopped at its memory cap ' + when
    if 'bad_alloc' in tail or 'failed to allocate' in tail:return 'it could not allocate memory under its cap ' + when
    return 'it stopped %s (its local runtime log says why)' % when


def stop_worker(kernel, worker, reason):
    from . import local_brain
    try:
        local_brain.terminate(kernel, worker, reason)
    finally:
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if local_brain.worker_identity(_get_db(kernel, SLOT, db)) == local_brain.worker_identity(worker):
                _put(kernel, SLOT, {}, reason, db)


def _get_db(kernel, key, db):
    from . import local_brain
    return local_brain.get(kernel, key, {}, db) or {}


def stop(kernel, reason='QUICK_STOPPED'):
    """brain.quick.stop: the quick model stops; her model and every kind's answers go on (her model answers them all)."""
    worker = _get(kernel, SLOT, {}) or {}
    if worker:stop_worker(kernel, worker, reason)
    _put(kernel, SELECTION, None, reason)
    return {'state': 'STOPPED'}


def forgotten(kernel, turn, principal=None, reason='TURN_FORGOTTEN'):
    """A turn was forgotten (turns.forget): a quick model that may hold it (running when it was asked) is stopped at once, so
    nothing forgotten survives in its memory; the owner loads it again when he wants it. Returns NOTHING_HELD or STOPPED."""
    from . import local_brain
    worker = _get(kernel, SLOT, {}) or {}
    if not local_brain.worker_live(worker) or (worker.get('started') or 0) > (turn.get('at') or 0):return 'NOTHING_HELD'
    try:
        store(kernel).update(worker, lambda v: v.__setitem__('forget', {'at': time.time(), 'reason': reason}))
    except Exception:  # noqa: BLE001 - the stop below is what matters
        pass
    stop(kernel, 'QUICK_STOPPED_TO_FORGET')
    return 'STOPPED'


# == the view: status, her column's line ===========================================================================
def kept_summary(kernel, worker):
    value = store(kernel).load(worker)
    return {'kept': sorted({e['kind'] for e in value['kinds'].values() if e.get('primed') and e.get('kind')}),
            'desks': sorted({e['kind'] for e in value['kinds'].values() if e.get('desk') and e.get('kind')}),
            'missed': sum(e.get('missed', 0) for e in value['kinds'].values())}


def status(kernel, brief=False):
    """brain.quick.status: the pair, the split row by row (decide), her clock's price of each kind on the model that answers
    it, the memory sum, why the last load was refused, and her column's line."""
    big = big_worker(kernel);quick = quick_worker(kernel) if big else None
    found, names = rows(kernel, big=big, quick=quick)
    given = [r['kind'] for r in found if r['model'] == 'quick']
    line = ''
    if quick:      # her column's model line, short: the Brain room names the quick model and says why
        line = 'quick: %s' % (', '.join(given) if given else 'no kind yet')
    out = {'line': line, 'quick_kinds': given, 'rows': found, 'offered': offered(kernel),
           'big': {'model_id': big.get('model_id'), 'name': names['big_name'], 'key': names['big_key']} if big else None,
           'quick': {'model_id': quick.get('model_id'), 'name': names['quick_name'], 'key': names['quick_key'],
                     'backend': quick.get('backend'), 'context': quick.get('context'),
                     'seal': (quick.get('seal') or {}).get('state')} if quick else None,
           'refused': _get(kernel, REFUSED, None), 'scope': SCOPE_WORDS, 'stopped': None}
    held = _get(kernel, SLOT, {}) or {}
    if held and quick is None and held.get('model_id') == (_get(kernel, SELECTION, {}) or {}).get('model_id'):
        from . import local_brain
        if not local_brain.worker_live(held):      # it stopped by itself: said, so a missing quick model is never a mystery
            out['stopped'] = '%s stopped: %s. Her model answers every kind; load it again when you want it.' % (
                name_of(kernel, held.get('model_id')), _stopped_why(held, 'while it answered'))
    if brief:return {k: out[k] for k in ('line', 'quick_kinds')}
    if quick:
        try:
            out['kept'] = kept_summary(kernel, quick)
        except Exception:  # noqa: BLE001
            out['kept'] = None
    try:
        out['pair'] = pair_sum(kernel, big, quick)
    except Exception:  # noqa: BLE001 - memory could not be read now
        out['pair'] = None
    return out


# == the model check's stage SQ, and the Brain room's keeping of its results ==========================================
def exam_papers(kinds=QUICK_KINDS, most=EXAM_MOST, root=None):
    """The quick model's exam: for each quick kind at most `most` items, short ones first, taken in turn from each paper that
    asks the kind (CHOOSE and STEER both ask NEXT); a kind with fewer items than the window (20) sits them twice. Returns
    (papers as model_exam.Paper with those items, the kinds' item counts)."""
    from . import model_exam
    papers, _ = model_exam.load_papers(root)
    chosen = {}
    for kind in kinds:
        lists = [[(p, i) for i in sorted(p.items, key=lambda i: 0 if i.get('short') else 1) if i.get('kind') == kind] for p in papers]
        lists = [l for l in lists if l];picked = []
        while lists and len(picked) < most:
            for l in list(lists):
                if l and len(picked) < most:picked.append(l.pop(0))
                if not l:lists.remove(l)
        if picked:chosen[kind] = picked
    by_paper = {}
    counts = {}
    for kind, picked in chosen.items():
        rounds = 2 if len(picked) < model_exam.WINDOW else 1
        counts[kind] = {'items': len(picked), 'rounds': rounds}
        for _ in range(rounds):
            for p, item in picked:by_paper.setdefault(p.name, []).append(item)
    out = [model_exam.Paper(p.name, p.folder, p.head, by_paper[p.name]) for p in papers if p.name in by_paper]
    return out, counts


def sit(port_, kinds=QUICK_KINDS, most=EXAM_MOST, clock=None, paused=None, on_item=None):
    """Sit the quick model's exam on its port; the results (model_exam.sit's rows) and the item counts."""
    from . import model_exam
    papers, counts = exam_papers(kinds, most)
    return model_exam.sit(papers, port_, short=False, clock=clock, paused=paused, on_item=on_item), counts


def pair_stage(check):
    """model_check's stage SQ: load the quick model beside hers, measure both on her typical question, sit the quick
    model's exam for the quick kinds, and propose the split. Its rows name no path."""
    from pathlib import Path
    from . import brain_clock, model_check, model_exam, runtime_tuning
    quick_file = getattr(check.args, 'quick', None)
    if not quick_file:return {'state': 'NOT_RUN', 'why': 'optional, and not asked (--quick FILE)'}
    work = check.work
    added = work.add(quick_file)
    got = work.invoke('brain.quick.use', {'id': added['model_id']})
    if got.get('state') == 'NOT_LOADED':return {'state': 'NOT_RUN', 'why': got.get('why'), 'file': Path(quick_file).name}
    loaded = work.wait(got['job'])
    qp = port(work.kernel)
    if qp is None:return {'state': 'FAILED', 'why': 'the quick model did not stay running'}
    qkey = qp.key();bkey = check.key or check.port.key()
    rates = {}
    for name, p, k in (('big', check.port, bkey), ('quick', qp, qkey)):
        read, _ = check.gate.measure(lambda p=p: model_check.read_speed(p, runtime_tuning.TYPICAL_NEW, 'q-r-%d' % time.time_ns()))
        write, _ = check.gate.measure(lambda p=p: model_check.write_speed(p, runtime_tuning.TYPICAL_ANSWER, 'q-w-%d' % time.time_ns()))
        r, w = read.get('per_second'), write.get('per_second')
        rates[name] = {'key': k, 'read_per_second': r, 'write_per_second': w, 'typical_ms': runtime_tuning.typical_ms(r, w)}
        if r and w:runtime_tuning.remember(k, r, w, {}, measured_on='model check, the pair (1.0 M2)')
    clock = brain_clock.Clock()
    results, counts = sit(qp, clock=clock, paused=check.gate.wait)
    exam_store = model_exam.MemoryStore()
    kinds = model_exam.record(exam_store, qkey, results)
    found, names = rows(work.kernel, clock=clock, big=check.work.worker(), quick=qp.worker, exam_store=exam_store)
    given = [r['kind'] for r in found if r['model'] == 'quick']
    summary = model_exam.summarise(results)
    (check.run / 'quick_pair.local.json').write_text(json.dumps({'big': rates['big'], 'quick': {**rates['quick'], 'file': Path(quick_file).name},
                                                                 'results': model_exam.exportable(results)}, indent=1) + '\n', encoding='utf-8')
    card = ['%s beside %s (the quick model, loaded in %s s): her typical question (%d read, %d written) about %s against %s.' % (
        names['quick_name'], names['big_name'], (loaded.get('load_seconds') and int(loaded['load_seconds'])) or '?',
        runtime_tuning.TYPICAL_NEW, runtime_tuning.TYPICAL_ANSWER, seconds(rates['quick']['typical_ms'] or 0),
        seconds(rates['big']['typical_ms'] or 0))]
    card += ['%s: %s, %s' % (r['kind'], r['answered_by'], r['words']) for r in found]
    card.append('Proposed: let the quick model answer %s.' % ', '.join(given) if given else 'Proposed: nothing; her model keeps every kind.')
    card.append(SCOPE_WORDS)
    return {'file': Path(quick_file).name, 'rates': {k: {kk: vv for kk, vv in v.items() if kk != 'key'} for k, v in rates.items()},
            'exam': {'items': counts, 'summary': summary, 'kinds': kinds}, 'rows': [{k: r.get(k) for k in ('kind', 'model', 'why', 'words',
            'price_ms', 'other_ms')} for r in found], 'proposed': given, 'card': card, 'load_seconds': loaded.get('load_seconds')}


def keep_pair(kernel, run):
    """The Brain room, after a model check with a quick model: its exam results into this computer's exam record for the
    quick model's key, and both models' measured rates for her clock. Returns what was kept, or None."""
    from pathlib import Path
    from . import model_exam, runtime_tuning
    path = Path(run) / 'quick_pair.local.json'
    if not path.exists():return None
    held = json.loads(path.read_text(encoding='utf-8'))
    quick = held.get('quick') or {};big = held.get('big') or {}
    kept = {}
    if quick.get('key'):kept['kinds'] = model_exam.record(model_exam.KernelStore(kernel), quick['key'], held.get('results') or [])
    for name, r in (('big', big), ('quick', quick)):
        if r.get('key') and r.get('read_per_second') and r.get('write_per_second'):
            runtime_tuning.remember(r['key'], r['read_per_second'], r['write_per_second'], {}, measured_on='model check, the pair (1.0 M2)')
            kept[name] = True
    return kept


# == the Kernel's operations ===========================================================================================
ID = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
LAUNCH = {'type': 'object', 'additionalProperties': False, 'properties': {
    'context': {'type': 'integer', 'minimum': 512, 'maximum': 8192}, 'threads': {'type': 'integer', 'minimum': 1, 'maximum': 32},
    'backend': {'type': 'string', 'enum': ['AUTO', 'CPU', 'VULKAN']}, 'gpu_layers': {'type': 'integer', 'minimum': -1, 'maximum': 512}}}
FIELDS = {
    'brain.quick.status': ({'brief': {'type': 'boolean'}}, []),
    'brain.quick.use': ({'id': ID, 'options': LAUNCH, 'request_key': {'type': 'string', 'maxLength': 128}}, ['id']),
    'brain.quick.stop': ({}, []),
    'brain.quick.split': ({'undo': {'type': 'boolean'}, 'again': {'type': 'boolean'},
                           'kinds': {'type': 'array', 'items': {'type': 'string', 'enum': list(QUICK_KINDS)}}}, []),
}
SCOPES = {'brain.quick.status': 'read', 'brain.quick.use': 'approve', 'brain.quick.stop': 'execute', 'brain.quick.split': 'execute'}
OBSERVERS = ('brain.quick.status',)


def dispatch(kernel, op, args, principal):
    if op == 'brain.quick.status':return status(kernel, bool(args.get('brief')))
    if op == 'brain.quick.use':return use(kernel, args, principal)
    if op == 'brain.quick.stop':return stop(kernel)
    if op == 'brain.quick.split':
        value = set_split(kernel, args.get('kinds'), bool(args.get('undo')), bool(args.get('again')))
        return {'offered': value['offered'], 'previous': value.get('previous'), 'status': status(kernel, brief=True)}
    raise ValueError('QUICK_OPERATION_UNKNOWN')
