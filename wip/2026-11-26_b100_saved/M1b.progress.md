# M1b progress (her model's memory cap and her measured rates)
Worktree: /home/user/Struthio/.claude/worktrees/agent-acf6d57a9a917c175 (HEAD fb024e1)

DESIGN (decided after reading code + tests):
- Part 1 cap: her explicit cap stays the resident budget (admission + RSS guard). On the processor the worker's
  address-space limit (RLIMIT_AS) = max(cap, quick_model.cap_mb(rung estimate)) via new brain_worker --address-space-mb.
  New workbench/brain_cap.py: address_space_mb(config), plan(value, options,...) -> state ROOMY/CLOSE/FEWER/NOT_LOADED/AUTO + words.
  Brain room (brain_qt) shows plan words under launch fields (cached by inputs). Model check S0 records/says it.
  Why not M2's rule on the resident cap: refuses caps < est+max(2G,half) (38,994 MiB for the 35B fixture), pushes 4B to
  reuse-off rung, breaks ~10 tests + campaign R07/R08/R15; M2 measured RSS ~ estimate, the overrun is address space.
- Part 2 rates: new workbench/tuning_rates.py carry_out(run) (inside Work: copy throwaway measured_rates.json to
  run/tuning_rates.local.json), keep(run) (owner profile: runtime_tuning.remember each). Called: model_check.s2t (carry),
  end of go() inside Work (carry), after Work (keep: console runs too), model_check_qt.finished (keep). runtime_tuning.measured
  cache invalidated by file mtime.

STATUS:
- DONE code: brain_cap.py, tuning_rates.py (new); marked 1.0 M1b edits in local_brain (_start_server argv + worker
  address_space_mb), brain_worker (--address-space-mb), runtime_tuning.measured (mtime), model_check (s0 cap words, s2t carry,
  go carry+keep), model_check_qt (keep in finished), brain_qt (cap_line + show_cap). Patch saved (M1b.patch).
- DONE stand-in smoke (M1b/standin.log, exit 0) + frames graphite/kasandra/day (M1b/frames/) with the first wording.
- Words shortened after the frames ("Close: ...", "Fewer kept prompts: ...") -> re-run standin + frames after live.
- DONE live (M1b/live_run1.log, live_check.log): 4B cap 5,852 near rung 5,596, AS limit 8,394, sealed, PLAN/READ KEPT,
  PLAN TAKEN, READY; console model check S2T carried+kept plain rates 50/5; her key == check key; measured None -> (50,5).
- DONE re-run standin_all (new words), frames read (graphite/kasandra/day, 2 sizes). APPLY_CHECK_OK on fb024e1.
- DONE result JSON (M1b.build.result.json); copy deleted.
- (old) NEXT: live run (bash M1b/run.sh live M1b/live.log, under the lock; cap = rung(6,cache4) estimate + 256), then
  re-run standin_all.sh, read frames, applycheck, result JSON, delete copy.
- No existing test changed (configuration's rule unchanged: the fixture numbers in standin.log match the tests).
