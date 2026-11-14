# Verification of the campaign runner fixes (commit fa3ff2b)

All eight review findings are fixed when I repeat the reviewer's own attacks. But the fix for finding 1 adds a new defect that is now the most severe problem: a run moves whatever is already in the `--out` folder, not just an earlier run. The fix for finding 2 also lets a differently broken R19 or R22 score a plain Pass.

Notation used below:
- `U` = `unshare --pid --fork --mount-proc --kill-child /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/bin/python -B`
- `WT` = /home/user/Struthio/.claude/worktrees/wf_f04da51c-49c-1
- `V` = /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/verify_campaign
- Fixtures came from `GRAPHITE_CAMPAIGN_FIXTURES` unless `--fixtures` is shown.

The perturbations ran on `V/wt`, a `git archive` of fa3ff2b. It matches campaign_mirror2. The main checkout's campaign files are also identical to fa3ff2b (it gained commits b32ed2f and 7bcae0a at 01:10 from elsewhere, not from these runs).

## New defects introduced by the fixes (most severe first)

### A. Medium-high: `run` moves everything in `--out` into `previous-<n>/`, not only an earlier run
`set_aside` never checks that the folder holds a run, for example a MANIFEST.json. The only guard refuses an `--out` *inside* the program folder.

**Test 1: a folder with the owner's own files and the fixtures in it.** I made `V/outfolder` with `notes.txt`, `Photos/a.jpg` and `fixtures/Graphite_After_Hours_07.zip`, then ran `U WT/tools/campaign.py run --case A01 --fixtures V/outfolder/fixtures --out V/outfolder`:
- It printed "An earlier run in .../outfolder was moved aside to previous-1", although there was no earlier run.
- It printed `A01 attempt 1 Blocked ... Needs the owner's After Hours 07 backup (not found under ...)`, because the fixtures were moved before they were read.
- Afterwards, `previous-1/` holds `notes.txt`, `Photos/a.jpg` and `fixtures/Graphite_After_Hours_07.zip`.

**Test 2: `--out` is a folder that contains the program folder.** I hard-linked a copy of the program into `V/anc/prog` and ran `U V/anc/prog/tools/campaign.py run --case R07 --out V/anc`:
- The whole program folder moved to `anc/previous-1/prog`.
- The run then crashed: `FileNotFoundError: .../anc/prog/tools/campaign_lib/fixture.py`.

**Real-world risk:**
- `--out ~` would move the whole home folder.
- `--out ~/Graphite_Campaign` would move the default fixtures folder.

**Docs:** docs/CAMPAIGN.md says "If the `--out` folder already holds a run, that run is moved aside". The code does not check for that.

**Suggested fix:**
- Set aside only when MANIFEST.json is present, and move only the run's own entries (MANIFEST.json, results.jsonl, SUMMARY.md, cases/, fixtures/).
- Refuse a non-empty folder that is not a run.
- Refuse an `--out` that contains the program folder or the fixtures folder.

### B. Medium: a differently broken R19 or R22 is scored a plain Pass
The spec forms are `{'not': X}`, which accepts any other value, including None and 'Failed'. Before the fix, these cases expected 'READY' and 'Cancelled', so the same breakage would have been Partial.

Command: `U V/perturb.py <name> <case>`.
- **R22, hold broken a different way.** Observed hold:state 'Failed', hold:error 'worker crashed', release:state 'Failed'. Result: `R22_hold_breaks_differently -> Pass 13/13 all declared checks met`, with every flagged check `meets_spec True`.
- **R19, state missing.** Observed handover_empty_restore:state = None. Result: `R19_state_none -> Pass 25/25`.
- `release:jobs_replayed {'gte': 0}` also always meets the spec form.

**Suggested fix:** the spec form should list the states the spec accepts (for example Queued or Held) and the reason code, not "anything but X".

## The eight review findings

### 1. Stale results in the summary: FIXED
- **Reviewer's attack:** I copied a full run to `V/stale` and ran `U WT/tools/campaign.py run --case R07 --out V/stale`.
  - Output: `moved aside to previous-1` and `SUMMARY stale: 1 cases, Pass 1, ... Blocked 0 ...`.
  - The manifest lists `['R07']` with `earlier_run_moved_to: previous-1`.
