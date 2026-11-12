"""The Field: an overview of real work objects and what feeds what (master specification, sections 70 to 72).

This module is the model only: no Qt, no storage. A caller hands it the objects of one assignment or workspace and the
links between them; it answers where each one sits, how far each is from the selected one, and where a key press goes.

    objects   FieldObject: one real thing with an identity (a source, a sheet, a calculation, a finding, a question)
    links     FieldLink: source feeds target; `stale` means the target must be rechecked against a changed source
    layout    ranks left to right by what feeds what, one column per rank, ordered to keep the wires short
    depth     0 for the selected object, 1 for what touches it, 2 beyond; the view draws depth as distance into the dark

Nothing here opens, edits or runs anything. Opening an object is the host's own function, called by the view.
"""
from dataclasses import dataclass, field

KINDS = ('source', 'sheet', 'calculation', 'document', 'finding', 'question', 'condition', 'method', 'job', 'folder',
         'interface', 'program', 'endpoint',        # these three are the network face: this computer, what runs, where it reaches
         'app')                                      # the programs face: one program or room Graphite can open
# Where a kind sits when nothing feeds it and it feeds nothing: left to right, material to conclusion.
KIND_RANK = {'source': 0, 'folder': 0, 'sheet': 1, 'method': 1, 'calculation': 2, 'job': 5, 'document': 3, 'finding': 3, 'question': 4, 'condition': 4,
             'interface': 0, 'program': 1, 'endpoint': 2, 'app': 0}
KIND_TAG = {'source': 'SOURCE', 'sheet': 'SHEET', 'calculation': 'CALC', 'document': 'PAGE', 'finding': 'FINDING',
            'question': 'OPEN QUESTION', 'condition': 'TOTAL', 'method': 'METHOD', 'job': 'JOB', 'folder': 'FOLDER',
            'interface': 'INTERFACE', 'program': 'PROGRAM', 'endpoint': 'ELSEWHERE', 'app': 'PROGRAM'}
RANK_TITLE = ('MATERIAL', 'TABLES', 'CALCULATIONS', 'FINDINGS', 'OPEN', 'WORK')
# States the view knows how to mark. Anything else is shown as its own word in quiet ink.
STATE_CURRENT, STATE_RECHECK, STATE_OPEN, STATE_HELD = 'current', 'recheck', 'open', 'held'
ATTENTION = (STATE_RECHECK, STATE_OPEN, STATE_HELD, 'waiting', 'paused', 'failed', 'interrupted')
# States drawn with the small green mark: the record agrees with its source, the line is up, the work is running.
SETTLED = (STATE_CURRENT, 'up', 'connected', 'listening', 'running', 'in use')


@dataclass
class FieldObject:
    id: str
    kind: str
    title: str
    role: str = ''                      # what it is for in this work, in the owner's words where the record has them
    state: str = STATE_CURRENT
    lines: tuple = ()                   # up to three short facts drawn on the sheet (a value, a page, a revision)
    where: str = ''                     # the identity a person can read: a path, a page, a record name
    target: object = None               # whatever the host needs to open it; opaque here
    tag: str = ''                       # the word above the title when the kind's own word is not the clearest one
    stac: str = ''                      # the staC line that reads this object: a read-only pipeline, exact, ready for the writing line
    column: int = -1                    # a fixed column for a face that is a shelf, not a flow (the programs); -1: by kind and by wires

    def needs_attention(self):
        return self.state in ATTENTION


@dataclass
class FieldLink:
    source: str
    target: str
    label: str = ''
    stale: bool = False


@dataclass
class Placement:
    rank: int
    row: int
    x: float
    y: float
    w: float
    h: float


