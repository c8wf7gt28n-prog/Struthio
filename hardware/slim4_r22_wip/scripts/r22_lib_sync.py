# Write the R22 library copies (SLIM4.pretty/FP_<ref>.kicad_mod) for the replaced footprints.
import pcbnew, sys, os
b=pcbnew.LoadBoard(sys.argv[1]); lib=sys.argv[2]
SRC={'U11':('Package_TO_SOT_SMD','Texas_DRT-3'),'U12':('Package_TO_SOT_SMD','Texas_DRT-3'),'D1':('Diode_SMD','D_SOD-882'),
     'Y1':('Crystal','Crystal_SMD_3225-4Pin_3.2x2.5mm'),'SW5':('Button_Switch_SMD','SW_SPST_B3U-1000P'),
     'SW6':('Button_Switch_SMD','SW_SPST_B3U-1000P'),'SW7':('Button_Switch_SMD','SW_SPST_B3U-1000P'),
     'J3':('Connector_JST','JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal'),
     'J4':('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal'),'J5':('Connector_JST','JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal')}
for ref,(l,n) in SRC.items():
    bf=b.FindFootprintByReference(ref)
    lf=pcbnew.FootprintLoad('/usr/share/kicad/footprints/'+l+'.pretty',n)
    lf.SetFPID(pcbnew.LIB_ID('','FP_'+ref)); lf.SetDescription(bf.GetDescription()); lf.SetValue(bf.GetValue()); lf.SetReference(ref)
    lf.Reference().SetVisible(False); lf.Value().SetVisible(False)
    pcbnew.FootprintSave(lib,lf)
print('library copies written')
