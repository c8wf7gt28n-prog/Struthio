# R26 edit 35 (text): board metadata. The R26 title block, and the stackup corrected to what JLCPCB's impedance
# calculator lists today for JLC06121H-3313: the centre 2116 prepreg is 0.1088 mm (R25 said 0.1164 mm). 1 oz outer,
# 0.5 oz inner, ENIG finish. Usage: python3 r26_meta.py BOARD.kicad_pcb DATE
import re, sys
p, date = sys.argv[1], sys.argv[2]
s = open(p).read()
TB = f'''  (title_block
    (title "STRUTHIO SLIM4 - main board")
    (date "{date}")
    (rev "R26")
    (company "R.A. Peddycoart")
  )
'''
s, n = re.subn(r'  \(title_block\n(    .*\n)*?  \)\n', TB, s, count=1)
assert n == 1, 'title block not found'
D = lambda i, kind, t, er: f'      (layer "dielectric {i}" (type "{kind}") (thickness {t}) (material "FR4") (epsilon_r {er}) (loss_tangent 0.02))\n'
C = lambda name, t: f'      (layer "{name}" (type "copper") (thickness {t}))\n'
STACK = ('    (stackup\n'
         '      (layer "F.SilkS" (type "Top Silk Screen"))\n'
         + C('F.Cu', 0.035) + D(1, 'prepreg', 0.0994, 4.1) + C('In1.Cu', 0.0152) + D(2, 'core', 0.35, 4.36)
         + C('In2.Cu', 0.0152) + D(3, 'prepreg', 0.1088, 4.16) + C('In3.Cu', 0.0152) + D(4, 'core', 0.35, 4.36)
         + C('In4.Cu', 0.0152) + D(5, 'prepreg', 0.0994, 4.1) + C('B.Cu', 0.035) +
         '      (layer "B.SilkS" (type "Bottom Silk Screen"))\n'
         '      (copper_finish "ENIG")\n'
         '      (dielectric_constraints no)\n'
         '    )\n')
s = re.sub(r'    \(stackup\n(      .*\n)*?    \)\n', '', s)          # idempotent
assert s.count('  (setup\n') == 1
s = s.replace('  (setup\n', '  (setup\n' + STACK, 1)
open(p, 'w').write(s)
print('meta: title block R26 (%s), stackup JLC06121H-3313 (2116 0.1088 mm), finish ENIG' % date)
