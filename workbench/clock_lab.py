"""Create the synthetic campaign exercise through existing import operations."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from . import project_desk as records

FIXTURE = Path(__file__).resolve().parents[1] / 'examples' / 'clock_lab' / 'inputs'


def copy_inputs(destination):
    """Create a new folder; never overwrite a previous exercise or include oracle data."""
    destination = Path(destination)
    manifest = json.loads((FIXTURE.parent / 'INPUTS.json').read_text())
    payloads = {}
    for name, sha in manifest['files'].items():
        if Path(name).name != name: raise ValueError('Invalid fixture manifest path')
        raw = (FIXTURE / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha: raise ValueError('Clock Lab input digest changed: ' + name)
        payloads[name] = raw
    destination.mkdir(exist_ok=False)
    for name, raw in payloads.items(): (destination / name).write_bytes(raw)
    return destination


def specification():
    return json.loads((FIXTURE / 'problem.json').read_text())


def start(kernel, source, principal):
    """source is an owner-selected external exercise folder, not program data."""
    preview = records.result_of(kernel, 'imports.preview', {'source': str(source), 'profile': 'ENGINEERING'}, principal)
    copy = records.result_of(kernel, 'imports.accept', {'id': preview['id'],
        'expected_digest': preview['content_digest'], 'for_slate': True}, principal)
    spec = specification()
    project = records.result_of(kernel, 'projects.create', {'title': 'Clock Lab',
        'intent': spec['request']}, principal)
    assignment = records.result_of(kernel, 'assignments.create', {'project': project['id'],
        'request': spec['request'], 'interpretation': 'Investigate the supplied synthetic constraints and retain evidence.',
        'intended_output': 'An evidenced feasibility answer with unresolved assumptions identified',
        'success': ['Every conclusion names its inputs, assumptions and checked result.'],
        'stop': ['Keep unprovided lifetimes unknown.'], 'questions': spec['questions'],
        'inputs': ['files:' + copy['work'] + '/requirements.md']}, principal)
    problem = records.result_of(kernel, 'problems.create', {**spec, 'project': project['id'],
        'assignment': assignment['id'], 'sources': [
            {'copy': copy['id'], 'path': name, 'label': label} for name, label in
            [('requirements.md', 'Requirements'), ('memory.csv', 'Memory inputs'),
             ('power.csv', 'Declared power assumptions'), ('parts.csv', 'Parts table')]]}, principal)
    return {'project': project, 'assignment': assignment, 'copy': copy, 'problem': problem}
