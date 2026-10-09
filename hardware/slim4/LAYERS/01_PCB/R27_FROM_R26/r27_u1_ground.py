# R27 edit 36: ground vias under U1's exposed pad. The pad (7.5 mm square, nine 2.1 mm paste segments on B.Cu) is the
# ESP32-P4's only GND connection, and R26 joined it to the ground planes through 4 vias of 0.2 mm (pre-order review,
# CHECKS/PREORDER_REVIEW_R26/P4CORE_findings.md M3; Espressif's guideline: as many as possible). This edit adds GND
# vias wherever a 0.45/0.2 mm through via keeps 0.15 mm from every other net's copper on every
# layer (the DSI D0 lane and slow nets cross under U1 on inner layers). The order already specifies vias in pads
# filled and capped, so solder does not wick into them.
exec(open(sys.argv[2]).read())
EP=(-3.75, 80.25, 3.75, 87.75)
others=_copper_items()
before=sum(1 for t in others if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND'
           and EP[0]<=mm(t.GetPosition().x)<=EP[2] and EP[1]<=mm(t.GetPosition().y)<=EP[3])
# Every 0.1 mm spot inside the pad (0.3 mm in from its edge) where a via fits, taken in a fixed order (row by row),
# kept 0.7 mm from each other and from existing vias: the DSI CLK pair over U1's west half on F.Cu and the slow nets
# crossing on In3 leave room for about 30.
ex=[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in others if t.Type()==pcbnew.PCB_VIA_T]
got=[]
for i in range(-34,35):
    for j in range(-34,35):
        x=round(i*0.1,2); y=round(84+j*0.1,2)
        if not (EP[0]+0.3<=x<=EP[2]-0.3 and EP[1]+0.3<=y<=EP[3]-0.3): continue
        if any(math.hypot(x-q[0],y-q[1])<0.7 for q in got+ex): continue
        if via_free(x,y,'GND',0.15,others):
            add_via(x,y,G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x),MM(y))); got.append((x,y))
print('u1 ground: exposed pad vias %d -> %d (%d added)'%(before, before+len(got), len(got)))
assert before+len(got)>=16, 'fewer than 16 ground vias under U1'
