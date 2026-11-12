"""Inspect an Ultra Cop snapshot and qualify a one-step thread-hint trial."""
from argparse import ArgumentParser
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from statistics import median
import time

from traffic_forecast import MIB, SOURCES, capture, example_trace, validated_samples
from workbench.host_observations import cpu_percent
from workbench.memory_forecast import evaluate, observe


SNAPSHOT = 'graphite.ultra-cop-snapshot/1'
RESOURCE_OBSERVATION = 'graphite.resource-observation/1'
PROPOSAL = 'graphite.ultra-cop-proposal/1'
COMPARISON = 'graphite.ultra-cop-comparison/1'
MIN_PAIRS = 3
MAX_PAIRS = 12
MAX_SNAPSHOT_AGE = 5
MAX_PROPOSAL_OBSERVATION_AGE = 60
RELATIVE_P95_ALLOWANCE = 0.05
P95_FLOOR_MS = 0.125
P95_CAP_MS = 2.0
MAX_SKIPPED_PROBE_FRACTION = 0.01
MIN_FOREGROUND_PROBES = 20


def _percent(value):
    return value if type(value) is int and 0 <= value <= 100 else None


def _cpu_counters(row):
    values = row.get('cpu_counters')
    if isinstance(values, list) and len(values) == 2 and all(
            type(value) is int and 0 <= value < 2**63 for value in values):
        return values
    return None


def _stall_delta(first, last):
    if not isinstance(first, dict) or not isinstance(last, dict):
        return None
    delta = {}
    for key in ('some', 'full'):
        earlier, later = first.get(key), last.get(key)
        if type(earlier) is int and type(later) is int and 0 <= earlier <= later < 2**63:
            delta[key] = later - earlier
    return delta or None


def snapshot(trace, *, live=False, budget_mib=3072):
    """Reduce a trace to the allowlisted, content-free fields an adviser needs."""
    rows, times, headrooms = validated_samples(trace)
    trend = None
    for at, headroom in zip(times, headrooms):
        trend = observe(trend, at, headroom) if headroom is not None else None
    latest = rows[-1]
    prediction = evaluate(trend, times[-1], headrooms[-1], budget_mib * MIB)
    cap = min(8, max(1, (os.cpu_count() or 2) - 1)) if live else None
    return dict(schema=SNAPSHOT, source=trace['source'], kind='LIVE_READBACK' if live else 'REPLAY',
                sampled_at_unix=latest.get('sampled_at_unix') if live else None,
                sample_count=len(rows), span_seconds=round(times[-1] - times[0], 3),
                available_bytes=latest['available_bytes'], reserve_bytes=latest['reserve_bytes'],
                reserved_future_bytes=latest['reserved_future_bytes'], headroom_bytes=headrooms[-1],
                forecast_horizon_seconds=prediction['horizon_seconds'],
                forecast_headroom_bytes=prediction['projected_headroom_bytes'] if prediction['eligible'] else None,
                foreground_active=latest['foreground_active'],
                cpu_busy_percent=cpu_percent(_cpu_counters(rows[0]), _cpu_counters(latest)),
                gpu_busy_percent=_percent(latest.get('gpu_busy_percent')),
                memory_stall_delta_us=_stall_delta(rows[0].get('memory_psi_total_us'),
                                                   latest.get('memory_psi_total_us')),
                background_threads=latest.get('background_threads') if live else None, thread_cap=cap)


def _adjacent(baseline, candidate, cap=8):
    return (type(baseline) is int and type(candidate) is int and type(cap) is int
            and 1 <= baseline <= cap <= 8 and 1 <= candidate <= cap and abs(candidate - baseline) == 1)


def _fresh_local(observation, now, max_age):
    if not isinstance(observation, dict):
        return False
    sampled = observation.get('sampled_at_unix')
    return (observation.get('kind') == 'LIVE_READBACK' and observation.get('source') == 'MEASURED_LOCAL'
            and type(sampled) in (int, float) and now - max_age <= sampled <= now)


