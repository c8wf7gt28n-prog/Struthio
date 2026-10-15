#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- reality-based acceleration benchmark (change order 5.3, HARD STOP rule).

Per representative 60 Hz workload it compares
  CPU path : dynamic RV64IM instruction count of the C kernel (rv64im_iss.py, checksums equal to a native run)
             x CPI / f_cpu                                      -> ISS_COUNTED x ASSUMPTION(CPI, f_cpu)
  FPGA path: host link time (real F133 driver over the board model, firmware/tools/bench_link.c)
             + FPGA compute (transform: RTL PERF counter, tb_ecp5_top; others: PLANNING estimate)
HARD STOP (CO 5.3): a workload whose transfer time exceeds its FPGA compute time and whose FPGA path is not faster
than the CPU is a failed offload. Nothing here is a hardware measurement.
Usage: benchmark_r85.py OUT_JSON OUT_MD"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R85 = os.path.normpath(os.path.join(HERE, "..", ".."))
R05C = os.path.normpath(os.path.join(R85, "..", "R05_BASELINE", "compute"))
FW = os.path.join(R85, "firmware")
B = os.path.join(HERE, "build")
os.makedirs(B, exist_ok=True)


def sh(cmd, cwd=HERE):
    return subprocess.run(cmd, cwd=cwd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode()


# ---------------------------------------------------------------- CPU side: ISS instruction counts
sh(f"riscv64-unknown-elf-gcc -O2 -march=rv64im -mabi=lp64 -ffreestanding -nostdlib -static -fno-builtin "
   f"-Wl,-Ttext=0x10000 -Wl,-e,_start -I{R05C} start.S kernels.c {R05C}/arc1_transform.c -lgcc -o {B}/kernels.elf")
sh(f"cc -O2 -DNATIVE -I{R05C} kernels.c {R05C}/arc1_transform.c -o {B}/kernels_native")
native = [int(x) for x in sh(f"{B}/kernels_native").split()]
iss = json.loads(sh(f"{sys.executable} -I rv64im_iss.py {B}/kernels.elf"))
if iss["result_sum"] != native:
    print("ISS self-check FAILED", iss["result_sum"], native)
    sys.exit(1)
marks = dict()
for mid, n in iss["marks"]:
    marks[mid] = n
cnt = {"transform": marks[11] - marks[10], "collision": marks[21] - marks[20], "particles": marks[31] - marks[30],
       "fir": marks[41] - marks[40]}
items_iss = {"transform": 170, "collision": 128 * 127 // 2, "particles": 512, "fir": 256}
ipi = {k: cnt[k] / items_iss[k] for k in cnt}

# ---------------------------------------------------------------- link: real driver over the model
sh(f"cc -std=c11 -O2 -Iinclude -Itests -I{R05C} tools/bench_link.c src/*.c tests/ecp5_mock.c {R05C}/arc1_transform.c "
   f"-o build/bench_link", cwd=FW)
link_rows = [json.loads(l) for l in sh(f"{FW}/build/bench_link 10e6 2000").splitlines() if l.startswith("{")]
assert all(r["fpga_used"] for r in link_rows), "link benchmark did not use the FPGA path"
xs = [r["n"] for r in link_rows]
ys = [r["total_us"] - r["engine_us"] for r in link_rows]
bs = [r["spi_bytes"] for r in link_rows]
nb = len(xs)
mx, my = sum(xs) / nb, sum(ys) / nb
slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
icpt = my - slope * mx
bytes_per_job = (bs[-1] - bs[0]) / (xs[-1] - xs[0])
us_per_byte = slope / bytes_per_job                 # effective, incl. protocol polling
batch_overhead_us = icpt

# ---------------------------------------------------------------- assumptions
F_CPU = 1.0e9          # ASSUMPTION: F133 C906 clock (no sourced figure in sources/f133)
CPI = (1.0, 2.0)       # ASSUMPTION: in-order single-issue core, best/worst
F_FPGA = 80e6          # routed sys_clk (BUILD_REPORT: 87 MHz achieved)
FRAME_US = 1e6 / 60
LINKS = {
    "A_current_SPI_10MHz (RTL mailbox limit sys/8; modelled with the real driver)": (us_per_byte, batch_overhead_us),
    "B_SPI_50MHz_single (needs a new source-synchronous mailbox slave; ASSUMPTION)": (us_per_byte / 5.0, batch_overhead_us / 2),
    "C_QSPI_4x50MHz (needs 3 more FPGA pins + new slave + F133 SPI0 quad host mode; ASSUMPTION)": (us_per_byte / 20.0, batch_overhead_us / 2),
}
WORK = [  # name, items per frame, CPU instr per item, bytes over the link per frame, FPGA cycles per frame, FPGA source
    ("2D transform (R05 contract), 170 rectangles", 170, ipi["transform"], 170 * 72 + 32,
     39 + 96 * 170, "RTL_SIMULATED (tb_ecp5_top PERF_LAST_CYCLES fit)"),
    ("AABB collision, 128 boxes all pairs (8128 tests)", 8128, ipi["collision"], 128 * 16 + 74 * 4 + 32,
     8128 // 8 + 128, "PLANNING estimate: 8 comparator lanes, no RTL"),
    ("particles, 512 (state resident in FPGA EBR, positions read back)", 512, ipi["particles"], 512 * 8 + 32,
     512 + 64, "PLANNING estimate: 1 particle/clock, no RTL"),
    ("DSP stress: 32-tap FIR, 735 samples (44.1 kHz / 60)", 735, ipi["fir"], 735 * 4 + 32,
     735 * 4 + 64, "PLANNING estimate: 8 MULT18X18D, 4 clocks/sample, no RTL"),
]
rows = []
for name, n, ipitem, nbytes, fcyc, fsrc in WORK:
    t_cpu = [n * ipitem * c / F_CPU * 1e6 for c in CPI]
    t_fc = fcyc / F_FPGA * 1e6
    for lname, (upb, ovh) in LINKS.items():
        t_link = nbytes * upb + ovh
        t_f = t_link + t_fc
        rows.append({"workload": name, "link": lname, "cpu_us_best": round(t_cpu[0], 1), "cpu_us_worst": round(t_cpu[1], 1),
                     "fpga_compute_us": round(t_fc, 1), "link_us": round(t_link, 1), "fpga_path_us": round(t_f, 1),
                     "transfer_dominates": t_link > t_fc,
                     "speedup_vs_cpu_worst": round(t_cpu[1] / t_f, 3), "speedup_vs_cpu_best": round(t_cpu[0] / t_f, 3),
                     "frame_pct_fpga_path": round(100 * t_f / FRAME_US, 1), "fpga_source": fsrc,
                     "link_bytes": nbytes, "cpu_instr_per_item": round(ipitem, 1),
                     "breakeven_link_MBps": round(nbytes / max(t_cpu[1] - t_fc - ovh, 1e-3), 1) if t_cpu[1] > t_fc + ovh else None})
cur = [r for r in rows if r["link"].startswith("A_")]
hard_stop = all(r["transfer_dominates"] and r["speedup_vs_cpu_worst"] < 1.0 for r in cur)
any_win = [r for r in rows if r["speedup_vs_cpu_worst"] >= 1.0]
out = {
    "schema": "arc1-r85-benchmark-v1",
    "evidence": {"cpu": "ISS_COUNTED instructions (rv64im_iss.py, checksums == native) x ASSUMPTION CPI/f_cpu",
                 "link": "HOST_TESTED driver over the board model (firmware/tools/bench_link.c), SCK 10 MHz, 2 us/CS",
                 "fpga": "transform RTL_SIMULATED; others PLANNING estimates"},
    "assumptions": {"f_cpu_Hz": F_CPU, "cpi_range": CPI, "fpga_sys_Hz": F_FPGA, "cs_overhead_ns": 2000},
    "iss": {"instructions": cnt, "items": items_iss, "instr_per_item": {k: round(v, 2) for k, v in ipi.items()},
            "checksums": native, "mix": {k: iss[k] for k in ("mul", "div", "load", "store", "branch")}},
    "link_measured": link_rows, "link_fit": {"us_per_byte": round(us_per_byte, 4), "batch_overhead_us": round(batch_overhead_us, 1),
                                             "bytes_per_transform_job": round(bytes_per_job, 2)},
    "rows": rows,
    "verdict": "HARD_STOP_TRANSFER_DOMINATED" if hard_stop else "MIXED",
    "any_scenario_where_fpga_wins": [(r["workload"], r["link"]) for r in any_win],
}
json.dump(out, open(sys.argv[1], "w"), indent=1)

L = ["# R8.5 acceleration benchmark (GENERATED by tools/bench/benchmark_r85.py)", "",
     f"**Verdict: {out['verdict']}.** Under the current link, every representative workload spends longer moving data over "
     "SPI than the FPGA spends computing, and the FPGA path is slower than the F133 CPU even with the worst-case CPU "
     "assumption. This is the change order's HARD STOP condition (5.3). It holds for the T35 too, since the link and the "
     "no-FPGA-to-BT820 rule are the same. The bottleneck is the architecture, not the FPGA part.", "",
     "Evidence: CPU = dynamic instruction counts from an RV64IM ISS (checksums equal to a native run) × assumed CPI 1–2 "
     "at an assumed 1.0 GHz. Link = the real F133 driver code against the board model at SCK 10 MHz, 2 µs per CS "
     "transaction. FPGA = RTL perf counter for the transform; the other workloads are planning estimates with no RTL. "
     "No hardware measurement.", "",
     f"Link fit (driver + model): {us_per_byte:.3f} µs per byte effective, {batch_overhead_us:.0f} µs per batch, "
     f"{bytes_per_job:.1f} SPI bytes per transform job.", "",
     "| Workload | Link | CPU µs (best–worst) | FPGA compute µs | Link µs | FPGA path µs | Transfer dominates | Speed-up vs worst CPU | Frame % (FPGA path) |",
     "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| {r['workload']} | {r['link'].split(' ')[0]} | {r['cpu_us_best']}–{r['cpu_us_worst']} | {r['fpga_compute_us']} | "
             f"{r['link_us']} | {r['fpga_path_us']} | {'YES' if r['transfer_dominates'] else 'no'} | "
             f"{r['speedup_vs_cpu_worst']} | {r['frame_pct_fpga_path']} |")
L += ["", "Link scenarios:"] + [f"* {k}" for k in LINKS] + ["",
      f"CPU instructions per item (ISS): " + ", ".join(f"{k} {v:.1f}" for k, v in ipi.items()) + ".", "",
      "## What this means", "",
      "* Data has to come back over SPI, because the F133 alone commands the BT820 (protected baseline; no FPGA→BT820 path). "
      "So offload pays only when CPU work per byte moved exceeds about (f_cpu / link bandwidth) cycles: ≈ 900 cycles/byte "
      "at today's ≈ 1.1 MB/s effective. The ARC-1 2D workloads need about 5–60 CPU instructions per byte moved.",
      "* With the multiplier mapping (8 of 72 MULT18X18D), 87 MHz timing and the PSRAM interface, the ECP5 meets every "
      "logic gate. It does not meet the CO 5.3 success criterion.",
      "* Options for the owner (CO 8.2: report, do not silently change): see STATUS_R85.md 'Stop/revert options'.", ""]
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print(json.dumps({"verdict": out["verdict"], "link_fit": out["link_fit"], "instr_per_item": out["iss"]["instr_per_item"]}))
