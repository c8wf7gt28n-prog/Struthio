# Review of the Graphite campaign runner (commit 20a2ad5)

The core claims hold. I re-ran `--set all` with a fresh empty HOME and got the same result as the report: `SUMMARY run_iso: 57 cases, Pass 27, Partial 0, Blocked 30, Fail 0, Timeout 0`. The test module passes: `Ran 7 tests in 8.243s / OK`. Isolation, the timeout kill, resume, the GGUF fixture and the resource decisions all behave as claimed. I found three Medium defects in the summary and the checks, and several smaller ones. They are listed most severe first.

## Findings

### 1. Medium: the summary mixes in stale results from earlier runs in the same `--out` folder
`report.load` reads every `cases/*/attempt-*/result.json` in the folder. `run` overwrites `MANIFEST.json` and `results.jsonl` but leaves the old attempt folders in place.
- **Test:** I copied my full run to `run_stale`, then ran `campaign.py run --case R07 --out .../run_stale`.
- **Output:** `SUMMARY run_stale: 57 cases, Pass 27, ... Blocked 30`. The manifest lists only `['R07']`, `results.jsonl` has 1 line, and the summary header says `After Hours 07 seed: not found` while still counting A01, A16, A17 and A27 as Pass.
- **Impact:** re-running a failure into its run folder is the spec's own use case, and the docs suggest a reused `--out ~/Graphite_Campaign/runs/today`. Leftover attempt-2 folders from an earlier `--attempts 2` run would be counted as reruns the same way.

### 2. Medium: "22 Pass" includes behaviour the spec explicitly forbids
These are filed as spec questions, but the spec text is not ambiguous:
- **R19** expects `small_context:state: READY` and `handover_empty_restore:state: READY`. The spec says "Require a valid model reply for Ready". Line 507 of `local_brain.py` ignores the restore probe's text.
- **R22** expects `hold:state: Cancelled`. The spec says "Hold new background work … On release of the hold, continue from the correct step".
- **R17** `offload_label` is a constant the case observes about itself (`ctx.observe('offload_label', SIMULATED_LABEL)`). When I switched R17 to llvmpipe, the run fell back to CPU with `offload_evidence: "CPU_WORKER_WITH_OFFLOAD_DISABLED"`, and the check still passed.

R07, R09 and R15 are genuine questions. The headline Pass count means "matches current behaviour", not "meets spec", and the report never says so.

### 3. Medium: A16's reopen-from-disk check looks only at B3
The expectation is `'reopened': {'contains': "'B3': '300'"}`. I changed `reopen_main` to print `'power': 'WRONG', 'unit': 'kg', 'finding_state': 'current'`.
- **Result:** `A16_reopen_wrong -> Pass 19/19`. The observed value was `{"B3":"300", ..., "power":"WRONG","unit":"kg","finding_state":"current"}` and the check was still ok.
- **Impact:** the separate process does not confirm that 3.60 W or the recheck flag were saved.

### 4. Medium-low: a case's revision ignores the helper code it runs through
`Case.revision()` hashes the case data plus the source of `fn` only. I tested this with `revision_check.py` on a scratch copy:
- I replaced the reserve observation in `_admission` with a hard-coded `2048`, then changed `FakeHost` `total_gib` from 64 to 32.
- `R05=ff0025a239bb R06=8778289411ad R12=1e1a59b23a05 R17=9f4be2ae4104` stayed the same through both edits.

The docstring in `core.py` ("a changed case is never mistaken for the one that ran before") is therefore false. Also, `tracked_changes` uses `--untracked-files=no`, so a new, uncommitted file is not flagged.

### 5. Medium-low: a case that crashes is scored Partial
`core.py` says "Fail (none met, or the case broke)", but `runner.child_main` gives Partial when any check was met:
- `R15_avail33 -> Partial 1/5  case broke: TypeError: 'NoneType' object is not subscriptable`
- `A27_rewrite_always -> Partial 2/7  case broke: Refused: field.set refused: B3 already says 300`

### 6. Low-medium: what the anchors claim
- **Blocked is written into each case, never checked.** `_anchor` sets `blocked=BLOCKED[sid]` unconditionally, and the runner returns Blocked in 0.0 s with no child process. LibreOffice is installed here (`/usr/bin/soffice`, `/usr/bin/libreoffice`), yet A07 still says "Needs … LibreOffice Calc". A07, A31, A32 and A35 list it among their needs, and A20 asks for it running in a desktop session. On the ThinkPad, with the model and apps present, these anchors would still say Blocked.
- **The five runnable anchors test a small slice of each situation.** Each one tests that situation's 0.4.1 baseline capability, not the finished result in its intent. For example, A01 is a trace and an exact power check, while S01's intent is "a readiness report … and a specific physical test". The summary shows them as Pass for the situation without saying this.

