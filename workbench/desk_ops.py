"""The desk as her hand plans over it: a small state read back from the window, and the Field's acts as operators on it.

Kasandra's hand, first slice ("Her door on the Field"). read.desk says everything the window shows; abstract() keeps the
part a plan needs: where the centre is, the Field's face, the selected sheet, whether the whole desk is in sight (and which
sheets are, when it is not), what is shown over the work, whose trace is drawn, what is open over the window, and where the
Field was entered from. The Field's sheets come with it, each with its other revision when it has one.

Each operator is one desk act, written as Op(name, pre, add, delete, certain, observe, cost):
  pre      what must be true before it (a function of the state, the sheets and the act's arguments)
  add      what it makes true, as fluent values
  delete   the fluents it puts away
  certain  the fluents its doer checks itself before it says it is done (desk_doers raises otherwise)
  observe  the fluents it may move that are known only at the next read: a plan predicts them, the next read decides
  cost     seconds, a running average of what the journal measured (seeded from the probes)
Every other fluent is left as it was (the frame rule); since the owner's own hand, or a refresh, can move anything, the
desk is read again before every act and the plan is made again when it differs.

Pure Python: no Qt. The doers are desk_doers.py; the search is planner.py; the goals are goals.py.
"""
import json
from dataclasses import dataclass, field, replace

# The probes' seconds (the map of the desk, 0.8.2): go.files 0.63, then.keep 0.78, sheet.compare 0.78; the rest about 0.5.
SEED_COSTS = {'go.files': 0.63, 'then.keep': 0.78, 'sheet.compare': 0.78}
DEFAULT_COST = 0.5
ALPHA = 0.3                     # the weight a new measurement gets in the running average


@dataclass(frozen=True)
class State:
    """What a plan needs of the window, hashable so a search can tell two states apart."""
    surface: str = 'workspace'          # field, home or workspace
    face: object = None                 # work, apps or network; None until the Field has been opened
    sel: object = None                  # the selected sheet's title, or None
    whole: object = None                # True / False, or None when it cannot be read
    in_sight: frozenset = frozenset()   # titles in sight when the whole desk is not
    over: object = None                 # None, ('revisions', older, newer), or ('other',) for a page, the steps, a what-if
    route: object = None                # the title whose trace is drawn (read.desk says it only while that sheet is selected)
    popups: frozenset = frozenset()     # what is open over the window: menu, panel, head:<menu>, apps, meter, equalizer
    came_from: object = None            # 'today' or 'work': where go.back returns to

    def key(self):
        return (self.surface, self.face, self.sel, self.whole, tuple(sorted(self.in_sight)), self.over, self.route,
                tuple(sorted(self.popups)), self.came_from)


@dataclass(frozen=True)
class Sheet:
    title: str
    kind: str = 'sheet'
    sibling: object = None              # the other revision's title, or None
    older: bool = False                 # this one is the older of the two


@dataclass(frozen=True)
class World:
    """The Field's sheets on its work face, read once at the start of a turn (the objects a plan may name)."""
    sheets: tuple = ()

    def get(self, title):
        return next((s for s in self.sheets if s.title == title), None)

    def titles(self):
        return tuple(s.title for s in self.sheets)

    def pair(self, title):
        """(older, newer) for a sheet with another revision on the desk, else None."""
        s = self.get(title)
        if s is None or not s.sibling:return None
        return (s.title, s.sibling) if s.older else (s.sibling, s.title)


def abstract(desk):
    """(State, World) from a read.desk tree (part 'all')."""
    desk = desk if isinstance(desk, dict) else {}
    where = desk.get('where') or {};f = desk.get('field') or {}
    rev = f.get('revisions')
    if isinstance(rev, dict) and rev.get('a') and rev.get('b'):over = ('revisions', rev['a'], rev['b'])
    elif f.get('reading') or f.get('steps') or f.get('go') or f.get('would'):over = ('other',)
    else:over = None
    route = f.get('route') if isinstance(f.get('route'), dict) else None
    sel = (f.get('selected') or {}).get('title') if isinstance(f.get('selected'), dict) else None
    state = State(surface=where.get('surface') or 'workspace', face=f.get('face'), sel=sel,
                  whole=f.get('whole') if isinstance(f.get('whole'), bool) else None, in_sight=frozenset(f.get('in_sight') or ()),
                  over=over, route=route.get('owner_title') if route else None, popups=frozenset(where.get('popups') or ()),
                  came_from=f.get('came_from'))
    sheets = []
    for o in f.get('objects') or ():
        if not isinstance(o, dict) or not o.get('title'):continue
        sheets.append(Sheet(o['title'], o.get('kind') or 'sheet', o.get('sibling'), bool(o.get('older'))))
    return state, World(tuple(sheets))


