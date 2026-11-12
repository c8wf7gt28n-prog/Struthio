"""Explicitly hypothetical CPU vs FPGA12 workload comparison.

Nothing here profiles compiled C, counts F133 instructions, predicts FPGA
fabric timing or measures a physical interconnect. This is a reproducible
scenario calculator driven by recorded HOST_SIM frame/input observations.
Units, scheduler and assumed throughput are documented in each report.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

MODEL_ID = 'ARC1_ASSUMPTION_SANDBOX_V1'
# Synthetic units and hypothetical rates. NOT verified ARC-1 specifications.
DEFAULT_PROFILE = {
    'frame_budget_us': 16667, 'f133_work_units_per_us': 8,
    'fpga12_work_units_per_us': 20, 'link_bytes_per_us': 2,
    'base_f133_units_per_frame': 50000,
    'f133_work_units_per_job': 10000,
    'fpga12_work_units_per_job': 10000,
    'dispatch_f133_units_per_job': 200,
    'input_bytes_per_job': 2048, 'output_bytes_per_job': 256,
}
_LIMITS = {
    'frame_budget_us': (1000, 100000),
    'f133_work_units_per_us': (1, 100000),
    'fpga12_work_units_per_us': (1, 100000),
    'link_bytes_per_us': (1, 100000),
    'base_f133_units_per_frame': (0, 100000000),
    'f133_work_units_per_job': (1, 100000000),
    'fpga12_work_units_per_job': (1, 100000000),
    'dispatch_f133_units_per_job': (0, 100000000),
    'input_bytes_per_job': (1, 1000000),
    'output_bytes_per_job': (1, 1000000),
}


def validate_profile(profile=None):
    """No arbitrary unknown keys, booleans or zero-divisor model values."""
    doc = deepcopy(DEFAULT_PROFILE) if profile is None else profile
    if not isinstance(doc, dict) or set(doc) != set(DEFAULT_PROFILE):
        raise ValueError('workload profile must specify exactly the documented fields')
    for key, (minimum, maximum) in _LIMITS.items():
        value = doc.get(key)
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError('%s must be an integer in %d..%d' % (key, minimum, maximum))
    return deepcopy(doc)


def _pct(amount, available):
    return round(100 * amount / available, 2)


def model_rows(inputs, mode, profile=None):
    """Deterministic comparison over the same input sequence for each mode.

    Frame jobs are a chosen demonstration *fixture*, NOT observed game logic:
    4 base jobs + low two input bits + one job each 30th frame.
    Synthetic CPU base time is serial with the job phase. In offload mode
    FPGA12 compute and link time are serial, overlapped with F133 dispatch.
    No overlap within the FPGA/link path and no cross-frame backlog is modeled.
    """
    if mode not in ('cpu', 'fpga12'):
        raise ValueError('mode must be cpu or fpga12')
    p = validate_profile(profile)
    out=[]
    for i, item in enumerate(inputs):
        if not isinstance(item, dict) or type(item.get('frame')) is not int or type(item.get('held')) is not int or not 0 <= item['held'] <= 255:
            raise ValueError('invalid host frame input at index %d' % i)
        jobs=4+(item['held']&3)+(1 if i%30==0 else 0)
        base=p['base_f133_units_per_frame']/p['f133_work_units_per_us']
        if mode=='cpu':
            cpu_units=p['base_f133_units_per_frame']+jobs*p['f133_work_units_per_job']
            fpga_units=0; link_bytes=0
            cpu_time=cpu_units/p['f133_work_units_per_us']
            fpga_time=0.0;link_time=0.0;critical=cpu_time
        else:
            cpu_units=p['base_f133_units_per_frame']+jobs*p['dispatch_f133_units_per_job']
            fpga_units=jobs*p['fpga12_work_units_per_job']
            link_bytes=jobs*(p['input_bytes_per_job']+p['output_bytes_per_job'])
            cpu_time=cpu_units/p['f133_work_units_per_us']
            fpga_time=fpga_units/p['fpga12_work_units_per_us']
            link_time=link_bytes/p['link_bytes_per_us']
            critical=base+max(jobs*p['dispatch_f133_units_per_job']/p['f133_work_units_per_us'],fpga_time+link_time)
        budget=p['frame_budget_us']
        out.append({
            'frame':item['frame'],'jobs':jobs,'mode':mode,'model_id':MODEL_ID,
            'evidence':'SCENARIO_ASSUMPTION',
            'f133_work_units':cpu_units,'fpga12_work_units':fpga_units,
            'link_transfer_bytes':link_bytes,
            'f133_busy_us':round(cpu_time,2),'fpga12_busy_us':round(fpga_time,2),
            'link_busy_us':round(link_time,2),'estimated_frame_us':round(critical,2),
            'f133_demand_pct':_pct(cpu_time,budget),
            'fpga12_demand_pct':_pct(fpga_time,budget),
            'link_demand_pct':_pct(link_time,budget),
            'frame_budget_us':budget,'deadline_met':critical<=budget,
        })
    return out


def compare(inputs, profile=None, input_trace_sha256=None):
    p=validate_profile(profile)
    if not inputs:
        raise ValueError('host trace has no frames')
    if len(inputs)>36000:
        raise ValueError('comparison is limited to 36000 frames')
    modes={mode:model_rows(inputs,mode,p) for mode in ('cpu','fpga12')}
    def aggregate(rows):
        count=len(rows)
        return {'frames':count,'total_jobs':sum(row['jobs'] for row in rows),
                'total_link_bytes':sum(row['link_transfer_bytes'] for row in rows),
                'mean_f133_demand_pct':round(sum(row['f133_demand_pct'] for row in rows)/count,2),
                'mean_fpga12_demand_pct':round(sum(row['fpga12_demand_pct'] for row in rows)/count,2),
                'mean_link_demand_pct':round(sum(row['link_demand_pct'] for row in rows)/count,2),
                'mean_estimated_frame_us':round(sum(row['estimated_frame_us'] for row in rows)/count,2),
                'worst_estimated_frame_us':max(row['estimated_frame_us'] for row in rows),
                'deadline_misses':sum(not row['deadline_met'] for row in rows)}
    a,b=aggregate(modes['cpu']),aggregate(modes['fpga12'])
    return {'schema':'arc1.offload_compare.v1','evidence':'SCENARIO_ASSUMPTION',
            'model_id':MODEL_ID,'input_trace_sha256':input_trace_sha256,
            'description':'Synthetic jobs inferred from frame and input mask, NOT executed C instructions or silicon telemetry',
            'model_limits':['Hypothetical work units, rates, and link sizes','No real F133 profiling or FPGA12 bitstream',
                            'No bus contention, cache/memory modeling, or inter-frame queueing',
                            'Images remain original HOST_SIM baseline output'],
            'profile':p,'modes':{'cpu':a,'fpga12':b},
            'mean_time_change_us':round(b['mean_estimated_frame_us']-a['mean_estimated_frame_us'],2),
            'mean_time_change_pct':round(100*(b['mean_estimated_frame_us']-a['mean_estimated_frame_us'])/a['mean_estimated_frame_us'],2),
            'per_frame':modes}


def load_profile(path=None):
    if path is None:
        return validate_profile()
    p=Path(path)
    if p.stat().st_size>4096:
        raise ValueError('profile too large')
    return validate_profile(json.loads(p.read_text(encoding='utf-8')))


def run(result, project, frames=120, profile_path=None):
    from .systemsim import _trace_inputs
    from .core import display_path, sha256_file
    result.command='arc1 workload-compare %s' % project.label
    trace=project.build_dir/'sim'/'trace.txt'
    inputs=_trace_inputs(trace)[:frames]
    if not inputs:
        result.fail('COMPARE-NO-TRACE','Run the host game simulator first; no trace is available')
        return
    try:
        profile=load_profile(profile_path)
        report=compare(inputs,profile,input_trace_sha256=sha256_file(trace))
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        result.fail('COMPARE-PROFILE',str(exc));return
    target=project.build_dir/'system_sim'
    target.mkdir(parents=True,exist_ok=True)
    # Give the existing Engineering Trace viewer two trace-compatible overlays.
    # These are not game execution traces. They are the original behavioral
    # records decorated with clearly labelled synthetic resource demands.
    from .systemsim import simulate_rows
    modes={}
    for mode in ('cpu','fpga12'):
        filename=target/('workload_%s.jsonl'%mode)
        overlay=simulate_rows(inputs, cartridge_name=project.label, workload_mode=mode,
                              workload_profile=profile)
        filename.write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in overlay),encoding='utf-8')
        modes[mode]={'trace':display_path(filename),'sha256':sha256_file(filename)}
        result.artifact(filename)
    report['overlay_traces']=modes
    report_path=target/'offload_compare.json'
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    result.artifact(report_path)
    result.extra['details']={'report':display_path(report_path),
        'evidence':'SCENARIO_ASSUMPTION','frames':len(inputs),
        'model_id':MODEL_ID,'input_trace_sha256':sha256_file(trace)}
    result.warn('Assumption sandbox, NOT observed chip workload, bus bandwidth or frame performance')
