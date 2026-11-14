"""P01 on the bench seed, every run (mouse, keys, mouse_still, keys_still), at the given window size; the read-backs compared
with the window afterwards (the scene sizes the window from given.size, so the size is put into a copy of the scene)."""
import json, sys, copy
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/field/desk')
import harness as H
from harness import act, short, LEFT

size = [int(x) for x in sys.argv[1].split('x')]
S = H.start(size=tuple(size))
w = S['w']
from workbench import desk_scene
from workbench.engineering_kernel import operator
scene = desk_scene.load(H.TREE + '/tools/campaign_lib/data/scenes/P01.json')
scene = copy.deepcopy(scene);scene['given']['size'] = size;import os;scene['given']['appearance'] = os.environ.get('GRAPHITE_APPEARANCE', 'graphite')
summary = {}
try:
    for run in (sys.argv[2].split(',') if len(sys.argv) > 2 else ('mouse', 'keys', 'mouse_still', 'keys_still')):
        for name, args in (('menu.close', {}), ('hand.dial', {'place': 'show'})):act(S, name, args)
        if getattr(w, '_field_active', False):act(S, 'go.back', {'by': 'pointer'})
        if (S['files'] / '07 Bench readings.csv').exists():S['k'].dispatch('files.trash', {'path': '07 Bench readings.csv'}, operator())
        w.type_bar.box.clear();w._desk_put = '';S['T'].settle(S)
        out = desk_scene.run_scene(w, scene, run, seed='bench', origin='desk-script:review')
        fails = desk_scene.failures(out)
        print('\n=== %s at %dx%d: passed=%s  window=%dx%d' % (run, size[0], size[1], out.get('passed'), w.width(), w.height()))
        for s in out['steps']:
            print('  %2d %-13s ok=%-5s by=%-7s %5.2fs %s' % (s['n'], s['act'], s['ok'], s['by'], s['seconds'], (s['words'] or '')[:110]))
        for n, c in fails:print('  FAIL step', n, json.dumps(c, ensure_ascii=False, default=str)[:300])
        print('  file left behind:', (S['files'] / '07 Bench readings.csv').exists(), '| line text:', repr(w.type_bar.box.text())[:80])
        summary[run] = (out.get('passed'), len(fails))
finally:
    print('\nSUMMARY', size, summary, 'LEFT', LEFT)
    sys.stdout.flush()
    H.finish(S)
