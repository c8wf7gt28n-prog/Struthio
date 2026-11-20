"""Her hand's planner, desk layer: from the window as read now to a state where the goals hold, in the fewest seconds.

Kasandra's hand, first slice. Methods are tried first: each is a short script of desk acts written as a scene's fragments
{act, args, expect}, a step skipped when what it is for already holds, and a gap filled by a small search (up to four acts)
when a step's precondition does not. The library of this slice:

  shown(s)          go.field; point.zoom whole only if s is out of sight; point.sheet s
  traced(s)         shown(s), then sheet.trace
  side_by_side(s)   shown(s or its other revision, whichever is nearer), then sheet.compare
  both_shown(x, y)  side_by_side(x), then shown(y) and sheet.trace: both hold at the end
  tidy              menu.close when anything is open over the window
  put_back(snap)    navigation only, back to the window as the turn found it

Several goals from one request are planned jointly first (all of them true at the end); the methods are tried in every
order of the goals. When no order of the methods gives a joint plan, a forward uniform-cost search over the operators
(desk_ops.OPS) looks for one. When neither finds one, the goals are planned one after another, in the order the owner said
them. A persist goal (nothing left open) must hold at the end, and no plan ends with an act that undoes one.

The acts are a table (desk_ops.Table): the Field's (desk_ops.DESK) unless another is given. An App's acts slot in as a
table of their own, with its own state and its goals' own paths; it is searched with no desk methods (0.8.6 S0).

Budgets: at most 4,096 expansions, 12 acts and 64 literals; past them the answer is TOO_FAR, said as "I could not plan that
within twelve acts." Ties break on cost, then on the number of acts, then on the acts' names and arguments, so the same
desk and the same goals always give the same plan. Plan time is measured (the target is under 50 ms).

Pure Python: no Qt.
"""
import heapq
import itertools
import json
import time
from dataclasses import dataclass, field

from . import desk_ops, goals as G

TOO_FAR_WORDS = 'I could not plan that within twelve acts.'
NONE_WORDS = 'I do not have a way to do that on the desk yet.'


@dataclass(frozen=True)
class Budget:
    expansions: int = 4096
    depth: int = 12
    literals: int = 64
    gap_depth: int = 4


BUDGET = Budget()


@dataclass
class Step:
    act: str
    args: dict
    about: object = None        # the sheet the act is about (for the card's words), when it names none itself
    cost: float = 0.0
    expect: dict = field(default_factory=dict)      # the certain fluents' predicted values

    def words(self):
        args = dict(self.args)
        if self.about and 'title' not in args:args['title'] = self.about
        return desk_ops.act_words(self.act, args)

    def fingerprint(self):
        return desk_ops.fingerprint(self.act, self.args)

    def as_record(self):
        return {'act': self.act, 'args': dict(self.args), 'about': self.about, 'cost': self.cost, 'words': self.words()}


@dataclass
class Plan:
    state: str                  # FOUND, HOLDS (nothing to do), TOO_FAR, NONE
    steps: list = field(default_factory=list)
    cost: float = 0.0
    expansions: int = 0
    depth: int = 0
    ms: float = 0.0
    how: str = ''               # method:<name>, search, sequence
    words: str = ''
    segments: list = field(default_factory=list)    # where each goal is first reached: the end of each offer at Ask first

    def as_record(self):
        return {'state': self.state, 'steps': [s.as_record() for s in self.steps], 'cost': round(self.cost, 4), 'expansions': self.expansions,
                'depth': self.depth, 'ms': round(self.ms, 3), 'how': self.how, 'words': self.words, 'segments': list(self.segments)}


# -- the goal test -------------------------------------------------------------------------------------------------------------------

def satisfied(goal_list, state, table=None):
    tree = (table or desk_ops.DESK).view(state)
    return all(G.holds(g, tree) for g in goal_list)


def literals(goal_list):
    return sum(len(g.expect) for g in goal_list)


def _names(steps):
    return tuple((s.act, json.dumps(s.args, sort_keys=True, ensure_ascii=False)) for s in steps)


def _rank(cost, steps):
    return (round(cost, 6), len(steps), _names(steps))


