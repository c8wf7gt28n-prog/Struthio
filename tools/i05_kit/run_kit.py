"""The I05 kit: every arm on every case, three repeats, interleaved, each run in a process of its own; then one summary.

Kept in the tree and never shipped (tools/package_graphite.NOT_SHIPPED), like tools/planted_bugs. It runs the command
`python -m workbench.i05_arms` of the Graphite folder it is given (by default the one it sits in), so the kit folder can
also be copied beside an installed Graphite and pointed at it. Read README.md first.

    python tools/i05_kit/run_kit.py --model /path/to/model.gguf --out ~/i05_results
    python tools/i05_kit/run_kit.py --arms N --out ~/i05_results            (no model: arm N alone)
    python tools/i05_kit/run_kit.py --dry                                   (lists what would run; starts nothing)
    python tools/i05_kit/run_kit.py --cases-file sealed_D.json --cases D --model ... --out ...   (the sealed case D)
    python tools/i05_kit/run_kit.py --summary-only --out ~/i05_results      (the summary again, from the result files)

Each run gets a new Office under OUT/keep/<arm>_<case>_<repeat>, removed after its result file is written unless --keep-all.
A run that already has its result file is skipped, so an interrupted kit carries on where it stopped.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent
ARMS = ('A', 'B1', 'B2', 'B2@4096', 'B3', 'N')
MODEL_ARMS = ('A', 'B1', 'B2', 'B2@4096', 'B3')


def schedule(arms, cases, repeats):
    """Interleaved: in each repeat every case, and in each case every arm, the arms' order turned by one each repeat."""
    out = []
    for r in range(1, repeats + 1):
        turn = (r - 1) % len(arms)
        order = list(arms[turn:]) + list(arms[:turn])
        for c in cases:
            for a in order:out.append((a, c, r))
    return out


def name(arm, case, repeat):
    return '%s_%s_%d' % (arm.replace('@', 'at'), case, repeat)


