# R26 edit 34: the slow nets edit 31 lifted out of the DSI area, reconnected around the new pairs from r26_nets.json
# (written offline by net_router.py on the board after edit 33: one track of the net's width per connection on F.Cu,
# In3.Cu or B.Cu, 0.45/0.2 mm vias between layers, 0.12 mm from other copper and 0.30 mm from the DSI pairs).
#  PGOOD_STATUS and PWR_WAKE: their hops south of J1; BTN_LEFT: its run under U1; USB_CURR_OUT2 (TUSB320 OUT2): its
#  whole run to the TUSB320.
exec(open(sys.argv[2]).read())
import json, os
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'r26_nets.json')))
rep = []
for nn, conns in J.items():
    nt = net(nn); L_ = 0.0; nv = 0
    for c in conns:
        assert c, nn + ': no route'
        for lay, pts in c['segments']:
            add(lay, [tuple(p) for p in pts], nt, c['width'])
            L_ += sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        for v in c['vias']: add_via(v[0], v[1], nt); nv += 1
    rep.append('%s %.1f mm, %d vias' % (nn, L_, nv))
print('nets: ' + '; '.join(rep))
