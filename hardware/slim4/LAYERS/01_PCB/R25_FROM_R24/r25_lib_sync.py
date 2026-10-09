# Delete the R24 library copies (SLIM4.pretty/FP_<ref>.kicad_mod) of the parts R25 removes: the six 0 ohm DSI links
# R301-R306 (edit 25).
import pcbnew, sys, os
b=pcbnew.LoadBoard(sys.argv[1]); lib=sys.argv[2]
for ref in ('R301','R302','R303','R304','R305','R306'):
    assert b.FindFootprintByReference(ref) is None, ref
    p=os.path.join(lib,'FP_'+ref+'.kicad_mod')
    if os.path.exists(p): os.remove(p)
print('library copies removed: R301-R306')
