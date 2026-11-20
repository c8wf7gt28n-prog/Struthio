# guards: independent review (notes, in progress)

Copy: work/b084b/guards/review/copy (main checkout tracked tree + guards.patch, applied cleanly; seed made current).

Done:
- Patch read once (20 files). bugs.json counts agree with the report: guarding 30/53 -> 51/53 (+2 on stale seed); other 40/78 -> 49/78; overall 70/131 -> 100/131.
- Registry holds schema digests, not source digests: not re-recording it in run.py is sound.

Findings so far:
- MUST (to confirm): test_release_check.Kit asserts tools/planted_bugs/run.py exists; tests_integrated ships and test_release_check is a FOCUSED module run by check_release.py --self-test from the program folder (DAILY_GUIDE): in the kit, planted_bugs is absent -> FAIL.
- MUST (to confirm): run.py leaves a planted bug in the copy when killed mid-bug (SIGTERM/SIGKILL/restart); README says a run can be stopped and started again; nothing restores or detects it -> later verdicts silently wrong.
- should: SystemExit raised in a worker thread is swallowed silently (threading ignores SystemExit).
- should: seed_bound duplicated in 7 modules.

Next: main module run both looks (running), kit check, revert two tests, restart repro, small rerun sample.
