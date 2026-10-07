#!/usr/bin/env python3
"""Write PROJECT_MANIFEST.json and SHA256SUMS.txt for the package (run last)."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


report = json.loads((ROOT / 'CHECKS/R27_CONVERGENCE_REPORT.json').read_text())
fit = json.loads((ROOT / 'LAYERS/02_CASE/R12_FIT_CHECKS.json').read_text())
case_files = ['LAYERS/02_CASE/' + n for n in ('STRUTHIO_CASE_R12.step', 'STRUTHIO_CASE_R12.stl', 'CASE_FRONT_SHELL_R12.step', 'CASE_FRONT_SHELL_R12.stl',
              'CASE_REAR_SHELL_R12.step', 'CASE_REAR_SHELL_R12.stl', 'CASE_CONTROLS_R12.step', 'CASE_CONTROLS_R12.stl',
              'CASE_SCREEN_STACK_R12.step', 'CASE_INTERNALS_R12.step', 'CASE_LAYER_R12_MESH.json', 'R12_FIT_CHECKS.json')]
acr_files = ['LAYERS/03_ACRYLIC/' + n for n in ('STRUTHIO_ACRYLIC_FACE_FILM_R2.step', 'STRUTHIO_ACRYLIC_FACE_FILM_R2.stl', 'ACRYLIC_FACE_FILM_CUTLINE_R2.svg',
             'ACRYLIC_FACE_FILM_CUTLINE_R2.dxf', 'ACRYLIC_LAYER_R2_CUT_SPEC.json', 'ACRYLIC_LAYER_R2_MESH.json')]
pcb_native = ['LAYERS/01_PCB/SLIM4_R22.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R22.kicad_pro', 'LAYERS/01_PCB/fp-lib-table', 'LAYERS/01_PCB/SLIM4.pretty/']
flex_files = ['LAYERS/04_DISPLAY_FLEX/' + n for n in ('generate_flex.py', 'export_flex.py', 'flex_rules.kicad_pro', 'panel_pinmap.csv', 'panel_pinmap_PREVIEW.csv', 'README.md')]
manifest = {
    'project': 'STRUTHIO SLIM4',
    'package_revision': 'R27',
    'package_issue': 'R27: PCB R22 replaces R21 (electrical and land-pattern review fixed, JLCPCB order files), display flex R1 added; CASE R12 / ACRYLIC R2 checked on R22, case pass open (see CHANGELOG.md, DECISIONS_R27.md)',
    'decisions': ['DECISIONS_R26.md', 'DECISIONS_R27.md'], 'bom_sourcing': 'CHECKS/BOM_SOURCING_R21.json',
    'previous_revision': 'R26',
    'package_status': 'PCB R22 order files ready (U1 stock to confirm); display flex waits for the panel pin table; CASE R12 needs its pass for the chosen panel and the R22 connectors (3 FAIL rows); not a production release',
    'units': 'mm',
    'coordinate_system': {'xy': 'SLIM4 PCB datum, R21 = R22 (Y down, KiCad)', 'z_origin': 'bottom of PCB is Z=0', 'positive_z': 'toward device front'},
    'convergence': {'checker': 'CHECKS/convergence_check.py', 'report': 'CHECKS/R27_CONVERGENCE_REPORT.md', 'converged': report['converged'],
                    'counts': report['counts'], 'baseline_audit': 'CHECKS/R24_BASELINE_AUDIT.md'},
    'parent_layers': [
        {'id': 'PCB', 'revision': 'R22', 'authority': 'locked for ordering; unchanged from the R27 delivery (check A1)', 'native': pcb_native,
         'interchange': ['LAYERS/01_PCB/SLIM4_R22_PCB_LAYER.json'], 'review': 'LAYERS/01_PCB/ELECTRICAL_REVIEW_R22.md',
         'status': 'JLCPCB order files ready; KiCad DRC 0/0/0; U1 ESP32-P4NRW32X out of stock at JLCPCB on 2026-10-07 (pre-order or consign)'},
        {'id': 'CASE', 'revision': 'R12', 'native_source': ['LAYERS/02_CASE/build_r12.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': case_files, 'status': 'complete enclosure converged on R21 in R26; on PCB R22 and the chosen panel three case items fail (C6, F1, I1): case pass open',
         'envelope_mm': [104.0, 135.3], 'body_thickness_mm': fit['z_stack_mm']['body_thickness'], 'thickness_over_caps_mm': fit['z_stack_mm']['with_caps'],
         'minimum_wall_mm': 2.0},
        {'id': 'ACRYLIC', 'revision': 'R2', 'native_source': ['LAYERS/02_CASE/build_r12.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': acr_files, 'status': 'clear unprinted prototype film, 0.175 PET + 0.025 OCA, edge inset 0.20', 'thickness_mm': 0.2, 'screen_cutout': False},
        {'id': 'DISPLAY_FLEX', 'revision': 'R1', 'native_source': flex_files, 'preview': 'LAYERS/04_DISPLAY_FLEX/PREVIEW_NOT_FOR_ORDER/',
         'status': 'generator complete (KiCad flex, JLCPCB files); the Startek panel pin table is still to be filled in panel_pinmap.csv'},
    ],
    'derived': {'assembly': 'ASSEMBLY/STRUTHIO_SLIM4_R27_ASSEMBLY.step', 'assembly_sequence': 'ASSEMBLY/ASSEMBLY_SEQUENCE.md',
                'component_envelopes': 'CHECKS/COMPONENT_ENVELOPES_R22.json', 'pcb_layer_exporter': 'CHECKS/export_pcb_layer.py', 'renders': 'CHECKS/renders/'},
    'tooling': {'python_requirements': 'requirements.txt',
                'regenerate_in_order': ['LAYERS/02_CASE/export_layer_formats.py', 'CHECKS/convergence_check.py', 'CHECKS/render_review.py', 'CHECKS/build_pcb_viewer_data.py', 'CHECKS/make_manifest.py']},
    'viewer': {'entry': 'index.html', 'pcb_mesh': 'model-data.js', 'case_mesh': 'case-layer-data.js', 'acrylic_mesh': 'acrylic-layer-data.js',
               'reference_mesh': 'case-r3-data.js', 'pcb_rear_plot': 'R22_REAR_BOARD.svg', 'offline_service_worker': 'sw.js',
               'deploy_bundle_builder': 'CHECKS/build_viewer_bundle.py',
               'studio_version': '1.1', 'pcb_data_builder': 'CHECKS/build_pcb_viewer_data.py', 'fab_summary': 'CHECKS/R22_FAB_SUMMARY.json'},
    'builder_packs': {'generator': 'CHECKS/build_builder_packs.py', 'needs': 'KiCad 7.0.x (kicad-cli, pcbnew) and requirements.txt',
                      'folders': ['1_PCB_FABRICATION', '2_3D_PRINTING', '3_ACRYLIC_STICKER', '4_DISPLAY_FLEX']},
    'reference_only': ['REFERENCES/PCB_R21/', 'REFERENCES/R10_CONTEXT/STRUTHIO_R10_UNSEPARATED_CONTEXT_REFERENCE.step', 'REFERENCES/SLIM4_R3_INTEGRATION/', 'case-r3-data.js'],
    'release_gates': 'PRODUCTION_GATES.md', 'cross_platform_instructions': 'AI_HANDOFF.md', 'change_report': 'AI_CHANGE_REPORT_R27.md',
    'sha256': {p: sha(p) for p in ['LAYERS/01_PCB/SLIM4_R22.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R22_PCB_LAYER.json'] + case_files + acr_files + flex_files + ['ASSEMBLY/STRUTHIO_SLIM4_R27_ASSEMBLY.step']},
    'checksums_file': 'SHA256SUMS.txt (all package payloads except manifest and checksum file)',
}
(ROOT / 'PROJECT_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
skip = {'PROJECT_MANIFEST.json', 'SHA256SUMS.txt'}
files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
lines = [f'{sha(f)}  {f}' for f in files if f not in skip]
(ROOT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
print(f'manifest + {len(lines)} checksums written')
