export const meta = {
  name: "campaign-and-take-apart",
  description: "Rebuild the 35B campaign runner (builder in a worktree, then a breaker), and in parallel map the owner's 'computer you can take apart' ideas onto the code (three readers, a synthesis, a skeptic)",
  phases: [
    { title: "Build", detail: "campaign runner in its own worktree" },
    { title: "Review", detail: "a second reader tries to break the runner" },
    { title: "Read", detail: "three readers check the document's claims against the code" },
    { title: "Design", detail: "the smallest build slice for the clearance experiment" },
    { title: "Check", detail: "a skeptic tests the slice against the code" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const PY = S + "/work/venv/bin/python"
const MIRROR = S + "/work/campaign_mirror"

const BUILD = `
You are building the first deliverable of a test campaign for Graphite, a Python 3.13 / PySide6 desktop workspace whose
assistant runs a local model through llama.cpp. You work in your OWN git worktree of the repository (your current
directory). The main repository at /home/user/Struthio is being edited by someone else at the same time: do not touch it.
A previous builder ran out of time after only reading; its notes are not available, start fresh but move quickly to
writing code. Budget your effort: read the spec and the two maps, skim the code at the seams they name, then build.

IMPORTANT, against losing work: the session's worker can be restarted, which deletes worktrees. After you finish each
file, copy it to ${MIRROR}/<the same relative path> (mkdir -p as needed). Keep the mirror current to the last version.

READ FIRST:
- The owner's spec, as text: ${S}/in/spec_docx/spec.txt (the "First build deliverable" paragraph and the RESOURCE
  CONTROL section are the target).
- Maps of the code (file:line at the commit before yours; verify in code): ${S}/work/maps/resources.md (memory, model and
  job paths, injection seams in section 4, 20 resource cases in section 5 with the decision the CURRENT code makes),
  ${S}/work/maps/fixtures.md (how a workspace is created and seeded, the After Hours 07 case, driving operations without
  a window, a proposed fixture and case format).
- The owner's 35 situations: ${S}/work/situations_35.json.
- The REAL model's header: ${S}/in/hf/head.gguf = first 32 MiB of Qwen3.6-35B-A3B-Q4_K_M.gguf (full file
  20,542,732,576 bytes, SHA-256 f4ffe03c9139e6a905a5d346f77d9fabdd179367c3280dfd005d1e75ca5ed8c8; metadata ends at byte
  10,989,318; architecture qwen35moe, now accepted by sdk/cli/arc1cli/gguf_inspect.py). A previous probe of the After
  Hours 07 case is at ${S}/camp/ah07_probe.py (it may help; verify it).

WHAT TO BUILD (new files only):
1. tools/campaign.py, one entry point:
     python3 tools/campaign.py list [--set resource|anchors|all]
     python3 tools/campaign.py run --case R07
     python3 tools/campaign.py run --set resource [--attempts 2] [--out <dir>]
     python3 tools/campaign.py summary <run dir>
     python3 tools/campaign.py run --mode real --case M01   # ThinkPad only; must refuse cleanly here (see 6)
   Implementation in tools/campaign_lib/ (fixture.py, cases_resource.py, cases_anchor.py, runner.py, report.py,
   gguf_fixture.py as you see fit). Standard library plus what Graphite already imports.
2. A FIXTURE WORKSPACE built fresh per attempt in a temporary folder, fully isolated: its own ARC1_WORKBENCH_CONFIG_HOME,
   HOME and XDG dirs, workspace root, kernel database. Nothing may touch the real user profile, the repository's .ledger,
   or /home/user/Struthio. Reset = delete and rebuild (or copy a template built once per run). Record fixture hashes.
3. A CASE FORMAT (JSON-serialisable): id, set, original situation id (S01..S35 or none), title, starting state, inputs,
   allowed operations, fault schedule, expected outcome (checks that read the result), time budget in seconds, mode
   (sim | real). A CASE MANIFEST per run: case ids, case revision hashes, build identity (git commit of the tree under
   test, workbench/version.py VERSION), Python and PySide6 versions, host summary, model file identity where relevant,
   the fault schedule.
4. RESOURCE SIMULATION CASES (set "resource", R01..): at least 18 of the 20 cases in resources.md section 5, through
   Graphite's REAL decision code (local_brain.configuration, resource_control decision/claim/_view, gguf_inspect.inspect /
   inspect_set, brain_runtime.parse_devices, start_server/run_model_job with fakes), readings injected ONLY at the seams
   in resources.md section 4 (unittest.mock patches inside the attempt's process). Each expectation is the decision the
   CURRENT code makes; where resources.md marks a mismatch with the spec, record "spec_question" in one sentence and
   still pass on current behaviour. Model preflight uses a GGUF FIXTURE built from the real header: write
   tools/campaign_lib/data/qwen35moe_header.json once (metadata scalars, chat template, tensor table: name, dims, type,
   offset; drop tokenizer arrays but keep their lengths) and a builder writing a valid GGUF from it with a short
   tokenizer, extended by a SPARSE truncate to the declared size (check with du that it takes little disk). Variants:
   valid; bad magic; truncated data; unsupported architecture; unsupported tensor type; no chat template; changed after
   registration. Do not hash 20 GB: patch local_brain.recheck/identity as resources.md says, or hash only what the code
   hashes and show it is bounded.
5. ANCHOR SET ("anchors"): one case per situation S01..S35 with its id and intent; each runnable now in sim mode with a
   declared check, or Blocked with the missing prerequisite in one specific sentence (most need the real model, a
   native application or owner data). Implement After Hours 07 fully headless through the kernel's operations (no
   window): settled current 280 mA -> 300 mA on the working copy, recalculate, and check FROM THE RECORDS: the cell says
   300, settled power 3.60 W at 12 V (was 3.36 W), the dependent finding is flagged for recheck, the source still says
   280 mA. Use the existing seed (see fixtures.md); if the real flow needs the model, script its choice and say so.
6. REAL MODE: --mode real checks for a registered model whose identity matches the owner's file (--model path or the
   registered model), prints exactly what it would run, refuses clearly with less than 24 GiB available or without the
   file. No downloads. It is for the ThinkPad.
7. RESULTS: per attempt JSON (case id, attempt, monotonic and wall times, outcome Pass | Partial | Blocked | Fail |
   Timeout, checks observed vs expected, reason, last durable result, injected faults, spec_question). TIMEOUT per case:
   each attempt in a child process killed at its budget, keeping its checkpoint file. A RESUME case that writes a
   checkpoint, is killed, resumes from its own checkpoint, and checks a write happened once. A markdown summary per run:
   counts by outcome, case table, slowest cases, spec questions.
8. TESTS: tests_integrated/test_campaign.py (unittest; a handful of resource cases and the anchor manifest through the
   runner; under ~60 s). Do not register it anywhere else.
9. docs/CAMPAIGN.md: a short owner runbook in plain words (list, run one, run a batch, read the summary; here versus the
   ThinkPad; the real-model runs and the remaining cases of the spec's 300 come next).

HARD RULES:
- Do not edit existing files (workbench/, sdk/, tools/check_*.py, tools/package_graphite.py, MANIFEST.json, other docs,
  workbench/version.py). A production change that seems necessary goes in your report under "production changes
  proposed".
- Never run tools/check_*_ui.py or tools/check_release.py --ui.
- Run tests and the runner only inside: unshare --pid --fork --mount-proc --kill-child ${PY} -B ... with
  QT_QPA_PLATFORM=offscreen if anything imports Qt.
- No network. Readable code; each module starts with a plain-words docstring.
- When done run: unshare --pid --fork --mount-proc --kill-child ${PY} -B tools/campaign.py run --set all --out
  ${S}/work/campaign_run_1 and the test module; paste their summary lines in your report.
- Commit in your worktree (git add only your new files; message ends with the two lines
  "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" and
  "Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8"). Do NOT push. Mirror the final files.

REPORT: worktree path, branch, commit hash; files; cases per set with outcomes; every spec_question; production changes
proposed; what you could not do, plainly.
`

const REVIEW = (built) => `
You are reviewing a test-campaign runner another engineer just built for Graphite (Python 3.13 / PySide6). Their report:
---
${built}
---
The work is in the worktree named there (a copy of the files is in ${MIRROR}). READ-ONLY for that worktree and for
/home/user/Struthio; scratch only under ${S}/work/review_campaign/. Run only inside
unshare --pid --fork --mount-proc --kill-child ${PY} -B ... (QT_QPA_PLATFORM=offscreen if Qt is imported). Never run
tools/check_*_ui.py. Spec: ${S}/in/spec_docx/spec.txt; code map: ${S}/work/maps/resources.md.
Try to break it:
1. Isolation: does any case read or write outside its fixture (real HOME, ~/.config, the repository's .ledger,
   /home/user/Struthio)? Run a batch with a fresh empty HOME, compare listings before and after, read the fixture code.
2. Honesty: does each resource case go through Graphite's decision code, or assert a hard-coded answer? For five cases,
   change an injected reading in a scratch copy and show the outcome follows the code.
3. Timeout and resume: an overrun is killed and saved as Timeout with partial results? The resume case resumes from its
   own checkpoint and the write is done once?
4. GGUF fixture: built from the real header, sparse on disk; do the bad variants fail at the check the case claims?
5. Anchors: S01..S35 exactly once; Blocked reasons specific; After Hours 07 checks the records (300 mA, 3.60 W, recheck
   flag, source still 280 mA), not its own variables.
6. Summary and manifest: build identity, case revisions, spec questions present? Run the test module.
Report findings most severe first, each with evidence (command and output). Say plainly what holds.
`

const READERS = [
  { key: "words", prompt: `staC words and the line behind Kas's answers. Files: workbench/stac_words.py and every caller; how the
assistant's Talk pane (workbench/shell2.py SlateFace and its cards) shows a staC line she read ("run, change or keep"), how
the typing bar's staC/Terminal/Stacy modes route a line (workbench/typebar_qt.py), history, "explain". Verify claims 3 and 5
of the brief exactly (does "word waits = field.read | pick waiting | select kind,title,state" work today? does "explain
waits" exist? does a word carry on in a pipe? is it per workspace? does it run with the model unloaded?). Then: what exists
and what is missing for "open the line behind her answer, add a filter, see the list change, name your version".` },
  { key: "methods", prompt: `Methods, checks and forks. Files: docs/STAGE5.md (around line 60), docs/BOSS_IMPLEMENTATION_PLAN.md
(around 176), docs/RELEASE_NOTES_0.3.md, and the code that holds calculations, findings, limits and recipes in the Field and
the kernel (workbench/field_model.py, field_service.py, datasheet_work.py, engineering_kernel.py, the dispatcher in
workbench/engine.py, any "procedure"/"recipe"/"limit"/"check" code). Verify claims 2, 6 and 8 of the brief. Then answer:
what is the closest existing thing to "a clearance method with a minimum (0.50 mm) applied to each row of a CSV", where
would a project-scoped copy (a fork that records its parent revision) live, how are units handled today (is there a unit
table; would "0.028 in" -> 0.7112 mm be explicit), and what records a result's inputs (source revision, method revision).` },
  { key: "surface", prompt: `Surfaces for Inspect, failure and menus. Files: workbench/shell2.py (Talk cards: StagedRun, PlanRun,
Undo, the Work trail), workbench/menus2.py and the Tools/Programs menus, right-click (context) menus on files and tables in
the Finder/centre (workbench/finder_qt.py and the sheet/table pages), workbench/stacy_hand.py and stacy_start.py (her acts
and how a program is started), and how subprocess failures are reported to the owner today. Verify claims 1, 7 and 8 of the
brief: is there a right-click on a result or a file that could carry "Inspect / Open method / Fork"? Is there a
per-project place for commands? How does a failed step report what worked and what stopped? What runs with the model off?` },
]

const READ_PROMPT = (r) => `You are one of three readers checking an owner's design discussion against the code of Graphite
(Python 3.13 / PySide6, repository /home/user/Struthio — READ ONLY: do not edit anything there; scratch files only under
${S}/work/take_apart/). The discussion, condensed, is ${S}/in/take_apart/brief.md: read it first.

Your part: ${r.prompt}

Cite file:line for every statement about the code. Mark each claim of the brief you checked as HOLDS, PARTLY (say what
part) or DOES NOT HOLD, with evidence. If you can run something cheaply to confirm (a staC line through the language's own
parser or engine, without a window), do it inside unshare --pid --fork --mount-proc --kill-child ${PY} -B ... with
QT_QPA_PLATFORM=offscreen and a temporary ARC1_WORKBENCH_CONFIG_HOME and HOME, and show the output. Never run
tools/check_*_ui.py. Finish with: what already exists that the experiment in point 9 can stand on, and what is missing,
as a list of concrete pieces with the files they would touch.`

const DESIGN = (notes) => `Three readers checked an owner's design discussion ("a computer you can take apart",
${S}/in/take_apart/brief.md — read it) against the Graphite code (/home/user/Struthio, READ ONLY). Their notes:

${notes}

Write the smallest build slice that makes the experiment in point 9 real and honest, standing on what exists: one clearance
method, one fixture (the rows 0.49, 0.50, 0.69, 0.70 mm, "0.028 in", a blank unit), one project menu entry; Inspect (the
three levels), Fork with a recorded parent revision, a side-by-side preview of both on the same input, pin, run with the
model off, and the assistant explaining the result from the forked version. For each piece: the file(s), the functions to
add or change, the records written, the tests that prove it (with the exact expected outputs from the fixture), and what is
deliberately left out. Keep the owner's rules: every change she makes asks or is on her allow-list (workbench/stacy_hand.py),
Undo where possible, nothing silently applied, no keyboard shortcut printed in the interface. Also list every claim of the
brief that the readers found does NOT hold, so the owner hears it plainly. Return markdown.`

const CHECK = (design) => `A design slice for Graphite (/home/user/Struthio, READ ONLY; scratch under ${S}/work/take_apart/) follows.
Try to break it against the code: name every step that would not work as written (a function that does not exist, a record
that is not kept where it says, a test expectation that is wrong — recompute the fixture's expected outputs yourself: rule
pass if value >= minimum; minimum 0.50 mm then 0.70 mm; rows 0.49, 0.50, 0.69, 0.70 mm, 0.028 in, blank unit), every place
it breaks one of the owner's rules (her allow-list in workbench/stacy_hand.py, Undo, nothing silently applied), and every
piece that is larger than it needs to be. Cite file:line. Then say what holds. Return markdown.

---
${design}`

const buildTrack = async () => {
  phase("Build")
  const built = await agent(BUILD, { label: "build:campaign", phase: "Build", isolation: "worktree" })
  if (!built) return { built: null, review: null }
  const review = await agent(REVIEW(built), { label: "review:campaign", phase: "Review" })
  return { built, review }
}

const takeApartTrack = async () => {
  const notes = await parallel(READERS.map(r => () => agent(READ_PROMPT(r), { label: "read:" + r.key, phase: "Read" })))
  const joined = READERS.map((r, i) => "## Reader: " + r.key + "\n\n" + (notes[i] || "(this reader did not return)")).join("\n\n")
  const design = await agent(DESIGN(joined), { label: "design:slice", phase: "Design" })
  if (!design) return { notes: joined, design: null, check: null }
  const check = await agent(CHECK(design), { label: "check:slice", phase: "Check" })
  return { notes: joined, design, check }
}

const [campaign, takeApart] = await parallel([buildTrack, takeApartTrack])
return { campaign, takeApart }
