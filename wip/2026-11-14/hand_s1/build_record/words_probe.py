import sys
sys.path.insert(0, '.')
from workbench import desk_ops as D, hand_words as H
w = D.World((D.Sheet('07 Bench readings'), D.Sheet('07 Limits Rev A ARCHIVED', 'sheet', '07 Limits Rev B CURRENT', True),
             D.Sheet('07 Limits Rev B CURRENT', 'sheet', '07 Limits Rev A ARCHIVED', False)))
for t in ('trace 07 Bench readings and put Rev A beside Rev B', 'show me where the bench readings come from',
          'where do the bench readings come from, and put the limits side by side', "what's for dinner",
          'trace the limits', 'close what is open', 'put Rev B beside its other revision', 'show 07 bench readings, then tidy up',
          'compare the limits', 'select Rev A and trace it'):
    m = H.match(t, w)
    print(repr(t), '->', m.full, m.goals, m.unmatched, m.ambiguous, H.desk_request(t, w, w.titles()))
for t in ('show me where the bench readings come from', 'where do the bench readings come from, and put the limits side by side', "what's for dinner"):
    c = H.candidates(t, w);print(H.pick_message(t, c))
for a in ('{"pick":[1]}', '{"pick":[8]}', '{"pick":[1,8]}', '{"pick":[9]}', '{"pick":[1,1]}', '{"pick":[]}', '{"pick":[true]}', 'x', '{"pick":[2,1]}'):
    try:print(a, H.read_pick(a, 8))
    except H.Invalid as e:print(a, 'INVALID', e)
