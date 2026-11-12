"""Bounded, read-only KiCad shape extraction for ARC-1 Workbench.

This is an *inspection drawing*, not a KiCad renderer/netlist/ERC/DRC engine.
A source must not be treated as electrically checked merely because it draws.
Qt is deliberately not required so parsers can be regression tested headlessly.
"""
from __future__ import annotations

import math
from pathlib import Path

from sdk.cli.arc1cli.kicad_sexpr import MAX_CAD_BYTES, ViewerError, parse


def read(path, root_tag):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CAD_BYTES:
        raise ViewerError('Missing, linked or oversized KiCad document')
    try:
        node = parse(path.read_text(encoding='utf-8'))
    except (UnicodeError, OSError) as exc:
        raise ViewerError(str(exc)) from exc
    if not node or node[0] != root_tag:
        raise ViewerError(f'Expected {root_tag} KiCad document')
    return node


def parts(node, name):
    return [p for p in node[1:] if isinstance(p, list) and p and p[0] == name]


def one(node, name):
    return next((p for p in node[1:] if isinstance(p, list) and p and p[0] == name), [])


def val(node, n=1, default=''):
    return node[n] if len(node) > n and not isinstance(node[n], list) else default


def xy(node, default=(0.0, 0.0)):
    try:
        return float(node[1]), float(node[2])
    except (IndexError, ValueError, TypeError):
        return default


def number(node, index=1, default=0.0):
    try:
        return float(node[index])
    except (IndexError, TypeError, ValueError):
        return default


def prop(node, name):
    for entry in parts(node, 'property'):
        if val(entry) == name:
            return val(entry, 2)
    return ''


def poly_points(node):
    return [xy(p) for p in parts(one(node, 'pts'), 'xy')]


def transform(xy_point, origin, degrees=0, y_up=True):
    """Map KiCad local symbol/footprint coordinates into sheet/board mm."""
    x, y = xy_point
    a = math.radians(degrees)
    if y_up:
        return (origin[0] + x*math.cos(a) - y*math.sin(a),
                origin[1] - (x*math.sin(a) + y*math.cos(a)))
    # Board coordinates have Y down; KiCad positive angles are counterclockwise.
    return (origin[0] + x*math.cos(a) + y*math.sin(a),
            origin[1] - x*math.sin(a) + y*math.cos(a))


def schematic(path):
    document = read(path, 'kicad_sch')
    defs = {}
    for lib in parts(document, 'lib_symbols'):
        for symbol in parts(lib, 'symbol'):
            defs[val(symbol)] = symbol
    output = {'kind': 'schematic', 'file': str(path), 'wires': [], 'junctions': [],
              'labels': [], 'symbols': [], 'missing_symbols': 0}
    for item in document[1:]:
        if not isinstance(item, list) or not item:
            continue
        typ = item[0]
        if typ in ('wire', 'polyline'):
            points = poly_points(item)
            if len(points) >= 2:
                output['wires'].append(points)
        elif typ in ('junction', 'no_connect'):
            output['junctions'].append((typ, xy(one(item, 'at'))))
        elif typ in ('label', 'global_label', 'hierarchical_label', 'text'):
            output['labels'].append((val(item), xy(one(item, 'at')), typ))
        elif typ == 'symbol':
            lib_id = val(one(item, 'lib_id'))
            shape = defs.get(lib_id)
            if shape is None:
                output['missing_symbols'] += 1
            at = one(item, 'at')
            origin, angle = xy(at), number(at, 3)
            # KiCad sheet units are mm; symbol definitions have Y positive up.
            primitive = {'origin': origin, 'rotation': angle, 'ref': prop(item, 'Reference'),
                         'value': prop(item, 'Value'), 'lib_id': lib_id,'native_uuid':val(one(item,'uuid')),
                         'rectangles': [], 'circles': [], 'lines': [], 'pins': [], 'arcs': []}
            if shape:
                for sub in parts(shape, 'symbol'):
                    for el in sub[1:]:
                        if not isinstance(el, list) or not el:
                            continue
                        tag = el[0]
                        if tag == 'rectangle':
                            primitive['rectangles'].append((transform(xy(one(el, 'start')), origin, angle),
                                                             transform(xy(one(el, 'end')), origin, angle)))
                        elif tag == 'circle':
                            primitive['circles'].append((transform(xy(one(el, 'center')), origin, angle),
                                                          number(one(el, 'radius'))))
                        elif tag == 'polyline':
                            points = poly_points(el)
                            if len(points) >= 2:
                                primitive['lines'].append([transform(p, origin, angle) for p in points])
                        elif tag == 'pin':
                            ap = one(el, 'at')
                            local = xy(ap)
                            endangle = math.radians(number(ap, 3))
                            length = number(one(el, 'length'))
                            terminal = (local[0] + length*math.cos(endangle),
                                        local[1] + length*math.sin(endangle))
                            primitive['pins'].append((transform(local, origin, angle),
                                                       transform(terminal, origin, angle)))
            output['symbols'].append(primitive)
    return output


