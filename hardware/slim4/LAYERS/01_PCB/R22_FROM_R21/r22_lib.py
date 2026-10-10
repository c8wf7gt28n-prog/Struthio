# R22 edit 1: USB-C data -> ESP32-P4 USB-Serial-JTAG (GPIO24 = D-, GPIO25 = D+)
import pcbnew, sys
MM=pcbnew.FromMM; mm=pcbnew.ToMM
TR=list(b.GetTracks()); KILL=[]
L={n:b.GetLayerID(n) for n in ("F.Cu","In1.Cu","In3.Cu","B.Cu")}
def near(a,x,y,t=0.003): return abs(mm(a.x)-x)<t and abs(mm(a.y)-y)<t
def seg_match(t,lay,x1,y1,x2,y2):
    if t.GetClass()!="PCB_TRACK" or t.GetLayer()!=L[lay]: return False
    s,e=t.GetStart(),t.GetEnd()
    return (near(s,x1,y1) and near(e,x2,y2)) or (near(s,x2,y2) and near(e,x1,y1))
def remove(lay,x1,y1,x2,y2,net):
    hit=[t for t in TR if t not in KILL and t.GetNetname()==net and seg_match(t,lay,x1,y1,x2,y2)]
    assert len(hit)==1,(lay,x1,y1,x2,y2,net,len(hit)); KILL.append(hit[0])
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

G=b.FindNet('GND')
