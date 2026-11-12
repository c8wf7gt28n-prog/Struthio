"""Record and replay a short headroom trace without controlling Graphite jobs."""
from argparse import ArgumentParser
from bisect import bisect_right
from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workbench.memory_forecast import HALF_LIFE_SECONDS, HORIZON_SECONDS, evaluate, observe


SCHEMA = 'graphite.traffic-forecast/1'
MAX_SAMPLES = 120
MIB = 1024**2
MEMORY_FIELDS = ('available_bytes', 'reserve_bytes', 'reserved_future_bytes')
SOURCES = ('MEASURED_LOCAL', 'SYNTHETIC_DEMO')


class Readback:
    """Supply the snapshot's database interface without initializing a Kernel."""

    def __init__(self, workspace):
        path = workspace.resolve() / '.ledger' / 'engineering.sqlite3'
        if not path.is_file():
            raise ValueError('Pass the workspace of an existing Graphite desk.')
        self.uri = path.as_uri() + '?mode=ro'

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.uri, uri=True, timeout=1)
        try:
            db.execute('BEGIN')
            yield db
        finally:
            db.close()


def memory_stalls():
    try:
        rows = Path('/proc/pressure/memory').read_text(encoding='ascii').splitlines()
        return {fields[0]: int(item.removeprefix('total='))
                for fields in map(str.split, rows) if fields and fields[0] in ('some', 'full')
                for item in fields[1:] if item.startswith('total=')}
    except (OSError, ValueError):
        return None


def capture(workspace, count, interval, *, include_policy=False):
    from workbench import host_observations, resource_control
    from workbench.engineering_kernel import Principal

    readback = Readback(workspace)
    principal = Principal('traffic-forecast-readback')
    start = time.monotonic()
    samples = []
    for _ in range(count):
        began = time.monotonic()
        sampled_at = time.time()
        traffic = resource_control.snapshot(readback, principal)
        sample = {'at_seconds': began - start,
                  **{name: traffic[name] for name in MEMORY_FIELDS},
                  'foreground_active': traffic['foreground_active'],
                  'memory_psi_total_us': memory_stalls(),
                  'gpu_busy_percent': host_observations.gpu()}
        if include_policy:
            sample.update(sampled_at_unix=sampled_at, cpu_counters=host_observations.cpu(),
                          background_threads=traffic['policy']['background_threads'])
        samples.append(sample)
        if len(samples) < count:
            time.sleep(max(0, began + interval - time.monotonic()))
    return {'schema': SCHEMA, 'source': 'MEASURED_LOCAL', 'samples': samples}


def example_trace():
    reserve = 2048 * MIB
    future = 512 * MIB
    headroom_gib = (5.6, 5.2, 4.6, 4.0, 3.5, 3.1, 2.4, 1.8, 2.1, 2.9, 3.7, 4.5, 5.1, 5.4, 5.6, 5.7)
    return {'schema': SCHEMA, 'source': 'SYNTHETIC_DEMO',
            'samples': [{'at_seconds': i, 'available_bytes': round(gib * 1024 * MIB) + reserve + future,
                         'reserve_bytes': reserve, 'reserved_future_bytes': future, 'foreground_active': False}
                        for i, gib in enumerate(headroom_gib)]}


def validated_samples(trace):
    if not isinstance(trace, dict) or trace.get('schema') != SCHEMA or trace.get('source') not in SOURCES:
        raise ValueError('Expected a Graphite traffic trace with a declared source.')
    rows = trace.get('samples')
    if not isinstance(rows, list) or not 2 <= len(rows) <= MAX_SAMPLES:
        raise ValueError(f'A traffic trace must have 2 to {MAX_SAMPLES} observations.')
    times, headrooms = [], []
    for row in rows:
        at = row.get('at_seconds') if isinstance(row, dict) else None
        if type(at) not in (int, float) or not 0 <= at <= 3600 or (times and at - times[-1] < 0.001):
            raise ValueError('Trace timestamps must increase by at least 1 ms and stay within one hour.')
        available, reserve, future = (row.get(name) for name in MEMORY_FIELDS)
        measured = (reserve, future) if available is None else (available, reserve, future)
        if (any(type(value) is not int or not 0 <= value <= 2**63-1 for value in measured)
                or type(row.get('foreground_active')) is not bool):
            raise ValueError('Expected byte counts and a boolean foreground lease in every observation.')
        times.append(at)
        headrooms.append(None if available is None else max(0, available - reserve - future))
    return rows, times, headrooms


