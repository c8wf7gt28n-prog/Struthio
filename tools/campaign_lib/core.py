"""What a case is, what an attempt records while it runs, and how its checks are scored.

A Case is plain data (JSON-serialisable) plus the function that drives it. The data declares the starting
state, inputs, allowed operations, fault schedule, the expected outcome as named checks, the time budget, the
mode and what the case needs from the machine (needs.py checks those at run time). The function never sees the
expected values: it only reports what it observed (Attempt.observe), and score() compares the two afterwards.

A case's revision is the SHA-256 of its data, its function's source and every file the runner is made of
(tools/campaign.py and everything under tools/campaign_lib, data files included), so a changed case, a changed
helper it runs through or a changed fixture is never mistaken for the one that ran before.

What the checks say: each expectation is what Graphite's CURRENT code does. Pass therefore means "every check
matched the current code", not "the spec is met". Where a check records current behaviour that an unambiguous line
of the spec contradicts, the case quotes that line in `spec_conflict` with what the spec would accept instead; such
a case is not a plain Pass but "Pass (current code; the spec asks otherwise)", counted apart. When the code changes
to what the spec asks, the same check is met by the spec's form and the case becomes a plain Pass.

Outcomes: Pass (every check met), Pass (current code; the spec asks otherwise), Partial (some met), Fail (none met,
or the case raised: a case that breaks is a Fail whatever it met before), Blocked (a need not met here, decided at
run time, or the steps are not written yet), Timeout (set by the runner when the budget ran out).
"""
from __future__ import annotations

import dataclasses
import decimal
import fractions
import hashlib
import inspect
import json
import os
import re
import time
from pathlib import Path

AGAINST_SPEC = 'Pass (current code; the spec asks otherwise)'
OUTCOMES = ('Pass', AGAINST_SPEC, 'Partial', 'Blocked', 'Fail', 'Timeout')
PASS_MEANS = ('Pass means every declared check matched what the current code does; it is not a verdict that the '
              'spec is met.')
CODE = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')
LIBRARY = Path(__file__).resolve().parent          # tools/campaign_lib
ENTRY = LIBRARY.parent / 'campaign.py'              # tools/campaign.py


