# R22 edit 3: GND tracks beside SW5-SW7 moved clear of the B3U-1000P library pads
import pcbnew, sys
exec(open(sys.argv[2]).read())   # helpers: remove/add/KILL from r22_lib.py
remove("B.Cu",25.827,15.931,25.827,30.673,"GND"); remove("B.Cu",25.827,30.673,25.0,31.5,"GND")
add("B.Cu",[(25.827,15.931),(25.827,26.9),(26.25,27.323),(26.25,31.7),(25.6,31.7)],G)
remove("B.Cu",25.827,34.327,25.827,39.673,"GND"); remove("B.Cu",25.0,40.5,25.827,39.673,"GND")
add("B.Cu",[(25.827,34.327),(26.25,34.75),(26.25,40.7),(25.6,40.7)],G)
remove("B.Cu",24.0,41.5,24.0,48.5,"GND"); remove("B.Cu",24.0,48.5,25.0,49.5,"GND")
add("B.Cu",[(24.0,41.5),(23.7,41.8),(23.7,48.7),(24.5,49.5),(25.0,49.5)],G)
