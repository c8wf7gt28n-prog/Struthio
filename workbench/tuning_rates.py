"""The rates the model check measured, carried out of its throwaway profile so her clock starts from them (1.0 M1b).

The model check runs on an invented workspace with a profile of its own (model_check.Work), removed when it closes. Its
tuning stage (S2T, 1.0 M1) and the pair stage (SQ, 1.0 M2) keep each launch's measured rates there
(runtime_tuning.remember, per model key: the key names the launch line's shape, so each setting tried has its own), and
so her clock (brain_clock, through runtime_tuning.measured) never saw them in the owner's profile.

carry_out() runs inside the check while its workspace is open: every rate it remembered, written beside the run as
tuning_rates.local.json (never for sending). keep() runs in the owner's profile: by the check itself once its workspace
is closed (so a run from the console reaches her clock too) and by the Brain room when the check it started ends (as
quick_model.keep_pair does for the pair); each rate is kept as measured, with what measured it. Keeping twice changes
nothing but the time it was kept.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

FILE = 'tuning_rates.local.json'
SCHEMA = 'graphite.tuning-rates/1'


def carry_out(run):
    """Inside the model check: the rates its own profile holds, written to the run folder. Returns how many."""
    from . import runtime_tuning
    try:
        held = json.loads(runtime_tuning._rates_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    rates = {str(k): v for k, v in (held.items() if isinstance(held, dict) else ())
             if isinstance(v, dict) and isinstance(v.get('read'), int) and isinstance(v.get('write'), int) and v['read'] > 0 and v['write'] > 0}
    if not rates:return 0
    path = Path(run) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'schema': SCHEMA, 'carried_at': int(time.time()), 'rates': rates}, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    os.chmod(tmp, 0o600);os.replace(tmp, path)
    return len(rates)


def keep(run):
    """In the owner's profile: each carried rate kept for her clock. Returns {'kept': n, 'by': [...]} or None when the run
    carried none."""
    from . import runtime_tuning
    path = Path(run) / FILE
    try:
        held = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(held, dict) or held.get('schema') != SCHEMA:return None
    kept = 0;by = set()
    for key, r in sorted((held.get('rates') or {}).items()):
        try:
            done = runtime_tuning.remember(key, int(r['read']), int(r['write']), r.get('settings') or {},
                                           measured_on=str(r.get('by') or 'model check'))
        except (KeyError, TypeError, ValueError, OSError):
            done = None
        if done:kept += 1;by.add(str(r.get('by') or 'model check'))
    return {'kept': kept, 'by': sorted(by)}


def words(kept):
    """One line for the check's console and the Brain room."""
    if not kept or not kept.get('kept'):return ''
    return ('Her clock now starts from the rates measured here: %d launch%s kept on this computer.' % (
        kept['kept'], '' if kept['kept'] == 1 else 'es'))
