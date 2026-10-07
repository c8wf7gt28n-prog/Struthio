# R22 edit 6: J4 moved 2.7 mm inboard so the SH body and its tabs stay on the board (cable still enters from +Y);
# C603 nudged 0.15 mm clear of the J3 courtyard.
exec(open(sys.argv[2]).read())
f=b.FindFootprintByReference('J4'); f.Move(pcbnew.VECTOR2I(0,MM(-2.7)))
LN=b.FindNet('SPK_L_N'); LP=b.FindNet('SPK_L_P')
remove("B.Cu",-44.5,112.897,-44.5,114.0,"SPK_L_N"); add("B.Cu",[(-44.5,112.897),(-44.5,111.3)],LN)
remove("B.Cu",-42.878,113.854,-43.354,113.854,"SPK_L_P"); remove("B.Cu",-43.354,113.854,-43.5,114.0,"SPK_L_P")
add("B.Cu",[(-42.878,113.854),(-42.878,111.922),(-43.5,111.3)],LP)
b.FindFootprintByReference('C603').Move(pcbnew.VECTOR2I(MM(-0.15),0))
