"""1.4.5 source-backed proof register, over the shared engineering kernel.

All board inputs are read-only. Model conclusions keep their limited scope.
No claimed board release, firmware boot, physical measurements or live pin edits.
"""
from pathlib import Path
import csv, hashlib, importlib.util, json, re, sys
from . import proof_checks as checks
from .hardware_review import BASE
from . import locations

CONTRACT='arc-ledger.hardware-proof/1.4.5'
DOMAINS=('power_reset','pin_electrical','clock_timing','boot_configuration','data_flow','physical_manufacture')
FAULTS={'none':[], 'corrupted_boot_image':['f133_rom'], 'missing_fpga_bitstream':['fpga12_config'],
        'stuck_reset':['reset_clocks'], 'd213_unavailable':['d213_rom'], 'missing_game_media':['game_media'],
        'unreachable_usb_recovery':['usb_recovery']}
FIELDS={
 'hardware.proof.inspect':({'expected_sources':{'type':'object'}},[]),
 'hardware.proof.trace':({'expected_sources':{'type':'object'},'fault':{'type':'string','enum':list(FAULTS)}},[]),
 'hardware.proof.check':({'kind':{'type':'string','enum':['pins','power','boot']},'fixture':{'type':'object','description':'Caller-supplied fixture; exact shapes and source-derived examples: docs/HARDWARE_STATUS.md. pins: pads/banks/assignments; power: case/limits/allowance_v; boot: path/claim/sha256.'},'expected_sources':{'type':'object'}},['kind','fixture']),
 'hardware.proof.result':({'id':{'type':'string'}},['id']),
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p,root):return p.relative_to(root).as_posix()
def bind(root):
    # Bind source inputs, never ignored local executables or generated build
    # reports. The same inventory policy is used by the engineering kernel.
    from .project_inventory import paths
    files=[p for p in paths(root) if p.relative_to(root).parts[0]=='hardware']
    files += [locations.program(root)/'workbench'/n for n in ('hardware_proof.py','proof_checks.py','proof_tools.py') if (locations.program(root)/'workbench'/n).is_file()]
    files += [p for p in paths(root) if p.relative_to(root).as_posix().startswith('development/hardware_proof/')]
    return {relative(p,root):sha(p) for p in sorted(files)}
def bound(root,expected=None):
    result=bind(root)
    if expected is not None and expected!=result:raise ValueError('STALE_PROOF_SOURCES: exact source and checker binding required')
    return result

def load_module(path,name):
    # Imported checker functions only: never call legacy report writers/main().
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    finally:sys.dont_write_bytecode=old

def power_inputs(root):
    module=load_module(root/BASE/'closure_p2/rail_envelope.py','ledger_p2_model')
    cases,_=module.extract(root/BASE)
    limits={k:getattr(module,v) for k,v in {'resistor_tolerance':'RESISTOR_TOL','fb_min':'FB_MIN','fb_max':'FB_MAX',
        'sense_min':'SENSE_MIN','sense_max':'SENSE_MAX','hysteresis_max':'HYS_MAX','bias_abs_a':'SENSE_CURRENT_A',
        'core_min':'ECP5_CORE_MIN','core_max':'ECP5_CORE_MAX'}.items()}
    return cases,limits,module

