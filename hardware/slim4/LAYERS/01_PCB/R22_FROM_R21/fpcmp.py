import pcbnew, sys, math, itertools
LIB='/usr/share/kicad/footprints/'
REF={
 'R0402':('Resistor_SMD','R_0402_1005Metric'),'C0402':('Capacitor_SMD','C_0402_1005Metric'),
 'R0603':('Resistor_SMD','R_0603_1608Metric'),'C0603':('Capacitor_SMD','C_0603_1608Metric'),
 'C0805':('Capacitor_SMD','C_0805_2012Metric'),
 'SOT-23-5':('Package_TO_SOT_SMD','SOT-23-5'),'SOT-23-6':('Package_TO_SOT_SMD','SOT-23-6'),'SOT-23':('Package_TO_SOT_SMD','SOT-23'),
 'DRT':('Package_TO_SOT_SMD','Texas_DRT-3'),'BQ':('Package_DFN_QFN','VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm'),
 'MAX':('Package_DFN_QFN','TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm'),'TUSB':('Package_DFN_QFN','Texas_X2QFN-12_1.6x1.6mm_P0.4mm'),
 'WSON8':('Package_SON','WSON-8-1EP_8x6mm_P1.27mm_EP3.4x4.3mm'),'SOD-523':('Diode_SMD','D_SOD-523'),'SOD-882':('Diode_SMD','D_SOD-882'),
 'SOD-123F':('Diode_SMD','D_SOD-123F'),'X2016':('Crystal','Crystal_SMD_2016-4Pin_2.0x1.6mm'),'X3225':('Crystal','Crystal_SMD_3225-4Pin_3.2x2.5mm'),
 'SH3':('Connector_JST','JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal'),'SH2':('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal'),
 'B3U':('Button_Switch_SMD','SW_SPST_B3U-1000P'),
}
def pads_local(f):
    out=[]
    o=f.GetOrientation(); flip=f.IsFlipped()
    for p in f.Pads():
        q=p.GetPosition()-f.GetPosition()
        v=pcbnew.VECTOR2I(q.x,q.y); 
        # undo footprint rotation
        a=-o.AsRadians() if hasattr(o,'AsRadians') else -math.radians(o/10)
        x,y=pcbnew.ToMM(v.x),pcbnew.ToMM(v.y)
        ca,sa=math.cos(a),math.sin(a)
        # KiCad y-down: rotation by +theta (CCW on screen) is x'=x cos+y sin, y'=-x sin+y cos
        xr=x*math.cos(-a)+y*math.sin(-a); yr=-x*math.sin(-a)+y*math.cos(-a)
        if flip: xr=-xr
        pr=(p.GetOrientation()-o).AsDegrees()%180
        sx,sy=pcbnew.ToMM(p.GetSize().x),pcbnew.ToMM(p.GetSize().y)
        if abs(pr-90)<1: sx,sy=sy,sx
        out.append((p.GetNumber(),xr,yr,sx,sy))
    return out
def ref_pads(lib,name):
    f=pcbnew.FootprintLoad(LIB+lib+'.pretty',name)
    out=[]
    for p in f.Pads():
        q=p.GetPosition(); pr=p.GetOrientation().AsDegrees()%180
        sx,sy=pcbnew.ToMM(p.GetSize().x),pcbnew.ToMM(p.GetSize().y)
        if abs(pr-90)<1: sx,sy=sy,sx
        out.append((p.GetNumber(),pcbnew.ToMM(q.x),pcbnew.ToMM(q.y),sx,sy))
    return out
def cent(P): 
    return (sum(p[1] for p in P)/len(P), sum(p[2] for p in P)/len(P))
def compare(A,B):
    # align by best of 8 symmetries using matched pad numbers (ignore unnumbered/MP)
    best=None
    for rot in range(4):
        for mir in (False,True):
            def T(p):
                x,y=p[1],p[2]
                if mir: x=-x
                for _ in range(rot): x,y=-y,x
                sx,sy=(p[3],p[4]) if rot%2==0 else (p[4],p[3])
                return (p[0],x,y,sx,sy)
            AT=[T(p) for p in A]
            ca=cent(AT); cb=cent(B)
            # match by number
            dn={};
            for p in B: dn.setdefault(p[0],[]).append(p)
            err=0; worst=0; sz=0; miss=[]
            for p in AT:
                c=dn.get(p[0])
                if not c: miss.append(p[0]); continue
                q=min(c,key=lambda q:(p[1]-ca[0]-q[1]+cb[0])**2+(p[2]-ca[1]-q[2]+cb[1])**2)
                d=math.hypot(p[1]-ca[0]-q[1]+cb[0],p[2]-ca[1]-q[2]+cb[1]); worst=max(worst,d)
                sz=max(sz,abs(p[3]-q[3]),abs(p[4]-q[4]))
            key=(len(miss),worst)
            if best is None or key<best[0]: best=(key,rot,mir,worst,sz,miss)
    return best
if __name__=='__main__':
    b=pcbnew.LoadBoard(sys.argv[1])
    MAP=dict(a.split('=') for a in sys.argv[2:])
    for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
        r=f.GetReference(); k=MAP.get(r) or MAP.get(r.rstrip('0123456789')+'*')
        if not k: continue
        A=pads_local(f); B=ref_pads(*REF[k])
        bst=compare(A,B)
        print(f"{r:5s} {k:9s} n={len(A)}/{len(B)} worst_pos={bst[3]:.3f} max_size_diff={bst[4]:.3f} missing={bst[5]} rot={bst[1]} mir={bst[2]}")
