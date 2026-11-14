"""Model fuzz on the fixed tree: arbitrary links (backward, cycles, self, duplicates, unknown kinds). Arrows reach everything,
nothing raises, ranks stay sane, each wire once, place() returns the triple, A walks every waiting object and comes back."""
import sys, random, time
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt'); sys.dont_write_bytecode = True
from workbench.field_model import Field, FieldObject as O, FieldLink as L, KIND_RANK
def unreachable(f):
    start = f.first(); seen = {start}; edge = [start]
    while edge:
        nxt = []
        for ident in edge:
            for d in ('left', 'right', 'up', 'down'):
                f.selected = ident; got = f.move(d)
                if got not in seen: seen.add(got); nxt.append(got)
        edge = nxt
    return [o.id for o in f.objects if o.id not in seen]
random.seed(11); kinds = ['source', 'sheet', 'calculation', 'document', 'finding', 'question', 'condition', 'job', 'gadget']
states = ['current', 'recheck', 'open', 'held', '', 'not read', 'unavailable', 'waiting', 'failed']
bad = {'unreachable': 0, 'raise': 0, 'far': 0, 'dup': 0, 'attention': 0, 'place': 0, 'rank_title': 0}; worst = 0; example = {}
for trial in range(4000):
    n = random.randint(1, 12)
    objs = [O('o%d' % i, random.choice(kinds), 'o%d' % i, state=random.choice(states)) for i in range(n)]
    links = [L(random.choice(objs).id, random.choice(objs).id, 'x', random.random() < 0.3) for _ in range(random.randint(0, 16))]
    try:
        f = Field(objs, links)
        miss = unreachable(f)
        if miss: bad['unreachable'] += 1; example.setdefault('unreachable', ({r: [(i, f.get(i).kind) for i in f.column(r)] for r in f.ranks()}, [(l.source, l.target) for l in f.links], miss))
        top = max(f.rank_of(o.id) for o in f.objects); worst = max(worst, top)
        # sane: an object is never more than (longest chain) columns beyond its kind's own place
        if top > max(KIND_RANK.values()) + n: bad['far'] += 1
        if len({(l.source, l.target) for l in f.links}) != len(f.links): bad['dup'] += 1
        waiting = [o.id for o in f.objects if o.needs_attention()]; seen = []
        f.select(f.first())
        for _ in range(len(waiting) + 1): seen.append(f.next_attention())
        if waiting and set(seen) != set(waiting): bad['attention'] += 1; example.setdefault('attention', (waiting, seen))
        back = []
        for _ in range(len(waiting) + 1): back.append(f.next_attention(backwards=True))
        if waiting and set(back) != set(waiting): bad['attention'] += 1
        placed, sw, sh = f.place(900, 500, 1.0, 120, 170)
        if set(placed) != {o.id for o in f.objects} or sw < 900 or sh < 500: bad['place'] += 1
        rects = sorted((p.x, p.y, p.w, p.h) for p in placed.values())
        for a in range(len(rects)):
            for b in range(a + 1, len(rects)):
                ax, ay, aw, ah = rects[a]; bx, by, bw, bh = rects[b]
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah: bad['place'] += 1; example.setdefault('overlap', (rects[a], rects[b]))
        for r in f.ranks():
            if not isinstance(f.rank_title(r), str) or not f.rank_title(r): bad['rank_title'] += 1
        f.census(); f.depth(); f.last()
    except Exception as e:
        bad['raise'] += 1; example.setdefault('raise', repr(e))
print('4000 random fields with arbitrary wires:', bad, '| furthest rank seen:', worst); print('examples:', example)
# a long chain that loops back on itself, and a big dense field: time
objs = [O('n%d' % i, 'sheet', 'n') for i in range(400)]; links = [L('n%d' % i, 'n%d' % ((i + 1) % 400)) for i in range(400)] + [L('n%d' % random.randrange(400), 'n%d' % random.randrange(400)) for _ in range(800)]
t = time.time(); f = Field(objs, links); dt = time.time() - t
print('400 objects, 1200 wires with loops: built in %.2fs, columns %d, furthest rank %d' % (dt, len(f.ranks()), max(f.ranks())))
