# R24 edit 17: the battery and system rails now ride the In2 planes (edit 16), so the old 0.152 mm routes of
#  BAT_PLUS and SYS_RAW on F.Cu and In3 (R23: 55 mm and 194 mm of them) are removed, (their vias stay: each now
#  lands in its plane). Pads keep their B.Cu stubs and vias into the planes; the blocks that follow add the vias still needed.
exec(open(sys.argv[2]).read())
kill_tracks(lambda t: t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname() in ('BAT_PLUS','SYS_RAW')
            and b.GetLayerName(t.GetLayer()) in ('F.Cu','In3.Cu'))
prune({'BAT_PLUS','SYS_RAW'},(-60,0,60,130))   # vias stay: they reach the planes
