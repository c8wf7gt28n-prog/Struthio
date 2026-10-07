#!/usr/bin/env python3
"""Review images for R27: exact cross-sections and shaded views of PCB R22 + CASE R12 + ACRYLIC R2.

Sections are cut from the B-rep solids (not from meshes), so dimensions read off the
plots are the CAD dimensions. Shaded views use a small z-buffer rasteriser.

    python CHECKS/render_review.py        # writes CHECKS/renders/*.png
"""
from pathlib import Path
import contextlib, io, math, runpy, sys

import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'CHECKS' / 'renders'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'CHECKS'))
sys.dont_write_bytecode = True   # keep CHECKS/ free of __pycache__
with contextlib.redirect_stdout(io.StringIO()):
    B = runpy.run_path(str(ROOT / 'LAYERS/02_CASE/build_r12.py'))
from convergence_check import pcb_items, pose  # noqa: E402

PCB_COLORS = {'board': '#1f8f4a', 'part': '#3a3f46', 'plunger': '#c84b1e'}


def items(pressed=None):
    out = []
    for it in pcb_items(B):
        out.append((it['name'], it['solid'], PCB_COLORS[it['kind']], 1.0))
    for it in B['PARTS']:
        s = it['solid'].val() if hasattr(it['solid'], 'val') else it['solid']
        if pressed and it['kind'] == 'moving':
            s = pose(dict(it, solid=s), pressed, B)
        a = 0.45 if it['kind'] == 'reserve' else (0.5 if it['group'] in ('acrylic', 'lens') else 1.0)
        out.append((it['name'], s, it['color'], a))
    return out


def section(title, fname, axis, value, uv, window, pressed=None, notes=()):
    """axis: 'x' or 'y' plane; uv: which world axes map to the plot (e.g. ('y','z'))."""
    n = {'x': cq.Vector(1, 0, 0), 'y': cq.Vector(0, 1, 0)}[axis]
    origin = {'x': cq.Vector(value, 0, 0), 'y': cq.Vector(0, value, 0)}[axis]
    plane = cq.Face.makePlane(400, 400, basePnt=origin, dir=n)
    idx = {'x': 0, 'y': 1, 'z': 2}
    fig, ax = plt.subplots(figsize=(12, 7.2), dpi=150)
    ax.set_facecolor('#0b1012'); fig.patch.set_facecolor('#0b1012')
    legend = {}
    for name, s, col, alpha in items(pressed):
        bb = s.BoundingBox()
        lo = {'x': bb.xmin, 'y': bb.ymin}[axis]; hi = {'x': bb.xmax, 'y': bb.ymax}[axis]
        if value < lo - 1e-6 or value > hi + 1e-6:
            continue
        try:
            sec = s.intersect(plane)
        except Exception:
            continue
        polys = []
        for f in sec.Faces():
            vs, tris = f.tessellate(0.02)
            P = np.array([[v.x, v.y, v.z] for v in vs])
            for t in tris:
                polys.append(P[list(t)][:, [idx[uv[0]], idx[uv[1]]]])
        if polys:
            ax.add_collection(PolyCollection(polys, facecolors=col, edgecolors=col, linewidths=0.2, alpha=alpha))
            key = name.split(' · ')[0][:34]
            legend.setdefault(key, col)
    ax.set_xlim(window[0], window[1]); ax.set_ylim(window[2], window[3]); ax.set_aspect('equal')
    ax.tick_params(colors='#9aa3a8', labelsize=7)
    for sp in ax.spines.values():
        sp.set_color('#33424a')
    ax.grid(True, color='#1d2a30', lw=0.5)
    ax.set_xlabel(f'{uv[0].upper()} (mm)', color='#9aa3a8', fontsize=8); ax.set_ylabel(f'{uv[1].upper()} (mm, +front)', color='#9aa3a8', fontsize=8)
    ax.set_title(title, color='#e7be68', fontsize=10, loc='left')
    handles = [plt.Line2D([0], [0], marker='s', color='none', markerfacecolor=c, markersize=7, label=k) for k, c in list(legend.items())[:16]]
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1.01, 1.0), fontsize=6.5, frameon=False, labelcolor='#c9d1d5')
    for i, t in enumerate(notes):
        ax.text(0.01, 0.02 + 0.045 * i, t, transform=ax.transAxes, color='#9aa3a8', fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / fname, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------------------
# Shaded views (z-buffer)
# ---------------------------------------------------------------------------
def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i+2], 16) for i in (0, 2, 4)], float) / 255


