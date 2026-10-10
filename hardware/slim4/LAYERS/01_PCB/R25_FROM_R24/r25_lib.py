# Helpers for the R24 -> R25 edits (executed inside run_edit.py with the board in `b`): r24_lib.py plus meanders (R25 edit 26),
# vias along a net's tracks, rectangle unions and polygon distances (edit 28); via_free also keeps same-net holes apart.
import pcbnew, sys, math
MM=pcbnew.FromMM; mm=pcbnew.ToMM
LIB='/usr/share/kicad/footprints/'
TR=list(b.GetTracks()); KILL=[]
L={n:b.GetLayerID(n) for n in ("F.Cu","In1.Cu","In2.Cu","In3.Cu","In4.Cu","B.Cu")}
def near(a,x,y,t=0.003): return abs(mm(a.x)-x)<t and abs(mm(a.y)-y)<t
def seg_match(t,lay,x1,y1,x2,y2):
    if t.GetClass()!="PCB_TRACK" or t.GetLayer()!=L[lay]: return False
    s,e=t.GetStart(),t.GetEnd()
    return (near(s,x1,y1) and near(e,x2,y2)) or (near(s,x2,y2) and near(e,x1,y1))
def remove(lay,x1,y1,x2,y2,net):
    hit=[t for t in TR if t.GetNetname()==net and seg_match(t,lay,x1,y1,x2,y2)]
    assert len(hit)==1,(lay,x1,y1,x2,y2,net,len(hit))
    if hit[0] not in KILL: KILL.append(hit[0])
def remove_via(x,y,net):
    hit=[t for t in TR if t.GetClass()=="PCB_VIA" and t.GetNetname()==net and near(t.GetPosition(),x,y)]
    assert len(hit)==1,(x,y,net); KILL.append(hit[0])
def add(lay,pts,net,w=0.152):
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x1),MM(y1))); t.SetEnd(pcbnew.VECTOR2I(MM(x2),MM(y2)))
        t.SetWidth(MM(w)); t.SetLayer(L[lay]); t.SetNet(net); b.Add(t)
def add_via(x,y,net):
    v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y))); v.SetWidth(MM(0.45)); v.SetDrill(MM(0.2))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(L["F.Cu"],L["B.Cu"]); v.SetNet(net); b.Add(v)
def pad(ref,num): return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber()==num][0]
def padxy(ref,num):
    p=pad(ref,num).GetPosition(); return (round(mm(p.x),4),round(mm(p.y),4))
def net(name, create=False):
    n=b.FindNet(name)
    if n is None and create:
        n=pcbnew.NETINFO_ITEM(b,name); b.Add(n)
    assert n is not None, name
    return n
def place(lib,name,ref,value,lcsc,note,x,y,rot,back=True,old=None):
    """Load a KiCad library footprint, put it on the back (default) at (x, y, rot) and give it the board's
    reference, value, description and local-library ID. `old` (a footprint) is removed and its attributes kept."""
    f=pcbnew.FootprintLoad(LIB+lib+'.pretty',name); b.Add(f)
    f.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y)))
    if back: f.Flip(f.GetPosition(),False)
    f.SetOrientationDegrees(rot)
    f.SetReference(ref); f.SetValue(value); f.Reference().SetVisible(False); f.Value().SetVisible(False)
    f.SetDescription(f'{value} | JLC {lcsc} | KiCad 7 library {lib}:{name} ({note})')
    f.SetFPID(pcbnew.LIB_ID('SLIM4','FP_'+ref))
    m=__import__('re').match(r'[A-Z]+_(\d{4})_(\d{4}Metric)$', name)
    if m: f.SetKeywords(f'SLIM4 R24 {ref[0]} {m[1]} {m[2]}')      # the board's tag convention (the BOM's package column)
    if old is not None:
        f.SetAttributes(old.GetAttributes()); KILL.append(old)
    return f
def pads_of(f):
    return {p.GetNumber()+('' if p.GetNumber()!='MP' else str(i)):p for i,p in enumerate(f.Pads())}
G=b.FindNet('GND')
_KS=[-1,set()]
def _dead(o):
    if _KS[0]!=len(KILL): _KS[1]={k.m_Uuid.AsString() for k in KILL}; _KS[0]=len(KILL)   # KILL only grows
    return o.m_Uuid.AsString() in _KS[1]
