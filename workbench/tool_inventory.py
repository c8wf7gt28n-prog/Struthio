"""Read-only host executable discovery; presence is not qualification."""
from __future__ import annotations
import shutil

TOOL_NAMES = (
    ('clang', 'LLVM C compiler'), ('ld.lld', 'LLVM linker'), ('llvm-objcopy', 'LLVM binary tool'),
    ('riscv64-unknown-elf-gcc', 'RISC-V bare-metal compiler'),
    ('yosys', 'FPGA synthesis'), ('nextpnr-ecp5', 'ECP5 place and route'),
    ('ecppack', 'ECP5 bitstream packing'), ('verilator', 'HDL simulator'),
    ('iverilog', 'Verilog simulator'), ('kicad-cli', 'KiCad command-line'),
    ('openocd', 'Hardware debugger transport'), ('riscv64-unknown-elf-gdb', 'RISC-V GDB'),
    ('flashrom', 'External SPI flash programmer'), ('xfel', 'Allwinner FEL utility'),
)

def inspect(which=None,root=None):
    lookup = which or shutil.which
    tools = []
    for name, label in TOOL_NAMES:
        path = lookup(name)
        tools.append({'id': name, 'label': label, 'status': 'FOUND' if path else 'NOT_AVAILABLE',
                      'executable': path, 'version': None, 'qualified': False})
    adapters=[]
    if root is not None:
        from .kicad_tools import discover,qualification_status
        native=discover(lookup);qualified=qualification_status(root,native)
        from .kibot_tools import discover as discover_kibot
        bot=discover_kibot(lookup)
        from .spice_tools import discover as discover_spice
        spice=discover_spice(lookup)
        from .hdl_tools import discover as discover_hdl
        from .surfer_tools import discover as discover_surfer
        for engine in ('icarus','verilator'):
            adapters.append({'id':engine+'.hdl','state':discover_hdl(engine,lookup)['state'],'qualification':None,
                             'notice':'Fixed native HDL profiles, retained diagnostics/traces and per-job capability cases. Digital models only; physical timing unqualified.'})
        adapters.append({'id':'surfer.vcd','state':discover_surfer(lookup)['state'],'qualification':None,
                         'notice':'Verified native Surfer saved-state/capture of a bound digital trace; separate Graphite cursor/zoom inspector. Optional Linux capture runtime.'})
        from .pnr_tools import discover as discover_pnr
        implementation=discover_pnr(lookup)
        for family in ('nextpnr','trellis'):
            adapters.append({'id':family+'.ecp5','state':implementation[family],'qualification':None,
                             'notice':'Bound 45F/381 or explicit 12F/256 package-proxy workflows; per-job native fixtures. Single-seed clock evidence and held offline bitstreams; no programming.'})
        from .yosys_tools import discover as discover_yosys
        synthesis=discover_yosys(lookup)
        adapters.append({'id':'yosys.ecp5','state':synthesis['state'],'qualification':None,
                         'notice':'R10 memory-enabled ECP5 synthesis profiles; capability fixtures repeat each job. No routing, timing or physical qualification.'})
        adapters.append({'id':'spice.passive','state':spice['state'],'qualification':None,
                         'notice':'Registered DC/RC jobs qualify native numerical cases on every run. Reduced passive models; no board qualification.'})
        adapters.append({'id':'kibot.outputs','state':bot['state'],'qualification':None,
                         'notice':'BOM/fabrication operations qualify their own fixtures on every run; no cached qualification.'})
        adapters.append({'id':'cad.drc','state':'CACHED_DRC_CAPABILITY' if qualified else native['state'],
                         'qualification':qualified,'notice':'Registered DRC checks revalidate version and qualification before use.'})
    result={'schema': 'arc1.workbench.tools/1', 'mode': 'READ_ONLY_PATH_DISCOVERY',
            'tools': tools, 'notice': 'Executable PATH discovery only. No tool has been run or qualified.'}
    if root is not None:
        result['operation_adapters']=adapters
        result['notice']='Discovery does not run tools. Operation adapters separately report cached capabilities, revalidated at execution.'
    return result