def raster(fname, yaw, pitch, explode=0.0, size=(1400, 1700), exclude=(), title=''):
    W, H = size
    tris_all, cols, alphas = [], [], []
    off = {'acrylic': 1.0, 'controls': 0.9, 'shell': 0.75, 'lens': 0.62, 'display': 0.55, 'routes': 0.2,
           'battery': -0.55, 'speakers': -0.34, 'rear': -0.9}
    groups = {it['name']: it['group'] for it in B['PARTS']}
    for name, s, col, alpha in items():
        if any(e in name for e in exclude):
            continue
        vs, ts = s.tessellate(0.15, 0.3)
        V = np.array([[v.x, v.y, v.z] for v in vs])
        dz = off.get(groups.get(name, ''), 0.0) * explode     # PCB items have no CASE group and stay at 0
        V[:, 2] += dz
        T = np.array(ts)
        if len(T):
            tris_all.append(V[T]); cols += [hexrgb(col)] * len(T); alphas += [alpha] * len(T)
    T = np.concatenate(tris_all)
    C = np.array(cols); A = np.array(alphas)
    # Camera: device coords X right, Y down, Z front. Convert to a right-handed view.
    P = T.copy(); P[..., 1] *= -1
    cy, sy = math.cos(yaw), math.sin(yaw); cp, sp = math.cos(pitch), math.sin(pitch)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    R = Rx @ Ry
    Q = P @ R.T
    nrm = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]); ln = np.linalg.norm(nrm, axis=1) + 1e-12; nrm /= ln[:, None]
    light = np.array([0.35, 0.55, 0.76]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(nrm @ light)
    xy = Q[..., :2]; mn = xy.reshape(-1, 2).min(0); mx = xy.reshape(-1, 2).max(0)
    sc = 0.92 * min(W / (mx[0] - mn[0]), H / (mx[1] - mn[1]))
    cx = (W - sc * (mx[0] - mn[0])) / 2; cyy = (H - sc * (mx[1] - mn[1])) / 2
    sx = (xy[..., 0] - mn[0]) * sc + cx; sy_ = H - ((xy[..., 1] - mn[1]) * sc + cyy)
    zb = np.full((H, W), -1e9); img = np.zeros((H, W, 3)); img[:] = hexrgb('#0b1012')
    depth = Q[..., 2]
    order = np.argsort(A)[::-1]      # opaque first, translucent last
    for i in order:
        x0, x1 = int(max(0, math.floor(sx[i].min()))), int(min(W - 1, math.ceil(sx[i].max())))
        y0, y1 = int(max(0, math.floor(sy_[i].min()))), int(min(H - 1, math.ceil(sy_[i].max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax_, ay), (bx, by), (cx_, cy_) = zip(sx[i], sy_[i])
        d = (by - cy_) * (ax_ - cx_) + (cx_ - bx) * (ay - cy_)
        if abs(d) < 1e-12:
            continue
        w0 = ((by - cy_) * (gx - cx_) + (cx_ - bx) * (gy - cy_)) / d
        w1 = ((cy_ - ay) * (gx - cx_) + (ax_ - cx_) * (gy - cy_)) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        z = w0 * depth[i, 0] + w1 * depth[i, 1] + w2 * depth[i, 2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        upd = m & (z > sub)
        if A[i] >= 0.99:
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = C[i] * shade[i]
        else:
            region = img[y0:y1 + 1, x0:x1 + 1]
            region[upd] = region[upd] * (1 - A[i] * 0.6) + C[i] * shade[i] * A[i] * 0.6
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if title:
        from PIL import ImageDraw
        ImageDraw.Draw(im).text((24, 20), title, fill=(231, 190, 104))
    im.save(OUT / fname)


if __name__ == '__main__':
    P = B['P']
    section('A · flap control section at X = 40.75 (SW2), rest', 'SECTION_A_FLAP_REST.png', 'x', 40.75, ('y', 'z'), (84, 136, -7, 11),
            notes=[f'cap nub {P["pregap"]} mm above D2LS FP; stop legs {B["STROKE"]:.2f} mm above board', 'retention flange Ø17.8 under the 2.0 mm plate'])
    section('A′ · flap control section at X = 40.75 (SW2), pressed to the stop', 'SECTION_A_FLAP_PRESSED.png', 'x', 40.75, ('y', 'z'), (84, 136, -7, 11), pressed='press',
            notes=['legs on the board; plunger driven past OP by the design overtravel'])
    section('B · DART row section at Y = 119.296, rest', 'SECTION_B_DART_REST.png', 'y', 119.296, ('x', 'z'), (-32, 32, -7, 11),
            notes=['FPC extension runs on the board between SW3 and SW4, wraps the tab, returns on the back to J1'])
    section('B′ · DART row section at Y = 119.296, right side pressed', 'SECTION_B_DART_RIGHT.png', 'y', 119.296, ('x', 'z'), (-32, 32, -7, 11), pressed='press_right')
    section('C · centre section at X = 0 (USB-C, battery, FPC wrap)', 'SECTION_C_CENTRE_X0.png', 'x', 0.0, ('y', 'z'), (-2, 136, -7, 11))
    section('D · speaker chamber section at X = 38.3', 'SECTION_D_SPEAKER.png', 'x', 38.3, ('y', 'z'), (108, 136, -7, 11))
    section('E · shoulder section at Y = 84 (board clamp, wall)', 'SECTION_E_SHOULDER_Y84.png', 'y', 84.0, ('x', 'z'), (-54, 54, -7, 11))
    section('F · lap joint and display stack at X = 20 (top edge, zoom)', 'SECTION_F_LAP_DISPLAY.png', 'x', 20.0, ('y', 'z'), (-1, 9, 3.5, 8.5),
            notes=[f'lap: {P["lap_clear"]:.2f} mm radial clearance, {P["lap_tape"]:.2f} mm tape seat', f'display tape frame {P["lcd_tape"]:.2f} mm: module to ledge and lens'])
    raster('VIEW_FRONT_ISO.png', yaw=-0.55, pitch=0.62, title='R27 · PCB R22 + CASE R12 + ACRYLIC R2 · assembled')
    raster('VIEW_EXPLODED.png', yaw=-0.55, pitch=0.42, explode=9.0, title='R27 · exploded (film, controls, front shell, lens, tape, LCD, routes, PCB, battery, speakers, rear)')
    raster('VIEW_REAR_ISO.png', yaw=math.pi + 0.5, pitch=0.5, title='R27 · rear: power plunger, RESET / BOOT pinholes, USB-C relief')
    raster('VIEW_INTERNALS.png', yaw=-0.55, pitch=0.62, exclude=('FRONT SHELL', 'FACE FILM', 'LENS', 'LCD', 'DISPLAY TAPE', 'FLAP CAP', 'DART ROCKER'),
           title='R27 · front shell, film, screen and controls hidden')
    print('renders written to', OUT)
