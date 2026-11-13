# R28 edit 47 (text): the title block says R28. The stackup (JLC06121H-3313, 2116 prepreg 0.1088 mm, ENIG) is R26's.
# Usage: python3 r28_meta.py BOARD.kicad_pcb DATE
import re, sys
p, date = sys.argv[1], sys.argv[2]
s = open(p).read()
TB = f'''  (title_block
    (title "STRUTHIO SLIM4 - main board")
    (date "{date}")
    (rev "R28")
    (company "R.A. Peddycoart")
  )
'''
s, n = re.subn(r'  \(title_block\n(    .*\n)*?  \)\n', TB, s, count=1)
assert n == 1, 'title block not found'
assert '(layer "dielectric 3" (type "prepreg") (thickness 0.1088)' in s, 'R26 stackup missing'
open(p, 'w').write(s)
print('meta: title block R28 (%s); stackup kept (JLC06121H-3313, 2116 0.1088 mm, ENIG)' % date)