def summary(out_dir):
    rows = {}
    for path in sorted(Path(out_dir).glob('*.json')):
        if path.name in ('summary.json', 'schedule.json'):continue
        try:
            v = json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            continue
        if v.get('schema') != 'graphite.i05-arm-run/1':continue
        rows.setdefault(v['arm'], []).append(v)
    table = {}
    for arm, runs in rows.items():
        turns = [r.get('model_turns') or 0 for r in runs]
        tops = [r['top_option_picked'] for r in runs if r.get('top_option_picked')]
        seconds = [s for r in runs for s in (r.get('turn_seconds') or []) if isinstance(s, (int, float))]
        table[arm] = {
            'runs': len(runs), 'passed': sum(r['state'] == 'PASSED' for r in runs),
            'by_case': {c: '%d of %d' % (sum(r['state'] == 'PASSED' for r in runs if r['case'] == c), sum(r['case'] == c for r in runs))
                        for c in sorted({r['case'] for r in runs})},
            'wrong_verdicts': sum(bool(r.get('wrong_verdict')) for r in runs),
            'asked_owner': sum(r['state'] == 'ASKED_OWNER' for r in runs),
            'questions_to_owner': sum(len(r.get('questions_to_owner') or []) for r in runs),
            'open_condition_at_finish': sum(bool(r.get('open_condition_at_finish')) for r in runs),
            'repeats_blocked': sum(r.get('repeats_blocked') or 0 for r in runs),
            'model_turns_most_per_case': max(turns) if turns else 0,
            'prompt_tokens_most_per_case': max((r.get('prompt_tokens') or 0) for r in runs),
            'tokens_total': sum((r.get('prompt_tokens') or 0) + (r.get('answer_tokens') or 0) for r in runs),
            'longest_turn_seconds': max(seconds) if seconds else None,
            'case_seconds_most': max((r.get('case_seconds') or 0) for r in runs),
            'top_option_picked': ('%d of %d' % (sum(t[0] for t in tops), sum(t[1] for t in tops))) if tops else None,
        }
    lines = ['# I05 results', '', 'Read beside PREDICTIONS.md. Each line is what the result files say, nothing more.', '',
             '| Arm | Passed | By case | Wrong verdicts | Asked you | Open condition at finish | Repeats blocked | Most turns a case | '
             'Most prompt tokens a case | Longest turn (s) | Most seconds a case | Top option picked |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for arm in [a for a in ARMS if a in table] + sorted(a for a in table if a not in ARMS):
        t = table[arm]
        lines.append('| %s | %d of %d | %s | %d | %d | %d | %d | %d | %d | %s | %s | %s |' % (
            arm, t['passed'], t['runs'], ', '.join('%s %s' % kv for kv in t['by_case'].items()), t['wrong_verdicts'], t['asked_owner'],
            t['open_condition_at_finish'], t['repeats_blocked'], t['model_turns_most_per_case'], t['prompt_tokens_most_per_case'],
            t['longest_turn_seconds'], t['case_seconds_most'], t['top_option_picked'] or '-'))
    (Path(out_dir) / 'summary.json').write_text(json.dumps(table, indent=2) + '\n', encoding='utf-8')
    (Path(out_dir) / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Run the I05 arms on the cases, three repeats, interleaved.')
    ap.add_argument('--graphite', type=Path, default=KIT.parent.parent, help='the Graphite folder (holds workbench/)')
    ap.add_argument('--model', type=Path, help='the model file (needed by every arm but N)')
    ap.add_argument('--arms', default=','.join(ARMS), help='a comma list, from: ' + ', '.join(ARMS))
    ap.add_argument('--cases', default='A,B,C', help='a comma list of case keys')
    ap.add_argument('--cases-file', type=Path, default=KIT / 'cases.json')
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--out', type=Path, help='the folder for the result files')
    ap.add_argument('--context', type=int);ap.add_argument('--threads', type=int);ap.add_argument('--memory-mb', type=int)
    ap.add_argument('--backend', choices=['AUTO', 'CPU', 'VULKAN'])
    ap.add_argument('--keep-all', action='store_true', help='keep every run\'s Office (several hundred MB each)')
    ap.add_argument('--dry', action='store_true', help='list the runs and check the command parses; start nothing')
    ap.add_argument('--summary-only', action='store_true')
    args = ap.parse_args(argv)
    arms = [a for a in args.arms.split(',') if a];cases = [c for c in args.cases.split(',') if c]
    bad = [a for a in arms if a not in ARMS]
    if bad:ap.error('no arm %s' % ', '.join(bad))
    if args.summary_only:
        if not args.out:ap.error('--out is needed')
        print(summary(args.out));return 0
    base = [sys.executable, '-B', '-m', 'workbench.i05_arms', '--cases', str(args.cases_file.resolve())]
    runs = schedule(arms, cases, args.repeats)
    if args.dry:
        listed = subprocess.run(base + ['--list'], cwd=args.graphite, capture_output=True, text=True)
        print(listed.stdout or listed.stderr)
        for a, c, r in runs:print('would run: arm %s, case %s, repeat %d' % (a, c, r))
        return listed.returncode
    if not args.out:ap.error('--out is needed for a run')
    if any(a in MODEL_ARMS for a in arms) and (not args.model or not args.model.is_file()):
        ap.error('arms %s need --model, an existing model file' % ', '.join(a for a in arms if a in MODEL_ARMS))
    args.out.mkdir(parents=True, exist_ok=True);keep = args.out / 'keep'
    (args.out / 'schedule.json').write_text(json.dumps({'runs': runs, 'started': time.time()}, indent=2) + '\n', encoding='utf-8')
    for a, c, r in runs:
        result = args.out / (name(a, c, r) + '.json')
        if result.exists():print('done already:', result.name);continue
        folder = keep / name(a, c, r)
        if folder.exists():shutil.rmtree(folder)
        cmd = base + ['--arm', a, '--case', c, '--repeat', str(r), '--keep', str(folder), '--output', str(result)]
        if a in MODEL_ARMS:
            cmd += ['--model', str(args.model.resolve())]
            for flag, value in (('--context', args.context), ('--threads', args.threads), ('--memory-mb', args.memory_mb),
                                ('--backend', args.backend)):
                if value is not None:cmd += [flag, str(value)]
        print('run: arm %s, case %s, repeat %d' % (a, c, r), flush=True)
        with (args.out / (name(a, c, r) + '.log')).open('w', encoding='utf-8') as log:
            done = subprocess.run(cmd, cwd=args.graphite, stdout=log, stderr=subprocess.STDOUT)
        if not result.exists():
            result.write_text(json.dumps({'schema': 'graphite.i05-arm-run/1', 'arm': a, 'case': c, 'repeat': r, 'state': 'FAILED',
                                          'acceptance_failures': ['The run stopped before writing its result (exit %d); see its log.' % done.returncode]},
                                         indent=2) + '\n', encoding='utf-8')
        if not args.keep_all and folder.exists():shutil.rmtree(folder, ignore_errors=True)
    print(summary(args.out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
