# R23 edit 14: value changes, in the board file and in the local-library copy of each footprint.
#  R412 charge current 250 mA -> 500 mA. BQ24074 ISET: 3.6 k -> 1.8 k (K_ISET 890 A.ohm / 1.8 k = 494 mA),
#   0.5 C for a 1000 mAh cell; the input limit stays 500 mA (USB) or 1.07 A (ILIM, USB-C 1.5 A / 3 A, set by firmware).
#  R309 backlight current 39 mA -> 74 mA. The Crystalfontz backlight is two strings of LEDs (19.6-23.8 V, 40 mA each,
#   1.68 W) on one anode with two cathode pins, which J1 joins. TPS61165 FB = 200 mV: 5.1 R -> 2.7 R gives 74 mA,
#   37 mA a string. Worst-case boost limit (0.96 A switch limit, 3.2 V cell, 8 uH, 1.0 MHz, 24 V string): 84 mA.
import sys, os
B=sys.argv[1]; lib=os.path.join(os.path.dirname(B),'SLIM4.pretty')
CHANGES=[('R412','0402WGF3601TCE | JLC C25891 |','0402WGF1801TCE | JLC C25871 |','0402WGF3601TCE','0402WGF1801TCE'),
         ('R309','0603WAF510KT5E | JLC C25197 |','0603WAF270KT5E | JLC C22946 |','0603WAF510KT5E','0603WAF270KT5E')]
for ref,old,new,oval,nval in CHANGES:
    edit=lambda t: t.replace(old,new).replace(f'(fp_text value "{oval}"',f'(fp_text value "{nval}"')
    s=open(B).read(); i=s.index(f'(footprint "SLIM4:FP_{ref}"'); j=s.index('\n  (footprint ',i+10)
    blk=edit(s[i:j]); assert blk!=s[i:j], ref
    open(B,'w').write(s[:i]+blk+s[j:])
    p=os.path.join(lib,f'FP_{ref}.kicad_mod'); m=open(p).read(); m2=edit(m); assert m2!=m, ref
    open(p,'w').write(m2)
    print(f'{ref} -> {nval}')
