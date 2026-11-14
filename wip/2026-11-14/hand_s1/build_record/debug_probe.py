"""Debug: from Today with the Tools menu open, say the P02 words; print each plan and state."""
import json, os, sys, time
sys.path.insert(0, os.getcwd())
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from tests_integrated.test_desk_acts import build_window, close_window, settle, act

W = {}
build_window(W, 'graphite-hand-debug-')
try:
    from workbench import desk_ops as D, planner as P, goals as G, hand_words as H
    from workbench.desk_doers import read_desk
    from workbench.her_hand_qt import hand
    w = W['w']
    act('go.today', store=W);act('head.open', {'menu': 'Tools'}, store=W)
    st, world = D.abstract(read_desk(w, 'all'))
    print('start', st, [s.title for s in world.sheets])
    her = hand(w);her.pace_ms = 60
    orig = P.plan

    def traced(*a, **k):
        p = orig(*a, **k);print('PLAN from', a[0], '->', p.state, p.how, [(s.act, s.args) for s in p.steps]);return p
    P.plan = traced
    w.shell2.face.ask('trace 07 Bench readings and put Rev A beside Rev B')
    end = time.monotonic() + 30
    while time.monotonic() < end and her.turn is not None and her.turn.state in ('thinking', 'acting'):settle(W, 20)
    r = her.record();print('turn', r['state'], r['why'], r['acts'], [(e['act'], e['ok'], e['code']) for e in r['envelopes']])
    st, world = D.abstract(read_desk(w, 'all'));print('end', st)
    print('match', H.match('trace 07 Bench readings and put Rev A beside Rev B', her.world()))
finally:
    close_window(W)