def package_inputs(root,board):
    path=root/BASE/'architecture/sources/lattice_ECP5U-12_pinout_FPGA-SC-02032_v2.1.csv'
    with path.open(encoding='utf-8-sig') as stream: lines=list(csv.reader(stream))
    header=next(i for i,r in enumerate(lines) if r and r[0]=='PAD')
    rows=[dict(zip(lines[header],r)) for r in lines[header+1:] if len(r)==len(lines[header])]
    pads={}
    for r in rows:
        pin=r['TQFP144'].strip()
        if pin.isdigit():
            fn=r['Pin/Ball Function'];dual=r['Dual Function']
            pads[pin]=dict(function=fn,bank=r['Bank'],kind='IO' if re.match(r'^P[LRBT]\d+[ABCD]$',fn) else 'SPECIAL',
                clock=any(tag in dual for tag in ('PCLK', 'GPLL')),dual_function=dual)
    component=next(c for c in board['components'] if c['ref']=='U40')
    banks={}
    for p in component['pins'].values():
        if p['name'].startswith('VCCIO'):
            banks[p['name'][5:]]=str(p['net']).split('_')[0]
    lpf=root/BASE/'fpga12/timing/r10_12f_tqfp144.lpf'
    proposed=[];active=[];io={};freq={}
    for line,text in enumerate(lpf.read_text().splitlines(),1):
        loc=re.search(r'LOCATE COMP "([^"]+)" SITE "([^"]+)"',text)
        if loc:
            record=dict(port=loc[1],pin=loc[2],line=line)
            (proposed if text.lstrip().startswith('#') else active).append(record)
        if not text.lstrip().startswith('#'):
            m=re.search(r'IOBUF PORT "([^"]+)" IO_TYPE=(\w+)',text)
            if m:io[m[1]]=m[2]
            m=re.search(r'FREQUENCY PORT "([^"]+)" ([\d.]+) MHZ',text)
            if m:freq[m[1]]=float(m[2])
    fixture={'pads':pads,'banks':banks,'assignments':[dict(port=r['port'],pin=r['pin'],io_type=io.get(r['port'],'UNKNOWN'),requires_clock=r['port'] in ('clk_25m','rgmii_rxc')) for r in proposed]}
    return dict(fixture=fixture,proposed_locations=proposed,active_locations=active,frequencies_mhz=freq,
        declared_component=component['mpn'],declared_footprint=component['footprint'],lpf=str(BASE/'fpga12/timing/r10_12f_tqfp144.lpf'))

