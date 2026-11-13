# R24 edit 16: In2 power planes re-planned so the battery and system rails each have a wide, unbroken path.
#  BAT_PLUS (battery <-> charger): the charger's east side, a strip along the top edge (north of U10 and of J2's
#  shell legs), the top-left band and the outer left arm down to Q2.
#  SYS_RAW (charger output -> regulators, backlight, amplifiers): the charger's west and south side, a band under
#  the charger and the whole right arm beside the battery window, joining the existing bottom-right block, bottom
#  band and left column. 3V3_SYS keeps the rest (the board-wide priority-0 pour); 1V1_HP is unchanged.
#  A notch in the battery block brings the system plane to C411's via (the charger's output capacitor).
#  R23 had the system rail in a 2.7 mm strip down the left arm and a 1 mm sliver across the top.
#  The new system plane is priority 1 (the R23 SYS_RAW areas it meets are 2, the 3V3 pour 0) so the fill does not
#  depend on the order of new and old areas; its edges keep 0.3 mm from the battery plane's outline (0.1 mm more
#  than the clearance), so neither fill clips the other.
exec(open(sys.argv[2]).read())
OLD=[z for z in zones_on('In2.Cu') if z.GetNetname()=='BAT_PLUS' or
     (z.GetNetname()=='SYS_RAW' and mm(z.GetBoundingBox().GetTop())<20)]
assert len(OLD)==5, [(z.GetNetname(),mm(z.GetBoundingBox().GetTop())) for z in OLD]
for z in OLD: b.Remove(z)
zone('In2.Cu', [(30.4,3.2),(30.4,10.8),(24.0,10.8),(24.0,8.8),(21.5,8.8),(21.5,10.8),(18.7,10.8),(18.7,6.0),(5.2,6.0),(5.2,4.45),(-5.2,4.45),(-5.2,10.5),
                (-22.2,10.5),(-22.2,60.0),(-30.4,60.0),(-30.4,3.2)], 'BAT_PLUS', prio=3, clearance=0.2, minw=0.2,
     conn='thermal', name='BAT_PLUS plane')
zone('In2.Cu', [(7.4,6.3),(15.2,6.3),(15.2,11.1),(21.8,11.1),(21.8,9.1),(23.7,9.1),(23.7,11.1),(30.4,11.1),(30.4,92.5),(19.25,92.5),(19.25,16.9),(7.4,16.9)],
     'SYS_RAW', prio=1, clearance=0.2, minw=0.2, conn='thermal', name='SYS_RAW plane, top and right arm')
