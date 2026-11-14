The eight memory and model rules are fixed and committed in the worktree. The resource campaign now passes all 22 cases plainly, R19 and R22 included, with no cases left counted as "Pass (current code; the spec asks otherwise)". Nothing was pushed.

- **Worktree:** `/home/user/Struthio/.claude/worktrees/wf_4195b148-da7-1`
- **Branch:** `worktree-wf_4195b148-da7-1`
- **Commit:** `82bce35` (base `5208841`), message ends with the two required lines
- **Mirror:** `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/memory_fix_mirror/` holds all 16 changed files at their relative paths, plus `memory_fix.patch` and `COMMIT.txt`.

## Campaign evidence
The resource set was run with `unshare --pid --fork --mount-proc --kill-child <venv>/bin/python -B tools/campaign.py run --set resource --out <dir>` (and `--set all` with `GRAPHITE_CAMPAIGN_FIXTURES` set). Run folders are under `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/memfix_runs/`.

| Run | Before | After |
|---|---|---|
| resource | 22 cases, Pass 20, spec-asks-otherwise 2, Fail 0, 6 open spec questions | 22 cases, Pass 22, spec-asks-otherwise 0, Fail 0, no open spec questions |
| all | 57 cases, Pass 25, spec-asks-otherwise 2, Blocked 30, Fail 0, 7 open spec questions | 57 cases, Pass 27, spec-asks-otherwise 0, Blocked 30, Fail 0, 1 open spec question (A16) |

- **Outcome changes:** R19 and R22 went from "spec asks otherwise" to plain Pass.
- **Checks catch the change:** a run with the new code but the old expectations (`mid1_resource`) showed R07, R08, R09, R15, R17, R19 and R20 as Partial.
- **Case data:** expectations for R05–R10, R15, R17, R19, R20 and R22 now describe the new behaviour. Their `spec_question` and `spec_conflict` entries are removed, because the questions are now decided in the code.
- **Timing of the `--set all` run:** it ran just before a last wording change to `docs/CAMPAIGN.md` and the manifest rebuild. The code was the same.

## What changed, item by item
1. **Auto cap.** In `workbench/local_brain.py:200-252`, Auto now accepts a model when its estimate, the foreground reserve and 4,096 MiB of headroom fit in what is available. The 4,096 MiB headroom is my choice. The budget stays 65% of available, but never below the estimate, above the 32,768 MiB ceiling, or past the room.
   - Refusals now give the numbers, for example: "Auto needs 32,157 MiB available for this model at 4,096 tokens (its 26,013 MiB estimate, the 2,048 MiB foreground reserve and 4,096 MiB headroom); 30,720 MiB is available".
   - **Smallest accepted availability for your model:** 32,157 MiB (31.40 GiB). R08 checks both sides: 32,157 MiB is accepted, 32,156 MiB is refused.
   - **R05:** 60 GiB, budget 32,768 (the ceiling), admitted.
   - **R06:** 40 GiB, budget 26,624 (65%), admitted.
   - **R07:** 39 GiB, Auto now accepts with a budget of 26,013 and is admitted with 37.0 GiB of headroom.
   - **R08:** 30 GiB, Auto refuses with the numbers above. A 26,100 MiB manual cap is accepted; a 29,000 MiB cap is refused as `MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM`, also with numbers.
   - **R10:** a 16,384 MiB cap is refused: "the 16,384 MiB cap is below this model's 26,013 MiB estimate at 4,096 tokens".
2. **One rule for admission and launch.** `resource_control.budget_room` (`resource_control.py:66`) is now used by `decision` (`:192`), `model_room` (`:288`) and `configuration` (`local_brain.py:232`); the old 80%-of-available launch check is gone. The owner's reserve setting comes from `reserve_setting` (`:59`), which every caller of `configuration` now passes: `model_settings.py:35`, `local_brain.py:500`, `brain_qt.py:82`, `model_settings_qt.py:70`, `worker_boundary.py:408`.
   - **R15:** admitted at 34 GiB, now ACTIVATED with 1 worker and READY. With 1 MiB less, it waits at admission ("Waiting for shared-memory headroom") instead of being refused at launch.
3. **Reserve and deadline.** When installed RAM cannot be read, the full reserve stays (`reserve_bytes`, `resource_control.py:51`). A request whose reading is lost after submit fails after 30 s (`claim`, `:260-270`).
   - **R09:** the reserve without installed RAM is now 2,048 MiB (was 128). The request ends Failed with "HOST_MEMORY_COULD_NOT_BE_MEASURED: available memory could not be read for 30 s, so this request was not started", after 30.0 s.
