# R26 edit 32: the three MIPI-DSI pairs as coupled pairs, drawn from r26_dsi_routes.json (written offline by
# dsi_pair_router.py, which finds each pair's centreline, and dsi_geometry.py, which turns it into P and N, matches the
# pairs and compensates the skew inside each pair; see those scripts).
#  Each line: U1 pad (B.Cu) -> breakout stub -> via -> In3.Cu stripline (0.10 mm, 0.18 mm gap, between the In2 ground
#  band of edit 33 and In4) -> via pair -> F.Cu microstrip (0.127 mm, 0.18 mm gap, over In1) -> J1 pad; or, where a
#  pair goes straight up from its breakout, B.Cu -> via -> F.Cu. P and N always share the layers and the vias.
#  Ground vias sit either side of each second via pair where they fit.
exec(open(sys.argv[2]).read())
import json, os
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'r26_dsi_routes.json')))
for nn, parts in J['lines'].items():
    nt = net(nn)
    for lay, pts, w in parts: add(lay, [tuple(p) for p in pts], nt, w)
    for v in J['vias'][nn]: add_via(v[0], v[1], nt)
for v in J['gnd_vias']: add_via(v[0], v[1], net('GND'))
rep = J['report']
print('dsi route: ' + '; '.join('%s P %.2f N %.2f mm' % (n, rep[n]['P'], rep[n]['N']) for n in ('D0', 'D1', 'CLK'))
      + '; spread %.3f mm, %d ground vias' % (rep['spread'], len(J['gnd_vias'])))
