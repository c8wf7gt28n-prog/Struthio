import sys
sys.path.insert(0, '.')
from workbench import desk_ops as D, planner as P, goals as G
w = D.World((D.Sheet('07 Bench readings'), D.Sheet('07 Limits Rev A ARCHIVED', 'sheet', '07 Limits Rev B CURRENT', True),
             D.Sheet('07 Limits Rev B CURRENT', 'sheet', '07 Limits Rev A ARCHIVED', False)))
today = D.State(surface='home', face='work', sel='07 Bench readings', whole=True)
tr = G.make('traced', {'s': '07 Bench readings'}, 1)
sb = G.make('side_by_side', {'a': '07 Limits Rev A ARCHIVED', 'b': '07 Limits Rev B CURRENT'}, 2)
td = G.tidy(3)
for goals in ([tr, td], [tr, sb, td], [sb, tr, td]):
    p = P.plan(today, w, goals)
    print(p.state, p.how, [(s.act, s.args) for s in p.steps], round(p.ms, 2), p.expansions, p.segments)
z = D.State(surface='field', face='work', sel='07 Bench readings', whole=False, in_sight=frozenset())
p = P.plan(z, w, [tr, td]);print(p.state, p.how, [(s.act, s.args) for s in p.steps])
p = P.plan(today, w, [tr, sb, td], budget=P.Budget(depth=2));print(p.state, p.words)
snap = D.State(surface='field', face='work', sel='07 Bench readings', whole=True)
now = D.State(surface='field', face='work', sel='07 Limits Rev A ARCHIVED', whole=True,
              over=('revisions', '07 Limits Rev A ARCHIVED', '07 Limits Rev B CURRENT'), popups=frozenset({'menu'}))
p = P.put_back(now, w, snap);print(p.state, [(s.act, s.args) for s in p.steps])
p = P.plan(today, w, [tr, sb, td], budget=P.Budget(expansions=3));print(p.state, p.words, p.expansions)
