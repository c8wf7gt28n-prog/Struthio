# Library copies for the battery-port edit: FP_J3 (now 2-pin) and the new FP_R424.
import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); lib=sys.argv[2]
for ref,(l,n) in {'J3':('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal'),'R424':('Resistor_SMD','R_0402_1005Metric')}.items():
    bf=b.FindFootprintByReference(ref)
    lf=pcbnew.FootprintLoad('/usr/share/kicad/footprints/'+l+'.pretty',n)
    lf.SetFPID(pcbnew.LIB_ID('','FP_'+ref)); lf.SetDescription(bf.GetDescription()); lf.SetValue(bf.GetValue()); lf.SetReference(ref)
    lf.SetKeywords(bf.GetKeywords()); lf.Reference().SetVisible(False); lf.Value().SetVisible(False)
    pcbnew.FootprintSave(lib,lf)
print('battery library copies written')
