# Pass 3 — Boot monitor, LCD and host evidence

- F133 C code: `firmware/f133/src/boot_monitor.c`, `serlcd_i2c.c`, `lcd_status.c`.
- Boot status must be granted only on explicit verified events; `READY` requires F133, NOR, D213 video, 12F and 45F readiness.
- Faults latch until monitor reset; the LCD receives `FAULT 0xNNNN` for actionable diagnosis.
- The SerLCD I²C wire encoder issues `0xFE,0x80` for line 1, `0xFE,0xC0` for line 2 with fixed 16-character ASCII rows. SparkFun OpenLCD protocol, default 7-bit address 0x72.
- Encoder is transport-only: F133 TWI0 pinmux (PB3/PB2 candidate), correct voltage, I²C pull-ups, clocking, power gating, timed bus-recovery and actual HAL callback are *not* implemented.
- GUI and agent `boot.simulate` display **HOST SIM** evidence only. They never mark physical ARC-1 hardware ready.
- No USB mass storage or NOR flashing is enabled. Stage ELF/BIN remain linker tests, not boot ROM-qualified images.
- Windows UI: orange Aqua-inspired visual treatment with File Manager navigation and Word 6 keyboard-oriented editor. No blue title bars or gray 3.1 raised-button aesthetic.

## Agent example
`{"id":9,"method":"boot.simulate","params":{"events":["f133","nor","d213","fpga12","fpga45","ready"]}}`

Never interpret an agent simulation result as physical boot telemetry.
