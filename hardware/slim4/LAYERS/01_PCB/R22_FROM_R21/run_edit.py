import pcbnew, sys, os
P=sys.argv[1]; b=pcbnew.LoadBoard(P)
for script in sys.argv[2:]:
    src=open(script).read()
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'r22_lib.py')).read())
    exec(src.split("exec(open(sys.argv[2]).read())")[-1])
    for t in KILL: b.Remove(t)
b.Save(P); print("saved")
