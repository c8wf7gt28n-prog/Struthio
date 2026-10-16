#!/usr/bin/env python3
"""ARC-1 Compact R10 -- native KiCad PCB generator (first placement, unrouted) from board/r10_board_plan.json.

What it does (owner handoff rev 1.1 s4/s5):
  * loads every footprint from the KiCad 9 libraries / ARC1_R10.pretty and assigns every pad its schematic net;
  * 6 copper layers, design rules for 0.8 mm BGA / 0.35 mm QFN fan-out, net classes for USB 90 ohm, TMDS 100 ohm,
    RGMII / SDRAM 50 ohm single-ended, power;
  * outline: a circle whose diameter is DERIVED from the placement, with two straight flats (rear: USB-C + HDMI,
    front: 2x USB-A) so the connector faces are planar; the case wall stays circular with openings at the flats;
  * functional placement: one block per schematic sheet (ICs first, their passives packed beside them), blocks placed
    greedily from the centre outwards inside the circle, connectors fixed at the flats with their mating faces flush
    with the board edge (0.5 mm overhang);
  * internal GND planes on In1/In4 (unfilled outlines), keep-out notes for the plug insertion envelopes.
It does NOT route the board. Output: cad/ARC1_R10.kicad_pcb (next to the schematic) and cad/pcb/placement.json.
Usage: gen_pcb.py <R10_WORK dir>
"""
import json
import math
import os
import sys

import pcbnew

