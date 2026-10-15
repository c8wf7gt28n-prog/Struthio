# BT820 host protocol (R07): addressing, framing, byte order, host commands

Implementation: `R07_WORK/firmware/src/bt820_host.c`, `src/bt820_gfx.c`, `include/bt820_regs.h`.
Evidence: **HOST_TESTED** (266 checks incl. ASan/UBSan, 4 killed mutants, R06 regression probe).
Nothing here has run against BT820 silicon.

## Sources checked at the source (MANUFACTURER_DOCUMENTED)

| Ref | Document | Where |
|---|---|---|
| DS | DS_BT820 v1.1 (BRT_000427), SHA-256 `a6d494e0…124d367` | §4.5.1 protocol, §4.5.2.1–3 read/write/host command (PDF pp. 21–26), Table 28 timing |
| AN | BRT_AN_086 BT82X Programming Guide v1.4, 2026-09-07, SHA-256 `0e9a634c…e24c75` | Table 2 memory map (p. 14), §2.3 Table 3 host commands (pp. 17–19), §2.4 Table 6 chip ID, §2.5 boot sequence (pp. 20–21), §2.14 swap chains, Reg. Defs. 114/115/125–128/144 |
| EA | Bridgetek EveApps-BT82X, commit `6b5a57eb55e6729a80980655a0b6b7ab2e89a16f` (MIT) | `common/eve_hal/EVE_HalImpl_RP2040.c` (`EVE_Hal_startTransfer`, `rdBuffer`, `EVE_Hal_transfer32`), `EVE_Hal.c` (host-command bytes), `EVE_Util.c` (`EVE_Util_bootup`), `EVE_GpuDefs.h` (absolute addresses), `application/Common.c` (`Display_Config`) |

## 1. The R06 defect and its correction

R06 refused every write at or above 0x7F000000. It did this because such a write begins with
byte 0xFF, the same as the host-command prefix. AN Table 2 places the **command FIFO
(0x7F000000)**, **both core register regions**, **the display list** and **all system/LVDS
registers** in that range, so the R06 rule blocked all normal use. The R07 handoff called this
out as P0, and the R07 probe (`make r06-probe`) reproduces the defect on the frozen R06 code.

R07 rule: **any access must lie entirely inside one documented region**. These are AN Table 2
plus REG_CMDB_WRITE (AN Reg. Def. 128, 0x7F010000, one word); usable RAM_G is the attached DDR
size minus the reserved top 2.5 MiB (AN §2.1). Everything else is refused before touching the
bus, as AN Table 2 note 1 says ("reserved and shall not be read from or written to").

### Why a valid write cannot be mistaken for a host command

| Frame | Byte 0 | Byte 1 | Bytes 2–3 | Total length |
|---|---|---|---|---|
| Host command (AN Table 3) | 0xFF | **0xE0–0xEB** | param, 0x00 | **exactly 5** |
| ACTIVE | 0x00 | 0x00 | 0x00, 0x00 | exactly 5 |
| Write to RAM_CMD/REG_CORE/RAM_DL | 0xFF | **0x00** | addr | ≥ 8 (4 address + ≥ 4 data) |
| Write to REG_CMDB_WRITE | 0xFF | **0x01** | 0x00 0x00 | ≥ 8 |
| Write to REG_LVDSTX/SYS/LVDSRX/I2S | 0xFF | **0x80** | addr | ≥ 8 |

Addresses 0x7FE0_0000–0x7FEB_FFFF, the only writes that would share the host-command second
byte, are not in the memory map. The driver refuses them, and also has a defensive check that
no write frame starts `FF E0..EF`. Bridgetek's reference host (EA `EVE_Hal_startTransfer`)
emits `(addr>>24)|0x80` with no special case, which is the same framing.

**Still unproven:** how the silicon decodes it, i.e. whether it uses byte 1, the length, or
both. Vendor question Q2 and bench step B1.4 (logic-analyser capture of a RAM_CMD write and a
host command) close this.

## 2. Framing implemented (DS §4.5.1, EA)

```
write : (A30..24 | 0x80) A23..16 A15..8 A7..0  D0 D1 D2 D3 ...   (CS# held for the burst)
read  : (A30..24)        A23..16 A15..8 A7..0  poll 0x00.. 0x01  D0 D1 D2 D3 ...
host  : 0xFF code param 0x00 0x00                                 (single channel only)
ACTIVE: 0x00 0x00 0x00 0x00 0x00
```

* 32-bit units, word-aligned addresses (DS §4.5.1 "transactions are word based").
* **Byte order: little-endian.** EA `EVE_Hal_transfer32` sends `value & 0xFF` first and
  assembles reads as `b0 | b1<<8 | …`. This retires the R06 byte-order assumption, at the level
  of the vendor reference, not yet silicon.
