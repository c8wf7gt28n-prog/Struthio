# R22 edit 2: replace package-proxy footprints that do not match the purchased parts with KiCad 7 library footprints.
import pcbnew, sys, math
P=sys.argv[1]; b=pcbnew.LoadBoard(P)
MM=pcbnew.FromMM; mm=pcbnew.ToMM
LIB='/usr/share/kicad/footprints/'
# ref: (lib, name, {new_pad: old_pad}, note)
JOBS={
 'U11':('Package_TO_SOT_SMD','Texas_DRT-3',{'1':'1','2':'2','3':'3'}),
 'U12':('Package_TO_SOT_SMD','Texas_DRT-3',{'1':'1','2':'2','3':'3'}),
 'D1': ('Diode_SMD','D_SOD-882',{'1':'K/A','2':'A/K'}),           # pad 1 = cathode -> USB_VBUS
 'Y1': ('Crystal','Crystal_SMD_3225-4Pin_3.2x2.5mm',{'1':'1','2':'4','3':'3','4':'2'}),  # crystal: P/N and the two GND pads are interchangeable
 'SW5':('Button_Switch_SMD','SW_SPST_B3U-1000P',{'1':'1','2':'2'}),
 'SW6':('Button_Switch_SMD','SW_SPST_B3U-1000P',{'1':'1','2':'2'}),
 'SW7':('Button_Switch_SMD','SW_SPST_B3U-1000P',{'1':'1','2':'2'}),
 'J3': ('Connector_JST','JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal',{'1':'1','2':'2','3':'3'}),
 'J4': ('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal',{'1':'1','2':'2'}),
 'J5': ('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal',{'1':'1','2':'2'}),
}
only=sys.argv[2].split(',') if len(sys.argv)>2 else list(JOBS)
BL=b.GetLayerID('B.Cu')
TR=list(b.GetTracks())
report=[]
KILL=[]
NOSTUB={'U11','U12'}   # re-placed and re-routed by r22_esd.py
def make(lib,name,old,rot,on=None):
    nf=pcbnew.FootprintLoad(LIB+lib+'.pretty',name)
    b.Add(nf)
    if on is None: KILL.append(nf)
    nf.SetPosition(old.GetPosition())
    if old.IsFlipped(): nf.Flip(old.GetPosition(),False)
    nf.SetOrientationDegrees(rot)
    return nf
for ref in only:
    lib,name,pmap=JOBS[ref]
    old=b.FindFootprintByReference(ref)
    oldp={p.GetNumber():p for p in old.Pads()}
    oldxy={n:(mm(p.GetPosition().x),mm(p.GetPosition().y)) for n,p in oldp.items()}
    best=None
    for rot in (0,90,180,270):
        nf=make(lib,name,old,rot)
        newxy={p.GetNumber():(mm(p.GetPosition().x),mm(p.GetPosition().y)) for p in nf.Pads() if p.GetNumber() in pmap}
        dx=sum(oldxy[pmap[n]][0]-newxy[n][0] for n in pmap)/len(pmap); dy=sum(oldxy[pmap[n]][1]-newxy[n][1] for n in pmap)/len(pmap)
        err=max(math.hypot(oldxy[pmap[n]][0]-newxy[n][0]-dx,oldxy[pmap[n]][1]-newxy[n][1]-dy) for n in pmap)
        if best is None or err<best[0]: best=(err,rot,dx,dy)
    err,rot,dx,dy=best
    nf=make(lib,name,old,rot,b)
    nf.Move(pcbnew.VECTOR2I(MM(dx),MM(dy)))
    nf.SetReference(ref); nf.SetValue(old.GetValue())
    nf.Reference().SetVisible(False); nf.Value().SetVisible(False)
    d=old.GetDescription().split(' | ')
    nf.SetDescription(' | '.join(d[:2]+[f'KiCad 7 library {lib}:{name} (R22 land-pattern fix)']))
    nf.SetFPID(pcbnew.LIB_ID('SLIM4','FP_'+ref))
    nf.SetAttributes(old.GetAttributes())
    for p in nf.Pads():
        n=p.GetNumber()
        if n in pmap: p.SetNet(oldp[pmap[n]].GetNet())
        elif n in ('MP',''): 
            p.SetNet(b.FindNet(''))   # mechanical tabs: no net
    # stubs from old pad centres (where tracks end) to new pad centres
    stubs=0
    for p in nf.Pads():
        n=p.GetNumber()
        if n not in pmap: continue
        ox,oy=oldxy[pmap[n]]; nx,ny=mm(p.GetPosition().x),mm(p.GetPosition().y)
        if math.hypot(nx-ox,ny-oy)<0.005 or ref in NOSTUB: continue
        attached=[t for t in TR if t.GetClass()=='PCB_TRACK' and t.GetNetCode()==p.GetNetCode() and t.GetLayer()==(BL if old.IsFlipped() else b.GetLayerID('F.Cu'))
                  and any(abs(mm(q.x)-ox)<0.01 and abs(mm(q.y)-oy)<0.01 for q in (t.GetStart(),t.GetEnd()))]
        if not attached: continue
        t=pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(ox),MM(oy))); t.SetEnd(pcbnew.VECTOR2I(MM(nx),MM(ny)))
        t.SetWidth(MM(0.152)); t.SetLayer(attached[0].GetLayer()); t.SetNet(p.GetNet()); b.Add(t); stubs+=1
    KILL.append(old)
    report.append(f'{ref}: {name} rot {rot} fit {err:.3f} mm, {stubs} stubs')
for o in KILL: b.Remove(o)
b.Save(P)
print('\n'.join(report))
