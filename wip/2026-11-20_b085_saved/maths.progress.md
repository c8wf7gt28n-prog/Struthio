# maths builder progress
- DONE. Result file written: b085/maths.build.result.json; patch b085/maths.patch (16 files, applies to a clean HEAD).
- Built: workbench/math_ranges.py, math_answers.py (math.answer), tolerances.py; stac_bridge grammar + freshness; Kernel/CLI registration;
  ALWAYS_ASKS row; planner guard in stacy_control; window words (readable_result, shell2 receipt link, console_qt); docs/INTEGRATED_I02.md
  grammar + 3 Rail Demo examples; tests test_math_core (25) + test_math_lines (11) in FOCUSED_MODULES; registry record regenerated.
- Checked: tier-1 list (73 modules) both looks, 1174 tests each, 0 failures; reruns after last change OK; fails-before shown.
- Frames (1366x768, both looks): b085/maths/frames/*.png
- Not done: Then row "Solve for..."; goal face (vectors 27-30); window checks not run.

# fix run after the review (worktree wf_9807ad9e-481-6; notes in maths.fix.md)
- Both must-fix items fixed: the planner guard reads every string argument of any command (investigation.step/.check,
  agenda.add/.suggest, stac.*), and a check over a sound range says "at least" and never "the ranges reach both sides".
- Should-fix items fixed: refusals in owner words, allowed ends rounded inward, EXACT_ALLOWED_SET only when rechecked, an
  equation's end said once and exactly, too-long numbers, whole ends for integer quantities, a given on the solved quantity and
  'for' outside solve refused, hashes once at import, stac.status math_grammar, docs (ID, how to set a tolerance), window tests.
- Registry regenerated against e4ce22b (4 operations added). Patch rewritten; it applies to a clean HEAD.
- Tests: test_math_core 33, test_math_lines 13, OK in both looks; new tests fail on the builder's code. Tier-1 list (73 modules):
  OK in both looks, 1186 tests each. DONE; result in maths.fix.result.json.
