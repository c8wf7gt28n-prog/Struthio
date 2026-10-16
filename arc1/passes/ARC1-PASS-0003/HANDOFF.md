# ARC1-PASS-0003 handoff — SDK checks outside a git clone

- **State:** REVIEW. Waiting for an independent reviewer (COV-003).
- **Owner:** agent:claude-code
- **Base commit:** `aa5808b3b52d2b092c3f19e3e368b7a504ae3df5` (ARC1-PASS-0002)

## Problem

From a source zip (no `.git`), `tests/run_tests.py` failed one test. It
validated every pass record against the current files. ARC1-PASS-0001
cites the hardware manifest that ARC1-PASS-0002 deliberately rewrote, so
its digests no longer match. In a git clone the record is checked at its
own commit and passes. The validator was right not to call it verified.
The test and the message did not say why.

## Change

- `sdk/cli/arc1cli/passrec.py` (SDK change): when no git history exists,
  `arc1 pass validate` now explains that an earlier pass must be checked
  from a git clone.
- `tests/run_tests.py` (protected, disclosed): without a git work tree,
  the repository-records test checks only the newest record, which still
  matches the current files. With git, it checks every record at its
  commit, as before.

## Reproduce

```sh
python3 tests/run_tests.py                     # in a git clone: 43 tests, OK
./arc1 pass validate passes/ARC1-PASS-0003
```

From a copy without `.git`, the suite reports OK with one skip, the
base-commit test, which needs a full clone. `arc1 pass validate
passes/ARC1-PASS-0001` still fails there, and now says why.

## Not run

- TST-004 independent reproduction.
- Any hardware check: R10 is on fabrication HOLD.
