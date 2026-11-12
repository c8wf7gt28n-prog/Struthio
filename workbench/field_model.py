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

KINDS = ('source', 'sheet', 'calculation', 'document', 'finding', 'question', 'method', 'job', 'folder')
# Where a kind sits when nothing feeds it and it feeds nothing: left to right, material to conclusion.
KIND_RANK = {'source': 0, 'folder': 0, 'sheet': 1, 'method': 1, 'calculation': 2, 'job': 2, 'document': 3, 'finding': 3, 'question': 4}
KIND_TAG = {'source': 'SOURCE', 'sheet': 'SHEET', 'calculation': 'CALC', 'document': 'PAGE', 'finding': 'FINDING',
            'question': 'OPEN QUESTION', 'method': 'METHOD', 'job': 'JOB', 'folder': 'FOLDER'}
RANK_TITLE = ('MATERIAL', 'TABLES', 'CALCULATIONS', 'FINDINGS', 'OPEN')
# States the view knows how to mark. Anything else is shown as its own word in quiet ink.
STATE_CURRENT, STATE_RECHECK, STATE_OPEN, STATE_HELD = 'current', 'recheck', 'open', 'held'
ATTENTION = (STATE_RECHECK, STATE_OPEN, STATE_HELD)


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

    def __post_init__(self):
        seen = set();kept = []
        for obj in self.objects:        # one sheet per identity; a repeated identity is the same thing, not a second one
            if obj.id and obj.id not in seen:
                seen.add(obj.id);kept.append(obj)
        self.objects = kept
        self.links = [link for link in self.links if link.source in seen and link.target in seen and link.source != link.target]
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
        rank = {obj.id: 0 for obj in self.objects}
        incoming = {obj.id: [] for obj in self.objects}
        for link in self.links:
            incoming[link.target].append(link.source)
        linked = {link.source for link in self.links} | {link.target for link in self.links}
        for _ in range(len(self.objects)):
            changed = False
            for obj in self.objects:
                want = max([rank[s] + 1 for s in incoming[obj.id]], default=0)
                if want > rank[obj.id] and want < len(self.objects) + 1:
                    rank[obj.id] = want;changed = True
            if not changed:
                break
        for obj in self.objects:        # an object nothing feeds and that feeds nothing sits where its kind belongs
            if obj.id not in linked:
                rank[obj.id] = KIND_RANK.get(obj.kind, 0)
            elif not incoming[obj.id]:  # a root keeps its kind's place when that is further right (a method that feeds a finding)
                rank[obj.id] = min(KIND_RANK.get(obj.kind, 0), min([rank[l.target] for l in self.feeds(obj.id)], default=0) - 1)
                rank[obj.id] = max(0, rank[obj.id])
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
        kinds = {self._by_id[i].kind for i in self.column(rank)}
        if len(kinds) == 1:
            return {'source': 'MATERIAL', 'folder': 'MATERIAL', 'sheet': 'TABLES', 'calculation': 'CALCULATIONS', 'document': 'PAGES',
                    'finding': 'FINDINGS', 'question': 'OPEN', 'method': 'METHODS', 'job': 'WORK'}[kinds.pop()]
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
        links = self.fed_by(self.selected) if step < 0 else self.feeds(self.selected)
        linked = [l.source if step < 0 else l.target for l in links]
        if linked:
            def rows_away(ident):
                column = self.column(self.rank_of(ident))
                return (abs(self.rank_of(ident) - rank), abs(column.index(ident) - row))
            return self.select(min(linked, key=rows_away))
        ranks = self.ranks();at = ranks.index(rank) + step
        if 0 <= at < len(ranks):
            column = self.column(ranks[at])
            return self.select(column[min(len(column) - 1, row)])
        return self.selected

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
                 'question': ('open question', 'open questions'), 'method': ('method', 'methods'), 'job': ('job', 'jobs')}
        parts = []
        for kind in KINDS:
            count = sum(1 for obj in self.objects if obj.kind == kind)
            if count:
                parts.append('%d %s' % (count, words[kind][count != 1]))
        recheck = sum(1 for obj in self.objects if obj.state == STATE_RECHECK)
        if recheck:
            parts.append('%d to recheck' % recheck)
        return parts

    def place(self, width, height, scale=1.0):
        """One Placement per object inside a width by height surface. Sheets shrink before any is dropped; when a column
        still cannot hold its sheets the surface is taller than `height` and the view scrolls (returned as the second value)."""
        ranks = self.ranks()
        if not ranks or width <= 0 or height <= 0:
            return {}, height
        margin = 28 * scale;gap_x = max(34 * scale, min(96 * scale, width * 0.045))
        columns = len(ranks)
        sheet_w = (width - 2 * margin - gap_x * (columns - 1)) / columns
        sheet_w = max(132 * scale, min(312 * scale, sheet_w))
        used = sheet_w * columns + gap_x * (columns - 1)
        if used > width - 2 * margin and columns > 1:     # narrow: keep the sheets readable and tighten the wires instead
            gap_x = max(18 * scale, (width - 2 * margin - sheet_w * columns) / (columns - 1));used = sheet_w * columns + gap_x * (columns - 1)
        left = max(margin, (width - used) / 2)
        tallest = max(len(self.column(rank)) for rank in ranks)
        gap_y = 22 * scale;top = 40 * scale;bottom = 14 * scale
        room = height - top - bottom
        sheet_h = max(74 * scale, min(138 * scale, (room - gap_y * (tallest - 1)) / tallest))
        need = top + bottom + tallest * sheet_h + (tallest - 1) * gap_y
        surface = max(height, need)
        placed = {}
        for at, rank in enumerate(ranks):
            ids = self.column(rank)
            block = len(ids) * sheet_h + (len(ids) - 1) * gap_y
            y = top + max(0.0, (surface - top - bottom - block) * 0.42)      # a little above the middle: the eye starts there
            x = left + at * (sheet_w + gap_x)
            for row, ident in enumerate(ids):
                placed[ident] = Placement(rank, row, x, y + row * (sheet_h + gap_y), sheet_w, sheet_h)
        return placed, surface
