# ARC1-PASS-0001 handoff — M0–M1 host SDK bootstrap

- **State:** REVIEW. Waiting for an independent reviewer (COV-003). The
  owner cannot accept this pass.
- **Owner:** agent:claude-code
- **Base commit:** `a5b6500994560dd9945fcabc801fd1588dc08b4b`. Before this
  pass, the repository held only the STRUTHIO web arcade. `arc1/` was added
  as a new, self-contained tree.
- **Board revision:** R10-proposed (design facts only, unverified).

## Reproduce

From a clean checkout, in `arc1/`:

```sh
./arc1 doctor
./arc1 build examples/hello_arc1
./arc1 test examples/hello_arc1
./arc1 pass validate passes/ARC1-PASS-0001
python3 tests/run_tests.py
```

Expected results: each command exits 0. `test` reports 4 tests and 0
failures. `pass validate` prints a PASS verdict with a "COV-003: awaiting
independent review" warning. The suite runs 41 tests. The gcc/clang
agreement test and the reference-`jsonschema` cross-check skip if clang or
the `jsonschema` package is missing; skipping is not failing, but say so in
your report.

Negative control required by spec §13.1:

```sh
./arc1 hw inspect --manifest passes/ARC1-PASS-0001/reports/corrupt-r10.hw.json; echo "exit $?"
```

This must print FAIL with code HW-002 and exit 1. The corrupted copy claims a
shared address space for the F133 pool.

## What was delivered

- **Main change (host demo and SDK skeleton):**
  - `arc1/game.h` ABI 0.2 and the host runtime
  - the `hello_arc1` demo: a moving sprite, mock controller replays,
    golden-frame, determinism and negative-control tests
  - CLI commands `doctor`, `new`, `build`, `sim`, `test`, `hw inspect`,
    `fpga check` and `device deploy`
  - the `arc1 new` template
  - `AGENTS.md`, the README, docs, toolchain lock, protected-path policy and
    the CI workflow (`.github/workflows/arc1-sdk.yml`)
- **SDK change (covenant contribution, separately identifiable):**
  - `sdk/cli/arc1cli/jsonschema_lite.py`: a dependency-free JSON Schema
    subset validator that fails closed on unsupported keywords
  - `passrec.py`: the covenant and pass-record validator, i.e. `arc1 pass validate`
  - `hardware.py`: the hardware-manifest semantic checks
  - the positive and negative fixtures in `tests/fixtures/*/cases.json`
    (21 pass, 12 hardware and 9 package negative cases)
  - Beneficiary: every later pass, through `arc1 pass validate`, and every
    manifest or package author.
- **Effort:** 100 planned task units, 15 reserved for the SDK change (15%).
  Actual effort was not measured; the record says `null` rather than
  inventing a number.
- **Deviation from COV-001:** no PLANNED record existed before work started,
  because this pass created the record format. The budget above was written
  down at the end, together with the implementation. Later passes must
  commit the PLANNED record first.

## Checks run (evidence in `reports/`, digests in `pass.json`)

| Check | Level | Result |
|---|---|---|
| `arc1 doctor` | STATIC_CHECK | PASS: gcc 13.3.0, Python 3.13.16 |
| `arc1 build examples/hello_arc1` | STATIC_CHECK | PASS: `-Wall -Wextra -Wpedantic -Werror` |
| `arc1 test examples/hello_arc1` | HOST_SIM | PASS, 4/4 |
| `arc1 sim … --replay tests/replays/steer.replay` | HOST_SIM | PASS |
| Covenant and manifest validator suite (20 tests, incl. cross-check vs `jsonschema` 4.26.0) | STATIC_CHECK | PASS |
| Host SDK suite (20 tests: CLI contract, goldens, tamper cases, gcc vs clang agreement, C API conformance with 111 checks) | HOST_SIM | PASS |
| Corrupted hardware manifest rejected | STATIC_CHECK | FAIL as intended (artifact, not a validation entry) |

The full `tests/run_tests.py` (41 tests) also passed. Its log is not
recorded in `pass.json`, because the suite validates `pass.json` itself.

## Not run / not available — do not report these as green

- **BOARD_TEST:** no identified ARC-1 board exists. `arc1 device deploy`
  answers NOT_AVAILABLE.
- **FPGA (G2):** no RTL in the repository. yosys and nextpnr-ecp5 are not
  installed here. `arc1 fpga check` answers NOT_RUN.
- **Target build:** no F133 RISC-V cross toolchain is locked.
- **TST-004:** no second agent or maintainer has reproduced the suite from a
  clean checkout yet. That is the reviewer's first task.
- **Not tested:** Windows and macOS. Python versions other than 3.13.16.
- **Protected-path disclosure:** no automated test covers this check.
  Every file in this pass is new, so this pass could not trigger it. It was
  exercised by hand after the first commit:
  1. A fixture copy had its `base_commit` set to that commit.
  2. One byte was added to `examples/hello_arc1/tests/golden/steer.json`.
  3. The validator failed with TST-003.
  4. Disclosing the change in `sensitive_changes` made it pass.
  5. With the same dirty tree, ARC1-PASS-0001 still passed, because it is
     checked at its own commit.

  The pass needs an automated regression test for this check.

## Known limitations

- COV-005 aggregation windows and the COV-007 impact review are not
  implemented.
- `jsonschema_lite` supports only the keywords listed in `SUPPORTED`.
- The host runtime is a behavioural model with no timing.
- The 320×180 resolution and the 16-colour palette are SDK choices, not
  display facts.
- `sdk_change` and `main_change` both list files under `sdk/cli/arc1cli/`.
  The split is by file, not by directory.

## Questions for the engineering owner (blocking for M5, not for M1)

The open questions are from spec Appendix E:

- the F133/D213 boot modes and link ownership
- the HDMI transmitter and stereo audio
- the ECP5 pin and timing plan
- the USB port allocation
- the recovery and authorization path

The R10 manifest records each of these under `uncertainties` with `null`
facts.

## Suggested next pass

M2/M3. A fresh agent should do the following:

1. Read `AGENTS.md`.
2. Change a visible behaviour of `hello_arc1`.
3. Add a reusable SDK diagnostic, for example a PPM image diff with a
   tolerance and a negative fixture.
4. Record `ARC1-PASS-0002`, including the `sensitive_changes` entry for the
   re-recorded goldens.
