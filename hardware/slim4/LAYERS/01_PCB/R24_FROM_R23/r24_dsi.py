# R24 edit 23: return-current vias for MIPI-DSI. Every DSI via (a pair changing between F.Cu over In1 and In3/B.Cu
# over In4) had its nearest ground via 3-10 mm away, so the return current had no short path between the In1 and In4
# ground planes. Each DSI via or via pair now gets a ground via within 1.2 mm where one fits (searched on free copper,
# 0.11 mm clearance on every layer), else as close as one fits: all 32 within 1.75 mm, 24 within 1.2 mm.
exec(open(sys.argv[2]).read())
import re
vias=[t for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and 'DSI' in t.GetNetname() and t.GetNetname()!='DSI_REXT']
POS=lambda t:(mm(t.GetPosition().x),mm(t.GetPosition().y))
base=lambda n: re.sub(r'_(P|N)(_SOC)?$', r'_\2', n)
gnd=lambda: [POS(t) for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND']
done=set(); report=[]
for v in vias:
    if v in done: continue
    x,y=POS(v)
    mate=[w for w in vias if w is not v and w not in done and base(w.GetNetname())==base(v.GetNetname()) and w.GetNetname()!=v.GetNetname() and math.hypot(POS(w)[0]-x,POS(w)[1]-y)<1.5]
    group=[v]+mate[:1]
    cx=sum(POS(g)[0] for g in group)/len(group); cy=sum(POS(g)[1] for g in group)/len(group)
    if min(math.hypot(gx-cx,gy-cy) for gx,gy in gnd())<=1.0: done.update(group); continue
    got=add_vias_near('GND',cx,cy,1,rmax=1.2,step=0.05,clr=0.11)
    if not got and len(group)==2:     # no spot near the pair centre: one beside each via
        got=[q for g in group for q in add_vias_near('GND',*POS(g),1,rmax=1.2,step=0.05,clr=0.11)]
    report.append(([g.GetNetname() for g in group],(round(cx,2),round(cy,2)),got))
    done.update(group)
for r in report:                                  # second pass, wider search, for the ones still without a ground via
    if r[2]: continue
    cx,cy=r[1]
    if min(math.hypot(gx-cx,gy-cy) for gx,gy in gnd())>1.2: r[2].extend(add_vias_near('GND',cx,cy,1,rmax=1.6,step=0.05,clr=0.11))
for v in vias:                                    # last pass: any single via still beyond 1.7 mm
    if min(math.hypot(gx-POS(v)[0],gy-POS(v)[1]) for gx,gy in gnd())>1.7: add_vias_near('GND',*POS(v),1,rmax=2.0,step=0.05,clr=0.11)
for v in vias: print('dsi: %-16s (%.2f, %.2f) nearest ground via %.2f mm'%(v.GetNetname(),*POS(v),min(math.hypot(gx-POS(v)[0],gy-POS(v)[1]) for gx,gy in gnd())))

