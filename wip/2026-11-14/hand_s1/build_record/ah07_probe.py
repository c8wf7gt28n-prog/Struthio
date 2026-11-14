"""Read the After Hours 07 Field (restored by a campaign case) and try the P02 words against it. argv: the case's ws root."""
import os, sys, json
sys.path.insert(0, os.getcwd())
from pathlib import Path
from workbench.engineering_kernel import Kernel, operator
from workbench.field_page import read_field, revision_sibling
from workbench import desk_ops as D, hand_words as H
root = Path(sys.argv[1])
k = Kernel(root)
field, reader = read_field(k, operator(), title='')


class V:
    pass
v = V();v.field = field;sheets = []
for o in field.objects:
    pair = revision_sibling(v, o);sib = None;older = False
    if pair:(_, a), (_, b) = pair;sib = (b if a.id == o.id else a).title;older = a.id == o.id
    sheets.append(D.Sheet(o.title, o.kind, sib, older))
    print(repr(o.title), o.kind, sib)
w = D.World(tuple(sheets))
for t in ('trace 07 Bench readings and put Rev A beside Rev B',):
    m = H.match(t, w);print(m)
