# R22 edit 7: part value changes (board file and SLIM4.pretty library copies)
#  C203/C204 crystal load caps 18 pF -> 12 pF C0G (Lucki L327S400H11L: CL = 10 pF; 12 pF in series + ~4 pF stray)
#  R309 backlight sense 24.9 -> 5.1 ohm: TPS61165 VFB 200 mV / 5.1 = 39 mA (panel: 2 parallel strings, 40 mA total)
#  U6 panel VCI LDO 2.8 V -> 3.0 V (TLV75530): mid-range for ST7703 / ILI9881C / ST7701S panels; net LCD_2V8 -> LCD_VCI_3V0
#  C309 backlight output 1 uF 25 V -> 1 uF 50 V: open-LED protection lets the output reach 39 V (no panel plugged in)
import sys, os
B=sys.argv[1]; lib=os.path.join(os.path.dirname(B),'SLIM4.pretty')
CHANGES={
 'C203':('C0402C180F5GACTU','C1882955','0402CG120J500NT','C1547'),
 'C204':('C0402C180F5GACTU','C1882955','0402CG120J500NT','C1547'),
 'R309':('0603WAF249KT5E','C247053','0603WAF510KT5E','C25197'),
 'U6':('TLV75528PDBVR','C2868951','TLV75530PDBVR','C507268'),
 'C309':('CS1608X7R105K250NRB','C513775','CL10A105KB8NNNC','C15849'),
}
def fix(text,old,oc,new,nc):
    return text.replace(f'{old} | JLC {oc} |',f'{new} | JLC {nc} |').replace(f'(fp_text value "{old}"',f'(fp_text value "{new}"')
s=open(B).read()
for ref,(old,oc,new,nc) in CHANGES.items():
    p=os.path.join(lib,f'FP_{ref}.kicad_mod'); m=open(p).read(); m2=fix(m,old,oc,new,nc); assert m2!=m,ref; open(p,'w').write(m2)
    i=s.index(f'(footprint "SLIM4:FP_{ref}"'); j=s.index('\n  (footprint ',i+10)
    blk=fix(s[i:j],old,oc,new,nc); assert blk!=s[i:j],ref; s=s[:i]+blk+s[j:]
s=s.replace('"LCD_2V8"','"LCD_VCI_3V0"')
open(B,'w').write(s); print('values:',', '.join(f'{r} {v[2]}' for r,v in CHANGES.items()))
