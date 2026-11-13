# R24 edit 18: the charger U10 (BQ24074).
#  - R414 (TMR 47 k) removed: TMR left open selects the datasheet's default safety timers (pre-charge 30 min,
#    fast charge 5 h), enough for a 1000 mAh cell at 0.49 A; its route ran under the exposed pad.
#  - Four thermal vias in the exposed pad (up to about 1.3 W at 5 V in, a deep-discharged cell and the system
#    load), GND vias at the output and battery capacitors C411/C412, and USB_VBUS tracks widened as far as their
#    neighbours allow, with a 0.6 mm neck at the 0.24 mm charger pin.
#  The output and battery pins keep one via each into their planes (about 1.6 mOhm: 3 mV at a 2 A peak).
exec(open(sys.argv[2]).read())
kill_tracks(lambda t: t.GetNetname()=='BQ_TMR')
KILL.append(fpr('R414'))
ep=add_vias_near('GND',17.0,8.0,4,rmax=0.62,step=0.05,clr=0.1)
assert len(ep)==4, ep
got_g=via_with_stub('GND','C411','2',n=1,w=0.4,rmin=0.6,rmax=1.6)+via_with_stub('GND','C412','2',n=1,w=0.4,rmin=0.6,rmax=1.6)
nw=widen({'USB_VBUS'})
print('charger: EP vias',ep,'cap GND',got_g,'VBUS segments widened',nw)
