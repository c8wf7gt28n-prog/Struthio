"""Validation shared by optional Qt UI; importable without Qt installed."""
from pathlib import Path
from .cartridge import CartridgeError, inspect_cartridge
ROOT=Path(__file__).resolve().parents[1]
EDIT_EXT={'.c','.h','.s','.py','.md','.json','.txt','.ld','.cmd','.sh','.yaml','.yml'}

def editable_file(candidate: Path, root: Path = ROOT) -> Path:
    """Allow bounded, rooted, nonsymlink source files only."""
    root = root.resolve()
    candidate = Path(candidate)
    if candidate.is_symlink():
        raise ValueError('Symbolic links are not editable in Workbench')
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError('File must exist inside the ARC-1 project')
    if candidate.suffix.lower() not in EDIT_EXT:
        raise ValueError('This file format is not supported by the source editor')
    if candidate.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('File too large for this editor (2 MiB limit)')
    return candidate


def verify_drop(path: Path, root: Path = ROOT) -> dict:
    """Validate a cartridge but NEVER execute content from the archive."""
    if Path(path).suffix.lower() != '.arc1cart':
        raise CartridgeError('Only .arc1cart archives can be imported')
    if Path(path).is_symlink():
        raise CartridgeError('Symbolic-link cartridge imports are refused')
    return inspect_cartridge(Path(path))

