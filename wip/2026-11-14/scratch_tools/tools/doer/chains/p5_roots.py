exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
from workbench.engine import engineering
from workbench import stacy_foundation, locations
k2 = engineering(w.root)
print('w.root =', w.root); print('bridge kernel root =', k.root, type(k).__name__); print('engineering(w.root) =', type(k2).__name__, getattr(k2, 'root', None), 'same object:', k2 is k)
for name, kk in (('bridge', k), ('engineering', k2)):
    try: st = stacy_foundation.seed_status(kk.root); print(name, 'seed:', st['state'], st.get('reason'), st.get('changed_sources'), st.get('missing_sources'))
    except Exception as e: print(name, 'seed error', e)
print('locations.program(w.root)=', locations.program(w.root))
r1 = k.dispatch('language.run', {'text': 'documents.list | pick documents | count'}, p); print('bridge:', r1['ok'], r1.get('error') or r1['result']['rows'])
r2 = k2.dispatch('language.run', {'text': 'documents.list | pick documents | count'}, p); print('engineering:', r2['ok'], r2.get('error') or r2['result']['rows'])
# after a file write?
k.dispatch('files.write', {'path': 'z.txt', 'text': 'z'}, p)
r1 = k.dispatch('language.run', {'text': 'documents.list | pick documents | count'}, p); print('bridge after files.write:', r1['ok'], r1.get('error') or r1['result']['rows'])
w._close_start(); settle()
r1 = k.dispatch('language.run', {'text': 'documents.list | pick documents | count'}, p); print('bridge after _close_start:', r1['ok'], r1.get('error') or r1['result']['rows'])
import inspect
print(inspect.getsource(w._close_start)[:800])
