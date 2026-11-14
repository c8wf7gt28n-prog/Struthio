import sys, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from workbench import menus2
open_window(); settle(30, 4)
for n in range(2): menus2.rebuild(w); settle(10, 2)
for name, m in w.menu_groups.items():
    texts = [a.text().replace('&', '') or '—' for a in m.actions()]
    print('%-10s title=%-10r same-object-as=%s rows=%d: %s' % (name, m.title().replace('&', ''), [o for o, mm in w.menu_groups.items() if mm is m and o != name], len(texts), texts[:14]))
fav = getattr(w, 'favorites', None); print('favorites:', fav)
w._closing = True; print('DONE')