def _touch(pt, t_self):
    """True when point pt (board units) touches a pad, via or another track of the same net on a shared layer."""
    for f in b.GetFootprints():
        if _dead(f): continue
        for p in f.Pads():
            if p.GetNetCode()==t_self.GetNetCode() and p.IsOnLayer(t_self.GetLayer()) and p.HitTest(pt): return True
    for o in b.GetTracks():
        if o.m_Uuid.AsString()==t_self.m_Uuid.AsString() or _dead(o) or o.GetNetCode()!=t_self.GetNetCode(): continue
        if o.Type()==pcbnew.PCB_VIA_T:
            if (o.GetPosition()-pt).EuclideanNorm()<=o.GetWidth()//2: return True
        elif o.GetLayer()==t_self.GetLayer() and o.HitTest(pt, 1000): return True
    return False
def prune(nets, box):
    """Remove track segments of `nets` inside box (x0,y0,x1,y1 mm) left with a free end, repeatedly."""
    x0,y0,x1,y1=box; inb=lambda p: x0<=mm(p.x)<=x1 and y0<=mm(p.y)<=y1
    while True:
        dead=[t for t in b.GetTracks() if not _dead(t) and t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname() in nets
              and (inb(t.GetStart()) or inb(t.GetEnd())) and not (_touch(t.GetStart(),t) and _touch(t.GetEnd(),t))]
        if not dead: return
        KILL.extend(dead)
def prune_all(nets, box):
    """prune() that also removes vias of `nets` inside box joined to at most one track and no pad, repeatedly."""
    x0,y0,x1,y1=box; inb=lambda p: x0<=mm(p.x)<=x1 and y0<=mm(p.y)<=y1
    while True:
        prune(nets, box)
        dead=[]
        for v in b.GetTracks():
            if v.Type()!=pcbnew.PCB_VIA_T or _dead(v) or v.GetNetname() not in nets or not inb(v.GetPosition()): continue
            pos=v.GetPosition(); r=v.GetWidth()//2
            n=sum(1 for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and not _dead(t) and t.GetNetCode()==v.GetNetCode()
                  and min((t.GetStart()-pos).EuclideanNorm(),(t.GetEnd()-pos).EuclideanNorm())<=r)
            pad=any(p.GetNetCode()==v.GetNetCode() and p.GetEffectiveShape().Collide(pcbnew.SEG(pos,pos),r) for f in b.GetFootprints() if not _dead(f) for p in f.Pads())
            lays={t.GetLayer() for t in b.GetTracks() if t.Type()!=pcbnew.PCB_VIA_T and not _dead(t) and t.GetNetCode()==v.GetNetCode()
                  and min((t.GetStart()-pos).EuclideanNorm(),(t.GetEnd()-pos).EuclideanNorm())<=r}
            if (n<=1 or len(lays)==1) and not pad: dead.append(v)   # a via used on one layer only joins nothing
        if not dead: return
        KILL.extend(dead)

# ---- R24 additions -------------------------------------------------------------------------------------------
def fpr(ref): return b.FindFootprintByReference(ref)
def move(ref, x, y, rot=None):
    """Move a (back-side) footprint to (x, y); rot in degrees as KiCad shows it for the placed part."""
    f=fpr(ref); f.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y)))
    if rot is not None: f.SetOrientationDegrees(rot)
    return f
def kill_tracks(pred):
    """Queue every track/via for which pred(t) is true."""
    for t in b.GetTracks():
        if not _dead(t) and pred(t): KILL.append(t)
def in_box(p, box):
    x0,y0,x1,y1=box; return x0<=mm(p.x)<=x1 and y0<=mm(p.y)<=y1
def track_in_box(t, box):
    if t.Type()==pcbnew.PCB_VIA_T: return in_box(t.GetPosition(), box)
    return in_box(t.GetStart(), box) or in_box(t.GetEnd(), box)
