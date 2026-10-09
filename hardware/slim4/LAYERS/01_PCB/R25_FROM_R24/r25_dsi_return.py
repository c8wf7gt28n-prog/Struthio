# R25 edit 27: return-current vias after the DSI relink. Removing R301-R306 and adding the direct links moved or removed
# several DSI vias, so some now sit 1.3-1.75 mm from the nearest ground via. Each DSI via beyond 1.0 mm gets a ground
# via as close as one fits (spiral search to 1.2 mm on free copper, 0.11 mm clearance on every layer).
exec(open(sys.argv[2]).read())
POS=lambda t:(mm(t.GetPosition().x),mm(t.GetPosition().y))
gnd=lambda: [POS(t) for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND']
vias=[t for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname().startswith('MIPI_DSI')]
near_d=lambda x,y: min(math.hypot(gx-x,gy-y) for gx,gy in gnd())
for v in sorted(vias, key=lambda v: -near_d(*POS(v))):
    if near_d(*POS(v))>1.0: add_vias_near('GND',*POS(v),1,rmax=1.2,step=0.05,clr=0.11)
ds=sorted(near_d(*POS(v)) for v in vias)
print('dsi return: %d DSI vias, %d within 1.0 mm, %d within 1.2 mm, worst %.2f mm'%(len(ds),sum(d<=1.0 for d in ds),sum(d<=1.2 for d in ds),ds[-1]))
