"""First behavioral ARC-1 full-system simulator.

This is deliberately a functional model: it coordinates the current R10
component roles and produces inspectable telemetry, but it does not claim bus
or clock-cycle accuracy. It consumes the real host game trace when available,
so the Workbench can observe a cartridge moving through a modeled system.
"""
from __future__ import annotations

import json
from pathlib import Path

from .core import display_path, sha256_file


def _trace_inputs(path):
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            frame, held, checksum = line.split()
            rows.append({"frame": int(frame), "held": int(held, 16), "checksum": checksum})
        except ValueError:
            continue
    return rows


def simulate_rows(inputs, scenario=None, cartridge_name='HOST_GAME', workload_mode=None, workload_profile=None):
    """Deterministic functional coordination with explicit injected faults.

    This models state transitions for learning and host debugging; it does not
    model clock, bus, analog power, or silicon behavior.
    """
    scenario = scenario or {}
    allowed = {'controller_mask', 'nor_fault_frame', 'fpga_fail', 'power_loss_frame',
               'cartridge_reload_frame', 'usb_detach_frame'}
    unknown = set(scenario) - allowed
    if unknown:
        raise ValueError('unknown scenario keys: ' + ', '.join(sorted(unknown)))
    if workload_mode and any(value is not None for value in scenario.values()):
        raise ValueError('assumption workload overlays cannot be mixed with injected hardware faults or controller overrides')
    mask = scenario.get('controller_mask')
    if mask is not None and (not isinstance(mask, int) or not 0 <= mask <= 255):
        raise ValueError('controller_mask must be 0..255')
    if scenario.get('fpga_fail') not in (None, '12', '45'):
        raise ValueError('fpga_fail must be 12 or 45')
    for key in ('nor_fault_frame', 'power_loss_frame', 'cartridge_reload_frame', 'usb_detach_frame'):
        v = scenario.get(key)
        if v is not None and (not isinstance(v, int) or not 0 <= v < len(inputs)):
            raise ValueError(key + ' must name a frame in the trace')
    rows = []
    nor_failed = False
    usb_attached = True
    cartridge_generation = 1
    for i, item in enumerate(inputs):
        held = item['held'] if mask is None else mask
        if i == scenario.get('cartridge_reload_frame'):
            cartridge_generation += 1
            nor_failed = False
            usb_attached = True
        if i == scenario.get('usb_detach_frame'):
            usb_attached = False
        if i == scenario.get('nor_fault_frame'):
            nor_failed = True
        outage = scenario.get('power_loss_frame') is not None and i in (
            scenario['power_loss_frame'], scenario['power_loss_frame'] + 1)
        runtime = 'power_off' if outage else 'recovery' if nor_failed else 'running'
        nor_reads = 0 if outage or nor_failed else 3 if i == 0 else 1 if i < 4 else 0
        d213_commands = 0 if runtime != 'running' else 4 + (held & 0x3) + (1 if i % 30 == 0 else 0)
        failed_fpga = scenario.get('fpga_fail')
        fpga45_busy = 0 if runtime != 'running' or failed_fpga == '45' else min(95, 24 + d213_commands * 5 + (i % 7))
        fpga45_state = 'power_off' if outage else 'config_failed' if failed_fpga == '45' else 'blocked' if nor_failed else 'active' if i else 'loading'
        fpga12_link = 'power_off' if outage else 'config_failed' if failed_fpga == '12' else 'blocked' if nor_failed else 'ready' if i >= 2 else 'training'
        event = 'frame' if i else 'boot -> cartridge mount'
        if held & 0x2:
            event = 'controller flap'
        if i == scenario.get('cartridge_reload_frame'):
            event = 'cartridge reload'
        if i == scenario.get('nor_fault_frame'):
            event = 'NOR read fault -> recovery'
        if i == scenario.get('power_loss_frame'):
            event = 'power loss'
        if i == scenario.get('usb_detach_frame'):
            event = 'USB cartridge detached'
        rows.append({
            'frame': item['frame'], 'tick': i, 'event': event,
            'input_mask': held, 'framebuffer_checksum': item['checksum'],
            'f133': {'pc': '0x%08x' % (0x40000000 + i * 32), 'nor_reads': nor_reads, 'runtime': runtime},
            'd213': {'commands': d213_commands, 'mailbox': 'offline' if outage else 'blocked' if nor_failed else 'ready' if i >= 1 else 'booting'},
            'fpga45': {'busy_percent': fpga45_busy, 'state': fpga45_state},
            'fpga12': {'link': fpga12_link, 'state': 'power_off' if outage else 'support'},
            'nor': {'partition': 'F1MA', 'reads': nor_reads, 'owner': 'F133', 'fault': nor_failed},
            'controller': {'held_mask': held, 'source': 'simulated' if mask is not None else 'host replay'},
            'usb': {'cartridge_port': 'attached' if usb_attached else 'detached',
                    'mode': 'power_off' if outage else 'host_simulated'},
            'memory': {'nor_partition': 'F1MA', 'f133_ram_bytes': 4194304,
                       'd213_ram_bytes': 8388608, 'gpu45_sdram_bytes': 0,
                       'ownership': 'none' if outage else 'F133 / D213 / FPGA45'},
            'cartridge': {'name': cartridge_name, 'generation': cartridge_generation,
                          'state': 'unpowered' if outage else 'mounted' if usb_attached else 'detached'},
            'evidence': 'HOST_SIM_BEHAVIORAL',
        })
    if workload_mode is not None:
        from .offload import model_rows
        metrics = model_rows(inputs, workload_mode, workload_profile)
        for row, metric in zip(rows, metrics):
            row['workload'] = metric
    return rows


def run(result, project, frames=120, scenario=None, workload_mode=None):
    result.command = "arc1 system-sim %s" % project.label
    if frames < 1 or frames > 36000:
        result.fail("SYSTEMSIM-FRAMES", "frames must be 1..36000")
        return
    trace = project.build_dir / "sim" / "trace.txt"
    inputs = _trace_inputs(trace)
    if not inputs:
        result.fail("SYSTEMSIM-TRACE", "run the host cartridge simulator first: %s" % display_path(trace))
        return
    inputs = inputs[:frames]
    outdir = project.build_dir / "system_sim"
    outdir.mkdir(parents=True, exist_ok=True)
    output = outdir / "system_trace.jsonl"
    try:
        rows = simulate_rows(inputs, scenario, cartridge_name=project.label, workload_mode=workload_mode)
    except ValueError as e:
        result.fail('SYSTEMSIM-SCENARIO', str(e))
        return
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    result.artifact(output)
    result.extra["details"] = {
        "frames": len(rows), "trace": display_path(output),
        "input_trace": display_path(trace), "trace_sha256": sha256_file(output),
        "model": "behavioral full-system coordination; not cycle-accurate",
        "components": ["F133", "D213", "ECP5-45F", "ECP5-12F", "NOR", "controller", "USB", "memory", "cartridge"],
        "scenario": scenario or {},
        "workload_mode": workload_mode, "workload_evidence": 'SCENARIO_ASSUMPTION' if workload_mode else None,
    }
    result.warn("Behavioral host model only; no silicon timing, vendor FPGA P&R, or board validation")