def _trial_result(baseline, candidate, budget_mib, reason):
    return dict(decision='HOLD' if reason else 'READY_FOR_ISOLATED_TRIAL', reason=reason,
                baseline_threads=baseline, candidate_threads=candidate,
                requested_bytes=budget_mib * MIB, settings_changed=False)


def trial_preflight(current, *, baseline, candidate, budget_mib, now):
    """Recheck a current readback before a human starts an isolated trial."""
    reason = None
    if not _fresh_local(current, now, MAX_SNAPSHOT_AGE):
        reason = 'FRESH_LOCAL_SNAPSHOT_REQUIRED'
    elif current['background_threads'] != baseline or not _adjacent(baseline, candidate, current['thread_cap']):
        reason = 'THREAD_CHANGE_OUTSIDE_CURRENT_POLICY'
    elif current['foreground_active']:
        reason = 'FOREGROUND_HAS_PRIORITY'
    elif current['headroom_bytes'] is None or current['headroom_bytes'] < budget_mib * MIB:
        reason = 'INSUFFICIENT_OBSERVED_HEADROOM'
    elif (current['forecast_headroom_bytes'] is not None
            and current['forecast_headroom_bytes'] < budget_mib * MIB):
        reason = 'INSUFFICIENT_FORECAST_HEADROOM'
    return _trial_result(baseline, candidate, budget_mib, reason)


