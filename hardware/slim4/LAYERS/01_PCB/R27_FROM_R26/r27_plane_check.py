# R27 check (after the zone fill): the core regulator's feedback and enable routes (FB_DCDC, EN_DCDC, 17-20 mm from
# U1 to U3, pre-order review P4CORE M1) run over unbroken ground: every F.Cu segment over In1's filled GND and every
# B.Cu segment over In4's, along its whole length widened by 0.2 mm each side. Moving U3 next to U1 would mean moving
# a dozen parts and the DSI escape; the divider (R104/R105/C134) is within 3 mm of U3's FB pin and the route's
# same-layer neighbours are static nets (CHIP_PU, 3V3_SYS, EN_DCDC, 1V1_HP), so the plane is what is checked.
# Usage: python3 r27_plane_check.py BOARD.kicad_pcb
import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); MM=pcbnew.FromMM; mm=pcbnew.ToMM
REF={'F.Cu':'In1.Cu','B.Cu':'In4.Cu'}
import math
def capsule(a, c, r, n=16):
    """All points within r of segment a-c (board units), as a polygon."""
    ang=math.atan2(c.y-a.y, c.x-a.x); pts=[]
    for k in range(n+1):
        th=ang-math.pi/2+math.pi*k/n; pts.append((c.x+r*math.cos(th), c.y+r*math.sin(th)))
    for k in range(n+1):
        th=ang+math.pi/2+math.pi*k/n; pts.append((a.x+r*math.cos(th), a.y+r*math.sin(th)))
    sp=pcbnew.SHAPE_POLY_SET(); sp.NewOutline()
    for x,y in pts: sp.Append(int(x),int(y))
    return sp
bad=[]; edges=[]; n=0; total=0.0; worst=0.0
for t in b.GetTracks():
    if t.Type()==pcbnew.PCB_VIA_T or t.GetNetname() not in ('FB_DCDC','EN_DCDC'): continue
    lay=b.GetLayerName(t.GetLayer())
    if lay not in REF: bad.append('%s on %s'%(t.GetNetname(),lay)); continue
    ref=b.GetLayerID(REF[lay])
    fill=pcbnew.SHAPE_POLY_SET()
    for z in b.Zones():
        if z.GetNetname()=='GND' and z.IsOnLayer(ref): fill.BooleanAdd(z.GetFilledPolysList(ref), pcbnew.SHAPE_POLY_SET.PM_FAST)
    # the track's own copper, less its ends where they meet the route's own vias and pads (their antipads and U1's pad
    # ring are holes in the plane by design)
    strip=capsule(t.GetStart(), t.GetEnd(), t.GetWidth()/2)
    for pt in (t.GetStart(), t.GetEnd()):
        own=any(v.Type()==pcbnew.PCB_VIA_T and v.GetNetCode()==t.GetNetCode() and (v.GetPosition()-pt).EuclideanNorm()<MM(0.05)
                for v in b.GetTracks())
        own=own or any(p.GetNetCode()==t.GetNetCode() and p.HitTest(pt) for f in b.GetFootprints() for p in f.Pads())
        if own: strip.BooleanSubtract(capsule(pt, pt, MM(0.45)), pcbnew.SHAPE_POLY_SET.PM_FAST)
    out=strip.CloneDropTriangulation(); out.BooleanSubtract(fill, pcbnew.SHAPE_POLY_SET.PM_FAST)
    a=out.Area()/1e12; worst=max(worst, a)
    if a > 0.002:
        # allowed only where the plane's hole is another net's via antipad (via radius + the plane's 0.15 mm clearance):
        # the track then crosses the edge of a clearance ring, not a split in the plane
        # ... or a slot round another net's track on the plane layer itself (the track crosses it)
        rings=pcbnew.SHAPE_POLY_SET(); names=set(); slots=set()
        sg=pcbnew.SEG(t.GetStart(),t.GetEnd())
        for v in b.GetTracks():
            if v.GetNetname()=='GND': continue
            if v.Type()==pcbnew.PCB_VIA_T:
                pos=v.GetPosition()
                if sg.Distance(pos) < v.GetWidth()//2+MM(0.15)+t.GetWidth()//2+MM(0.01):
                    rings.BooleanAdd(capsule(pos,pos,v.GetWidth()//2+MM(0.16)), pcbnew.SHAPE_POLY_SET.PM_FAST)
                    names.add('its own' if v.GetNetCode()==t.GetNetCode() else v.GetNetname())
            elif v.GetLayer()==ref and v.GetNetCode()!=t.GetNetCode():
                band=capsule(v.GetStart(), v.GetEnd(), v.GetWidth()//2+MM(0.16))
                x=band.CloneDropTriangulation(); x.BooleanIntersection(out, pcbnew.SHAPE_POLY_SET.PM_FAST)
                if x.Area()>0: rings.BooleanAdd(band, pcbnew.SHAPE_POLY_SET.PM_FAST); slots.add(v.GetNetname())
        rest=out.CloneDropTriangulation(); rest.BooleanSubtract(rings, pcbnew.SHAPE_POLY_SET.PM_FAST)
        where='%s %s (%.2f, %.2f)-(%.2f, %.2f): %.3f mm2'%(t.GetNetname(), lay, mm(t.GetStart().x), mm(t.GetStart().y),
                                                           mm(t.GetEnd().x), mm(t.GetEnd().y), a)
        if rest.Area()/1e12 > 0.002: bad.append(where+' of track over a hole in %s that is not a via antipad'%REF[lay])
        else:
            what=[]
            if names: what.append('the edge of %s via antipad'%'/'.join(sorted(n_ if n_=='its own' else 'a '+n_ for n_ in names)))
            if slots: what.append('the slot round %s on %s'%('/'.join(sorted(slots)), REF[lay]))
            edges.append(where+' over '+' and '.join(what))
    n+=1; total+=mm(t.GetLength())
print('plane check: FB_DCDC/EN_DCDC %d segments, %.1f mm: %s; %d cross a via antipad edge or another net\'s slot '
      '(largest %.3f mm2 of track)'%(n, total, 'no other gap in their ground planes' if not bad else 'GAPS', len(edges), worst))
for x in bad+edges: print('  '+x)
sys.exit(1 if bad else 0)