def report(root,expected=None):
    root=Path(root).resolve();sources=bound(root,expected);hw=root/BASE
    board=json.loads((hw/'board/r10_board_plan.json').read_text());findings=[]
    def citations(names):
        return [dict(path=str(BASE/n),sha256=sources[str(BASE/n)]) for n in names]
    def add(id,domain,component,status,claim,names,missing,next_check,details=None,evidence='SOURCE-CHECKED',severity='BLOCKER'):
        findings.append(dict(id=id,domain=domain,component=component,status=status,severity=severity,
            claim=claim,evidence_state=evidence,sources=citations(names),assumptions=['Source snapshot observations; vendor transcription not independently requalified'],
            tool={'name':'Ledger Hardware Proof','version':CONTRACT,'checker_sha256':sources.get('workbench/hardware_proof.py')},
            run_artifact='response#/findings/'+str(len(findings)),missing_proof=missing,proposed_correction=next_check,next_executable_check=next_check,details=details or {}))
    cases,limits,legacy=power_inputs(root)
    models=[]
    for c in cases:
        model=checks.power(c,limits);legacy_m=legacy.evaluate(c)['ideal_static_headroom_v']
        agreement=all(abs(model['margins_v'][k]-legacy_m[k])<1e-12 for k in legacy_m)
        if not agreement:raise ValueError('Independent Decimal/P2 model disagreement')
        models.append(dict(case=c,limits=limits,result=model,legacy_margins=legacy_m,independent_formula_agrees=agreement))
    min_margin=min(min(m['result']['margins_v'].values()) for m in models)
    add('PWR-01','power_reset','FPGA12 + FPGA45','INVALID' if min_margin<.005 else 'UNPROVEN',
        'Present dividers do not demonstrate a 5 mV common static margin (explicit P3 study criterion, not a qualified board requirement).',
        ['board/r10_board_plan.json','closure_p2/rail_envelope.py','closure_p3/README.md'],
        ['Qualified ripple, droop, load, thermal and supervisor/disable delay budgets','Pin-level voltage at R32/R38 downstream of sense point'],
        'Run proof.qualify to independently recompute DC margins; then establish guaranteed load/transient/delay budgets before proposing any ECO.',dict(models=models,criterion_v=.005))
    comps={c['ref']:c for c in board['components']}
    gates=[dict(ref=ref,supply=comps[ref]['pins']['5']['net']) for ref in ('U47','U50')]
    add('PWR-02','power_reset','PROGRAMN interlocks','UNPROVEN','Switched-rail PROGRAMN interlocks cannot establish power-off reset behavior from net connectivity alone.',
        ['board/r10_board_plan.json','cad/fpga_supervision.kicad_sch','closure_p3/README.md'],['Guaranteed partial-rail truth table, leakage/injection and latency'],
        'Review exact buffer datasheets and model power-off corners; measure PROGRAMN and I/O isolation on first article.',dict(gates=gates))
    package=package_inputs(root,board);legal=checks.pins(package['fixture'])
    add('PIN-01','pin_electrical','FPGA12 U40','INVALID' if legal['status']=='INVALID' else 'UNPROVEN',
        'Commented TQFP144 locations are source proposals; active exact-package implementation remains unproven.',
        ['board/r10_board_plan.json','architecture/sources/lattice_ECP5U-12_pinout_FPGA-SC-02032_v2.1.csv','fpga12/timing/r10_12f_tqfp144.lpf'],
        ['Active pin locking and vendor exact-package implementation report','All connected parts bank/reset-state and alternate-function ownership audit'],
        'Run vendor exact-part fitter with approved constraints, retaining pin/bank and timing reports; do not substitute proxy256.',dict(package=package,fixture_check=legal))
    # Compare each proposed port pad with actual board net for a reviewable ownership map.
    endpoints=[dict(port=r['port'],package_pad=r['pin'],board_net=comps['U40']['pins'].get(r['pin'],{}).get('net'),
        package_function=package['fixture']['pads'].get(r['pin'],{}).get('function')) for r in package['proposed_locations']]
    add('LINK-01','data_flow','F133 ↔ FPGA12','UNPROVEN','RGMII net ownership, declared RTL ports and host protocol sources exist; no complete target link is qualified.',
        ['board/r10_board_plan.json','fpga12/rtl/rgmii_rx.sv','fpga12/rtl/rgmii_tx.sv','firmware/host_support/include/eth_link.h','firmware/host_support/src/fpga_link.c'],
        ['F133 target EMAC pinmux/driver','Source-synchronous skew/directionality and frame/retry bounds at target speed','RTL-to-constraint correspondence in vendor implementation'],
        'Trace F133 startup → FPGA12 configuration → RGMII; run actual RTL simulation when available, then exact-package implementation.',dict(endpoints=endpoints,nets={n:v for n,v in board['nets'].items() if n.startswith('ETH_')}))
    clocks=[dict(ref=ref,mpn=comps[ref]['mpn'],frequency=comps[ref]['value'],pins=comps[ref]['pins']) for ref in ('X3','X4')]
    add('CLK-01','clock_timing','FPGA12 + FPGA45','UNPROVEN','Oscillator MPNs are TBD; frequency declarations and proxy timing archives do not prove target I/O timing.',
        ['board/r10_board_plan.json','fpga12/timing/r10_12f_tqfp144.lpf','fpga12/timing/r10_12f_proxy256.lpf','fpga12/timing/R10_12F_FIT_TIMING.json','closure_p8/P8_ROUTING_REVIEW.json'],
        ['Selected oscillator tolerances/jitter/startup','RGMII setup/hold and skew constraints','Actual copper stack-up, return paths and route delays','Applicable vendor implementation timing report'],
        'Select oscillator evidence without changing source; obtain exact-part implementation reports and quantify board skew from routed PCB.',dict(clocks=clocks,frequency_declarations_mhz=package['frequencies_mhz'],timing_archive='HISTORICAL_PROXY_ONLY'))
    registry=json.loads((hw/'closure_p9/P9_FIRMWARE_TARGETS.json').read_text())
    stale=[n for n,h in registry['source_snapshot_sha256'].items() if sha(hw/n)!=h]
    add('BOOT-01','boot_configuration','F133 / D213','INVALID' if stale else 'UNPROVEN','Host firmware components are not a ROM-bootable F133 or D213 runtime.',
        ['closure_p9/P9_FIRMWARE_TARGETS.json','closure_p9/P9_BOOT_GRAPH.json','firmware/f133_bootloader/src/r10_boot.c','firmware/d213_flashless_proof/loader/r10_d213_start.c'],
        sorted(set(x for t in registry['targets'] for x in t['blockers'])),
        'Run proof.qualify host sequence tests and boot-container rejection, then validate vendor images, DDR startup and actual USB ROM transport.',dict(stale_registry_sources=stale,targets=registry['targets']))
    add('BOOT-02','boot_configuration','F133 / D213 / both FPGAs','UNPROVEN','A complete bare-metal service runtime is not established by host-backed component tests.',
        ['closure_p9/P9_FIRMWARE_TARGETS.json','closure_p9/P9_MEMORY_DOMAINS.json','memory/R10_memory_owner_map.md','firmware/f133_bootloader/src/ecp5_cfg.c'],
        ['Target startup/linker/DDR','Interrupt/timer integration','USB host and HID gamepads','Storage/import and game media','Audio transport','FPGA target SPI and validated bitstreams','D213 display target driver'],
        'Use the service dependency map; identify a target implementation and regression for each missing service. ARC-OS implementation belongs to 1.4.8.')
    add('LINK-02','data_flow','F133 ↔ D213 ↔ FPGA45','UNPROVEN','USB boot coordinator, graphics command and FPGA45 loader sources do not provide a verified target transport.',
        ['firmware/d213_flashless_proof/loader/r10_d213_start.c','f133/graphics_link/src/gfx_link.c','d213/fpga45_loader/src/d213_fpga45.c','memory/R10_memory_owner_map.md'],
        ['Real USB enumeration/role mux and transfer/retry bounds','D213 independent DDR/firmware','FPGA45 target loader and memory-controller timing'],
        'Compile host coordinator/graphics-loader tests; independently establish real F133 USB → D213 and D213 SPI → FPGA45 transports.')
    from .hardware_review import inspect
    cad=inspect(root)
    add('PCB-01','physical_manufacture','Main PCB','INVALID' if cad['findings']['errors'] else 'UNPROVEN',
        'Source parity is distinct from routed-board and manufacturing qualification; archived DRC is historical.',
        ['cad/ARC1_R10.kicad_pcb','cad/NETLIST.xml','board/r10_board_plan.json','closure_p8/P8_FAB_GATES.csv','closure_p8/P8_ROUTING_REVIEW.json'],
        ['Fresh native KiCad ERC/DRC and unrouted count','Final stack-up/impedance, via and clearance rules','Footprint/connector/enclosure and assembly checks'],
        'Run proof.qualify for native tool availability; if KiCad is installed rerun ERC/DRC against current files. Review connector and enclosure dimensions separately.',dict(source_audit=cad))
    add('PHY-01','physical_manufacture','ARC-1 console','PHYSICAL-TEST-REQUIRED','First-article power, DDR, USB, clocks, HDMI and recovery need board measurements.',
        ['closure_p8/P8_FAB_GATES.csv','closure_p5/FIRST_ARTICLE_TEST_PLAN.csv'],
        ['Instrumented first article and independent fabrication release'],
        'Keep fabrication HOLD; plan current-limited bring-up and measured rails, reset, DDR, link and first-picture checks.',evidence='BLOCKED')
    result=dict(schema=CONTRACT,fabrication='HOLD',physical_hardware=False,design_feasibility='NOT_YET_DETERMINABLE',
        first_article_fabrication_readiness='HOLD',source_hashes=sources,domains=list(DOMAINS),findings=findings,
        known_failure_reproduced=any(f['id']=='PWR-01' and f['status']=='INVALID' for f in findings),
        evidence_policy='Host checks only close host/model requirements; never target timing or physical gates.',
        external_specification_status='Existing local vendor transcriptions retained, no new vendor qualification claimed')
    result['graph']=graph(result,root)
    result['services']=services(root,sources)
    if bind(root)!=sources:raise ValueError('Sources changed during proof inspection')
    return result