ZCONN={'solid':pcbnew.ZONE_CONNECTION_FULL,'thermal':pcbnew.ZONE_CONNECTION_THERMAL}
def zone(lay, pts, netname, prio=5, clearance=0.15, minw=0.15, conn='solid', name=''):
    z=pcbnew.ZONE(b); z.SetLayer(L[lay]); z.SetNet(net(netname))
    o=z.Outline(); o.NewOutline()
    for x,y in pts: o.Append(MM(x),MM(y))
    z.SetAssignedPriority(prio); z.SetLocalClearance(MM(clearance)); z.SetMinThickness(MM(minw))
    z.SetPadConnection(ZCONN[conn]); z.SetThermalReliefGap(MM(0.2)); z.SetThermalReliefSpokeWidth(MM(0.3))
    z.SetIsFilled(False)
    if name: z.SetZoneName(name)
    b.Add(z); return z
def zones_on(lay, netname=None):
    return [z for z in b.Zones() if z.GetLayer()==L[lay] and (netname is None or z.GetNetname()==netname)]
def rect(x0,y0,x1,y1): return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
NEW_VIAS=[]
def _copper_items():
    out=[]
    for t in b.GetTracks():
        if _dead(t): continue
        out.append(t)
    return out
def via_free(x, y, netname, clr=0.12, others=None):
    """True when a 0.45/0.2 through via of netname at (x, y) keeps clr from all copper of other nets on every layer,
    from holes, and 0.25 mm from the board edge and the window."""
    pos=pcbnew.VECTOR2I(MM(x),MM(y)); r=MM(0.225); c=MM(clr)
    nc=net(netname).GetNetCode()
    seg=pcbnew.SEG(pos,pos)
    for t in (others if others is not None else _copper_items()):
        if t.Type()==pcbnew.PCB_VIA_T:      # any via, same net included: holes stay apart (R25)
            if (t.GetPosition()-pos).EuclideanNorm() < r+t.GetWidth()//2+(c if t.GetNetCode()!=nc else 0): return False
            continue
        if t.GetNetCode()==nc: continue
        else:
            if t.GetEffectiveShape().Collide(seg, r+c): return False
    for f in b.GetFootprints():
        if _dead(f): continue
        fx,fy=mm(f.GetPosition().x),mm(f.GetPosition().y)
        if abs(fx-x)>8 or abs(fy-y)>8: continue
        for p in f.Pads():
            same=p.GetNetCode()==nc and nc!=0
            if p.GetDrillSizeX()>0:      # holes: keep 0.25 mm whatever the net
                if p.GetEffectiveHoleShape().Collide(seg, r+MM(0.25)): return False
            if same: continue
            if p.GetEffectiveShape().Collide(seg, r+c): return False
    for v in NEW_VIAS:
        if (v-pos).EuclideanNorm() < MM(0.45+0.15): return False
    ec=b.GetBoardEdgesBoundingBox()
    # edge clearance: test against Edge.Cuts segments
    for d in b.GetDrawings():
        if d.GetLayer()==b.GetLayerID('Edge.Cuts') and d.GetEffectiveShape().Collide(seg, r+MM(0.25)): return False
    return True
def add_vias_near(netname, cx, cy, n, rmax=1.6, step=0.1, clr=0.12, avoid_box=None):
    """Place up to n vias of netname nearest to (cx, cy) on free spots (spiral search). Returns the positions."""
    import itertools
    others=_copper_items()
    cands=[]
    k=int(rmax/step)
    for i in range(-k,k+1):
        for j in range(-k,k+1):
            x=round(cx+i*step,3); y=round(cy+j*step,3); d=math.hypot(x-cx,y-cy)
            if d<=rmax: cands.append((d,x,y))
    cands.sort()
    got=[]
    for d,x,y in cands:
        if len(got)>=n: break
        if avoid_box and avoid_box[0]<=x<=avoid_box[2] and avoid_box[1]<=y<=avoid_box[3]: continue
        if via_free(x,y,netname,clr,others):
            add_via(x,y,net(netname)); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x),MM(y))); got.append((x,y))
    return got
