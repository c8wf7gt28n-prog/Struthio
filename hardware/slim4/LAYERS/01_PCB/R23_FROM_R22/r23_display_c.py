# R23 edit 15, part C: the routed copper between J1's fan-out and the parts it serves, read from r23_display_c.json
#  (track segments and vias, mm). How it was made (the file records the result, so the build does not depend on
#  any router): the DSI lines and the backlight pair with a 0.05 mm grid search over F.Cu, In3 and B.Cu
#  (0.12 mm working clearance, 0.22 mm for LED+), P and N one after the other in the order that matched the pairs
#  best; VCI, IOVCC, RESX and the status nets with Freerouting 2.5.0 (fixed copper locked, keepouts at the battery
#  window and under J1's pad row); CHG_STATUS with the grid search (its north run is shortened to the new joint).
#  The DSI lines are length-matched with meanders: P = N within 0.01 mm; D0 56.25, D1 54.84, CLK 60.25 mm.
exec(open(sys.argv[2]).read())
import json
R=json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[2])),'r23_display_c.json')))
for t in R['tracks']:
    add(t['layer'],[tuple(t['a']),tuple(t['b'])],net(t['net']),t['w'])
for v in R['vias']:
    add_via(v['x'],v['y'],net(v['net']))
for m in R.get('trim',[]):                              # shorten an existing track to a new junction
    hit=[t for t in TR if t.GetNetname()==m['net'] and seg_match(t,m['layer'],*m['seg'])]
    assert len(hit)==1, m
    to=pcbnew.VECTOR2I(MM(m['to'][0]),MM(m['to'][1]))
    hit[0].SetStart(to) if near(hit[0].GetStart(),*m['end']) else hit[0].SetEnd(to)
print('part C:',len(R['tracks']),'segments,',len(R['vias']),'vias')
