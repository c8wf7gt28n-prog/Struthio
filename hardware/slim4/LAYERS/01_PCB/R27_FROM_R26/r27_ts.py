# R27 edit 41: the charger's TS resistor near the charger. R424 (10 k from BQ24074 TS to GND, which holds TS at a
# "normal temperature" level) sat by J3, 88 mm of track and two vias from U10 pin 1 (pre-order review POWER M4): a fault
# on that run stops charging while CHG still reads charging. The back is full round U10 (C409, C411, the VBUS and
# SYS_RAW tracks), so the route keeps its pin-1 stub, its via and the start of its In3 run, and ends at the first
# point along that run where a new via fits with R424 beside it on the back (placed by search, joined by a short
# track). The rest of the run, its far via, the old R424 and R424's old GND stub go.
exec(open(sys.argv[2]).read())
old=fpr('R424'); ox,oy=mm(old.GetPosition().x),mm(old.GetPosition().y); KILL.append(old)
TS=net('BQ_TS'); ts=TS.GetNetCode()
A=(19.0382, 7.25); B=(13.3366, 12.9516)          # the In3 segment leaving U10's via
keep=[t for t in b.GetTracks() if t.GetNetCode()==ts and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['B.Cu']
      and (near(t.GetStart(),18.4,7.25) or near(t.GetEnd(),18.4,7.25))]
keep_via=[t for t in b.GetTracks() if t.GetNetCode()==ts and t.Type()==pcbnew.PCB_VIA_T and near(t.GetPosition(),*A)]
assert len(keep)==1 and len(keep_via)==1
KEEP={t.m_Uuid.AsString() for t in keep+keep_via}      # SWIG proxies do not compare equal: match by UUID
kill_tracks(lambda t: t.GetNetCode()==ts and t.m_Uuid.AsString() not in KEEP)
prune(['GND'], (ox-2, oy-2, ox+2, oy+2))
L_AB=math.hypot(B[0]-A[0],B[1]-A[1]); done=None
for k in range(int(L_AB/0.25)+1):
    s_=min(1.0, 0.8/L_AB + k*0.25/L_AB)          # from 0.8 mm past U10's via towards the bend
    V=(round(A[0]+(B[0]-A[0])*s_,3), round(A[1]+(B[1]-A[1])*s_,3))
    if not via_free(*V,'BQ_TS',0.12): continue
    via=pcbnew.PCB_VIA(b); via.SetPosition(pcbnew.VECTOR2I(MM(V[0]),MM(V[1]))); via.SetWidth(MM(0.45)); via.SetDrill(MM(0.2))
    via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(L["F.Cu"],L["B.Cu"]); via.SetNet(TS); b.Add(via)
    try:                                          # the via is in place first, so R424's GND pad keeps clear of it
        f,txt=place_joined('R424','Resistor_SMD','R_0402_1005Metric','0402WGF1002TCE','C25744',
                           'R27: BQ24074 TS 10 k to GND, near U10 (KiCad 7 library Resistor_SMD:R_0402_1005Metric)',
                           [V], 2.5,
                           {'1':('BQ_TS', [V], 2.5, False), '2':('GND', copper_points('GND', exclude=('R424',)), 2.0, None)})
    except AssertionError:
        b.Remove(via); continue
    NEW_VIAS.append(pcbnew.VECTOR2I(MM(V[0]),MM(V[1])))
    add('In3.Cu',[A,V],TS,0.152)
    done=(V,txt); break
assert done, 'no place for R424 along the BQ_TS run'
V,txt=done
run=0.64+math.hypot(V[0]-A[0],V[1]-A[1])
print('ts: R424 moved from (%.2f, %.2f) to near U10; BQ_TS now %.1f mm of In3 to a via at (%.2f, %.2f) (was 88.3 mm); %s'%(ox,oy,run,V[0],V[1],txt))