4. **Ready means a valid reply.**
   - A restored previous model with an empty reply is no longer Ready (`local_brain.py:562-564`). In R19 it is not restored and the state is `MODEL_STOPPED`.
   - **My choice for the smaller context: refuse** (`local_brain.py:427-436`), with `MODEL_CONTEXT_BELOW_SELECTION: the worker gives 2,048 tokens; 4,096 were selected`. On Vulkan it gets one CPU retry; R19's Vulkan variant then reaches READY at 4,096 tokens.
   - **Why refuse:** Graphite passes the context size explicitly, and llama.cpp's fit option only fills in settings that were not given. So a smaller report means the worker cannot give what was selected. Marking it Ready would make later replies fail for prompts the selection allows. You can still choose the smaller context explicitly.
5. **A work hold holds.** Queued work now waits at admission with the reason "Work is held: waiting for the owner to resume work" (`resource_control.py:257-261`). Resuming refuses only while work is running and reports how many queued requests continue (`work_trail.py:185-194`).
   - **R22:** during the hold both requests stay Queued and no worker starts. On release, 0 requests are replayed and 2 continue; the held model load activates once and is not run again. The earlier activation and the held one each recorded exactly one activation.
   - Cancel and Master Stop still end held work.
6. **Shared memory reading.** `brain_runtime.host()` (`brain_runtime.py:30-32`) now reads memory through the worker guard's own function (`brain_worker.host_memory`, `brain_worker.py:14`), cgroup v2 included. The other R cases use simulated readings, so their outcomes do not change. R20 gained checks using the real `host()` against fixture cgroup files: admission and the guard both see 20.0 GiB available.
7. **Memory stop stays visible.** A memory-guard stop during a handover is now remembered (`local_brain.py:549`) and shown in `brain.status` (`:128`) until a model is next Ready (cleared at `:541` and `:571`). In R20 the stop now shows after the failed load and after the launch shortfall, and clears once the previous model is READY again.
8. **Simulated offload mark.** When the runtime is the campaign's fixture, the offload evidence now reads `SIMULATED_WORKER_LOAD_LOG: offloaded 41/41 layers to GPU (fixture runtime, not a GPU)` (`local_brain.py:447`). A real run still records `PINNED_WORKER_LOAD_LOG` exactly as before; the new unit test checks both. R17 checks the mark.

Other files changed:
- **Brain page message** (`brain_qt.py:216`): a memory refusal now shows its advice followed by the numbers.
- **New unit tests:** `tests_integrated/test_resource_rules.py` holds the tests for all eight items.
- **Campaign test:** `tests_integrated/test_campaign.py` now expects R19 and R22 to be plain passes. It also tests the "spec asks otherwise" outcome on a made-up case, since no real case uses it any more.
- **Docs:** `docs/CAMPAIGN.md` explains the new decisions.
- **Seed and manifest:** rebuilt with `package_graphite.py --manifest-only`; the seed state is `VERIFIED_SOURCE_BINDINGS`, 1,279 files.

## Tests
| Module | Before | After |
|---|---|---|
| `test_resource_rules` (new) | 12 of 13 fail on the old code | 13/13 OK |
| `test_campaign` | 23 OK | 23 OK |
| `test_kasandra` | 20 OK | 20 OK |
| `test_model_settings` | 13 run, 4 failures + 1 error | the same 5, with the same failure reasons; none added |

- **Unit-test discrimination:** the 13th test passes on the old code too, by design. It checks that cancel still ends held work and that running work still blocks resume.
- **`test_model_settings` known failures** (identical before and after):
  - `test_worker_uses_frozen_options_even_after_saved_defaults_change` (the error)
  - `test_explicit_request_and_restore_override_launch_defaults`
  - `test_failed_activation_retains_original_restore_and_reports_owned_restored_worker`
  - `test_new_requests_freeze_defaults_auto_and_keep_idempotency_after_defaults_change`
  - `test_owner_cancellation_stays_stopped_and_never_automatically_restores`
- **Fifteen related modules** that reach this code (241 tests) pass both on a copy of the old commit and in the worktree: agent_loop, cabinet_actions, change_sets, continuing_work, discovery, model_turn, network_watch, operations, problem, project_desk, readiness, return_thread, service_lifecycle, slate_reasoning, tool_selection.

## Not done, and behaviour you should know about
- **Untested window changes:** I did not run `tools/check_*_ui.py`, as instructed. I also skipped `test_frame`, `test_launcher` and `test_release_check`, because they reference those checks. So the small edits to `brain_qt.py` and `model_settings_qt.py` were only compiled, not tested on screen.
- **Manual caps are looser:** a manual cap now only needs to fit within what is available less the reserve. At 30 GiB a 26,100 MiB cap is now accepted; the old rule refused it.
- **Running work during a hold** is unchanged: it is still stopped and Cancelled. New submissions are still refused while work is held.
- **Manifest change from the old commit:** the rebuilt manifest drops 2,528 entries for other worktrees' files that the old commit's `MANIFEST.json` listed by mistake (`.claude/worktrees/wf_6f300cdb-acf-1`, `wf_f04da51c-49c-1`). Rebuilding the manifest in the main folder while worktrees exist would add them back; that packaging problem is not fixed here.
- **No version bump:** the version is still 0.8.0.