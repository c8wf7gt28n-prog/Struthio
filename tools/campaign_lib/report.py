"""The run summary: a short markdown page an owner can read once after a batch.

It reads MANIFEST.json and, for exactly the cases and attempts that manifest lists, cases/<id>/attempt-<n>/result.json
(nothing else in the folder counts: an earlier run moved aside to previous-<n>/, or a stray attempt folder, is never
read). It writes SUMMARY.md: what Pass means, counts by outcome (first attempts are the scored ones; later attempts
are reruns), a table of every case, the cases whose current behaviour a quoted spec line contradicts, the anchors
that ran and the baseline slice each covers, the slowest attempts, the spec questions, and what is Blocked and why.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .core import AGAINST_SPEC, OUTCOMES, PASS_MEANS, passed

MISSING = 'Missing'
ORDER = OUTCOMES
NOT_WRITTEN = 'steps not written yet'


def load(run_dir):
    """The manifest and this run's own results: one per (listed case, attempt 1..attempts_per_case)."""
    run_dir = Path(run_dir)
    manifest = json.loads((run_dir / 'MANIFEST.json').read_text())
    attempts = int(manifest.get('attempts_per_case') or 1)
    results = []
    for case in manifest['cases']:
        for number in range(1, attempts + 1):
            path = run_dir / 'cases' / case['id'] / ('attempt-%d' % number) / 'result.json'
            result = json.loads(path.read_text()) if path.is_file() else None
            if result is not None and result.get('case_revision') not in (None, case.get('revision')):
                result, why = None, 'its result.json is from another revision of the case'
            else:
                why = 'no result.json: the run stopped before this attempt, or is still running'
            if result is None:
                result = dict(case_id=case['id'], set=case.get('set'), situation=case.get('situation'),
                              title=case.get('title'), attempt=number, outcome=MISSING, reason=why, seconds=0)
            results.append(result)
    return manifest, results


def _cell(text, limit=110):
    return str(text if text is not None else '').replace('|', '/').replace('\n', ' ')[:limit]


def _outcome_cell(r):
    if r.get('slice') and passed(r['outcome']):
        return '%s (baseline slice of %s)' % (r['outcome'], r.get('situation'))
    return r['outcome']


def headline(manifest, first, results):
    counts = Counter(r['outcome'] for r in first)
    shown = list(ORDER) + ([MISSING] if counts.get(MISSING) else [])
    slices = sum(1 for r in first if r.get('slice') and passed(r['outcome']))
    questions = sum(1 for r in first if r.get('spec_question') and passed(r['outcome']))
    line = 'SUMMARY %s: %d cases, %s%s. Pass means every check matched the current code, not that the spec is met' % (
        manifest['run'], len(first), ', '.join('%s %d' % (k, counts.get(k, 0)) for k in shown),
        ' (+%d reruns)' % (len(results) - len(first)) if len(results) > len(first) else '')
    if slices:
        line += ('; %d of the passing cases %s only a baseline slice of %s situation' % (
            slices, 'is an anchor that covers' if slices == 1 else 'are anchors that cover',
            'its' if slices == 1 else 'their'))
    if questions:
        line += '; %d %s open spec questions' % (questions, 'carries' if questions == 1 else 'carry')
    return line + '.', counts, shown


