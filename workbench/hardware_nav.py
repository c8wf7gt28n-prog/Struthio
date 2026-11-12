"""ARC-1 functional hardware navigator model, independent of Qt.

References existing engineering sources; never moves, copies or changes a source.
A node is a machine/device, meaningful engineering category, or a real file.
Folder enumeration is bounded to the explicitly associated, scoped directory.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

BASE = Path('hardware/compact-arc1/R10_WORK')
CAD = BASE / 'cad'

@dataclass(frozen=True)
class Group:
    title: str
    sources: tuple[str, ...]
    icon: str = 'folder'

@dataclass(frozen=True)
class Device:
    id: str
    title: str
    role: str
    icon: str
    overview: str | None
    groups: tuple[Group, ...]


def group(label, *refs, icon='folder'):
    return Group(label, tuple(refs), icon)


def devices(root=None):
    b = 'hardware/compact-arc1/R10_WORK/'
    c = b + 'cad/'
    return (
        Device('case', 'Case', 'CAD and print-file inspection; enclosure geometry missing', 'pcb', None, (
            group('Available geometry', c+'pcb', 'branding/ARC1_ENCLOSURE_CONCEPT.jpg', icon='image'),
        )),
        Device('viability', 'Hardware Viability', 'Coverage, checks and source-bound evidence', 'ready', None, (
            group('Verification sources', 'workbench/hardware_coverage.py', 'workbench/hardware_proof.py', icon='report'),
        )),
        Device('arcos', 'Operating System · ARC-OS', 'Controller launcher, portable SDK and kernel/BSP investigation', 'firmware', 'docs/CONSOLE.md', (
            group('Launcher & services', 'software/arcos/src', icon='c'),
            group('Portable SDK', 'software/arcos/include', icon='c'),
            group('Separate games', 'software/arcos/games', icon='c'),
            group('Kernel sources & provenance', 'software/arcos/upstream', 'software/arcos/bsp', icon='firmware'),
            group('Tests', 'software/arcos/tests', icon='report'),
        )),
        Device('ledger', 'Hardware & Software Ledger', 'Current engineering sources, register and source checks', 'ready', 'docs/HARDWARE_STATUS.md', (
            group('Engineering models', *(b+'closure_p'+str(n) for n in range(1,11)), icon='report'),
            group('Register bindings', 'project/register/bindings.json', 'project/evidence_registry.json', icon='report'),
        )),
        Device('development', 'Graphite workshop', 'Inspect, propose and review bounded source improvements', 'firmware', 'docs/WORKSHOP.md', (
            group('Workshop services', 'workbench/clip_workshop.py', 'workbench/engineering_kernel.py', icon='c'),
            group('Current proposal', 'project/review/command_parser', icon='report'),
            group('Checks', 'tools/check_release.py', icon='report'),
        )),
        Device('f133', 'F133 · Main CPU', 'Boot, system authority and firmware', 'cpu', b+'f133/PHYSICAL_PROPERTIES.md', (
            group('Firmware', b+'firmware/f133_bootloader', b+'f133/graphics_link', b+'firmware/f133_board_diag', icon='firmware'),
            group('Boot & firmware targets', b+'closure_p9', b+'closure_p5', icon='firmware'),
            group('STRUTHIO C runtime · HOST ONLY', b+'closure_p11_struthio/port', icon='c'),
            group('Schematics', c+'f133.kicad_sch', c+'boot_nor.kicad_sch', icon='schematic'),
            group('Pins & signals', b+'sources/f133/f133_elqfp128_all_pins.csv', b+'hardware/R10_PIN_FUNCTION_MATRIX.csv', b+'architecture/R10_interface_matrix.csv', icon='pin'),
            group('Physical properties', b+'f133/PHYSICAL_PROPERTIES.md', icon='spec'),
            group('Tests & evidence', b+'qa/R10_gate_report.md', icon='report'),
        )),
        Device('d213', 'D213 · Graphics CPU', 'Display engine and graphics-service processor', 'gpu', b+'d213/PHYSICAL_PROPERTIES.md', (
            group('Firmware & drivers', b+'d213/gpu_driver', b+'firmware/d213_flashless_proof', b+'firmware/d213_video_diag', icon='firmware'),
            group('Schematics', c+'d213.kicad_sch', c+'video.kicad_sch', icon='schematic'),
            group('STRUTHIO graphics assets', b+'closure_p11_struthio/STRUTHIO_ASSET_INVENTORY.json', b+'closure_p11_struthio/output', icon='image'),
            group('Video startup evidence', b+'closure_p7', b+'closure_p9', icon='report'),
            group('Links & interfaces', b+'d213/gmac_link', b+'sources/artinchip/d21x_hw_facts.json', icon='pin'),
            group('Physical properties', b+'d213/PHYSICAL_PROPERTIES.md', icon='spec'),
            group('Tests & evidence', b+'d213/gpu_driver/tests', b+'qa/R10_gate_report.md', icon='report'),
        )),
        Device('fpga45', 'FPGA45 · Graphics Logic', 'Graphics RTL, raster and memory interfaces', 'fpga', b+'fpga45/PHYSICAL_PROPERTIES.md', (
            group('RTL source', b+'fpga45/rtl', icon='rtl'),
            group('Testbenches & simulation', b+'fpga45/tb', b+'fpga45/sim', icon='rtl'),
            group('Schematics', c+'fpga45.kicad_sch', c+'sdram45.kicad_sch', icon='schematic'),
            group('Pins & constraints', b+'fpga45/constraints', b+'sources/lattice/lfe5u45_cabga381_pinout.csv', icon='pin'),
            group('Physical properties', b+'fpga45/PHYSICAL_PROPERTIES.md', icon='spec'),
            group('Reports & evidence', b+'fpga45/evidence', b+'closure_p10', icon='report'),
        )),
        Device('fpga12', 'FPGA12 · Adaptive Logic', 'Adaptive/coproc FPGA and support logic', 'fpga', b+'fpga12/PHYSICAL_PROPERTIES.md', (
            group('RTL source', b+'fpga12/rtl', icon='rtl'),
            group('Testbenches', b+'fpga12/tb', icon='rtl'),
            group('Schematics', c+'fpga12.kicad_sch', c+'psram12.kicad_sch', c+'fpga_supervision.kicad_sch', icon='schematic'),
            group('Pins & constraints', b+'fpga12/timing', icon='pin'),
            group('Physical properties', b+'fpga12/PHYSICAL_PROPERTIES.md', icon='spec'),
            group('Adaptive model', b+'fpga12/adaptive', icon='c'),
            group('Tests & evidence', b+'fpga12/timing', b+'fpga12/adaptive', b+'closure_p10', icon='report'),
        )),
        Device('nor', 'NOR Flash · Storage', 'Partition inspection and offline image staging', 'nor', b+'memory/NOR_FLASH_PARTITIONS.md', (
            group('Memory map & partitions', b+'memory/R10_nor_partition.csv', b+'memory/NOR_FLASH_PARTITIONS.md', b+'memory/R10_memory_owner_map.md', icon='memory'),
            group('Boot circuitry', c+'boot_nor.kicad_sch', icon='schematic'),
            group('Image and loader sources', b+'memory/measured_images.json', b+'firmware/f133_bootloader', icon='firmware'),
            group('Evidence & diagnostics', b+'qa/R10_gate_report.md', icon='report'),
        )),
        Device('pcb', 'Main PCB · Electrical', 'Board layout and electrical design sources', 'pcb', b+'PHYSICAL_PROPERTIES.md', (
            group('P8 cross-probe & routing review', b+'closure_p8', icon='report'),
            group('PCB layout', c+'ARC1_R10.kicad_pcb', c+'ARC1_R10.kicad_pro', icon='pcb'),
            group('Schematic sheets', c+'ARC1_R10.kicad_sch', c+'f133.kicad_sch', c+'d213.kicad_sch',
                  c+'fpga45.kicad_sch', c+'fpga12.kicad_sch', c+'boot_nor.kicad_sch', c+'power.kicad_sch',
                  c+'video.kicad_sch', c+'usb_host.kicad_sch', c+'usb_link.kicad_sch', c+'usb_power.kicad_sch',
                  c+'sdram45.kicad_sch', c+'psram12.kicad_sch', c+'fpga_supervision.kicad_sch', c+'debug.kicad_sch', icon='schematic'),
            group('Netlist & pin mapping', c+'NETLIST.xml', b+'hardware/R10_PIN_FUNCTION_MATRIX.csv', icon='pin'),
            group('Physical properties', b+'PHYSICAL_PROPERTIES.md', b+'board/r10_board_plan.json', icon='spec'),
            group('ERC / DRC evidence', b+'closure_p8/P8_VERIFICATION.json', c+'ERC.txt', b+'qa/R10_gate_report.md', icon='report'),
        )),
        Device('interfaces', 'Console Interfaces', 'Video, audio, USB and power connections', 'interface', b+'PHYSICAL_INTERFACES.md', (
            group('Video / audio', c+'video.kicad_sch', b+'PHYSICAL_INTERFACES.md', icon='schematic'),
            group('USB & communications', c+'usb_host.kicad_sch', c+'usb_link.kicad_sch', c+'usb_power.kicad_sch', icon='schematic'),
            group('Power system', c+'power.kicad_sch', b+'closure_p1', b+'closure_p2', b+'closure_p3', icon='schematic'),
            group('Controller & debug', c+'debug.kicad_sch', icon='schematic'),
            group('Interface definitions', b+'architecture/R10_interface_matrix.csv', icon='pin'),
        )),
        Device('arcade', 'Cartridge · STRUTHIO 1.8.0', 'Game source, art and manifest', 'game', 'examples/struthio_arcade/README_WORKBENCH.md', (
            group('Native C sources & gameplay', 'software/struthio', icon='c'),
            group('Build, simulation & packaging', 'workbench/native_struthio.py', 'software/struthio/README.md', icon='firmware'),
            group('Tests & parity', 'software/struthio/test_core.c', 'software/struthio/test_rings.c', 'software/struthio/ring_oracle.mjs', icon='report'),
            *cartridge_groups(root),
            group('JavaScript behavioral reference', 'examples/struthio_arcade/src', icon='firmware'),
            group('Images & audio', 'examples/struthio_arcade/assets', icon='image'),
            group('Project documentation', 'examples/struthio_arcade/README_WORKBENCH.md', 'examples/struthio_arcade/manifest.webmanifest', icon='spec'),
        )),
        Device('workbench', 'Graphite · Tools', 'The development environment itself', 'workbench', 'workbench/README.md', (
            group('Engineering kernel & remote', 'workbench/engineering_kernel.py', 'workbench/engineering_cli.py', 'workbench/engineering_tabs.py', 'workbench/remote_service.py', 'workbench/remote_pwa', icon='firmware'),
            group('Project office & goals', 'project', 'docs/HARDWARE_STATUS.md', icon='ready'),
            group('Application source', 'workbench/qt_app.py', 'workbench/engine.py', 'workbench/hardware_nav.py',
                  'workbench/hardware_overview.py', 'workbench/hardware_browser.py', 'workbench/hardware_review.py', 'workbench/viewer_tabs.py', 'workbench/project_services.py',
                  'workbench/project_tabs.py', 'workbench/editor_recovery.py',
                  'workbench/system_instruments.py', 'workbench/instruments_qt.py', icon='firmware'),
            group('Agent & Graphite', 'workbench/agent.py', 'workbench/clip.py', 'workbench/activity.py', 'docs/HARDWARE_STATUS.md', icon='firmware'),
            group('Theme & settings', 'workbench/qt_theme.py', 'workbench/session.py', icon='spec'),
            group('Tests', 'tests', icon='report'),
        )),
    )


def file_icon(path):
    if Path(path).name in ('Makefile','GNUmakefile'):
        return 'config'
    suffix = Path(path).suffix.lower()
    return {
        '.c': 'c', '.h': 'h', '.cpp': 'c', '.hpp':'h', '.s':'asm', '.sv':'rtl', '.v':'rtl', '.vhd':'rtl',
        '.kicad_sch':'schematic', '.kicad_pcb':'pcb', '.kicad_pro':'pcb',
        '.lpf':'pin', '.csv':'table', '.png':'image', '.jpg':'image', '.jpeg':'image', '.webp':'image',
        '.md':'text', '.txt':'text', '.log':'report', '.json':'config', '.jsonl':'report', '.py':'script',
        '.ld':'config', '.xml':'config', '.webmanifest':'config', '.sh':'script', '.cmd':'script',
        '.css':'script', '.html':'script', '.js':'script', '.mjs':'script', '.mp3':'audio',
    }.get(suffix, 'file')


SKIP = {'.git', '__pycache__', '.venv', 'node_modules', 'build', 'dist', 'obj', '.pytest_cache', '.mypy_cache'}


def group_files(root, device, category):
    """Return real files for exactly the requested group; no broad filesystem walk.

    A directory can have nested file folders, represented by their relative paths,
    so two different 'main.c' files never collide.
    """
    root = Path(root).resolve()
    grp = next(g for g in device.groups if g.title == category)
    seen, paths = set(), []
    for rel in grp.sources:
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = (p for p in sorted(path.rglob('*')) if p.is_file()
                          and not any(part in SKIP or part.startswith('.') for part in p.relative_to(path).parts))
        else:
            continue
        for candidate in candidates:
            try:
                actual = candidate.resolve()
                actual.relative_to(root)
            except ValueError:
                continue
            if actual not in seen:
                seen.add(actual)
                paths.append(actual)
    return paths


def catalog(root):
    """Source-backed device inventory with counts for the navigator and overview."""
    return [(device, [(g, group_files(root, device, g.title)) for g in device.groups]) for device in devices(root)]


def cartridge_groups(root=None):
    from .hardware_import import descriptor, P11
    try:
        data=descriptor(root or Path(__file__).resolve().parents[1])
    except (OSError,ValueError,KeyError,TypeError):
        return (group('Import contract unavailable', P11+'P11_WORKBENCH_IMPORT_CONTRACT.json',icon='report'),)
    groups=[group('Original JavaScript reference · read only',data['reference_source_path'],icon='firmware'),
            group('Native C bootstrap · partial port',data['c_port_path'],icon='c')]
    for item in data['capabilities']:
        if 'file' in item and item['id'] not in ('struthio_reference','struthio_c_core'):
            groups.append(group(item['tree'].split(' > ')[-1],P11+item['file'],icon='image' if item.get('viewer')=='IMAGE' else 'report'))
    groups.append(group('Port handoff & status',P11+'README_HANDOFF.md',P11+'STRUTHIO_PORT_STATUS.json',P11+'P11_VERIFICATION.json',icon='report'))
    return tuple(groups)


# Physical containment and tool ownership used by the navigator, not electrical connectivity.
PARENTS = {'development':'workbench','ledger':'workbench'}
NAVIGATION_ORDER = ('arcos','f133','d213','fpga45','fpga12','nor','pcb','interfaces','case','viability','arcade','workbench','development','ledger')


def navigation(root=None):
    inventory={d.id:d for d in devices(root)}
    return [(inventory[key], PARENTS.get(key)) for key in NAVIGATION_ORDER if key in inventory]