R10 = os.path.abspath(sys.argv[1])
CAD = os.path.join(R10, "cad")
STD = os.environ.get("KICAD_FOOTPRINTS", "/usr/share/kicad/footprints")
plan = json.load(open(os.path.join(R10, "board", "r10_board_plan.json")))
MM = pcbnew.FromMM
GAP = 0.4                          # courtyard-to-courtyard spacing inside blocks (mm)
BLOCK_GAP = 1.2                    # between blocks (routing channels)
EDGE_KEEP = 1.5                    # copper/parts keep-in from the outline
OVERHANG = 0.5                     # connector face beyond the board edge


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    path = os.path.join(CAD, "symbols-and-footprints", "ARC1_R10.pretty") if lib == "ARC1_R10" else \
        os.path.join(STD, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def cy_box(fp):
    """courtyard bbox (mm, relative to the footprint position); falls back to the pad bbox"""
    sh = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = sh.BBox() if sh.OutlineCount() else fp.GetBoundingBox(False)
    pos = fp.GetPosition()
    return ((bb.GetX() - pos.x) / 1e6, (bb.GetY() - pos.y) / 1e6, (bb.GetRight() - pos.x) / 1e6, (bb.GetBottom() - pos.y) / 1e6)


board = pcbnew.BOARD()
board.SetCopperLayerCount(6)
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = MM(0.09)
ds.m_MinClearance = MM(0.09)
ds.m_ViasMinSize = MM(0.4)
ds.m_MinThroughDrill = MM(0.2)
ds.m_CopperEdgeClearance = MM(0.3)
ds.m_HoleToHoleMin = MM(0.25)

nets = {}
for n in sorted(plan["nets"]):
    ni = pcbnew.NETINFO_ITEM(board, n)
    board.Add(ni)
    nets[n] = ni

# net classes (impedance targets are for the fabricator's stack-up calculation; widths here are placeholders)
classes = {
    "POWER": (0.30, 0.10, None, None, lambda n: n in ("GND",) or n.startswith(("1V", "2V5", "3V3", "VBUS", "VDD", "HDMI_5V",
                                                                                "USBA1_VBUS", "USBA2_VBUS"))),
    "USB_90R_DIFF": (0.12, 0.12, 0.12, 0.15, lambda n: n.endswith(("_DP", "_DM"))),
    "TMDS_100R_DIFF": (0.10, 0.12, 0.10, 0.20, lambda n: n.startswith("TMDS_")),
    "RGMII_50R": (0.11, 0.15, None, None, lambda n: n.startswith(("G_", "ETH_"))),
    "SDRAM_50R": (0.11, 0.12, None, None, lambda n: n.startswith("SDR_")),
}
nc_settings = ds.m_NetSettings
_def = nc_settings.GetDefaultNetclass()
_def.SetClearance(MM(0.1)); _def.SetTrackWidth(MM(0.1)); _def.SetViaDiameter(MM(0.45)); _def.SetViaDrill(MM(0.2))
for cname, (w, clr, dpw, dpg, match) in classes.items():
    nc = pcbnew.NETCLASS(cname)
    nc.SetTrackWidth(MM(w)); nc.SetClearance(MM(clr))
    if dpw:
        nc.SetDiffPairWidth(MM(dpw)); nc.SetDiffPairGap(MM(dpg))
    nc_settings.SetNetclass(cname, nc)
    for n in nets:
        if match(n):
            nc_settings.SetNetclassPatternAssignment(n, cname)

# ------------------------------------------------------------------ footprints
fps = {}
for c in plan["components"]:
    if not c["footprint"]:
        continue
    fp = load_fp(c["footprint"])
    fp.SetReference(c["ref"]); fp.SetValue(c["value"])
    if c["dnp"]:
        fp.SetDNP(True)
    for pad in fp.Pads():
        num = pad.GetNumber()
        d = c["pins"].get(num)
        if d and d["net"]:
            pad.SetNet(nets[d["net"]])
    board.Add(fp)
    fps[c["ref"]] = (fp, c)

# ------------------------------------------------------------------ connectors (fixed, edge)
EXT = {c["ref"]: c for c in plan["components"] if c["note"].startswith(("FRONT", "REAR"))}


def orient_outward(fp, want):
    """rotate in 90 degree steps so that (courtyard centre - pad centroid) points along want (unit vector)"""
    best = None
    for a in (0, 90, 180, 270):
        fp.SetOrientationDegrees(a)
        x0, y0, x1, y1 = cy_box(fp)
        pads = [p.GetPosition() - fp.GetPosition() for p in fp.Pads() if p.GetNumber() not in ("", "SH", "S1", "5")]
        px = sum(p.x for p in pads) / len(pads) / 1e6; py = sum(p.y for p in pads) / len(pads) / 1e6
        v = ((x0 + x1) / 2 - px, (y0 + y1) / 2 - py)
        score = v[0] * want[0] + v[1] * want[1]
        if best is None or score > best[0]:
            best = (score, a)
    fp.SetOrientationDegrees(best[1])
    return best[1]


def conn_layout():
    """orient each edge connector outward; x positions side by side around x = 0; returns needed half chord"""
    lay, need = {}, 0.0
    # spacing between connector courtyards: rear 5 mm; front 11 mm -> ~28 mm USB-A pitch, room for a 22 mm wide
    # thumb drive beside a controller plug plus finger grip (handoff s1 "adequate plug/grip clearance")
    for face, want, gap in (("REAR", (0, -1), 5.0), ("FRONT", (0, 1), 11.0)):
        refs = sorted([r for r, c in EXT.items() if c["note"].startswith(face)], key=lambda r: EXT[r]["part"])
        widths = []
        for r in refs:
            fp = fps[r][0]
            orient_outward(fp, want)
            fp.SetPosition(pcbnew.VECTOR2I(0, 0))
            x0, y0, x1, y1 = cy_box(fp)
            widths.append((r, x0, x1, y0, y1))
        total = sum(x1 - x0 for _, x0, x1, _, _ in widths) + gap * (len(widths) - 1)
        x = -total / 2
        for r, x0, x1, y0, y1 in widths:
            lay[r] = (x - x0, want, (x0, y0, x1, y1))
            x += (x1 - x0) + gap
        need = max(need, total / 2 + 1.0)
    return lay, need


CONN, NEED_HALF = conn_layout()


def place_connectors(R, flat):
    occ = []
    for r, (x, want, (x0, y0, x1, y1)) in CONN.items():
        y = (-flat - OVERHANG - y0) if want[1] < 0 else (flat + OVERHANG - y1)
        fps[r][0].SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        occ.append((x + x0 - 1.0, y + y0 - 1.0, x + x1 + 1.0, y + y1 + 1.0))
    return occ


# ------------------------------------------------------------------ blocks (one per sheet)
PASSIVE = {"R0402", "R0603", "C0402", "C0603", "C0805", "C1210", "FB0603", "L4035", "F1812", "TP", "LED", "TVS_SMF",
           "SCHOTTKY", "PWR_FLAG", "PADS_1x2", "PADS_1x4", "MH", "FID"}


def has_tht(fp):
    return any(p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) for p in fp.Pads())


