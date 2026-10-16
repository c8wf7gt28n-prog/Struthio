#!/usr/bin/env python3
"""Emit the ARC-1 Compact R10 KiCad project from design.py (writer copied from R85C_WORK/cad/gen, frozen).

Outputs (in R10_WORK/cad/):
  ARC1_R10.kicad_pro, ARC1_R10.kicad_sch (root) + one .kicad_sch per sheet,
  symbols-and-footprints/ARC1_R10.kicad_sym, symbols-and-footprints/ARC1_R10.pretty/,
  sym-lib-table, fp-lib-table, ../board/r10_board_plan.json

Connectivity: every connected pin gets a global label at its electrical end
point; every intentionally unconnected pin gets a no-connect flag. Deterministic
UUIDs (uuid5) make the output reproducible byte-for-byte.
"""
import json
import math
import os
import re
import shutil
import sys
import uuid

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import PARTS            # noqa: E402
from design import build           # noqa: E402

CAD = os.path.normpath(os.path.join(HERE, ".."))
SF = os.path.join(CAD, "symbols-and-footprints")
PRETTY = os.path.join(SF, "ARC1_R10.pretty")
LIB = "ARC1_R10"
PROJ = "ARC1_R10"
NS = uuid.UUID("6a1c0de8-1010-4a8c-9a1e-ad5c0de0a110")
GRID = 2.54
VERSION = "20231120"
SLIM4_PRETTY = os.environ.get("SLIM4_PRETTY", "")


