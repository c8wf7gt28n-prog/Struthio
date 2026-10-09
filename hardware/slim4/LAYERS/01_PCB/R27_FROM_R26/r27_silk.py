# R27 edit 43: silkscreen labels on the back, where the parts are (R26 had no silkscreen text; pre-order review AUDIO_IO
# M5): the battery plug's polarity ("+" level with J3 pin 1, "-" with pin 2, "BAT"), the speaker sides (J4 "SPK L", J5 "SPK R") and the three
# small buttons (SW5 "PWR", SW6 "RST", SW7 "BOOT"). Back-side text is mirrored so it reads from the back. Each label
# goes on the first side of its part (and the first of three gaps) where its outline clears every pad, every
# courtyard and the board edge by 0.15 mm.
exec(open(sys.argv[2]).read())
SILK=b.GetLayerID('B.SilkS')
back=[f for f in b.GetFootprints() if f.IsFlipped() and not _dead(f)]
for f in back: f.BuildCourtyardCaches()
def box_clear(bb):
    c=MM(0.15)
    r=pcbnew.BOX2I(bb.GetPosition(), bb.GetSize()); r.Inflate(c)
    poly=pcbnew.SHAPE_POLY_SET(); poly.NewOutline()
    for x,y in ((r.GetLeft(),r.GetTop()),(r.GetRight(),r.GetTop()),(r.GetRight(),r.GetBottom()),(r.GetLeft(),r.GetBottom())):
        poly.Append(x,y)
    for f in back:
        for p in f.Pads():
            if p.IsOnLayer(L['B.Cu']) and r.Intersects(p.GetBoundingBox()): return False
        cy=f.GetCourtyard(pcbnew.B_CrtYd)
        if cy.OutlineCount():
            x=poly.CloneDropTriangulation(); x.BooleanIntersection(cy, pcbnew.SHAPE_POLY_SET.PM_FAST)
            if x.Area()>0: return False
    edge=b.GetBoardEdgesBoundingBox()
    if not edge.Contains(r): return False
    seg=[pcbnew.SEG(pcbnew.VECTOR2I(*a),pcbnew.VECTOR2I(*c_)) for a,c_ in
         (((r.GetLeft(),r.GetTop()),(r.GetRight(),r.GetTop())),((r.GetRight(),r.GetTop()),(r.GetRight(),r.GetBottom())),
          ((r.GetRight(),r.GetBottom()),(r.GetLeft(),r.GetBottom())),((r.GetLeft(),r.GetBottom()),(r.GetLeft(),r.GetTop())))]
    for d in b.GetDrawings():
        if d.GetLayer()==b.GetLayerID('Edge.Cuts') and any(d.GetEffectiveShape().Collide(s, MM(0.3)) for s in seg): return False
    return True
def text(s, x, y, h=0.8):
    t=pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(SILK); t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(h),MM(h))); t.SetTextThickness(MM(0.15))
    t.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y))); return t
def label(s, anchor, around, h=0.8, sides=None):
    """Put text s beside the box `around` (x0,y0,x1,y1 mm), level with `anchor`: the sides in the order given
    (default: nearest first), each at three gaps."""
    x0,y0,x1,y1=around; ax,ay=anchor
    t=text(s,0,0,h); bb0=t.GetBoundingBox(); w=mm(bb0.GetWidth()); hh=mm(bb0.GetHeight())
    at={'above':lambda g:(ax, y0-g-hh/2), 'below':lambda g:(ax, y1+g+hh/2), 'left':lambda g:(x0-g-w/2, ay),
        'right':lambda g:(x1+g+w/2, ay)}
    if sides:
        cands=[at[sd](g) for sd in sides for g in (0.35,0.8,1.4)]
    else:
        cands=sorted((at[sd](g) for sd in at for g in (0.35,0.8,1.4)), key=lambda c: math.hypot(c[0]-ax,c[1]-ay))
    for cx,cy in cands:
        t.SetPosition(pcbnew.VECTOR2I(MM(cx),MM(cy)))
        if box_clear(t.GetBoundingBox()):
            b.Add(t); return '%s (%.2f, %.2f)'%(s,cx,cy)
    raise AssertionError('no room for label '+s)
def bbox_mm(ref):
    f=fpr(ref); cy=f.GetCourtyard(pcbnew.B_CrtYd); bb=cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False,False)
    return (mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom()))
done=[]
j3=bbox_mm('J3'); p1=padxy('J3','1')
done.append(label('+', p1, j3, 1.2, sides=('left',)))
done.append(label('-', padxy('J3','2'), j3, 1.2, sides=('left',)))
done.append(label('BAT', ((j3[0]+j3[2])/2,(j3[1]+j3[3])/2), j3))
for ref,s,sides in (('J4','SPK L',None),('J5','SPK R',None),('SW5','PWR',('right','left','above','below')),
                    ('SW6','RST',('right','left','above','below')),('SW7','BOOT',('right','left','above','below'))):
    bb=bbox_mm(ref); done.append(label(s, ((bb[0]+bb[2])/2,(bb[1]+bb[3])/2), bb, sides=sides))
print('silk: '+', '.join(done))
