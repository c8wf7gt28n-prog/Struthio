"""Can the arrow keys reach every object? BFS over move() from first()."""
import sys, random
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/wt'); sys.dont_write_bytecode = True
from workbench.field_model import Field, FieldObject as O, FieldLink as L
def unreachable(f):
    start = f.first(); seen = {start}; edge = [start]
    while edge:
        nxt = []
        for ident in edge:
            for d in ('left', 'right', 'up', 'down'):
                f.selected = ident; got = f.move(d)
                if got not in seen: seen.add(got); nxt.append(got)
        edge = nxt
    return [o for o in f.objects if o.id not in seen]
# the real case, by shape
S = ['p1', 'p2', 'p3']; T = ['t1', 't2', 't3']; C = ['c1', 'c2']; F = ['page', 'f1', 'f2', 'f3', 'f4']; Q = ['q']
objs = [O(i, 'source', i) for i in S] + [O(i, 'sheet', i) for i in T] + [O(i, 'calculation', i) for i in C] + [O('page', 'document', 'page')] + [O(i, 'finding', i) for i in F[1:]] + [O('q', 'question', 'q', state='open')]
links = [L('p1', 't1'), L('p2', 't2'), L('p3', 't3'), L('t1', 'c1'), L('t1', 'c2'), L('p1', 'f1'), L('p3', 'f1'), L('p1', 'f2'), L('p3', 'f2'), L('p2', 'f3'), L('p3', 'f3'), L('t3', 'f4')]
f = Field(objs, links); print('real case shape: unreachable by arrows:', [o.id for o in unreachable(f)])
# a small, ordinary shape: two sources, each read into a sheet, each sheet into a calculation, one finding from the sources
objs = [O('p1', 'source', 'p1'), O('p2', 'source', 'p2'), O('t1', 'sheet', 't1'), O('t2', 'sheet', 't2'), O('f1', 'finding', 'f1'), O('f2', 'finding', 'f2')]
links = [L('p1', 'f1'), L('p2', 'f2')]
f = Field(objs, links); print('sources feed findings directly, sheets stand alone: unreachable:', [o.id for o in unreachable(f)], '| columns', {r: f.column(r) for r in f.ranks()})
random.seed(7); bad = 0; total = 0; example = None
kinds = ['source', 'sheet', 'calculation', 'finding', 'question']
for trial in range(3000):
    n = random.randint(2, 9)
    objs = [O('o%d' % i, random.choice(kinds), 'o%d' % i) for i in range(n)]
    order = {k: i for i, k in enumerate(kinds)}
    links = []
    for _ in range(random.randint(0, 8)):
        a, b = random.sample(objs, 2)
        if order[a.kind] < order[b.kind]: links.append(L(a.id, b.id))
    f = Field(objs, links); total += 1; miss = unreachable(f)
    if miss:
        bad += 1
        if example is None or len(f.objects) < len(example[0].objects): example = (f, miss)
print('random forward-only fields with objects the arrows cannot reach: %d of %d' % (bad, total))
if example:
    f, miss = example
    print(' smallest example: columns', {r: [(i, f.get(i).kind) for i in f.column(r)] for r in f.ranks()}, '| links', [(l.source, l.target) for l in f.links], '| first', f.first(), '| unreachable', [o.id for o in miss])
