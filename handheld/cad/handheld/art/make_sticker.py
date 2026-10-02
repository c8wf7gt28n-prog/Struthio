#!/usr/bin/env python3
# STRUTHIO HANDHELD · the front art sticker, cut exactly to the
# template (../svg/struthio_sticker_cut.svg: wings, DART rocker, grille).
# Art is the game's own: the STRUTHIO logo and the jousting scene from
# arcade/assets/art/hero-art.webp. Writes:
#   sticker_front_print.html  print sheet: art clipped to the outline + 1.5 mm bleed
#   sticker_front_proof.html  the same with the cut lines and the cut-away holes marked
# render_sticker.mjs turns both into 600 dpi PNGs.
import os, re
from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', 'svg', 'struthio_sticker_cut.svg')
HERO = 'hero-art.webp'      # 941 x 1672, the game's hero art (from arcade/assets/art), next to the HTML pages
BLEED = 1.5
LOGO_W, LOGO_H = 30.0, 7.6                                 # the band above the wing holes is ~8.5 mm

svg = open(TEMPLATE).read()
d = re.search(r'<path d="([^"]*)"', svg, re.S).group(1)
rings = []
for sub in re.split(r'M', d)[1:]:
    pts = [tuple(map(float, p.split(','))) for p in re.findall(r'-?[\d.]+,-?[\d.]+', sub)]
    rings.append(Polygon(pts).buffer(0))
rings.sort(key=lambda p: -p.area)
outer, holes = rings[0], rings[1:]
sticker = outer
for h in holes: sticker = sticker.difference(h)
x0, y0, x1, y1 = outer.bounds
bleed = outer.buffer(BLEED, join_style=2)
bx0, by0, bx1, by1 = bleed.bounds

def path(geom):
    polys = getattr(geom, 'geoms', [geom])
    out = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)
            out.append('M ' + ' L '.join(f'{x:.3f},{y:.3f}' for x, y in c) + ' Z')
    return ' '.join(out)

def hero(box, src_x0, src_x1, src_cy):
    """Box art scaled so source columns src_x0..src_x1 span the box width, source row src_cy at its centre."""
    bx, by, bw, bh = box
    s = bw / (src_x1 - src_x0)
    return f'<image href="{HERO}" x="{bx - src_x0 * s:.3f}" y="{by + bh / 2 - src_cy * s:.3f}" width="{941 * s:.3f}" height="{1672 * s:.3f}" preserveAspectRatio="none"/>'

cx = (x0 + x1) / 2
art = (f'<g clip-path="url(#bleed)">'
       # the arena and both jousters, filling the bleed box
       + hero((bx0, by0, bx1 - bx0, by1 - by0), 60, 880, 690)
       # a void band behind the logo so it reads over the scene
       + f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{y0 + LOGO_H + 1.5 - by0}" fill="url(#fade)"/>'
       # the STRUTHIO logo, from the same box art
       + f'<g mask="url(#logoh)"><g mask="url(#logofade)"><svg x="{cx - LOGO_W / 2}" y="{y0 + 0.2}" width="{LOGO_W}" height="{LOGO_H}" viewBox="20 80 900 262" preserveAspectRatio="xMidYMid meet" overflow="hidden">'
         f'<image href="{HERO}" x="0" y="0" width="941" height="1672"/></svg></g></g>'
       + '</g>')
defs = (f'<defs><clipPath id="bleed"><path d="{path(bleed)}"/></clipPath>'
        '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#07131F" stop-opacity="0.92"/><stop offset="0.7" stop-color="#07131F" stop-opacity="0.55"/>'
        '<stop offset="1" stop-color="#07131F" stop-opacity="0"/></linearGradient>'
        # soft edges for the logo crop (the box art carries its own dark backing):
        # fade only the outer 14% left/right and the bottom 18%, never the letters
        '<linearGradient id="lh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000"/>'
        '<stop offset="0.14" stop-color="#fff"/><stop offset="0.86" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
        '<linearGradient id="lv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000"/><stop offset="0.06" stop-color="#fff"/>'
        '<stop offset="0.82" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
        f'<mask id="logoh" maskUnits="userSpaceOnUse" x="{cx - LOGO_W / 2}" y="{y0 + 0.2}" width="{LOGO_W}" height="{LOGO_H}">'
        f'<rect x="{cx - LOGO_W / 2}" y="{y0 + 0.2}" width="{LOGO_W}" height="{LOGO_H}" fill="url(#lh)"/></mask>'
        f'<mask id="logofade" maskUnits="userSpaceOnUse" x="{cx - LOGO_W / 2}" y="{y0 + 0.2}" width="{LOGO_W}" height="{LOGO_H}">'
        f'<rect x="{cx - LOGO_W / 2}" y="{y0 + 0.2}" width="{LOGO_W}" height="{LOGO_H}" fill="url(#lv)"/></mask></defs>')

def page(name, body):
    w, h = bx1 - bx0, by1 - by0
    html = (f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:#fff}}</style></head><body>'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="{bx0} {by0} {w} {h}">{defs}{body}</svg></body></html>')
    open(os.path.join(HERE, name), 'w').write(html)
    print(name, f'{w:.1f} x {h:.1f} mm')

page('sticker_front_print.html', art)
holes_path = path(unary_union(holes)) if holes else ''
proof = (art
         + f'<path d="{holes_path}" fill="#ffffff" fill-opacity="0.55" stroke="none"/>'
         + f'<path d="{path(sticker)}" fill="none" stroke="#FF2BD6" stroke-width="0.18"/>'
         + f'<path d="{path(bleed)}" fill="none" stroke="#20C4D7" stroke-width="0.12" stroke-dasharray="0.8 0.5"/>')
page('sticker_front_proof.html', proof)
