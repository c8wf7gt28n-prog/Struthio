# After the R27 build: write the board's library copies (SLIM4.pretty/FP_<ref>.kicad_mod) for the footprints added or
# changed by the edits, so the board and its library agree (KiCad DRC: lib_footprint_issues / lib_footprint_mismatch).
# Each copy is the board footprint normalized as KiCad's library compares it: at the origin, unflipped, rotation 0,
# with no nets. Usage: python3 r27_export_lib.py BOARD.kicad_pcb PRETTY_DIR REF [REF ...]
import pcbnew, sys, os
b=pcbnew.LoadBoard(sys.argv[1]); pretty=sys.argv[2]
for ref in sys.argv[3:]:
    f=b.FindFootprintByReference(ref); assert f, ref
    c=pcbnew.FOOTPRINT(f)
    c.SetOrientationDegrees(0)
    if c.IsFlipped(): c.Flip(c.GetPosition(), False)
    c.SetPosition(pcbnew.VECTOR2I(0,0))
    for p in c.Pads(): p.SetNetCode(0)
    path=os.path.join(pretty, 'FP_%s.kicad_mod'%ref)
    if os.path.exists(path): os.remove(path)
    pcbnew.FootprintSave(pretty, c)
    assert os.path.exists(path), path
print('library: wrote %s'%', '.join('FP_%s'%r for r in sys.argv[3:]))
