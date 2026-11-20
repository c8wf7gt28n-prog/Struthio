"""What must be true when her hand is done: goals, their evidence, and the finish rule. Desk goals only, in this slice.

A goal is made from a template and its parameters, never from a model's words: its statement is the template's words with
the sheet's title put in. Its test is the same {path: matcher} a scene's step expects (desk_scene.lookup and matches), so a
scene's expect and a desk goal are one language; the planner reads the same paths from a predicted state (desk_ops.view).

Two modes. A "seen" goal is a milestone: it is met once a read of the window shows it, and the read is kept as its evidence
(the paths that matched, and a digest of what read.desk said of the window and the Field at that moment). It is not checked
again unless it is `persist`. A `persist` goal must still hold at the final read: the standing tidy goal, nothing left open
over the owner's window, ends every turn.

States, inside: OPEN, HOLDS, FAILS, UNDECIDED, SEEN, and a `stale` flag. On screen: open, holds, does not hold, cannot tell,
shown, recheck. The words "held", "BROKEN", "condition" and "interval" are not used here: Graphite gives them other meanings.

Pure Python: no Qt.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .desk_scene import lookup, matches

OPEN, HOLDS, FAILS, UNDECIDED, SEEN = 'OPEN', 'HOLDS', 'FAILS', 'UNDECIDED', 'SEEN'
SHOWN_WORDS = {OPEN: 'open', HOLDS: 'holds', FAILS: 'does not hold', UNDECIDED: 'cannot tell', SEEN: 'shown'}
ORIGINS = ('OWNER', 'HER', 'DEDUCED', 'WORK_ORDER')

# template -> (statement, the paths it reads). Each statement is fixed words with the sheet's title put in.
TEMPLATES = {
    'traced': 'The trace of “{s}” is shown',
    'side_by_side': '“{a}” and “{b}” are side by side',
    'shown': '“{s}” is selected in the Field',
    'tidy': 'Nothing is left open over your window',
    'field': 'The Field is in front',
}
DESK_PARTS = ('where', 'field')         # the read.desk parts a desk goal's evidence digests


@dataclass
class Goal:
    id: str
    statement: str
    template: str
    params: dict
    aim: str = 'achieve'                # achieve, or decide
    mode: str = 'seen'                  # seen (a desk milestone) or hold
    persist: bool = False
    form: str = 'desk'
    bind: dict = field(default_factory=dict)
    bounds: list = field(default_factory=list)
    evidence: object = None
    state: str = OPEN
    stale: bool = False
    slack: object = None
    depends: tuple = ()
    origin: str = 'OWNER'
    agreed: bool = False
    agreed_by: str = ''
    test: object = None                 # its own {path: value}, for a goal over another table's acts (an App's); None: the template's

    @property
    def expect(self):
        return dict(self.test) if self.test is not None else expect_of(self.template, self.params)

    def predicate(self):
        """What makes it true, for the model's list and for its dedup: the template and the sorted parameters."""
        return (self.template, tuple(sorted(self.params.items())))

    def words(self):
        """Its state on her card."""
        word = SHOWN_WORDS.get(self.state, 'open')
        if self.persist and self.state == HOLDS:word = 'holds'
        return 'recheck' if self.stale else word

    def as_record(self):
        return {'id': self.id, 'statement': self.statement, 'template': self.template, 'params': dict(self.params), 'mode': self.mode,
                'persist': self.persist, 'state': self.state, 'stale': self.stale, 'origin': self.origin, 'agreed': self.agreed,
                'evidence': self.evidence}


def expect_of(template, params):
    """The goal's test as {path: value}: read.desk paths, the same as a scene step's expect."""
    if template == 'traced':return {'where.surface': 'field', 'field.route.owner_title': params['s']}
    if template == 'side_by_side':return {'where.surface': 'field', 'field.revisions.a': params['a'], 'field.revisions.b': params['b']}
    if template == 'shown':return {'where.surface': 'field', 'field.selected.title': params['s']}
    if template == 'tidy':return {'where.popups': []}
    if template == 'field':return {'where.surface': 'field'}
    raise ValueError('no goal template named %r' % template)


def make(template, params, n=1, origin='OWNER', persist=None):
    """A goal from its template: its words are the template's, never anyone's free words."""
    if template not in TEMPLATES:raise ValueError('no goal template named %r' % template)
    params = {k: str(v) for k, v in dict(params or {}).items()}
    statement = TEMPLATES[template].format(**params)
    keep = template == 'tidy' if persist is None else bool(persist)
    return Goal('C%d' % n, statement, template, params, mode='hold' if keep else 'seen', persist=keep, origin=origin)


def tidy(n):
    return make('tidy', {}, n, origin='DEDUCED')


def holds(goal, tree):
    """Whether the goal is true on a read.desk tree (or a predicted state's view)."""
    return all(matches(want, lookup(tree, path)) for path, want in goal.expect.items())


def digest(desk):
    """A digest of what read.desk said of the window and the Field."""
    part = {k: desk.get(k) for k in DESK_PARTS if isinstance(desk, dict)}
    return hashlib.sha256(json.dumps(part, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()


def observe(goals, desk, act=0):
    """Mark what this read shows: a seen goal that holds now is SEEN, with its evidence (once); a persist goal holds or is
    open again. Returns the goals that were newly seen."""
    seen = []
    for g in goals:
        if g.state == SEEN and not g.persist:continue      # a milestone met is not checked again
        if holds(g, desk):
            if g.persist:g.state = HOLDS
            else:g.state = SEEN;seen.append(g)
            g.evidence = {'paths': {p: lookup(desk, p) for p in g.expect}, 'digest': digest(desk), 'act': act}
        elif g.persist:
            g.state = OPEN
    return seen


def open_goals(goals):
    """The goals a plan still has to reach: every seen goal not yet seen, and every persist goal."""
    return [g for g in goals if g.persist or g.state != SEEN]


def finished(goals, desk):
    """The finish rule: every seen goal was seen, with its evidence; every persist goal holds at this final read.
    (whether done, the goals that are not)."""
    missing = []
    for g in goals:
        if g.persist:
            if not holds(g, desk):missing.append(g)
        elif g.state != SEEN or not g.evidence:missing.append(g)
    return not missing, missing


def phi(goals):
    """Progress, lower is nearer: twice each open goal, once each that cannot be told or must be checked again."""
    total = 0
    for g in goals:
        if g.stale:total += 1
        elif g.state == UNDECIDED:total += 1
        elif g.state in (OPEN, FAILS) and not (g.persist and g.state == HOLDS):total += 2
    return total


def closing(goals, acts):
    """The card's last line: how many acts, and what holds."""
    kept = [g for g in goals if not g.persist]
    met = sum(1 for g in kept if g.state == SEEN)
    if not kept:return 'Done in %d act%s.' % (acts, '' if acts == 1 else 's')
    what = ('both are shown' if met == 2 == len(kept) else 'it is shown' if met == 1 == len(kept) else
            'all %d are shown' % met if met == len(kept) else '%d of %d are shown' % (met, len(kept)))
    return 'Done in %d act%s; %s.' % (acts, '' if acts == 1 else 's', what)
