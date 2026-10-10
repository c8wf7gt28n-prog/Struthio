# R25 edit 29: ground reference for the DSI pairs on In3. On JLCPCB's 1.2 mm 6-layer stackup (JLC06121H-3313) In3 sits
# 0.116 mm (2116 prepreg) below In2 and 0.35 mm (core) above the In4 ground plane, so In2 is the nearer reference. In R24
# the DSI runs on In3 lay under a patchwork of In2 power pours (3V3_SYS, 1V1_HP, SYS_RAW) with gaps between them. A GND
# area on In2 now covers every In3 DSI segment with 0.6 mm to spare each side (more than 5x the 0.116 mm height), joined
# into one band, so on In3 the pairs are striplines between ground on both sides; the band is stitched by the DSI
# return vias of edit 23/27 and the other ground vias it covers.
exec(open(sys.argv[2]).read())
LIN2=L['In2.Cu']; LIN3=L['In3.Cu']
band=pcbnew.SHAPE_POLY_SET()
segs=[t for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==LIN3 and t.GetNetname().startswith('MIPI_DSI')]
def capsule(a, c, r, n=16):
    """Polygon (mm) of all points within r of segment a-c: two half-circles joined."""
    ang=math.atan2(c[1]-a[1], c[0]-a[0]); pts=[]
    for k in range(n+1):                       # cap round c, facing away from a
        th=ang-math.pi/2+math.pi*k/n; pts.append((c[0]+r*math.cos(th), c[1]+r*math.sin(th)))
    for k in range(n+1):                       # cap round a, facing away from c
        th=ang+math.pi/2+math.pi*k/n; pts.append((a[0]+r*math.cos(th), a[1]+r*math.sin(th)))
    sp=pcbnew.SHAPE_POLY_SET(); sp.NewOutline()
    for x,y in pts: sp.Append(MM(x),MM(y))
    return sp
for t in segs:
    band.BooleanAdd(capsule((mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y)), mm(t.GetWidth())/2+0.6), pcbnew.SHAPE_POLY_SET.PM_FAST)
band.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
band.Inflate(MM(0.4), 16); band.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)     # close the gaps between neighbouring runs
band.Inflate(MM(-0.4), 16); band.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
outl=pcbnew.SHAPE_POLY_SET()
for i in range(band.OutlineCount()): outl.AddOutline(band.COutline(i))  # holes in the band become ground too
outl.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
z=zone('In2.Cu', [], 'GND', prio=6, clearance=0.2, minw=0.15, conn='solid', name='DSI_REF_IN2')
z.Outline().RemoveAllContours(); z.Outline().Append(outl)
ref1v1=[zz for zz in b.Zones() if zz.GetNetname()=='1V1_HP' and zz.IsOnLayer(LIN2)][0]
ov=outl.CloneDropTriangulation(); ov.BooleanIntersection(ref1v1.Outline(), pcbnew.SHAPE_POLY_SET.PM_FAST)
print('dsi ref: In2 GND band over %d In3 DSI segments, %d outline(s), %.1f mm2; overlaps the 1V1 area by %.2f mm2'%(len(segs), outl.OutlineCount(), outl.Area()/1e12, ov.Area()/1e12))
# 50 ohm single-ended on every layer of that stackup (Hammerstad-Jensen / IPC-2141 estimates): 0.152 mm on F.Cu/B.Cu
# over 0.0994 mm 3313 (about 50 ohm under solder mask); on In3, now between ground on In2 (0.1164 mm) and In4
# (0.35 mm), 0.152 mm would be 46.7 ohm, so the In3 DSI segments become 0.135 mm (50 ohm). Narrower necks (0.1 mm
# near U1 and on the CLK_P link) are widened to the layer's width where 0.1 mm clearance allows.
W50={'F.Cu':0.152,'B.Cu':0.152,'In3.Cu':0.135}
others=_copper_items(); nw=nn=0
for t in [t for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname().startswith('MIPI_DSI')]:
    lay=b.GetLayerName(t.GetLayer()); w=W50[lay]; cur=mm(t.GetWidth())
    if abs(cur-w)<1e-4: continue
    if cur>w: t.SetWidth(MM(w)); nn+=1; continue
    a=(mm(t.GetStart().x),mm(t.GetStart().y)); c=(mm(t.GetEnd().x),mm(t.GetEnd().y))
    if seg_free(lay,a,c,w,t.GetNetCode(),0.1,others): t.SetWidth(MM(w)); nw+=1
left=sum(mm(t.GetLength()) for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname().startswith('MIPI_DSI') and abs(mm(t.GetWidth())-W50[b.GetLayerName(t.GetLayer())])>1e-4)
print('dsi ref: In3 DSI segments set to 0.135 mm: %d; necks widened: %d; still narrower than 50 ohm width: %.2f mm'%(nn,nw,left))
