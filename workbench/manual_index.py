"""Small, explicit R10 documentation catalog for the desktop Workbench.

The SLIM4 Studio manual inspired the navigation, but only current R10 files
are indexed. Archive data cannot become an active hardware fact by search.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Entry:
    title: str
    group: str
    evidence: str
    path: str
    description: str


CATALOG = (
    Entry('Workbench guide', 'System', 'GUIDE', 'docs/HARDWARE_STATUS.md', 'Desktop layout, controls and evidence labels'),
    Entry('Controlled build plan', 'System', 'PLAN', 'docs/HARDWARE_STATUS.md', 'R10 work order and fabrication hold'),
    Entry('Workbench v0.5 handoff', 'System', 'PLAN',
          'docs/handoffs/ARC1_Workbench_v0_5_CODEX_IMPLEMENTATION_HANDOFF.txt',
          'Owner-supplied staged Workbench design plan; proposed integrations are not implemented evidence'),
    Entry('System physical properties', 'Hardware', 'DESIGN', 'hardware/compact-arc1/R10_WORK/PHYSICAL_PROPERTIES.md', 'Board-level devices and interfaces'),
    Entry('Physical interfaces', 'Hardware', 'DESIGN', 'hardware/compact-arc1/R10_WORK/PHYSICAL_INTERFACES.md', 'Current R10 interface inventory'),
    Entry('F133 physical properties', 'F133', 'DESIGN', 'hardware/compact-arc1/R10_WORK/f133/PHYSICAL_PROPERTIES.md', 'Processor role and resources'),
    Entry('D213 physical properties', 'D213', 'DESIGN', 'hardware/compact-arc1/R10_WORK/d213/PHYSICAL_PROPERTIES.md', 'Graphics processor role and resources'),
    Entry('FPGA45 physical properties', 'FPGA45', 'DESIGN', 'hardware/compact-arc1/R10_WORK/fpga45/PHYSICAL_PROPERTIES.md', 'Programmable device role and interfaces'),
    Entry('FPGA12 physical properties', 'FPGA12', 'DESIGN', 'hardware/compact-arc1/R10_WORK/fpga12/PHYSICAL_PROPERTIES.md', 'Programmable device role and interfaces'),
    Entry('NOR flash partitions', 'Memory', 'DESIGN', 'hardware/compact-arc1/R10_WORK/memory/NOR_FLASH_PARTITIONS.md', 'Partition ownership and current design assumptions'),
    Entry('Stage 2 change log', 'Hardware QA', 'DESIGN / HOLD', 'hardware/compact-arc1/R10_WORK/qa/STAGE2_CHANGELOG.md', 'Electrical and floorplan corrections'),
    Entry('R10 gate report', 'Hardware QA', 'DESIGN / HOLD', 'hardware/compact-arc1/R10_WORK/qa/R10_gate_report.md', 'Open and closed fabrication gates'),
    Entry('STRUTHIO Arcade 1.8', 'STRUTHIO', 'BROWSER SOURCE', 'examples/struthio_arcade/README_WORKBENCH.md', 'Sole authorized STRUTHIO game and browser workflow'),
)


def available(root: Path) -> tuple[Entry, ...]:
    """Return only catalogued, regular project files; reject symlink escapes."""
    root = Path(root).resolve()
    found = []
    for entry in CATALOG:
        path = root / entry.path
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        if path.is_file() and not path.is_symlink():
            found.append(entry)
    return tuple(found)


def search(root: Path, query: str = '', group: str = 'All') -> tuple[Entry, ...]:
    """Find every query term in an entry's metadata or document text."""
    terms = re.findall(r'\w+', query.casefold())
    results = []
    for entry in available(root):
        if group != 'All' and entry.group != group:
            continue
        if terms:
            body = (Path(root) / entry.path).read_text(encoding='utf-8', errors='replace')
            haystack = ' '.join((entry.title, entry.group, entry.evidence,
                                 entry.description, entry.path, body)).casefold()
            if not all(term in haystack for term in terms):
                continue
        results.append(entry)
    return tuple(results)
