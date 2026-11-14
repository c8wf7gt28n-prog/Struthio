"""Part 1: every number and rule of PAL 0.2 section 6 in exact rational arithmetic (fractions.Fraction only)."""
from fractions import Fraction as F
from decimal import Decimal, getcontext
import math, itertools, json

getcontext().prec = 40
out = {}
def rec(key, value):
    out[key] = value
    print('%-44s %s' % (key, value))

def dec(q):
    return str(Decimal(q.numerator) / Decimal(q.denominator))

mA = F(1, 1000); mW = F(1, 1000); ms = F(1, 1000)
V = F(12); I = 280 * mA; LIM = F(6)
P = V * I
rec('P = 12 V x 280 mA [W]', (P, dec(P)))
rec('headroom 6 - P [W]', (LIM - P, dec(LIM - P)))
# solve 12 V * I <= 6 W, I >= 0
ceil_I = LIM / V
rec('ceiling 6/12 [A] -> mA', (ceil_I, ceil_I / mA))
rec('12 V x 500 mA <= 6 (inclusive)', V * 500 * mA <= LIM)
rec('12 V x 501 mA [W]', (V * 501 * mA, dec(V * 501 * mA)))
rec('501 mA violates', V * 501 * mA > LIM)
rec('startup 110 ms - 80 ms [ms]', (110 * ms - 80 * ms) / ms)
rec('startup power 12 V x 650 mA [W] (P01 csv)', dec(V * 650 * mA))
P300 = V * 300 * mA
rec('P at 300 mA [W], headroom', (dec(P300), dec(LIM - P300)))
# Rectangle V in [11.8, 12.2], I in [270, 290] mA. P = V*I is nondecreasing in V for I >= 0 and in I for V >= 0,
# so min is at (Vlo, Ilo) and max at (Vhi, Ihi); all four corners are checked anyway (general interval product rule).
Vlo, Vhi = F('11.8'), F('12.2'); Ilo, Ihi = 270 * mA, 290 * mA
corners = {(str(v), str(i / mA)): v * i for v in (Vlo, Vhi) for i in (Ilo, Ihi)}
rec('corners [W]', {k: dec(x) for k, x in corners.items()})
pmin, pmax = min(corners.values()), max(corners.values())
rec('enclosure [W]', (dec(pmin), dec(pmax)))
rec('min headroom [W]', dec(LIM - pmax))
# brute force: a fine rational grid inside the rectangle never leaves the corner enclosure
grid_ok = all(pmin <= (Vlo + (Vhi - Vlo) * F(a, 40)) * (Ilo + (Ihi - Ilo) * F(b, 40)) <= pmax for a in range(41) for b in range(41))
rec('41x41 grid inside enclosure', grid_ok)
rec('monotone: min at (Vlo,Ilo), max at (Vhi,Ihi)', pmin == Vlo * Ilo and pmax == Vhi * Ihi)
# robust ceiling over V in [11.8, 12.2]: need V*I <= 6 for every V, worst V = 12.2
rob = LIM / Vhi
rec('robust ceiling 6/12.2 [A], [mA]', (rob, rob / mA, dec(rob / mA)))
rec('robust ceiling at 11.8 V would be [mA]', (LIM / Vlo / mA, dec(LIM / Vlo / mA)))
rec('floor(robust mA)', math.floor(rob / mA))
rec('12.2 V x 491 mA [W]', dec(Vhi * 491 * mA))
rec('12.2 V x 492 mA [W]', dec(Vhi * 492 * mA))
rec('491 passes / 492 fails', (Vhi * 491 * mA <= LIM, Vhi * 492 * mA > LIM))
rec('12 V x 1 mA [mW]', V * mA / mW)
# partial derivatives at (12 V, 280 mA)
rec('dP/dV = I [W/V]', dec(I))
rec('dP/dI = V [W/A], [W/mA]', (dec(V), dec(V * mA)))
rec('range effect: dP from V range (0.4 V x 280 mA), from I range (20 mA x 12 V) [W]', (dec((Vhi - Vlo) * I), dec(20 * mA * V)))
# Clock Lab memory: 16 MiB, two 6 MiB, workspace 5 MiB (declared), all concurrent
rec('Clock Lab workspace boundary 16-6-6 [MiB]', 16 - 6 - 6)
rec('Clock Lab all-concurrent demand 6+6+5 [MiB]', 6 + 6 + 5)
rec('Clock Lab power 5 V x 250 mA [W]', F(5) * 250 * mA)

# ---------------- rules ----------------
def affine_solve(a, b, strict=False, domain=(None, None, False, False), step=None, offset=F(0)):
    """Solve a*x + b <= 0 (or < 0 if strict) over domain (lo, hi, lo_open, hi_open), optional integer lattice offset+k*step.
    Returns ('EMPTY'|'ALL'|interval...). Exact reference implementation."""
    lo, hi, lo_open, hi_open = domain
    if a == 0:
        ok = (b < 0) if strict else (b <= 0)
        res = ('DOMAIN', lo, hi, lo_open, hi_open) if ok else ('EMPTY',)
    else:
        r = -b / a
        if a > 0:   # x <= r (x < r)
            nlo, nhi, nlo_open, nhi_open = lo, r, lo_open, strict
            if hi is not None and (hi < r or (hi == r and hi_open)):nhi, nhi_open = hi, hi_open
        else:       # x >= r (x > r)
            nlo, nhi, nlo_open, nhi_open = r, hi, strict, hi_open
            if lo is not None and (lo > r or (lo == r and lo_open)):nlo, nlo_open = lo, lo_open
        res = ('RANGE', nlo, nhi, nlo_open, nhi_open)
    if res[0] == 'EMPTY':return res
    _, l, h, lopen, hopen = res
    if l is not None and h is not None and (l > h or (l == h and (lopen or hopen))):return ('EMPTY',)
    if step is None:return res
    # integer lattice: offset + k*step
    kl = None if l is None else (math.floor((l - offset) / step) + 1 if lopen and ((l - offset) / step).denominator == 1 else math.ceil((l - offset) / step))
    kh = None if h is None else (math.ceil((h - offset) / step) - 1 if hopen and ((h - offset) / step).denominator == 1 else math.floor((h - offset) / step))
    if kl is not None and kh is not None and kl > kh:return ('EMPTY',)
    return ('LATTICE', None if kl is None else offset + kl * step, None if kh is None else offset + kh * step)

