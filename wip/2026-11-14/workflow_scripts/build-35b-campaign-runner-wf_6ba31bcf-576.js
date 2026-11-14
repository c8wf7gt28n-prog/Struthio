export const meta = {
  name: "build-35b-campaign-runner",
  description: "Build the first deliverable of the 35B test campaign (runner, fixture workspace, case manifest, resource-simulation and anchor cases, summary) in an isolated worktree, then have a second reader try to break it",
  phases: [
    { title: "Build", detail: "one builder in its own git worktree" },
    { title: "Review", detail: "one reader runs it and tries to break it" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const PY = S + "/work/venv/bin/python"

const BUILD = `
You are building the first deliverable of a test campaign for Graphite, a Python 3.13 / PySide6 desktop workspace whose
assistant (Stacy) runs a local model through llama.cpp. You work in your OWN git worktree of the repository (your current
directory). The main repository at /home/user/Struthio is being edited by someone else at the same time: do not touch it.

READ FIRST (all are files you can read):
- The owner's spec, as text: ${S}/in/spec_docx/spec.txt (read all of it; the "First build deliverable" paragraph and the
  RESOURCE CONTROL section are the target of this build).
- Maps of the code made today by other readers (they cite file:line at the commit before yours; trust them as a guide,
  verify in the code): ${S}/work/maps/resources.md (the memory, model and job paths, their seams for injection, and 20
  concrete resource cases with the decision the CURRENT code makes), ${S}/work/maps/fixtures.md (how a workspace is
  created and seeded, the After Hours 07 case, driving operations without a window, a proposed fixture and case format).
- The owner's 35 situations as structured data: ${S}/work/situations_35.json.
- The REAL model's header: ${S}/in/hf/head.gguf is the first 32 MiB of ggml-org/Qwen3.6-35B-A3B-GGUF
  Qwen3.6-35B-A3B-Q4_K_M.gguf (full file 20,542,732,576 bytes, SHA-256
  f4ffe03c9139e6a905a5d346f77d9fabdd179367c3280dfd005d1e75ca5ed8c8). Its metadata ends at byte 10,989,318. The
  architecture qwen35moe was added to sdk/cli/arc1cli/gguf_inspect.py ARCHITECTURES in the commit you start from.

WHAT TO BUILD (new files only, except where stated):
1. tools/campaign.py: one entry point. Examples it must support:
     python3 tools/campaign.py list [--set resource|anchors|all]
     python3 tools/campaign.py run --case R07            # one case
     python3 tools/campaign.py run --set resource        # a batch
     python3 tools/campaign.py run --set resource --attempts 2 --out <dir>
     python3 tools/campaign.py summary <run dir>
     python3 tools/campaign.py run --mode real --case M01  # ThinkPad only; must refuse cleanly here (see 6)
   Put the implementation in a package tools/campaign_lib/ (fixture.py, cases_resource.py, cases_anchor.py, runner.py,
   report.py, gguf_fixture.py as you see fit). Python standard library plus what Graphite already imports.
2. A FIXTURE WORKSPACE built fresh for every attempt in a temporary folder, fully isolated: its own
   ARC1_WORKBENCH_CONFIG_HOME, HOME and XDG dirs, workspace root, kernel database. Nothing may read or write the real
   user profile, the repository's own .ledger, or /home/user/Struthio. Reset = delete and rebuild (or copy a template
   built once per run). Record the fixture's hashes in the attempt.
3. A CASE FORMAT (JSON-serialisable): id, set, original situation id (S01..S35 or none), title, starting state, inputs,
   allowed operations, fault schedule (injected readings / failures), expected outcome (checks that read the result),
   time budget in seconds, and mode (sim | real). A CASE MANIFEST is written for every run: case ids, case revision
   hashes, build identity (git commit of the tree being tested, workbench/version.py VERSION), Python and PySide6
   versions, host summary, model file identity where relevant, and the fault schedule.
4. RESOURCE SIMULATION CASES (set "resource", ids R01..): at least 18 of the 20 cases in resources.md section 5,
   exercised through Graphite's REAL decision code (local_brain.configuration, resource_control decision/claim/_view,
   gguf_inspect.inspect / inspect_set, brain_runtime.parse_devices, start_server/run_model_job with fakes) with readings
   injected ONLY at the seams listed in resources.md section 4 (unittest.mock patches inside the attempt's process).
   Each case's expectation is the decision the CURRENT code makes; where resources.md marks ⚠ (the code differs from
   what the spec seems to expect), the case must record a field "spec_question" saying so in one sentence, and still pass
   on the current behaviour. For model preflight use a GGUF FIXTURE built from the real header: write
   tools/campaign_lib/data/qwen35moe_header.json once (metadata scalars, the chat template, the tensor table: name,
   dims, type, offset; drop the tokenizer arrays but keep their lengths), and a builder that writes a valid GGUF from
   that JSON with a short tokenizer, then extends it with a SPARSE truncate to the declared size so the real offsets fit
   (it must take little disk; check with du). Variants: the valid file; bad magic; truncated data; an unsupported
   architecture; an unsupported tensor type; no chat template; and "changed after registration" (modify a byte inside
   the header after brain.model.add). Do not hash 20 GB: patch local_brain.recheck/identity as resources.md says, or
   hash only what the code hashes and show it is bounded.
5. ANCHOR SET (set "anchors"): one case per original situation S01..S35, carrying its id and intent. Each is either
   runnable now in sim mode with a declared check, or recorded as Blocked with the missing prerequisite in one sentence
   (be honest: most need the real model, a native application or data the owner supplies). Implement at least the
   After Hours 07 case fully headless through the kernel's operations (no window): change the settled current 280 mA ->
   300 mA on the working copy, recalculate, and check from the records: the cell says 300, settled power 3.60 W at 12 V
   (was 3.36 W), the dependent finding is flagged for recheck, and the source still says 280 mA. Use the existing seed
   for that case (find it via fixtures.md); if the real flow needs the model, script the model's choice and say so in
   the case.
6. REAL MODE: --mode real must check for a registered model whose identity matches the owner's file (path given by
   --model or the Brain room's registered model), print exactly what it would run, and refuse with a clear message on a
   host with less than 24 GiB available or without the file. It must NOT download anything. It is for the ThinkPad.
7. RESULTS: per attempt a JSON result (case id, attempt, start/end monotonic and wall times, outcome Pass | Partial |
   Blocked | Fail | Timeout, the checks with observed vs expected, the reason, the last durable result, injected faults,
   any spec_question). A TIMEOUT per case (from its budget) that saves partial results: run each attempt in a child
   process and kill it at the budget, keeping whatever checkpoint file it wrote. A RESUME case (e.g. R99 or A-resume)
   that deliberately writes a checkpoint, is killed, and is resumed from its own checkpoint, and checks a write
   happened once. A readable summary (markdown) per run: counts by outcome, the table of cases, the slowest cases,
   and the list of spec questions.
8. TESTS: tests_integrated/test_campaign.py with unittest tests that run a handful of resource cases and the anchor
   manifest through the runner and check outcomes; keep it under ~60 s. Do NOT register it anywhere else.
9. A short owner runbook: docs/CAMPAIGN.md (how to list, run one, run a batch, read the summary; what runs here versus
   on the ThinkPad; that the real-model runs and the remaining ~265 cases of the spec's 300 come next). Plain words.

HARD RULES:
- Do not edit existing files under workbench/, sdk/, tools/check_*.py, tools/package_graphite.py, MANIFEST.json, docs
  other than the new docs/CAMPAIGN.md, or workbench/version.py. If a production change seems necessary, do not make it:
  list it in your report under "production changes proposed".
- Never run tools/check_*_ui.py or tools/check_release.py --ui in your worktree (they write captures into build/).
- Run tests and your runner only inside: unshare --pid --fork --mount-proc --kill-child ${PY} -B ...
  with QT_QPA_PLATFORM=offscreen if anything imports Qt. Use ${PY} as the interpreter.
- No network access is needed; do not download anything.
- Keep the code readable; the project's style is dense but every module starts with a docstring in plain words.
- When done, run: unshare --pid --fork --mount-proc --kill-child ${PY} -B tools/campaign.py run --set all --out
  ${S}/work/campaign_run_1 and the new test module, and paste their summary lines into your report.
- Commit your work in your worktree (git add only your new files; commit message ends with the two lines
  "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" and
  "Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8"). Do NOT push.

REPORT (your final message): the worktree path, the branch name and the commit hash; the list of files; how many cases
per set with outcomes from the run; every spec_question; the production changes you propose; and anything you could
not do, plainly.
`

const REVIEW = (built) => `
You are reviewing a test-campaign runner another engineer just built for Graphite (Python 3.13 / PySide6). Their report:

---
${built}
---

The work is in the git worktree named in that report. READ-ONLY: do not edit, create or delete files in that worktree or
in /home/user/Struthio (scratch files only under ${S}/work/review_campaign/). Run things only inside
unshare --pid --fork --mount-proc --kill-child ${PY} -B ... (QT_QPA_PLATFORM=offscreen if Qt is imported). Never run
tools/check_*_ui.py. The spec it implements: ${S}/in/spec_docx/spec.txt; the code map: ${S}/work/maps/resources.md.

Try to break it. In particular:
1. Isolation: does any case read or write outside its temporary fixture (the real HOME, ~/.config, the repository's
   .ledger, /home/user/Struthio)? Check by running a batch with a fresh empty HOME and comparing a listing of the real
   locations before and after, and by reading the fixture code.
2. Honesty: does each resource case really go through Graphite's decision code, or does it assert a hard-coded answer?
   Pick five cases and show, by changing an injected reading in a scratch copy of the case (not in the worktree), that
   the outcome follows the code.
3. Timeout and resume: does a case that overruns its budget get killed and saved as Timeout with partial results? Does
   the resume case really resume from its own checkpoint, and is the write done once?
4. The GGUF fixture: is it built from the real header, sparse on disk, and do the bad variants fail at the check the
   case claims?
5. The anchor set: does it cover S01..S35 exactly once, and are the Blocked reasons specific? Does the After Hours 07
   case check the records (300 mA, 3.60 W, recheck flag, source still 280 mA) rather than its own variables?
6. The summary and manifest: are build identity, case revisions and spec questions present? Run the test module.
Report findings as a list, most severe first, each with the evidence (command and output). Say plainly what holds.
`

phase("Build")
const built = await agent(BUILD, { label: "build:campaign", phase: "Build", isolation: "worktree" })
if (!built) return { built: null, review: null }
phase("Review")
const review = await agent(REVIEW(built), { label: "review:campaign", phase: "Review" })
return { built, review }