def graph(report,root,fault='none'):
    b=str(BASE)+'/'
    # Every transition carries an explicit blocker; this is the declared dependency model.
    specs=[
      ('input_power','Input power',[],'power_reset','board/r10_board_plan.json','VBUS_5V','Input/connector/ESD qualification','Current-limited supply diagnosis'),
      ('rails','Regulator rails',['input_power'],'power_reset','closure_p2/rail_envelope.py','1V1_F12 / 1V1_F45','Qualified transient/current/thermal margins','Measure and isolate failed rail'),
      ('reset_clocks','Reset and clocks',['rails'],'clock_timing','cad/fpga_supervision.kicad_sch','F12_RAILS_VALID / F12_OSC_25M','Exact oscillator plus partial-rail reset/clock timing','Host logs available; target reset behavior unproven'),
      ('f133_rom','F133 ROM / first firmware',['reset_clocks'],'boot_configuration','firmware/f133_bootloader/src/r10_boot.c','SPI0_* / F133_RESET_N','ROM image/header/linker/startup','ROM recovery requires proven USB route'),
      ('f133_memory','F133 local memory',['f133_rom'],'boot_configuration','closure_p9/P9_MEMORY_DOMAINS.json','1V8_DRAM','Target DDR initialization and memory test','ROM recovery; DDR-independent diagnostics missing'),
      ('usb_recovery','USB ROM / recovery route',['reset_clocks'],'data_flow','firmware/f133_board_diag/r10_f133_mmio.c','USB0_SEL / REC_USB_DP','Mux role/pinmux and physical recovery access','Host diagnosis remains; target recovery not guaranteed'),
      ('d213_rom','D213 ROM transport',['f133_memory','usb_recovery'],'boot_configuration','firmware/d213_flashless_proof/loader/r10_d213_start.c','D213_USB0_DP / D213_RESET_REQ_N','F133 USB host driver + vendor preboot','Host coordinator abort; actual USB recovery unproven'),
      ('d213_ddr','D213 DDR / firmware',['d213_rom'],'boot_configuration','closure_p9/P9_FIRMWARE_TARGETS.json','D213 DDR domain','Qualified DDR PBP and application handoff','Reset and retry only after vendor transport proof'),
      ('fpga12_config','FPGA12 configuration',['f133_memory','reset_clocks'],'boot_configuration','firmware/f133_bootloader/src/ecp5_cfg.c','FPGA12_PROGRAMN / FPGA12_DONE','Correct device bitstream and target SPI configuration','Host image rejection; real PROGRAMN recovery unproven'),
      ('rgmii','F133 ↔ FPGA12 request/response',['fpga12_config','f133_memory'],'data_flow','fpga12/rtl/rgmii_rx.sv','ETH_TXCK / ETH_RXCK','Exact pads, active constraints, EMAC, skew and retries','Host protocol diagnostics; no measured target link'),
      ('fpga45_config','FPGA45 configuration',['d213_ddr','reset_clocks'],'boot_configuration','d213/fpga45_loader/src/d213_fpga45.c','FPGA45_PROGRAMN / FPGA45_DONE','D213 target SPI and FPGA45 exact bitstream','Host loader errors; real configuration recovery unproven'),
      ('graphics_flow','Interprocessor graphics flow',['d213_ddr','fpga45_config','rgmii'],'data_flow','f133/graphics_link/src/gfx_link.c','F133 → D213 → FPGA45','Target protocol, buffers, bounds and memory crossings','Abort/retry host logic; target fault containment missing'),
      ('pixels','Pixel timing',['graphics_flow'],'clock_timing','firmware/d213_video_diag/r10_video_start.c','RGB pixel bus','D213 display engine and verified pixel clock','Retain host diagnostics; actual display stop not proven'),
      ('hdmi','HDMI first picture',['pixels'],'physical_manufacture','firmware/d213_video_diag/r10_adv7513.c','HDMI_HPD / TMDS_*','ADV7513 target I2C plus signal integrity and sink lock','Host HPD failure diagnostics; bench test required'),
      ('game_media','Game media / storage',['f133_memory','usb_recovery'],'boot_configuration','closure_p9/P9_FIRMWARE_TARGETS.json','USB storage/import (target unverified)','USB/HID/storage drivers and approved GameCard topology','Missing-media state requires future target implementation')]
    nodes=[];edges=[]
    for id,title,deps,domain,path,net,missing,recovery in specs:
        name=b+path;exists=name in report['source_hashes']
        nodes.append(dict(id=id,title=title,status='UNPROVEN',evidence_state='SOURCE-CHECKED' if exists else 'BLOCKED',domain=domain,
            source=dict(path=name,sha256=report['source_hashes'].get(name)),net=net,intended_software=path,
            missing_proof=missing,testability='Host verification available where explicitly logged; target/physical verification missing',recovery=recovery))
        for dep in deps:edges.append(dict(**{'from':dep,'to':id},status='UNPROVEN',missing_proof=missing,source=name))
    if report['known_failure_reproduced']:
        nodes[1]['status']='INVALID';nodes[1]['missing_proof']='Current divider model fails explicit 5 mV study criterion; qualified design margin still undefined'
    return dict(nodes=nodes,edges=edges,complete=False,scope='Declared conservative boot-to-picture and Silicon Federation dependency model; optional FPGA rendering bypasses not qualified',
        missing_edges=['Target firmware call/order verification','Per-net IO timing/return path/DDR training proof','Complete USB/gamepad/storage/audio initialization'],
        fault=checks.propagate(nodes,edges,FAULTS[fault]))