def seg_free(lay, a, c, w, nc, clr=0.12, others=None):
    """True when a track of width w (mm) from a to c (mm) on lay keeps clr from copper of other nets on that layer."""
    A=pcbnew.VECTOR2I(MM(a[0]),MM(a[1])); C=pcbnew.VECTOR2I(MM(c[0]),MM(c[1])); sg=pcbnew.SEG(A,C); r=MM(w/2+clr)
    lid=L[lay]
    for t in (others if others is not None else _copper_items()):
        if t.GetNetCode()==nc: continue
        if t.Type()==pcbnew.PCB_VIA_T:
            if sg.Distance(t.GetPosition()) < r+t.GetWidth()//2: return False
        elif t.GetLayer()==lid and t.GetEffectiveShape().Collide(sg, r): return False
    for f in b.GetFootprints():
        if _dead(f): continue
        for p in f.Pads():
            if (p.GetNetCode()==nc and nc!=0) or not p.IsOnLayer(lid): continue
            if p.GetEffectiveShape().Collide(sg, r): return False
            if p.GetDrillSizeX()>0 and p.GetEffectiveHoleShape().Collide(sg, MM(w/2+0.25)): return False
    for d in b.GetDrawings():
        if d.GetLayer()==b.GetLayerID('Edge.Cuts') and d.GetEffectiveShape().Collide(sg, MM(w/2+0.25)): return False
    return True
def _fine_pad_at(pt, nc, lid):
    """The smallest dimension (mm) of a pad of net nc on layer lid under point pt, or None."""
    for f in b.GetFootprints():
        if _dead(f): continue
        for p in f.Pads():
            if p.GetNetCode()==nc and p.IsOnLayer(lid) and p.HitTest(pt): return min(mm(p.GetSize().x),mm(p.GetSize().y))
    return None
def split_at_fine_pads(nets, neck=0.6, fine=0.4):
    """Split each track of nets that ends on a pad narrower than fine mm, neck mm from that pad, so widen() can leave
    the short end at its width (fine-pitch pins) and widen the rest."""
    for t in list(b.GetTracks()):
        if _dead(t) or t.Type()==pcbnew.PCB_VIA_T or t.GetNetname() not in nets: continue
        for end in ('start','end'):
            pt=t.GetStart() if end=='start' else t.GetEnd(); other=t.GetEnd() if end=='start' else t.GetStart()
            d=_fine_pad_at(pt, t.GetNetCode(), t.GetLayer())
            L_=(other-pt).EuclideanNorm()
            if d is None or d>=fine or L_<=MM(neck+0.2): continue
            k=MM(neck)/L_; mid=pcbnew.VECTOR2I(int(pt.x+(other.x-pt.x)*k), int(pt.y+(other.y-pt.y)*k))
            n2=pcbnew.PCB_TRACK(b); n2.SetStart(mid); n2.SetEnd(other); n2.SetWidth(t.GetWidth()); n2.SetLayer(t.GetLayer()); n2.SetNet(t.GetNet()); b.Add(n2)
            if end=='start': t.SetEnd(mid)
            else: t.SetStart(mid)
            NECKS.add(t.m_Uuid.AsString())
            break
NECKS=set()
def widen(nets, widths=(0.8,0.6,0.5,0.4,0.3,0.25,0.2), layers=('F.Cu','B.Cu','In3.Cu'), clr=0.12, box=None):
    """Give each track of nets the widest of widths that keeps clr from other nets' copper (tracks, vias, pads).
    Tracks split off by split_at_fine_pads() (the necks into fine-pitch pins) keep their width."""
    split_at_fine_pads(nets)
    others=_copper_items(); n=0
    for t in list(b.GetTracks()):
        if _dead(t) or t.Type()==pcbnew.PCB_VIA_T or t.GetNetname() not in nets: continue
        lay=b.GetLayerName(t.GetLayer())
        if lay not in layers: continue
        if box and not track_in_box(t, box): continue
        if t.m_Uuid.AsString() in NECKS: continue
        if any(z.GetLayer()==t.GetLayer() and z.GetNetCode()!=t.GetNetCode() and z.GetBoundingBox().Inflate(MM(0.6)).Intersects(t.GetBoundingBox())
               for z in b.Zones()): continue        # next to another net's copper area: leave as routed
        a=(mm(t.GetStart().x),mm(t.GetStart().y)); c=(mm(t.GetEnd().x),mm(t.GetEnd().y))
        for w in widths:
            if w<=mm(t.GetWidth())+1e-6: break
            if seg_free(lay,a,c,w,t.GetNetCode(),clr,others):
                t.SetWidth(MM(w)); n+=1; break
    return n
