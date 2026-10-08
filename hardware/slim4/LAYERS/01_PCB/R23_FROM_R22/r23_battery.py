# R23 edit 12: plug-and-play battery port with reverse-polarity protection.
#  J3 becomes a JST PH 2.0 mm right-angle socket (S2B-PH-SM4-TB, LCSC C295747), the plug used by Adafruit/SparkFun-style
#  1-cell packs: pin 1 BAT+, pin 2 GND. It sits at the board edge left of the battery window, opening toward the window.
#  Q2 AO3401A (P-MOSFET, LCSC C15127, JLC Basic) sits between the socket and BAT_PLUS: drain to the socket (new net
#  BAT_CONN), source to BAT_PLUS (tied into the In2 BAT_PLUS pour with vias), gate to GND. A pack plugged in reversed
#  leaves Q2 off; a correct pack turns it on through its body diode, and the on channel then carries charge current too.
exec(open(sys.argv[2]).read())
BP=net('BAT_PLUS'); BC=net('BAT_CONN',create=True)
OLD=b.FindFootprintByReference('J3')
remove("B.Cu",-23.0,64.0,-23.0,62.5,"BAT_PLUS"); remove("B.Cu",-23.0,62.5,-28.0,57.5,"BAT_PLUS")
KILL.append(OLD)
# the old pin-2 ground run (C603 -> J3 -> long link toward U1) goes; C603 and R419 get their own via
for a in [(-26.5,62.5,-25.0,64.0),(-25.0,64.0,-24.0,64.0),(-24.0,64.0,-24.0,69.4),(-24.0,69.4,-13.3,80.1),(-13.3,80.1,-12.5,80.1)]:
    remove("B.Cu",*a,"GND")
# keep C603 / R419 ground: a via at the end of their run (before pruning, so the run is kept)
add_via(-26.5,62.5,G)
prune({'GND'},(-31.0,60.0,-12.0,81.0))
# J3: JST PH, mouth toward the window (+x)
j=place('Connector_JST','JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal','J3','S2B-PH-SM4-TB(LF)(SN)','C295747',
        'R23 battery: JST PH 2.0, pin 1 BAT+ (to Q2 drain), pin 2 GND',-24.8,67.9,270)
j.SetAttributes(OLD.GetAttributes())
p1=padxy('J3','1'); p2=padxy('J3','2')
assert abs(p1[0]+27.65)<1e-3 and abs(p1[1]-66.9)<1e-3 and abs(p2[1]-68.9)<1e-3, (p1,p2)
for p in j.Pads(): p.SetNet(BC if p.GetNumber()=='1' else G if p.GetNumber()=='2' else b.FindNet(''))
# Q2: AO3401A, S up (BAT_PLUS), G down (GND), D right (BAT_CONN)
q=place('Package_TO_SOT_SMD','SOT-23','Q2','AO3401A','C15127','R23 battery reverse-polarity P-MOSFET: 1 G, 2 S, 3 D',-21.4,56.0,0)
q.SetAttributes(OLD.GetAttributes())
g=padxy('Q2','1'); s=padxy('Q2','2'); d=padxy('Q2','3')
assert abs(s[1]-55.05)<1e-3 and abs(g[1]-56.95)<1e-3 and abs(d[0]+20.462)<1e-3, (g,s,d)
for p in q.Pads(): p.SetNet({'1':G,'2':BP,'3':BC}[p.GetNumber()])
# source to BAT_PLUS: wide link to the BAT_PLUS corner and two vias into the In2 BAT_PLUS pour
add("B.Cu",[s,(s[0]-0.9,s[1]),(-23.448,52.948)],BP,0.5); add_via(-23.3,54.3,BP); add_via(-22.9,53.6,BP)
add("B.Cu",[(-22.9,53.6),(-23.3,54.3)],BP,0.5)
# drain to J3 pin 1 (0.5 mm), under the socket body between its signal and tab pads
add("B.Cu",[d,(d[0],62.0),(-24.75,62.0),(-24.75,p1[1]),p1],BC,0.5)
# gate to the R424 ground pad
add("B.Cu",[g,(g[0],58.3),(-21.99,58.65),(-21.99,59.0)],G)
# J3 pin 2 to ground: two vias
add("B.Cu",[p2,(-25.0,p2[1]),(-24.6,69.65)],G,0.4); add_via(-25.0,p2[1],G); add_via(-24.6,69.65,G)
