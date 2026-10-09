# R27 edit 37: 10 uF bulk capacitors at U1's core supply pins. R26 had 100 nF beside each of the four VDD_HP pins
# (pads 26, 54, 76, 91) and its only bulk capacitor (C135, 22 uF) at the regulator, 13-16 mm away (pre-order review
# P4CORE M2; Espressif's reference puts 10 uF at the chip). One 10 uF 0402 (Samsung CL05A106MQ5NUNC, 6.3 V X5R, JLC
# C15525) goes on the back beside the north pins (C138) and one beside the south pins (C139), placed by search
# (place_joined in r27_lib.py): within 4.5 mm of a core pin, courtyard clear, pads joined by short 0.3 mm tracks to
# 1V1_HP and GND copper, or by a new via (for 1V1_HP only into the In2 1V1_HP plane).
exec(open(sys.argv[2]).read())
# A 1V1 via must land in the In2 plane's filled copper (other zones take priority over parts of its outline), so the
# zones are filled first and the via's spot needs filled 1V1_HP all round it (0.45 mm radius).
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
FILL=pcbnew.SHAPE_POLY_SET()
for z in b.Zones():
    if z.GetNetname()=='1V1_HP' and z.IsOnLayer(L['In2.Cu']):
        FILL.BooleanAdd(z.GetFilledPolysList(L['In2.Cu']), pcbnew.SHAPE_POLY_SET.PM_FAST)
def in_1v1_plane(x,y):
    pts=[(x,y)]+[(x+0.45*math.cos(a*math.pi/4), y+0.45*math.sin(a*math.pi/4)) for a in range(8)]
    return all(FILL.Contains(pcbnew.VECTOR2I(MM(px),MM(py)), -1, 0) for px,py in pts)
UNDER_U1=(-5.6, 78.4, 5.6, 89.6)
out=[]
for ref, pins in (('C138', ('76','91')), ('C139', ('26','54'))):
    f,txt=place_joined(ref,'Capacitor_SMD','C_0402_1005Metric','CL05A106MQ5NUNC','C15525',
                       'R27: 10 uF bulk at the U1 core pins (KiCad 7 library Capacitor_SMD:C_0402_1005Metric)',
                       [padxy('U1',p) for p in pins], 4.5,
                       {'1':('1V1_HP', copper_points('1V1_HP', exclude=('U1',)), 2.5, in_1v1_plane),
                        '2':('GND', copper_points('GND', exclude=('U1',)), 2.0, None)}, keepout=UNDER_U1)
    out.append(txt)
print('core bulk: '+'; '.join(out))
