# R23 edit 15, part C0: the DSI pairs between J1's column (ends at Y 90) and the 0-ohm links R301-R306. Everything
#  of the six DSI nets outside the hand-routed fan-out goes; R22's short stubs and vias at R301-R306 come back
#  (they were DRC-clean in R22), and part C1 joins each via to its column end.
exec(open(sys.argv[2]).read())
DSI=['MIPI_DSI_CLK_P','MIPI_DSI_CLK_N','MIPI_DSI_D0_P','MIPI_DSI_D0_N','MIPI_DSI_D1_P','MIPI_DSI_D1_N']
for t in b.GetTracks():
    if t.GetNetname() not in DSI: continue
    if t.Type()==pcbnew.PCB_VIA_T or t.GetLayer()!=L['F.Cu'] or max(mm(t.GetStart().y),mm(t.GetEnd().y))>90.01: KILL.append(t)
STUBS={'MIPI_DSI_CLK_P':([(-0.8,94.8),(-1.303,95.303),(-1.303,96.537)],(-1.303,96.537)),
       'MIPI_DSI_CLK_N':([(0.8,94.8),(0.8,93.873)],(0.8,93.873)),
       'MIPI_DSI_D0_P':([(-2.4,94.8),(-1.73,95.47),(-1.73,96.128)],(-1.73,96.128)),
       'MIPI_DSI_D0_N':([(-4.0,94.8),(-3.479,94.279)],(-3.479,94.279)),
       'MIPI_DSI_D1_P':([(4.0,94.8),(4.653,95.453),(4.653,95.938)],(4.653,95.938)),
       'MIPI_DSI_D1_N':([(2.4,94.8),(2.903,95.303),(2.903,95.511),(3.966,96.574),(5.889,96.574)],(5.889,96.574))}
for n,(pts,v) in STUBS.items():
    add("B.Cu",pts,net(n)); add_via(*v,net(n))
for t in b.GetTracks():
    if not _dead(t): t.SetLocked(True)
