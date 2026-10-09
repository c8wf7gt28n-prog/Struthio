# Write the R24 library copies (SLIM4.pretty/FP_<ref>.kicad_mod) of the new and replaced footprints, and delete the
# copies of the removed parts (C301, C405, R414).
import pcbnew, sys, os
b=pcbnew.LoadBoard(sys.argv[1]); lib=sys.argv[2]
SRC={'C402':('Capacitor_SMD','C_0603_1608Metric'),'C416':('Capacitor_SMD','C_0603_1608Metric'),
     'C417':('Capacitor_SMD','C_0805_2012Metric'),'C418':('Capacitor_SMD','C_0805_2012Metric'),'C419':('Capacitor_SMD','C_0805_2012Metric'),
     'C420':('Capacitor_SMD','C_0805_2012Metric'),'C421':('Capacitor_SMD','C_0805_2012Metric')}
for ref,(l,n) in SRC.items():
    bf=b.FindFootprintByReference(ref)
    lf=pcbnew.FootprintLoad('/usr/share/kicad/footprints/'+l+'.pretty',n)
    lf.SetFPID(pcbnew.LIB_ID('','FP_'+ref)); lf.SetDescription(bf.GetDescription()); lf.SetKeywords(bf.GetKeywords()); lf.SetValue(bf.GetValue()); lf.SetReference(ref)
    lf.Reference().SetVisible(False); lf.Value().SetVisible(False)
    pcbnew.FootprintSave(lib,lf)
for ref in ('C301','C405','R414'):
    assert b.FindFootprintByReference(ref) is None, ref
    p=os.path.join(lib,'FP_'+ref+'.kicad_mod')
    if os.path.exists(p): os.remove(p)
print('library copies written')