def replay(trace, budget_mib):
    rows, times, headrooms = validated_samples(trace)
    budget = budget_mib * MIB
    results = []
    scores = {name: dict(admit=0, hold=0, observed_drop_after_admit=0, hold_without_observed_drop=0)
              for name in ('persistence', 'ewma')}
    trend = None
    unscored = 0
    for i, headroom in enumerate(headrooms):
        at = times[i]
        trend = observe(trend, at, headroom) if headroom is not None else None
        forecast = evaluate(trend, at, headroom, budget) if headroom is not None else {}
        eligible = headroom is not None and headroom >= budget and not rows[i]['foreground_active']
        estimate = {'persistence': eligible, 'ewma': eligible and forecast.get('outcome') != 'defer'}

        cutoff = at + HORIZON_SECONDS
        window = headrooms[i:bisect_right(times, cutoff)]
        observed = min(window) if cutoff <= times[-1] and len(window) > 1 and None not in window else None
        if eligible:
            if observed is None:
                unscored += 1
            else:
                for name, admit in estimate.items():
                    scores[name]['admit' if admit else 'hold'] += 1
                    scores[name]['observed_drop_after_admit'] += admit and observed < budget
                    scores[name]['hold_without_observed_drop'] += not admit and observed >= budget
        results.append({'at_seconds': at, 'headroom_bytes': headroom,
                        'ewma_forecast_min_bytes': forecast.get('projected_headroom_bytes'),
                        'forecast_reason': forecast.get('reason'), 'sampled_future_min_bytes': observed, **estimate})
    return {'source': trace['source'], 'budget_mib': budget_mib, 'horizon_seconds': HORIZON_SECONDS,
            'ewma_half_life_seconds': HALF_LIFE_SECONDS, 'eligible_but_unscored': unscored, 'scores': scores,
            'scope': 'One newly arriving background batch per sampled time. Scoring starts where '
                     'current headroom and the foreground lease permit it.',
            'limits': 'Recorded future samples do not establish what would happen if Graphite admitted or held a batch. '
                      'Live wait history, queue and lane checks are outside this replay. '
                      'Stall and GPU-busy observations are not bandwidth.',
            'samples': results}


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    sample = commands.add_parser('capture', help='record local readback and optional Linux counters')
    sample.add_argument('--workspace', type=Path, required=True)
    sample.add_argument('--output', type=Path, required=True)
    sample.add_argument('--samples', type=int, default=30)
    sample.add_argument('--interval', type=float, default=1.0, help='seconds between observations')
    report = commands.add_parser('replay', help='compare capacity suggestions on a trace or the synthetic demo')
    report.add_argument('trace', nargs='?', type=Path)
    report.add_argument('--budget-mib', type=int, default=3072)
    args = parser.parse_args()

    try:
        if args.command == 'capture':
            if not 2 <= args.samples <= MAX_SAMPLES or not 0.5 <= args.interval <= 5:
                raise ValueError(f'Use 2 to {MAX_SAMPLES} samples and a 0.5 to 5 second interval.')
            if args.output.exists():
                raise ValueError('Choose a new trace filename.')
            trace = capture(args.workspace, args.samples, args.interval)
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(trace, indent=2) + '\n')
            return
        if not 1 <= args.budget_mib <= 262144:
            raise ValueError('Use a budget of 1 to 262144 MiB.')
        if args.trace and args.trace.stat().st_size > 512 * 1024:
            raise ValueError('Trace exceeds the 512 KiB replay limit.')
        trace = json.loads(args.trace.read_text(encoding='utf-8')) if args.trace else example_trace()
        print(json.dumps(replay(trace, args.budget_mib), indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Traffic forecast: {exc}\n')


if __name__ == '__main__':
    main()
