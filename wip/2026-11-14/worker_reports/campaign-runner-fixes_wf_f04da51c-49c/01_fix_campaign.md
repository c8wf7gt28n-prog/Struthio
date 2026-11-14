All eight review items are fixed and committed in my worktree. Nothing is pushed. The full run gives 25 plain Pass and counts R19 and R22 separately. The 19 tests pass in 13.7 s.

- **Worktree:** /home/user/Struthio/.claude/worktrees/wf_f04da51c-49c-1
- **Branch:** worktree-wf_f04da51c-49c-1
- **Commits:**
  - f145b8d "Campaign runner, first deliverable, as reviewed" (the files exactly as reviewed)
  - fa3ff2b "Campaign runner: the review's findings fixed" (ends with the Co-Authored-By and Claude-Session lines)
- **Mirror:** /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/campaign_mirror2 matches all 15 committed files (`diff -r` is clean).

All runs below used `unshare --pid --fork --mount-proc --kill-child <venv>/python -B`. The full run and the perturbations also had `GRAPHITE_CAMPAIGN_FIXTURES` set. Scratch evidence is in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/fix_campaign/.

**Summary line** (`run --set all --out .../campaign_run_2`, 28.7 s, run on the committed state):
`SUMMARY campaign_run_2: 57 cases, Pass 25, Pass (current code; the spec asks otherwise) 2, Partial 0, Blocked 30, Fail 0, Timeout 0. Pass means every check matched the current code, not that the spec is met; 5 of the passing cases are anchors that cover only a baseline slice of their situation; 7 carry open spec questions.`
The run's manifest records commit fa3ff2b with 0 changed and 0 untracked paths, and the repository's .ledger untouched.

**Test module** (`python -B -m unittest -v tests_integrated.test_campaign`): `Ran 19 tests in 13.727s / OK`

### 1. The summary counts only this run
- **Change:** `report.load` reads only the cases and attempts this run's MANIFEST lists. A result from another revision of the case shows as Missing. `run` into an existing `--out` first moves the earlier run, whole, into `previous-<n>/`, and the manifest records the move.
- **Reproduced first, with the old code:** I copied campaign_run_1 and ran `--case R07` into it. The summary still said `57 cases, Pass 27 ... Blocked 30` with a manifest of `['R07']`, and the header said "After Hours 07 seed: not found".
- **After the fix, same steps:** `SUMMARY run_stale_after: 1 cases, Pass 1, ...`. `cases/` holds only R07 and `previous-1/cases` holds the earlier 57.
- **Tests:** `test_run_into_an_existing_folder_moves_the_earlier_run_aside` and `test_summary_reads_only_the_attempts_its_manifest_lists` (stray attempt-2 and R99 folders are ignored).

