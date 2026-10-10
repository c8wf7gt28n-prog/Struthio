# R28 check (after the zone fill): the radio's RF path, U15 pin 37 (RF_OUT) through R704 to J701 (U.FL).
#   - every RADIO_RF / RADIO_ANT track is on B.Cu and 0.18 mm wide: a 50 ohm microstrip over In4's ground across the
#     0.0994 mm prepreg (JLC06121H-3313, er about 4.1);
#   - In4's filled GND covers each track's strip plus 0.30 mm each side (no antipad, slot or gap under it);
#   - the nearest copper of another net on B.Cu (not GND) is reported, and must be 0.30 mm or more from the track edge.
# Usage: python3 r28_rf_check.py BOARD.kicad_pcb
import pcbnew, sys, math
b = pcbnew.LoadBoard(sys.argv[1]); MM = pcbnew.FromMM; mm = pcbnew.ToMM
RF, W, SIDE, KEEP = ('RADIO_RF', 'RADIO_ANT'), 0.18, 0.30, 0.30
lid = {n: b.GetLayerID(n) for n in ('B.Cu', 'In4.Cu')}


def capsule(a, c, r, n=16):
    ang = math.atan2(c.y - a.y, c.x - a.x); sp = pcbnew.SHAPE_POLY_SET(); sp.NewOutline()
    for k in range(n + 1):
        th = ang - math.pi / 2 + math.pi * k / n; sp.Append(int(c.x + r * math.cos(th)), int(c.y + r * math.sin(th)))
    for k in range(n + 1):
        th = ang + math.pi / 2 + math.pi * k / n; sp.Append(int(a.x + r * math.cos(th)), int(a.y + r * math.sin(th)))
    return sp


gnd4 = pcbnew.SHAPE_POLY_SET()
for z in b.Zones():
    if z.GetNetname() == 'GND' and z.IsOnLayer(lid['In4.Cu']) and not z.GetIsRuleArea():
        gnd4.BooleanAdd(z.GetFilledPolysList(lid['In4.Cu']), pcbnew.SHAPE_POLY_SET.PM_FAST)
bad, total, segs = [], 0.0, []
for t in b.GetTracks():
    if t.GetNetname() not in RF: continue
    if t.Type() == pcbnew.PCB_VIA_T:
        bad.append(f'{t.GetNetname()}: a via at ({mm(t.GetPosition().x):.2f}, {mm(t.GetPosition().y):.2f})'); continue
    a, c = t.GetStart(), t.GetEnd(); L = mm((c - a).EuclideanNorm()); total += L
    segs.append(t)
    if t.GetLayer() != lid['B.Cu']: bad.append(f'{t.GetNetname()}: a track on {t.GetLayerName()}')
    if abs(mm(t.GetWidth()) - W) > 1e-4: bad.append(f'{t.GetNetname()}: a track {mm(t.GetWidth()):.3f} mm wide')
    strip = capsule(a, c, MM(W / 2 + SIDE)); strip.BooleanSubtract(gnd4, pcbnew.SHAPE_POLY_SET.PM_FAST)
    if strip.Area() > MM(0.001) * MM(1):
        bad.append(f'{t.GetNetname()} ({mm(a.x):.2f}, {mm(a.y):.2f})-({mm(c.x):.2f}, {mm(c.y):.2f}): '
                   f'{strip.Area() / 1e12:.4f} mm2 of its strip not over In4 GND')
near = (1e9, '')
for t in segs:
    sg = pcbnew.SEG(t.GetStart(), t.GetEnd())
    for o in b.GetTracks():
        if o.GetNetname() in RF + ('GND',): continue
        if o.Type() != pcbnew.PCB_VIA_T and o.GetLayer() != lid['B.Cu']: continue
        d = mm(o.GetEffectiveShape().GetClearance(pcbnew.SHAPE_SEGMENT(sg, t.GetWidth())))
        if d < near[0]: near = (d, f'{o.GetNetname()} {"via" if o.Type() == pcbnew.PCB_VIA_T else "track"}')
    for f in b.GetFootprints():
        for q in f.Pads():
            if q.GetNetname() in RF + ('GND',) or not q.IsOnLayer(lid['B.Cu']): continue
            if abs(mm(q.GetPosition().x - t.GetStart().x)) > 6 or abs(mm(q.GetPosition().y - t.GetStart().y)) > 6: continue
            d = mm(q.GetEffectiveShape().GetClearance(pcbnew.SHAPE_SEGMENT(sg, t.GetWidth())))
            if d < near[0]: near = (d, f'{f.GetReference()}.{q.GetNumber()} {q.GetNetname()}')
if near[0] < KEEP: bad.append(f'other-net copper {near[0]:.3f} mm from the RF track ({near[1]})')
print(f'rf check: {len(segs)} RF segments, {total:.2f} mm, all B.Cu {W} mm over In4 GND (+{SIDE} mm each side); '
      f'nearest other-net copper {near[0]:.2f} mm ({near[1]})' if not bad else 'rf check FAILED:\n  ' + '\n  '.join(bad))
sys.exit(1 if bad else 0)