def _titles(goal_list, state, world, extra=()):
    """The sheets a plan may name: those the goals name, their other revisions, and the selection."""
    out = set(extra)
    for g in goal_list:
        for v in g.params.values():
            if world.get(v) is not None:
                out.add(v)
                pair = world.pair(v)
                if pair:out.update(pair)
    sel = getattr(state, 'sel', None)      # another table's state may have no selection
    if sel and world.get(sel) is not None:out.add(sel)
    return out


def successors(state, world, titles, costs, ops=None, avoid=(), table=None):
    """Every act that applies here, with the state it leads to, in a fixed order (never one in `avoid`: an act refused
    twice in a turn is dropped for the rest of it)."""
    table = table or desk_ops.DESK
    for name in (ops or table.planned):
        op = table.ops[name]
        if op.sense:continue
        for args in op.grounds(state, world, titles):
            if not op.pre(state, world, args) or desk_ops.fingerprint(name, args) in avoid:continue
            nxt = op.apply(state, world, args)
            if nxt.key() == state.key():continue      # an act that changes nothing is never planned
            yield Step(name, dict(args), about=state.sel if name in ('sheet.trace', 'sheet.compare') else None,
                       cost=float(costs.get(name, desk_ops.DEFAULT_COST)),
                       expect={f: getattr(nxt, f) for f in op.certain}), nxt


class _Counter:
    def __init__(self, limit):
        self.n = 0;self.limit = limit

    def take(self):
        self.n += 1
        return self.n <= self.limit


def search(state, world, test, titles, costs, depth, counter, ops=None, avoid=(), table=None):
    """Forward uniform-cost search: (steps, final state, 'FOUND'), or (None, None, 'TOO_FAR' / 'NONE')."""
    if test(state):return [], state, 'FOUND'
    frontier = [(_rank(0.0, []), next_id(), state, [])]
    best = {state.key(): 0.0};cut = False
    while frontier:
        rank, _, s, steps = heapq.heappop(frontier)
        if test(s):return steps, s, 'FOUND'
        if not counter.take():return None, None, 'TOO_FAR'
        if len(steps) >= depth:
            cut = True;continue
        cost = rank[0]
        for step, nxt in successors(s, world, titles, costs, ops, avoid, table):
            g = cost + step.cost;key = nxt.key()
            if key in best and best[key] <= g - 1e-9:continue
            best[key] = g
            heapq.heappush(frontier, (_rank(g, steps + [step]), next_id(), nxt, steps + [step]))
    return None, None, 'TOO_FAR' if cut else 'NONE'


_ids = itertools.count()


def next_id():
    # the heap compares ranks first; the id only keeps it from comparing states (ranks already break every tie)
    return next(_ids)


# -- methods -------------------------------------------------------------------------------------------------------------------------

def _f(act, args=None, expect=None):
    return {'act': act, 'args': dict(args or {}), 'expect': expect}


def m_shown(s, state, world):
    """go.field; point.zoom whole only if s is out of sight; point.sheet s."""
    return [_f('go.field', {}, lambda st: st.surface == 'field' and st.face == 'work'),
            _f('point.zoom', {'to': 'whole'}, lambda st, s=s: in_view_or_selected(st, world, s)),
            _f('point.sheet', {'title': s}, lambda st, s=s: st.sel == s)]


def in_view_or_selected(state, world, title):
    return state.sel == title or desk_ops.in_view(state, world, title)


def m_traced(s, state, world):
    return m_shown(s, state, world) + [_f('sheet.trace', {}, lambda st, s=s: st.route == s)]


def m_side(a, b, state, world):
    """Either revision selected works (the comparison is the same pair from both): the one already selected, else the older."""
    pick = state.sel if state.sel in (a, b) else a
    pair = ('revisions', a, b)
    return [_f('go.field', {}, lambda st: (st.surface == 'field' and st.face == 'work') or st.over == pair)] + \
        [dict(f, expect=(lambda st, e=f['expect']: e(st) or st.over == pair) if f['expect'] else None) for f in m_shown(pick, state, world)[1:]] + \
        [_f('sheet.compare', {}, lambda st: st.over == pair)]


def m_tidy(state, world):
    return [_f('menu.close', {}, lambda st: not st.popups)]