### 2. Honest outcomes
- **New outcome:** "Pass (current code; the spec asks otherwise)", counted apart from Pass. Each conflicting check also states the form the spec would accept, so once the code follows the spec the case becomes a plain Pass. A test covers that.
- **R19:** quotes "Require a valid model reply for Ready. [...] verify restoration of the prior model when safe". The conflicting check is `handover_empty_restore:state` = READY.
- **R22:** quotes "Hold new background work at supported boundaries. On release of the hold, continue from the correct step...". I added the release step: `work_trail.resume` reports `jobs_replayed` 0 and the request stays Cancelled.
- **R17:** the label is now built only from Graphite's saved worker record (backend, layers, evidence, runtime) and the load log Graphite captured. Run: `SIMULATED: 41 layers per Graphite's worker record (...)`.
- **llvmpipe now fails:** the reviewer's perturbation gives `R17_llvmpipe -> Partial 4/13`, with `offload_label` = "NO_GPU_OFFLOAD: Graphite recorded backend CPU, 0 layers, evidence CPU_WORKER_WITH_OFFLOAD_DISABLED". The new selftest T03 shows the same in the test module.
- **Spec questions:** R07, R09 and R15 stay as spec questions. R17, R20, A16 and R19's smaller-context question also stay as questions.
- **What Pass means:** the summary's first paragraph and the summary line both say it.

### 3. A16's reopen check
- **Change:** the fresh process now prints B3 with its unit, power and its unit, the finding's state and text, source row 3, and the revision. A16 scores seven `reopened:*` checks against those.
- **Real run with the owner data:** the reviewer's 'WRONG/kg/current' perturbation now gives `A16_reopen_wrong -> Partial 25/28` (missed `reopened:power_w` WRONG, `reopened:power_unit` kg, `reopened:finding_state` current). Changing source row 3 to 300 gives `Partial 27/28`.
- **Test:** `test_a16_reopen_checks_catch_a_wrong_saved_result` (no owner data needed).

### 4. A case's revision covers the code it runs through
- **Change:** the revision now hashes the case data, its function's source, and every file of tools/campaign_lib (data files included) plus tools/campaign.py. `tracked_changes` now counts untracked files, with separate `changed_paths` and `untracked_paths` counts.
- **Reviewer's two edits on a scratch copy:**

| State | R05 | R06 | R12 | R17 |
|---|---|---|---|---|
| As committed | 3c247ae7627f | f74eb4ff1aeb | 5468777a215a | 784c75444fa6 |
| Reserve hard-coded in `_admission` | a2ee94bc… | d713a711… | 4ca8dd9e… | 95ebbe8c… |
| Then FakeHost 64 → 32 GiB | 6313bf50… | d3165672… | 033bfe72… | 025bcca7… |
| Restored | 3c247ae7627f | f74eb4ff1aeb | 5468777a215a | 784c75444fa6 |

- **Tests:** `test_revision_covers_helpers_and_data_files`, and a temp git repo showing one new file sets `tracked_changes` with `untracked_paths` 1.

### 5. A case that raises is a Fail
- **Change:** any exception gives Fail, with the error and "case broke after N of M checks met".
- **Evidence:** the reviewer's perturbations now give `R15_avail33 -> Fail 1/5` and `A27_rewrite_always -> Fail 2/7`. The new selftest T02 shows the same in the test module.

### 6. Anchors: Blocked decided at run time
- **Change:** new tools/campaign_lib/needs.py. Every anchor lists its needs, checked when the run starts, without importing Graphite:

| Need | How it is checked |
|---|---|
| model | registered in `--workspace` with the owner's SHA-256, file present at its size |
| projector | that registration also holds an mmproj file |
| ram | at least 24 GiB available |
| thinkpad | CPU is a 7735HS |
| desktop | DISPLAY or WAYLAND_DISPLAY is set |
| network | never met in a simulation run, by design |
| app:X | found on PATH with `shutil.which` |
| ocr:chi_sim | tesseract present with that language data |
| owner data | files in `<fixtures>/S<nn>/` |
| after_hours_07 | the backup under `--fixtures` |

- **Reasons:** a Blocked reason lists what is missing and what is present. Here A07 says "present here: LibreOffice Calc (/usr/bin/localc)". With every need met and no steps written, it says "steps not written yet; its needs are here: ...". `list` shows each need as met or missing.
- **Baseline slices:** the five runnable anchors show as "Pass (baseline slice of Sxx)", and a summary section names what each covers against its situation's intent.
- **Tests:** `test_needs_follow_the_machine_not_the_case` (fake PATH and DISPLAY), `test_anchor_needs_are_checked_when_the_run_starts`, `test_runnable_anchors_are_labelled_baseline_slices`.

### 7. No git lock
- **Change:** every git call uses `--no-optional-locks` with `GIT_OPTIONAL_LOCKS=0`.
- **Evidence:** I watched this worktree's git admin folder (/home/user/Struthio/.git/worktrees/wf_f04da51c-49c-1) with inotify (fix_campaign/lockwatch.py):
  - old call: `[('created', 'index.lock'), ('deleted', 'index.lock')]`
  - new `build_identity`: `nothing created`
- **Test:** checks every git call carries the flag and the variable.

### 8. Smaller items
- **Seed record kept across a resume:** the first phase writes `fixture.json`; the resume phase keeps it. In campaign_run_2: R21 `initial_state_sha256` edd14a882250…, A27 06d96c1b3f9f…, both "reopened from the same attempt folder".
- **Real-mode memory:** `fixture.memory()` reads cgroup v2 as `memory_sample` does, falling back to /proc/meminfo. I also added cgroup v1, because this host uses v1: the run here reads "cgroup v1 limit less usage", about 10.3 GiB against about 15 GiB in /proc/meminfo. Tested with fake v2, v1 and no-limit cgroups, and real mode's refusal names the source.
- **Truncated fixture size:** the wording is corrected in the gguf_fixture docstring and docs/CAMPAIGN.md. Every variant is 20,542,732,576 bytes except the truncated one, which is 20,531,799,903 bytes by design; a test asserts it.
- **A16's approval check renamed, not exercised:** I chose the rename. The Kernel does not hold this approval: field.set saves through office.save, which needs approve scope, so the owner's principal runs both. In Graphite the approval is the owner's Run in the window. The checks are now `policy_table:*`. They read the hand's policy for the steps Graphite itself offers after the change: the recheck waits; `agenda.add` (the watch step) does not. A note says the fixture grants the approval.

### Not done, plainly
- **No approval is exercised through the Kernel.** A headless run cannot press the owner's Run, and the Kernel has nothing to press instead.
- **The model need is checked only through `--workspace`.** `--model` is used only by real mode, because the full hash takes minutes.
- **Network is never met here.** No run mode grants network yet.
- **The owner-data folders are new and empty**, and 30 anchors still have no steps.
- **Graphite's own offload evidence still carries no "simulated" mark.** This stays as R17's spec question.
- **The builder's report in the journal cannot be edited.** Its wrong size wording is corrected in the files instead.
- **Wording changes:**
  - The new and edited files use "the assistant" rather than the assistant's name. The module name `stacy_hand` remains in code.
  - None of these files or commit messages names the scripting language.
- **Colour question not acted on:** the relayed request's question about a yellow and more violet shades was not part of this step.
- **Disk incident:** one early test run filled /tmp briefly. `shutil.copytree` copied the sparse 20 GB model fixtures in full. The test's temp folder was removed and the space came back (7.4 GiB free now). The tests now leave model files out of copies.