def services(root,sources):
    rows=[('startup_memory','closure_p9/P9_FIRMWARE_TARGETS.json','ROM/startup/linker/DDR target dependencies missing'),
          ('interrupts_timers','firmware/f133_board_diag/r10_f133_diag.c','Host callbacks/read-only probes do not implement target interrupt/timer services'),
          ('usb_gamepads','firmware/f133_board_diag/r10_f133_mmio.c','USB host and HID drivers missing'),
          ('storage_import','firmware/f133_bootloader/src/spi_nor.c','Mock-backed SPI NOR; target HAL and USB import missing'),
          ('audio','board/r10_board_plan.json','I2S nets exist; target audio service not established'),
          ('fpga_configuration','firmware/f133_bootloader/src/ecp5_cfg.c','Host loader present; target transport/bitstreams missing'),
          ('diagnostics','firmware/f133_board_diag/r10_f133_diag.c','Host diagnostics present; actual target clock/pinctrl pending'),
          ('video','firmware/d213_video_diag/r10_video_start.c','Host first-light orchestration present; target DE/DDR/HDMI missing')]
    return [dict(service=id,status='UNPROVEN',source=dict(path=str(BASE/path),sha256=sources.get(str(BASE/path))),missing_proof=missing) for id,path,missing in rows]


