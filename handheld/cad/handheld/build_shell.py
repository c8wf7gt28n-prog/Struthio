#!/usr/bin/env python3
# STRUTHIO HANDHELD · builds the sculpted front and back shells.
# OpenSCAD 2021's CGAL needs tens of minutes for booleans on the curved skin,
# so the skin and the final booleans are done here with manifold3d; every
# dimension still comes from struthio_handheld.scad:
#   - OpenSCAD exports the core outline (shell_core2d) and the plain parts:
#     front_add / front_cut, back_add / back_cut, speaker_bore;
#   - the outer and inner skins are lofted here: the core outline grown
#     outward by the revolved side profiles (shell_prof_out / _in), which is
#     what the SCAD's minkowski() describes;
#   - front = (outer ∩ z<=FRONT_T) ∪ front_add − front_cut
#     back  = (outer ∩ z>=FRONT_T) − (inner − back_add) − back_cut − (bore ∩ inner)
#   python3 build_shell.py      (from cad/handheld; needs openscad, numpy, trimesh, manifold3d)
import math, os, re, subprocess, sys, tempfile
import numpy as np
import trimesh
import manifold3d as mf

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'struthio_handheld.scad')
P = {}
for line in open(SRC).read().splitlines():
    for stmt in line.split('//')[0].split(';'):
        m = re.match(r'\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+)$', stmt)
        if m:
            try: P[m.group(1)] = eval(m.group(2), {'__builtins__': {}}, P)
            except Exception: pass
if P.get('SHELL_STYLE') != 'sleek':
    sys.exit('SHELL_STYLE is not "sleek": export the slab style with openscad directly')

TMP = tempfile.mkdtemp(prefix='struthio_shell_')
def scad(part, ext):
    out = os.path.join(TMP, f'{part}.{ext}')
    subprocess.run(['openscad', '-q', '-o', out, '-D', f'part="{part}"', SRC], check=True)
    return out

def to_manifold(path):
    t = trimesh.load(path)
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))

def core_ring():
    """shell_core2d() as one closed ring, resampled every 0.4 mm, counter-clockwise"""
    t = open(scad('core2d', 'svg')).read()
    d = re.search(r'<path d="([^"]*)"', t, re.S).group(1)
    pts = np.array([[float(a), -float(b)] for a, b in re.findall(r'(-?[\d.]+),(-?[\d.]+)', d)])
    if np.allclose(pts[0], pts[-1]): pts = pts[:-1]
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    if area < 0: pts = pts[::-1]
    seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = int(s[-1] / 0.4)
    u = np.linspace(0, s[-1], n, endpoint=False)
    closed = np.vstack([pts, pts[:1]])
    ring = np.c_[np.interp(u, s, closed[:, 0]), np.interp(u, s, closed[:, 1])]
    # outward normals from a smoothed tangent
    tan = np.roll(ring, -2, 0) - np.roll(ring, 2, 0)
    tan /= np.linalg.norm(tan, axis=1)[:, None]
    normal = np.c_[tan[:, 1], -tan[:, 0]]           # right of the tangent = outward for CCW
    return ring, normal

def profile_out():
    rb, rf, zs, zb = P['SHELL_RB'], P['SHELL_RF'], P['SHELL_ZS'], P['SHELL_ZB']
    pts = [(rb - rf + rf * math.sin(math.radians(90 * i / 12)), rf - rf * math.cos(math.radians(90 * i / 12))) for i in range(13)]
    pts += [(rb * math.cos(math.radians(90 * i / 32)), zs + (zb - zs) * math.sin(math.radians(90 * i / 32))) for i in range(33)]
    return pts
def profile_in():
    rw, zs, zt = P['SHELL_RB'] - P['WALL'], P['SHELL_ZS'], P['SHELL_ZB'] - P['BACK_WALL']
    pts = [(rw, P['FRONT_T'] - 1.0)]
    pts += [(rw * math.cos(math.radians(90 * i / 32)), zs + (zt - zs) * math.sin(math.radians(90 * i / 32))) for i in range(33)]
    return pts

def loft(ring, normal, prof):
    """the core ring grown by r(z) at each profile station; capped top and bottom"""
    prof = [(r, z) for r, z in prof]
    n = len(ring)
    verts, faces = [], []
    for r, z in prof:
        verts.extend(np.c_[ring + r * normal, np.full(n, z)])
    m = len(prof)
    for j in range(m - 1):
        a, b = j * n, (j + 1) * n
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((a + i, a + i2, b + i2)); faces.append((a + i, b + i2, b + i))
    lo, hi = 0, (m - 1) * n
    # bottom and top caps, each triangulated from its own station ring
    for tri in mf.triangulate([ring + prof[0][0] * normal]):
        faces.append((lo + tri[0], lo + tri[2], lo + tri[1]))
    for tri in mf.triangulate([ring + prof[-1][0] * normal]):
        faces.append((hi + tri[0], hi + tri[1], hi + tri[2]))
    v = np.asarray(verts, np.float32); f = np.asarray(faces, np.uint32)
    man = mf.Manifold(mf.Mesh(vert_properties=v, tri_verts=f))
    if man.status() != mf.Error.NoError or man.volume() <= 0:
        sys.exit(f'loft failed: {man.status()}')
    return man

def slab(z0, z1):
    return mf.Manifold.cube([200, 240, z1 - z0]).translate([-100, -120, z0])

def write(man, path):
    # features that graze the curved skin leave zero-volume slivers: merge
    # near-coincident vertices, then keep the one real solid
    man = man.simplify(0.01)
    man = max(man.decompose(), key=lambda m: m.volume())
    mesh = man.to_mesh()
    trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts).export(path)

def main():
    ring, normal = core_ring()
    outer = loft(ring, normal, profile_out())
    inner = loft(ring, normal, profile_in())
    parts = {k: to_manifold(scad(k, 'stl')) for k in ('front_add', 'front_cut', 'back_add', 'back_cut', 'speaker_bore')}
    ft = P['FRONT_T']
    front = ((outer ^ slab(-1, ft)) + parts['front_add']) - parts['front_cut']
    # cavity = inner skin minus the features; carving it (rather than adding the
    # features to outer - inner) avoids pinched edges where a feature meets the skin
    cavity = inner - parts['back_add']
    back = ((outer ^ slab(ft, P['SHELL_ZB'] + 1)) - cavity) - parts['back_cut'] - (parts['speaker_bore'] ^ inner)
    os.makedirs(os.path.join(HERE, 'stl'), exist_ok=True)
    for name, man in (('front', front), ('back', back)):
        path = os.path.join(HERE, 'stl', f'struthio_{name}.stl')
        write(man, path)
        b = man.bounding_box()
        print(f'{name}: {man.volume()/1000:.1f} cm3, {b[3]-b[0]:.1f} x {b[4]-b[1]:.1f} x {b[5]-b[2]:.1f} mm -> {os.path.relpath(path, HERE)}')

if __name__ == '__main__':
    main()
