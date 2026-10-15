# Host-side drivers (R06): BT820 host link, T35 mailbox, optional offload

Evidence level: **HOST_TESTED** on x86-64 Linux against byte-level mocks, plus ASan/UBSan and a
freestanding object compile. **Not built for the F133. No BSP, no SPI driver binding, and no
contact with silicon.** Real F133 SPI1/SPI0 bindings for `arc1_spi_hal` are PASS 7 step 1.

| File | Role |
|---|---|
| `include/arc1_hal.h` | 4-callback SPI HAL (select, transfer, now_us) the F133 BSP must implement |
| `src/bt820_host.c` | BT820 QSPI host transactions, strictly from BT820 DS v1.1 section 4.5: 31-bit address, write flag in the Addr3 MSB, read poll for 0x01, 32-bit word rules, host command `FF cmd param 00 00`, ACTIVE `00×5`, 0xDEADABBA detection. **Single channel mode only.** |
| `src/t35_link.c` | AMBX v1 mailbox client: probe, status (0xFFFF / reserved bits ⇒ NOT_READY), exchange with timeout, overrun handling |
| `src/accel_dispatch.c` | Sends R05 JOB frames (R05 `SCENE_PAYLOAD_V1`) through the mailbox. Requires STATUS ACCEPTED, RESULT and STATUS DONE. **Any deviation means a CPU fallback** using R05 `arc1_transform_batch`, and a new HELLO with a larger epoch next time. |
| `tests/mocks.c` | BT820 slave mock; T35 mock with a software R05-semantics accelerator and eight fault engines |
| `tests/test_firmware.c` | 231 checks |

The R05 C sources (`protocol/src/arc1_protocol.c`, `compute/arc1_transform.c`) are compiled
**unmodified, by path**.

## What the tests show (and what they don't)

* Every fault case returns results bit-identical to the CPU reference. The cases are: no FPGA,
  FPGA disabled, transport-loopback FPGA (the R06 RTL engine), never answers, late, corrupted
  CRC, wrong tag, application error, reset mid-job, and missing DONE.
* **Graceful degradation:** the BT820 command stream (FNV hash of every write and host command)
  is identical across CPU-only, a healthy accelerator, and every fault case. Losing the T35
  never changes or blocks the graphics path. The draw stream is **synthetic**: placeholder
  addresses, not the BT820 memory map, not STRUTHIO content.
* A well-formed but numerically wrong FPGA answer is caught only in `verify` mode, which is
  meant for bring-up. In normal mode the FPGA result is trusted. That limitation is tested and
  documented.
* Not shown: SPI timing, F133 SPI controller behaviour, BT820 register-level initialisation,
  display output, real frame time.

## Assumptions to retire in PASS 7

1. The byte order of 32-bit BT820 data words is little-endian (BRT_AN_086, not yet read).
2. BT820 writes at ≥ 0x7F000000 are refused, because their first byte would equal the
   host-command prefix 0xFF; the datasheet is silent on this.
3. The F133 SPI controller can hold CS# across separate transfers, which the read-poll loop needs.
   Otherwise the binding must use one long transfer with in-buffer 0x01 search.

`make` (or `make test sanitize freestanding`) runs everything. Override `CC` and `R05` as needed.