def pack_avoid(items, width, obstacles):
    """shelf packing that skips rectangles occupied by through-hole parts on the other side"""
    pos, x, y, rowh, W = {}, 0.0, 0.0, 0.0, 0.0
    for ref, w, h in items:
        while True:
            if x > 0 and x + w > width:
                x, y, rowh = 0.0, y + rowh + GAP, 0.0
            hit = [o for o in obstacles if not (x + w + GAP <= o[0] or x >= o[2] + GAP or y + h + GAP <= o[1] or y >= o[3] + GAP)]
            if not hit:
                break
            x = max(o[2] for o in hit) + GAP
            if x + w > width and x > 0:
                x, y, rowh = 0.0, y + max(rowh, 0.5) + GAP, 0.0
        pos[ref] = (x, y)
        x += w + GAP
        rowh = max(rowh, h)
        W = max(W, x)
    return pos, (W, y + rowh)


def pack(items, width):
    """shelf packing of (ref, w, h) -> {ref: (x, y)} top-left; returns placements and (W, H)"""
    pos, x, y, rowh, W = {}, 0.0, 0.0, 0.0, 0.0
    for ref, w, h in items:
        if x > 0 and x + w > width:
            x, y, rowh = 0.0, y + rowh + GAP, 0.0
        pos[ref] = (x, y)
        x += w + GAP
        rowh = max(rowh, h)
        W = max(W, x)
    return pos, (W, y + rowh)


BOTTOM = {"R0402", "R0603", "C0402", "C0603", "FB0603", "TP"}   # small passives + test pads on the bottom side
blocks = []
sheets = sorted({c["sheet"] for _, c in fps.values()})
for sh in sheets:
    refs = [r for r, (fp, c) in fps.items() if c["sheet"] == sh and r not in EXT and not r.startswith(("H", "FID"))]
    if not refs:
        continue
    for r in refs:
        fps[r][0].SetOrientationDegrees(0)
    dims = {}
    for r in refs:
        x0, y0, x1, y1 = cy_box(fps[r][0])
        dims[r] = (x1 - x0, y1 - y0, x0, y0)
    top = sorted([r for r in refs if fps[r][1]["part"] not in BOTTOM], key=lambda r: -dims[r][0] * dims[r][1])
    bot = sorted([r for r in refs if fps[r][1]["part"] in BOTTOM], key=lambda r: (fps[r][1]["part"], r))
    a_top = sum((dims[r][0] + GAP) * (dims[r][1] + GAP) for r in top)
    a_bot = sum((dims[r][0] + GAP) * (dims[r][1] + GAP) for r in bot)
    variants = []
    for f in (0.75, 1.0, 1.35):
        width = max([dims[r][0] + GAP for r in refs] + [math.sqrt(max(a_top, a_bot)) * f])
        pos_t, (Wt, Ht) = pack([(r, dims[r][0], dims[r][1]) for r in top], width)
        obst = [(pos_t[r][0], pos_t[r][1], pos_t[r][0] + dims[r][0], pos_t[r][1] + dims[r][1]) for r in top
                if has_tht(fps[r][0])]
        pos_b, (Wb, Hb) = pack_avoid([(r, dims[r][0], dims[r][1]) for r in bot], width, obst)
        pos = dict(pos_t); pos.update(pos_b)
        variants.append({"pos": pos, "W": max(Wt, Wb), "H": max(Ht, Hb)})
    blocks.append({"sheet": sh, "refs": refs, "dims": dims, "variants": variants, "bottom": set(bot),
                   "area": min(v["W"] * v["H"] for v in variants)})
blocks.sort(key=lambda b: -b["area"])


import random


