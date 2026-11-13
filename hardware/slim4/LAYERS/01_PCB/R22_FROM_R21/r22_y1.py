# R22 edit 5: Y1 on the KiCad 3225 land pattern; drop the GND link that now runs under pad 3 (C120 keeps its GND path)
exec(open(sys.argv[2]).read())
remove("B.Cu",-10.75,79.3,-10.75,78.35,"GND"); remove("B.Cu",-10.75,78.35,-9.65,77.25,"GND")
