# R26 edit 33: ground reference on In2 for the DSI pairs' In3 sections (R25 edit 29's band, redrawn for the new
# routes). On JLCPCB's JLC06121H-3313 stackup In3 sits 0.1088 mm (2116 prepreg) below In2 and 0.35 mm (core) above the
# In4 ground plane, so In2 is the nearer reference, and In2 is the power layer. A GND area on In2 covers every In3 DSI
# segment with 0.6 mm to spare each side (more than 5x the 0.109 mm height), the runs joined into one band, so on In3
# the pairs are striplines between ground on both sides (0.10 mm lines, 0.18 mm gap: about 98 ohm differential,
# IPC-2141 asymmetric stripline with the coupled-stripline factor). The band is stitched by the ground vias it covers
# and clears other nets by 0.15 mm, like the In1 and In4 planes (edit 31).
#  Where D0 runs under U1 the band crosses the south strip of the In2 1V1_HP area; the 1V1 via at (6.09, 87.58) that
#  feeds U1's south-row core pins would be left on an island, so a 0.4 mm 1V1 channel on In2 joins it to the main
#  1V1 area to the north-west (up X 6.09, west along Y 86.4). The channel stays north of D0: between D0's copper and
#  1V1 the band keeps 0.32 mm (about 3 heights) along the channel and 0.22 mm at the feed via, 0.6 mm everywhere else.
#  Return vias: every DSI layer change between differently referenced layers (B.Cu or In3 to F.Cu: In4/In2 to In1)
#  needs a ground via on each side of the pair; B.Cu -> In3 (D0, D1 breakouts) shares In4, the plane between the two
#  layers, and needs none. Where the via row has none (edit 32 puts them beside the second via pair where they fit),
#  two ground vias go in mirror-symmetric about the pair (equal distance to P and N) at the nearest free pair of
#  spots within 1.6 mm; where no such pair is free, one ground via on the pair's axis (equally far from P and N)
#  within 2.2 mm; failing that, each side keeps its nearest existing ground via or gets the nearest free spot within
#  2.2 mm. The report lists what each transition got.
exec(open(sys.argv[2]).read())
LIN2=L['In2.Cu']; LIN3=L['In3.Cu']
band=pcbnew.SHAPE_POLY_SET()
segs=[t for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==LIN3 and t.GetNetname().startswith('MIPI_DSI')]
segs.sort(key=lambda t: (t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y))   # same band every build
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
import json, os
J=json.load(open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'r26_dsi_routes.json')))
others=_copper_items(); ret=[]
for name in ('D0','D1','CLK'):
    vp,vn=J['vias']['MIPI_DSI_%s_P'%name],J['vias']['MIPI_DSI_%s_N'%name]
    for k in range(len(vp)):
        if k==1 and J['pairs'][name]['via'][2]: ret.append('%s row 2: in-row'%name); continue
        if k==0 and J['pairs'][name]['start']['layer']=='In3.Cu':
            # B.Cu -> In3: both reference In4 (the plane between them), so the return current stays on In4 round the hole
            P,N=vp[k],vn[k]; m=((P[0]+N[0])/2,(P[1]+N[1])/2)
            dg=min(math.dist((mm(t.GetPosition().x),mm(t.GetPosition().y)),m) for t in others if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND')
            ret.append('%s breakout: B.Cu-In3, shared In4 reference (nearest ground via %.2f mm)'%(name,dg)); continue
        P,N=vp[k],vn[k]; m=((P[0]+N[0])/2,(P[1]+N[1])/2); d=math.dist(P,N); u=((P[0]-N[0])/d,(P[1]-N[1])/d); n=(-u[1],u[0])
        gv=[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in others if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='GND']
        gv=[g for g in gv if math.dist(g,m)<=1.6]
        side=lambda g: (g[0]-m[0])*u[0]+(g[1]-m[1])*u[1]
        if any(side(g)>0.05 for g in gv) and any(side(g)<-0.05 for g in gv):
            near_=sorted(gv,key=lambda g: math.dist(g,m))
            gp=min((g for g in gv if side(g)>0.05),key=lambda g: math.dist(g,m)); gn=min((g for g in gv if side(g)<-0.05),key=lambda g: math.dist(g,m))
            ret.append('%s %s: existing, %.2f / %.2f mm on the P / N side'%(name,('breakout','row 2')[k],math.dist(gp,m),math.dist(gn,m))); continue
        cands=sorted((math.hypot(a,bb),a,bb) for a in [0.75+0.05*i for i in range(16)] for bb in [-1.2+0.05*j for j in range(49)] if math.hypot(a,bb)<=1.6)
        got=None
        for dd,a,bb in cands:      # mirror-symmetric pair first
            g1=(round(m[0]+a*u[0]+bb*n[0],3),round(m[1]+a*u[1]+bb*n[1],3)); g2=(round(m[0]-a*u[0]+bb*n[0],3),round(m[1]-a*u[1]+bb*n[1],3))
            if via_free(*g1,'GND',0.12,others) and via_free(*g2,'GND',0.12,others): got=(g1,g2); break
        how='mirror-symmetric'
        if not got:                # else one ground via on the pair's axis (equally far from P and N)
            ax=sorted((abs(t_),(round(m[0]+t_*n[0],3),round(m[1]+t_*n[1],3))) for t_ in [sg*(0.6+0.05*i) for i in range(33) for sg in (1,-1)])
            f=next((p_ for dd,p_ in ax if via_free(*p_,'GND',0.12,others) and all((pcbnew.VECTOR2I(MM(p_[0]),MM(p_[1]))-v).EuclideanNorm()>=MM(0.6) for v in NEW_VIAS)),None)
            if f:
                add_via(*f,net('GND')); NEW_VIAS.append(pcbnew.VECTOR2I(MM(f[0]),MM(f[1])))
                ret.append('%s %s: on the axis, (%.2f, %.2f) %.2f mm'%(name,('breakout','row 2')[k],*f,math.dist(f,m))); continue
        if not got:                # else the nearest ground via on each side, existing or new
            how='one each side'; got=[]
            for sg in (1,-1):
                ex=[g for g in gv if sg*side(g)>0.05]
                if ex: got.append(min(ex,key=lambda g: math.dist(g,m))); continue
                pts=sorted((math.hypot(x,y),(round(m[0]+x,3),round(m[1]+y,3))) for x in [-2.2+0.05*i for i in range(89)] for y in [-2.2+0.05*j for j in range(89)])
                f=next((p_ for dd,p_ in pts if dd<=2.2 and sg*side(p_)>0.3 and via_free(*p_,'GND',0.12,others) and all((pcbnew.VECTOR2I(MM(p_[0]),MM(p_[1]))-v).EuclideanNorm()>=MM(0.6) for v in NEW_VIAS)),None)
                assert f, (name,k,'no return via on side',sg)
                add_via(*f,net('GND')); NEW_VIAS.append(pcbnew.VECTOR2I(MM(f[0]),MM(f[1]))); got.append(f)
        else:
            for g in got: add_via(*g,net('GND')); NEW_VIAS.append(pcbnew.VECTOR2I(MM(g[0]),MM(g[1])))
        ret.append('%s %s: %s, (%.2f, %.2f) %.2f mm / (%.2f, %.2f) %.2f mm'%(name,('breakout','row 2')[k],how,*got[0],math.dist(got[0],m),*got[1],math.dist(got[1],m)))
print('dsi ref: return vias: '+'; '.join(ret))
FEED=(6.0945,87.5767)
assert any(t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()=='1V1_HP' and near(t.GetPosition(),*FEED) for t in b.GetTracks())
ch=rect_poly([(5.89,86.2,6.29,FEED[1]),(4.2,86.2,6.29,86.6)])
cut=ch.CloneDropTriangulation(); cut.Inflate(MM(0.15),16)
outl.BooleanSubtract(cut, pcbnew.SHAPE_POLY_SET.PM_FAST)
z1=[zz for zz in b.Zones() if zz.GetNetname()=='1V1_HP' and zz.IsOnLayer(LIN2)]
assert len(z1)==1
o1=z1[0].Outline().CloneDropTriangulation(); o1.BooleanAdd(ch, pcbnew.SHAPE_POLY_SET.PM_FAST); o1.Simplify(pcbnew.SHAPE_POLY_SET.PM_FAST)
z1[0].Outline().RemoveAllContours(); z1[0].Outline().Append(o1)
z=zone('In2.Cu', [], 'GND', prio=6, clearance=0.15, minw=0.15, conn='solid', name='DSI_REF_IN2')
z.Outline().RemoveAllContours(); z.Outline().Append(outl)
ov={}
for zz in b.Zones():
    if zz.IsOnLayer(LIN2) and zz.GetNetname()!='GND' and not zz.GetIsRuleArea():
        o=outl.CloneDropTriangulation(); o.BooleanIntersection(zz.Outline(), pcbnew.SHAPE_POLY_SET.PM_FAST)
        if o.Area()>0: ov[zz.GetNetname()]=ov.get(zz.GetNetname(),0)+o.Area()/1e12
print('dsi ref: 1V1 feed channel to (%.2f, %.2f) added'%FEED)
print('dsi ref: In2 GND band over %d In3 DSI segments, %d outline(s), %.1f mm2; overlaps In2 areas: %s'%(len(segs), outl.OutlineCount(), outl.Area()/1e12, ', '.join('%s %.2f mm2'%kv for kv in sorted(ov.items())) or 'none'))
