# ECP5 configuration, the two interfaces, the P0–P6 state machine and the protocol (R8.5)

Code: `firmware/src/ecp5_cfg.c` (configuration interface), `firmware/src/fpga_link.c` + `accel_job.c` (operational
interface), `firmware/src/accel_service.c` (state machine). RTL: `fpga_ecp5/rtl/`. Evidence: HOST_TESTED against a
behavioural sysCONFIG/mailbox model and RTL_SIMULATED. Nothing has run on an ECP5.

## 1. Configuration mode and circuit

* **Slave SPI (SSPI), CFG[2:0] = 001** (TN-02039 Table 4.6): CFG_0 (U4) has a 4.7 kΩ pull-up, CFG_1 (T4) and CFG_2 (R4)
  are tied to GND. The F133 is the only configuration master. JTAG is always available as an independent path.
* Balls (bank 8, VCCIO8 = 3V3_FPGA, CONFIG_IOVOLTAGE = 3.3): CCLK U3, MOSI/D0 W2, MISO/D1 V2, SN T2, HOLDN R2 (10 kΩ
  pull-up, inactive), PROGRAMN W3, INITN V3, DONE Y3. Pull-ups per TN-02038 Tables 6.1–6.3: 4.7 kΩ on PROGRAMN, INITN,
  DONE and SN; 1 kΩ on CCLK; 33 Ω series on CCLK at the buffer. JTAG: TCK 4.7 kΩ pull-down; TMS, TDI, TDO 4.7 kΩ pull-ups.
* F133 side: SPI0 (PC2 CLK, PC4 MOSI, PC5 MISO) through the R08 isolation buffers U21–U24. SN comes from F133 PE4 via U23,
  PROGRAMN from PE8 (open-drain use, 470 Ω), INITN to PD0, DONE to PE9. Full matrix: `board/F133_PINMUX_MATRIX_R85.csv`.
* Speed: CCLK ≤ 60 MHz (DS). The plan is 25 MHz. The compressed bitstream is 288,697 bytes (this design), so the wire
  time is 92 ms; the host model including CS overhead gives 100 ms.

### Configuration flash: removed (CO 4.2)

The R08 T35 had its own W25Q32 (U19). R8.5 removes it, for these reasons:
* **Ownership/update:** game-specific images live with the game on microSD and the base diagnostic image in NOR
  ASSETS. One owner (the F133) and one update path (the game package), with no second flash that can hold a stale or
  half-written image.
* **Cost/area:** one SOIC-8 and four passives fewer.
* **F133 streaming is sufficient:** about 0.1 s per game swap at 25 MHz, and recovery needs no flash programmer.
* **Not shareable:** the boot NOR cannot double as the FPGA flash. Master-SPI mode would make the FPGA a second master on
  the boot bus, which is exactly the hazard the corrective handoff removed.

The rule `ecp5_sysconfig` fails if any SPI NOR connects to an FPGA ball (negative test `test_config_flash_reintroduced`).

### Constraint found in R8.5: no NOR→FPGA streaming

LSC_BITSTREAM_BURST needs SN low for the whole bitstream. The boot NOR shares SCK/MOSI/MISO, so the F133 cannot read
the NOR while the burst is open. NOR-resident images must first be **staged in DRAM** (64 MiB). microSD (SMHC0) is a
separate bus and can be streamed directly. The F133 boot0 diagnostic image has no DRAM, so it only **probes** the FPGA
(rails, INITN, READ_ID = 0x41112043, status) and never configures it. The `ecp5_configure_stream()` header states this
restriction.

## 2. Two distinct interfaces (CO 4.2)

| | CONFIGURATION interface | OPERATIONAL interface |
|---|---|---|
| When | P3, FPGA not in user mode (DONE low) | P4/P5, after DONE, user design running |
| FPGA end | sysCONFIG engine (hard logic) | `mbx_spi_slave` + AMBX v3 registers (user RTL) |
| Balls | CCLK U3, D0 W2, D1 V2, SN T2 | user I/O R1 (same SCK net as CCLK), W2, V2, T2, IRQ_N E6 |
| Protocol | Lattice opcodes: READ_ID E0, LSC_READ_STATUS 3C, ISC_ENABLE C6, ISC_ERASE 0E, LSC_INIT_ADDRESS 46, LSC_BITSTREAM_BURST 7A, ISC_DISABLE 26 | AMBX: 0x02 write / 0x0B read + 16-bit address; AJOB/ARES frames in the 8 KiB buffers |
| Separation | SLAVE_SPI_PORT = DISABLE (LPF SYSCONFIG): after wake-up the sysCONFIG port is off and its balls are user I/O. AMBX frames cannot reach sysCONFIG | before DONE the user design does not exist. The host checks DONE + INITN + DISCOVER before any mailbox access |
| Clock | ≤ 60 MHz (plan 25 MHz) | ≤ sys_clk/8 = 10 MHz (oversampling slave, RTL_SIMULATED at /8 and /16) |

