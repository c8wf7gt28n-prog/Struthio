# F133 boot-pin policy (R07)

Machine-checked in `R07_WORK/board/r07_board_plan.json` (`f133.boot_policy`, rules `boot.*` in
`check_board_plan.py`, 6 new negative tests). Evidence: **PLANNING_CALCULATED** against
manufacturer tables. Not measured on a board.

## Sources

| Ref | Document | Note |
|---|---|---|
| F133-DS | Allwinner F133 Datasheet (rev. history to v1.4), SHA-256 `59d743fa…b69b2` | eLQFP128 pin list (Table 4-2), mux (Table 4-3), PC3–PC7 pull-ups 12–18 kΩ (Table 5-3), BROM features (§2.2.1) |
| D1H-UM | Allwinner **D1-H** User Manual v1.0 (2022-01-18): two mirrors, bbs.aw-ol.com (SHA-256 `fe5e5287…dfc9d`) and github.com/devdotnetorg/Allwinner-SoC (`b1db27dd…486167f`) | §3.3.2.1 Tables 3-4/3-5/3-7, §3.4 VER_REG |
| (not obtained) | F133 User Manual v1.0 (mangopi.org mirror cited by the R07 handoff) | **TLS certificate expired; not downloaded** (verification was not bypassed). linux-sunxi copies sit behind a Cloudflare challenge. |

**Transcription check against the R07 handoff.** The handoff quotes "F133 User Manual §3.4.2.1
Tables 3-4 and 3-5". The D1-H manual has the same table content at **§3.3.2.1** (section
numbers differ between the documents): 00 = SPI NOR→SPI NAND; 01 = SMHC0→SPI NOR→other;
10 = SMHC0→SPI NAND→other; 11 = SMHC0→EMMC2_BOOT→EMMC2_USR→other. **No discrepancy in
content.** The D1-H is the D1s/F133's sibling with the same BROM description. Applying it to the
F133-B is an **ASSUMPTION** that the bench check below must confirm.

## Rules from the manual

1. eFuse **BOOT_MODE = 0** → GPIO pins select (Table 3-5). **BOOT_MODE = 1** → eFuse select
   (Tables 3-6/3-7), and the straps are ignored. Do not assume the straps win.
2. Pin status is readable at **VER_REG 0x03000024 bits[12:11]** (BOOT_SEL_PAD_STA). eFuse
   select bits are at SID **0x03006210 bits[27:16]**.
3. A Fast Boot register in the RTC (0x07090120) overrides both when non-zero (Table 3-8). It is
   cleared on power-on in normal parts. Read and log it at bring-up.

## Board policy (R07)

| Pin | F133 function | Shared with | Strap | Resistor | Reason |
|---|---|---|---|---|---|
| PC4 | BOOT-SEL0 / SPI0-MOSI | T35 GPIOL_82 input | **1** | 10 kΩ pull-up to 3V3 | Also matches the internal PU reset state (Table 4-2) |
| PC5 | BOOT-SEL1 / SPI0-MISO | T35 GPIOL_83 tri-state output | **1** | 10 kΩ pull-up to 3V3 | Also matches the internal PU |
| → code | **11**: SMHC0 → EMMC2_BOOT → EMMC2_USR → other media | | | | microSD first; no eMMC fitted |

**Robustness argument** (checker rule `boot.sd_first` plus negative test). Codes **01, 10 and
11 all try SMHC0 first**; only **00** does not. A boot failure therefore needs *both* pins held
low while the BROM samples them.

**T35 kept off the strap pins.** R06 had a 10 kΩ *pull-up* on T35 CRESET_N, so the FPGA
configured itself in parallel with the F133 boot. A faulty bitstream could then drive PC5 (its
MISO pin) low during F133 reset. R07 changes it to a **4.7 kΩ pull-down**, so the T35 stays
unconfigured until F133 firmware drives PE8 high. While unconfigured, every Trion GPIO is in
weak pull-up (T35 DS), which helps keep the straps at 1. Worst case against the internal CRESET_N
pull-up (27 kΩ min): 3.40 V × 4.7/(4.7+27) = **0.504 V ≤ VIL 0.8 V** (rule
`boot.t35_held_in_reset`). Cost: the FPGA no longer starts on its own. That is acceptable: it is
optional, and the F133 owns its lifecycle (PASS_6 principle 3). PE8 becomes a push-pull output.

**Back-powering.** T35 and F133 share the 3V3 rail (single rail in the plan), so no pin sees a
powered driver on an unpowered device, except while one regulator ramps before another.
Sequence and ramp rates are in `R06_WORK/docs/ARCHITECTURE_R06.md` §4. A "T35 unpowered"
configuration exists only if a separate T35 VCCIO switch is added. Then PC4/PC5 must be checked
for injection into unpowered T35 pads (not in the current plan).

## Recovery path

* UART0 console on PE2/PE3 (Function6, VCC-PE 3.3 V): reserve a header or test pads.
* **USB0-DM/DP (pins 114/115)** reserved for USB FEL (`f133.analog_reserved`).
* The F133 eLQFP128 pin list has **no FEL pin**. (D1-H UM §3.3.2.2 describes a FEL pin with
  status at 0x03000024 bit 8; F133-DS Table 4-2 lists none.) The documented entries are the
  "mandatory upgrade process through USB and SD card" (F133-DS §2.2.1) and, by the BROM flow,
  FEL when no medium yields a valid BOOT0. **ASSUMPTION** that removing the microSD drops the
  F133 into USB FEL; verify on a D1s-class board (e.g. MangoPi MQ-R, R07 handoff S9).
* A known-good recovery microSD image (the R07 bare-metal banner image, `R07_WORK/f133_boot/`)
  should be kept.

## Bench checks (stage A of `BENCH_BRINGUP_PLAN.md`)

1. Power the board with T35 CRESET_N held low. Scope PC4/PC5 through the F133 reset release:
   both must stay ≥ 0.7 × VCC-IO.
2. Boot the banner image. It prints VER_REG[12:11] (expect `11`), SID 0x03006210[27:16] and the
   Fast Boot register.
3. Remove the card: confirm USB FEL enumeration (`sunxi-fel version` on a PC).
4. Release CRESET_N from firmware, confirm CDONE, then repeat steps 1–2 after a warm F133 reset
   with the T35 *configured*. The SS_N pull-up keeps T35 MISO tri-stated.