def observation_digest(observation):
    encoded = json.dumps(observation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return sha256(encoded).hexdigest()


def proposal_preflight(proposal, observation, read_current, *, clock=time.time):
    """Bind one advisory proposal to its input, then independently sample current conditions."""
    fields = {'schema', 'observation_sha256', 'baseline_threads', 'candidate_threads', 'budget_mib', 'reason'}
    if not isinstance(proposal, dict) or set(proposal) != fields or proposal['schema'] != PROPOSAL:
        raise ValueError('Expected only the fields of a Graphite Ultra Cop proposal.')
    baseline, candidate, budget = (proposal[key] for key in ('baseline_threads', 'candidate_threads', 'budget_mib'))
    if not _adjacent(baseline, candidate):
        raise ValueError('Propose adjacent thread hints in the 1 to 8 range.')
    if type(budget) is not int or not 1 <= budget <= 262144:
        raise ValueError('Use a whole budget of 1 to 262144 MiB.')
    if proposal['reason'] != 'COMPARE_BACKGROUND_THROUGHPUT':
        raise ValueError('Use the supported proposal reason COMPARE_BACKGROUND_THROUGHPUT.')
    digest = proposal['observation_sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Use a lowercase SHA-256 digest for the reviewed observation.')

    current = None
    if (not _fresh_local(observation, clock(), MAX_PROPOSAL_OBSERVATION_AGE)
            or observation.get('schema') not in (SNAPSHOT, RESOURCE_OBSERVATION)):
        trial = _trial_result(baseline, candidate, budget, 'PROPOSAL_OBSERVATION_NOT_FRESH_LOCAL')
    elif observation_digest(observation) != digest:
        trial = _trial_result(baseline, candidate, budget, 'PROPOSAL_OBSERVATION_MISMATCH')
    elif observation.get('background_threads') != baseline:
        trial = _trial_result(baseline, candidate, budget, 'PROPOSAL_BASELINE_MISMATCH')
    else:
        current = read_current(budget)
        now = clock()
        trial = (trial_preflight(current, baseline=baseline, candidate=candidate, budget_mib=budget, now=now)
                 if _fresh_local(observation, now, MAX_PROPOSAL_OBSERVATION_AGE)
                 else _trial_result(baseline, candidate, budget, 'PROPOSAL_OBSERVATION_NOT_FRESH_LOCAL'))
    return dict(proposal=proposal, snapshot=current, trial=trial)


def _positive(record, key):
    value = record.get(key) if isinstance(record, dict) else None
    if type(value) not in (int, float) or not 0.000001 <= value <= 10**12:
        raise ValueError(f'Expected a positive bounded {key} in every observation.')
    return value


def _skipped_probe_fraction(arm):
    """Keep missing probe coverage distinct from a measured zero."""
    keys = ('foreground_samples', 'foreground_skipped_slots')
    if all(key not in arm for key in keys):
        return None
    sampled, skipped = (arm.get(key) for key in keys)
    if (type(sampled) is not int or not MIN_FOREGROUND_PROBES <= sampled <= 10**12
            or type(skipped) is not int or not 0 <= skipped <= 10**12):
        raise ValueError('Probe counters require at least 20 samples and a nonnegative skipped-slot count.')
    return skipped / (sampled + skipped)


def score(comparison):
    """Screen interleaved, same-workload pairs before any consideration of use."""
    if (not isinstance(comparison, dict) or comparison.get('schema') != COMPARISON
            or comparison.get('source') not in SOURCES):
        raise ValueError('Expected a comparison with a declared observation source.')
    baseline, candidate = (comparison.get(key) for key in ('baseline_threads', 'candidate_threads'))
    if not _adjacent(baseline, candidate):
        raise ValueError('Compare adjacent thread hints in the 1 to 8 range.')
    workload = comparison.get('workload')
    if not isinstance(workload, str) or not 1 <= len(workload.strip()) <= 128:
        raise ValueError('Provide the identifier of the fixed workload used for all pairs.')
    pairs = comparison.get('pairs')
    if not isinstance(pairs, list) or not MIN_PAIRS <= len(pairs) <= MAX_PAIRS:
        raise ValueError(f'Provide {MIN_PAIRS} to {MAX_PAIRS} interleaved observation pairs.')
    method = comparison.get('method')
    period = (_positive(method, 'foreground_period_ms')
              if isinstance(method, dict) and 'foreground_period_ms' in method else None)
    # For the 5 ms CPU probe, a sub-0.125 ms change fits within 2.5% of one period.
    floor = P95_FLOOR_MS if period is None else min(P95_FLOOR_MS, period / 40)
    cap = P95_CAP_MS if period is None else min(P95_CAP_MS, period / 4)
    throughput, latency, deltas, pair_checks = [], [], [], []
    observed_probe_arms = 0
    work_units = None
    for index, pair in enumerate(pairs):
        expected_first = 'baseline' if index % 2 == 0 else 'candidate'
        if not isinstance(pair, dict) or pair.get('first') != expected_first:
            raise ValueError('Alternate the run order of consecutive pairs, starting with baseline.')
        before, after = pair.get('baseline'), pair.get('candidate')
        before_units = _positive(before, 'completed_units')
        if before_units != _positive(after, 'completed_units') or work_units not in (None, before_units):
            raise ValueError('Every observation must complete identical work units.')
        work_units = before_units
        throughput.append(_positive(before, 'seconds') / _positive(after, 'seconds'))
        baseline_p95 = _positive(before, 'foreground_p95_ms')
        candidate_p95 = _positive(after, 'foreground_p95_ms')
        latency.append(candidate_p95 / baseline_p95)
        delta = candidate_p95 - baseline_p95
        deltas.append(delta)
        allowance = min(cap, max(floor, baseline_p95 * RELATIVE_P95_ALLOWANCE))
        holds = []
        if candidate_p95 > baseline_p95 + allowance:
            holds.append('PAIRED_P95_INCREASE')
        if period is not None and candidate_p95 > period:
            holds.append('CANDIDATE_P95_EXCEEDS_PROBE_PERIOD')
        probe_fractions = {}
        for name, arm in (('baseline', before), ('candidate', after)):
            fraction = _skipped_probe_fraction(arm)
            if fraction is not None:
                observed_probe_arms += 1
                if fraction > MAX_SKIPPED_PROBE_FRACTION:
                    holds.append(name.upper() + '_MISSED_PROBE_BUDGET')
            probe_fractions[name] = None if fraction is None else round(fraction, 6)
        pair_checks.append(dict(pair=index + 1, p95_delta_ms=round(delta, 6),
                                allowed_increase_ms=round(allowance, 6),
                                skipped_probe_fractions=probe_fractions, holds=holds))
    if observed_probe_arms not in (0, len(pairs) * 2):
        raise ValueError('Probe counters must be reported for every arm or omitted throughout.')
    median_rate, median_latency = median(throughput), median(latency)
    if any(check['holds'] for check in pair_checks):
        outcome = 'KEEP_BASELINE_FOREGROUND_REGRESSION'
    elif median_rate >= 1.10 or (median_latency <= 0.90 and median(deltas) <= -floor and median_rate >= 0.95):
        outcome = 'CANDIDATE_WORTH_RECHECKING'
    else:
        outcome = 'KEEP_BASELINE_BENEFIT_TOO_SMALL'
    return dict(source=comparison['source'], workload=workload, pairs=len(pairs),
                median_throughput_ratio=round(median_rate, 4), median_latency_ratio=round(median_latency, 4),
                worst_latency_ratio=round(max(latency), 4), median_latency_delta_ms=round(median(deltas), 6),
                foreground_guard=dict(relative_allowance=RELATIVE_P95_ALLOWANCE, floor_ms=floor, cap_ms=cap,
                                      probe_period_ms=period, max_skipped_probe_fraction=MAX_SKIPPED_PROBE_FRACTION,
                                      coverage='REPORTED' if observed_probe_arms else 'NOT_REPORTED',
                                      pairs=pair_checks), outcome=outcome, settings_changed=False)


def _unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('JSON objects must use unique field names.')
    return result


def _read(path):
    with path.open('rb') as stream:
        data = stream.read(512 * 1024 + 1)
    if len(data) > 512 * 1024:
        raise ValueError('JSON input exceeds 512 KiB.')
    return json.loads(data, object_pairs_hook=_unique_object)


def main():
    parser = ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('snapshot', help='summarize live readback, an existing trace, or the demo')
    origin = inspect.add_mutually_exclusive_group()
    origin.add_argument('--workspace', type=Path)
    origin.add_argument('--trace', type=Path)
    trial = commands.add_parser('trial', help='check one proposed thread hint using a fresh readback')
    trial.add_argument('--workspace', type=Path, required=True)
    trial.add_argument('--baseline-threads', type=int, required=True)
    trial.add_argument('--candidate-threads', type=int, required=True)
    trial.add_argument('--budget-mib', type=int, required=True)
    advisory = commands.add_parser('check-proposal', help='review a bound one-step advisory proposal without applying it')
    advisory.add_argument('proposal', type=Path)
    advisory.add_argument('--observation', type=Path, required=True)
    advisory.add_argument('--workspace', type=Path, required=True)
    compare = commands.add_parser('score', help='score paired trials without applying settings')
    compare.add_argument('comparison', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'score':
            result = score(_read(args.comparison))
        elif args.command == 'check-proposal':
            def read_current(budget):
                return snapshot(capture(args.workspace, 3, 1.0, include_policy=True), live=True, budget_mib=budget)

            result = proposal_preflight(_read(args.proposal), _read(args.observation), read_current)
        else:
            budget = args.budget_mib if args.command == 'trial' else 3072
            if not 1 <= budget <= 262144:
                raise ValueError('Use a budget of 1 to 262144 MiB.')
            if args.workspace:
                trace = capture(args.workspace, 3, 1.0, include_policy=True)
            else:
                trace = _read(args.trace) if args.trace else example_trace()
            result = snapshot(trace, live=args.workspace is not None, budget_mib=budget)
            if args.command == 'trial':
                result = dict(snapshot=result, trial=trial_preflight(
                    result, baseline=args.baseline_threads, candidate=args.candidate_threads,
                    budget_mib=budget, now=time.time()))
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Ultra Cop: {exc}\n')


if __name__ == '__main__':
    main()
