# R25 edit 25: the six 0-ohm DSI links R301-R306 removed; each CPU-side route joined straight to its panel-side route.
#  R301-R306 sat with their CPU-side pad facing away from U1, so every CPU-side route ran past its resistor and came back
#  (CLK_P by a 7 mm, three-via detour). Without them each DSI signal is one net from U1 to J1, shorter, with no pad
#  discontinuity; DSI_*_SOC tracks and U1 pads 35-40 (DSI pins) take the panel-side net names.
exec(open(sys.argv[2]).read())
def seg_kill(netname, lay, x1, y1, x2, y2, tol=0.004):
    hit=[t for t in TR if t.GetNetname()==netname and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L[lay] and
         ((near(t.GetStart(),x1,y1,tol) and near(t.GetEnd(),x2,y2,tol)) or (near(t.GetStart(),x2,y2,tol) and near(t.GetEnd(),x1,y1,tol)))]
    assert len(hit)==1,(netname,lay,x1,y1,x2,y2,len(hit)); KILL.append(hit[0])
def via_kill(netname, x, y, tol=0.004):
    hit=[t for t in TR if t.GetNetname()==netname and t.Type()==pcbnew.PCB_VIA_T and near(t.GetPosition(),x,y,tol)]
    assert len(hit)==1,(netname,x,y); KILL.append(hit[0])
def link(netname, lay, pts, w):
    nc=net(netname).GetNetCode(); obs,zs=_obstacles(L[lay],nc)
    # the SOC net still carries its old name until the rename below: treat it as the same signal
    soc=net(SOCOF[netname]).GetNetCode()
    obs=[o for o in obs if o.GetNetCode()!=soc]
    assert _poly_free(pts, w, L[lay], nc, 0.1, obs, zs), (netname, lay, pts)
    add(lay, pts, net(netname), w)
SOCOF={'MIPI_DSI_%s'%s:'DSI_%s_SOC'%s for s in ('CLK_P','CLK_N','D0_P','D0_N','D1_P','D1_N')}
for r in ('R301','R302','R303','R304','R305','R306'): KILL.append(fpr(r))

# CLK_P: SOC F.Cu run down x -1.1 ends at (-1.1, 94.3); join it on F.Cu to the panel-side via (-1.303, 96.537).
for seg in ((-1.1,94.3,-2.9,96.1),(-2.9,96.1,-2.9,96.7),(-2.9,96.7,-2.7,96.9),(-2.7,96.9,-2.2,96.9),(-2.2,96.9,-2.1,97.0),(-2.1,97.0,-1.1,97.0),(-1.1,97.0,-1.1,97.05)):
    seg_kill('DSI_CLK_P_SOC','F.Cu',*seg)
via_kill('DSI_CLK_P_SOC',-1.1,97.05)
for seg in ((-0.9,96.85,-1.1,97.05),(-0.8,95.8,-0.8,96.65),(-0.8,96.65,-0.9,96.75),(-0.9,96.75,-0.9,96.85)): seg_kill('DSI_CLK_P_SOC','B.Cu',*seg)
for seg in ((-1.303,95.303,-1.303,96.537),(-0.8,94.8,-1.303,95.303)): seg_kill('MIPI_DSI_CLK_P','B.Cu',*seg)
link('MIPI_DSI_CLK_P','F.Cu',[(-1.1,94.3),(-1.303,94.503),(-1.303,96.537)],0.1)

# CLK_N: SOC B.Cu down x 1.642 meets the panel-side via (0.8, 93.873) by a 0.84 mm jog.
seg_kill('DSI_CLK_N_SOC','B.Cu',1.642,91.851,1.642,94.958); seg_kill('DSI_CLK_N_SOC','B.Cu',1.642,94.958,0.8,95.8)
seg_kill('MIPI_DSI_CLK_N','B.Cu',0.8,94.8,0.8,93.873)
link('MIPI_DSI_CLK_N','B.Cu',[(1.642,91.851),(1.642,93.873),(0.8,93.873)],0.152)

# D0_P: the SOC In3 diagonal joins the panel-side In3 run at (-1.75, 96.15); both D0_P vias there go.
seg_kill('DSI_D0_P_SOC','In3.Cu',-3.925,94.912,-2.4,96.437); via_kill('DSI_D0_P_SOC',-2.4,96.437)
seg_kill('DSI_D0_P_SOC','B.Cu',-2.4,95.8,-2.4,96.437)
seg_kill('MIPI_DSI_D0_P','B.Cu',-1.73,95.47,-1.73,96.128); seg_kill('MIPI_DSI_D0_P','B.Cu',-2.4,94.8,-1.73,95.47)
via_kill('MIPI_DSI_D0_P',-1.73,96.128)                 # In3 on both sides now: the via is not needed
link('MIPI_DSI_D0_P','In3.Cu',[(-3.925,94.912),(-2.741,96.096),(-1.75,96.15)],0.152)

# D0_N: its SOC via (-4.529, 92.904) stays; B.Cu from it runs through R304's old place to the panel-side via (-3.479, 94.279)
# (a straight In3 drop would cross D0_P's In3 diagonal).
seg_kill('DSI_D0_N_SOC','B.Cu',-4.529,95.271,-4.529,92.904); seg_kill('DSI_D0_N_SOC','B.Cu',-4.0,95.8,-4.529,95.271)
seg_kill('MIPI_DSI_D0_N','B.Cu',-4.0,94.8,-3.479,94.279)
link('MIPI_DSI_D0_N','B.Cu',[(-4.529,92.904),(-4.529,93.8),(-4.05,94.279),(-3.479,94.279)],0.152)

# D1_N: the SOC via (1.663, 95.564) joins the panel-side B.Cu at (2.903, 95.511) straight across R306's old place.
seg_kill('DSI_D1_N_SOC','B.Cu',1.663,95.564,2.164,95.564); seg_kill('DSI_D1_N_SOC','B.Cu',2.164,95.564,2.4,95.8)
seg_kill('MIPI_DSI_D1_N','B.Cu',2.4,94.8,2.903,95.303); seg_kill('MIPI_DSI_D1_N','B.Cu',2.903,95.303,2.903,95.511)
link('MIPI_DSI_D1_N','B.Cu',[(1.663,95.564),(2.903,95.511)],0.152)

# D1_P: the SOC B.Cu run down x 3.497 continues through R305's old place to the panel-side via (4.3, 94.5).
seg_kill('DSI_D1_P_SOC','B.Cu',4.0,95.8,3.497,95.297)
mp=[t for t in TR if t.GetNetname()=='MIPI_DSI_D1_P' and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['B.Cu']]
for t in mp: KILL.append(t)          # the pad-to-via stub at R305
link('MIPI_DSI_D1_P','B.Cu',[(3.497,95.297),(3.497,95.6),(4.3,95.6),(4.3,94.5)],0.152)

# one net per signal from U1 to J1
for s,(soc) in [(k,v) for k,v in SOCOF.items()]:
    n=net(s)
    for t in b.GetTracks():
        if t.GetNetname()==soc and t not in KILL: t.SetNet(n)
    for p in fpr('U1').Pads():
        if p.GetNetname()==soc: p.SetNet(n)
print('dsi links: done')
