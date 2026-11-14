#!/usr/bin/env python3
"""Graphite's test campaign: run a case or a batch in disposable workspaces and read the summary.

  python3 tools/campaign.py list [--set resource|anchors|all|selftest|real]
  python3 tools/campaign.py run --case R07
  python3 tools/campaign.py run --set resource [--attempts 2] [--out <dir>] [--fixtures <dir>]
  python3 tools/campaign.py summary <run dir>
  python3 tools/campaign.py run --mode real --case M01 [--model <path> | --workspace <dir>]   (ThinkPad only)

Each attempt runs in its own child process and folder (its own HOME, profile and workspace) and is killed at its
time budget. A run folder holds MANIFEST.json, results.jsonl, SUMMARY.md and cases/<id>/attempt-<n>/; a run into a
folder that already holds one moves the earlier run aside to previous-<n>/ first, and the summary counts only the
cases and attempts this run's manifest lists. What a case needs (the model, an application, the owner's data, a
desktop session) is checked when the run starts; a case whose needs are not met is Blocked and says what is missing.
The owner's After Hours 07 backup and other data are read from --fixtures (default ~/Graphite_Campaign/fixtures, or
$GRAPHITE_CAMPAIGN_FIXTURES). See docs/CAMPAIGN.md.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['--child']:
        from tools.campaign_lib import runner
        return runner.child_main(argv[1])
    if argv[:1] == ['--reopen']:
        from tools.campaign_lib import cases_anchor
        return cases_anchor.reopen_main(argv[1], json.loads(argv[argv.index('--ids') + 1])) or 0
    parser = argparse.ArgumentParser(prog='campaign.py', description='Graphite test campaign runner')
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list', help='list cases, with their needs checked on this machine now')
    listing.add_argument('--set', default='all')
    listing.add_argument('--fixtures', help='folder holding the After Hours 07 backup and the owner\'s data')
    listing.add_argument('--workspace', help='a workspace where the owner\'s model is registered')
    go = sub.add_parser('run', help='run a case or a set')
    go.add_argument('--case', action='append', help='case id (repeatable, or comma separated)')
    go.add_argument('--set', default=None, help='resource, anchors, all, selftest, real or scenes')
    go.add_argument('--attempts', type=int, default=1)
    go.add_argument('--out', help='run folder (default: a new folder under the system temp folder)')
    go.add_argument('--fixtures', help='folder holding the After Hours 07 backup or zip, and the owner\'s data for a '
                                       'situation in <fixtures>/S<nn>/')
    go.add_argument('--mode', choices=('sim', 'real'), default='sim')
    go.add_argument('--model', help='real mode: path to the owner\'s GGUF file')
    go.add_argument('--workspace', help='a workspace where the owner\'s model is registered (the "model" need; '
                                        'real mode uses it too)')
    go.add_argument('--skip-hash', action='store_true', help='real mode: do not hash the whole model file now')
    show = sub.add_parser('summary', help='write and print a run\'s SUMMARY.md')
    show.add_argument('run_dir')
    args = parser.parse_args(argv)
    from tools.campaign_lib import fixture, needs, report, runner
    if args.command == 'list':
        probe = needs.Probe(fixtures=fixture.fixtures_dir(args.fixtures), workspace=args.workspace)
        for case in runner.select(args.set):
            blocked, checked = needs.decide(case, probe)
            state = 'Blocked: ' + blocked if blocked else '%s, %ss' % (case.mode, case.budget_s)
            print('%-4s %-8s %-4s %s  [%s]' % (case.id, case.set, case.situation or '', case.title, state))
            if case.needs:
                print('       needs: %s' % ', '.join(('%s (met)' if c['met'] else '%s (missing)') % c['need'] for c in checked))
        return 0
    if args.command == 'summary':
        text, line = report.summary(args.run_dir)
        print(text)
        return 0
    if args.case:
        args.case = [c for item in args.case for c in item.split(',') if c]
    if args.attempts < 1:
        parser.error('--attempts must be at least 1')
    return runner.run(args)


if __name__ == '__main__':
    raise SystemExit(main())