Neither interface reaches the boot NOR: the isolation buffers are off (BUS_EN_N pull-up) during F133 reset and BROM, and
the F133 holds NOR CS0# high by GPIO while the FPGA is selected. NOR independence (G3) rests on this board-level
argument (rules `boot_straps_00`, `spi0_fpga_isolated`) and on the R08 boot trace, and needs the R08 bench items.

## 3. State machine P0–P6 (`accel_service.c`)

| State | F133 action | FPGA guarantee | Implemented by / tested in |
|---|---|---|---|
| P0 reset | BROM boots NOR (straps 00) | rails off (PE0 pull-down), buffers off, PROGRAMN released | board pulls; `svc_init` → `ecp5_safe(power_off)` |
| P1 launcher | graphics/audio/USB without FPGA | FPGA off (or held unconfigured) | FIT F03c, F10b: CPU path, identical results |
| P2 select | read container, check CRC32, IDCODE, ABI; quiesce PSRAM (REQ = 0) and ABORT the old job | no I/O contention | `ecp5_image_check`; FIT F04c, F08b, F10a, X05, X11 |
| P3 configure | power-up (VCC_PG, INITN), PROGRAMN pulse ≥ 110 ns, READ_ID, ISC_ENABLE/ERASE/INIT_ADDRESS, burst, status, ISC_DISABLE, DONE | DONE timeout and explicit error | `ecp5_configure`; FIT F03a/b, F04a/b, F05, F11, X01–X04 |
| P4 handshake | DISCOVER (magic, VERSION = 3, CAPS incl. AJOB and image-required caps), known-answer AJOB, PSRAM power + READY (+ BIST) | no game work before signature + self-test | FIT F06, F07a/b, F08a, X12 |
| P5 play | AJOB batches; timeout → ABORT; CRC/sequence error → one retry; 3 consecutive failures → P6 | bounded latency (20 ms timeout), CPU result always | FIT X06–X10; N0 |
| P6 fault | PSRAM off, buffers off, FPGA rails off, back to P1 | no effect on NOR boot, USB or graphics (service never touches SPI1 or NOR CS) | `fault()`; mutant `MUTANT_SVC_NO_SAFE_ON_FAULT` killed by 11 cases |

## 4. Versioned protocol (CO 5.1 message classes)

| Class | Realisation | Validation |
|---|---|---|
| DISCOVER | AMBX MAGIC "AMBX" @0x0000, VERSION u16 = 3 @0x0004, CAPS u16 @0x0006 (b0 PSRAM, b1 BIST, b2 power guard, b3 AJOB) | blank/absent FPGA reads 00 (MISO pull-down) → NOT_READY; VERSION ≠ 3 → FL_VERSION → P6 (F08a) |
| SUBMIT | AJOB frame: "AJOB", version 1, opcode 1 (TRANSFORM_BATCH), count ≤ 170, seq u32, CRC32 over count × 48 B | RTL rejects BAD_VERSION/BAD_OPCODE/BAD_LENGTH/PAYLOAD_CRC with count 0 (11 RTL cases); length bounded by the 8 KiB buffer |
| COMPLETE | ARES frame: "ARES", version, status, count, seq echo, CRC32 over count × 24 B | host checks magic, seq, status, count, length, CRC (`ajob_parse`); 20 ms timeout |
| PERFORMANCE | PERF_LAST_CYCLES @0x24, PERF_JOBS @0x28, PERF_ITEMS @0x2C, LAST_STATUS @0x30 | checked in tb_ecp5_top; used by the benchmark |
| RESET/ABORT | CONTROL b6 ABORT → ARES status 5 (ABORTED), count 0, seq echoed; PROGRAMN pulse; power-off | tb_ecp5_top ajob_abort + ajob_after_abort; FIT X08, X11 |

Legacy: a request that does not start with "AJOB" is looped back unchanged, so the R05 golden wire frames still pass
(tb_ecp5_top golden_loopback).

## 5. What is not proven

ECP5 status-register bit positions (taken from the Linux lattice-sysconfig driver and TN-02039), the real
configuration timing, F133 SPI0 at 25 MHz through the buffers, HOLDN behaviour, and every board-level waveform.
All are bench items in `RISK_REGISTER_R85.md`.
