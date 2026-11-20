# maths fix run (after review) - worktree wf_9807ad9e-481-6
- Applied b085/maths.patch (registry hunk excluded; registry regenerated in the copy and copied back).
- DONE: must-fix 1 (planner guard over every string argument; GIVEN_IS_THE_OWNERS words), must-fix 2 (sound-range check words),
  should-fix: owner-word refusals, inward rounding of allowed ends, guarantee only when rechecked, == once, too-long numbers,
  integer range ends, given on the solved quantity refused, 'for' only on solve, hashes once, stac.status math_grammar, docs,
  window tests (Terminal + Kasandra receipt link).
- test_math_core 33 OK, test_math_lines 13 OK, both looks (first run).
- Fails-before shown: on the builder's code (recovered by undoing this run's edits, fix/rev.py) the 8 new core tests and 3 line
  tests fail; the window test fails with the old Terminal and with the old Kasandra side (fix/win_before.sh).
- Frames retaken (both looks, 1366x768): b085/maths/fix/frames/*.png, read: answer, exact end, receipt, 'Apps', no keys.
- Patch rewritten (143528 bytes, 16 files); it applies to a clean archive of HEAD (apply --check, no errors).
- Tier-1 list (73 modules) both looks: 146 of 146 module runs OK, 1186 tests each look, 0 failures/errors/skips.
- DONE. Result: b085/maths.fix.result.json. Copy deleted.