def pcb(path):
    document = read(path, 'kicad_pcb')
    output = {'kind': 'pcb', 'file': str(path), 'tracks': [], 'vias': [], 'pads': [],
              'graphics': [], 'refs': [], 'layers': [], 'zones_omitted': 0, 'pad_shapes': [], 'unsupported_pads': 0}
    for layers in parts(document, 'layers'):
        output['layers'] = [val(x, 1) for x in layers[1:] if isinstance(x, list) and len(x) >= 3
                            and x[1].endswith(('.Cu', '.SilkS', '.Cuts'))]
    for item in document[1:]:
        if not isinstance(item, list) or not item:
            continue
        tag = item[0]
        if tag == 'segment':
            output['tracks'].append((xy(one(item, 'start')), xy(one(item, 'end')),
                                     number(one(item, 'width'), default=0.2), val(one(item, 'layer'))))
        elif tag == 'via':
            output['vias'].append((xy(one(item, 'at')), number(one(item, 'size'), default=0.7)))
        elif tag == 'zone':
            output['zones_omitted'] += 1
        elif tag in ('gr_line', 'gr_arc', 'gr_rect', 'gr_circle'):
            layer = val(one(item, 'layer'), default='Dwgs.User')
            if tag in ('gr_line', 'gr_rect', 'gr_arc'):
                output['graphics'].append((tag, xy(one(item, 'start')),
                                           xy(one(item, 'end')),
                                           xy(one(item, 'mid')), layer))
            else:
                output['graphics'].append((tag, xy(one(item, 'center')),
                                           xy(one(item, 'end')), (0,0), layer))
        elif tag == 'footprint':
            at = one(item, 'at')
            origin, angle = xy(at), number(at, 3)
            ref = prop(item, 'Reference')
            if not ref:
                for label in parts(item, 'fp_text'):
                    if val(label) == 'reference':
                        ref = val(label, 2)
            output['refs'].append((origin, ref))
            for pad in parts(item, 'pad'):
                p = one(pad, 'at')
                center = transform(xy(p), origin, angle, y_up=False)
                width, height = xy(one(pad, 'size'), (1.0, 1.0))
                layers = [p for p in one(pad, 'layers')[1:] if isinstance(p, str)]
                # Serialized pad orientation is board-absolute (KiCad parsePAD/SetOrientation).
                output['pads'].append((center, width, height, number(p, 3), layers, val(pad)))
                shape=val(pad,3)
                output['pad_shapes'].append((shape,number(one(pad,'roundrect_rratio'),default=.25)))
                if shape not in ('rect','circle','oval','roundrect'):output['unsupported_pads']+=1
    return output



def arc_points(start, mid, end, segments=64):
    """Sample a circle through three points, choosing the sweep through mid."""
    ax,ay=start;bx,by=mid;cx,cy=end
    d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
    if abs(d)<1e-10:return [start,mid,end]
    aa=ax*ax+ay*ay;bb=bx*bx+by*by;cc=cx*cx+cy*cy
    ox=(aa*(by-cy)+bb*(cy-ay)+cc*(ay-by))/d
    oy=(aa*(cx-bx)+bb*(ax-cx)+cc*(bx-ax))/d
    radius=math.hypot(ax-ox,ay-oy)
    a,b,c=[math.atan2(y-oy,x-ox) for x,y in (start,mid,end)]
    sweep=(c-a)%(2*math.pi)
    if (b-a)%(2*math.pi)>sweep:sweep-=2*math.pi
    return [(ox+radius*math.cos(a+sweep*i/segments),oy+radius*math.sin(a+sweep*i/segments))
            for i in range(segments+1)]
