# R23 edit 13: plug-and-play speaker ports. J4 (left) and J5 (right) become Molex PicoBlade 1.25 mm right-angle
#  sockets (53261-0271, LCSC C177225), the plug small speakers ship with (Adafruit 3923 / 4227, Waveshare 8 ohm 2 W):
#  pin 1 = +, pin 2 = -. J4 opens toward the bottom edge as before; J5 keeps its orientation.
exec(open(sys.argv[2]).read())
for ref,(x,y,rot),pn,nn,old_routes,new_routes in [
    ('J4',(-44.0,113.7,180),'SPK_L_P','SPK_L_N',
        [("B.Cu",-42.878,113.854,-42.878,111.922,'SPK_L_P'),("B.Cu",-42.878,111.922,-43.5,111.3,'SPK_L_P'),
         ("B.Cu",-44.5,112.897,-44.5,111.3,'SPK_L_N')],
        [('SPK_L_P',[(-42.878,113.854),(-42.878,112.6),(-43.375,112.1)]),('SPK_L_N',[(-44.5,112.897),(-44.625,112.772),(-44.625,112.1)])]),
    ('J5',(44.3,111.6,0),'SPK_R_P','SPK_R_N',
        [("B.Cu",43.431,114.069,43.5,114.0,'SPK_R_P'),("B.Cu",42.866,114.069,43.431,114.069,'SPK_R_P'),
         ("B.Cu",44.5,115.088,44.5,114.0,'SPK_R_N')],
        [('SPK_R_P',[(42.866,114.069),(43.675,114.069)]),('SPK_R_N',[(44.5,115.088),(44.925,114.663),(44.925,114.0)])])]:
    OLD=b.FindFootprintByReference(ref)
    for r in old_routes: remove(*r)
    j=place('Connector_Molex','Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal',ref,'53261-0271','C177225',
            f'R23 speaker {"left" if ref=="J4" else "right"}: Molex PicoBlade 1.25, pin 1 +, pin 2 -',x,y,rot,old=OLD)
    for p in j.Pads(): p.SetNet(net(pn) if p.GetNumber()=='1' else net(nn) if p.GetNumber()=='2' else b.FindNet(''))
    print(ref, padxy(ref,'1'), padxy(ref,'2'))
    for n,pts in new_routes: add("B.Cu",pts,net(n))