def library_digest(folder=LIBRARY, entry=ENTRY):
    """SHA-256 over every source and data file the runner is made of, by relative path and content.

    Computed afresh on every call (about a megabyte of files); a run computes it once and passes it along."""
    digest = hashlib.sha256()
    root = Path(folder).resolve()
    files = sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for path in files:
        digest.update(str(path.relative_to(root)).encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    if entry and Path(entry).is_file():
        digest.update(b'campaign.py\0' + hashlib.sha256(Path(entry).read_bytes()).digest())
    return digest.hexdigest()


@dataclasses.dataclass
class Case:
    id: str
    set: str
    title: str
    situation: str | None = None
    intent: str = ''
    seed: str = 'base'                       # base | after_hours_07 | none
    start: dict = dataclasses.field(default_factory=dict)
    inputs: dict = dataclasses.field(default_factory=dict)
    allowed: list = dataclasses.field(default_factory=list)
    faults: list = dataclasses.field(default_factory=list)
    expect: dict = dataclasses.field(default_factory=dict)
    budget_s: float = 60
    mode: str = 'sim'                        # sim | real
    needs: list = dataclasses.field(default_factory=list)   # checked at run time by needs.py
    spec_question: str | None = None         # a genuine question for the owner; the case still passes
    spec_conflict: dict | None = None        # {"line": <quoted spec line>, "where": ..., "expects": {check: spec form}}
    slice: str | None = None                 # an anchor that runs: the part of its situation it covers
    resume: dict | None = None               # {"kill_after": "<checkpoint step>"} for a resume case
    source_case: str | None = None           # e.g. "resources.md section 5, case 7"
    fn: object = None

    def data(self):
        return {k: v for k, v in dataclasses.asdict(self).items() if k != 'fn'}

    def revision(self, library=None):
        """SHA-256 of the case data, its function's source and the runner's own files (library_digest)."""
        text = json.dumps(self.data(), sort_keys=True, ensure_ascii=False)
        source = inspect.getsource(self.fn) if self.fn else ''
        library = library or library_digest()
        return hashlib.sha256((text + '\n' + source + '\n' + library).encode()).hexdigest()


def code_of(error):
    """The first Graphite reason code in an error text or a dispatch refusal."""
    if isinstance(error, dict):
        error = (error.get('error') or {}).get('message') or (error.get('error') or {}).get('code') or json.dumps(error)
    found = CODE.search(str(error))
    return found[0] if found else str(error)[:160]


class Attempt:
    """The running attempt as a case sees it: observe values, log progress, keep a checkpoint."""

    def __init__(self, case, folder, number, phase='first'):
        self.case = case
        self.folder = Path(folder)
        self.number = number
        self.phase = phase
        self.observed = {}
        self.notes = {}
        self.faults = []
        self.spec_question = case.spec_question
        self.kernel = None
        self.owner = None
        self.models = self.folder / 'models'
        self.progress_path = self.folder / 'progress.jsonl'
        self.checkpoint_path = self.folder / 'checkpoint.json'
        self.t0 = time.monotonic()

    # -- what the case reports ----------------------------------------------------------------
    def observe(self, name, value):
        self.observed[name] = _plain(value)
        self.progress('observe', check=name, value=self.observed[name])

    def note(self, name, value):
        self.notes[name] = _plain(value)

    def fault(self, description, **detail):
        self.faults.append(dict(at=round(time.monotonic() - self.t0, 4), fault=description, **_plain(detail)))
        self.progress('fault', fault=description)

    def progress(self, step, **data):
        """Append one durable line: what has happened so far survives a kill."""
        line = dict(t=round(time.monotonic() - self.t0, 4), wall=time.time(), phase=self.phase, step=step, **_plain(data))
        with self.progress_path.open('a') as stream:
            stream.write(json.dumps(line, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def checkpoint(self, step, **state):
        """Write the attempt's own checkpoint atomically; a resumed attempt reads it back."""
        data = dict(case=self.case.id, step=step, wall=time.time(), **_plain(state))
        temporary = self.checkpoint_path.with_suffix('.part')
        temporary.write_text(json.dumps(data, indent=1, ensure_ascii=False))
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, self.checkpoint_path)
        self.progress('checkpoint', checkpoint=step)
        return data

    def read_checkpoint(self):
        return json.loads(self.checkpoint_path.read_text()) if self.checkpoint_path.is_file() else None

    # -- driving Graphite ------------------------------------------------------------------------
    def call(self, op, args=None, principal=None):
        """kernel.dispatch, logged; returns the result or raises with Graphite's reason."""
        r = self.kernel.dispatch(op, args or {}, principal or self.owner)
        self.progress('op', op=op, ok=r['ok'], code=None if r['ok'] else code_of(r))
        if not r['ok']:
            raise Refused(op, r)
        return r['result']

    def try_call(self, op, args=None, principal=None):
        r = self.kernel.dispatch(op, args or {}, principal or self.owner)
        self.progress('op', op=op, ok=r['ok'], code=None if r['ok'] else code_of(r))
        return r


class Refused(Exception):
    def __init__(self, op, response):
        super().__init__('%s refused: %s' % (op, code_of(response)))
        self.op = op
        self.response = response
        self.code = code_of(response)


def _plain(value):
    """Make a value JSON-safe (Decimal, Path, tuples, sets) without losing what it says."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value)]
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def matches(want, got):
    """A declared expectation against an observation. Plain values compare equal; a few forms are richer."""
    if isinstance(want, dict) and len(want) == 1:
        (form, arg), = want.items()
        if form == 'contains':
            return got is not None and str(arg) in str(got)
        if form == 'startswith':
            return isinstance(got, str) and got.startswith(arg)
        if form == 'in':
            return got in arg
        if form == 'decimal':             # an exact number: '18/5' and '3.60' are the same value
            try:
                return fractions.Fraction(str(got)) == fractions.Fraction(decimal.Decimal(str(arg)))
            except (ValueError, ZeroDivisionError, decimal.InvalidOperation):
                return False
        if form == 'gte':
            return isinstance(got, (int, float)) and got >= arg
        if form == 'lte':
            return isinstance(got, (int, float)) and got <= arg
        if form == 'between':
            return isinstance(got, (int, float)) and arg[0] <= got <= arg[1]
        if form == 'not':                 # anything observed except this value
            return got != '<not observed>' and not matches(arg, got)
    return want == got


def score(case, observed):
    """Checks observed vs expected, and the outcome they add up to.

    A check named in case.spec_conflict["expects"] is met by the current behaviour (its `expected`) or by the form
    the spec asks for; while it is met only by the current behaviour the outcome is AGAINST_SPEC, not Pass."""
    conflict = (case.spec_conflict or {}).get('expects', {})
    checks = []
    for name, want in case.expect.items():
        got = observed.get(name, '<not observed>')
        check = dict(check=name, expected=want, observed=got, ok=matches(want, got))
        if name in conflict:
            check['spec_expects'] = conflict[name]
            check['meets_spec'] = matches(conflict[name], got)
            check['ok'] = check['ok'] or check['meets_spec']
        checks.append(check)
    met = sum(c['ok'] for c in checks)
    if checks and met == len(checks):
        against = [c for c in checks if 'meets_spec' in c and not c['meets_spec']]
        outcome = AGAINST_SPEC if against else 'Pass'
    elif met:
        outcome = 'Partial'
    else:
        outcome = 'Fail'
    return outcome, checks


def passed(outcome):
    """Pass, or Pass on current code against a quoted spec line: every check met either way."""
    return outcome in ('Pass', AGAINST_SPEC)
