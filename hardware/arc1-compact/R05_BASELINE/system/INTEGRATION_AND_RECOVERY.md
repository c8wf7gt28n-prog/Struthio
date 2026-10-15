# Compact integration worksheet — proposals, not electrical assignments

Selected core/RAM remains F133-B 64 MiB + T35F400C3/private 128 MiB x16 DDR3L +
BT820B/private 128 MiB DDR3L (MN820 initially). The working screen remains the
Newhaven 7-inch 1024×600 LVDS candidate. No assembled Compact was tested.

| Boundary | Proposed owner/implementation | Required confirmation |
|---|---|---|
| CPU boot | SD0 for first prototype | Exact board/BSP image, PF pin group, UART boot and 64 MiB runtime budget |
| CPU scene link | CPU SPI0 master; FPGA SPI slave | PC2–PC7 sharing; PC4/5 boot-select high impedance; reset/DMA/IRQ/CS timing |
| Graphics commands | FPGA sole BT820 QSPI master | Real QSPI engine, voltage/reset/startup/init, asset uploads and FIFO telemetry |
| Panel | BT820 single-channel LVDS | Corrected porch convention, exact mapping/encoding, differential levels/termination, connector/backlight and motion |
| FPGA configuration | Dedicated externally reachable configuration/JTAG path | Exact configuration mode, flash ownership/isolation, CRESET_N/CDONE access and invalid-image recovery |
| FPGA DDR | FPGA hard x16 channel | Exact SKU/rails/timings/byte lanes/VREF/ZQ/PLL; Efinity full-package fit and address tests |
| BT DDR | MN820 module first | Real initialization/readback and full memory range; later discrete layout needs separate proof |
| Game storage | Open | Medium/capacity, controller ownership, update/recovery and loading bursts |
| Inputs/audio/power | Open | Exact pins, clock/reset ownership, rails/current/thermal/backlight budget and concurrent-load tests |
| Optional FPGA pixels | Route/reserve decision before PCB freeze | Legal bank/pin/clock placement and extra capture/latency qualification; not needed by first command scene |

The new protocol and compute code provide testable building blocks. They do not
implement SPI PHY, GPIO/DMA/IRQ HAL, BT init/drawing driver, async firmware queues,
DDR controller integration or a complete Efinity project. Use a persistent status
and explicit acknowledgment; do not rely on a transient IRQ pulse. Store outputs
before releasing job credits; bounded retry retention must not re-execute work.

Recovery sequence to implement and fault-test:

1. Keep unpowered/reset device interfaces high impedance and boot straps valid.
2. Boot CPU diagnostics independently of valid FPGA user logic.
3. Reach real FPGA reset/configuration/JTAG even with an invalid application image.
4. Establish a fresh quiescent epoch; discard stale queues/results/address grants.
5. Initialize and test local DDR/BT/panel through the verified ownership matrix.
6. Start deterministic jobs and presentation; retain traces across faults.

Test invalid FPGA image, CPU/FPGA reset mid-job, lost response, bad CRC, repeated
command, exhausted credits, corrupt game storage, lost graphics/display and
power interruption. Code-level epoch/CRC tests are not these physical tests.

## Exact package source work completed

`T35F400_package_source_facts.csv` has 400 unique manufacturer ball records,
zero assigned PCB nets and explicit source row references. The raw workbook's
SHA256 is in `package_source_report.json`; it was downloaded from the official
Efinix endpoint and is not redistributed. Independent openpyxl comparison checked
every A–H field against the standard-library extractor. Counts are overlapping
source annotations, not available-pin counts: 230 GPIO-named entries, 54 DDR
annotations, 138 DDIO annotations, 92 LVDS-annotated pins. Do not sum them.

Run `python3 system/extract_t35_package.py PATH_TO_VENDOR_XLSX` to reproduce the
derived source records. Native Efinity must still assign all simultaneous
DDR/mailbox/QSPI/config/debug/clock and retained video resources legally.
