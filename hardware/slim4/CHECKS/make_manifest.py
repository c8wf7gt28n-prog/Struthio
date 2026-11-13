#!/usr/bin/env python3
"""Write PROJECT_MANIFEST.json and SHA256SUMS.txt for the package (run last)."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


report = json.loads((ROOT / 'CHECKS/R33_CONVERGENCE_REPORT.json').read_text())
fit = json.loads((ROOT / 'LAYERS/02_CASE/R12_FIT_CHECKS.json').read_text())
case_files = ['LAYERS/02_CASE/' + n for n in ('STRUTHIO_CASE_R12.step', 'STRUTHIO_CASE_R12.stl', 'CASE_FRONT_SHELL_R12.step', 'CASE_FRONT_SHELL_R12.stl',
              'CASE_REAR_SHELL_R12.step', 'CASE_REAR_SHELL_R12.stl', 'CASE_CONTROLS_R12.step', 'CASE_CONTROLS_R12.stl',
              'CASE_SCREEN_STACK_R12.step', 'CASE_INTERNALS_R12.step', 'CASE_LAYER_R12_MESH.json', 'R12_FIT_CHECKS.json')]
acr_files = ['LAYERS/03_ACRYLIC/' + n for n in ('STRUTHIO_ACRYLIC_FACE_FILM_R2.step', 'STRUTHIO_ACRYLIC_FACE_FILM_R2.stl', 'ACRYLIC_FACE_FILM_CUTLINE_R2.svg',
             'ACRYLIC_FACE_FILM_CUTLINE_R2.dxf', 'ACRYLIC_LAYER_R2_CUT_SPEC.json', 'ACRYLIC_LAYER_R2_MESH.json')]
pcb_native = ['LAYERS/01_PCB/SLIM4_R28.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R28.kicad_pro', 'LAYERS/01_PCB/fp-lib-table', 'LAYERS/01_PCB/SLIM4.pretty/']
manifest = {
    'project': 'STRUTHIO SLIM4',
    'package_revision': 'R33',
    'package_issue': 'R33: PCB R28 adds the peer-to-peer radio: U15 RAKwireless RAK3172-SiP (STM32WLE5 LoRa/FSK, 902-928 MHz, RUI3 AT firmware) with the RAK3272-SiP reference parts (DC-DC inductor, beads, decoupling, NRST and BOOT0 resistors, RF pi network) and a J701 U.FL antenna socket, on three U1 pins that had no net (UART on GPIO39/40, NRST on GPIO50); none of the R27 copper moved (DRC 0/0/0, R27 items unchanged, DSI report and core-regulator ground check identical, RF path 0.18 mm on B.Cu over unbroken In4 ground); firmware R13 (radio AT driver, RADIO self-test line, radio console commands); case still set aside (see CHANGELOG.md, DECISIONS_R33.md)',
    'decisions': ['DECISIONS_R26.md', 'DECISIONS_R27.md', 'DECISIONS_R28.md', 'DECISIONS_R29.md', 'DECISIONS_R30.md', 'DECISIONS_R31.md', 'DECISIONS_R32.md', 'DECISIONS_R33.md'], 'bom_sourcing': 'CHECKS/BOM_SOURCING_R21.json',
    'previous_revision': 'R30',
    'package_status': 'PCB R28 order files ready (U1 stock and the U15 RAK3172-SiP to source); firmware for R23-R28 builds (firmware/slim4; R28 adds the radio pins); CASE R12 set aside by the owner, its pass for the 5 in panel is open (FAIL rows in the convergence report); not a production release',
    'units': 'mm',
    'coordinate_system': {'xy': 'SLIM4 PCB datum, R21 = R22 = R23 = R24 = R25 = R26 = R27 = R28 (Y down, KiCad)', 'z_origin': 'bottom of PCB is Z=0', 'positive_z': 'toward device front'},
    'convergence': {'checker': 'CHECKS/convergence_check.py', 'report': 'CHECKS/R33_CONVERGENCE_REPORT.md', 'converged': report['converged'],
                    'counts': report['counts'], 'baseline_audit': 'CHECKS/R24_BASELINE_AUDIT.md'},
    'parent_layers': [
        {'id': 'PCB', 'revision': 'R28', 'authority': 'locked for ordering; unchanged from the R33 delivery (check A1)', 'native': pcb_native,
         'interchange': ['LAYERS/01_PCB/SLIM4_R28_PCB_LAYER.json'], 'review': ['LAYERS/01_PCB/ELECTRICAL_REVIEW_R22.md', 'LAYERS/01_PCB/README_PCB_LAYER.md'],
         'rebuild': 'LAYERS/01_PCB/R28_FROM_R27/build_r28.sh (from REFERENCES/PCB_R27)', 'preorder_review': 'CHECKS/PREORDER_REVIEW_R26/README.md', 'bringup': 'LAYERS/01_PCB/BRINGUP_PROCEDURE.md', 'dsi_pair_check': 'CHECKS/R28_DSI_REPORT.md', 'display_port': 'LAYERS/01_PCB/DISPLAY_PORT.md', 'release_gates': 'LAYERS/01_PCB/RELEASE_GATES.md',
         'status': 'JLCPCB order files ready; KiCad DRC 0/0/0; U1 ESP32-P4NRW32X out of stock at JLCPCB on 2026-10-07 (pre-order or consign)'},
        {'id': 'CASE', 'revision': 'R12', 'native_source': ['LAYERS/02_CASE/build_r12.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': case_files, 'status': 'complete enclosure converged on R21 in R26; set aside by the owner for PCB R23-R28 and the 5 in panel: case pass open (FAIL rows in the convergence report)',
         'envelope_mm': [104.0, 135.3], 'body_thickness_mm': fit['z_stack_mm']['body_thickness'], 'thickness_over_caps_mm': fit['z_stack_mm']['with_caps'],
         'minimum_wall_mm': 2.0},
        {'id': 'ACRYLIC', 'revision': 'R2', 'native_source': ['LAYERS/02_CASE/build_r12.py', 'LAYERS/02_CASE/export_layer_formats.py'],
         'interchange': acr_files, 'status': 'clear unprinted prototype film, 0.175 PET + 0.025 OCA, edge inset 0.20', 'thickness_mm': 0.2, 'screen_cutout': False},
    ],
    'derived': {'assembly': 'ASSEMBLY/STRUTHIO_SLIM4_R33_ASSEMBLY.step', 'assembly_sequence': 'ASSEMBLY/ASSEMBLY_SEQUENCE.md',
                'component_envelopes': 'CHECKS/COMPONENT_ENVELOPES_R28.json', 'dsi_pair_checker': 'CHECKS/dsi_pair_check.py', 'pcb_layer_exporter': 'CHECKS/export_pcb_layer.py', 'renders': 'CHECKS/renders/'},
    'tooling': {'python_requirements': 'requirements.txt',
                'regenerate_in_order': ['CHECKS/export_pcb_layer.py (after a board edit)', 'CHECKS/dsi_pair_check.py', 'LAYERS/02_CASE/export_layer_formats.py', 'CHECKS/build_builder_packs.py', 'CHECKS/convergence_check.py', 'CHECKS/render_review.py', 'CHECKS/build_pcb_viewer_data.py', 'CHECKS/build_bench_data.py', 'CHECKS/build_r13_reference_data.py', 'CHECKS/build_viewer_bundle.py', 'CHECKS/make_manifest.py']},
    'viewer': {'entry': 'index.html', 'pcb_mesh': 'model-data.js', 'case_mesh': 'case-layer-data.js', 'acrylic_mesh': 'acrylic-layer-data.js',
               'reference_mesh': 'case-r3-data.js', 'r13_controls_prototype_mesh': 'case-r13-data.js', 'bench_and_docs_data': 'bench-data.js',
               'bench_layer': 'bench.js (SYSTEMS, BENCH, DOCS tabs; bench records stay in the browser until exported)', 'pcb_rear_plot': 'R28_REAR_BOARD.svg', 'offline_service_worker': 'sw.js',
               'deploy_bundle_builder': 'CHECKS/build_viewer_bundle.py',
               'studio_version': '1.2', 'pcb_data_builder': 'CHECKS/build_pcb_viewer_data.py', 'fab_summary': 'CHECKS/R28_FAB_SUMMARY.json'},
    'builder_packs': {'generator': 'CHECKS/build_builder_packs.py', 'needs': 'KiCad 7.0.x (kicad-cli, pcbnew) and requirements.txt',
                      'folders': ['1_PCB_FABRICATION', '2_3D_PRINTING', '3_ACRYLIC_STICKER']},
    'reference_only': ['REFERENCES/PCB_R25/', 'REFERENCES/PCB_R24/', 'REFERENCES/PCB_R23/', 'REFERENCES/PCB_R22/', 'REFERENCES/PCB_R21/', 'REFERENCES/DISPLAY_FLEX_R1/', 'REFERENCES/R10_CONTEXT/STRUTHIO_R10_UNSEPARATED_CONTEXT_REFERENCE.step', 'REFERENCES/SLIM4_R3_INTEGRATION/', 'case-r3-data.js'],
    'release_gates': 'PRODUCTION_GATES.md', 'cross_platform_instructions': 'AI_HANDOFF.md', 'change_report': 'AI_CHANGE_REPORT_R33.md', 'firmware': '../../firmware/slim4 (ESP-IDF project for PCB R23-R28; the radio needs R28)',
    'sha256': {p: sha(p) for p in ['LAYERS/01_PCB/SLIM4_R28.kicad_pcb', 'LAYERS/01_PCB/SLIM4_R28_PCB_LAYER.json'] + case_files + acr_files + ['ASSEMBLY/STRUTHIO_SLIM4_R33_ASSEMBLY.step']},
    'checksums_file': 'SHA256SUMS.txt (all package payloads except manifest and checksum file)',
}
(ROOT / 'PROJECT_MANIFEST.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
skip = {'PROJECT_MANIFEST.json', 'SHA256SUMS.txt'}
files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
lines = [f'{sha(f)}  {f}' for f in files if f not in skip]
(ROOT / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
print(f'manifest + {len(lines)} checksums written')