def m_put_back(snap, state, world):
    """Navigation only, back to the snapshot: what is over the work, the selection, the face, what is open, the surface."""
    frags = []
    if snap.surface == 'field' or state.surface == 'field':
        frags.append(_f('go.field', {}, lambda st: st.surface == 'field' and st.face == (snap.face or 'work')))
        if snap.over is None:frags.append(_f('sheet.close', {}, lambda st: st.over is None))
        if snap.sel and world.get(snap.sel) is not None:
            frags.append(_f('point.zoom', {'to': 'whole'}, lambda st: in_view_or_selected(st, world, snap.sel)))
            frags.append(_f('point.sheet', {'title': snap.sel}, lambda st: st.sel == snap.sel))
    frags.append(_f('menu.close', {}, lambda st: not st.popups or bool(snap.popups)))
    if snap.surface != 'field':frags.append(_f('go.back', {}, lambda st: st.surface == snap.surface))
    return frags


def method_for(goal, state, world):
    p = goal.params
    if goal.template == 'shown':return m_shown(p['s'], state, world)
    if goal.template == 'traced':return m_traced(p['s'], state, world)
    if goal.template == 'side_by_side':return m_side(p['a'], p['b'], state, world)
    if goal.template == 'tidy':return m_tidy(state, world)
    if goal.template == 'field':return [_f('go.field', {}, lambda st: st.surface == 'field')]
    return None


def run_fragments(frags, state, world, titles, costs, budget, counter, ops=None, avoid=()):
    """Play a method's fragments on a predicted state: a step whose purpose holds is skipped, a step whose precondition does
    not hold gets a gap filled by a small search. (steps, state) or None."""
    steps = []
    for frag in frags:
        if frag['expect'] is not None and frag['expect'](state):continue
        op = desk_ops.OPS[frag['act']]
        if desk_ops.fingerprint(frag['act'], frag['args']) in avoid:return None
        if not op.pre(state, world, frag['args']):
            gap, at, how = search(state, world, lambda st, op=op, a=frag['args']: op.pre(st, world, a), titles, costs, budget.gap_depth, counter, ops, avoid)
            if gap is None:return None
            steps += gap;state = at
        nxt = op.apply(state, world, frag['args'])
        steps.append(Step(frag['act'], dict(frag['args']), about=state.sel if frag['act'] in ('sheet.trace', 'sheet.compare') else None,
                          cost=float(costs.get(frag['act'], desk_ops.DEFAULT_COST)), expect={f: getattr(nxt, f) for f in op.certain}))
        state = nxt
    return steps, state


def by_methods(goal_list, state, world, titles, costs, budget, counter, avoid=()):
    """The methods in every order of the goals (the persist goals last); the cheapest order after which every goal holds."""
    kept = [g for g in goal_list if not g.persist];persist = [g for g in goal_list if g.persist]
    best = None
    for order in itertools.permutations(kept):
        frags = []
        for g in list(order) + persist:
            got = method_for(g, state, world)
            if got is None:frags = None;break
            frags += got
        if frags is None:continue
        out = run_fragments(frags, state, world, titles, costs, budget, counter, avoid=avoid)
        if out is None:continue
        steps, end = out
        if not satisfied(goal_list, end) or len(steps) > budget.depth:continue
        cost = sum(s.cost for s in steps);rank = _rank(cost, steps)
        if best is None or rank < best[0]:best = (rank, steps, order)
    if best is None:return None
    order = best[2]
    templates = [g.template for g in order]
    name = 'both_shown' if templates == ['side_by_side', 'traced'] else '+'.join(templates) or 'tidy'
    return best[1], name


def segments(steps, goal_list, state, world, joint=True, table=None):
    """Where an offer at Ask first ends (1-based act counts). The owner's Go ahead authorises the moves up to the next goal:
    for goals planned jointly that is the state where they all hold, so the whole plan is one segment; for goals planned
    one after another, each goal ends its own."""
    if joint:return [len(steps)] if steps else []
    table = table or desk_ops.DESK
    out = [];reached = set();s = state
    for n, step in enumerate(steps, 1):
        s = table.ops[step.act].apply(s, world, step.args)
        tree = table.view(s)
        for g in goal_list:
            if g.id not in reached and not g.persist and G.holds(g, tree):reached.add(g.id);out.append(n)
    if steps and (not out or out[-1] != len(steps)):out.append(len(steps))
    return sorted(set(out))


