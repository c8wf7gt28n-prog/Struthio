# Owner selection record

Project: ARC-1 Compact. Date: 14 October 2026.

The owner proposed: “Can we do f133,t35,b820, screen, memory”. The responding proposal named F133-B, T35F400C3 and Bridgetek **BT820B**; 64 MiB CPU DDR2, 128 MiB FPGA-private x16 DDR3L and 128 MiB graphics-private DDR3L; and Newhaven NHD-7.0-1024600AF-LSXP as a concrete screen candidate. It described an initial CPU SPI → FPGA QSPI → BT820 LVDS → screen path and retained implementation/bench qualification.

The owner then approved the direction and requested a handoff to Claude to confirm and continue work.

Consequently:

- **Selected working core:** F133-B + T35F400C3 + BT820B, built-in display.
- **Selected installed RAM target:** 64 + 128 + 128 MiB = 320 MiB across three private pools.
- **Named screen for confirmation:** NHD-7.0-1024600AF-LSXP. This is an accepted evaluation candidate, not a bench-qualified screen.
- **Initial graphics-memory implementation:** MN820 module, including BT820B and 128 MiB DDR3L. Final discrete implementation remains a later engineering choice.
- **Proposed interfaces:** CPU scene mailbox to FPGA; FPGA sole BT command master; BT direct LVDS screen output. These require implementation and testing.
- **Still open:** exact FPGA DRAM SKU, final BT DRAM implementation, permanent boot/game storage, screen orientation, power/audio/control circuits, exact pins, clocks and measured performance.

Approval establishes a design direction for confirmation and development. It does not certify electrical compatibility, completed firmware, timing closure or manufacturing release. Routine implementation and read-only/source verification can proceed within this direction. A substantiated need to replace a selected core component should be reported with a concrete reason and minimal alternative, while unaffected work continues.
