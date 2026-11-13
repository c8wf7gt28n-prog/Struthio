# R22 edit 1: USB-C data -> ESP32-P4 USB-Serial-JTAG (GPIO24 = D-, GPIO25 = D+)
import pcbnew, sys
P=sys.argv[1]
b=pcbnew.LoadBoard(P)
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

DM=b.FindNet("USB_HS_DM"); DP=b.FindNet("USB_HS_DP")
# rename the J2->U1 pair: it now serves the USB-Serial-JTAG PHY
DM.SetNetname("USB_JTAG_DM"); DP.SetNetname("USB_JTAG_DP")
# pads: HS PHY pins 49/50 become unused; GPIO24/25 take the pair
nc=b.FindNet(""); 
for n in ("49","50"): pad("U1",n).SetNet(nc)
pad("U1","52").SetNet(DM); pad("U1","53").SetNet(DP)
for old in ("USB_RECOVERY_GPIO24","USB_RECOVERY_GPIO25"):
    pass

# D-: inside the pad ring, from the existing via at (-1.474, 88.171) to pad 52
remove("B.Cu",-3.325,88.481,-3.015,88.171,"USB_JTAG_DM")
remove("B.Cu",-3.325,88.875,-3.325,88.481,"USB_JTAG_DM")
add("B.Cu",[(-3.015,88.171),(-4.075,88.171)],DM)
add("B.Cu",[(-4.075,88.171),(-4.375,88.471),(-4.375,88.875)],DM,0.1)

# D+: the existing outside via (-3.427, 89.528) hops on In1 to a new via left of pad 52, then B.Cu up into pad 53
remove("B.Cu",-3.675,88.875,-3.675,89.28,"USB_JTAG_DP")
remove("B.Cu",-3.675,89.28,-3.427,89.528,"USB_JTAG_DP")
VP=(-4.95,89.55)
add("In1.Cu",[(-3.427,89.528),VP],DP)
add_via(*VP,DP)
add("B.Cu",[VP,(-4.875,89.475),(-4.875,88.375)],DP)

# make room for the new via on In3: drop the redundant In3 GND tie (both ends are GND vias on the In1/In4 planes)
remove("In3.Cu",-8.977,84.5,-2.0795,84.5,"GND")
remove("In3.Cu",-2.0795,84.5,-1.291,85.2885,"GND")
remove("In3.Cu",-1.291,85.2885,-1.291,85.597,"GND")
remove("In3.Cu",-1.291,85.597,-5.539,89.845,"GND")

# ...and on F.Cu: jog FB_DCDC right of the via, CHIP_PU left of the GND via
remove("F.Cu",-4.684,90.554,-4.684,80.365,"FB_DCDC")
remove("F.Cu",-5.383,91.252,-4.684,90.554,"FB_DCDC")
FB=b.FindNet("FB_DCDC")
add("F.Cu",[(-4.684,80.365),(-4.684,88.9),(-4.45,89.134),(-4.45,90.319),(-5.383,91.252)],FB)
remove("F.Cu",-4.987,89.906,-4.987,81.789,"CHIP_PU")
remove("F.Cu",-6.021,90.94,-4.987,89.906,"CHIP_PU")
PU=b.FindNet("CHIP_PU")
add("F.Cu",[(-4.987,81.789),(-4.987,88.6),(-5.95,89.563),(-5.95,90.869),(-6.021,90.94)],PU)
for t in KILL: b.Remove(t)
b.Save(P)
print("ok")