### 7. Low: each run takes a git lock inside /home/user/Struthio
The parent's `git status` in `fixture.build_identity` locks the git index, and strace caught it:
- `openat(".../Struthio/.git/worktrees/wf_6f300cdb-acf-1/index.lock", O_RDWR|O_CREAT|O_EXCL) = 3`
- `unlink(...index.lock) = 0`

This is the only write outside the run folder and TMPDIR. The fix is `git --no-optional-locks` or `GIT_OPTIONAL_LOCKS=0`. My own before-and-after `git status` listings of /home/user/Struthio took the same kind of lock: `.git` mtime moved and no content changed.

### 8. Low: smaller gaps
- **Resume cases lose their seed record.** For R21 and A27 the resume phase replaces the per-attempt `fixture` record, so the seed's `initial_state_sha256` and backup hash are missing (`A27 1 Pass None`).
- **A16's approval check reads a policy table.** `approval_asked_for` passes scopes the case supplies to `stacy_hand.hers`. No approval is ever exercised.
- **Real mode's RAM check reads `/proc/meminfo`, not the cgroup** — the same issue the report raises for `brain_runtime.host()`.
- **Report wording:** "each variant is 20,542,732,576 bytes apparent" is not quite right. The truncated variant is 20,531,799,903 bytes by design.

## What holds

- **Isolation:**
  - **Method:** a full run under `env -i HOME=<empty>` and `strace -f`.
  - **Result:** the empty HOME is unchanged (only the `..` entry differs), `/root` is unchanged apart from the excluded `.claude` folder, and the worktree is clean.
  - **No other writes:** nothing outside the run folder and TMPDIR except the git lock above. Nothing reads `/root` or the main checkout, apart from git reading `.git`.
  - **No network:** no `connect` calls, only `bind` to 127.0.0.1:0.
  - **Kills:** only the attempts' own process groups (`kill(-34)`, `kill(-41)`) and the supervisor's own child.
  - **Per attempt:** each attempt's `isolation` record puts config_dir, concern_home, home and workspace inside the attempt folder.
  - **Mirror:** identical to the committed files. All 14 changed files are new (`A`).
- **Honesty:** ten perturbations to injected readings in a scratch copy all moved the outcome as Graphite's code dictates:
  - R05 at 45 GiB: cap 29952, headroom 43.0
  - R07 at 40 GiB: Auto accepted
  - R12 at 33 GiB: not admitted, 31.0
  - R13 at 34 GiB: admitted
  - R11 with model RSS 6 GiB: future 10.0, headroom 28.0
  - R09 with total 64 GiB: reserve 2048; with the reading kept: Running
  - R15 at 33 GiB: not admitted
  - R20 at 60 GiB: `MODEL_LOAD_TIMEOUT` from `_start_server`
  - R17 on llvmpipe: CPU, `-ngl 0`
  - A16 with 310 mA: 93/25 W, "now 3.72 W"
- **Timeout:**
  - **Outcome:** T01 ends as `Timeout`, `returncode -15`, after 3.012 s.
  - **Kept:** checkpoint `started`, check `started` met, last durable step the `started` observation.
  - **Cleanup:** no processes left in the namespace.
- **Resume:** R21 and A27 are killed with SIGKILL at their checkpoint and resume in the same folder, and the write count is 1. When I forced a rewrite, R21 reported `step1_writes 2` and A27 was refused by Graphite. Two attempts get fresh folders with identical seed hashes.
- **GGUF fixture:**
  - **Header data:** 47 keys, 7,816-character template, 733 tensors of types F32, Q8_0 and Q4_K.
  - **Real tensor table:** the header's data offset plus the last tensor's end equals 20,542,732,576 exactly, which is strong evidence the table came from the real file.
  - **Size on disk:** the valid fixture uses 57,344 bytes.
  - **Rejections:** bad magic is rejected at `gguf_inspect.py:56`, truncated at `:96` (`GGUF_TENSOR_DATA_TRUNCATED`). Architecture, tensor type and template problems are rejected in `local_brain:configuration`.
- **Anchors:**
  - **Coverage:** S01..S35 appear exactly once.
  - **Blocked reasons:** each is one specific sentence.
  - **A16's sources:** it reads 300 mA, 18/5 W, recheck and the source row's 280 mA from saved records, not its own variables. The exception is `exact_check`, which uses a hard-coded 12 V.
- **Manifest and summary:**
  - **Recorded:** the commit, version, Python and PySide6 versions, host, backup hashes and header hash.
  - **Revisions:** the 57 case revisions are identical between campaign_run_1 and my run.
  - **Spec questions:** all 8 are present.
  - **Real mode:** refuses with exit 2. A sparse stand-in file passes the size and architecture checks and is refused only for RAM.

Everything is in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/review_campaign/:
- run_iso
- run_stale
- run_t01
- run_att2
- perturb/
- strace_iso.txt
- strace_net.txt
- perturb.py
- revision_check.py
- gguf_check.py
- timeout_check.py