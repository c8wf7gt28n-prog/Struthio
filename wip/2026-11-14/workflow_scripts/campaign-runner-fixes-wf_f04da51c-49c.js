export const meta = {
  name: "campaign-runner-fixes",
  description: "Fix the defects a reviewer found in the 35B campaign runner (in its own worktree), then have a second reader verify each fix",
  phases: [
    { title: "Fix", detail: "one builder fixes the review's findings" },
    { title: "Verify", detail: "one reader re-runs the reviewer's attacks against the fixed runner" },
  ],
}

const S = "/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad"
const PY = S + "/work/venv/bin/python"
const MIRROR = S + "/work/campaign_mirror"
const MIRROR2 = S + "/work/campaign_mirror2"
const JOURNAL = "/root/.claude/projects/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/subagents/workflows/wf_6f300cdb-acf/journal.jsonl"

const FIX = `
You are fixing a test-campaign runner for Graphite (Python 3.13 / PySide6). You work in your OWN git worktree (your current
directory). The main repository at /home/user/Struthio is being edited by someone else: do not touch it.

START: the runner's files are NOT in your worktree yet. Copy everything under ${MIRROR}/ into your worktree at the same
relative paths (tools/campaign.py, tools/campaign_lib/**, tests_integrated/test_campaign.py, docs/CAMPAIGN.md), then commit
them as "Campaign runner, first deliverable, as reviewed" so your fixes are a diff on top. Against losing work (the
session's worker can be restarted, which deletes worktrees): after you finish each file, copy it to ${MIRROR2}/<same
relative path>.

READ: the builder's report and the reviewer's findings are the results labelled build:campaign and review:campaign in
${JOURNAL} (JSON lines; a line with "type":"started" maps agentId to label; a "type":"result" line holds the text). Read
both in full. The spec is ${S}/in/spec_docx/spec.txt; the code map ${S}/work/maps/resources.md. Owner data for the After
Hours 07 anchors: set GRAPHITE_CAMPAIGN_FIXTURES=${S}/work/campaign_fixtures when you run.

FIX, in this order (each with a test in tests_integrated/test_campaign.py or a selftest case, and keep the module under ~60 s):
1. The summary must count only this run: report.load reads only the cases and attempts this run's MANIFEST lists, and
   'run' into an existing --out moves earlier results aside (out/previous-N/) instead of mixing them. Reproduce the
   reviewer's run_stale test first and show it fixed.
2. Honest outcomes: a case whose current behaviour contradicts an unambiguous line of the spec is not a plain Pass. Add
   an outcome or flag that the summary counts separately, e.g. "Pass (current code; the spec asks otherwise)", for R19 and
   R22 (quote the spec line in the case). R17 must observe the offload label from Graphite's actual result, not a
   constant it wrote itself; show that the llvmpipe fallback now fails or flags. Keep R07, R09, R15 as spec questions.
   The summary's headline says plainly what Pass means.
3. A16's reopen-from-disk check covers everything the case claims was saved: 300 mA, 3.60 W (18/5), the finding flagged
   for recheck, the unit, and the source still 280 mA. Show the reviewer's 'WRONG/kg/current' perturbation now fails.
4. A case's revision covers the code it runs through: hash the case data, its function, and every source file of
   tools/campaign_lib plus its data files; tracked_changes counts untracked files too.
5. A case that raises is Fail with the error, whatever checks it met before (as core.py's docstring says).
6. Anchors: Blocked is decided at run time from checkable needs (the model registered and matching the owner's file,
   LibreOffice present via shutil.which, a desktop session via DISPLAY/WAYLAND_DISPLAY, owner data present, etc.); each
   anchor lists its needs; with every need met but the steps not yet written, the outcome says so ("Blocked: steps not
   written yet; its needs are here"). The five runnable anchors are labelled in the summary as the baseline slice of
   their situation, not the situation's whole intent.
7. No git lock in the repository: every git call uses --no-optional-locks (or GIT_OPTIONAL_LOCKS=0).
8. Smaller: keep the seed record across a resume (R21, A27); real mode reads available memory from the cgroup when there
   is one (as workbench/brain_worker.memory_sample does) and from /proc/meminfo otherwise; correct the report wording
   about the truncated variant's size; A16's approval check either exercises an approval through the Kernel or is
   renamed to say it reads the policy table.

HARD RULES: do not edit files outside tools/campaign.py, tools/campaign_lib/, tests_integrated/test_campaign.py and
docs/CAMPAIGN.md. Run everything only inside unshare --pid --fork --mount-proc --kill-child ${PY} -B ... with
QT_QPA_PLATFORM=offscreen if Qt is imported. Never run tools/check_*_ui.py. No network. When done run
  unshare --pid --fork --mount-proc --kill-child ${PY} -B tools/campaign.py run --set all --out ${S}/work/campaign_run_2
(with GRAPHITE_CAMPAIGN_FIXTURES set) and the test module; commit in your worktree (message ends with the two lines
"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" and
"Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8"); do NOT push; make sure ${MIRROR2} holds the
final version of every file.

REPORT: worktree path, branch, commit; for each of the 8 items what you changed and the evidence it works (command and
output); the new summary line; anything not done, plainly.
`

const VERIFY = (fixed) => `
A builder fixed a Graphite test-campaign runner after a review. Their report:
---
${fixed}
---
The original review is the result labelled review:campaign in ${JOURNAL} (JSON lines; "started" lines map agentId to
label). The reviewer's scripts and runs are in ${S}/work/review_campaign/. The fixed files are in the worktree named above
and copied in ${MIRROR2}. READ-ONLY for the worktree and /home/user/Struthio; scratch only under
${S}/work/verify_campaign/. Run only inside unshare --pid --fork --mount-proc --kill-child ${PY} -B ... (QT_QPA_PLATFORM=
offscreen if Qt is imported; GRAPHITE_CAMPAIGN_FIXTURES=${S}/work/campaign_fixtures). Never run tools/check_*_ui.py.

For each of the review's findings 1 to 8, repeat the reviewer's own attack (their scripts are there) against the fixed
runner and say FIXED, PARTLY or NOT FIXED with the command and output. Then look for anything the fixes broke: run the
whole set twice into the same --out, run the test module, and check isolation once more (empty HOME, strace for writes
outside the run folder and TMPDIR, and for any git index.lock). Report most severe first; say plainly what holds.
`

phase("Fix")
const fixed = await agent(FIX, { label: "fix:campaign", phase: "Fix", isolation: "worktree" })
if (!fixed) return { fixed: null, verify: null }
phase("Verify")
const verify = await agent(VERIFY(fixed), { label: "verify:campaign", phase: "Verify" })
return { fixed, verify }
