#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · pictures of the board, top and bottom, from out/struthio_one_slim.kicad_pcb.

    /usr/bin/python3 plot_board.py           writes out/board_top.png and out/board_bottom.png

Top: the parts, their pads and the top copper, seen from the front of the handheld.
Bottom: the bottom copper, seen through the board from the front (not mirrored).
"""
import os
import pcbnew
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
OX, OY, S = 100.0, 100.0, 14
X0, X1, Y0, Y1 = -40, 40, -74, 40                       # design frame, mm
FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)

def plot(layer, path, title):
    b = pcbnew.LoadBoard(os.path.join(OUT, 'struthio_one_slim.kicad_pcb'))
    W, H = int((X1 - X0) * S), int((Y1 - Y0) * S) + 40
    im = Image.new('RGB', (W, H), (16, 40, 28)); d = ImageDraw.Draw(im)
    def P(v): x = pcbnew.ToMM(v.x) - OX; y = OY - pcbnew.ToMM(v.y); return ((x - X0) * S, (Y1 - y) * S + 40)
    d.text((12, 10), title, fill=(255, 255, 255), font=FONT)
    for dr in b.GetDrawings():
        if dr.GetLayer() == pcbnew.Edge_Cuts: d.line([P(dr.GetStart()), P(dr.GetEnd())], fill=(240, 240, 240), width=3)
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = P(t.GetPosition()); r = 0.35 * S; d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(214, 178, 72)); continue
        if t.GetLayer() != layer: continue
        w = max(2, int(pcbnew.ToMM(t.GetWidth()) * S))
        d.line([P(t.GetStart()), P(t.GetEnd())], fill=(214, 140, 72) if layer == pcbnew.F_Cu else (110, 160, 230), width=w)
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if not pad.IsOnLayer(layer): continue
            c = P(pad.GetPosition()); sz = pad.GetSize()
            hx, hy = pcbnew.ToMM(sz.x) * S / 2, pcbnew.ToMM(sz.y) * S / 2
            if round(pad.GetOrientationDegrees()) % 180 == 90: hx, hy = hy, hx
            d.rectangle([c[0] - hx, c[1] - hy, c[0] + hx, c[1] + hy], fill=(230, 196, 90))
        if layer == pcbnew.F_Cu:
            c = P(fp.GetPosition()); d.text((c[0] + 8, c[1] - 24), fp.GetReference(), fill=(255, 255, 255), font=FONT)
    im.save(path, optimize=True)
    print('wrote', os.path.relpath(path, HERE))

if __name__ == '__main__':
    plot(pcbnew.F_Cu, os.path.join(OUT, 'board_top.png'), 'STRUTHIO ONE SLIM rev S1 (0.8 mm) - top (parts side), seen from the front')
    plot(pcbnew.B_Cu, os.path.join(OUT, 'board_bottom.png'), 'STRUTHIO ONE SLIM rev S1 (0.8 mm) - bottom copper, seen through from the front')
