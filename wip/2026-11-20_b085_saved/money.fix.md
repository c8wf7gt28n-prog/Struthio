RESTART NOTE (coordinator, 20 Nov 07:12 UTC): the 5-hour usage limit stopped this fix at about 06:33. The fixer's worktree as it stood is saved as money.wf_2a0093ca-846-3.patch (the builder's patch plus the fix work so far; compare with money.patch to see what the fix had changed). Start from it if it applies and is sound; the scripts in money/ (edit_dates.py and others) show what was under way.

# money fix (after review)
- started: applied money.patch to fresh worktree (HEAD fbd8f27), clean.
- restart 2 (this run): fresh worktree at 6c88fc9; applied money.wf_2a0093ca-846-3.patch (builder + partial fix) cleanly.
- 1st save: all four must_fix and the cheap should_fix coded, tests added (not yet run); docs updated; patch rewritten.
  Next: copy, run test_math_money_dates both looks, then the importers (tool_selection, stac_bridge users).
- test_math_money_dates: 33 tests, both looks: 1 failure in my own new assertion (offered() limit 6 too small for the power-budget guard); fixed with limit 50.
- displacement rule added in tool_selection: when Money or Dates matches, the sheet's maths ('calculate' family) is offered only by name
  (budget plan was 5,590 chars with 5 calc schemas; target < 5,000).
- running now: 17 modules both looks (runall.sh -> money/runall.default, runall.kasandra). Then prefix.sh (new tests vs builder code).
- found by the run: 'check the power budget of the board' got math.money via 'budget' and lost the sheet's maths. Fixed: 'budget' and
  'allowance' out of the single words (budget phrases instead), and displacement only when Money/Dates match by MORE words than calculate.
  Patch saved. Next: runfinal.sh (13 modules both looks) after runall finishes; then prefix.sh; then result JSON.
- DONE. final run (runfinal.sh) 13 modules both looks OK; earlier run 17 modules both looks OK (bar one stale assertion of mine).
  prefix.sh: 10 of 33 fail on the builder's code (7 F, 3 E). mutfix.sh: the reviewer's 3 uncaught mutants (4 variants) now fail.
  Registry regenerated in a copy and copied back. Copy deleted. Patch rewritten and checked.
