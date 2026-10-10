# R26 edit 31: clear the way for the DSI reroute (audit SLIM4_R30/R25 pre-order: route each DSI pair as a coupled pair
# with the same layer sequence and vias for P and N).
#  - R25's DSI copper (meandered single lines, its vias) and the In2 ground band under it are removed; edits 32-33 route
#    the three pairs again and redraw the band under their new In3 sections.
#  - The In3 1V1_HP run from U1's pin-26 via to the feedback divider is removed: since R25 every via on it lands in the
#    In2 1V1_HP area, which carries the rail; the run crossed the DSI escape under U1.
#  - USB_CURR_OUT2 (TUSB320 OUT2, a static level): the part of its 300-segment autorouted path between U1's escape
#    via and the corner at (-8.4, 75.3), which wound through the DSI escape and the area CLK now uses, is lifted;
#    edit 34 routes that part again. Its run on to the west edge and the TUSB320 stays. BTN_LEFT's F.Cu run under U1 goes too (edit 34 reroutes it between its vias).
#  - CHG_STATUS's F.Cu diagonal (11.75, 81.7) -> (16.25, 77.2) moves to In3 (same line, via at its south end; the
#    via at its north end becomes an In3 corner and goes): it walled off J1's south side from the east column.
#  - The backlight pair (LCD_LED_A/K) jogs 1.1 mm east into the old DSI column between J1 and Y 88-89.5, with its widths
#    and LED_A's 0.2 mm clearance kept: beside the flash vias it left one pair's width where D0 and D1 both climb.
#  - PGOOD_STATUS's and PWR_WAKE's short hops south of J1 (F.Cu jogs, their vias and the first In3 run east) are lifted:
#    they sat where CLK enters J1. Edit 34 reconnects them between the anchors left in place.
#  - The bare ground stitching via at (1.59, 91.25) on the B.Cu strap under the DSI pads goes (D1's In3 lane).
#  - The ground planes on In1 and In4 clear other nets by 0.15 mm (the Default netclass clearance) instead of 0.2 mm,
#    so a via's antipad is 0.375 mm in radius; the DSI pairs keep 0.17 mm from via pads (dsi_pair_router.VIA_GROW) and
#    so never run over a hole in their reference planes.
#  - EN_DCDC (U1 GPIO -> U3 EN, a static level) leaves the F.Cu column at X -0.69 that split the free F.Cu over U1's
#    west half in two: from its via at (-4.37, 78.47) it now runs down X -3.75/-3.6 between FB_DCDC and the USB_JTAG vias
#    and joins its old run at Y 97.7 (24.3 mm instead of 22.1 mm). The CLK pair gets that area for its matching.
exec(open(sys.argv[2]).read())
dsi=lambda n: n.startswith('MIPI_DSI')
kill_tracks(lambda t: dsi(t.GetNetname()))
for z in [z for z in b.Zones() if z.GetZoneName()=='DSI_REF_IN2']: b.Remove(z)
L3=L['In3.Cu']
kill_tracks(lambda t: t.GetNetname()=='1V1_HP' and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L3)
def _uc2_lift(t):
    # USB_CURR_OUT2 between U1's escape via (4.125, 85.225) and the corner (-8.4, 75.3) of its run to the west edge
    if t.GetNetname()!='USB_CURR_OUT2': return False
    if t.Type()==pcbnew.PCB_VIA_T:
        x,y=mm(t.GetPosition().x),mm(t.GetPosition().y)
        return not (abs(x-4.125)<0.01 and abs(y-85.225)<0.01) and x>-8.45 and y>74.9
    ends=[(mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y))]
    if t.GetLayer()==L['B.Cu'] and all(4.0<=x<=4.95 and 85.1<=y<=85.65 for x,y in ends): return False   # pad 18 -> via
    return all(x>-8.45 and y>74.9 for x,y in ends)
kill_tracks(_uc2_lift)
kill_tracks(lambda t: t.GetNetname()=='BTN_LEFT' and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['F.Cu'] and mm(t.GetStart().x)>-5)  # not SW1's pad stub
remove_via(1.592,91.251,'GND')   # bare stitching via on the ground strap, in D1's In3 lane
remove('F.Cu',11.75,81.7,16.25,77.2,'CHG_STATUS')
remove_via(16.25,77.2,'CHG_STATUS')
add_via(11.75,81.7,net('CHG_STATUS'))
add('In3.Cu',[(11.75,81.7),(16.25,77.2)],net('CHG_STATUS'),0.1)
remove('F.Cu',16.55,75.95,16.85,76.25,'LCD_LED_A'); remove('F.Cu',16.85,76.25,16.85,90.0,'LCD_LED_A')
add('F.Cu',[(16.55,75.95),(17.65,75.95)],net('LCD_LED_A'),0.152)
add('F.Cu',[(17.65,75.95),(17.95,76.25),(17.95,88.0),(16.85,89.1),(16.85,90.0)],net('LCD_LED_A'),0.3)
remove('F.Cu',16.91,75.55,17.21,75.85,'LCD_LED_K'); remove('F.Cu',17.21,75.85,17.21,90.0,'LCD_LED_K')
add('F.Cu',[(16.91,75.55),(18.0,75.55)],net('LCD_LED_K'),0.25)
add('F.Cu',[(18.0,75.55),(18.31,75.86),(18.31,88.4),(17.21,89.5),(17.21,90.0)],net('LCD_LED_K'),0.152)
for seg in ((0.699,76.951,5.372,76.951),(5.372,76.951,6.172,76.151),(6.338,76.151,6.172,76.151)):
    remove('F.Cu',*seg,'PGOOD_STATUS')
remove_via(6.338,76.151,'PGOOD_STATUS')
for seg in ((6.338,76.151,9.537,76.151),(9.537,76.151,9.951,75.737),(10.151,75.537,9.951,75.737),(10.225,75.537,10.151,75.537)):
    remove('In3.Cu',*seg,'PGOOD_STATUS')
for seg in ((4.7,78.7,5.763,77.637),(5.763,77.637,5.763,77.155),(4.575,78.825,4.7,78.7)):
    remove('F.Cu',*seg,'PWR_WAKE')
remove_via(5.763,77.155,'PWR_WAKE')
for seg in ((5.763,77.155,5.763,76.089),(5.763,76.089,6.111,75.741),(6.111,75.741,8.603,75.741)):
    remove('In3.Cu',*seg,'PWR_WAKE')
remove('F.Cu',-0.694,82.149,-4.374,78.469,'EN_DCDC'); remove('F.Cu',-0.694,99.0,-0.694,82.149,'EN_DCDC')
add('F.Cu',[(-4.374,78.469),(-3.75,79.093),(-3.75,89.25),(-4.05,89.55),(-3.6,90.0),(-3.6,94.75),(-0.694,97.656),(-0.694,99.0)],net('EN_DCDC'),0.152)
for z in [z for z in b.Zones() if z.GetNetname()=='GND' and not z.GetIsRuleArea() and (z.IsOnLayer(L['In1.Cu']) or z.IsOnLayer(L['In4.Cu']))]:
    assert abs(mm(z.GetLocalClearance())-0.2)<1e-6; z.SetLocalClearance(MM(0.15))
print('clear: R25 DSI copper and band, In3 1V1 run, USB_CURR_OUT2 and BTN_LEFT F.Cu removed, EN_DCDC moved west')
