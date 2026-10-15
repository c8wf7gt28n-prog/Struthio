# MN820 VCC3V3 direction and module I/O levels (R07)

## Contradiction (re-checked at the source)

MN820 DS v1.0 (BRT_000442, SHA-256 `29e0a74b…`):
* §5.1 (p.17): "accepts an input voltage in the range of 3.0 to 3.6 volts" → **input**.
* Table 2 (CN1 pinout, pp.10–15): pins 13/15/17/19 "VCC3V3 P 3.3V **output** power supply".
* Table 3 (p.18): "VCC3V3 **Output** voltage range 3.0 / 3.3 / 3.6 V" *and*
  "Icc_3V3 Operating current, VCC=3V3, **245 mA** typ" (measured with a test card).

The R07 handoff quotes the first two correctly. It does not mention Table 3, which uses the
same "output" wording but gives a supply *current*, as an input would have.

## Resolution evidence (MANUFACTURER_DOCUMENTED reference design)

VM820C BT820 Credit Card Module Datasheet **v1.1** (BRT_000441), retrieved from
docs.rs-online.com (SHA-256 `4d54c766d9e09909ab2a3f47504c776c394672b8776d1e2c8cf3d82053d79046`):

* §3.1.1: "DC-DC converter steps down input power to 3.3V for system requirements".
* Figure 5 (p.17) "DC-DC BUCK CONVERTER (VSYS → 3V3)", output net **VCC3V3**.
* Figure 7 (p.19) "INTERBOARD CONNECTOR TO MN820", receptacle **CN6**: net **VCC3V3 tied to
  pins 13, 15, 17, 19** (read from the rendered schematic).
* The VM820C tables use the same "3.3V output power supply" wording for its *own* headers, where
  the 3.3 V clearly comes from the baseboard regulator. The wording describes the baseboard side.

**Conclusion (R07):** the host board **supplies** 3.3 V into MN820 CN1 pins 13/15/17/19, with
245 mA typical for a test card (allow ≥ 2× for budget, unmeasured). The module makes its own
1.1 V and 1.35 V (§5.1). Status: **resolved by reference schematic; written Bridgetek
confirmation still requested (Q1)** before first power-on. Bench step A0 first powers the
module from a current-limited supply.

## Connector

Module plug Hirose **DF40C-100DP-0.4V(51)**. Mating receptacle used on VM820C:
**DF40C-100DS-0.4V(51)**, stacking height **1.5 mm**. Alternative **DF40HC(3.0)-100DS-0.4V**
gives 3.0 mm (MN820 DS §5.3). The handoff's citation is correct.

## New finding: module-level I/O levels

MN820 Table 3 guarantees **VOH ≥ 2.4 V, VOL ≤ 0.4 V, VIH ≥ 2.0 V, VIL ≤ 0.8 V** at the
connector. R06 used BT820 chip levels (VOH = VCCIO − 0.4 V) instead. With the module figure, the
F133 input threshold VIH = 0.7 × VCC-IO is met only for VCC-IO ≤ 3.428 V. R07 therefore
tightens the 3V3 rail to **3.20–3.40 V** (±3 % including transients). The resulting margin on
the module spec is only **+0.02 V** (check `level.compatible[BT_IO1:MN820->F133]`). The test
`test_r06_rail_fails_mn820_module_voh` shows the R06 window fails. Bench: measure MISO/IO VOH at
the F133 pin. If it is near 2.4 V, add a level-restoring buffer or run the F133 PD domain at
3.3 V nominal with a tighter regulator.

## Power tree impact

The 3V3 rail feeds the F133 I/O, every T35 VCCIO bank, the PSRAM, the microSD and the MN820. The
MN820 is the largest known 3V3 load (245 mA typ). Size the regulator for MN820 + T35 VCCIO +
microSD peaks with margin. Current-limit the first power-up.