@dataclass
class Field:
    objects: list = field(default_factory=list)
    links: list = field(default_factory=list)
    title: str = ''
    selected: str = ''
    verbs: tuple = ('from', 'feeds')    # how a link reads from its target's side and from its source's side
    note: str = ''                      # what the reader left out, in words; the view says it so nothing is hidden silently
    aside: str = ''                     # what is not here because it belongs elsewhere, said quietly
    heads: tuple = ()                   # the columns' names, for a face that names its own (the programs' shelf)
    compact: bool = False               # a shelf of many small things: a sheet carries its name and state; the foot says the rest
    moved: tuple = ()                   # results that changed when a calculation was brought up to date: (old words, new words, its title)

    def __post_init__(self):
        seen = set();kept = []
        for obj in self.objects:        # one sheet per identity; a repeated identity is the same thing, not a second one
            if obj.id and obj.id not in seen:
                seen.add(obj.id);kept.append(obj)
        self.objects = kept
        once = {};links = []
        for link in self.links:          # each wire once: the same source feeding the same target is one wire, stale if any says so
            if link.source not in seen or link.target not in seen or link.source == link.target:continue
            key = (link.source, link.target)
            if key in once:
                once[key].stale = once[key].stale or link.stale
                if not once[key].label:once[key].label = link.label
            else:
                once[key] = link;links.append(link)
        self.links = links
        self._by_id = {obj.id: obj for obj in self.objects}
        self._rank = self._ranks()
        self._columns = self._order()
        if self.selected not in self._by_id:
            self.selected = self.first()

    # ---- structure -------------------------------------------------------------------------------------------------
    def get(self, ident):
        return self._by_id.get(ident)

    def feeds(self, ident):
        return [link for link in self.links if link.source == ident]

    def fed_by(self, ident):
        return [link for link in self.links if link.target == ident]

    def _ranks(self):
        """Longest path from what nothing feeds. A cycle cannot hang this: each object is settled at most len(objects) times."""
        # Every object starts where its kind belongs (material at the left, conclusions at the right) and is pushed
        # further right only when something that feeds it already sits at or beyond that place.
        rank = {obj.id: obj.column if obj.column >= 0 else KIND_RANK.get(obj.kind, 0) for obj in self.objects}
        incoming = {obj.id: [] for obj in self.objects};outgoing = {obj.id: [] for obj in self.objects}
        for link in self.links:
            outgoing[link.source].append(link.target)
        # A wire that closes a loop does not rank anything: without this each pass would push a loop one column further right.
        state = {}
        def walk(start):
            stack = [(start, iter(outgoing[start]))];state[start] = 1
            while stack:
                node, following = stack[-1]
                for target in following:
                    if state.get(target) == 1:continue                 # a back wire: closes a loop, ranks nothing
                    incoming[target].append(node)
                    if target not in state:
                        state[target] = 1;stack.append((target, iter(outgoing[target])))
                        break
                else:
                    state[node] = 2;stack.pop()
        for obj in self.objects:
            if obj.id not in state:walk(obj.id)
        ceiling = len(KIND_RANK) + len(self.objects)
        for _ in range(len(self.objects)):
            changed = False
            for obj in self.objects:
                want = max([rank[s] + 1 for s in incoming[obj.id]], default=0)
                if rank[obj.id] < want <= ceiling:
                    rank[obj.id] = want;changed = True
            if not changed:
                break
        return rank

    def _order(self):
        """Columns by rank; inside a column, by the average row of what feeds each object, so wires cross less."""
        columns = {}
        for obj in self.objects:
            columns.setdefault(self._rank[obj.id], []).append(obj.id)
        ordered = {};row = {}
        for rank in sorted(columns):
            ids = columns[rank]
            def weight(ident, ids=ids):
                rows = [row[l.source] for l in self.fed_by(ident) if l.source in row]
                return (sum(rows) / len(rows) if rows else float(ids.index(ident)), ids.index(ident))
            ids = sorted(ids, key=weight)
            for index, ident in enumerate(ids):
                row[ident] = index
            ordered[rank] = ids
        return ordered

    def ranks(self):
        return sorted(self._columns)

    def column(self, rank):
        return list(self._columns.get(rank, ()))

    def rank_of(self, ident):
        return self._rank.get(ident, 0)

    def rank_title(self, rank):
        if self.heads and 0 <= rank < len(self.heads):return self.heads[rank]
        kinds = {self._by_id[i].kind for i in self.column(rank)}
        if len(kinds) == 1:
            kind = kinds.pop()
            return {'source': 'MATERIAL', 'folder': 'MATERIAL', 'sheet': 'TABLES', 'calculation': 'CALCULATIONS', 'document': 'PAGES',
                    'finding': 'FINDINGS', 'question': 'OPEN', 'condition': 'OPEN', 'method': 'METHODS', 'job': 'WORK',
                    'interface': 'THIS COMPUTER', 'program': 'PROGRAMS', 'endpoint': 'ELSEWHERE'}.get(kind, str(kind).upper())
        return RANK_TITLE[min(rank, len(RANK_TITLE) - 1)]

    # ---- selection -------------------------------------------------------------------------------------------------
    def first(self):
        """Start on what needs the owner, else on the conclusion, else on the first thing."""
        for want in (lambda o: o.needs_attention(), lambda o: o.kind == 'finding', lambda o: True):
            for rank in reversed(self.ranks()):
                for ident in self.column(rank):
                    if want(self._by_id[ident]):
                        return ident
        return ''

    def select(self, ident):
        if ident in self._by_id:
            self.selected = ident
        return self.selected

    def depth(self):
        """Steps from the selected object along links in either direction: 0 itself, 1 touching, 2 further, 3 unrelated."""
        near = {obj.id: 3 for obj in self.objects}
        if self.selected not in near:
            return near
        near[self.selected] = 0;edge = [self.selected]
        touching = {}
        for link in self.links:
            touching.setdefault(link.source, []).append(link.target);touching.setdefault(link.target, []).append(link.source)
        if self.selected not in touching:        # nothing is wired to the selected object: the rest stays readable, one step back
            return {ident: (0 if ident == self.selected else 2) for ident in near}
        for step in (1, 2):
            following = []
            for ident in edge:
                for other in touching.get(ident, ()):
                    if near[other] > step:
                        near[other] = step;following.append(other)
            edge = following
        return near

    def move(self, direction):
        """Arrow keys. Left and right follow a wire when there is one, otherwise go to the nearest row of the next column."""
        if not self.selected:
            return self.select(self.first())
        rank = self.rank_of(self.selected);ids = self.column(rank);row = ids.index(self.selected)
        if direction in ('up', 'down'):
            step = -1 if direction == 'up' else 1
            return self.select(ids[max(0, min(len(ids) - 1, row + step))])
        step = -1 if direction == 'left' else 1
        ranks = self.ranks();at = ranks.index(rank) + step
        if not 0 <= at < len(ranks):
            return self.selected
        beside = self.column(ranks[at])
        links = self.fed_by(self.selected) if step < 0 else self.feeds(self.selected)
        linked = [ident for ident in (l.source if step < 0 else l.target for l in links) if ident in beside]
        if linked:      # a wire into the next column is followed; a wire that bridges over columns is not, so every column is reachable
            return self.select(min(linked, key=lambda ident: abs(beside.index(ident) - row)))
        return self.select(beside[min(len(beside) - 1, row)])

    def last(self):
        """End: the last object in reading order."""
        ranks = self.ranks()
        return self.column(ranks[-1])[-1] if ranks else ''

    def next_attention(self, backwards=False):
        """Tab: the next object that needs the owner, in reading order; stays put when there is none."""
        order = [ident for rank in self.ranks() for ident in self.column(rank)]
        waiting = [ident for ident in order if self._by_id[ident].needs_attention()]
        if not waiting:
            return self.selected
        if backwards:
            waiting.reverse();order.reverse()
        at = order.index(self.selected) if self.selected in order else -1
        for ident in waiting:
            if order.index(ident) > at:
                return self.select(ident)
        return self.select(waiting[0])

    # ---- counting and layout ---------------------------------------------------------------------------------------
    def census(self):
        """What the head says: counts by kind in reading order, then what is waiting."""
        words = {'source': ('source', 'sources'), 'folder': ('folder', 'folders'), 'sheet': ('sheet', 'sheets'),
                 'calculation': ('calculation', 'calculations'), 'document': ('page', 'pages'), 'finding': ('finding', 'findings'),
                 'question': ('open question', 'open questions'), 'condition': ('total', 'totals'), 'method': ('method', 'methods'), 'job': ('job', 'jobs'),
                 'interface': ('interface', 'interfaces'), 'program': ('program', 'programs'), 'endpoint': ('place reached', 'places reached'), 'app': ('program', 'programs')}
        parts = []
        for kind in KINDS:
            count = sum(1 for obj in self.objects if obj.kind == kind)
            if count:
                parts.append('%d %s' % (count, words.get(kind, (kind, kind + 's'))[count != 1]))
        recheck = sum(1 for obj in self.objects if obj.state == STATE_RECHECK)
        if recheck:
            parts.append('%d to recheck' % recheck)
        return parts

    def place(self, width, height, scale=1.0, sheet_h=None, least_w=None):
        """One Placement per object, and the size of the surface they need. Sheets are never squeezed below a readable size:
        `sheet_h` is the height one sheet needs for its words (the view measures it) and `least_w` the narrowest it may be.
        When the columns or a column's sheets do not fit, the surface is wider or taller than the given room and the view
        scrolls. Returns (placements, surface_width, surface_height)."""
        ranks = self.ranks()
        if not ranks or width <= 0 or height <= 0:
            return {}, width, height
        margin = 28 * scale;columns = len(ranks)
        least_w = least_w or 172 * scale;sheet_h = sheet_h or 138 * scale
        gap_x = max(34 * scale, min(96 * scale, width * 0.045))
        sheet_w = (width - 2 * margin - gap_x * (columns - 1)) / columns
        if sheet_w < least_w and columns > 1:             # narrow: tighten the wires and the rim first
            gap_x = 22 * scale;margin = 16 * scale
            sheet_w = (width - 2 * margin - gap_x * (columns - 1)) / columns
        sheet_w = max(least_w, min(312 * scale, sheet_w))
        used = sheet_w * columns + gap_x * (columns - 1)
        surface_w = max(width, used + 2 * margin)
        left = max(margin, (surface_w - used) / 2)
        tallest = max(len(self.column(rank)) for rank in ranks)
        gap_y = (14 if self.compact else 22) * scale;top = 40 * scale;bottom = 30 * scale     # the bottom rim clears the strip that says where the surface goes on
        need = top + bottom + tallest * sheet_h + (tallest - 1) * gap_y
        surface_h = max(height, need)
        placed = {}
        for at, rank in enumerate(ranks):
            ids = self.column(rank)
            block = len(ids) * sheet_h + (len(ids) - 1) * gap_y
            y = top if self.compact else top + max(0.0, (surface_h - top - bottom - block) * 0.42)      # a flow sits a little above the middle, where the eye starts; a shelf starts at the top
            x = left + at * (sheet_w + gap_x)
            for row, ident in enumerate(ids):
                placed[ident] = Placement(rank, row, x, y + row * (sheet_h + gap_y), sheet_w, sheet_h)
        return placed, surface_w, surface_h
