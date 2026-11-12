"""Render read-only R10 PCB layer previews from the native KiCad board.

Requires kicad-cli and Inkscape. Never writes to the PCB itself.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOARD = Path('hardware/compact-arc1/R10_WORK/cad/ARC1_R10.kicad_pcb')
OUTPUT = Path('docs/assets/r10_board_view')
LAYERS = ('F.Cu', 'In1.Cu', 'In2.Cu', 'In3.Cu', 'In4.Cu', 'B.Cu', 'F.SilkS', 'Edge.Cuts')


def render(root: Path = ROOT) -> dict:
    root = Path(root)
    board = root / BOARD
    if not board.is_file():
        raise FileNotFoundError(board)
    destination = root / OUTPUT
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='arc1-board-view-') as temporary:
        tmp = Path(temporary)
        env = os.environ.copy()
        for key, name in (('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache'),
                          ('XDG_DATA_HOME', 'data')):
            folder = tmp / name
            folder.mkdir()
            env[key] = str(folder)
        env['FONTCONFIG_CACHE'] = str(tmp / 'cache')
        for layer in LAYERS:
            svg = tmp / (layer + '.svg')
            png = destination / (layer + '.png')
            plot_layers = layer if layer == 'Edge.Cuts' else layer + ',Edge.Cuts'
            subprocess.run(['kicad-cli', 'pcb', 'export', 'svg', '--layers', plot_layers,
                            '--mode-single', '--page-size-mode', '2', '--output', str(svg), str(board)],
                           check=True, env=env, capture_output=True, text=True, timeout=90)
            subprocess.run(['inkscape', str(svg), '--export-type=png',
                            '--export-filename=' + str(png), '--export-width=1200'],
                           check=True, env=env, capture_output=True, text=True, timeout=90)
    record = {'source': BOARD.as_posix(), 'sha256': sha256(board.read_bytes()).hexdigest(),
              'evidence': 'DESIGN / FABRICATION HOLD', 'layers': list(LAYERS),
              'generator': 'kicad-cli 9 SVG + Inkscape PNG', 'interactive_view': 'read-only'}
    (destination / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    print(json.dumps(render(), indent=2))