def view(state):
    """A state written as the parts of read.desk that goals read, so a goal is one {path: matcher} for a real read and for a
    predicted state alike (desk_scene.lookup and matches)."""
    revisions = {'a': state.over[1], 'b': state.over[2]} if state.over and state.over[0] == 'revisions' else None
    return {'where': {'surface': state.surface, 'popups': sorted(state.popups)},
            'field': {'face': state.face, 'selected': {'title': state.sel} if state.sel else None, 'whole': state.whole,
                      'route': {'owner_title': state.route} if state.route else None, 'revisions': revisions,
                      'over': bool(state.over)}}


def in_view(state, world, title):
    """Whether a pointer can reach the sheet now: the whole desk is in sight, or that sheet is."""
    return state.whole is True or title in state.in_sight


# -- the operators ------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Op:
    name: str
    pre: object                 # (state, world, args) -> bool
    add: object                 # (state, world, args) -> {fluent: value}
    delete: tuple = ()          # fluents put back to their empty value
    certain: tuple = ()
    observe: tuple = ()
    cost: float = DEFAULT_COST
    grounds: object = None      # (state, world, titles) -> [args]: the instances worth trying
    sense: bool = False         # read.desk: never a step of a plan, it is how every step is checked
    putback_only: bool = False  # used only to put the window back where the turn found it

    def apply(self, state, world, args):
        """The predicted state after this act."""
        values = dict(self.add(state, world, args))
        for name in self.delete:values.setdefault(name, EMPTY[name])
        return replace(state, **values)


EMPTY = {'over': None, 'route': None, 'popups': frozenset(), 'sel': None, 'in_sight': frozenset(), 'whole': None}


def _field(state):
    return state.surface == 'field'


def _go_field_pre(s, w, a):
    return not (_field(s) and s.face == 'work')


def _go_field_add(s, w, a):
    out = {'surface': 'field', 'face': 'work' if (a.get('face') == 'work' or s.face in (None, 'work')) else s.face}
    if not _field(s):
        # The Field reads the records again as it comes to the front: a page or a what-if over the work goes, the
        # comparison stays (field_qt.set_field); the selection is kept while its sheet is there.
        out['over'] = s.over if s.over and s.over[0] == 'revisions' else None
        out['came_from'] = 'today' if s.surface == 'home' else 'work'
    if s.face not in (None, 'work'):      # another face: other sheets, so the selection is read again
        out.update(sel=None, route=None, in_sight=frozenset(), over=None)
    return out


def _zoom_pre(s, w, a):
    return _field(s) and s.whole is not True


def _zoom_add(s, w, a):
    return {'whole': True, 'in_sight': frozenset(w.titles())}


def _point_pre(s, w, a):
    t = a.get('title')
    return _field(s) and s.face == 'work' and w.get(t) is not None and s.sel != t and in_view(s, w, t)


def _point_add(s, w, a):
    t = a['title']
    # The trace is drawn only while its sheet is selected (field_qt paints it away the moment the selection moves); a
    # comparison stays; a page shown over the work is put away by the press beside it.
    return {'sel': t, 'route': s.route if s.route == t else None,
            'over': s.over if s.over and s.over[0] == 'revisions' else None}


def _trace_pre(s, w, a):
    return _field(s) and bool(s.sel) and w.get(s.sel) is not None and in_view(s, w, s.sel) and s.route != s.sel


def _trace_add(s, w, a):
    return {'route': s.sel}


def _compare_pre(s, w, a):
    pair = w.pair(s.sel) if s.sel else None
    return _field(s) and s.face == 'work' and pair is not None and in_view(s, w, s.sel) and s.over != ('revisions',) + pair


def _compare_add(s, w, a):
    return {'over': ('revisions',) + w.pair(s.sel)}


def _close_pre(s, w, a):
    return _field(s) and s.over is not None


def _menu_close_pre(s, w, a):
    return bool(s.popups)


def _back_pre(s, w, a):
    return _field(s) and s.came_from in ('today', 'work')


def _back_add(s, w, a):
    return {'surface': 'home' if s.came_from == 'today' else 'workspace'}


def _no_args(s, w, titles):
    return [{}]


def _go_field_args(s, w, titles):
    return [{}] if s.face in (None, 'work') else [{'face': 'work'}]


def _point_args(s, w, titles):
    return [{'title': t} for t in sorted(titles) if w.get(t) is not None]


