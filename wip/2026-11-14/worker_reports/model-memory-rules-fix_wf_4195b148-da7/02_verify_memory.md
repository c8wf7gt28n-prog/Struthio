The builder's numbers all reproduce, and the eight fixes do what the report says. I found two safety gaps in the new launch rule. Neither one lets the machine run out of memory. I also found three minor issues.

## Findings, most severe first

### 1. A handover near the limit can lose the previous model (medium; confirmed in simulation, plausible on real hardware)
- **Where:** `resource_control.model_room` (`resource_control.py:288`) and `run_model_job`, which turns recovery off on any `GRAPHITE_HOST_MEMORY_LIMIT` (`local_brain.py:546-549`).
- **How it happens:**
  - Admission and the run-time configuration add back the memory the live model will free.
  - The launch check runs after `terminate()` and adds nothing back. It only passes if available memory has already risen by the full amount the old model freed.
  - `terminate` waits up to 3 s for the supervisor pid to die, not for its memory to be freed.
- **Why it is new:** the new rule leaves no gap between admission and launch for manual caps and frozen budgets. The old 80%-of-available check at run left about 4.4 GiB of slack, and it refused these requests at submit.
- **Evidence** (`probe/handover.py`): previous model holding 22,528 MiB, manual cap 26,100, 5,684 MiB available.
  - New code, memory fully returned: ACTIVATED.
  - New code, 97% returned: the old model is stopped, then the launch fails with `GRAPHITE_HOST_MEMORY_LIMIT`. Nothing is restored. The state is `MODEL_STOPPED` with the memory-stop message.
  - Old code: refused at submit, and the previous model stayed READY.
- **Sweep** (`probe/sweep.py`, part A, 509 MiB grid from 16 to 64 GiB, 108 combinations): 10 disagreements in the new code, all at 97% returned. None at 100%. None in the old code.
- **Suggested fix:**
  - Have the launch check wait until the old worker's memory is visibly back (or carry the add-back until then), or keep a margin.
  - A launch check that refuses before anything has started could leave restore allowed. The restore goes through `model_room` again, so it would still be refused if there is no room.

### 2. Auto's 4 GiB headroom is checked only at submit (medium)
- Once Auto has fixed a budget at submit, admission, run and launch only require budget + 2 GiB reserve.
- **Evidence** (`probe/sweep.py`, part B): how far availability can drop between submit and run while the model still launches.

| Auto submitted at | Budget | Launches down to | Left once the budget is resident |
|---|---|---|---|
| 32,157 MiB | 26,013 | 28,061 | 2,048 |
| 39 GiB | 26,013 | 28,064 | 2,051 |
| 45 GiB | 29,952 | 32,000 | 2,048 |
| 60 GiB | 32,768 | 34,816 | 2,048 |

- The old code launched only down to 37,440 / 40,960 MiB (7,488 / 8,192 left) at 45 / 60 GiB. Below that it failed the job at run, which was the R15 bug.
- **Not swap by itself:** the worker guard stops the model below the 2 GiB reserve, checking every 0.25 s. The estimate (1.3 × file size + KV + 384 MiB) also overstates the resident size by roughly 5 GiB for this file on CPU.
- **But:** the space guaranteed to the window has fallen from about 6.4 GiB or more to 2 GiB. The docs (`docs/CAMPAIGN.md`) describe the headroom without saying it applies at submit only.
- **Suggested fix:** keep the headroom with the frozen Auto budget at admission and launch.

### 3. A lost reading that comes and goes never reaches the 30 s deadline (low)
- Any measured reading resets the timer.
- **Evidence:** measured for 0.4 s every 20.4 s, each time with too little room. After 10 simulated minutes the request is still Queued with "Host memory could not be measured" (`probe/lost.py`).
- A reading of 0 is also handled two ways: admission waits on headroom indefinitely, while configuration calls it `HOST_MEMORY_COULD_NOT_BE_MEASURED`.
- On Linux, `host()` falls back to `sysconf`, so a missing reading is mainly a simulation or non-Linux case.

### 4. The memory-stop message sticks (low)
- It stays through a later unrelated failure (an empty reply) and through an owner Stop, until some model is next Ready.
- A reading lost exactly at launch also sets the message and turns off restore (`probe/banner.py`). The launch refusal itself is old behaviour; the persistent message is new.

