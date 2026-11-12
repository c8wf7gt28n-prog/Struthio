"""Inventory reconciliation over preserved sources. Mapping is not validation."""
import csv
import hashlib
import json
from pathlib import Path
from collections import Counter
from . import viewer_data as cad
from .hardware_proof import BASE, DOMAINS, bind, load_module

FIELDS = {
    'hardware.coverage.inspect': ({'expected_revision': {'type': 'string'}}, []),
    'hardware.checks.inspect': ({}, []),
}


def registry():
    return [dict(id=id, version=1, tool=tool, scope=scope, environment=env,
                 prerequisites=prereq, timeout_seconds=300, output_limit_bytes=2097152,
                 acceptance=criterion, artifacts=['JSON report', 'stdout', 'stderr'],
                 qualification=qualification)
            for id,tool,scope,env,prereq,criterion,qualification in [
        ('source-consistency','proof.coverage','All inventoried components and interfaces','static source inspection',
         ['current schematic, PCB, BOM, netlist, board and interface records'],
         'No unresolved cross-source disagreement; gaps remain visible','fixed Ledger adapter'),
        ('preserved-proof-pilots','proof.qualify','Existing six-domain pilots and negative fixtures','host C / optional RTL',
         ['C11 compiler', 'GNU Make', 'optional Icarus and KiCad'],
         'Existing checker assertions pass; missing tools recorded separately','fixed Ledger adapter'),
        ('arcos-lifecycle','arcos.test','ARC-OS host lifecycle and diagnostics','native host C',
         ['C11 compiler','Linux or macOS POSIX loader'],
         'Lifecycle, replay and rejection assertions pass','fixed Ledger adapter'),
        ('native-erc-drc',None,'Current board and schematics','KiCad exact project version',
         ['compatible kicad-cli','qualified project libraries'],
         'Review fresh ERC/DRC and schematic parity reports','BLOCKED: no dedicated qualified adapter'),
        ('exact-fpga',None,'FPGA45 and FPGA12 exact devices/packages','vendor fitter',
         ['licensed compatible vendor tools','approved exact-package constraints'],
         'Pin/bank and timing reports meet reviewed constraints','BLOCKED: exact-package qualification absent'),
        ('physical-validation',None,'Every board, rail, clock and interface','ARC-1 physical measurement',
         ['identified board','bench equipment','separate owner approval'],
         'Reviewed measurements satisfy component requirements','BLOCKED: fabrication and flashing HOLD'),
    ]]


def inspect(root, expected=None):
    root=Path(root).resolve(); hw=root/BASE
    sources=bind(root)
    sources['workbench/hardware_coverage.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    revision=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest()
    if expected is not None and expected!=revision:
        raise ValueError('STALE: inventory or checker changed; inspect current coverage')
    checker=load_module(hw/'closure_p8/crossprobe.py','ledger_coverage_crossprobe')
    index,_=checker.create_index(root)
    plan=json.loads((hw/'board/r10_board_plan.json').read_text())
    records={}
    def add(ref,source,value=None,dnp=None):
        row=records.setdefault(ref,dict(id=ref,kind='component',sources={},claims=['source-consistency'],
                                       domains=list(DOMAINS),validation='BLOCKED',gaps=[]))
        row['sources'][source]=dict(value=value,dnp=dnp)
    for ref,c in index['components'].items():add(ref,'netlist',c.get('value'))
    for ref,c in index['pcb']['footprints'].items():add(ref,'pcb')
    for c in plan['components']:add(c['ref'],'board_plan',c.get('value'),c.get('dnp'))
    with (hw/'bom/ARC1_R10_stage2_BOM.csv').open(newline='',encoding='utf-8-sig') as stream:
        for c in csv.DictReader(stream):
            for ref in c['References'].split():add(ref,'bom',c['Value'],c.get('DNP'))
    for path in sorted((hw/'cad').glob('*.kicad_sch')):
        for symbol in cad.parts(cad.read(path,'kicad_sch'),'symbol'):
            ref=cad.prop(symbol,'Reference')
            if ref and not ref.startswith('#'):
                add(ref,'schematic',cad.prop(symbol,'Value'),cad.val(cad.one(symbol,'dnp')))
    for row in records.values():
        absent=sorted({'schematic','pcb','netlist','bom','board_plan'}-row['sources'].keys())
        if absent:row['gaps'].append('Missing from: '+', '.join(absent))
        values={s['value'] for s in row['sources'].values() if s['value'] is not None}
        if len(values)>1:row['gaps'].append('Value disagreement: '+repr(sorted(values)))
        row['gaps'].append('Component-specific electrical, timing and physical acceptance mapping requires review')
    interfaces=[]
    for name,net in sorted(index['nets'].items()):
        interfaces.append(dict(id='net:'+name,kind=net['kind'],endpoints=net['pins'],
                               claims=['source-consistency'],domains=['pin_electrical','data_flow'],
                               validation='BLOCKED',gaps=['Endpoint electrical/timing compatibility unqualified']))
    with (hw/'architecture/R10_interface_matrix.csv').open(newline='',encoding='utf-8-sig') as stream:
        for i,row in enumerate(csv.DictReader(stream)):
            interfaces.append(dict(id='architecture:'+str(i+1),kind='architecture_interface',record=row,
                                   claims=[],domains=['data_flow'],validation='BLOCKED',
                                   gaps=['Architecture row requires reviewed net/endpoint mapping']))
    for path in sorted(hw.rglob('*')):
        if path.is_file() and (path.suffix.lower() in ('.step','.stp','.stl','.3mf','.fcstd') or 'MECHANICAL' in path.name):
            interfaces.append(dict(id='mechanical:'+path.relative_to(root).as_posix(),kind='mechanical_source',
                                   claims=[],domains=['physical_manufacture'],validation='BLOCKED',
                                   gaps=['Fit, clearance and manufacturing acceptance unverified']))
    items=list(records.values())+interfaces
    errors=index['findings']['errors']; warnings=index['findings']['warnings']
    return dict(schema='arc-ledger.hardware-coverage/1',revision=revision,source_hashes=sources,
                evidence_type='STATIC_CHECK',fabrication='HOLD',domains=list(DOMAINS),
                totals=dict(items=len(items),components=len(records),interfaces=len(interfaces),
                            mapped_to_source_check=sum(bool(r['claims']) for r in items),
                            unmapped=sum(not r['claims'] for r in items),with_gaps=len(items),
                            cross_source_errors=len(errors),cross_source_warnings=len(warnings)),
                status_totals=dict(Counter(r['validation'] for r in items)),items=items,
                cross_source=dict(status='FAIL' if errors else 'PASS',errors=errors,warnings=warnings,
                                  scope='Preserved P8 checker: PCB/netlist/plan ownership only'),
                checks=registry(),status='FAIL' if errors else 'SOURCE-CHECKED',
                notice='Coverage is an inventory denominator, never a probability of first boot. All physical claims remain open.')


def dispatch(kernel,op,args):
    if op=='hardware.checks.inspect':return dict(schema='arc-ledger.check-registry/1',checks=registry())
    return inspect(kernel.root,args.get('expected_revision'))
