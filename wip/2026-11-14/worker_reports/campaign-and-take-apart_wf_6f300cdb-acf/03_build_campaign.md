**Report: campaign runner, first deliverable**

The runner, the fixture workspace, 22 resource cases, 35 anchors, real mode, the tests and the runbook are built and committed. In the full run every case that can run here passed and the rest are Blocked. Nothing is pushed.

- **Worktree:** /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1
- **Branch:** campaign-runner-first-deliverable
- **Commit:** 20a2ad57e1b8a0115872e13a941ff5b20f627655, on top of 3d284ac. No existing file was changed.
- **Mirror:** /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/campaign_mirror/ matches the committed files.

**Summary lines**
- Full run (`run --set all --out /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/campaign_run_1`): `SUMMARY campaign_run_1: 57 cases, Pass 27, Partial 0, Blocked 30, Fail 0, Timeout 0`
- Tests (`python -B -m unittest -v tests_integrated.test_campaign`, under unshare): `Ran 7 tests in 8.203s` / `OK`
- The run's manifest records git commit 20a2ad5 with no uncommitted changes, VERSION 0.7.0, Python 3.13.18, PySide6 6.8.3, and the repository's .ledger untouched.
- I ran the full command with one addition: `GRAPHITE_CAMPAIGN_FIXTURES=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/campaign_fixtures`. That folder holds a copy of the uploaded `Graphite_After_Hours_07.zip`. Without it, A01, A16, A17 and A27 report Blocked, because the backup is owner data and is not shipped.

**Files (all new)**
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/tools/campaign.py
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/tools/campaign_lib/: `__init__.py`, `core.py`, `fixture.py`, `sim.py`, `gguf_fixture.py`, `cases_resource.py`, `cases_anchor.py`, `runner.py`, `report.py`
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/tools/campaign_lib/data/qwen35moe_header.json: 47 metadata keys, 7,816-character chat template, 733 tensors of types F32, Q8_0 and Q4_K; the three tokenizer arrays are dropped and their lengths kept.
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/tools/campaign_lib/data/situations_35.json
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/tests_integrated/test_campaign.py
- /home/user/Struthio/.claude/worktrees/wf_6f300cdb-acf-1/docs/CAMPAIGN.md

**Cases per set**
- **resource, R01–R22: 22 Pass.** R01–R20 follow resources.md section 5, cases 1–20. R21 is the resume case: it is killed after a durable settings write, resumes from its own checkpoint, and the write count is 1. R22 covers Stop and the work hold.
  - Each GGUF fixture variant is 20,542,732,576 bytes apparent and about 56 KiB on disk.
- **anchors, A01–A35: 5 Pass, 30 Blocked.**
  - A01 (S01): exact 84/25 W check and trace to the PDF.
  - A16 (S16): After Hours 07 run headless, 19 checks. The cell says 300 mA. Power is 18/5 W at 12 V (was 84/25 W). Finding claim f2a610f2 reads "recheck: says 3.36 W; now 3.6 W". The source row still says 280 mA, the PDF original hash is unchanged, and a separate process reopens the saved result. The model's choice of operations is scripted, and each result says so.
  - A17 (S17): backup verify and restore.
  - A27 (S27): crash recovery on After Hours 07, with the completed change recognised and not repeated.
  - A28 (S28): foreground turn and reserve.
  - The other 30 each name their missing prerequisite in one sentence.
- **selftest, T01:** the deliberate overrun ends as Timeout, killed at 3 s with its checkpoint and partial checks kept. It runs in the tests, not in `all`.
- **real mode, M01/M02:** on this machine it exits 2 with "REFUSED": the model file is absent and only 14.9 GiB of RAM is available.

The real-file numbers differ slightly from resources.md, which assumed 20.5e9 bytes:
- The estimate is 27,275,977,692 B (26,013 MiB), so the manual caps use 26,100 MiB.
- Case 1's warning in resources.md (qwen35moe not accepted) no longer applies at 3d284ac, which added qwen35moe; R01 now registers and is accepted.

**Spec questions (each case still passes on current behaviour)**
- **R07:** At 39 GiB available, the Auto cap (65% of available, 25,958 MiB) is 55 MiB below the 26,013 MiB estimate. Auto therefore refuses a model that fits with 13 GiB to spare.
- **R09:** When installed RAM can't be read, the foreground reserve drops from 2 GiB to 128 MiB. A request whose reading is lost after submit waits with no deadline.
- **R15:** Admission lets a 32 GiB model in at 34 GiB available, but the launch check (cap under 80% of available) then fails it.
- **R17:** The stored offload count carries no mark that it came from a simulated log.
- **R19:** A worker reporting a 2,048-token context reaches Ready while the selection says 4,096. A restored previous model is marked running even when its probe reply is empty.
- **R20:** After a memory-guard stop during a handover, both worker slots are cleared, so `brain.status` shows `resource_stop` as None.
- **R22:** A work hold cancels queued work at claim instead of holding it.
- **A16:** Any saved sheet change also sends the Startup power calculation to recheck, although neither of its inputs moved.

**Production changes proposed (none made)**
- Add a simulated or source label to `offload_evidence`.
- Make `brain_runtime.host()` read the process's own cgroup, as `brain_worker.memory_sample` does.
- Use one memory rule for admission and launch (`resource_control.decision` vs `local_brain.configuration`), and review the Auto cap factor.
- Keep the full reserve when installed RAM is unknown, and give `claim` a wait deadline.
- Require a non-empty reply for the restore probe (local_brain.py around line 508), and refuse a worker-reported context smaller than the requested one, or record it in the selection.
- Keep `resource_stop` visible after a pressure stop during a handover.
- Hold queued jobs during a work hold instead of cancelling them.
- Limit recheck to calculations whose input cells changed, if the answer to the A16 question is yes.
- The release check will flag `EDITED_SOURCES_NOT_YET_PACKAGED` until packaging rewrites MANIFEST.json, because new files are under tools/.

**What I could not do**
- **Real 35B runs:** the model file isn't here and the host has too little RAM. Real mode only checks prerequisites, prints its plan and refuses; actually running the model is the next deliverable.
- **Window-only parts of the spec run:** "return to the same Field tile", visually following the source link, screenshots and the model choosing actions all need the window. Headless, the source link is checked through `field.trace` and the source records, and the request is parsed by a scripted pattern.
- **Not covered:**
  - the "four failures and one error" baseline from 0.4.4;
  - real cgroup memory pressure (the pressure cases use simulated readings and a patched supervisor sample);
  - the `MODEL_FILE_CHANGED_BEFORE_LOAD` and `MODEL_FILE_CHANGED_SINCE_LOAD` variants.
- **Bounded hashing:** simulation never hashes the whole file; it reads at most 17 MiB (size, first 16 MiB, last 1 MiB). R03's changed-file case therefore changes a byte inside that window.