# affinity: each block is pulled toward the connector or block it talks to most (short critical routes)
ANCHOR = {"video": "J:HDMI_A", "usb_host": "J:USB_A", "usb_power": "J:USB_C", "power": "J:USB_C",
          "f133": "B:usb_host", "emmc": "B:f133", "boot_nor": "B:f133", "fpga12": "B:f133", "psram12": "B:fpga12",
          "d213": "B:f133", "usb_link": "B:d213", "fpga45": "B:d213", "sdram45": "B:fpga45"}
HOLE_R = 0.78                       # mounting holes on a circle at 0.78 R, 45/135/225/315 degrees


def hole_xy(R):
    return [(HOLE_R * R * math.cos(math.radians(a)), HOLE_R * R * math.sin(math.radians(a))) for a in (45, 135, 225, 315)]


def try_place(R, order):
    if R <= NEED_HALF + 1:
        return None
    flat = math.sqrt(R * R - NEED_HALF * NEED_HALF)
    rects = place_connectors(R, flat)
    for hx, hy in hole_xy(R):
        rects.append((hx - 3.2, hy - 3.2, hx + 3.2, hy + 3.2))          # M2.5 pad + washer keep-out
    centers = {}
    for r, (x, want, (x0, y0, x1, y1)) in CONN.items():
        part = EXT[r]["part"]
        y = (-flat - OVERHANG - y0) if want[1] < 0 else (flat + OVERHANG - y1)
        centers.setdefault("J:" + part, []).append((x + (x0 + x1) / 2, y + (y0 + y1) / 2))
    lim = R - EDGE_KEEP
    pts = sorted(((x, y) for x in range(-int(R), int(R) + 1) for y in range(-int(R), int(R) + 1)
                  if math.hypot(x, y) < lim), key=lambda p: math.hypot(*p))
    g = BLOCK_GAP
    placed = []
    for b in order:
        a = ANCHOR.get(b["sheet"])
        anc = None
        if a and a in centers:
            xs = centers[a]
            anc = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs))
        best_c, done = None, None
        for (cx, cy) in pts:
            rr = math.hypot(cx, cy)
            if best_c is not None and rr * 0.5 > best_c:
                break
            for vi, v in enumerate(b["variants"]):
                w, h = v["W"], v["H"]
                x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
                if abs(y0) > flat - EDGE_KEEP or abs(y1) > flat - EDGE_KEEP:
                    continue
                if any(math.hypot(x, y) > lim for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))):
                    continue
                if not all(x1 + g <= a_ or x0 >= c + g or y1 + g <= bb or y0 >= d + g for (a_, bb, c, d) in rects):
                    continue
                cost = rr * 0.5 + (math.hypot(cx - anc[0], cy - anc[1]) if anc else rr)
                if best_c is None or cost < best_c:
                    best_c, done = cost, (x0, y0, vi)
        if not done:
            return None
        v = b["variants"][done[2]]
        rects.append((done[0], done[1], done[0] + v["W"], done[1] + v["H"]))
        centers["B:" + b["sheet"]] = [(done[0] + v["W"] / 2, done[1] + v["H"] / 2)]
        placed.append((b, done))
    return placed, flat


best = None
R = math.sqrt(sum(b["area"] for b in blocks) / math.pi) + NEED_HALF * 0.3
order = sorted(blocks, key=lambda b: -b["area"])
while best is None:
    best = try_place(R, order)
    if best is None:
        R += 1.0
        if R > 120:
            raise SystemExit("placement failed below 240 mm diameter")
placed, flat = best
place_connectors(R, flat)

for b, (bx, by, vi) in placed:
    for r in b["refs"]:
        w, h, x0, y0 = b["dims"][r]
        px, py = b["variants"][vi]["pos"][r]
        fp = fps[r][0]
        fp.SetPosition(pcbnew.VECTOR2I(MM(bx + px - x0), MM(by + py - y0)))
        if r in b["bottom"]:
            # flip about the courtyard centre so the part stays in its packed cell
            c = pcbnew.VECTOR2I(MM(bx + px + w / 2), MM(by + py + h / 2))
            fp.Flip(c, pcbnew.FLIP_DIRECTION_LEFT_RIGHT)

# mounting holes at the reserved positions (case bosses)
holes = [r for r in fps if fps[r][1]["part"] == "MH"]
for r, (hx, hy) in zip(sorted(holes), hole_xy(R)):
    fps[r][0].SetPosition(pcbnew.VECTOR2I(MM(hx), MM(hy)))
