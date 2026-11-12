"""Selected-board adapter; the preserved ARC/R10 adapter keeps its own bindings."""
from pathlib import Path
import xml.etree.ElementTree as ET
from . import kicad_tools as cad
from .experiment_runtime import sha


def run(root, discovered, board, folder):
    folder=Path(folder);before=sha(board)
    tool=cad.probe(discovered,folder/'probe')
    qualified=cad.qualify(root,tool,folder/'qualification')
    native=cad.native_drc(tool,board,folder/'drc',cad.environment(folder/'drc',tool['major']))
    export_help=cad.invoke([tool['executable'],'pcb','export','svg','--help'],folder/'export-help',cad.environment(folder/'export-help',tool['major']),10)
    if export_help['exit_status'] or any(flag not in export_help['stdout'] for flag in ('--layers','--mode-single')):raise ValueError('BOARD_SVG_CAPABILITY_MISSING')
    out=folder/'export';out.mkdir(parents=True,exist_ok=False);target=out/'board.svg'
    exported=cad.invoke([tool['executable'],'pcb','export','svg','--mode-single','--layers','Edge.Cuts','--exclude-drawing-sheet','--fit-page-to-board','--output',str(target),str(board)],folder/'export-process',cad.environment(folder/'export-process',tool['major']),30)
    matches=list(out.glob('*.svg'))
    if exported['exit_status'] or len(matches)!=1:raise ValueError('BOARD_SVG_EXPORT_FAILED')
    if matches[0]!=target:matches[0].rename(target)
    if target.stat().st_size>2*1024*1024 or ET.parse(target).getroot().tag!='{http://www.w3.org/2000/svg}svg':raise ValueError('BOARD_SVG_INVALID')
    if sha(board)!=before or cad.discover()!=discovered:raise ValueError('BOARD_INPUT_OR_TOOL_CHANGED')
    return {'state':'VIOLATIONS' if native['total'] else 'NO_REPORTED_VIOLATIONS','execution_status':'COMPLETED',
        'native':native,'export':{**exported,'path':str(target),'sha256':sha(target)},'qualification':qualified,
        'source_unchanged':True,'physical_qualification':False,
        'scope':'Selected embedded board geometry and stored zone fills. No external library comparison, refill, schematic parity, ERC or fabrication approval.'}
