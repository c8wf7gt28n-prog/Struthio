"""Write every CASE R11 / ACRYLIC R1 interchange file and the viewer meshes.

Run after editing build_r11.py:
    python LAYERS/02_CASE/export_layer_formats.py
then re-run the cross-layer checks:
    python CHECKS/convergence_check.py
"""
from pathlib import Path
import contextlib, io, json, math, re, runpy
import cadquery as cq

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]
ACRYLIC = ROOT / 'LAYERS' / '03_ACRYLIC'
ASSEMBLY = ROOT / 'ASSEMBLY'
ACRYLIC.mkdir(parents=True, exist_ok=True)
ASSEMBLY.mkdir(parents=True, exist_ok=True)

with contextlib.redirect_stdout(io.StringIO()):
    B = runpy.run_path(str(CASE / 'build_r11.py'))
P, PARTS = B['P'], B['PARTS']


def val(x):
    return x.val() if hasattr(x, 'val') else x


def color(hexs, a=1.0):
    h = hexs.lstrip('#')
    return cq.Color(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def safe(name):
    out = ''.join(c if c.isalnum() else '_' for c in name.upper())
    while '__' in out:
        out = out.replace('__', '_')
    return out.strip('_')[:60]


STEP_STAMP = '2026-10-06T00:00:00'   # fixed header time so rebuilds are byte-identical


def fix_stamp(path):
    t = Path(path).read_text()
    Path(path).write_text(re.sub(r"(FILE_NAME\('[^']*',)'[0-9T:-]+'", lambda m: m.group(1) + "'" + STEP_STAMP + "'", t, count=1))


def step(name, items, path):
    a = cq.Assembly(name=name)
    for it in items:
        a.add(val(it['solid']), name=safe(it['name']), color=color(it['color']))
    a.export(str(path))
    fix_stamp(path)


def stl(items, path):
    cq.exporters.export(cq.Compound.makeCompound([val(it['solid']) for it in items]), str(path),
                        exportType='STL', tolerance=0.08, angularTolerance=0.12)


def by(sub):
    return [p for p in PARTS if p['sub'] == sub]


case_parts = [p for p in PARTS if p['layer'] == 'CASE']
film_parts = [p for p in PARTS if p['layer'] == 'ACRYLIC']
controls = by('controls')

# ---- CASE R11 ----
step('STRUTHIO_CASE_R11', case_parts, CASE / 'STRUTHIO_CASE_R11.step')
stl([p for p in case_parts if p['kind'] != 'reserve'], CASE / 'STRUTHIO_CASE_R11.stl')
step('CASE_FRONT_SHELL_R11', by('front_shell'), CASE / 'CASE_FRONT_SHELL_R11.step'); stl(by('front_shell'), CASE / 'CASE_FRONT_SHELL_R11.stl')
step('CASE_REAR_SHELL_R11', by('rear_shell'), CASE / 'CASE_REAR_SHELL_R11.step'); stl(by('rear_shell'), CASE / 'CASE_REAR_SHELL_R11.stl')
step('CASE_CONTROLS_R11', controls, CASE / 'CASE_CONTROLS_R11.step'); stl(controls, CASE / 'CASE_CONTROLS_R11.stl')
step('CASE_SCREEN_STACK_R11', by('screen'), CASE / 'CASE_SCREEN_STACK_R11.step')
step('CASE_INTERNALS_R11', by('internals'), CASE / 'CASE_INTERNALS_R11.step')

# ---- ACRYLIC R1 ----
step('STRUTHIO_ACRYLIC_CLEAR_FACE_FILM_R1', film_parts, ACRYLIC / 'STRUTHIO_ACRYLIC_FACE_FILM_R1.step')
stl(film_parts, ACRYLIC / 'STRUTHIO_ACRYLIC_FACE_FILM_R1.stl')

film = B['FILM_POLY']
loops = [list(film.exterior.coords)[:-1]] + [list(h.coords)[:-1] for h in film.interiors]


def pathd(pts):
    return 'M ' + ' '.join((f'{x:.4f},{y:.4f}' if i == 0 else f'L {x:.4f},{y:.4f}') for i, (x, y) in enumerate(pts)) + ' Z'


# SVG: Y down, exactly the shared R21 XY datum (no flip), so the file overlays the PCB plots.
svg = '\n'.join([
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<svg xmlns="http://www.w3.org/2000/svg" width="104mm" height="135.3mm" viewBox="-52 0 104 135.3">',
    '<title>STRUTHIO acrylic face film R1 cutline — planning only</title>',
    '<desc>Clear 0.20 mm assumed face film, viewed from the front. Coordinates are mm on the shared R21 PCB XY datum (Y down). '
    'Cut paths: outline, two flap-bezel cutouts, DART relief cutout and six vent slots. The display window stays continuous. '
    'Supplier must confirm kerf/offset and material compensation.</desc>',
    f'<g id="CUTLINE" fill="none" stroke="#d34b56" stroke-width="0.15" fill-rule="evenodd"><path d="{" ".join(pathd(l) for l in loops)}"/></g>',
    '</svg>', ''])
(ACRYLIC / 'ACRYLIC_FACE_FILM_CUTLINE_R1.svg').write_text(svg)


def dxf_poly(pts):
    # DXF Y is up: mirror the shared datum's Y-down coordinates so the part is not flipped.
    q = '0\nLWPOLYLINE\n100\nAcDbEntity\n8\nCUTLINE\n100\nAcDbPolyline\n90\n' + str(len(pts)) + '\n70\n1\n'
    for x, y in pts:
        q += f'10\n{x:.5f}\n20\n{-y:.5f}\n'
    return q


header = '0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n'
(ACRYLIC / 'ACRYLIC_FACE_FILM_CUTLINE_R1.dxf').write_text(header + ''.join(map(dxf_poly, loops)) + '0\nENDSEC\n0\nEOF\n')

spec = {
    'layer': 'ACRYLIC', 'revision': 'R1', 'status': 'clear-film cutline study; NOT production artwork',
    'units': 'mm', 'shared_xy_datum': 'SLIM4_R21 PCB XY (Y down); film lower face Z=7.65 mm on the front plate',
    'outer_size_mm': [104.0, 135.3], 'outline_source': 'CASE R11 exterior outline (identical)',
    'film_thickness_mm_assumed': P['film_t'],
    'screen_window': 'No screen cutout; clear film continuous across the lens. Print/white/relief not designed.',
    'cutouts_mm': {
        'flap_centers': [list(c) for c in P['flap_centers']],
        'flap_cut_diameter': P['bezel_od'] + 2 * P['film_clear'],
        'dart_center': [0.0, P['dart_cy']],
        'dart_cut_size': [P['dart_surround'][0] + 2 * P['film_clear'], P['dart_surround'][1] + 2 * P['film_clear']],
        'dart_cut_corner_radius': P['dart_surround_r'] + P['film_clear'],
        'vent_x': [c[0] for c in B['SPK_CENTERS']], 'vent_y': B['GRILLE_YS'],
        'vent_slot_size': [P['grille_slot'][0] + 0.2, P['grille_slot'][1] + 0.2],
    },
    'why_changed_from_R0': [
        'Outline follows CASE R11 (shoulders and finger scallop widened to clear the R21 board; saddle lift 4.0 mm).',
        'Flap and DART cutouts enlarged to clear the molded relief, which now rises through the film from the shell.',
        'DART cutout centred on the R11 pill (Y 119.80); vent slots follow the speakers at X ±38.3, Y 123.7-127.5.',
    ],
    'release_gate': 'Confirm material, optics, perimeter, adhesive, control and vent clearances, tolerance, and supplier process before cutting.',
}
(ACRYLIC / 'ACRYLIC_LAYER_R1_CUT_SPEC.json').write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n')

# ---- Viewer meshes ----
def mesh(it, tol):
    verts, tris = val(it['solid']).tessellate(tol, 0.35)
    rows = []
    for t in tris:
        p = [[round(float(verts[i].x), 3), round(float(verts[i].y), 3), round(float(verts[i].z), 3)] for i in t]
        a, b, c = p
        u = [b[j] - a[j] for j in range(3)]; v = [c[j] - a[j] for j in range(3)]
        n = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]
        shade = round(0.72 + 0.28 * abs(n[2]) / (math.sqrt(sum(k*k for k in n)) or 1), 3)
        rows.append({'p': p, 's': shade})
    opacity = {'lens': 0.32, 'acrylic': 0.23}.get(it['group'], 0.55 if it['kind'] == 'reserve' else 1)
    return {'name': it['name'], 'group': it['group'], 'sub': it['sub'], 'kind': it['kind'], 'color': it['color'], 'opacity': opacity, 'triangles': rows}