def via_with_stub(netname, pad_ref, pad_num, n=1, w=0.4, rmin=0.5, rmax=1.6, lay='B.Cu', clr=0.12):
    """Add up to n vias near a pad, each joined to the pad centre by a track of width w that is clear of other copper."""
    p=pad(pad_ref,pad_num); px,py=mm(p.GetPosition().x),mm(p.GetPosition().y); nc=p.GetNetCode()
    others=_copper_items(); got=[]
    cands=sorted({(round(math.hypot(i*0.1,j*0.1),3),round(px+i*0.1,3),round(py+j*0.1,3)) for i in range(-16,17) for j in range(-16,17)
                  if rmin<=math.hypot(i*0.1,j*0.1)<=rmax})
    for d,x,y in cands:
        if len(got)>=n: break
        if not via_free(x,y,netname,clr,others): continue
        if not seg_free(lay,(px,py),(x,y),w,nc,clr,others): continue
        add_via(x,y,net(netname)); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x),MM(y)))
        add(lay,[(px,py),(x,y)],net(netname),w); got.append((x,y)); others=_copper_items()
    return got

# ---- R25: meanders for length/flight-time matching ------------------------------------------------------------
def _obstacles(lid, nc):
    """Copper of other nets on layer lid (tracks, vias, pads) and other-net copper areas on that layer."""
    obs=[]
    for t in b.GetTracks():
        if _dead(t) or t.GetNetCode()==nc: continue
        if t.Type()==pcbnew.PCB_VIA_T or t.GetLayer()==lid: obs.append(t)
    for f in b.GetFootprints():
        if _dead(f): continue
        for p in f.Pads():
            if p.GetNetCode()!=nc and p.IsOnLayer(lid): obs.append(p)
    zs=[z for z in b.Zones() if z.GetLayer()==lid and z.GetNetCode()!=nc]
    return obs, zs
def _poly_free(pts, w, lid, nc, clr, obs, zs):
    r=MM(w/2+clr)
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        sg=pcbnew.SEG(pcbnew.VECTOR2I(MM(x1),MM(y1)),pcbnew.VECTOR2I(MM(x2),MM(y2)))
        for o in obs:
            if o.GetEffectiveShape(lid).Collide(sg, r): return False
        for z in zs:
            if z.Outline().Collide(sg, r): return False
        for d in b.GetDrawings():
            if d.GetLayer()==b.GetLayerID('Edge.Cuts') and d.GetEffectiveShape().Collide(sg, MM(w/2+0.25)): return False
    return True
def meander_once(net_name, lid, dl, clr=0.12, pitch=0.45, amps=(1.0,0.8,0.6,0.45,0.3), end=0.35, dry=False):
    """Insert one trombone meander adding up to dl mm into the longest-fitting straight segment of net on layer lid.
    Returns the length added (0 if nothing fits)."""
    nc=net(net_name).GetNetCode(); obs,zs=_obstacles(lid,nc)
    segs=[t for t in b.GetTracks() if not _dead(t) and t.Type()!=pcbnew.PCB_VIA_T and t.GetNetCode()==nc and t.GetLayer()==lid]
    segs.sort(key=lambda t:-t.GetLength())
    for t in segs:
        a=(mm(t.GetStart().x),mm(t.GetStart().y)); c=(mm(t.GetEnd().x),mm(t.GetEnd().y)); L=math.dist(a,c); w=mm(t.GetWidth())
        if L<2*end+2*pitch: continue
        u=((c[0]-a[0])/L,(c[1]-a[1])/L)
        for A in amps:
            nbmax=int((L-2*end)/(2*pitch))
            nb=min(nbmax, max(1, math.ceil(dl/(2*A))))
            if nb<1: continue
            gain=min(dl, 2*A*nb); Ause=gain/(2*nb)
            if Ause<0.08: continue
            span=2*pitch*nb
            for side in (1,-1):
                nrm=(-u[1]*side,u[0]*side)
                k=0
                while end+k*0.15+span<=L-end+1e-9:
                    off=end+k*0.15; k+=1
                    p=(a[0]+u[0]*off,a[1]+u[1]*off); q=[a,p]
                    for _ in range(nb):
                        p1=(p[0]+nrm[0]*Ause,p[1]+nrm[1]*Ause); p2=(p1[0]+u[0]*pitch,p1[1]+u[1]*pitch)
                        p3=(p2[0]-nrm[0]*Ause,p2[1]-nrm[1]*Ause); p4=(p3[0]+u[0]*pitch,p3[1]+u[1]*pitch)
                        q+=[p1,p2,p3,p4]; p=p4
                    q.append(c)
                    if not _poly_free(q[1:-1], w, lid, nc, clr, obs, zs): continue
                    if not dry:
                        KILL.append(t); add(b.GetLayerName(lid), q, net(net_name), w)
                    return 2*Ause*nb
    return 0.0