### 5. The shared memory reading covers only the process's own cgroup and the root (low)
- A MemoryMax on a parent slice is invisible to both admission and the guard. With a 16 GiB limit on the parent and 4 GiB used, both still read 40,960 MiB (`probe/cgroup.py`).
- cgroup v1 is not read at all. This container uses v1, and old and new read identically here.

### Notes
- When `/props` gives no `n_ctx`, the model still reaches READY with `REQUESTED_LIMIT`, so its context is not checked. The reply is still checked. This is old behaviour.
- New submissions during a hold are refused rather than held. The spec says "Hold new background work". The builder disclosed this.

## What holds

**Builder's numbers, rerun from the `82bce35` and `5208841` trees:**
- **Whole campaign** (with the fixtures folder): 57 cases, Pass 27, spec-asks-otherwise 0, Blocked 30, Fail 0, 1 open spec question (A16).
- **Resource set:** 22 of 22 plain Pass. These match the builder exactly.
- **Tests:**
  - `test_resource_rules`: 13/13 on the new code. On the old code 12 of 13 fail (8 because new names are missing, 4 on assertions); the cancel/resume test passes by design.
  - `test_campaign` 23 OK; `test_kasandra` 20 OK.
  - `test_model_settings`: the same 5 failures before and after, with identical reasons.
  - The 15 related modules: the same counts and all OK on both trees.
- **Manifest:** 1,279 entries, all present with matching hashes, and no worktree entries.

**The questions you asked:**
- **Auto at 64 GiB installed:**

| Available | Auto result | Left once the budget is resident |
|---|---|---|
| 20 GiB | Refused, with the numbers | — |
| 30 GiB | Refused, with the numbers | — |
| 39 GiB | Budget 26,013 | 13,923 MiB |
| 45 GiB | Budget 29,952 | 16,128 MiB |
| 60 GiB | Budget 32,768 | 28,672 MiB |

  - The smallest accepted availability is 32,157 MiB (budget 26,013, 6,144 left once resident); 32,156 MiB is refused.
  - At submit, Auto alone cannot push the machine into swap or starve the window.
- **Admission and launch agree:**
  - Every MiB from 19.5 to 34 GiB, across 16 combinations (237,584 points): 0 disagreements when the old model's memory returns in full.
  - When availability drops between submit and run: 0 disagreements. The old code had 340 and 384 refusals at run in the 45 and 60 GiB sweeps.
  - In every campaign case, a model that was admitted launched, except R20's deliberate fault after admission.
- **Lost reading:**
  - A steady loss ends Failed at exactly 30.0 s.
  - During a hold there is no deadline; after resume it fails 30 s later.
  - The 2,048 MiB reserve is kept when installed RAM is unknown.
- **Ready:**
  - Only two code paths mark a worker live (`local_brain.py:540` and `:570`), and both now need non-empty text.
  - Refused as expected: a whitespace-only reply; a smaller context on CPU (no retry); a smaller context on Vulkan (one CPU retry, then Ready at full context only); a restore with a whitespace reply or a smaller context (`MODEL_STOPPED`).
  - The old code reached READY in 4 of these cases.
- **Hold:**
  - Two queued activations through 10 simulated minutes of hold stay Queued, and no worker starts.
  - Submissions are refused during the hold, and resume is refused while a job is Running.
  - On resume, 2 continue and 0 are replayed. Each runs once (2 workers in total), and claiming a finished job again does nothing.
  - Cancel during the hold ends the job.
  - A hold that arrives after admission is not checked by `run_model_job`. It relies on the existing kill loop in `Kernel.run_job` (polls every 0.05 s), which is unchanged.
- **Shared reading:** admission and the guard read identically for a limit on the process's own scope (20,480 MiB each) and on this machine.

Files are in `/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/verify_memfix/`:
- `probe/` (`run.sh`, `common.py`, `auto_table.py`, `sweep.py`, `handover.py`, `lost.py`, `ready.py`, `hold.py`, `banner.py`, `cgroup.py`; outputs `sweep_new_509.txt`, `sweep_old_509.txt`, `sweep_new_fine.txt`)
- `runs/all/`, `runs/resource/` (and their `.log` files)
- `tests/` (`summary.txt`, per-module logs)