TOL = {'front_shell': 0.35, 'rear_shell': 0.4, 'screen': 0.45, 'controls': 0.25, 'internals': 0.4, 'film': 0.3}
case_json = {
    'layer': 'CASE', 'revision': 'R11', 'package': 'R25',
    'status': 'complete enclosure candidate converged on R21 (front shell, rear shell, controls, screen stack, internals); not a tooling release',
    'source': 'LAYERS/02_CASE/build_r11.py via export_layer_formats.py', 'units': 'mm', 'shared_xy_datum': 'SLIM4_R21 PCB XY',
    'case_outline_mm': [104.0, 135.3], 'body_thickness_mm': round(B['Z_FILM_TOP'] - B['Z_FLOOR_OUT'], 3),
    'parts': [mesh(it, TOL[it['sub']]) for it in case_parts],
}
(CASE / 'CASE_LAYER_R11_MESH.json').write_text(json.dumps(case_json, separators=(',', ':'), ensure_ascii=False) + '\n')
(ROOT / 'case-layer-data.js').write_text('window.STRUTHIO_CASE_LAYER=' + json.dumps(case_json, separators=(',', ':'), ensure_ascii=False) + ';\n')
acrylic_json = {
    'layer': 'ACRYLIC', 'revision': 'R1', 'package': 'R25', 'status': 'clear film only; artwork pending',
    'source': 'LAYERS/02_CASE/export_layer_formats.py', 'units': 'mm', 'shared_xy_datum': 'SLIM4_R21 PCB XY',
    'thickness_mm_assumed': P['film_t'], 'parts': [mesh(it, TOL['film']) for it in film_parts],
}
(ACRYLIC / 'ACRYLIC_LAYER_R1_MESH.json').write_text(json.dumps(acrylic_json, separators=(',', ':'), ensure_ascii=False) + '\n')
(ROOT / 'acrylic-layer-data.js').write_text('window.STRUTHIO_ACRYLIC_LAYER=' + json.dumps(acrylic_json, separators=(',', ':'), ensure_ascii=False) + ';\n')

