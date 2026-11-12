"""Provenance checks for read-only R10 PCB preview images."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = Path('docs/assets/r10_board_view')


def load(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    preview = root / PREVIEW
    record = json.loads((preview / 'manifest.json').read_text(encoding='utf-8'))
    source = (root / record['source']).resolve()
    source.relative_to(root)
    layers = record['layers']
    if not isinstance(layers, list) or not layers or len(set(layers)) != len(layers):
        raise ValueError('invalid layer list')
    images = {}
    for layer in layers:
        if not isinstance(layer, str) or not layer or '/' in layer or '\\' in layer or '..' in layer:
            raise ValueError('invalid layer name')
        path = preview / (layer + '.png')
        if not path.is_file() or path.is_symlink():
            raise ValueError('missing preview layer ' + layer)
        images[layer] = path
    record['images'] = images
    record['current'] = source.is_file() and sha256(source.read_bytes()).hexdigest() == record['sha256']
    return record