def brute(a, b, strict, lo, hi, step):
    """Check against enumeration on a lattice inside a finite domain."""
    xs = []; x = lo
    while x <= hi:
        v = a * x + b
        if (v < 0) if strict else (v <= 0):xs.append(x)
        x += step
    return ('EMPTY',) if not xs else ('LATTICE', xs[0], xs[-1])

cases = {
    'pos a, le: 12x-6<=0 (x in A)': (F(12), F(-6), False, (F(0), None, False, False), None),
    'pos a, lt: 12x-6<0': (F(12), F(-6), True, (F(0), None, False, False), None),
    'pos a, le, mA lattice': (F(12) / 1000, F(-6), False, (F(0), None, False, False), F(1)),
    'pos a, lt, mA lattice (root on lattice)': (F(12) / 1000, F(-6), True, (F(0), None, False, False), F(1)),
    '12.2 V, le, mA lattice': (F('12.2') / 1000, F(-6), False, (F(0), None, False, False), F(1)),
    '12.2 V, lt, mA lattice (root off lattice)': (F('12.2') / 1000, F(-6), True, (F(0), None, False, False), F(1)),
    'neg a, le: -12x+3.6<=0 -> x>=0.3': (F(-12), F('3.6'), False, (F(0), None, False, False), None),
    'neg a, lt': (F(-12), F('3.6'), True, (F(0), None, False, False), None),
    'neg a, lt, 5 mA lattice offset 0': (F(-12) / 1000, F('3.6'), True, (F(0), None, False, False), F(5)),
    'zero a, b<=0 -> whole domain': (F(0), F(-1), False, (F(0), F(1), False, False), None),
    'zero a, b=0, le -> whole domain': (F(0), F(0), False, (F(0), F(1), False, False), None),
    'zero a, b=0, lt -> empty': (F(0), F(0), True, (F(0), F(1), False, False), None),
    'zero a, b>0 -> contradiction': (F(0), F(1), False, (F(0), F(1), False, False), None),
    'pos a, root below domain (12x+1<=0, x>=0)': (F(12), F(1), False, (F(0), None, False, False), None),
    'pos a, root at closed domain edge (12x<=0, x>=0)': (F(12), F(0), False, (F(0), None, False, False), None),
    'pos a, strict at closed edge (12x<0, x>=0)': (F(12), F(0), True, (F(0), None, False, False), None),
    'pos a, root at open domain edge (12x<=0, x>0)': (F(12), F(0), False, (F(0), None, True, False), None),
}
rules = {}
for name, (a, b, s, d, st) in cases.items():
    r = affine_solve(a, b, s, d, st)
    rules[name] = [str(x) if isinstance(x, F) else x for x in r]
    print('%-50s %s' % (name, rules[name]))
out['affine_rules'] = rules
# brute-force cross-check of the lattice results on a finite window
for name, (a, b, s, d, st) in cases.items():
    if st is None:continue
    hi = F(2000)
    got = affine_solve(a, b, s, (d[0], hi, d[2], False), st)
    bf = brute(a, b, s, d[0], hi, st)
    assert got == bf, (name, got, bf)
print('lattice results agree with enumeration over [0, 2000]')
# floor vs ceil-1: strict with integer root
rec('strict, integer root 500: floor(500)=500 is wrong, ceil(500)-1', (math.floor(F(500)), math.ceil(F(500)) - 1))

# dependency problem
def isub(x, y):return (x[0] - y[1], x[1] - y[0])
def imul(x, y):
    ps = [p * q for p in x for q in y];return (min(ps), max(ps))
X = (F(1), F(3))
rec('x - x exact', 0)
rec('[1,3] - [1,3] independent', tuple(map(str, isub(X, X))))
rec('x*x on [-1,2]: true range vs independent product', ((0, 4), tuple(map(str, imul((F(-1), F(2)), (F(-1), F(2)))))))
# power with an affine dependency: P*(1 - P/12) hmm skip; headroom 6 - V*I over box, exact: corners again
rec('headroom 6 - V*I over box [W]', (dec(LIM - pmax), dec(LIM - pmin)))
# denominator crossing zero
xs = (F(-1), F(2))
rec('1/x endpoints only on [-1,2] (WRONG as enclosure)', (str(min(1 / xs[0], 1 / xs[1])), str(max(1 / xs[0], 1 / xs[1]))))
rec('1/x true image on [-1,0)u(0,2]', '(-inf,-1] u [1/2,+inf)')
rec('split [-1,0): image', '(-inf,-1]')
rec('split (0,2]: image', '[1/2,+inf)')
rec('1/x at x=1/1000 inside interval', 1 / F(1, 1000))
# straddling enclosure
rec('enclosure [5.9,6.1] vs <=6: undecided by enclosure alone', 'yes')
# exact enclosure that is attained: corner (12.2 V, 500 mA) gives
rec('12.2 V x 500 mA [W] (attained corner, a counterexample)', dec(Vhi * 500 * mA))
json.dump({k: str(v) for k, v in out.items()}, open(__file__.replace('exact.py', 'exact.json'), 'w'), indent=1)