# ---- Fit summary (the full cross-layer report is CHECKS/R25_CONVERGENCE_REPORT.*) ----
fit = {
    'revision': 'R11', 'status': 'CONVERGED ON R21 IN CAD — PHYSICAL GATES OPEN (see CHECKS/R25_CONVERGENCE_REPORT.md)',
    'exterior_outline_mm': [104.0, 135.3], 'r21_pcb_changed': False, 'pcb_thickness_mm': P['pcb_t'],
    'z_stack_mm': {
        'rear_floor_outer': B['Z_FLOOR_OUT'], 'rear_floor_inner': P['floor_inner_z'], 'board': [0.0, P['pcb_t']],
        'lcd_module': [P['lcd_z0'], P['lcd_z0'] + B['LCD_T']], 'front_plate': [P['plate_z0'], B['Z_PLATE_TOP']],
        'film': [B['Z_PLATE_TOP'], B['Z_FILM_TOP']], 'relief_top': B['Z_RELIEF_TOP'], 'cap_top': B['Z_CAP_TOP'],
        'body_thickness': round(B['Z_FILM_TOP'] - B['Z_FLOOR_OUT'], 3), 'with_caps': round(B['Z_CAP_TOP'] - B['Z_FLOOR_OUT'], 3),
    },
    'screen': {'lcd_module_mm': list(P['lcd']), 'lcd_top_y': P['lcd_top_y'], 'lcd_center_y': round(B['LCD_CY'], 3),
               'active_center_y': round(B['ACTIVE_CY'], 3), 'opening_mm': list(P['screen_opening']), 'lens_mm': list(P['lens'])},
    'controls': {'flap_centers': [list(c) for c in P['flap_centers']], 'flap_stroke_to_stop_mm': round(B['STROKE'], 3), 'pregap_mm': P['pregap'],
                 'dart_switch_row_y': P['dart_y'], 'dart_pill_center_y': P['dart_cy'], 'dart_stop_angle_deg': round(math.degrees(B['THETA_DART']), 3),
                 'power': 'rear plunger on SW5 (PWR_WAKE); pinholes on SW6 RESET and SW7 BOOT'},
    'battery_envelope_mm': list(P['battery']), 'speakers': {'part': 'Same Sky CMS-18138A-SP', 'centers': [list(c) for c in B['SPK_CENTERS']]},
    'board_clamps': B['CLAMP_POSTS'], 'rear_supports': B['REAR_ONLY_POSTS'],
    'parameters': {k: (list(v) if isinstance(v, tuple) else v) for k, v in P.items()},
}
(CASE / 'R11_FIT_CHECKS.json').write_text(json.dumps(fit, indent=2, ensure_ascii=False) + '\n')

# ---- Full assembly for review (PCB solids derived from the PCB layer JSON) ----
sys_path = str(ROOT / 'CHECKS')
import sys
sys.path.insert(0, sys_path)
sys.dont_write_bytecode = True   # keep CHECKS/ free of __pycache__
from convergence_check import pcb_items  # noqa: E402
asm = cq.Assembly(name='STRUTHIO_SLIM4_R25_ASSEMBLY')
for it in pcb_items(B):
    asm.add(it['solid'], name=safe(it['name']), color=color('#1f8f4a' if it['kind'] == 'board' else '#30343a'))
for it in PARTS:
    asm.add(val(it['solid']), name=safe(it['name']), color=color(it['color']))
asm.export(str(ASSEMBLY / 'STRUTHIO_SLIM4_R25_ASSEMBLY.step'))
fix_stamp(ASSEMBLY / 'STRUTHIO_SLIM4_R25_ASSEMBLY.step')
print('CASE R11, ACRYLIC R1, viewer meshes and R25 assembly written.')
