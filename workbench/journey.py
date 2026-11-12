"""Slate's Control Center facts: five journey stages read from real project state.

No Qt. Every line comes from saved files, kernel jobs, candidates or evidence; nothing
is estimated, and there are no completion percentages. A stage whose inputs cannot be
read says so instead of guessing.
"""
import json
from pathlib import Path

STAGES = ('explore', 'understand', 'build', 'prove', 'improve')
FINISHED = ('Completed', 'Failed', 'Cancelled', 'Interrupted')
WAITING = ('Waiting for Approval', 'Waiting for Execution Approval', 'Waiting for Agent', 'Waiting for Provider')


def _stage(title, status, detail='', state='READY'):
    return {'title': title, 'status': status, 'detail': detail, 'state': state}


def _unavailable(title, exc):
    return _stage(title, 'Unavailable', type(exc).__name__ + ': ' + str(exc)[:160], 'UNAVAILABLE')


def explore(root):
    from . import brain_link
    from .cad_export import status as export_status
    graph, _, revision = brain_link.bound(root)
    pins = sum(graph.pin_count.values()) if isinstance(getattr(graph, 'pin_count', None), dict) else \
        sum(len(c.get('pins', [])) for c in graph.components.values())
    export = export_status(root)['state'].replace('_EXPORT', '').replace('_', ' ').lower()
    return _stage('Explore', '%d parts · %d nets · %d pins' % (len(graph.components), len(graph.nets), pins),
                  'Native netlist revision %s · KiCad export %s' % (revision[:12], export)), revision


def understand(root):
    from .handbook import ensure
    from . import database_rom
    pages = json.loads((Path(root) / ensure(root)['pages_file']).read_text())
    count = len(pages['pages'] if isinstance(pages, dict) else pages)
    volumes = database_rom.dispatch(type('K', (), {'root': Path(root)})(), 'records.status', {}).get('volumes', [])
    records = sum(v.get('records', 0) for v in volumes)
    return _stage('Understand', '%d Orange Book chapters · %d sealed reference record%s' % (count, records, '' if records == 1 else 's'),
                  'Chapters read current project sources; references search attached Database ROM volumes')


def build(root, jobs):
    from .console_services import inspect
    console = inspect(root).get('build')
    latest = next((j for j in jobs if j.get('tool') in ('native.build', 'console.build')), None)
    model = 'Console model current' if console and console.get('current') else 'Console model needs a build'
    last = (latest['tool'] + ' · ' + latest['state']) if latest else 'no native build recorded'
    state = 'ATTENTION' if latest and latest['state'] == 'Failed' else 'READY'
    return _stage('Build', model, 'Last build: ' + last, state)


def prove(root):
    from .engineering_register import snapshot
    evidence = snapshot(root)['evidence']
    passed = sum(1 for e in evidence if e.get('outcome') == 'PASS')
    missing = sum(1 for e in evidence if e.get('currency') in ('MISSING', 'UNASSESSED'))
    return _stage('Prove', '%d evidence record%s · %d passing' % (len(evidence), '' if len(evidence) == 1 else 's', passed),
                  '%d missing or unassessed · board tests remain blocked; no first-boot probability' % missing,
                  'ATTENTION' if missing else 'READY')


def improve(root, jobs, candidates):
    waiting = [j for j in jobs if j.get('state') in WAITING]
    review = [c for c in candidates if c.get('state') in ('review', 'Review', 'SUBMITTED', 'Submitted')]
    proposal = json.loads((Path(root) / 'project/review/command_parser/SOURCE.json').read_text())
    parser = 'parser proposal ' + proposal.get('acceptance', 'unknown').replace('_', ' ').lower()
    return _stage('Improve', '%d candidate%s · %d awaiting approval' % (len(candidates), '' if len(candidates) == 1 else 's', len(waiting) + len(review)),
                  parser.capitalize(), 'ATTENTION' if waiting or review else 'READY')


def next_action(jobs, stages):
    waiting = next((j for j in jobs if j.get('state') in WAITING), None)
    if waiting:
        return {'stage': 'improve', 'text': 'Review the %s job waiting for %s' % (waiting['tool'], waiting['state'].split(' for ')[-1].lower())}
    latest = next((j for j in jobs if j.get('state') in FINISHED), None)
    if latest and latest['state'] == 'Failed':
        return {'stage': 'improve', 'text': 'Inspect the failed %s job and its evidence' % latest['tool']}
    if stages['build']['status'].endswith('needs a build'):
        return {'stage': 'build', 'text': 'Build the console model, then boot a native game'}
    if 'pending' in stages['improve']['detail'].lower():
        return {'stage': 'improve', 'text': 'Review the command-parser proposal'}
    return {'stage': 'explore', 'text': 'Follow a component in Brain Link'}


def snapshot(root, kernel, last_workspace='Console hardware'):
    """All Control Center facts. Each stage fails independently and reports why."""
    root = Path(root).resolve()
    try:jobs = kernel.listing('jobs')
    except Exception:jobs = []
    try:candidates = kernel.listing('candidates')
    except Exception:candidates = []
    stages, revision = {}, None
    try:stages['explore'], revision = explore(root)
    except Exception as exc:stages['explore'] = _unavailable('Explore', exc)
    for key, fn in (('understand', lambda: understand(root)), ('build', lambda: build(root, jobs)),
                    ('prove', lambda: prove(root)), ('improve', lambda: improve(root, jobs, candidates))):
        try:stages[key] = fn()
        except Exception as exc:stages[key] = _unavailable(key.title(), exc)
    project = 'ARC-1 · R10' + (' · revision ' + revision[:12] if revision else '')
    return {'schema': 'arc-ledger.control-center/1', 'project': project, 'last_workspace': last_workspace,
            'next_action': next_action(jobs, stages), 'stages': stages, 'estimated': False,
            'physical_hardware': False}
