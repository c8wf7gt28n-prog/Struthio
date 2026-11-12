"""Measure a bounded paired CPU workload for `ultra_cop.py score`.

Each arm runs in a fresh child process. Its foreground latency proxy measures
the scheduled wake and completion of a small CPU request during background work.
The results apply to this host and workload. No Graphite settings are changed.
"""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import pbkdf2_hmac
import json
from math import ceil, floor
import os
from pathlib import Path
import platform
import subprocess
import sys
from threading import Barrier
from time import perf_counter, sleep

from ultra_cop import COMPARISON, MIN_FOREGROUND_PROBES, MIN_PAIRS


BASELINE_THREADS = 2
CANDIDATE_THREADS = 3
UNITS = 120
BACKGROUND_ITERATIONS = 100_000
FOREGROUND_ITERATIONS = 256
FOREGROUND_PERIOD = 0.005
ARM_TIMEOUT = 15


def cpu_unit(iterations):
    return pbkdf2_hmac('sha256', b'graphite', b'cpu-comparison', iterations)


def measure_arm(threads):
    """Time equal background work and the foreground requests due during it."""
    started = 0.0

    def mark_start():
        nonlocal started
        started = perf_counter()

    ready = Barrier(threads + 1, action=mark_start, timeout=3)

    def background():
        cpu_unit(FOREGROUND_ITERATIONS)  # Warm each worker before starting the clock.
        ready.wait()
        for _ in range(UNITS // threads):
            cpu_unit(BACKGROUND_ITERATIONS)
        return UNITS // threads, perf_counter()

    probes = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        work = [executor.submit(background) for _ in range(threads)]
        ready.wait()
        due = started + FOREGROUND_PERIOD
        while not all(task.done() for task in work):
            delay = due - perf_counter()
            if delay > 0:
                sleep(delay)
            cpu_unit(FOREGROUND_ITERATIONS)
            observed = perf_counter()
            probes.append((due, (observed - due) * 1000))
            # A late request represents its own deadline. Skip expired slots.
            due = started + (floor((observed - started) / FOREGROUND_PERIOD) + 1) * FOREGROUND_PERIOD
        runs = [task.result() for task in work]

    finished = max(end for _, end in runs)
    latencies = sorted(value for due, value in probes if due < finished)
    if len(latencies) < MIN_FOREGROUND_PROBES:
        raise ValueError(f'Only {len(latencies)} foreground samples during background work.')
    seconds = finished - started
    return dict(completed_units=sum(count for count, _ in runs), seconds=seconds,
                foreground_p95_ms=latencies[ceil(0.95 * len(latencies)) - 1],
                foreground_samples=len(latencies),
                foreground_skipped_slots=max(0, floor(seconds / FOREGROUND_PERIOD) - len(latencies)))


def child_arm(threads):
    command = [sys.executable, str(Path(__file__).resolve()), '--worker-threads', str(threads)]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=ARM_TIMEOUT)
    return json.loads(completed.stdout)


def measure():
    arms = {'baseline': BASELINE_THREADS, 'candidate': CANDIDATE_THREADS}
    pairs = []
    for index in range(MIN_PAIRS):
        first, second = ('baseline', 'candidate') if index % 2 == 0 else ('candidate', 'baseline')
        pairs.append({'first': first, first: child_arm(arms[first]), second: child_arm(arms[second])})
    logical_cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count()
    return dict(schema=COMPARISON, source='MEASURED_LOCAL',
                workload='Fixed PBKDF2-SHA256 batch with periodic foreground CPU requests',
                baseline_threads=BASELINE_THREADS, candidate_threads=CANDIDATE_THREADS,
                host=dict(scope='CURRENT_EXECUTION_HOST', system=platform.system(),
                          machine=platform.machine(), python=platform.python_version(),
                          visible_logical_cpus=logical_cpus),
                method=dict(background_iterations_per_unit=BACKGROUND_ITERATIONS,
                            foreground_iterations=FOREGROUND_ITERATIONS,
                            foreground_period_ms=FOREGROUND_PERIOD * 1000,
                            foreground_latency='Scheduled wake to completion, nearest-rank p95',
                            arm_timeout_seconds=ARM_TIMEOUT), pairs=pairs)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--worker-threads', type=int, choices=(BASELINE_THREADS, CANDIDATE_THREADS),
                        help='run one isolated arm')
    args = parser.parse_args()
    try:
        result = measure_arm(args.worker_threads) if args.worker_threads else measure()
        print(json.dumps(result, indent=2, allow_nan=False))
    except subprocess.TimeoutExpired:
        parser.exit(2, f'Ultra Cop measurement: an arm exceeded {ARM_TIMEOUT} seconds.\n')
    except subprocess.CalledProcessError as error:
        parser.exit(2, error.stderr or 'Ultra Cop measurement: an arm failed.\n')
    except (OSError, ValueError) as error:
        parser.exit(2, f'Ultra Cop measurement: {error}\n')


if __name__ == '__main__':
    main()