def U(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


def q(s):
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + s + '"'


def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


FONT = "(effects (font (size 1.27 1.27)))"
FONT_HIDE = "(effects (font (size 1.27 1.27)) (hide yes))"


# ------------------------------------------------------------------ symbol geometry
class SymGeo:
    def __init__(self, part):
        self.part = part
        self.pins = {}     # number -> (x, y, angle, side)
        p = part
        if p.key == "PWR_FLAG":
            self.pins["1"] = (0.0, 0.0, 90, "B")
            self.box = (-1.27, 2.54, 1.27, 0)
            return
        if p.small:
            if len(p.pins) == 2:
                self.pins[p.pins[0][0]] = (-3.81, 0.0, 0, "L")
                self.pins[p.pins[1][0]] = (3.81, 0.0, 180, "R")
                self.box = (-2.54, 1.016, 2.54, -1.016)
            elif len(p.pins) == 1:
                self.pins[p.pins[0][0]] = (-2.54, 0.0, 0, "L")
                self.box = (-1.27, 1.27, 1.27, -1.27)
            else:
                self.box = (-1.27, 1.27, 1.27, -1.27)
            return
        left = [x for x in p.pins if x[3] == "L"]
        right = [x for x in p.pins if x[3] == "R"]
        n = max(len(left), len(right))
        ln = max([len(x[1]) for x in left] + [1])
        rn = max([len(x[1]) for x in right] + [1])
        w = max(15.24, (ln + rn) * 1.27 * 0.75 + 7.62)
        w = math.ceil(w / (2 * GRID)) * 2 * GRID
        top = math.ceil((n - 1) / 2) * GRID
        for i, x in enumerate(left):
            self.pins[x[0]] = (-w / 2 - GRID, top - i * GRID, 0, "L")
        for i, x in enumerate(right):
            self.pins[x[0]] = (w / 2 + GRID, top - i * GRID, 180, "R")
        self.box = (-w / 2, top + GRID, w / 2, top - n * GRID)

    def size(self):
        x0, y0, x1, y1 = self.box
        return (x1 - x0, y0 - y1)


def lib_symbol(part, geo, prefixed):
    name = (LIB + ":" if prefixed else "") + part.key
    base = part.key
    out = [f"(symbol {q(name)}"]
    if part.key == "PWR_FLAG":
        out.append("(power)")
    if part.small or part.key == "PWR_FLAG":
        out.append("(pin_numbers (hide yes)) (pin_names (offset 0) (hide yes))")
    else:
        out.append("(pin_names (offset 0.508))")
    inbom = "no" if part.key == "PWR_FLAG" else "yes"
    out.append(f"(exclude_from_sim no) (in_bom {inbom}) (on_board {'no' if part.key == 'PWR_FLAG' else 'yes'})")
    x0, y0, x1, y1 = geo.box
    out.append(f"(property \"Reference\" {q(part.prefix)} (at {f(x0)} {f(y0 + 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left)))")
    out.append(f"(property \"Value\" {q(part.value)} (at {f(x0)} {f(y1 - 1.27)} 0) (effects (font (size 1.27 1.27)) (justify left)))")
    out.append(f"(property \"Footprint\" {q(part.fp)} (at 0 0 0) {FONT_HIDE})")
    out.append(f"(property \"Datasheet\" {q(part.datasheet)} (at 0 0 0) {FONT_HIDE})")
    out.append(f"(property \"Description\" {q(part.desc)} (at 0 0 0) {FONT_HIDE})")
    gfx = []
    if part.key == "PWR_FLAG":
        gfx.append("(polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.016 1.905) (xy 0 2.54) (xy 1.016 1.905) (xy 0 1.27)) "
                   "(stroke (width 0) (type default)) (fill (type none)))")
    elif part.small and len(part.pins) <= 1:
        gfx.append("(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))")
    else:
        gfx.append(f"(rectangle (start {f(x0)} {f(y0)}) (end {f(x1)} {f(y1)}) (stroke (width 0.254) (type default)) "
                   f"(fill (type {'none' if part.small else 'background'})))")
    out.append(f"(symbol {q(base + '_0_1')} " + " ".join(gfx) + ")")
    pins = []
    for num, nm, et, side in part.pins:
        x, y, a, s = geo.pins[num]
        ln = 0 if part.key == "PWR_FLAG" else (1.27 if part.small else GRID)
        pins.append(f"(pin {et} line (at {f(x)} {f(y)} {a}) (length {f(ln)}) (name {q(nm)} {FONT}) (number {q(num)} {FONT}))")
    out.append(f"(symbol {q(base + '_1_1')} " + " ".join(pins) + ")")
    out.append(")")
    return " ".join(out)


# ------------------------------------------------------------------ schematic pieces
def label(net, x, y, side, key):
    ang, just = (180, "right") if side == "L" else (0, "left") if side == "R" else (270, "right")
    return (f"(global_label {q(net)} (shape passive) (at {f(x)} {f(y)} {ang}) (fields_autoplaced yes) "
            f"(effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(U('gl', key))}) "
            f"(property \"Intersheetrefs\" \"${{INTERSHEET_REFS}}\" (at {f(x)} {f(y)} 0) {FONT_HIDE}))")


def text_note(s, x, y, key):
    return f"(text {q(s)} (exclude_from_sim no) (at {f(x)} {f(y)} 0) (effects (font (size 2 2)) (justify left)) (uuid {q(U('tx', key))}))"


def comp_instance(c, geo, X, Y, root_uuid, sheet_uuid):
    p = PARTS[c.part]
    x0, y0, x1, y1 = geo.box
    fields = [
        ("Reference", c.ref, X + x0, Y - y0 - 1.27, False),
        ("Value", c.value, X + x0, Y - y1 + 1.27, False),
        ("Footprint", p.fp, X, Y, True),
        ("Datasheet", p.datasheet, X, Y, True),
        ("Description", p.desc, X, Y, True),
        ("MPN", c.mpn, X, Y, True),
        ("Manufacturer", c.mfr, X, Y, True),
        ("LCSC", c.lcsc or "", X, Y, True),
        ("Evidence", p.evidence, X, Y, True),
        ("Footprint_status", p.fp_status, X, Y, True),
        ("Note", c.note, X, Y, True),
        ("Source", p.src, X, Y, True),
        ("Reuse", "SLIM4_R26_BOM_LINE (re-validate)" if c.slim4 else "", X, Y, True),
    ]
    is_flag = c.part == "PWR_FLAG"
    out = [f"(symbol (lib_id {q(LIB + ':' + p.key)}) (at {f(X)} {f(Y)} 0) (unit 1) (exclude_from_sim no) "
           f"(in_bom {'no' if is_flag else 'yes'}) (on_board {'no' if is_flag else 'yes'}) (dnp {'yes' if c.dnp else 'no'}) "
           f"(uuid {q(U('sym', c.ref))})"]
    for k, v, x, y, hide in fields:
        eff = FONT_HIDE if hide else "(effects (font (size 1.27 1.27)) (justify left))"
        out.append(f"(property {q(k)} {q(v)} (at {f(x)} {f(y)} 0) {eff})")
    for num, *_ in p.pins:
        out.append(f"(pin {q(num)} (uuid {q(U('pin', c.ref, num))}))")
    out.append(f"(instances (project {q(PROJ)} (path {q('/' + root_uuid + '/' + sheet_uuid)} (reference {q(c.ref)}) (unit 1))))")
    out.append(")")
    return " ".join(out)


def place(comps, geos, width=760.0):
    """simple shelf packing; returns {ref: (X, Y)} and used extents"""
    pos = {}
    x, y, row_h = 30.0, 40.0, 0.0
    big = sorted([c for c in comps if not PARTS[c.part].small], key=lambda c: -geos[c.ref].size()[1])
    small = [c for c in comps if PARTS[c.part].small]
    maxx = 0.0
    for c in big + small:
        g = geos[c.ref]
        w, h = g.size()
        lab = 0 if c.part in ("PWR_FLAG", "FID", "MH_NPTH") else 34.0
        cw = w + 2 * lab + 10
        if x + cw > width and x > 30.0:
            x = 30.0
            y += row_h + 12.7
            row_h = 0.0
        X = round((x + lab - geos[c.ref].box[0]) / GRID) * GRID
        Y = round((y - (-geos[c.ref].box[1])) / GRID) * GRID + 0.0
        Y = round((y + geos[c.ref].box[1]) / GRID) * GRID
        pos[c.ref] = (X, Y)
        x += cw
        row_h = max(row_h, h + 10)
        maxx = max(maxx, x)
    return pos, max(maxx + 20, 420.0), y + row_h + 40


def sheet_file(d, sheet, root_uuid, sheet_uuid, title, page):
    comps = [c for c in d.comps if c.sheet == sheet]
    geos = {c.ref: SymGeo(PARTS[c.part]) for c in comps}
    pos, W, H = place(comps, geos)
    used = sorted({c.part for c in comps})
    body = [f"(kicad_sch (version {VERSION}) (generator \"arc1_r10_gen\") (generator_version \"8.0\") "
            f"(uuid {q(U('file', sheet))}) (paper \"User\" {f(math.ceil(W))} {f(math.ceil(H))})",
            f"(title_block (title {q('ARC-1 Compact R10: ' + title)}) (date \"2026-10-16\") (rev \"R10-draft\") "
            f"(company \"STRUTHIO ARC-1\") (comment 1 \"SELECTED_UNVERIFIED engineering capture - NOT released for fabrication\") "
            f"(comment 2 \"Generated by R10_WORK/cad/gen/gen_kicad.py from design.py - edit the source, not this file\"))",
            "(lib_symbols " + " ".join(lib_symbol(PARTS[k], SymGeo(PARTS[k]), True) for k in used) + ")"]
    body.append(text_note(f"{title}\nSheet generated from design.py; global labels carry every net.", 30, 20, sheet))
    for c in comps:
        g = geos[c.ref]
        X, Y = pos[c.ref]
        body.append(comp_instance(c, g, X, Y, root_uuid, sheet_uuid))
        p = PARTS[c.part]
        for num, nm, et, side in p.pins:
            px, py, a, s = g.pins[num]
            ex, ey = X + px, Y - py
            if num in c.conn:
                body.append(label(c.conn[num], ex, ey, s, (c.ref, num)))
            elif (c.ref, num) in d.intent_nc:
                body.append(f"(no_connect (at {f(ex)} {f(ey)}) (uuid {q(U('nc', c.ref, num))}))")
            else:
                raise SystemExit(f"pin {c.ref}.{num} ({nm}) neither connected nor declared no-connect")
    body.append(")")
    return "\n".join(body) + "\n"


def root_file(d, root_uuid):
    parts = [f"(kicad_sch (version {VERSION}) (generator \"arc1_r10_gen\") (generator_version \"8.0\") "
             f"(uuid {q(root_uuid)}) (paper \"A3\")",
             "(title_block (title \"ARC-1 Compact R10 - hierarchical root\") (date \"2026-10-16\") (rev \"R10-draft\") "
             "(comment 1 \"NOT approved for fabrication (HOLD). Bring-up prototype capture.\"))",
             "(lib_symbols)"]
    x, y = 25.4, 40.64
    for i, (name, fname, title) in enumerate(d.sheets):
        su = U("sheet", name)
        parts.append(f"(sheet (at {f(x)} {f(y)}) (size 76.2 20.32) (fields_autoplaced yes) (stroke (width 0.1524) (type solid)) "
                     f"(fill (color 0 0 0 0.0000)) (uuid {q(su)}) "
                     f"(property \"Sheetname\" {q(name)} (at {f(x)} {f(y - 0.7112)} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) "
                     f"(property \"Sheetfile\" {q(fname)} (at {f(x)} {f(y + 20.8788)} 0) (effects (font (size 1.27 1.27)) (justify left top))) "
                     f"(instances (project {q(PROJ)} (path {q('/' + root_uuid)} (page {q(str(i + 2))})))))")
        parts.append(text_note(title, x + 80, y + 10, "root" + name))
        y += 30.48
        if y > 250:
            y = 40.64
            x += 200
    parts.append("(sheet_instances (path \"/\" (page \"1\")))")
    parts.append(")")
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------------ footprints
def fp_header(name, descr, tags):
    return [f"(footprint {q(name)} (version 20240108) (generator \"arc1_r10_gen\") (generator_version \"8.0\") (layer \"F.Cu\")",
            f"(descr {q(descr)}) (tags {q(tags)}) (attr smd)",
            f"(property \"Reference\" \"REF**\" (at 0 -1 0) (layer \"F.SilkS\") (uuid {q(U('fpr', name))}) (effects (font (size 1 1) (thickness 0.15))))",
            f"(property \"Value\" {q(name)} (at 0 1 0) (layer \"F.Fab\") (uuid {q(U('fpv', name))}) (effects (font (size 1 1) (thickness 0.15))))"]


def rect_layer(name, layer, x0, y0, x1, y1, w=0.05):
    return (f"(fp_rect (start {f(x0)} {f(y0)}) (end {f(x1)} {f(y1)}) (stroke (width {f(w)}) (type solid)) (fill none) "
            f"(layer {q(layer)}) (uuid {q(U('fprect', name, layer))}))")


def gen_df40(path):
    name = "Hirose_DF40C-100DS-0.4V_51"
    L = fp_header(name, "Hirose DF40C-100DS-0.4V(51) receptacle, 1.5 mm stack. GENERATED_DERIVED from DF40 catalog land "
                        "pattern dims (0.4 pitch, 0.2 pad width, outer 3.78 / inner 2.38 mm -> 0.70 x 0.20 pads, rows 3.08 c-c). "
                        "Pin numbering: odd row / even row ASSUMED to mirror MN820 CN1 - verify with the Hirose drawing in R09",
                  "Hirose DF40 board-to-board 0.4mm R08")
    for i in range(1, 101):
        col = (i - 1) // 2
        x = (col - 24.5) * 0.4
        y = -1.54 if i % 2 == 1 else 1.54
        L.append(f"(pad {q(str(i))} smd rect (at {f(x)} {f(y)}) (size 0.2 0.7) (layers \"F.Cu\" \"F.Paste\" \"F.Mask\") "
                 f"(uuid {q(U('pad', name, i))}))")
    L.append(rect_layer(name, "F.Fab", -11.4, -2.2, 11.4, 2.2, 0.1))
    L.append(rect_layer(name, "F.CrtYd", -11.9, -2.7, 11.9, 2.7, 0.05))
    L.append(")")
    open(os.path.join(path, name + ".kicad_mod"), "w").write("\n".join(L) + "\n")


def gen_f133(path):
    src = "/usr/share/kicad/footprints/Package_QFP.pretty/LQFP-128_14x14mm_P0.4mm.kicad_mod"
    name = "Allwinner_F133_eLQFP128_14x14_P0.4_EP5.72"
    t = open(src).read()
    t = t.replace('(footprint "LQFP-128_14x14mm_P0.4mm"', f'(footprint {q(name)}', 1)
    t = re.sub(r'\(descr "[^"]*"\)', '(descr "F133 eLQFP128: KiCad LQFP-128_14x14mm_P0.4mm leads + exposed pad 129 = 5.72 x 5.72 mm '
               '(F133 DS rev 2.3 package D3/E3). GENERATED_DERIVED: lead land and EP paste pattern to be checked in R09")', t, count=1)
    ep = (f'\t(pad "129" smd rect (at 0 0) (size 5.72 5.72) (layers "F.Cu" "F.Mask") (uuid {q(U("ep", name))}))\n'
          + "".join(f'\t(pad "" smd rect (at {f(x)} {f(y)}) (size 1.15 1.15) (layers "F.Paste") (uuid {q(U("eppaste", name, x, y))}))\n'
                    for x in (-2.15, -0.72, 0.72, 2.15) for y in (-2.15, -0.72, 0.72, 2.15)))
    i = t.rstrip().rfind(")")
    t = t[:i] + ep + ")\n"
    open(os.path.join(path, name + ".kicad_mod"), "w").write(t)


def gen_d213(path):
    """D213EC QFN128 (D21x DS v1.4 Figure 5-6): D = E = 12.30, e = 0.35 (32 per side, Nd = Ne = 10.85), b = 0.13
    (0.08-0.18), L = 0.40 (0.35-0.45), exposed pad D2 = E2 = 7.00 centred (K = 2.25 REF). Pin 1 top of the left side,
    counter-clockwise (top view). Land: 0.18 x 0.60 mm (0.15 mm outward toe, 0.05 mm inward heel), pad gap 0.17 mm;
    exposed pad 7.0 mm copper + 3x3 paste windows (~50 %) + 5x5 thermal vias 0.3 mm. GENERATED_DERIVED: check against
    the vendor recommended land pattern (none published) and the fabricator's 0.35 mm-pitch capability."""
    name = "ArtInChip_QFN-128-1EP_12.3x12.3mm_P0.35mm_EP7.0x7.0mm"
    L = [f"(footprint {q(name)} (version 20240108) (generator \"arc1_r10_gen\") (generator_version \"8.0\") (layer \"F.Cu\")",
         f"(descr {q('D213EC QFN128 12.3x12.3 mm, 0.35 mm pitch, EP 7.0 mm; D21x DS v1.4 Fig 5-6. GENERATED_DERIVED')}) "
         f"(tags \"QFN 0.35 D213\") (attr smd)",
         f"(property \"Reference\" \"REF**\" (at 0 -7.5 0) (layer \"F.SilkS\") (uuid {q(U('fpr', name))}) (effects (font (size 1 1) (thickness 0.15))))",
         f"(property \"Value\" {q(name)} (at 0 7.5 0) (layer \"F.Fab\") (uuid {q(U('fpv', name))}) (effects (font (size 1 1) (thickness 0.15))))"]
    half, e, n = 6.15, 0.35, 32
    plen, pw = 0.60, 0.18                  # toe 0.15 mm beyond the edge, heel 0.05 mm inside the 0.40 mm lead (L nom)
    cx = half + 0.15 - plen / 2            # inner end at 5.70 mm keeps 0.185 mm to the corner pads of the next side
    for i in range(128):
        side, k = divmod(i, n)
        off = (k - (n - 1) / 2) * e
        if side == 0:   x, y, w, h = -cx, off, plen, pw          # left, top -> bottom
        elif side == 1: x, y, w, h = off, cx, pw, plen           # bottom, left -> right
        elif side == 2: x, y, w, h = cx, -off, plen, pw          # right, bottom -> top
        else:           x, y, w, h = -off, -cx, pw, plen         # top, right -> left
        L.append(f"(pad {q(str(i + 1))} smd roundrect (at {f(x)} {f(y)}) (size {f(w)} {f(h)}) (layers \"F.Cu\" \"F.Paste\" \"F.Mask\") "
                 f"(roundrect_rratio 0.25) (uuid {q(U('pad', name, i + 1))}))")
    L.append(f"(pad \"129\" smd rect (at 0 0) (size 7 7) (layers \"F.Cu\" \"F.Mask\") (uuid {q(U('ep', name))}))")
    for x in (-2.2, 0, 2.2):
        for y in (-2.2, 0, 2.2):
            L.append(f"(pad \"\" smd rect (at {f(x)} {f(y)}) (size 1.6 1.6) (layers \"F.Paste\") (uuid {q(U('epp', name, x, y))}))")
    for x in (-2.8, -1.4, 0, 1.4, 2.8):
        for y in (-2.8, -1.4, 0, 1.4, 2.8):
            L.append(f"(pad \"129\" thru_hole circle (at {f(x)} {f(y)}) (size 0.6 0.6) (drill 0.3) (layers \"*.Cu\") (uuid {q(U('via', name, x, y))}))")
    L.append(rect_layer(name, "F.Fab", -6.15, -6.15, 6.15, 6.15, 0.1))
    L.append(rect_layer(name, "F.CrtYd", -6.9, -6.9, 6.9, 6.9, 0.05))
    L.append(f"(fp_circle (center -6.6 -5.6) (end -6.45 -5.6) (stroke (width 0.15) (type solid)) (fill solid) (layer \"F.SilkS\") (uuid {q(U('pin1', name))}))")
    L.append(")")
    open(os.path.join(path, name + ".kicad_mod"), "w").write("\n".join(L) + "\n")


def copy_slim4(path):
    m = {"FP_U13": "SLIM4_FP_U13_TUSB320LAI_RWB_X2QFN12", "FP_U11": "SLIM4_FP_U11_TPD2EUSB30_DRT3", "FP_L2": "SLIM4_FP_L2_ASWPA4035"}
    for k, v in m.items():
        s = os.path.join(SLIM4_PRETTY, k + ".kicad_mod")
        dst = os.path.join(path, v + ".kicad_mod")
        if SLIM4_PRETTY and os.path.exists(s):
            t = open(s).read()
            t = t.replace(f'(footprint "{k}"', f'(footprint {q(v)}', 1)
            t = t.replace("(descr \"", "(descr \"SLIM4_CANDIDATE copied from SLIM4 R26 SLIM4.pretty/" + k +
                          ".kicad_mod unchanged except name; re-validate against the datasheet land pattern before use | ", 1)
            open(dst, "w").write(t)
        elif not os.path.exists(dst):
            raise SystemExit(f"SLIM4 footprint {k} missing (copied from R85C_WORK/cad/symbols-and-footprints/ARC1_R85.pretty)")


def main():
    d = build()
    root_uuid = U("root")
    os.makedirs(PRETTY, exist_ok=True)
    gen_f133(PRETTY); gen_d213(PRETTY); copy_slim4(PRETTY)
    # symbol library
    used = sorted({c.part for c in d.comps})
    lib = [f"(kicad_symbol_lib (version {VERSION}) (generator \"arc1_r10_gen\") (generator_version \"8.0\")"]
    lib += [lib_symbol(PARTS[k], SymGeo(PARTS[k]), False) for k in used]
    lib.append(")")
    open(os.path.join(SF, "ARC1_R10.kicad_sym"), "w").write("\n".join(lib) + "\n")
    open(os.path.join(CAD, "sym-lib-table"), "w").write(
        '(sym_lib_table (version 7)\n  (lib (name "ARC1_R10")(type "KiCad")(uri "${KIPRJMOD}/symbols-and-footprints/ARC1_R10.kicad_sym")(options "")(descr "ARC-1 R10 generated symbols"))\n)\n')
    open(os.path.join(CAD, "fp-lib-table"), "w").write(
        '(fp_lib_table (version 7)\n  (lib (name "ARC1_R10")(type "KiCad")(uri "${KIPRJMOD}/symbols-and-footprints/ARC1_R10.pretty")(options "")(descr "ARC-1 R10 generated / SLIM4-candidate footprints"))\n)\n')
    pro = {"meta": {"filename": PROJ + ".kicad_pro", "version": 1},
           "sheets": [[root_uuid, "Root"]] + [[U("sheet", n), n] for n, _, _ in d.sheets],
           "text_variables": {}}
    json.dump(pro, open(os.path.join(CAD, PROJ + ".kicad_pro"), "w"), indent=2)
    open(os.path.join(CAD, PROJ + ".kicad_sch"), "w").write(root_file(d, root_uuid))
    for i, (name, fname, title) in enumerate(d.sheets):
        open(os.path.join(CAD, fname), "w").write(sheet_file(d, name, root_uuid, U("sheet", name), title, i + 2))
    # machine-readable plan for checks
    nets = {}
    for c in d.comps:
        if c.part == "PWR_FLAG":
            continue
        for pin, net in c.conn.items():
            nets.setdefault(net, []).append(f"{c.ref}.{pin}")
    plan = {
        "schema_id": "arc1-r10-board-plan-v1", "revision": "R10-draft-1", "date": "2026-10-16",
        "status": "SELECTED_UNVERIFIED (native KiCad schematic generated; not reviewed, not laid out, not fabricated)",
        "sheets": [{"name": n, "file": fn, "title": t} for n, fn, t in d.sheets],
        "components": [{"ref": c.ref, "part": c.part, "value": c.value, "mpn": c.mpn, "manufacturer": c.mfr, "lcsc": c.lcsc,
                        "footprint": PARTS[c.part].fp, "footprint_status": PARTS[c.part].fp_status, "dnp": c.dnp,
                        "sheet": c.sheet, "note": c.note, "evidence": PARTS[c.part].evidence, "slim4_reuse": c.slim4,
                        "pins": {p[0]: {"name": p[1], "etype": p[2], "net": c.conn.get(p[0]),
                                        "nc_reason": d.intent_nc.get((c.ref, p[0]))} for p in PARTS[c.part].pins}}
                       for c in d.comps if c.part != "PWR_FLAG"],
        "nets": dict(sorted(nets.items())),
    }
    os.makedirs(os.path.join(CAD, "..", "board"), exist_ok=True)
    json.dump(plan, open(os.path.join(CAD, "..", "board", "r10_board_plan.json"), "w"), indent=1, sort_keys=False)
    print(f"generated {len(d.comps)} symbols on {len(d.sheets)} sheets, {len(nets)} nets")


if __name__ == "__main__":
    main()
