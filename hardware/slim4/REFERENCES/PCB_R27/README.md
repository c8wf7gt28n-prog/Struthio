# PCB R27 — reference only

The R27 board as delivered in package R32: `SLIM4_R27.kicad_pcb`, its project, `fp-lib-table`, the local `SLIM4.pretty` library (as in R27), the studio layer JSON, KiCad's DRC report (0 / 0 / 0) and the release gates (`RELEASE_GATES_R27.md`, copied from `RELEASE_GATES.md`). Superseded by PCB R28 in `LAYERS/01_PCB/`, which adds the peer-to-peer radio.

What R28 changes from R27: U15, a RAKwireless RAK3172-SiP (STM32WLE5 LoRa / FSK, 902–928 MHz), with its DC-DC inductor, beads, decoupling, reset and boot resistors, the RF pi network and the J701 U.FL antenna socket (27 parts, two of them not fitted); a RADIO_3V3 pour on In3 and a ground pour under the SiP; three U1 lines on pads that had no net (UART TX / RX on GPIO39 / 40, NRST on GPIO50). Nothing of R27's copper moved: every R27 track, via, pad, footprint and zone outline is in R28 unchanged.

It is kept because `LAYERS/01_PCB/R28_FROM_R27/build_r28.sh` rebuilds R28 from it, edit by edit.
