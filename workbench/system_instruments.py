"""Source-labelled Workbench instrument view model (no Qt dependency).

Only the FPGA45 'busy_percent' field is currently a percentage, and that
is a *behavioral* estimate, not measured FPGA occupancy or LUT utilization.
The other data are states, counters or unavailable measurements; never
normalize arbitrary counts into fictitious capacity percentages.
"""
from __future__ import annotations

from . import dashboard

TABS = ('Compute', 'Links', 'Memory', 'Timing', 'Events')

# Every proposed hardware resource is represented, including unavailable ones.
ROWS = {
    'Compute': (
        ('f133', 'F133 · CPU workload'),
        ('d213', 'D213 · graphics CPU'),
        ('fpga45', 'FPGA45 · graphics logic'),
        ('fpga12', 'FPGA12 · adaptive logic'),
    ),
    'Links': (
        ('cpu_accel', 'F133 ↔ FPGA12'),
        ('cpu_graphics', 'F133 ↔ D213'),
        ('graphics_fpga', 'D213 ↔ FPGA45'),
        ('storage', 'NOR interface'),
    ),
    'Memory': (
        ('f133_ram', 'F133 · RAM used'),
        ('d213_ram', 'D213 · RAM used'),
        ('fpga45_ram', 'FPGA45 · buffers used'),
        ('fpga12_ram', 'FPGA12 · memory used'),
        ('nor_owner', 'Memory ownership'),
    ),
    'Timing': (
        ('f133_cycles', 'F133 · CPU cycles'),
        ('d213_cycles', 'D213 · compute cycles'),
        ('fpga45_timing', 'FPGA45 · pipeline timing'),
        ('fpga12_latency', 'FPGA12 · offload latency'),
        ('frame_time', 'Frame deadline / time'),
    ),
    'Events': (
        ('f133_state', 'F133 · runtime'),
        ('nor_reads', 'NOR · modeled reads'),
        ('controller', 'Controller · input mask'),
        ('cartridge', 'Cartridge · state'),
        ('usb', 'USB · cartridge port'),
        ('fault', 'NOR · fault state'),
    ),
}


def _empty():
    return {'value': 'Not instrumented', 'percent': None,
            'detail': 'No validated capacity or utilization measurement in the current host model',
            'evidence': 'NOT_INSTRUMENTED'}


def _status(value, detail):
    return {'value': str(value), 'percent': None, 'detail': detail,
            'evidence': 'HOST_SIM_BEHAVIORAL'}