def summary(run_dir):
    run_dir = Path(run_dir)
    manifest, results = load(run_dir)
    first = [r for r in results if r['attempt'] == 1]
    line, counts, shown = headline(manifest, first, results)
    build = manifest['build']
    changes = build.get('changed_paths', 0) + build.get('untracked_paths', 0)
    out = ['# Campaign run %s' % manifest['run'], '',
           '**What Pass means.** %s The expectations are what Graphite does today, so a Pass shows the current '
           'behaviour held, nothing more. A case whose checks record current behaviour that a quoted spec line '
           'contradicts is counted apart as "%s". An anchor that passes covers a baseline slice of its situation, '
           'not the situation\'s whole intent; the table says so on each one.' % (PASS_MEANS, AGAINST_SPEC), '',
           '- Build: Graphite %s, commit %s%s' % (
               build.get('version'), (build.get('git_commit') or '?')[:12],
               ' (with uncommitted changes: %d paths, %d of them untracked)' % (changes, build.get('untracked_paths', 0))
               if build.get('tracked_changes') else ''),
           '- Python %s, PySide6 %s; host %s, %s logical CPUs' % (
               manifest['runtime']['python'], manifest['runtime']['pyside6'], manifest['host']['cpu'],
               manifest['host']['logical_cpus']),
           '- Model identity: %s (%s bytes); simulation uses the fixture built from its real header' % (
               manifest['model']['owner_file']['name'], format(manifest['model']['owner_file']['bytes'], ',')),
           '- After Hours 07 seed: %s' % (manifest['fixtures']['after_hours_07'].get('backup_json_sha256') or 'not found'),
           '- Repository .ledger untouched: %s' % manifest.get('repo_ledger_untouched', 'not yet known'),
           '- Runner files SHA-256: %s (part of every case revision)' % (manifest.get('runner_library_sha256') or '?')[:16]]
    if manifest.get('earlier_run_moved_to'):
        out.append('- An earlier run in this folder was moved aside to %s/ and is not counted here'
                   % manifest['earlier_run_moved_to'])
    out += ['', '## Counts (first attempts)', '',
            '| ' + ' | '.join(shown) + ' | Total |', '|' + '---|' * (len(shown) + 1),
            '| ' + ' | '.join(str(counts.get(k, 0)) for k in shown) + ' | %d |' % len(first), '']
    for set_name in sorted({r.get('set') or '?' for r in first}):
        rows = [r for r in first if (r.get('set') or '?') == set_name]
        c = Counter(r['outcome'] for r in rows)
        text = '- %s: %s' % (set_name, ', '.join('%s %d' % (k, c[k]) for k in shown if c.get(k)))
        sliced = sum(1 for r in rows if r.get('slice') and passed(r['outcome']))
        if sliced:
            text += ' (each passing anchor is a baseline slice of its situation, not its whole intent)'
        out.append(text)
    out += ['', '## Cases', '', '| Case | Situation | Title | Attempt | Outcome | Checks | Seconds | Reason |',
            '|---|---|---|---|---|---|---|---|']
    for r in results:
        out.append('| %s | %s | %s | %d | %s | %s | %.1f | %s |' % (
            r['case_id'], r.get('situation') or '', _cell(r.get('title'), 70), r['attempt'], _outcome_cell(r),
            '%s/%s' % (r.get('checks_met', 0), r.get('checks_total', 0)) if r.get('checks_total') else '',
            r.get('seconds', 0), _cell(r.get('reason'))))
    against = [r for r in first if r['outcome'] == AGAINST_SPEC]
    out += ['', '## Against the spec: the current code passes, a quoted spec line asks otherwise', '']
    for r in against:
        conflict = r.get('spec_conflict') or {}
        out.append('- %s: %s. The spec (%s): "%s"' % (r['case_id'], conflict.get('current', 'see its checks'),
                                                      conflict.get('where', 'spec'), conflict.get('line')))
    if not against:
        out.append('- none')
    sliced = [r for r in first if r.get('slice') and r['outcome'] not in ('Blocked', MISSING)]
    out += ['', '## Anchors that ran: each covers a baseline slice of its situation', '']
    out += ['- %s (%s) %s: covers %s.' % (r['case_id'], r.get('situation'), r['outcome'], r['slice']) for r in sliced] \
        or ['- none']
    ran = [r for r in results if r['outcome'] not in ('Blocked', MISSING)]
    out += ['', '## Slowest attempts', '']
    for r in sorted(ran, key=lambda r: -r.get('seconds', 0))[:5]:
        out.append('- %s attempt %d: %.1f s (%s)' % (r['case_id'], r['attempt'], r.get('seconds', 0), r['outcome']))
    questions = [(r['case_id'], r['spec_question']) for r in first if r.get('spec_question')]
    out += ['', '## Spec questions (genuine questions for the owner; the case passes on current behaviour)', '']
    out += ['- %s: %s' % q for q in questions] or ['- none']
    misses = [r for r in first if r['outcome'] in ('Partial', 'Fail', 'Timeout', MISSING)]
    out += ['', '## Not passing', '']
    for r in misses:
        out.append('- %s %s: %s; last durable step: %s' % (r['case_id'], r['outcome'], _cell(r.get('reason'), 200),
                                                          _cell(json.dumps(r.get('last_durable_result')), 160)))
    if not misses:
        out.append('- none')
    blocked = [r for r in first if r['outcome'] == 'Blocked']
    waiting = [r for r in blocked if str(r.get('reason', '')).startswith(NOT_WRITTEN)]
    out += ['', '## Blocked (needs checked when the run started)', '',
            '%d blocked: %d for a need not met here, %d with every need met and the steps not written yet.' % (
                len(blocked), len(blocked) - len(waiting), len(waiting)), '']
    out += ['- %s (%s %s): %s' % (r['case_id'], r.get('situation') or '', _cell(r.get('title'), 60), r.get('reason'))
            for r in blocked] or ['- none']
    out += ['', line, '']
    text = '\n'.join(out)
    (run_dir / 'SUMMARY.md').write_text(text)
    return text, line
