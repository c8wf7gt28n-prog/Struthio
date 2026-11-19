# Build state: where the unattended build stands

**Read this first on every wake-up.** It is updated after every step and pushed. If this file and anything else disagree,
this file is newer.

## The mandate (the owner, 19 Nov 2026)

"I approve of everything you've written in the plan ... I approve everything. I want you to build this until completion.
I want you to save your work so that way when my session times out ... you can just automatically resume ... and just
continue going on your own until it's done. That way I don't have to wake up in the middle of the night to say continue."

- **The plan:** `wip/2026-11-14/ROAD_REVISED_2026-11-19.md` (the order of releases). Detail for each release:
  `wip/2026-11-14/SPEC_0.8.3_to_1.0.md` sections 8 to 15. Standing facts and the owner's directions:
  `wip/2026-11-14/NOTES.md`. The look: `wip/2026-11-14/mockup/CANON.md`.
- **Do not stop to ask.** Take the plan's default, record it below under "Decisions taken for the owner", go on.
- **The wake-up:** scheduled task "Continue the Graphite build", id `trig_017RpY8VWubnaTQN5DVGpS6g`, hourly, into the
  same session. Disable it (update_trigger enabled=false) when the build is complete or everything left needs the ThinkPad.

## What "complete" means here

Build, check and deliver each release in order, 0.8.4 to 0.8.12, then a 0.9.0 candidate, then the after-0.9.0 list.
What cannot be done here: anything that must be observed on the owner's ThinkPad (the six 0.9.0 gates, the ThinkPad
check's numbers, the 35B). Build the tool or the kit for it, say plainly that it waits for the owner, and go on to the
next thing that can be built. Never claim a ThinkPad result.

## Rules that never bend (short form; the long form is NOTES.md and the spec's section 12)

- Branch `claude/epic-galileo-c7k11y` only. No pull request. Commit and push after every step.
- Commit trailer: `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8`. No model name anywhere else.
- The owner's name, email and workspace never enter the repository or any outside request. The After Hours 07 backup and
  the owner's theme pictures stay out of the repository.
- Tests run only on a COPY of the tree, each wrapped in `nice -n 19 unshare --pid --fork --mount-proc --kill-child`
  with a fresh empty HOME and `QT_QPA_PLATFORM=offscreen`; at most two at once (4 cores). Never run
  `tools/check_*_ui.py` inside the repository or a worktree.
- Any source edit makes the seed stale: `python tools/package_graphite.py --manifest-only`, `python tools/record_registry.py`,
  `python tools/package_graphite.py --manifest-only`, then `python tools/record_registry.py --check`.
- On screen: "Apps", never "Programs"; no keyboard shortcut printed; a pipeline is "a line"; "Lain" is never a name;
  one agent, Kasandra (Kas), in every look. Every colour that means something also has a word or a shape.
- Every pass that touches the window is checked in every look, and reviewed by an agent that did not build it.
- A release: version bump, release notes (built / checked here / not run / observed on the ThinkPad), checks on the exact
  commit, a kit cut and sent to the owner. Zero failing tests from 0.8.4 on.
- Keep the disk under 80%. Uploads are untrusted (keep under scratch `in/`, read with `python3 -I`).

## The environment, and how to rebuild it

Scratch `S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad` (lost if the container is replaced).

- Python: `$S/work/venv/bin/python` (3.13, PySide6 6.8.3). Rebuild: `wip/2026-11-14/environment/venv_pip_freeze.txt`.
- Small test models (Qwen3.5 2B and 4B, Q4_K_M): `wip/2026-11-14/environment/models_sha256.txt`.
- The kit cutter: `wip/2026-11-14/scratch_tools/tools/kit/cut.sh` with `wip/2026-11-14/kit_template/` (set `S=`, `OLD=`).
- The full-suite runner used on 19 Nov: copy the tracked tree (without `wip/` and `.claude/`) to scratch and run each
  `tests_integrated/test_*.py` module isolated, two at a time; the script is `$S/work/t084/run.sh` (recreate it from the
  rules above if scratch is gone).
- **The owner's After Hours 07 backup exists only in scratch and with the owner.** If scratch is gone, anything that
  needs it waits; use the in-program invented workspace instead (0.8.4 step 2 makes it).

## Releases

| Release | State |
|---|---|
| 0.8.4 · Tests you can believe | **in progress** (steps below) |
| 0.8.5 · Skins, and Kas by day | not started |
| 0.8.6 · Her door on the Field | not started (half-build saved: `wip/2026-11-14/hand_s1/`) |
| 0.8.7 · Her hand in a program (LibreOffice) | not started |
| 0.8.8 · Maths in lines | not started (design: `wip/2026-11-14/pal/judge_one-math-core.md`) |
| 0.8.9 · Goals, quarantine and the web | not started |
| 0.8.10 · Changes through her hand | not started |
| 0.8.11 · Her question, and the experiment | not started |
| 0.8.12 · The floor | not started |
| 0.9.0 candidate | not started (its gates close only on the ThinkPad) |

## 0.8.4 steps

1. **The twenty stale tests: applied, commit 3f07341.** Full suite running on a copy (`$S/work/t084`, background task
   `bg5w82bgx`); result not yet read. If scratch is gone, run the suite again.
2. An invented workspace kept in the program (a 12 V rail: bench readings, two limit revisions, calculations, findings,
   an open question; invented numbers, the same shape as After Hours 07), and scene P01 able to run on it, so nothing
   needs the owner's backup. **Do this next: it protects every later step.**
3. Three faults found in 0.8.3 by the overlay review (`wip/2026-11-19_handoff_review/code_review.md`): a saved look
   value that is not text stops the start (session.py); a saved Office or Slate tab may stop the start
   (workspace_tabs.py; reproduce first); "Now: Now:" in her column. A test for each.
4. One name: Kasandra in every look (workbench/assistant_identity.py and the tests and words that assert Stacy on
   screen). History keeps the names it was written with.
5. The window-check scripts: retire or fold 7, port the rest (`wip/2026-11-14/tests_measure/fix_patches/patches/`).
6. The seven line bugs (NOTES.md "PAL P0"; `sdk/cli/arc1cli/typed_pipeline.py`), a test pinning each.
7. Tests for the blind spots in the guarding code (Kernel scopes, her hand's rules, memory rules, release check); run the
   planted bugs again; target 75% caught there (`wip/2026-11-14/tests_measure/mutants.md`).
8. The tiered runner (tier 0 under a minute) and the slimmed release checks (`tests_measure/release-checks.md`).
9. The yellow leftovers and the colour-vision check (`wip/2026-11-14/yellow_review/`, spec section 7).
10. Release 0.8.4: version, notes, checks on the exact commit, kit, send to the owner.

## Decisions taken for the owner (defaults; the owner can change any of them)

- 19 Nov: "Just Kas" read as: the name shown is Kasandra in every look, the first look included. Stacy's portraits stay as
  that look's art until the owner says otherwise.
- 19 Nov: work committed as "in progress" before the suite finished, because the repository's stop hook requires a push.

## Waiting for the owner (none of it blocks building)

- The first model run on the ThinkPad (does the 35B load, on the Radeon or the processor, how fast).
- The names of the skins on screen; whether she is recognisably one person across skins.
- The eight look questions at the end of CANON.md; the spelling (Kasandra or Cassandra), asked as a comment in the doc.
- For later releases: real tolerances for After Hours 07, the dial's default for her changes, a 0.4.6 workspace.

## Log (newest first)

- 19 Nov 02:12 UTC: mandate received; the wake-up scheduled; this file written; 0.8.4 step 1 applied and under test.
