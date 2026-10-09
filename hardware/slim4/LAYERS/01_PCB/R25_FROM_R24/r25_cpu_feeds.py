# R25 edit 28: CPU supply feeds. In R24 the In2 1V1_HP area was a 19 x 28 mm rectangle over the whole of U1 and U3, so
# the 3V3_SYS vias inside it (two of U1's ring vias, U3's and R403's) landed on 0.15 mm2 3V3 islands and U1's nine 3V3
# pins reached the 3V3 plane only through 7.8-29.7 mm of 0.114-0.152 mm track. The 1V1_HP area is now shaped to what
# 1V1 needs: a block under U1's core, fingers to the 1V1 vias beside the package, a strip down the west side and along
# the south edge to L2's output vias, a leg to the feedback divider, and a stub up from L2 - leaving the band where the
# DSI pairs run on In3 free for the In2 ground reference added by edit 29. The 3V3 plane fills the rest. Plane vias are
# then added on U1's 3V3 and 1V1 branches (3V3 only outside the 1V1 area, 1V1 only inside it).
exec(open(sys.argv[2]).read())
LIN2=L['In2.Cu']
z1=[z for z in b.Zones() if z.GetNetname()=='1V1_HP' and z.IsOnLayer(LIN2)]; assert len(z1)==1; z1=z1[0]
RECTS=[(-4.6,79.0,4.6,89.0),        # under U1's core
       (3.0,87.15,7.2,89.0),        # pin-26 via (6.10, 87.58)
       (-7.9,86.45,-5.3,104.5),     # west strip, U1's left side down past the DSI band
       (-7.9,102.0,7.2,104.5),      # south strip to L2's output vias (5.5/6.4, 103.4)
       (3.0,98.0,7.2,104.5),        # stub up from L2
       (-4.6,98.0,-2.8,102.0),      # leg to the feedback divider vias (-3.36, 99.27), (-4.12, 100.52)
       (-6.25,79.95,-4.5,80.80),    # finger: pin-76 via (-5.96, 80.38)
       (-6.00,86.45,-4.5,89.00),    # pin-54 via (-5.64, 86.89): the 2.55 mm joint between the core and the west strip
       (-7.70,93.30,-5.3,94.15),    # finger: via (-7.31, 93.73)
       (-1.85,76.90,-0.75,79.1)]    # finger: pin 91's branch above the package
SP=rect_poly(RECTS)
z1.Outline().RemoveAllContours()
z1.Outline().Append(SP)
vs=lambda n:[(mm(t.GetPosition().x),mm(t.GetPosition().y)) for t in b.GetTracks() if t.Type()==pcbnew.PCB_VIA_T and t.GetNetname()==n]
for x,y in vs('1V1_HP'):
    if -10.5<x<9.5 and 75.5<y<104.5: assert poly_dist(SP,x,y)<-0.25, ('1V1 via outside its area',x,y)
for x,y in vs('3V3_SYS'):
    assert poly_dist(SP,x,y)>0.25, ('3V3 via inside the 1V1 area',x,y)
BOX=(-8.5,76.5,8.5,90.0)
g3=vias_along('3V3_SYS',BOX,ok=lambda x,y: poly_dist(SP,x,y)>0.3)
g1=vias_along('1V1_HP',BOX,ok=lambda x,y: poly_dist(SP,x,y)<-0.3)
print('cpu feeds: 1V1_HP In2 area reshaped; plane vias added 3V3_SYS %d %s, 1V1_HP %d %s'%(len(g3),g3,len(g1),g1))
print('cpu feeds: segments widened', widen({'3V3_SYS','1V1_HP'}, widths=(0.4,0.3,0.25,0.2), layers=('B.Cu',), box=BOX))
