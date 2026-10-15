#!/usr/bin/env python3
"""Run host + HDL checks, retain complete output, and reject diagnostic-only exits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iverilog', default='iverilog')
    parser.add_argument('--vvp', default='vvp')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    logs = root / 'verification_logs'
    logs.mkdir(exist_ok=True)
    versions = []
    for command in (['cc', '--version'], [sys.executable, '--version'],
                    [args.iverilog, '-V'], [args.vvp, '-V']):
        result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        versions.append('$ ' + ' '.join(command) + '\n' + result.stdout +
                        f'\nexit_code={result.returncode}\n')
    (logs / 'tool_versions.log').write_text('\n'.join(versions))
    command = ['make', '-B', 'check', f'IVERILOG={args.iverilog}', f'VVP={args.vvp}']
    result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    log = '$ ' + ' '.join(command) + '\n' + result.stdout + f'\nexit_code={result.returncode}\n'
    (logs / 'complete_verification.log').write_text(log)
    print(result.stdout, end='')
    c_runner = re.search(r'PASS C vector runner: (\d+) cases', result.stdout)
    c_abi = re.search(r'PASS C ABI: (\d+) batch and (\d+) scalar oracle comparisons', result.stdout)
    rtl = re.search(r'PASS RTL: (\d+) oracle comparisons; busy/held-output reset cancellation; '
                    r'input stalls=(\d+) output stalls=(\d+) simultaneous retire/accept=(\d+) cycles=(\d+)',
                    result.stdout)
    diagnostic = bool(re.search(r'(^|\n)(ERROR:|FATAL:)', result.stdout))
    passed = bool(result.returncode == 0 and c_runner and c_abi and rtl and not diagnostic)
    if passed:
        passed = (int(c_runner[1]) == int(c_abi[1]) == int(c_abi[2]) == int(rtl[1]) == 1165
                  and all(int(rtl[i]) > 0 for i in (2, 3, 4)))
    source_names = ['arc1_transform.c', 'arc1_transform.h', 'rtl/arc1_transform.sv',
                    'tests/generate_vectors.py', 'tests/test_reference.py',
                    'tests/vector_check.c', 'tests/transform_tb.sv',
                    'tests/run_verification.py', 'Makefile', 'CONTRACT.md']
    report = {
        'schema_id': 'arc1-compute-verification-v1',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': 'PASS_HOST_AND_RTL_SIMULATION' if passed else 'FAIL',
        'command': command, 'exit_code': result.returncode,
        'requires_explicit_pass_markers': True, 'error_diagnostic_present': diagnostic,
        'c_ubsan_oracle_cases': int(c_runner[1]) if c_runner else None,
        'c_batch_oracle_cases': int(c_abi[1]) if c_abi else None,
        'c_scalar_oracle_cases': int(c_abi[2]) if c_abi else None,
        'rtl_oracle_cases': int(rtl[1]) if rtl else None,
        'rtl_input_stall_cycles': int(rtl[2]) if rtl else None,
        'rtl_output_stall_cycles': int(rtl[3]) if rtl else None,
        'rtl_simultaneous_retire_accept': int(rtl[4]) if rtl else None,
        'rtl_simulation_cycles': int(rtl[5]) if rtl else None,
        'reset_during_compute_and_held_result_checked': bool(rtl),
        'efinity_run': False, 'synthesis_run': False, 'static_timing_run': False,
        'physical_fpga_test': False, 'acceleration_measured': False,
        'source_sha256': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                          for name in source_names},
        'vectors_sha256': hashlib.sha256((root / 'build/vectors.hex').read_bytes()).hexdigest(),
        'logs': ['verification_logs/tool_versions.log', 'verification_logs/complete_verification.log'],
    }
    (root / 'verification_results.json').write_text(json.dumps(report, indent=2) + '\n')
    if not passed:
        print('Verification failed: require all explicit PASS markers and no ERROR/FATAL diagnostic.', file=sys.stderr)
        return 1
    print('PASS: retained complete logs and verification_results.json; host/RTL simulation only.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