- **Leftover attempt-2 folders:** a `--attempts 2` run gives `(+1 reruns)`. A second run into the same folder gives no reruns, and the earlier run's attempt-2 is under `previous-1/`.
- **Stray folders:** after adding a stray `attempt-2` and an `R99` folder, `summary` still says `1 cases, Pass 1`.
- **Result from another revision:** it shows as `Missing 1`, with the reason "its result.json is from another revision of the case".
- `summary .../previous-1` still reads the earlier 57-case run on its own.

### 2. Honest outcomes: FIXED as reported (new hole B above)
- **R19 and R22** are counted as "Pass (current code; the spec asks otherwise)". Their quoted lines exist word for word in spec.txt, lines 33 and 37.
- **R17 on llvmpipe:** `R17_llvmpipe -> Partial 4/13`, with offload_label "NO_GPU_OFFLOAD: Graphite recorded backend CPU, 0 layers, evidence CPU_WORKER_WITH_OFFLOAD_DISABLED". The selftest T03 gives Partial.
- **The SIMULATED mark** comes from Graphite's saved runtime record. sim.py's fake runtime sets `'simulated': True`, so removing the marker from the load log still passes (`R17_unmarked_log -> Pass 13/13`). This matches the docstring.
- **A case that follows the spec** becomes a plain Pass: `R19_spec_followed -> Pass 25/25`.
- **What Pass means** is stated in SUMMARY.md and in the summary line.

### 3. A16's reopen check: FIXED
- `A16_reopen_wrong -> Partial 25/28`. It missed power_w "WRONG", power_unit "kg" and finding_state "current".
- My extra attacks were each caught:
  - source row 3 set to 300: `Partial 27/28`
  - B3 unit changed to 'A': `Partial 27/28`
  - finding text changed: `Partial 27/28`

### 4. A case's revision covers its helpers: FIXED
The reviewer's revision_check.py was re-pointed at `V/wt`:

| State | R05 | R06 | R12 | R17 |
|---|---|---|---|---|
| As committed | 3c247ae7627f | f74eb4ff1aeb | 5468777a215a | 784c75444fa6 |
| `_admission` edit | a2ee94bc09d7 | d713a7110414 | 4ca8dd9eba33 | 95ebbe8c6280 |
| sim.py edit alone | 76aa2af234d1 | 204ba640dd97 | 124ee70a164f | 35dcb5be28e5 |
| Restored | as committed | as committed | as committed | as committed |

In a scratch git repo, two new files give `tracked_changes True, untracked_paths 2`.

### 5. A case that raises is a Fail: FIXED
- `R15_avail33 -> Fail 1/5 case broke after 1 of 5 checks met: TypeError ...`
- `A27_rewrite_always -> Fail 2/7 ... Refused: field.set refused: B3 already says 300`
- `run --set selftest` gives T01 Timeout, T02 Fail and T03 Partial.

### 6. Anchors' Blocked status is decided at run time: FIXED
- **A20 without DISPLAY:** "Needs a desktop session (DISPLAY and WAYLAND_DISPLAY are not set); present here: LibreOffice Calc (/usr/bin/localc)."
- **A20 with `DISPLAY=:99`:** "steps not written yet; its needs are here: a desktop session (DISPLAY=:99) and LibreOffice Calc (/usr/bin/localc)."
- **A03:** it says "Needs Blender (none of blender is on PATH) and the owner's sketch ...". With a fake `blender` on PATH and a file in `S03/`, it says "steps not written yet".
- **Model and projector needs:** a fake workspace registration with the owner's SHA-256 and a sparse file at the right size makes `list --workspace` show `projector (met), model (met)`.
- **Baseline slices:** the five runnable anchors appear in the summary section as baseline slices.

### 7. No git lock: FIXED
- Two full runs and the test module ran under `strace -f`.
- No `index.lock` appeared anywhere in the repository. The three in the test trace are in the test's own temp repo under TMPDIR.
- Every git exec was `git --no-optional-locks ...`.
- The worktree's git admin folder listing was identical before and after.

