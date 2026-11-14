export const meta = {
  name: "model-memory-rules-fix",
  description: "Fix the memory and model rules the 35B campaign found (Auto cap, one admission rule, reserve, ready means a valid reply, hold not cancel, cgroup reading) in a worktree; then a verifier tries to break the fixes with the campaign and the tests",
  phases: [
    { title: "Fix", detail: "one builder in its own worktree" },
    { title: "Verify", detail: "one reader re-runs the campaign and attacks the fixes" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const PY = S + "/work/venv/bin/python"
const MIRROR = S + "/work/memory_fix_mirror"

const FIX = `
You are fixing Graphite's memory and model rules (Python 3.13 / PySide6 desktop workspace; it runs a local model through
llama.cpp). You work in your OWN git worktree of the repository (your current directory). The main repository at
/home/user/Struthio is being edited by someone else: do not touch it. Against losing work: after each file you change,
copy it to ${MIRROR}/<same relative path> (mkdir -p); keep the mirror current.

The owner's model: Qwen3.6-35B-A3B Q4_K_M, 20,542,732,576 bytes, on a ThinkPad with 64 GB of RAM, Radeon 680M (Vulkan),
Debian 13. The owner's spec, as text: ${S}/in/spec_docx/spec.txt (read its RESOURCE CONTROL and Load sections). A code map:
${S}/work/maps/resources.md. The test campaign in this repository (tools/campaign.py, tools/campaign_lib/, docs/CAMPAIGN.md,
tests_integrated/test_campaign.py) exercises exactly these rules; run it with
  unshare --pid --fork --mount-proc --kill-child ${PY} -B tools/campaign.py run --set resource --out <a new folder under ${S}/work/memfix_runs/>
(and --set all with GRAPHITE_CAMPAIGN_FIXTURES=${S}/work/campaign_fixtures). Read docs/CAMPAIGN.md and the SUMMARY of a
run first: the summary lists the spec questions and the two "Pass (current code; the spec asks otherwise)" cases.

FIX, each with a test (in the existing test module for that code, or a new focused one) and the campaign case's
expectation updated so the case says the new behaviour (and is a plain Pass where the spec is now met):
1. Auto cap (workbench/local_brain.py configuration): at 39 GiB available Auto refuses the owner's model because the cap
   is 65 % of available (25,958 MiB) and the estimate is 26,013 MiB. Make Auto accept a model whose estimate plus the
   foreground reserve and a stated headroom fits in what is available, and say the numbers when it refuses. Keep a
   ceiling. Show R05-R08 and R10 with the new decisions (R07 becomes an accept at 39 GiB; say what the smallest
   accepted availability is now).
2. One memory rule decides admission and launch (resource_control.decision vs local_brain's launch check): a model
   admitted must not be refused at launch by a different rule for the same numbers (R15).
3. When installed RAM cannot be read, keep the full foreground reserve (not 128 MiB), and give a request whose reading is
   lost after submit a deadline after which it fails with a clear reason (R09).
4. Ready means a valid reply: a restored previous model whose probe reply is empty is not READY; a worker that reports a
   smaller context than the one selected is refused, or the selection is updated and the owner told (choose, say which,
   and why) (R19). R19 must become a plain Pass.
5. A work hold holds: queued background work stays queued during the hold and continues from the right step on release,
   with a completed write done once (R22 must become a plain Pass).
6. brain_runtime.host() reads available memory the way brain_worker.memory_sample does (cgroup v2), so admission and
   the worker agree (R-cases that read host()).
7. After a memory-guard stop during a handover, the stop stays visible in brain.status (R20).
8. offload evidence from a simulated run is marked as simulated (R17), without changing what a real run records.
Keep every change small and readable; each module starts with a plain-words docstring; comments say why.

HARD RULES: run tests and the campaign only inside unshare --pid --fork --mount-proc --kill-child ${PY} -B ... with
QT_QPA_PLATFORM=offscreen if anything imports Qt. Never run tools/check_*_ui.py. Run every test module you touch, plus
tests_integrated.test_campaign, test_model_settings (it has 5 known baseline failures: list them before and after and make
sure you add none), test_resource* if any, and test_kasandra. After a source change, rebuild the seed and manifest with
${PY} -B tools/package_graphite.py --manifest-only (the line language refuses lines until the seed is rebuilt). No network.
Do not edit tools/check_*.py. The window must never name the line language (call a line "a line"). Commit in your worktree
(message ends with the two lines "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" and
"Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8"); do NOT push; keep the mirror current.

REPORT: worktree path, branch, commit; for each item what changed (file:line) and the evidence (command and output: the
campaign summary line before and after, the cases that changed outcome); the test results before and after; anything not
done, plainly.
`

const VERIFY = (fixed) => `
A builder changed Graphite's memory and model rules. Their report:
---
${fixed}
---
The worktree named there is READ-ONLY for you, as is /home/user/Struthio; a copy of the changed files is in ${MIRROR}.
Scratch only under ${S}/work/verify_memfix/. Run only inside unshare --pid --fork --mount-proc --kill-child ${PY} -B ...
(QT_QPA_PLATFORM=offscreen if Qt is imported). Never run tools/check_*_ui.py. Spec: ${S}/in/spec_docx/spec.txt; map:
${S}/work/maps/resources.md.
Try to break the fixes, most of all on safety: can the new Auto rule admit a model that would push the machine into swap or
starve the window (work the numbers for 64 GB with 20, 30, 39, 45 and 60 GiB available)? Do admission and launch now agree
for every case in the campaign and for a sweep of availabilities you choose? Does a lost reading ever wait forever? Is
READY ever reached without a valid reply? Does a held job ever run during the hold, or twice after it? Run the whole
campaign (with GRAPHITE_CAMPAIGN_FIXTURES=${S}/work/campaign_fixtures) and the test modules the builder ran; compare with
the builder's numbers. Report findings most severe first with evidence; say plainly what holds.
`

phase("Fix")
const fixed = await agent(FIX, { label: "fix:memory", phase: "Fix", isolation: "worktree" })
if (!fixed) return { fixed: null, verify: null }
phase("Verify")
const verify = await agent(VERIFY(fixed), { label: "verify:memory", phase: "Verify" })
return { fixed, verify }
