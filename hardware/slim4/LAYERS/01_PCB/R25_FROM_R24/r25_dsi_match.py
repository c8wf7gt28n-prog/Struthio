# R25 edit 26: match the six DSI signals end to end (U1 pad to J1 pad) in flight time.
#  Flight time per layer: outer layers (microstrip over In1/In4 ground) about 5.9 ps/mm, In3 (stripline between the
#  In2 and In4 planes) about 6.9 ps/mm. Every signal gets meanders until it is within 0.5 ps of the slowest one
#  Via barrels are not in the model: each layer change adds roughly 4-8 ps of barrel, and P and N of a pair differ by
#  1-2 changes (2-7 vias a signal), so up to about 16 ps between P and N is left unmodelled.
exec(open(sys.argv[2]).read())
VEL={'F.Cu':5.9,'B.Cu':5.9,'In3.Cu':6.9}
SIGS=['MIPI_DSI_%s'%s for s in ('CLK_P','CLK_N','D0_P','D0_N','D1_P','D1_N')]
def ftime(n):
    T=0.0
    for t in b.GetTracks():
        if _dead(t) or t.Type()==pcbnew.PCB_VIA_T or t.GetNetname()!=n: continue
        T+=mm(t.GetLength())*VEL[b.GetLayerName(t.GetLayer())]
    return T
def flen(n): return sum(mm(t.GetLength()) for t in b.GetTracks() if not _dead(t) and t.Type()!=pcbnew.PCB_VIA_T and t.GetNetname()==n)
AMPS=dict(amps=(2.0,1.6,1.3,1.0,0.8,0.6,0.45,0.3,0.2,0.1), pitch=0.36, end=0.25)
target=max(ftime(n) for n in SIGS)
for n in SIGS:
    for lay in ('B.Cu','F.Cu','In3.Cu'):
        need=target-ftime(n)
        if need<0.5: break
        meander(n, lay, need/VEL[lay], **AMPS)
for n in SIGS: print('dsi match: %-16s %7.2f ps  %7.3f mm  (target %.2f ps)'%(n, ftime(n), flen(n), target))
