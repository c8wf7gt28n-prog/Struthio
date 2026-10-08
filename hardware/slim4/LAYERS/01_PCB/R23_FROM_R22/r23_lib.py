# Helpers for the R22 -> R23 edits (executed inside run_edit.py with the board in `b`).
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