* Read polling: the driver clocks single bytes until 0x01, with a configurable limit (R06/R07:
  64), then reads the data. EA polls in 8-byte blocks (`POLLING_BYTES`) and copies data that
  follows 0x01 inside the block. Either way is valid. The F133 binding must keep CS# asserted
  across calls.
* CS# high for at least 2 SCK cycles between transactions (DS §4.5.1) is the HAL's job, and is
  checked on the bench.
* Burst reads/writes of internal registers are allowed only in single and dual modes; quad mode
  bursts only to DDR (DS §4.5.2.1–2). Not an issue: only single mode is used.

## 3. Host commands (AN §2.3 Table 3)

| Code | Name | Param | Rule enforced by the driver |
|---|---|---|---|
| — | ACTIVE | — | 5 × 0x00 |
| E0/E1/E2 | STANDBY/SLEEP/POWERDOWN | 0x00 | power state updated |
| E4 | SETPLLSP1 | NS/CKS | **low-power state only** |
| E6 | SETSYSCLKDIV | 0x1n | **low-power state only** |
| E7 | RESET_PULSE | 0x00 | chip stays active |
| E8 | SETBOOTCFG | DDR/touch/audio/WDT bits | **low-power state only**; needs BOOTCFGEN first |
| E9 | BOOTCFGEN | 0xC1 allow / 0xC0 lock | **low-power state only** |
| EB | SETDDRTYPE | 0x08 = DDR3L 1 Gbit 1333 MT/s | **low-power state only** |

Any other code is refused. All host commands are refused outside single-channel mode ("ignored"
by the chip, AN §2.3). After RST_N the chip is in SLEEP (AN §2.3), and the driver mirrors that
in `bt820_note_hw_reset`.

## 4. Boot and identification (AN §2.5, EA `EVE_Util_bootup`)

RST_N low 1 ms → high; BOOTCFGEN(C1) → SETBOOTCFG(80) → SETDDRTYPE(08) → BOOTCFGEN(C0) →
SETSYSCLKDIV(17) → ACTIVE → 40 ms → poll REG_BOOT_STATUS (0x7F80044C) until **0x522E2E2E**
→ REG_CHIP_ID (0x7F800448) = **0x08200100** (AN Table 6) → REG_ID (0x7F006000) low byte
= **0x7C** (AN Reg. Def. 144) → REG_CPURESET (0x7F006088) = 0. Each failure has its own
code and the report keeps the raw values. The tests check the exact 6-frame host-command
sequence byte for byte.

Correction to the R07 handoff: it says "Read REG_ID (expected 0x7C)". That is correct, but
REG_ID only proves an EVE-family device is running. The BT820B-specific check is
**REG_CHIP_ID = 0x08200100**, and the driver checks both.

## 5. Command FIFO and first frame (AN §2.2, §5; EA)

Ring of 16 KiB at RAM_CMD. The host keeps `wp`, reads REG_CMD_READ (0x7F00614C) for free space
(one word kept empty), writes words at RAM_CMD + wp (splitting at the wrap), then writes
REG_CMD_WRITE (0x7F006150). REG_CMD_READ = 0x3FFF means a coprocessor fault. Test frame:
`CMD_DLSTART, CLEAR_COLOR_RGB, CLEAR(1,1,1), DISPLAY, CMD_SWAP, CMD_GRAPHICSFINISH`. AN §2.2
recommends going through RAM_CMD rather than writing RAM_DL directly, which is followed here.

## 6. Scan-out (AN §2.14, EA `Display_Config`, `EVE_Util_config`): data **unconfirmed**

The sequence is: video timing registers, REG_DISP=1, LVDSTX_PLLCFG (EA formula), LVDSTX_EN=CH0,
SC0_SIZE=2, SC0_PTR0/1 (EA 36 MiB / 45 MiB), SO_MODE, SO_SOURCE=SWAPCHAIN_0, SO_FORMAT=RGB8,
SO_EN=1, then CMD_RENDERTARGET(SWAPCHAIN_0, RGB8, w, h). The timing values come from the R05
candidate-panel plan (1280×625 total, 1024×600 active, 48 MHz, SO mode 0, TX clkdiv 5). R05
itself marks them `TABLE_ARITHMETIC_INFERENCE_REQUIRES_PANEL_CONFIRMATION`. A lit, correct
picture is a bench result, and none exists.

## 7. Not done / open

Dual/Quad SPI (needs the F133 SPI register check; REG_SYS_CFG SPI_WIDTH bits 9:8 in ACTIVE).
Watchdog/touch/audio enables. Asset loading from BT820's own flash or SD. Error recovery via
REG_CPURESET. Silicon confirmation of section 1.
