# money (0.8.5 money and dates) progress

DONE. Patch: b085/money.patch (12 files, applies to HEAD with git apply --check). Result: b085/money.build.result.json.
- New: workbench/math_typed.py, math_money.py, math_dates.py; tests_integrated/test_math_money_dates.py (23 tests).
- Changed: stac_bridge (money/dates forms, owners_only), stacy_control, engineering_kernel, engineering_cli, tool_selection
  (Money and dates family), docs/INTEGRATED_I02.md (new section, 6 worked examples), registry record, check_hatch (own line).
- Tier 0 both looks 0 failing (870 tests); 24 affected modules pass (see result JSON).
- Throwaway copy deleted; scripts and logs kept under b085/money/.

FIX AFTER REVIEW (20 Nov, second run; first fix run was cut off at the usage limit). Patch b085/money.patch rewritten (12 files,
applies clean to HEAD 6c88fc9). Result: b085/money.fix.result.json; notes: b085/money.fix.md.
- must_fix 1: a name given one date counts months, years and business days (the name stays, plus the days reached); left to right
  from the date or name that starts a sum, anything else refused (precedence kept).
- must_fix 2: round must be a positive decimal step; deadline/business/expression fields checked in words; typed.answer inside the
  try; no exception leaves math.money or math.dates (Kernel.dispatch returns a refusal state).
- must_fix 3: two narrow families (Money, Dates) with phrases; when one matches by more words than the sheet's maths, that family is
  offered only by name. Plans: the six reviewed messages back to their sizes without money/dates; budget request 3,264 chars.
- must_fix 4: '(exact 10/3 USD)' once.
- should_fix: clamp flag, weekend holiday and precedence guard now caught by tests (mutants fail); left-to-right or refuse; dates
  outside 1..9999 DOMAIN_ERROR; end excluded edges (count >= 1, no-day-inside refused, business day before); business days by
  whole weeks; helpful refusals for 1,200 USD, $10, 10 usd, 1e3 USD, 1 Month, businessday, dotted dates; each kind's reason in solve;
  round field described in the schema. Registry record regenerated (round's schema digest changed).
- Tests: 13 modules both looks after the last change, all OK (test_math_money_dates 33). Not done: holidays-source reading (owner).
