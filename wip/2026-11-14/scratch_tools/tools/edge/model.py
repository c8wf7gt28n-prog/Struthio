import sys, math, itertools, random, time
sys.path.insert(0, '/home/user/Struthio'); sys.dont_write_bytecode = True
from workbench.field_model import Field, FieldObject as O, FieldLink as L, KINDS, KIND_RANK

def check_place(f, tag):
    bad = []
    for width in (300, 600, 814, 1368, 3000):
        for height in (200, 500, 1050):
            for scale in (0.85, 1.0, 1.4, 2.0):
                try:
                    placed, surface = f.place(width, height, scale)
                except Exception as e:
                    bad.append(('EXC', width, height, scale, repr(e))); continue
                rects = []
                for i, p in placed.items():
                    vals = (p.x, p.y, p.w, p.h)
                    if any(math.isnan(v) or math.isinf(v) for v in vals): bad.append(('nan', width, height, scale, i))
                    if p.w <= 0 or p.h <= 0: bad.append(('neg', width, height, scale, i, p.w, p.h))
                    if p.x < -0.01 or p.x + p.w > width + 0.01: bad.append(('outside-x', width, height, scale, i, round(p.x,1), round(p.x + p.w,1)))
                    if p.y < -0.01 or p.y + p.h > surface + 0.01: bad.append(('outside-y', width, height, scale, i, round(p.y,1), round(p.y+p.h,1), surface))
                    rects.append((i, p))
                if len(placed) != len(f.objects): bad.append(('count', width, height, scale, len(placed), len(f.objects)))
                # overlap check per pair (n small) else per column neighbours
                if len(rects) <= 60:
                    for (i, a), (j, b) in itertools.combinations(rects, 2):
                        if a.x < b.x + b.w - 0.01 and b.x < a.x + a.w - 0.01 and a.y < b.y + b.h - 0.01 and b.y < a.y + a.h - 0.01:
                            bad.append(('overlap', width, height, scale, i, j)); break
    kinds = {}
    for b in bad: kinds.setdefault(b[0], []).append(b[1:])
    print(tag, 'place problems:', {k: (len(v), v[:3]) for k, v in kinds.items()} or 'none')

def check_moves(f, tag):
    ids = {o.id for o in f.objects}
    bad = []
    try:
        fi = f.first()
        if ids and fi not in ids: bad.append(('first', fi))
        if not ids and fi != '': bad.append(('first-empty', fi))
    except Exception as e: bad.append(('first EXC', repr(e)))
    for start in list(ids)[:50] + ['']:
        for d in ('left', 'right', 'up', 'down', 'bogus'):
            f.selected = start
            try:
                r = f.move(d)
                if ids and r not in ids: bad.append(('move', start, d, r))
            except Exception as e: bad.append(('move EXC', start, d, repr(e)))
        for back in (False, True):
            f.selected = start
            try:
                r = f.next_attention(back)
                if ids and start in ids and r not in ids: bad.append(('next', start, back, r))
                if start == '' and r not in ids and r != '': bad.append(('next-empty', r))
            except Exception as e: bad.append(('next EXC', start, back, repr(e)))
        f.selected = start
        try:
            d = f.depth()
            if set(d) != ids: bad.append(('depth keys',))
        except Exception as e: bad.append(('depth EXC', start, repr(e)))
    print(tag, 'move problems:', bad[:6] or 'none')

def run(tag, objs, links, sel=''):
    t = time.time()
    try:
        f = Field(list(objs), list(links), 'T', sel)
    except Exception as e:
        print(tag, 'CONSTRUCT EXC', repr(e)); return None
    dt = time.time() - t
    print('\n==', tag, 'objects', len(f.objects), 'links', len(f.links), 'ranks', f.ranks(), 'max rank', max(f._rank.values(), default=None), 'build %.3fs' % dt, 'selected', f.selected)
    check_place(f, tag); check_moves(f, tag)
    return f

run('empty', [], [])
run('one', [O('a', 'source', 'A')], [])
f = run('cycle2', [O('a', 'sheet', 'A'), O('b', 'sheet', 'B')], [L('a', 'b'), L('b', 'a')])
print(' ranks', f._rank)
f = run('cycle3', [O('a', 'source', 'A'), O('b', 'sheet', 'B'), O('c', 'calculation', 'C')], [L('a', 'b'), L('b', 'c'), L('c', 'a')])
print(' ranks', f._rank)
f = run('self', [O('a', 'source', 'A')], [L('a', 'a')])
f = run('missing', [O('a', 'source', 'A')], [L('a', 'zz'), L('zz', 'a')])
f = run('dups', [O('a', 'source', 'A'), O('a', 'sheet', 'A2'), O('', 'sheet', 'noid'), O('b', 'finding', 'B')], [L('a', 'b')])
print(' kept', [(o.id, o.kind) for o in f.objects])
f = run('200col', [O('s%d' % i, 'source', 'S%d' % i) for i in range(200)], [])
f = run('12ranks', [O('n%d' % i, 'source', 'N%d' % i) for i in range(12)], [L('n%d' % i, 'n%d' % (i + 1)) for i in range(11)])
print(' ranks', f._rank)
# long chain in reverse insertion order: does the longest path converge?
n = 40
f = run('chain40rev', [O('n%d' % i, 'source', 'N') for i in reversed(range(n))], [L('n%d' % i, 'n%d' % (i + 1)) for i in range(n - 1)])
print(' max rank', max(f._rank.values()), 'expect', n - 1)
# big cycle 30
n = 30
f = run('cycle30', [O('n%d' % i, 'source', 'N') for i in range(n)], [L('n%d' % i, 'n%d' % ((i + 1) % n)) for i in range(n)])
print(' ranks', sorted(f._rank.values()))
# unknown kind, None kind
f = run('unknownkind', [O('a', 'weird', 'A'), O('b', None, 'B'), O('c', 'question', 'C', state='open')], [L('a', 'c')])
if f:
    try: print(' rank_title', [f.rank_title(r) for r in f.ranks()], 'census', f.census())
    except Exception as e: print(' rank_title/census EXC', repr(e))
# two unknown kinds in the same column -> rank_title
f = run('unknownkind-alone', [O('a', 'weird', 'A')], [])
if f:
    try: print(' rank_title', [f.rank_title(r) for r in f.ranks()])
    except Exception as e: print(' rank_title EXC', repr(e))
# random graphs
random.seed(3)
for trial in range(200):
    n = random.randint(1, 25)
    objs = [O('o%d' % i, random.choice(KINDS), 'T%d' % i, state=random.choice(['current', 'recheck', 'open', 'held', 'unavailable'])) for i in range(n)]
    links = [L('o%d' % random.randrange(n), 'o%d' % random.randrange(n)) for _ in range(random.randint(0, 40))]
    f = Field(objs, links)
    ids = {o.id for o in f.objects}
    for w in (300, 600, 814, 1368, 3000):
        for s in (0.85, 1.0, 1.4, 2.0):
            placed, surface = f.place(w, 600, s)
            for i, p in placed.items():
                if p.x < -0.01 or p.x + p.w > w + 0.01:
                    print('random', trial, 'outside', w, s, len(f.ranks()), round(p.x), round(p.x + p.w)); break
            else: continue
            break
        else: continue
        break
    for _ in range(60):
        r = f.move(random.choice(['left', 'right', 'up', 'down'])); assert r in ids
        r = f.next_attention(random.random() < .5); assert r in ids
    # link direction vs rank: a link whose source is at same/greater rank than target (cycles only?)
print('random done')
