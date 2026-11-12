"""Evidence-gated first-boot readiness; no estimated success probability.

R10 is on fabrication HOLD. File presence counts as design material being
available, *never* as successful ERC/DRC, an operational PCB, or TV output.
"""
from __future__ import annotations
from pathlib import Path
import hashlib, json
from .project_services import project_path

DESIGN_INPUTS = (
    ('schematic', 'R10 KiCad schematic', 'hardware/compact-arc1/R10_WORK/cad/ARC1_R10.kicad_sch'),
    ('pcb', 'R10 KiCad PCB', 'hardware/compact-arc1/R10_WORK/cad/ARC1_R10.kicad_pcb'),
    ('hw_manifest', 'Sourced R10 hardware manifest', 'hardware/manifests/arc1-r10.hw.json'),
    ('nor_map', 'Proposed NOR partition CSV', 'hardware/compact-arc1/R10_WORK/memory/R10_nor_partition.csv'),
)

# These require structured, reviewable test evidence, not existence of a file.
VERIFICATION_GATES = (
    ('erc', 'Schematic ERC and electrical sign-off', 'Independent electrical review and current ERC log'),
    ('drc', 'PCB DRC / fabrication outputs', 'Manufacturing release with verified DRC, Gerbers and drill files'),
    ('firmware', 'Bootable firmware and recovery plan', 'Target-qualified boot image and proven recovery path'),
    ('fpga', 'FPGA configuration / timing', 'Device-specific P&R, timing and boot configuration evidence'),
    ('power', 'Measured manufactured-board power rails', 'Board ID, instrument details, and measured power-up log'),
    ('boot', 'Physical first boot', 'Board ID, console logs and reproducible first-instruction proof'),
    ('tv', 'Physical TV output', 'Board ID, video signal measurements and TV output observation'),
    ('recovery', 'Physical flash and recovery validation', 'Readback, protection and recovery proof on a real board'),
)

def snapshot(root):
    root = Path(root).resolve()
    inputs = []
    for ident, label, name in DESIGN_INPUTS:
        p = root / name
        present = p.is_file() and not p.is_symlink()
        inputs.append({'id': ident, 'label': label, 'file': name,
                       'status': 'DOCUMENTED' if present else 'MISSING',
                       'evidence_class': 'DESIGN',
                       'note': ('Design source exists; verification not inferred' if present
                                else 'Design source not present')})
    gates = [{'id': ident, 'label': label, 'status': 'NOT_VERIFIED',
              'evidence_required': evidence, 'evidence_class': None}
             for ident, label, evidence in VERIFICATION_GATES]
    issues = apply_records(root, gates)
    return {'schema': 'arc1.workbench.readiness/1', 'board_connected': False,
            'fabrication_status': 'HOLD', 'first_boot_probability_percent': None,
            'goal_first_try_success_percent': 95, 'registry_issues': issues,
            'verified_gates': sum(g['status']=='VERIFIED_RECORD' for g in gates), 'required_gates': len(gates),
            'design_inputs': inputs, 'gates': gates,
            'notice': 'Design inputs are not manufacturing or board-test evidence. '
                      'First-boot confidence cannot be calculated from this archive.'}



def apply_records(root, gates):
    """Validate submitted review records and file hashes, not physical outcomes.

    No record automatically authorizes manufacture/programming. Reviewer identity
    is an attribution in a local record, not a cryptographic authentication.
    """
    registry = root/'project/evidence_registry.json'
    if not registry.exists():return []
    issues=[]
    try:
        if registry.stat().st_size > 1024*1024:raise ValueError('Registry too large')
        doc=json.loads(registry.read_text(encoding='utf-8'))
        if doc.get('schema')!='arc1.evidence/1' or not isinstance(doc.get('records'),list):
            raise ValueError('Unsupported evidence registry')
    except (OSError,ValueError,AttributeError) as e:return [str(e)]
    records=doc['records']
    for gate in gates:
        selected=[r for r in records if isinstance(r,dict) and r.get('gate')==gate['id']]
        if not selected:continue
        try:
            if len(selected)!=1:raise ValueError('Duplicate gate records')
            r=selected[0]
            needed={'erc':'STATIC_CHECK','drc':'STATIC_CHECK','fpga':'FPGA_PNR'}.get(gate['id'],'BOARD_TEST')
            if r.get('evidence_class')!=needed:raise ValueError('Wrong evidence class; requires '+needed)
            if r.get('review_state')!='accepted' or not r.get('reviewer') or not r.get('author') or r['reviewer']==r['author']:
                raise ValueError('Independent accepted review required')
            if not r.get('reviewed_at'):raise ValueError('Review date required')
            if needed=='BOARD_TEST' and (not r.get('board_id') or not r.get('equipment')):
                raise ValueError('Board and equipment identity required')
            for field in ('artifacts','subjects'):
                entries=r.get(field)
                if not isinstance(entries,list) or not entries:raise ValueError('Hashed '+field+' required')
                for item in entries:
                    p=project_path(root,item['path'])
                    if not p.is_file() or p.stat().st_size>64*1024*1024:raise ValueError('Invalid evidence file')
                    if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
                        raise ValueError('Stale '+field+' hash: '+item['path'])
            gate.update(status='VERIFIED_RECORD',evidence_class=needed,reviewer=r['reviewer'],
                        evidence_path=r['artifacts'][0]['path'])
        except (OSError,ValueError,KeyError,TypeError,AttributeError) as e:
            gate['status']='RECORD_REJECTED';issues.append(gate['id']+': '+str(e))
    return issues
