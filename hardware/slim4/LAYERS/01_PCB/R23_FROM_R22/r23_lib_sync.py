# Write the R23 library copies (SLIM4.pretty/FP_<ref>.kicad_mod) of the new and replaced footprints.
import pcbnew, sys, os
b=pcbnew.LoadBoard(sys.argv[1]); lib=sys.argv[2]
SRC={'J1':('Connector_FFC-FPC','Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal'),
     'J3':('Connector_JST','JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal'),
     'J4':('Connector_Molex','Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal'),
     'J5':('Connector_Molex','Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal'),
     'Q2':('Package_TO_SOT_SMD','SOT-23')}
for ref,(l,n) in SRC.items():
    bf=b.FindFootprintByReference(ref)
    lf=pcbnew.FootprintLoad('/usr/share/kicad/footprints/'+l+'.pretty',n)
    lf.SetFPID(pcbnew.LIB_ID('','FP_'+ref)); lf.SetDescription(bf.GetDescription()); lf.SetValue(bf.GetValue()); lf.SetReference(ref)
    lf.Reference().SetVisible(False); lf.Value().SetVisible(False)
    pcbnew.FootprintSave(lib,lf)
print('library copies written')
