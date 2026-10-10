# R22 edit 8: battery port for any 2-wire cell.
#  J3 becomes the same JST SH 2-pin socket as the speakers (pin 1 BAT+, pin 2 GND). The charger's TS input
#  (BQ24074 pin 1) gets a fixed 10 k resistor to GND, R424, as the datasheet specifies when no thermistor is used;
#  the old NTC route is cut back to it. Cell protection stays on the cell's own PCM.
exec(open(sys.argv[2]).read())
import math
LIB='/usr/share/kicad/footprints/'
TS=b.FindNet('BAT_NTC'); TS.SetNetname('BQ_TS')
# cut the NTC route back: J3 pin 2 stub, its via, and the last part of the In3 run
remove("B.Cu",-24.0,64.0,-24.0,62.09,"BQ_TS"); remove_via(-24.0,62.09,"BQ_TS")
remove("In3.Cu",-24.0,21.115,-24.0,62.09,"BQ_TS")
L['In3.Cu']=b.GetLayerID('In3.Cu')
add("In3.Cu",[(-24.0,21.115),(-24.0,59.0)],TS); add_via(-24.0,59.0,TS)
# R424 10 k, TS to GND, beside J3 (back side)
r=pcbnew.FootprintLoad(LIB+'Resistor_SMD.pretty','R_0402_1005Metric'); b.Add(r)
r.SetPosition(pcbnew.VECTOR2I(MM(-22.5),MM(59.0))); r.Flip(r.GetPosition(),False); r.SetOrientationDegrees(0)
r.SetReference('R424'); r.SetValue('0402WGF1002TCE'); r.Reference().SetVisible(False); r.Value().SetVisible(False)
r.SetDescription('0402WGF1002TCE | JLC C25744 | KiCad 7 library Resistor_SMD:R_0402_1005Metric (R22: BQ24074 TS 10 k to GND)')
r.SetFPID(pcbnew.LIB_ID('SLIM4','FP_R424')); r.SetKeywords('SLIM4 R22 R 0402 1005Metric')
pp=sorted(r.Pads(),key=lambda p:p.GetPosition().x)        # left pad -> TS, right pad -> GND
pp[0].SetNet(TS); pp[1].SetNet(G)
xl=mm(pp[0].GetPosition().x); xr=mm(pp[1].GetPosition().x)
add("B.Cu",[(-24.0,59.0),(xl,59.0)],TS)
add("B.Cu",[(xr,59.0),(-21.2,59.0)],G); add_via(-21.2,59.0,G)
# J3: JST SH 2-pin, pin 1 at (-23, 64) like before, pin 2 at (-24, 64) to GND
old=b.FindFootprintByReference('J3')
j=pcbnew.FootprintLoad(LIB+'Connector_JST.pretty','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal'); b.Add(j)
j.SetPosition(pcbnew.VECTOR2I(MM(-23.5),MM(66.0))); j.Flip(j.GetPosition(),False); j.SetOrientationDegrees(180)
pads={p.GetNumber():(round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3)) for p in j.Pads() if p.GetNumber()!='MP'}
assert pads=={'1':(-23.0,64.0),'2':(-24.0,64.0)}, pads
BP=b.FindNet('BAT_PLUS')
for p in j.Pads():
    p.SetNet(BP if p.GetNumber()=='1' else G if p.GetNumber()=='2' else b.FindNet(''))
j.SetReference('J3'); j.SetValue('SM02B-SRSS-TB(LF)(SN)'); j.Reference().SetVisible(False); j.Value().SetVisible(False)
j.SetDescription('SM02B-SRSS-TB(LF)(SN) | JLC C160402 | KiCad 7 library Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal (R22 battery: pin 1 BAT+, pin 2 GND)')
j.SetFPID(pcbnew.LIB_ID('SLIM4','FP_J3')); j.SetAttributes(old.GetAttributes())
KILL.append(old)
# GND: tie the C603 GND run to pin 2 and take the long GND link from pin 2, clear of the new tab pads
remove("B.Cu",-25.0,64.0,-25.0,67.6,"GND"); remove("B.Cu",-25.0,67.6,-12.5,80.1,"GND")
add("B.Cu",[(-25.0,64.0),(-24.0,64.0)],G)
add("B.Cu",[(-24.0,64.0),(-24.0,69.4),(-13.3,80.1),(-12.5,80.1)],G)
