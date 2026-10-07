#!/usr/bin/env python3
"""Write PROJECT_MANIFEST.json and SHA256SUMS.txt for the package (run last)."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


report = json.loads((ROOT / 'CHECKS/R25_CONVERGENCE_REPORT.json').read_text())
fit = json.loads((ROOT / 'LAYERS/02_CASE/R11_FIT_CHECKS.json').read_text())
case_files = ['LAYERS/02_CASE/' + n for n in ('STRUTHIO_CASE_R11.step', 'STRUTHIO_CASE_R11.stl', 'CASE_FRONT_SHELL_R11.step', 'CASE_FRONT_SHELL_R11.stl',
              'CASE_REAR_SHELL_R11.step', 'CASE_REAR_SHELL_R11.stl', 'CASE_CONTROLS_R11.step', 'CASE_CONTROLS_R11.stl',
              'CASE_SCREEN_STACK_R11.step', 'CASE_INTERNALS_R11.step', 'CASE_LAYER_R11_MESH.json', 'R11_FIT_CHECKS.json')]
acr_files = ['LAYERS/03_ACRYLIC/' + n for n in ('STRUTHIO_ACRYLIC_FACE_FILM_R1.step', 'STRUTHIO_ACRYLIC_FACE_FILM_R1.stl', 'ACRYLIC_FACE_FILM_CUTLINE_R1.svg',
             'ACRYLIC_FACE_FILM_CUTLINE_R1.dxf', 'ACRYLIC_LAYER_R1_CUT_SPEC.json', 'ACRYLIC_LAYER_R1_MESH.json')]
pcb_native = ['LAYERS/01_PCB/SLIM4_R21.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R21.kicad_pro', 'LAYERS/01_PCB/fp-lib-table', 'LAYERS/01_PCB/SLIM4.pretty/']
manifest = {
    'project': 'STRUTHIO SLIM4',
    'package_revision': 'R25',
    'package_issue': 'R25 clean re-issue: corrections and clean-up of the first R25 zip; CASE R11 / ACRYLIC R1 geometry unchanged (see CHANGELOG.md)',
    'previous_revision': 'R24',
    'package_status': 'cross-platform engineering/debug handoff; layers converged in CAD; not a fabrication release',
    'units': 'mm',
    'coordinate_system': {'xy': 'SLIM4_R21 PCB datum (Y down, KiCad)', 'z_origin': 'bottom of PCB is Z=0', 'positive_z': 'toward device front'},
    'convergence': {'checker': 'CHECKS/convergence_check.py', 'report': 'CHECKS/R25_CONVERGENCE_REPORT.md', 'converged': report['converged'],
                    'counts': report['counts'], 'baseline_audit': 'CHECKS/R24_BASELINE_AUDIT.md'},
    'parent_layers': [
        {'id': 'PCB', 'revision': 'R21', 'authority': 'locked baseline; unchanged from R24 (check A1)', 'native': pcb_native,
         'interchange': ['LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json'], 'status': 'engineering review; not fabrication release'},
        {'id': 'CASE', 'revision': 'R11', 'native_source': ['LAYERS/02_CASE/build_r11.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': case_files, 'status': 'complete enclosure candidate converged on R21; physical gates open',
         'envelope_mm': [104.0, 135.3], 'body_thickness_mm': fit['z_stack_mm']['body_thickness'], 'thickness_over_caps_mm': fit['z_stack_mm']['with_caps'],
         'minimum_wall_mm': 2.0},
        {'id': 'ACRYLIC', 'revision': 'R1', 'native_source': ['LAYERS/02_CASE/build_r11.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': acr_files, 'status': 'clear film/cutline study only; print artwork pending', 'assumed_thickness_mm': 0.2, 'screen_cutout': False},
    ],
    'derived': {'assembly': 'ASSEMBLY/STRUTHIO_SLIM4_R25_ASSEMBLY.step', 'assembly_sequence': 'ASSEMBLY/ASSEMBLY_SEQUENCE.md',
                'component_envelopes': 'CHECKS/COMPONENT_ENVELOPES_R21.json', 'renders': 'CHECKS/renders/'},
    'tooling': {'python_requirements': 'requirements.txt',
                'regenerate_in_order': ['LAYERS/02_CASE/export_layer_formats.py', 'CHECKS/convergence_check.py', 'CHECKS/render_review.py', 'CHECKS/make_manifest.py']},
    'viewer': {'entry': 'index.html', 'pcb_mesh': 'model-data.js', 'case_mesh': 'case-layer-data.js', 'acrylic_mesh': 'acrylic-layer-data.js',
               'reference_mesh': 'case-r3-data.js', 'pcb_rear_plot': 'R21_REAR_BOARD.svg', 'offline_service_worker': 'sw.js',
               'deploy_bundle_builder': 'CHECKS/build_viewer_bundle.py'},
    'reference_only': ['REFERENCES/R10_CONTEXT/STRUTHIO_R10_UNSEPARATED_CONTEXT_REFERENCE.step', 'REFERENCES/SLIM4_R3_INTEGRATION/', 'case-r3-data.js'],
    'release_gates': 'PRODUCTION_GATES.md', 'cross_platform_instructions': 'AI_HANDOFF.md', 'change_report': 'AI_CHANGE_REPORT_R25.md',
    'sha256': {p: sha(p) for p in ['LAYERS/01_PCB/SLIM4_R21.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R21_PCB_LAYER.json'] + case_files + acr_files + ['ASSEMBLY/STRUTHIO_SLIM4_R25_ASSEMBLY.step']},
    'checksums_file': 'SHA256SUMS.txt (all package payloads except manifest and checksum file)',
}
(ROOT / 'PROJECT_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
skip = {'PROJECT_MANIFEST.json', 'SHA256SUMS.txt'}
files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
lines = [f'{sha(f)}  {f}' for f in files if f not in skip]
(ROOT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
print(f'manifest + {len(lines)} checksums written')