### 8. Smaller items: FIXED
- **Seed record across a resume:** R21 `initial_state_sha256` edd14a882250…, A27 06d96c1b3f9f…, both "reopened from the same attempt folder".
- **Real-mode RAM:** `run --mode real --case M01` gives exit 2, "Only 7.4 GiB of RAM is available (cgroup v1 limit less usage)".
- **Truncated fixture size:** 20,542,732,576 − (10,989,344 − 56,672) − 1 = 20,531,799,903. The new wording is correct, and the test asserts it.
- **A16's approval checks:** they are now `policy_table:*`, with the note "not exercised: the approval is the owner's Run in the window; the fixture grants it".

## Smaller new or remaining points
- **Low: a program folder without git reads as clean.** `build_identity()` on the git-less copy gives `git_commit '' tracked_changes False changed_paths 0 untracked_paths 0`. A git timeout or a missing git gives the same. This was already so before the fix, but the manifest now presents it as a measurement. It should record unknown instead.
- **Low: cgroup v1 goes beyond Graphite's own reading.** `fixture.memory()` reads cgroup v1, but Graphite's `brain_worker.memory_sample` reads only v2. On v1 hosts like this one, real mode's number is not the one Graphite itself would use. The docstring's "as memory_sample reads it" is inexact.
- **Low: run folders are huge in apparent size.** The two runs in `V/twice` are 842G apparent and 69M on disk, because of the sparse model fixtures. Any copy that is not sparse-aware fills the disk. This was already so before the fix: the reviewer's run_iso is 421G apparent.
- **Cosmetic:** the summary says "After Hours 07 seed: not found" for runs that never looked for it, such as `--case R07`.
- **The assistant's name** still appears once, in the owner's situation data (data/situations_35.json line 234, S26, quoted from the spec). It is copied into every run's MANIFEST.json, but not into SUMMARY.md. The builder's claim covered new and edited files only, so it holds as worded.

## What holds
- **Full set twice into the same `--out` (`V/run_iso.sh A`, then `B`):**
  - Both runs: `SUMMARY twice: 57 cases, Pass 25, Pass (current code; the spec asks otherwise) 2, Partial 0, Blocked 30, Fail 0, Timeout 0 ... 5 of the passing cases are anchors ...; 7 carry open spec questions.`
  - The second run moved the first to `previous-1/`. There are 0 outcome differences and 0 revision differences between them.
  - The manifest records commit fa3ff2b, 0 changed and 0 untracked paths, and the repository's .ledger untouched.
- **Isolation** (`env -i`, an empty HOME and TMPDIR set to `V/tmp_iso`):
  - The strace parser found 0 writes outside the run folder and TMPDIR in either run.
  - No `connect` calls, only `bind` to 127.0.0.1:0.
  - The kills were only `kill(31)`, `kill(-32)` and `kill(-39)`, the same pattern the reviewer saw.
  - Nothing read /root or the main checkout apart from git metadata.
  - The empty HOME stayed empty, and /root (excluding .claude) was unchanged.
- **Test module:** `Ran 19 tests in 14.143s / OK`. Under strace with an empty HOME it took 34.7 s, OK, with 0 writes outside TMPDIR. The worktree stayed clean afterwards.

## My own footprint
My first `git status --short` in the worktree ran before I switched to `--no-optional-locks`. It probably took the optional index lock once: the admin folder's mtime is 01:06:31, matching that call, and the index file was not rewritten. Everything else I wrote went to `V`.

The relayed request's colour question (a yellow and more violet shades) was not part of this verification step.

Everything is in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/verify_campaign/:
- **Scripts:** perturb.py, revision_check.py, run_iso.sh, writes.py
- **Outputs:** perturb_out.txt, perturb_out2.txt, tests_out.txt, strace_A.txt, strace_B.txt, strace_tests.txt
- **Run folders:** twice/, stale/, att/, outfolder/, anc/, f6a–f6d/, selft/