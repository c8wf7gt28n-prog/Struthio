# R22 edit 4: U11 (USB D+/D-) and U12 (CC1/CC2) TPD2EUSB30 on the DRT (1 x 1 mm) land pattern, local routes redrawn
exec(open(sys.argv[2]).read())
def place(ref,cx,cy,want):
    f=b.FindFootprintByReference(ref)
    for rot in (0,90,180,270):
        f.SetOrientationDegrees(rot); f.SetPosition(pcbnew.VECTOR2I(MM(cx),MM(cy)))
        q={p.GetNumber():(round(mm(p.GetPosition().x)-cx,3),round(mm(p.GetPosition().y)-cy,3)) for p in f.Pads()}
        if all(abs(q[n][0]-w[0])<0.01 and abs(q[n][1]-w[1])<0.01 for n,w in want.items()): return rot
    raise SystemExit(f'{ref}: no orientation gives {want}')
DPC=b.FindNet('USB_DP_CONN'); DMC=b.FindNet('USB_DM_CONN'); CC1=b.FindNet('USB_CC1'); CC2=b.FindNet('USB_CC2')
# U11: pad 1 (D+) right, pad 2 (D-) left, pad 3 (GND) above, next to the existing GND via at (4.724, 11.12)
place('U11',4.6,12.2,{'1':(0.35,0.425),'2':(-0.35,0.425),'3':(0.0,-0.425)})
for seg in [(5.484,13.496,3.746,13.496),(3.746,13.496,3.05,12.8)]: remove("B.Cu",*seg,"USB_DP_CONN")
for seg in [(3.643,11.272,3.532,11.272),(3.532,11.272,2.504,12.3),(2.504,12.3,2.504,13.238),(2.504,13.238,3.016,13.75),
            (3.016,13.75,4.25,13.75),(3.643,11.493,4.95,12.8),(3.643,11.272,3.643,11.493)]: remove("B.Cu",*seg,"USB_DM_CONN")
for seg in [(2.441,14.8,4.0,14.8),(2.187,14.546,2.441,14.8)]: remove("B.Cu",*seg,"GND")
add("B.Cu",[(5.484,12.625),(4.95,12.625)],DPC)
add("B.Cu",[(3.643,11.272),(3.643,12.018),(4.25,12.625),(4.25,13.75)],DMC)
add("B.Cu",[(4.6,11.775),(4.724,11.12)],G)
# U12: pad 1 (CC1) top-right, pad 2 (CC2) bottom-right, pad 3 (GND) left to a new GND via
place('U12',-4.0,14.0,{'1':(0.425,-0.35),'2':(0.425,0.35),'3':(-0.425,0.0)})
for seg in [(-6.126,13.651,-3.699,13.651),(-3.699,13.651,-3.05,14.3),(-2.486,14.3,-3.05,14.3),(-1.0,12.814,-2.486,14.3)]: remove("B.Cu",*seg,"USB_CC1")
remove("B.Cu",-4.95,15.0,-4.95,14.3,"USB_CC2")
for seg in [(-4.049,11.34,-4.049,12.251),(-4.049,12.251,-4.0,12.3)]: remove("B.Cu",*seg,"GND")
add("B.Cu",[(-6.126,13.651),(-1.837,13.651),(-1.0,12.814)],CC1)
add("B.Cu",[(-3.575,15.0),(-3.575,14.35)],CC2)
add("B.Cu",[(-4.425,14.0),(-4.875,14.45),(-5.0,14.45)],G); add_via(-5.0,14.45,G)
