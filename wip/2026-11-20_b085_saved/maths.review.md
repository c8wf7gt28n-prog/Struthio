# Review of "maths" (0.8.5, the one maths core in lines)

Status: DONE. Verdict: accept after fixes (2 must-fix, both small). Result: b085/maths.review.result.json.

## What I ran
- Fresh copy of main (e4ce22b) + the patch. Every hunk applies except docs/GRAPHITE_0.1_REGISTRY.json (main moved since the
  builder started: the "setting" item landed). Applied the rest with --exclude, regenerated the registry
  (record_registry --check: 775 ops served, no differences). Regenerate it at merge.
- Tier-1 list for the change (73 modules from run_tiers.plan(1)), each module alone, nice/unshare, fresh HOME:
  default 73/73 OK, 1176 tests; kasandra 73/73 OK, 1176 tests; 0 failures, 0 errors, 0 skipped.
  (Builder said 1174: main gained 2 tests since.)
- Five reverts, one at a time in a second copy, each caught by the tests named:
  strict lattice step (test_3, test_10); tolerance applied when RECHECK (test_23); freshness forced CURRENT (test_19);
  everything ATTAINED (test_11, test_18); no corner witness (test_2, test_6, test_17).
- 35 adversarial inputs to math_answers.ask (never raised) and kernel probes (review/probe_*.py).
- Frames read: the Kasandra-side solve (default look), the receipt and the Terminal (kasandra look).

## Must fix
1. Kasandra can still put her own range into a maths line: stacy_control.validate_actions checks only stac.* and math.answer.
   A provider plan with investigation.step (or investigation.check, agenda.add, agenda.suggest) whose `program` is a math line
   with `given` is ACCEPTED; investigation.step then runs it and records "Holds ... 15 to 16 MiB to spare" on her range.
2. Check words overclaim on a sound (loose) range: "x*x >= 0" over x -1..2 says "the ranges reach both sides of it" (false:
   it always holds); "x*x <= 4" over -1..2 says "with 0 to 6 to spare" (true spare 0 to 4). The range stage says "may be
   wider"; the check stage does not.

## Should fix: see the result file.
