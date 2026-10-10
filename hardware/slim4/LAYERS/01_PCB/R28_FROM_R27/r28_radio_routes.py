# R28 edit 46: the eight radio signals, U1 to U15, from r28_radio_routes.json (written offline by radio_router.py on
# the board after edit 45: one 0.152 mm track per net on F.Cu, In3.Cu or B.Cu, 0.45/0.2 mm vias between layers,
# 0.12 mm from other copper, 0.30 mm from the crystal, FB_DCDC, EN_DCDC, CHIP_PU and the DSI pairs, vias 0.60 mm from
# FB_DCDC and EN_DCDC, nothing under the module body).
exec(open(sys.argv[2]).read())
import json, os
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'r28_radio_routes.json')))
rep = []
assert '_conflicts' not in J, 'r28_radio_routes.json is from a run that did not converge'
for nn, c in J.items():
    assert c, nn + ': no route'
    nt = net(nn); L_ = 0.0
    for r in c.get('remove', []):          # a re-routed R27 net: its old stretch next to U1 goes first
        if r[0] == 'via': remove_via(r[1], r[2], nn)
        else: remove(r[0], r[1], r[2], r[3], r[4], nn)
    for lay, pts in c['segments']:
        add(lay, [tuple(p) for p in pts], nt, c['width'])
        L_ += sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
    for v in c['vias']: add_via(v[0], v[1], nt)
    rep.append('%s %.1f mm, %d vias%s' % (nn, L_, len(c['vias']), ' (re-routed, %d R27 items replaced)' % len(c['remove'])
                                          if c.get('remove') else ''))
print('radio routes: ' + '; '.join(rep))
