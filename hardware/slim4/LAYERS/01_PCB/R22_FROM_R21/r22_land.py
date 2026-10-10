# R22 edit 11: power-inductor lands to Sunlord's recommended patterns (board file and SLIM4.pretty library copies)
#  L1 MWSA0402S-1R0MT: pads 1.5 x 2.5 at +-1.85 (MWSA-S catalogue p.2); the proxy stopped 0.35 mm short of the toe
#  L2 ASWPA4035S2R2MT, L3 WPN4020H100MT: pads 1.1 x 3.7 at +-1.5 (ASWPA / WPN catalogues); the proxy was narrower than the terminals
#  plus: the audited proxy descriptions, and one 3V3_SYS track jog under L2
import sys, os, re
B = sys.argv[1]; lib = os.path.join(os.path.dirname(B), 'SLIM4.pretty')
LAND = {'L1': (1.85, 1.5, 2.5, 'Sunlord MWSA-S recommended land 1.5 x 2.5 at 3.7 pitch'),
        'L2': (1.5, 1.1, 3.7, 'Sunlord ASWPA recommended land 1.1 x 3.7 at 3.0 pitch'),
        'L3': (1.5, 1.1, 3.7, 'Sunlord WPN recommended land 1.1 x 3.7 at 3.0 pitch')}
OLD = 'R8 first-copper package proxy; exact land-pattern audit remains a fab gate'


def edit(blk, ref, board):
    x, w, h, note = LAND[ref]
    blk, n = re.subn(r'\(pad "([12])" smd roundrect \(at -?[\d.]+ 0(?:\.0)?( 180)?\) \(size [\d.]+ [\d.]+\)',
                     lambda m: f'(pad "{m[1]}" smd roundrect (at {-x if m[1] == "1" else x:g} 0{m[2] or ""}) (size {w:g} {h:g})', blk)
    assert n == 2, (ref, n)
    assert OLD in blk, ref
    return blk.replace(OLD, note + ' (R22)')


s = open(B).read()
for ref in LAND:
    i = s.index(f'(footprint "SLIM4:FP_{ref}"'); j = s.index('\n  (footprint ', i + 10)
    s = s[:i] + edit(s[i:j], ref, True) + s[j:]
    p = os.path.join(lib, f'FP_{ref}.kicad_mod'); m = edit(open(p).read(), ref, False); open(p, 'w').write(m)
# Every other R8 proxy land was compared with the KiCad 7 library land for its package in the R22 audit
# (ELECTRICAL_REVIEW_R22.md, R22_FROM_R21/fpcmp.py): the descriptions say so instead of 'audit remains a fab gate'.
AUDITED = 'R8 first-copper land; checked in the R22 land-pattern audit (ELECTRICAL_REVIEW_R22.md)'
n_desc = s.count(OLD)
s = s.replace(OLD, AUDITED)
for f in sorted(os.listdir(lib)):
    p = os.path.join(lib, f); m = open(p).read()
    if OLD in m:
        open(p, 'w').write(m.replace(OLD, AUDITED))
# L2's wider pad 2 reaches y 102.85: the 3V3_SYS track that ran under its end (y 102.8) drops to y 103.7 at x 2.2-2.65.
JOG = [('(segment (start 2.2 102.65) (end 2.35 102.8)', '(segment (start 2.2 102.65) (end 2.2 103.25)'),
       ('(segment (start 2.35 102.8) (end 3 102.8)', '(segment (start 2.2 103.25) (end 2.65 103.7)'),
       ('(segment (start 3 102.8) (end 3.9 103.7)', '(segment (start 2.65 103.7) (end 3.9 103.7)')]
for a, b in JOG:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(B, 'w').write(s)
print('lands:', ', '.join(f'{r} {w:g}x{h:g} at +-{x:g}' for r, (x, w, h, _) in LAND.items()), f'; {n_desc} audited descriptions')