def snapshot(row=None, source=None, source_sha256=None):
    """Return stable tabs and rows for idle or verified behavioral trace state."""
    base = dashboard.snapshot(row, source, source_sha256)
    valid = base['evidence'] == 'HOST_SIM_BEHAVIORAL'
    tabs = {tab: [{'id': key, 'label': name, **_empty()} for key, name in entries]
            for tab, entries in ROWS.items()}
    view = {'evidence': base['evidence'], 'frame': base['frame'], 'source': base['source'],
            'source_sha256': base['source_sha256'], 'tabs': tabs}
    if not valid:
        return view

    def set_row(tab, ident, data):
        next(r for r in tabs[tab] if r['id'] == ident).update(data)

    def safe_str(obj, key):
        val = obj.get(key) if isinstance(obj, dict) else None
        return val if isinstance(val, str) and 0 < len(val) <= 64 else None

    def safe_count(obj, key):
        val = obj.get(key) if isinstance(obj, dict) else None
        return val if type(val) is int and 0 <= val <= 1_000_000 else None

    cpu, gfx, f45, f12 = (row.get(k, {}) for k in ('f133', 'd213', 'fpga45', 'fpga12'))
    nor, memory, controller, cartridge, usb = (row.get(k, {}) for k in
                                                ('nor', 'memory', 'controller', 'cartridge', 'usb'))
    runtime = safe_str(cpu, 'runtime')
    if runtime:
        for tab, ident in [('Compute', 'f133'), ('Events', 'f133_state')]:
            set_row(tab, ident, _status('State: ' + runtime, 'Modeled runtime state; CPU load unknown'))
    commands = safe_count(gfx, 'commands')
    if commands is not None:
        set_row('Compute', 'd213', _status('%d modeled commands / frame' % commands,
                'Behavioral mailbox count, not D213 compute utilization'))
        set_row('Links', 'cpu_graphics', _status('%d mailbox commands / frame' % commands,
                'Observed in model, no byte count, transfer rate or link capacity'))
    busy = f45.get('busy_percent') if isinstance(f45, dict) else None
    if type(busy) is int and 0 <= busy <= 100:
        set_row('Compute', 'fpga45', {'value': '%d%% behavioral workload' % busy, 'percent': busy,
                'evidence': 'HOST_SIM_BEHAVIORAL',
                'detail': 'Synthetic workload formula, NOT FPGA resource use or measured silicon activity'})
    link = safe_str(f12, 'link')
    if link:
        set_row('Compute', 'fpga12', _status('Link: ' + link, 'Link state only; work and resource utilization unknown'))
        set_row('Links', 'cpu_accel', _status('Link: ' + link, 'Link state only; no bytes, bandwidth or latency modeled'))
    nor_reads = safe_count(nor, 'reads')
    if nor_reads is not None:
        set_row('Links', 'storage', _status('%d modeled reads / frame' % nor_reads,
                'Read events only; NOR throughput and interface capacity unknown'))
        set_row('Events', 'nor_reads', _status('%d reads / frame' % nor_reads,
                'Model-generated events, not measured chip accesses'))
    owner = safe_str(memory, 'ownership')
    if owner:
        set_row('Memory', 'nor_owner', _status(owner, 'Modeled ownership; not RAM allocation or capacity use'))
    mask = safe_count(controller, 'held_mask')
    if mask is not None and mask <= 255:
        set_row('Events', 'controller', _status('0x%02X' % mask, 'Host replay or scenario input state'))
    generation = safe_count(cartridge, 'generation')
    cart_state = safe_str(cartridge, 'state')
    if cart_state:
        set_row('Events', 'cartridge', _status(
            cart_state + (' · generation %d' % generation if generation is not None else ''),
            'Modeled cartridge state and generation'))
    port = safe_str(usb, 'cartridge_port')
    if port:
        set_row('Events', 'usb', _status(port, 'Simulated USB cartridge port; no physical device'))
    fault = nor.get('fault') if isinstance(nor, dict) else None
    if type(fault) is bool:
        set_row('Events', 'fault', _status('FAULT' if fault else 'No modeled fault',
                'Scenario fault flag, not physical diagnostics'))
    # The optional scenario sandbox is distinct from HOST_SIM observations.
    workload = row.get('workload') if isinstance(row.get('workload'), dict) else None
    if workload and workload.get('evidence') == 'SCENARIO_ASSUMPTION' and workload.get('model_id') == 'ARC1_ASSUMPTION_SANDBOX_V1' and workload.get('frame') == view['frame']:
        for tab, ident, key, value in (
            ('Compute','f133','f133_demand_pct','F133 workload demand'),
            ('Compute','fpga12','fpga12_demand_pct','FPGA12 workload demand'),
            ('Links','cpu_accel','link_demand_pct','Link demand'),
        ):
            amount=workload.get(key)
            if type(amount) in (int,float) and 0 <= amount <= 10000:
                set_row(tab,ident,{'value':'%.1f%% assumed budget' % amount,
                    'percent':min(100,round(amount)),
                    'detail':value+' within user-adjustable synthetic model, NOT measured hardware; >100% means over budget',
                    'evidence':'SCENARIO_ASSUMPTION'})
        for tab,ident,key,unit in (
            ('Links','cpu_accel','link_transfer_bytes','bytes/frame'),
            ('Timing','f133_cycles','f133_work_units','synthetic units/frame'),
            ('Timing','fpga12_latency','fpga12_busy_us','assumed us/frame'),
            ('Timing','frame_time','estimated_frame_us','assumed us/frame'),
        ):
            value=workload.get(key)
            if type(value) in (int,float) and 0 <= value <= 1_000_000_000:
                entry=next(r for r in tabs[tab] if r['id']==ident)
                if entry['percent'] is None:
                    entry.update(_status('%s %s'%(value,unit),'Assumption sandbox, NOT physical measurements'))
                    entry['evidence']='SCENARIO_ASSUMPTION'
        if workload.get('mode') == 'fpga12':
            # Display actual synthetic transfer byte count alongside link-budget bar.
            entry=next(r for r in tabs['Links'] if r['id']=='cpu_accel')
            entry['value']+=' · %s modeled B/frame' % workload.get('link_transfer_bytes','?')
    return view
