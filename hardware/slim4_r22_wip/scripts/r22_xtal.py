# R22 edit 7: crystal load capacitors 18 pF -> 12 pF C0G (Lucki L327S400H11L: CL = 10 pF; 12 pF + ~4 pF stray -> 10 pF)
import pcbnew, sys, re, os
B=sys.argv[1]; lib=os.path.join(os.path.dirname(B),'SLIM4.pretty')
OLD,NEW='C0402C180F5GACTU | JLC C1882955 |','0402CG120J500NT | JLC C1547 |'
for ref in ('C203','C204'):
    p=os.path.join(lib,f'FP_{ref}.kicad_mod'); s=open(p).read()
    s=s.replace(OLD,NEW).replace('(fp_text value "C0402C180F5GACTU"','(fp_text value "0402CG120J500NT"'); open(p,'w').write(s)
s=open(B).read()
for ref in ('C203','C204'):
    i=s.index(f'(footprint "SLIM4:FP_{ref}"'); j=s.index('\n  (footprint ',i+10)
    blk=s[i:j].replace(OLD,NEW).replace('(fp_text value "C0402C180F5GACTU"','(fp_text value "0402CG120J500NT"')
    s=s[:i]+blk+s[j:]
open(B,'w').write(s); print('crystal caps -> 12 pF')
