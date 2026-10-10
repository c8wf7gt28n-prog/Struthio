# R27 edit 36: ground vias in U1's exposed pad. The land (pad 105 on B.Cu: nine 2.1 mm copper squares 2.7 mm apart,
# each with its own mask and paste opening, solder mask in the 0.6 mm gaps) is the ESP32-P4's only GND connection, and
# R26 joined it to the ground planes through 4 vias of 0.2 mm (pre-order review,
# CHECKS/PREORDER_REVIEW_R26/P4CORE_findings.md M3; Espressif's guideline: as many as possible). This edit adds GND
# vias whose whole 0.45 mm land lies inside one of the nine squares, so each joins the pad's own copper, and then vias
# in the gaps, each joined to the nearest square by a 0.25 mm B.Cu stub under the gap's mask (without it a gap via
# would reach only the inner planes), wherever a 0.45/0.2 mm through via keeps 0.15 mm from every other net's
# copper on every layer (the DSI D0 lane and slow nets cross under U1 on inner layers). The order specifies every via
# epoxy filled and capped (POFV), so solder does not wick into them.
exec(open(sys.argv[2]).read())
EP=(-3.75, 80.25, 3.75, 87.75)
U1=b.FindFootprintByReference('U1')
SQ=[(mm(p.GetPosition().x), mm(p.GetPosition().y), mm(p.GetSize().x)/2) for p in U1.Pads() if p.GetNumber()=='105']
assert len(SQ)==9 and all(abs(h-1.05)<1e-6 for _,_,h in SQ), 'U1 pad 105 is not nine 2.1 mm squares'
def in_square(x, y):
    return any(abs(x-px)<=h-0.225+1e-9 and abs(y-py)<=h-0.225+1e-9 for px,py,h in SQ)
others=_copper_items()
before=sum(1 for t in others if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND'
           and EP[0]<=mm(t.GetPosition().x)<=EP[2] and EP[1]<=mm(t.GetPosition().y)<=EP[3])
# Every 0.1 mm spot where a via's land fits inside a square and the via fits, taken in a fixed order (row by row),
# kept 0.7 mm from each other and from existing vias.
ex=[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in others if t.Type()==pcbnew.PCB_VIA_T]
got=[]
for i in range(-34,35):
    for j in range(-34,35):
        x=round(i*0.1,2); y=round(84+j*0.1,2)
        if not in_square(x, y): continue
        if any(math.hypot(x-q[0],y-q[1])<0.7 for q in got+ex): continue
        if via_free(x,y,'GND',0.15,others):
            add_via(x,y,G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x),MM(y))); got.append((x,y))
inside=len(got)
# Second pass: the gaps (0.3 mm in from the land's outline), each via with a stub from its centre to 0.1 mm inside the
# nearest square, checked for clearance on B.Cu like any track.
for i in range(-34,35):
    for j in range(-34,35):
        x=round(i*0.1,2); y=round(84+j*0.1,2)
        if in_square(x, y) or not (EP[0]+0.3<=x<=EP[2]-0.3 and EP[1]+0.3<=y<=EP[3]-0.3): continue
        if any(math.hypot(x-q[0],y-q[1])<0.7 for q in got+ex): continue
        if not via_free(x,y,'GND',0.15,others): continue
        px,py,h=min(SQ, key=lambda q: math.hypot(x-min(max(x,q[0]-q[2]),q[0]+q[2]), y-min(max(y,q[1]-q[2]),q[1]+q[2])))
        tx=min(max(x,px-h+0.1),px+h-0.1); ty=min(max(y,py-h+0.1),py+h-0.1)
        if not seg_free('B.Cu',(x,y),(tx,ty),0.25,G.GetNetCode(),0.15,others): continue
        add_via(x,y,G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x),MM(y))); got.append((x,y))
        add('B.Cu',[(x,y),(tx,ty)],G,0.25)
print('u1 ground: exposed pad vias %d -> %d (%d added: %d inside the nine pad squares, %d in the gaps with a B.Cu stub '
      'to a square)'%(before, before+len(got), len(got), inside, len(got)-inside))
assert before+len(got)>=16, 'fewer than 16 ground vias under U1'