OPS = {
    'go.field': Op('go.field', _go_field_pre, _go_field_add, certain=('surface', 'face'), observe=('sel', 'whole', 'in_sight', 'over'),
                   grounds=_go_field_args),
    'point.zoom': Op('point.zoom', _zoom_pre, _zoom_add, observe=('whole', 'in_sight'), grounds=lambda s, w, t: [{'to': 'whole'}]),
    'point.sheet': Op('point.sheet', _point_pre, _point_add, certain=('sel',), observe=('route', 'over'), grounds=_point_args),
    'sheet.trace': Op('sheet.trace', _trace_pre, _trace_add, certain=('route',), grounds=_no_args),
    'sheet.compare': Op('sheet.compare', _compare_pre, _compare_add, certain=('over',), cost=SEED_COSTS['sheet.compare'], grounds=_no_args),
    'sheet.close': Op('sheet.close', _close_pre, lambda s, w, a: {}, delete=('over',), certain=('over',), grounds=_no_args),
    'menu.close': Op('menu.close', _menu_close_pre, lambda s, w, a: {}, delete=('popups',), certain=('popups',), grounds=_no_args),
    'read.desk': Op('read.desk', lambda s, w, a: True, lambda s, w, a: {}, cost=0.0, grounds=_no_args, sense=True),
    'go.back': Op('go.back', _back_pre, _back_add, delete=('popups',), certain=('surface',), grounds=_no_args, putback_only=True),
}
PLANNED = tuple(n for n, op in OPS.items() if not op.sense and not op.putback_only)      # the eight acts of the slice, less the read


# -- tables of acts (0.8.6 S0: the planner is not the Field's alone) ----------------------------------------------------------------

@dataclass(frozen=True)
class Table:
    """The acts a plan may use, and how a state is read as goals read it. The Field's acts are DESK; an App's acts
    (LibreOffice, GIMP, Godot) slot in later as a table of their own, its own state and its own goals' paths, and the planner
    is the same. `methods`: whether the planner's desk methods (planner.method_for) apply; another table is searched only."""
    ops: dict
    planned: tuple
    view: object                # state -> the tree a goal's {path: value} reads
    methods: bool = False


DESK = Table(OPS, PLANNED, view, methods=True)


def costs(journal_rows=(), seed=None):
    """Seconds per act: the seeds, then a running average of each act's measured seconds, oldest first."""
    out = {name: SEED_COSTS.get(name, DEFAULT_COST) for name in OPS};out['read.desk'] = 0.0
    out.update(seed or {})
    for name, seconds in journal_rows:
        if name in out and isinstance(seconds, (int, float)) and seconds >= 0:out[name] = learn(out[name], seconds)
    return out


def learn(before, seconds, alpha=ALPHA):
    return round((1 - alpha) * float(before) + alpha * float(seconds), 4)


def certain_fluents(name):
    return OPS[name].certain if name in OPS else ()


def agrees(name, predicted, observed):
    """Whether what the doer checks itself came out as predicted: [] or the fluents that differ."""
    return [f for f in certain_fluents(name) if getattr(predicted, f) != getattr(observed, f)]


def fingerprint(name, args):
    """An act and its arguments as one string: the unit an offer authorises."""
    return name + ' ' + json.dumps(args or {}, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


# -- the act's words on her card (the registry's words, the arguments filled in) ---------------------------------------------

def act_words(name, args=None):
    """One row of her card: what the act does, in the registry's plain words with its arguments filled in. No key, no
    name of the line language."""
    args = args or {}
    title = args.get('title') or args.get('sheet')
    if name == 'go.field':return 'Bring the Field to the front' + (', on its %s face' % args['face'] if args.get('face') else '') + '.'
    if name == 'point.zoom':return {'whole': 'See the whole desk.', 'reading': 'See the desk at its reading size.'}.get(args.get('to'), 'Zoom the desk.')
    if name == 'point.sheet':return 'Select “%s” in the Field; nothing opens.' % title
    if name == 'sheet.trace':return 'Trace %s: where it comes from and what rests on it.' % (('“%s”' % title) if title else 'the selected sheet')
    if name == 'sheet.compare':return 'Put %s beside its other revision, side by side.' % (('“%s”' % title) if title else 'the selected sheet')
    if name == 'sheet.close':return 'Put away what is shown over the work.'
    if name == 'menu.close':return 'Close whatever menu or card is open.'
    if name == 'go.back':return 'Leave the Field for the place you came from.'
    if name == 'read.desk':return 'Read back what the window shows now.'
    from .desk_acts import ACTS
    return ACTS[name].words if name in ACTS else name
