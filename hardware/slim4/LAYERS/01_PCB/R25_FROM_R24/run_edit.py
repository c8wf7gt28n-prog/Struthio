import pcbnew, sys, os
__board_path__=sys.argv[1]; b=pcbnew.LoadBoard(__board_path__)
for script in sys.argv[2:]:
    src=open(script).read()
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'r25_lib.py')).read())
    exec(src.split("exec(open(sys.argv[2]).read())")[-1])
    for t in KILL: b.Remove(t)
assert isinstance(__board_path__, str) and __board_path__.endswith('.kicad_pcb'), 'an edit overwrote the board path'
b.Save(__board_path__); print("saved")
