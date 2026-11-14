"""A probe of her hand on the bench window: P02 and P03 through desk_scene, and a few door checks. Run from the worktree."""
import json, os, sys, time
sys.path.insert(0, os.getcwd())
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from tests_integrated.test_desk_acts import build_window, close_window, settle, act
from pathlib import Path

W = {}
build_window(W, 'graphite-hand-probe-')
try:
    from workbench import desk_scene, desk_doers
    w = W['w']
    ROOT = Path(os.getcwd())
    which = sys.argv[1:] or ['P02:mouse', 'P02:ask', 'P03:mouse']
    for item in which:
        sid, run = item.split(':')
        scene = desk_scene.load(ROOT / ('tools/campaign_lib/data/scenes/%s.json' % sid))
        print('check', desk_scene.check_scene(scene))
        started = time.monotonic()
        out = desk_scene.run_scene(w, scene, run, seed='bench', origin='desk-script:%s' % sid)
        print(item, 'passed', out.get('passed'), 'blocked', out.get('blocked'), round(time.monotonic() - started, 1), 's')
        for s in out.get('steps', []):
            print('  step', s['n'], s['act'], s['ok'], s['by'], s['seconds'], (s['words'] or '')[:160])
            for c in s['checks']:
                if not c['ok']:print('     MISS', c['path'], 'want', c['want'], 'got', json.dumps(c['got'], default=str)[:300])
        hand = getattr(w, 'her_hand', None)
        if hand is not None and hand.turn is not None:
            r = hand.record()
            print('  turn', r['state'], 'acts', r['acts'], 'plans', r['plans'], r['plan_ms'], r['plan_how'], 'why', r['why'][:200])
            print('  rows', [(x['act'], x['args'], x['state']) for x in r['rows']])
            print('  envs', [(e['act'], e['ok'], e['code'], e['by']) for e in r['envelopes']])
        settle(W)
        act('menu.close', store=W);act('hand.dial', {'place': 'show'}, store=W)
        if getattr(w, '_field_active', False):act('go.back', {'by': 'pointer'}, store=W)
finally:
    close_window(W)
