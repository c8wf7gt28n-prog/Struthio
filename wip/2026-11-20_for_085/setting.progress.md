# setting (remove appearance.cursive) - progress
- Started. Survey done. Plan: drop spec (settings_registry), CURSIVE_DEFAULT, session field+loader, session_settings write/refresh,
  ledger_control.value, control_qt readback+restyle loop; shell2.cursive_on removed (pleasantry asks _script_ready());
  SCRIPT_ON/quiet-script drawing kept (used by QuietWords, quiet_script, pleasantry, Wordmark, Apps captions, chrome_css; pinned by test_graphite).
  check_settings_02_ui: step moved to appearance.writing_marker. test_lit_controls rewritten; test_settings_advanced cursive test moved to writing_marker.
  Regenerate docs/GRAPHITE_0.1_REGISTRY.json with tools/record_registry.py (in copy, then copy back the json).
- Next: edits.
- DONE: all source/test/tool/doc edits in worktree; registry record regenerated (49->48 settings); patch written and applies (setting.patch).
- New tests fail before (2 of 3 in test_lit_controls failed on reverted copy) and pass after (graphite look).
- RUNNING: tier-1 modules (61) in both looks + check_settings_02_ui both looks via setting/batch.sh -> setting/summary.txt
- Next: read summary, fix failures, write result JSON.