fids = [r for r in fps if fps[r][1]["part"] == "FID"]
for i, r in enumerate(sorted(fids)):
    a = math.radians(160 + 110 * i)
    fps[r][0].SetPosition(pcbnew.VECTOR2I(MM((R - 3) * math.cos(a)), MM((R - 3) * math.sin(a))))

# ------------------------------------------------------------------ outline: circle with two flats
half = math.sqrt(R * R - flat * flat)
ang = math.degrees(math.asin(flat / R))


def seg(x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); s.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetWidth(MM(0.1))
    board.Add(s)


def arc(a0, a1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts)
    am = (a0 + a1) / 2
    p = lambda a: pcbnew.VECTOR2I(MM(R * math.cos(math.radians(a))), MM(R * math.sin(math.radians(a))))
    s.SetArcGeometry(p(a0), p(am), p(a1)); s.SetWidth(MM(0.1))
    board.Add(s)


seg(-half, -flat, half, -flat)               # rear flat (top)
seg(-half, flat, half, flat)                 # front flat (bottom)
arc(-ang, ang)                               # right side: from top-right to bottom-right
arc(180 - ang, 180 + ang)                    # left side

# GND reference planes (outlines only; filled by the layout engineer)
for layer in (pcbnew.In1_Cu, pcbnew.In4_Cu):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(nets["GND"])
    pts = []
    for k in range(73):
        a = math.radians(k * 5)
        x, y = (R - 0.5) * math.cos(a), (R - 0.5) * math.sin(a)
        y = max(-flat + 0.5, min(flat - 0.5, y))
        pts.append(pcbnew.VECTOR2I(MM(x), MM(y)))
    z.AppendCorner(pts[0], -1)
    for p in pts[1:-1]:
        z.AppendCorner(p, 0)
    board.Add(z)

# insertion-envelope notes for the mechanical designer (User.Comments)
for r, c in EXT.items():
    fp = fps[r][0]
    t = pcbnew.PCB_TEXT(board); t.SetLayer(pcbnew.Cmts_User)
    t.SetText(f"{r} {c['part']} {c['note'].split('.')[0]}: plug insertion envelope keep-out in front of this face")
    t.SetPosition(fp.GetPosition()); t.SetTextSize(pcbnew.VECTOR2I(MM(1), MM(1)))
    board.Add(t)

# move the design from (0,0) to the centre of an A4 landscape sheet; set the drill/aux and grid origins to the board centre
OX, OY = 148.5, 105.0
shift = pcbnew.VECTOR2I(MM(OX), MM(OY))
for item in list(board.GetFootprints()) + list(board.GetDrawings()) + list(board.Zones()):
    item.Move(shift)
ds.SetAuxOrigin(shift); ds.SetGridOrigin(shift)
out = os.path.join(CAD, "ARC1_R10.kicad_pcb")
board.Save(out)
summary = {"diameter_mm": round(2 * R, 1), "flat_distance_from_centre_mm": round(flat, 2), "flat_chord_mm": round(2 * half, 1),
           "copper_layers": 6, "footprints": len(fps),
           "connectors": {r: {"part": c["part"], "face": c["note"].split(".")[0],
                              "x_mm": round(fps[r][0].GetPosition().x / 1e6 - OX, 2), "y_mm": round(fps[r][0].GetPosition().y / 1e6 - OY, 2),
                              "rot_deg": fps[r][0].GetOrientationDegrees()} for r, c in EXT.items()},
           "blocks": {b["sheet"]: {"x_mm": round(x, 1), "y_mm": round(y, 1), "w_mm": round(b["variants"][vi]["W"], 1),
                                   "h_mm": round(b["variants"][vi]["H"], 1)} for b, (x, y, vi) in placed}}
os.makedirs(os.path.join(CAD, "pcb"), exist_ok=True)
json.dump(summary, open(os.path.join(CAD, "pcb", "placement.json"), "w"), indent=1)
print(json.dumps({k: summary[k] for k in ("diameter_mm", "flat_chord_mm", "footprints")}))