def plan(state, world, goal_list, *, costs=None, budget=BUDGET, joint=True, extra_titles=(), avoid=(), table=None):
    """A plan from `state` to a state where every goal in `goal_list` holds (goals.Goal; persist goals included), over
    `table`'s acts (the Field's when none is given)."""
    started = time.perf_counter();table = table or desk_ops.DESK
    costs = costs or desk_ops.costs();counter = _Counter(budget.expansions)
    titles = _titles(goal_list, state, world, extra_titles)

    def done(p):
        p.ms = (time.perf_counter() - started) * 1000.0;p.expansions = counter.n;p.depth = len(p.steps)
        p.cost = round(sum(s.cost for s in p.steps), 6)
        if p.state == 'TOO_FAR':p.words = TOO_FAR_WORDS
        elif p.state == 'NONE':p.words = NONE_WORDS
        p.segments = segments(p.steps, goal_list, state, world, joint=p.how != 'sequence', table=table) if p.state == 'FOUND' else []
        return p
    if literals(goal_list) > budget.literals:return done(Plan('TOO_FAR'))
    if satisfied(goal_list, state, table):return done(Plan('HOLDS', how='holds'))
    found = by_methods(goal_list, state, world, titles, costs, budget, counter, avoid) if table.methods else None
    if found is not None:
        return done(Plan('FOUND', found[0], how='method:' + found[1]))
    steps, end, how = search(state, world, lambda st: satisfied(goal_list, st, table), titles, costs, budget.depth, counter, avoid=avoid, table=table)
    if steps is not None:return done(Plan('FOUND', steps, how='search'))
    if how == 'TOO_FAR' and counter.n > budget.expansions:return done(Plan('TOO_FAR'))
    kept = [g for g in goal_list if not g.persist];persist = [g for g in goal_list if g.persist]
    if joint and len(kept) > 1:
        # one after another, in the order the owner said them: each goal is a milestone, met and then left behind
        all_steps = [];at = state
        for g in kept:
            part = plan(at, world, [g], costs=costs, budget=budget, joint=False, extra_titles=extra_titles, avoid=avoid, table=table)
            counter.n += part.expansions
            if part.state not in ('FOUND', 'HOLDS'):return done(Plan(part.state))
            for step in part.steps:at = table.ops[step.act].apply(at, world, step.args)
            all_steps += part.steps
        if persist:
            tail = plan(at, world, persist, costs=costs, budget=budget, joint=False, extra_titles=extra_titles, avoid=avoid, table=table)
            counter.n += tail.expansions
            if tail.state not in ('FOUND', 'HOLDS'):return done(Plan(tail.state))
            all_steps += tail.steps
        if len(all_steps) > budget.depth:return done(Plan('TOO_FAR'))
        return done(Plan('FOUND', all_steps, how='sequence'))      # its segments are its goals, one by one
    return done(Plan(how if how in ('TOO_FAR', 'NONE') else 'NONE'))


def put_back(state, world, snapshot, *, costs=None, budget=BUDGET):
    """A plan back to the window as the turn found it (navigation only)."""
    started = time.perf_counter();costs = costs or desk_ops.costs();counter = _Counter(budget.expansions)
    titles = {t for t in (snapshot.sel, state.sel) if t and world.get(t) is not None}
    frags = m_put_back(snapshot, state, world)
    ops = desk_ops.PLANNED + ('go.back',)
    out = run_fragments(frags, state, world, titles, costs, budget, counter, ops)
    p = Plan('FOUND' if out and out[0] else 'HOLDS' if out else 'NONE', out[0] if out else [], how='method:put_back')
    if out is None:p.words = NONE_WORDS
    p.ms = (time.perf_counter() - started) * 1000.0;p.expansions = counter.n;p.depth = len(p.steps);p.cost = round(sum(s.cost for s in p.steps), 6)
    return p


def back_to(state, snapshot):
    """Whether the window is back as the snapshot had it: the surface, the selection, what is over the work."""
    if state.surface != snapshot.surface:return False
    if snapshot.surface != 'field':return True
    return state.sel == snapshot.sel and state.over == snapshot.over