def dispatch(k,op,a):
    if op=='hardware.proof.result':
        e=k.record('evidence',a['id'])
        if not e['tool'].startswith('proof.') or 'diagnostics' not in e:raise ValueError('No hardware proof report in evidence')
        d=e['diagnostics']
        current=bind(k.root)
        if e['tool']=='proof.coverage':current['workbench/hardware_coverage.py']=sha(locations.program(k.root)/'workbench/hardware_coverage.py')
        return dict(evidence=e,source_current=d.get('source_hashes')==current)
    if op in ('hardware.proof.inspect','hardware.proof.trace'):
        r=report(k.root,a.get('expected_sources'))
        if op.endswith('.trace'):return dict(schema=CONTRACT,source_hashes=r['source_hashes'],graph=graph(r,k.root,a.get('fault','none')),fabrication='HOLD')
        return r
    sources=bound(k.root,a.get('expected_sources'));f=a['fixture']
    required={'pins':('pads','banks','assignments'),'power':('case','limits'),'boot':('path','claim','sha256')}[a['kind']]
    missing=[key for key in required if key not in f]
    if missing:raise ValueError('Missing '+a['kind']+' fixture fields: '+', '.join(missing)+'; see docs/HARDWARE_STATUS.md')
    if a['kind']=='pins':r=checks.pins(f)
    elif a['kind']=='power':r=checks.power(f['case'],f['limits'],f.get('allowance_v',0))
    else:
        p=k.safe(f['path'])
        if p.stat().st_size>32*1024*1024:raise ValueError('Artifact exceeds 32 MiB screening limit')
        data=p.read_bytes()
        r=checks.boot_artifact(data,f['claim'],f['sha256'],hashlib.sha256(data).hexdigest())
    if sources!=bind(k.root):raise ValueError('Sources changed during check')
    return dict(schema=CONTRACT,result=r,evidence_state='SOURCE-CHECKED',fixture_authority='CALLER_SUPPLIED_NOT_ACCEPTED_HARDWARE',source_hashes=sources,fabrication='HOLD')
