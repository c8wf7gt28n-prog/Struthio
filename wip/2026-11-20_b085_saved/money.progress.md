# money (0.8.5 money and dates) progress

DONE. Patch: b085/money.patch (12 files, applies to HEAD with git apply --check). Result: b085/money.build.result.json.
- New: workbench/math_typed.py, math_money.py, math_dates.py; tests_integrated/test_math_money_dates.py (23 tests).
- Changed: stac_bridge (money/dates forms, owners_only), stacy_control, engineering_kernel, engineering_cli, tool_selection
  (Money and dates family), docs/INTEGRATED_I02.md (new section, 6 worked examples), registry record, check_hatch (own line).
- Tier 0 both looks 0 failing (870 tests); 24 affected modules pass (see result JSON).
- Throwaway copy deleted; scripts and logs kept under b085/money/.
