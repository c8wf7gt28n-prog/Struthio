# R10 interconnect decisions — 2026-10-16

Authority: owner delegated unfinished design decisions. This addendum supersedes
conflicting proposals in the older change sheet; it does not constitute a fabricated
schematic, a board test, or approval to manufacture. Fabrication remains HOLD.

## Decisions made

1. Retain F133-B, D213ECV, LFE5U-45F-6BG381C and LFE5U-12F-6TG144C.
   Keep USB1-host to USB0-device, both direct RGMII links and LVDS0. Retired PBUS
   option A is not an active design conflict. Preserve existing signal assignments.
2. Select **AS4C16M16SA-6TIN**, industrial 54-pin TSOP-II SDRAM, 32 MiB.
   The generated map now names all 39 signal pins and all 15 supply/ground/NC pins.
   No address/control swaps are permitted without changing constraints and review.
   Keep the existing controller rate; the part's rating is not a board timing proof.
3. Retain APS3204L-3SQNA-SN 4 MiB PSRAM intent. Do not substitute an 8 MiB part
   or another package without revisiting commands, timing and pinout.
4. Select W25Q512JVFIQ, 64 MiB SOIC16 300 mil, with dedicated RESET pin 3.
   Q suffix defaults QE to 1; do not rely on IO3 functioning as HOLD or RESET.
   Preserve central F133-owned flash and the D213 DNP boot-flash fallback.
   Define independence as **continued D213 operation after successful boot**, not
   cold boot while F133 is held reset. A single F133-owned NOR cannot satisfy that
   latter requirement. Do not populate a second flash merely to disguise this limit.
5. Production FPGA configuration requires real rail-good evidence. A constant
   VCC_PG=1 is forbidden. No production BSP exists yet, so this is a binding
   contract correction, not a claim that hardware gating is implemented.
6. Recovery must disconnect **both USB data lines** from the F133 host before a
   PC is attached to D213 USB0. Select a power-off-only service disconnect for the
   first prototype: disconnect the internal host data/VBUS link, then connect the
   recovery fixture. No live two-host cable or testpoint-only recovery connection.
   Connector/fixture routing and VBUS isolation still need schematic review.
7. Enable the internal USB host path after rails/reset are valid, before attempting
   ROM download. Wait for ROM enumeration, transfer firmware, then wait for the
   application-ready handshake. Never wait for application-ready before supplying
   the USB connection needed to load that application.
8. Both RGMII CPU drivers use fixed 1 Gbit/s full-duplex operation, not PHY
   discovery/autonegotiation. FPGA forwarded receive clocks must be running before
   CPU MAC enable. Calibrate delays; do not copy an RMII example pinmux.
9. Keep HDMI as a required output. Do not silently replace it with a panel header.
   **Selected 2026-10-16 (DECISIONS.md D6): TI TFP410 from D213 RGB888 (PD0-PD27),
   strap mode, no initialisation firmware, DVI video through a type-A HDMI receptacle.**
10. (D5) Prototypes fit the D213 boot SPI NOR; the F133 drives D213 RESETN and PA0
   open-drain so it can force USB download mode with or without D213 firmware.
11. (D7) The 45F forwards 125 MHz to D213 GMAC0_CLKIN (PE3); DNP 0R and oscillator
   alternatives. Found missing while reading D21x UM 12.2.3.4 / HW guide Table 2-8.

## Electrical interlock requirements

ECP5 banks 2/3/6/7 are not hot-socket tolerant (DS-02012, section 3.6).
Our SDRAM/PSRAM and 25 MHz oscillator connections use these banks. Sequence core,
auxiliary, VCCIO and external drivers so their voltage/current limits hold during
startup, shutdown and brownout. A shared nominal 3.3 V rail alone is not proof.

- Define supervisor thresholds, rail discharge and oscillator OE in the schematic.
- Keep external memory outputs inactive until the FPGA core and relevant IO supply
  are valid; constrain behavior during rail loss, not just normal power-up.
- PROGRAMN and software waiting for DONE alone do not provide power-off isolation.
- Shared F133 SPI0 must never select NOR and FPGA simultaneously. Gate return-path
  buffer enable with both selected-device state and valid-rail state.
- Add the missing 45F rail-good sensing/interlock to the actual board binding.

## What is verified, and what is not

The inspected active maps have no newly found incompatible pin reuse across the
main processor/FPGA links. This is **pin-plan evidence**, not netlist/ERC evidence.
The old pin generator did not validate individual SDRAM package endpoints. That
gap is repaired. It still does not validate a complete board.

The old NOR map mixed eight-pin endpoints with a 16-pin recovery design. It now
uses the selected SOIC16 package throughout, including all supplies, NCs and the
dedicated RESET pin. Verified against Winbond's manufacturer datasheet Rev.B,
Figures 1b/ordering information (distributor-hosted copy). Check current revision
before procurement. Boot-ROM compatibility, status-register policy, reset pulse
timing and high-address reads still require implementation/bench validation.

Older D213 register documentation and newer SDK documentation disagree about
GMAC0 RGMII delay fields. Retain the selected link but require a pinned SDK/chip
revision confirmation and loopback/calibration before claiming it works.

## Completion gates (all required before fabrication)

| Gate | Required evidence | Current result |
|---|---|---|
| Exact packages | Memory packages selected; remaining complete board pin maps | Partial |
| R10 schematic | All supplies, bypass capacitors, reset/boot/JTAG/control and connector nets; ERC | Generated (cad/), ERC 0/0, crosscheck A-I PASS, every-pin tables generated; human review pending |
| Power | Regulator sizing, startup/shutdown/brownout interlocks and budget | Not verified |
| D213 boot | Repeated flashless cold boots and recovery, including failed downloads | Not run |
| Video | Selected HDMI bridge, documented initialization and standalone display | ADV7513 selected with embedded audio (D8, supersedes the TFP410); init sequence documented (AN-1270 + Linux driver); display NOT_RUN |
| FPGA timing | Exact TQFP144 implementation; SDRAM/PSRAM/RGMII IO timing | Not complete |
| Board links | USB/RGMII/memory stress tests, temperature/voltage margins | Not run |
| PCB release | Stackup, return paths, constraints, DRC, reviewed BOM and procurement | First placement only (Ø 119.6 mm, DRC 0 errors, unrouted); routing/planes/stack-up/DFM not done |

Host tests and proxy-package P&R do not close these gates. `check_interconnect.py`
checks the repaired SDRAM map; `--require-release` intentionally returns nonzero
while release evidence remains missing. It does not automatically grant release.

## Sources

- Alliance AS4C16M16SA-C&I Rev.3.0, Figure 1 and ordering table:
  https://www.alliancememory.com/wp-content/uploads/256Mb-AS4C16M16SA-CI_V3.0_March-2015.pdf
- Lattice ECP5 family datasheet, section 3.6:
  https://www.latticesemi.com/view_document?document_id=50461
- Current ArtInChip MAC configuration documentation:
  https://aicdoc.artinchip.com/topics/sdk/mac/mac_config_lite-lite.html
- Older ArtInChip SYSCFG register documentation (revision discrepancy):
  https://www.artinchip.com/knowledge/oxy_ex-1/topics/syscfg-register-d21x.html
- Winbond manufacturer W25Q512JV Rev.B, Figures 1b and ordering information,
  distributor-hosted copy:
  https://resources.ampheo.com/static/datasheets/winbond-electronics-corporation/w25q512jvfiq.pdf

These decisions require follow-through in schematic/BSP work. They are not a
statement that all unfinished project work is now complete.
