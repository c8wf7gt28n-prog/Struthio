# ARC1-PASS-0002 handoff — R10 hardware facts and branding

- **State:** REVIEW. Waiting for an independent reviewer (COV-003).
- **Owner:** agent:claude-code
- **Base commit:** `8cb940ed711f76c743635f1384bbe09e78b4561b` (ARC1-PASS-0001)
- **Board revision:** R10-development, **fabrication HOLD**
- **Risk tier:** MEDIUM, because the hardware schema had a breaking change
  (0.2 → 0.3).

## Reproduce

From a clean checkout with full git history, in `arc1/`:

```sh
./arc1 doctor
./arc1 hw inspect
./arc1 hw inspect --manifest passes/ARC1-PASS-0002/reports/tampered-source-r10.hw.json; echo "exit $?"
./arc1 pass validate passes/ARC1-PASS-0001
./arc1 pass validate passes/ARC1-PASS-0002
python3 tests/run_tests.py
```

Expected results:

- `hw inspect` prints PASS with a "Fabrication status: HOLD" warning.
- The tampered-source manifest prints FAIL HW-001 ("cited source changed:
  …DECISIONS.md") and exits 1.
- Both pass records print PASS with the COV-003 warning. PASS-0001 is
  checked at its own commit, so this pass's manifest rewrite does not break
  it.
- The suite runs 43 tests and reports OK.

To check the vendored sources against the original handoff, extract the six
archives (their digests are in `hardware/sources/r10/PROVENANCE.md`) and
compare each file in `hardware/sources/r10/SHA256SUMS` with
`arc1-compact/HANDOFF_MANIFEST_SHA256.txt`.

## What was delivered

- **Main change:**
  - **Manifest:** `hardware/manifests/arc1-r10.hw.json` was rewritten from
    the owner's R10 handoff. It records:
    - the four chips with manufacturers, exact ordering codes, datasheet
      references, power rails, clocks and boot dependencies
    - seven peripherals: the central and D213 NOR, ADV7513, TPD12S016,
      TS3USB221A, USB2514B, and the TLV62569P FPGA buck with its
      power-good finding
    - five links with full pin lists: F133↔12F RGMII, D213 GMAC0↔45F RGMII,
      F133 USB1↔D213 USB0, D213 RGB888→ADV7513 and F133 I2S2→ADV7513
    - ten open uncertainties

    All links stay `proposed_unverified`, all claims stay `not_tested`, and
    `fabrication_status` is `HOLD`.
  - **Vendored sources:** 14 handoff files in `hardware/sources/r10/`,
    byte-identical to the originals, with `SHA256SUMS` and `PROVENANCE.md`.
    PROVENANCE.md records the archive digests and the host-check
    reproduction.
  - **Logo:** `docs/assets/arc1-logo.jpg` is a 1086×362 copy of the owner's
    logo (byte-identical to `R10_WORK/branding/ARC1_logo.png`), shown in the
    README.
  - **Docs:** README, AGENTS.md, `docs/MIGRATION.md` and TRACEABILITY.
- **SDK change (covenant):**
  - Hardware schema 0.3 adds sources, peripherals and fabrication status.
  - `hardware.py` checks:
    - each cited file exists, is unmodified and stays inside the SDK
    - each reference resolves to a listed source
    - each `#anchor` occurs in its source
    - board links cite at least one source
    - peripheral attachments are known
    - fabrication status agrees with the simulation flag, and RELEASED needs
      board evidence
  - `hardware/tools/r10_links.py` derives each link's pin list from the
    vendored interface table, and a test requires the manifest to match it.
  - 11 new negative fixtures and 1 positive fixture.
  - Beneficiary: every later manifest edit.
- **Effort:** 60 planned task units, 12 reserved for the SDK change (20%).
  Actual effort was not measured.
- **Deviation from COV-001, again:** no PLANNED record was committed before
  the work. The budget was written down at the end. The next pass should
  commit its PLANNED record first.

## Checks run

| Check | Level | Result |
|---|---|---|
| `arc1 doctor` | STATIC_CHECK | PASS |
| `arc1 hw inspect` (R10) | DESIGN | PASS |
| `arc1 test examples/hello_arc1` | HOST_SIM | PASS 4/4 |
| Hardware traceability suite (schema, lock, hardware, package tests) | STATIC_CHECK | PASS |
| Host SDK and covenant suites | HOST_SIM | PASS |
| R10 `run_host_checks.sh` on a clean handoff copy | HOST_SIM | **FAIL**, 13/16 (see below) |
| Tampered cited source rejected | STATIC_CHECK | FAIL as intended (artifact) |
| Protected-file disclosure (TST-003) | STATIC_CHECK | Fired on 7 real modifications before they were disclosed, then passed |

The full `tests/run_tests.py` (43 tests) also passed.

## R10 host checks: why 3 of 16 steps fail

The log is `reports/r10-run-host-checks.log`.

- **Bootloader:** `firmware/f133_bootloader` stops at a `git diff` step,
  because the handoff ships without `.git`. Inside a temporary git
  repository the whole step passes (`reports/r10-f133-bootloader-in-git.log`,
  all mutants killed).
- **CAD:** `cad/gen/design.py` and `crosscheck_r10.py` need the KiCad
  standard footprint library at `/usr/share/kicad`, which was not installed.
  The handoff's own log shows them passing on a machine that had it.
- Every generator that ran reproduced its committed output byte for byte.

None of these is a design defect. All three are gaps in how the handoff
reproduces. I did not change the handoff.

## Not run / not available

- RTL and P&R (`run_all.sh`): the FPGA toolchain is absent.
- Any board test: R10 is on HOLD.
- TST-004 independent reproduction of PASS-0001 or PASS-0002.

## Known limitations

- The SDK's C API and host runtime have not changed. Nothing in them is
  mapped to R10 hardware yet. HDMI, USB and the cartridge appear only in the
  manifest.
- Anchors are checked as plain substrings, so an anchor proves the text
  exists in the source, not that the source says what the manifest claims.
  Each value still needs a reviewer to read the cited passage.
- `PROMPT_FOR_CLAUDE.txt` in the handoff is stale R06 guidance. It was
  ignored in favour of `START_HERE.md` and `CLAUDE.md`, as the handoff README
  directs.
- Two R10 owner confirmations are still listed OPEN in `R10_WORK/BASE.md`:
  the fourth programmable device and the BT820 replacement. The decisions log
  records them as delegated (D2). The manifest repeats this as an
  uncertainty and does not resolve it.

## Suggested next pass

1. Map the game API's audio and input paths onto R10 as capability
   declarations: HDMI audio through F133 I2S2, controllers through the
   USB2514B. They stay `ARC1_E_UNSUPPORTED` on the host until a target
   exists.
2. Make the R10 host checks reproducible without git or a system KiCad
   install, as a change to the R10 tree itself, owned by the hardware
   engineer.
