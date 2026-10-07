import pcbnew,sys,re
p=sys.argv[1]
b=pcbnew.LoadBoard(p); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(p)
b=pcbnew.LoadBoard(p); pcbnew.WriteDRCReport(b,"DRC.rpt",pcbnew.EDA_UNITS_MILLIMETRES,True)
t=open("DRC.rpt").read()
print("\n".join(l for l in t.splitlines() if l.startswith("** Found")))
