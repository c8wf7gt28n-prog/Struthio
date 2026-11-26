"""Her model's memory cap on the processor, and what the owner's cap gives her, said before loading (1.0 M1b).

On the processor the worker guard (brain_worker) caps the runtime's address space (RLIMIT_AS) as well as watching its
resident memory, and llama-server's address space runs past the memory sum's estimate: some 930 MiB at Ready with the 4B
and the 2B here (M2, measured from /proc), more as the prompt cache fills. A cap the owner set near her estimate could
therefore end in std::bad_alloc as M1's larger prompt cache filled, though her resident memory stayed at the estimate
(4,645 MiB at Ready against the 4B's 4,669 MiB, M2).

Her cap stays the owner's: it is the budget the memory rule admits and the resident memory the guard holds her to. What
changes is the address-space limit on the processor: the larger of her cap and her rung's estimate with the room M2 gives
the quick model (quick_model.cap_mb, the one formula: the estimate and the larger of 2,048 MiB and half of it). The rung is
the one her cap holds (local_brain.configuration), and the room is that rung's, so the limit and the rung agree. On the
Radeon the guard watches resident memory only, as before.

plan() says, before loading, what the launch fields give her, with the numbers: every kept prompt with room above her
estimate; every kept prompt but close to it; fewer kept prompts; or not loaded, with the least cap that loads. The Brain
room shows it under the launch fields, and the model check's S0 records it.
"""
from __future__ import annotations

MIB = 1024 * 1024


def _mib(n):
    return '{:,} MiB'.format(int(n))


def _up(n_bytes):
    """Bytes in whole MiB, rounded up (the memory rule's own rounding)."""
    return -(-int(n_bytes) // MIB)


def room_mb(estimate_bytes):
    """Her rung's estimate with the quick model's room above it, in whole MiB (quick_model.cap_mb: M2's one formula)."""
    from .quick_model import cap_mb
    return cap_mb(estimate_bytes)


def address_space_mb(config, backend=None):
    """The worker guard's address-space limit for this launch: on the processor the larger of the budget and the rung's
    estimate with its room; None on the Radeon, where the guard watches resident memory only."""
    backend = backend or (config or {}).get('backend') or 'CPU'
    if backend != 'CPU':return None
    budget = int((config or {}).get('memory_mb') or 0)
    estimate = int((config or {}).get('estimated_peak_bytes') or 0)
    if not estimate:return budget or None
    return max(budget, room_mb(estimate))


def _rung_words(config, full, rungs):
    if rungs <= 1:return ''
    if (config.get('checkpoints'), config.get('prompt_cache_mb')) == (full.get('checkpoints'), full.get('cache_mb')):
        return ' with every kept prompt'
    if not config.get('checkpoints') and not config.get('prompt_cache_mb'):
        return ' with no kept prompt (reuse off)'
    return ' with %s checkpoints and a %s prompt cache' % (config.get('checkpoints'), _mib(config.get('prompt_cache_mb') or 0))


def plan(value, options=None, root=None, reclaimable_bytes=0, reserve_mb=None):
    """What these launch options give her model, before anything loads: a dict with state (AUTO, ROOMY, CLOSE, FEWER or
    NOT_LOADED), the numbers in whole MiB and her words. Never starts anything; never raises for a refusal."""
    from . import local_brain, resource_control, runtime_tuning
    options = dict(options or {})
    cap = int(options.get('memory_mb') or 0) or None
    context = int(options.get('context') or 2048)
    out = {'cap_mb': cap, 'context': context}
    full = least = None;rungs = 0
    try:
        tuned = runtime_tuning.settings(options)
        head = runtime_tuning.mtp_layers(value['inspection']) if tuned['mtp_draft'] else 0
        ladder = resource_control.reuse_ladder(value['inspection'], value['total_bytes'], context, tuned['kv_type'], head)
        if options.get('reuse') is False:ladder = ladder[-1:]
        full, least, rungs = ladder[0], ladder[-1], len(ladder)
        out.update(full_mb=_up(full['estimate']), least_mb=_up(least['estimate']), room_mb=room_mb(full['estimate']))
    except (ValueError, KeyError, TypeError):
        pass
    tokens = '{:,}'.format(context)
    try:
        config = local_brain.configuration(value, options, root, reclaimable_bytes, reserve_mb)
    except ValueError as exc:
        code, _, rest = str(exc).partition(': ')
        out.update(state='NOT_LOADED', code=code)
        if cap and full is not None and code == 'MODEL_MEMORY_BUDGET_TOO_SMALL' and cap < out['least_mb']:
            out['words'] = ("She will not load: your %s cap is below her model's %s estimate at %s tokens%s. Set at least %s%s." % (
                _mib(cap), _mib(out['least_mb']), tokens, ' even with no kept prompt' if rungs > 1 else '', _mib(out['least_mb']),
                ('; %s keeps every prompt' % _mib(out['full_mb'])) if rungs > 1 else ''))
        else:
            text = rest or code
            out['words'] = 'She will not load with these fields: ' + text[:1].lower() + text[1:] + '.'
        return out
    need = _up(config['estimated_peak_bytes'])
    space = address_space_mb(config)
    out.update(backend=config['backend'], memory_mb=config['memory_mb'], estimate_mb=need, checkpoints=config.get('checkpoints'),
               prompt_cache_mb=config.get('prompt_cache_mb'), address_space_mb=space)
    held = _rung_words(config, full or {}, rungs)
    every = full is None or need >= out['full_mb']
    if not cap:
        out['state'] = 'AUTO'
        words = 'Auto gives her %s for her %s estimate at %s tokens%s.' % (_mib(config['memory_mb']), _mib(need), tokens, held)
    elif every and cap >= out.get('room_mb', 0):
        out['state'] = 'ROOMY'
        words = 'Fits with room: your %s cap holds her %s estimate at %s tokens%s.' % (_mib(cap), _mib(need), tokens, held)
    elif every:
        out['state'] = 'CLOSE'
        words = ('Close: your %s cap holds her %s estimate at %s tokens%s, %s above it. If her memory grows past your cap she is '
                 'stopped; %s gives her the room her quick model is given.' % (
                     _mib(cap), _mib(need), tokens, held, _mib(cap - need), _mib(out['room_mb'])))
    else:
        out['state'] = 'FEWER'
        words = ('Fewer kept prompts: your %s cap is below the %s she needs with every kept prompt at %s tokens, so she loads%s '
                 '(%s). %s keeps every one.' % (_mib(cap), _mib(out['full_mb']), tokens, held, _mib(need), _mib(out['full_mb'])))
    if space and space > int(config['memory_mb']):
        words += (' On the processor her address space may reach %s (her runtime reserves more than it uses) while her memory '
                  'is held to %s.' % (_mib(space), _mib(config['memory_mb'])))
    out['words'] = words
    return out