def meander(net_name, layer, dl, **kw):
    """Add dl mm to net on layer with as many meanders as needed; returns the length actually added."""
    lid=L[layer]; got=0.0; tries=0
    while dl-got>0.02 and tries<40:
        tries+=1
        g=meander_once(net_name, lid, dl-got, **kw)
        if g<=0: break
        got+=g
    return got

# ---- R25: plane vias along supply branches ----------------------------------------------------------------------
def vias_along(netname, box, lay='B.Cu', gap=1.2, clr=0.12, ok=None):
    """Put through vias of netname on its own tracks on lay inside box (x0,y0,x1,y1), so long branches reach the plane
    sooner: points every 0.05 mm along the tracks, the one farthest from any same-net via first, while that distance
    exceeds gap and the via clears other copper by clr; ok(x, y), when given, must accept the point (e.g. inside the
    net's own plane region). Returns the positions added."""
    lid=L[lay]; nc=net(netname).GetNetCode(); got=[]
    pts=[]
    for t in b.GetTracks():
        if _dead(t) or t.Type()==pcbnew.PCB_VIA_T or t.GetNetCode()!=nc or t.GetLayer()!=lid: continue
        a=(mm(t.GetStart().x),mm(t.GetStart().y)); c=(mm(t.GetEnd().x),mm(t.GetEnd().y)); n=max(1,int(math.dist(a,c)/0.05))
        for i in range(n+1):
            x=round(a[0]+(c[0]-a[0])*i/n,3); y=round(a[1]+(c[1]-a[1])*i/n,3)
            if box[0]<=x<=box[2] and box[1]<=y<=box[3] and (ok is None or ok(x,y)): pts.append((x,y))
    while True:
        vs=[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in b.GetTracks() if not _dead(t) and t.Type()==pcbnew.PCB_VIA_T and t.GetNetCode()==nc]
        cand=sorted(((min(math.dist(p,v) for v in vs),p) for p in pts), reverse=True)
        others=_copper_items(); placed=False
        for d,p in cand:
            if d<=gap: break
            if via_free(p[0],p[1],netname,clr,others):
                add_via(p[0],p[1],net(netname)); NEW_VIAS.append(pcbnew.VECTOR2I(MM(p[0]),MM(p[1]))); got.append(p); placed=True; break
        if not placed: return got

def rect_poly(rects):
    """Union of axis-aligned rectangles (x0, y0, x1, y1) in mm as a SHAPE_POLY_SET."""
    out=pcbnew.SHAPE_POLY_SET()
    for x0,y0,x1,y1 in rects:
        r=pcbnew.SHAPE_POLY_SET(); r.NewOutline()
        for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)): r.Append(MM(x),MM(y))
        out.BooleanAdd(r, pcbnew.SHAPE_POLY_SET.PM_STRICTLY_SIMPLE)
    out.Simplify(pcbnew.SHAPE_POLY_SET.PM_STRICTLY_SIMPLE)
    return out
def poly_dist(sp, x, y):
    """Signed distance in mm from (x, y) to the outline of sp: negative inside."""
    pt=pcbnew.VECTOR2I(MM(x),MM(y)); d=mm(sp.SquaredDistance(pt)**0.5) if False else None
    dmin=min(mm(sp.COutline(i).SquaredDistance(pt, True)**0.5) for i in range(sp.OutlineCount()))
    return -dmin if sp.Contains(pt) else dmin
