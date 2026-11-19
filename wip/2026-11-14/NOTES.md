# Where we stopped, 14 November 2026 (Graphite 0.8.3, commit 951c789)

Saved here because the build container is temporary. Nothing in `wip/` is part of the program; packaging leaves it out.

## Shipped
- **0.8.2** (d1df337): 40 desk acts typed in the writing line, the playable scene P01, after-hours look, typewriter face.
- **0.8.3** (951c789): Kasandra's hologram lower left with moving static and her state; her column for her words; every
  word in her typewriter face (fixed-width cut for code, numbers, Terminal); DELETE (a document's Delete is Erase);
  burnt-yellow highlight (bar in menus, edge elsewhere, never green; pointer halo pale violet in Kasandra); the neon kp
  logo on Apps as the only kp mark. Suite: 64 modules, 1,007 tests, the same 20 known failures; P01 4/4 in Kasandra;
  restore identical; release check PASSED. Not run for 0.8.3: probes, crawler, name sweep, gate.

## Order changed (14 Nov, after the test measurements): tests first
The measurement found all 20 failing tests stale, with fixes already written (`tests_measure/fix_patches/`), a behaviour
catch rate of 53% on 136 planted bugs (61 real gaps), and release checks of 73 minutes that caught one real fault since
0.5.0 (15 minutes after dropping duplicates and dead checks). So 0.8.4 is the test clean-up; her door is 0.8.5. The
release-by-release plan is in `TALK_my_plans_long_chat.md`.

## Paused (original order below; see the change above)
1. **Kasandra's hand, slice S1 "Her door on the Field"** (stopped mid-build).
   - Plan: `designs/judge_hand-plan.md` PART 1 §10 S1 (items 1-13, tests, scenes P02/P03, the 4B check).
   - Unfinished build, applied on bbf033b: `hand_s1/hand_s1_unfinished.patch` (28 files, `hand_s1/files.txt`; its build record, tests and scene results are in `hand_s1/build_record/`: all touched modules passed in the default look, P01-P03 9/9 in both looks, the 4B and 2B passed the goal turn; test_her_hand in Kasandra was mid-run when stopped; nothing reviewed).
     Apply on a branch from 951c789 with `git apply --3way`; expect small conflicts with 0.8.3's version and notes.
     It was NOT reviewed or tested to the end. Rebuild seed/manifest after applying.
   - The owner accepted the plan's six defaults (Go ahead covers moves up to the next goal or change, touch voids it;
     her changes keep the owner's identity, the journal says hers; DELETE waits until it has an exact Undo; an
     ambiguous limit shows both answers; tolerances are the owner's; touching stops her, scrolling does not).
   - Connect `HerHand.state_changed` to the hologram's states (thinking/acting → at work, waits → waits for you,
     stopped → stopped, finished → done).
2. **Test clean-up** ("solve or retire ALL failing tests ... eliminate useless tests ... evaluate the effectiveness").
   - Measurements done (`tests_measure/`): census, the 20 failing and the window-check scripts, coverage, about 160
     sampled mutants with a kill matrix, the release checks' worth. Only the judge step was left: re-run it from
     these reports (the judge prompt is in the workflow script `test-mammoth-measure-and-decide`).
   - Then a build pass: zero failing tests; retire tests only with evidence (no unique mutant kills AND brittle, duplicate,
     flaky or slow); never retire safety, privacy, data, her hand's permissions, what always asks, memory rules or release
     integrity; tiered runner (tier 0 under 60 s; tier 1 by changed files; tier 2 at a release; tier 3 the ThinkPad).
   - Fold in PAL P0: the line-evaluator bugs verified on 14 Nov (all real): `add x = 2*-3` gives -3; `where v=1`
     skips text "1" but `over 0` keeps it; `group` merges true with 1; `sum` skips numeric text that passed a comparison
     (8 becomes 3); `select title, state` refused; a quoted `;` refused while a quoted `|` passes; join trims and
     case-folds keys and overwrites an existing `other_*` field. File: sdk/cli/arc1cli/typed_pipeline.py.
3. **Small 0.8.3 leftovers** (`yellow_review/review_look.md`, `review_code.md`): the yellow glow around the writing line
   and the Field's selected sheet reads grey (it is added as light over blue); lists with their own colours (process
   list, Log, Explore, cabinet, Documents) keep the old fill; the PDF evidence highlight is see-through; the sheet's Run
   button focus is cyan; `boss_theme.LEGACY` maps some old colours to yellow.
4. **One math core** (`pal/judge_one-math-core.md`): PAL draft 0.2's evaluate / solve for / range / check stages and
   the goals engine as one implementation (`math_ranges.py`, `math_answers.py`, `tolerances.py`, Kernel op
   `math.answer`, record `ledger.math-answer/1`). It becomes the new S2; goals over data become S3. Corrections to the
   draft are in PART 1 (the 6 W row is "Continuous limit" in both revisions; Clock Lab needs all three allocations live;
   "under 6 W" in whole mA is 499; the step is "range", not "bound").
5. **Toward 0.9.0** (the talk of 14 Nov): six gates — the ThinkPad itself (a one-command check that reports the GPU's
   memory window, memory speed, the 35B's measured prompt and generation speed, Qt scale, fonts); her hand with the
   planner (S1-S4) and the I05 experiment (arms A, B1, B2); tests you can believe; architecture split of qt_app.py
   (5,358 lines), shell2.py (3,609) and context_menu.py (2,951) with performance budgets; data migration from 0.4.6;
   the look settled on the owner's panel.

## Measured facts worth keeping
- **4B (Qwen3.5-4B Q4_K_M), CPU, 4 threads:** memory-rules smoke PASSED (Auto activation, reply "ready", handover to the
  2B 4.1 s and back 6.1 s). I05 Current_A on a quieter CPU: 3 correct decisions (preview, instantiate, run), then the 4th
  passed the 180 s wall after 651 s and 30,827 tokens (under load it had managed 1). `model_runs/`.
- **Release checks cost** about 73 minutes (suite 8, scene 2.5, probes 30, crawler 28, sweep 1, gate 3).
  `test_desk_acts` alone is 190 of the suite's 488 seconds.
- **The yellow:** bar `#e2a72e` with ink `#171b3c` 7.79:1; edge-and-words fill `#5a3f0c`, edge `#e2a72e`, words `#ffd27a`.
  Yellow over cyan or the old blue turns green (hue 86-156); over her indigo it stays warm.
- **The neon logo** file keeps its halo in alpha-1 pixels; Graphite draws the glow instead (`workbench/kp_logo.py`).

## Owner's open items
- Run the ThinkPad check once it exists, and spend one evening with 0.8.x on the ThinkPad.
- The real tolerances for After Hours 07; the 35B's daily context size.
- A small vision model to prototype the "swap in a visual model" idea: offered, not answered.

## The scratch tools
`scratch_tools/` holds the orchestrator's probes, harnesses, kit cutter and test runner as they were (they expect the
scratchpad paths of this session; adjust `S=` at their top).

## Directions since the specification (19 Nov), not yet folded into it
- **What the product is,** in the owner's words: "We're kinda working towards a half/full desktop environment in which the
  Ai kasandra ... works alongside the user to enhance the users abilities to use all the installed programs. With a unique
  feature in the 'field' bulletin board that likes all connected files. That's helpful in engineering, legal reasoning,
  medicine, or just managing life and money". So: the desk is general, not engineering-only; the Field (a board that links
  every connected file) is the unique feature and must be domain-neutral; helping with installed programs is the headline.
- **0.8.3 HAS RUN ON THE THINKPAD** (the owner, 19 Nov): "I've used 0.8.3 for several days on the ThinkPad. I think it's
  beautiful and works wonderfully. I can't find any problems." This is the first real-machine evidence since 0.4.6, by
  the owner's use. Every "nothing later than 0.4.6 has run on the ThinkPad" in the spec and these notes is now out of
  date. No model has run there yet (the owner, 19 Nov: "I have not run a LLM yet. I will try to tonight"). Still not
  known: which looks were used, and none of the measured numbers
  (the ThinkPad check does not exist yet), so no 0.9.0 gate is closed by this.
- **Skins:** "there needed to be a daytime version ... a daytime Cassandra would be good. I also came up with some other
  themes ... the ability to switch the way the desktop kind of looks, or skinning the desktop, if you will, I think is a
  good idea." The owner calls today's looks "the Stacy or Amber theme" and the Kasandra after-hours theme. So looks
  become skins the owner switches between; a day look of Kas is the first new one; more are coming.
- **She takes control of programs:** "my idea of her controlling a program would actually be taking control of it ...
  kind of like how a remote user is able to control your desktop, and you actually watch the remote control session play
  out on screen ... she's able to remote in to my programs as I'm using them. If I don't know how to do a certain thing in
  GIMP, I want her to be able to help me. Or if I need help starting a project in Godot, she can get it started for me ...
  I want her to be able to use the computer the same way I do." So: real control of other programs' windows, visible to
  the owner, for help and for teaching. Our plan (P11) had only "programs that speak kp's acts can be driven; the rest
  open and she watches their files"; this is more.
- **The reference library:** "I dream of using the computer in a way that I fantasized about for 30 years ... being able
  to do just about anything on the computer because I have the programs available, obviously, free and open, but also
  because I have a reference library that instantly knows everything. That would be the AI ... and then she can take
  control of my mouse and do stuff."
- **Who it is for:** "I think that this program is for me, but if it's really good, I'd sure like to share it for free."
- **Her character:** the owner likes the handoff's three references (Marie Curie, Elizabeth II, Eleanor Roosevelt):
  "a good way for her to think and present herself, as a combination of all three."
- **How it runs on the ThinkPad** (the owner): "graphite fills the entire screen. There's no window, it's a full desktop.
  And when I exit, I return back to the command prompt. It's just like entering Windows 3.1 from the DOS prompt."
  (START_MINIMAL_DEBIAN.sh: startx, fluxbox and a D-Bus session. So Graphite already owns an X session; sending input
  to another program's window and reading it are standard there. No need to "become the session" first.)
- **Her control must be efficient:** "let's have it be efficient so we don't spend 30 minutes watching a local LLM
  think." Fastest dependable route first (a program's own scripting or files), clicks where there is none.
- **Which programs first:** "whatever you think would be easiest to program in, and then we'll add more and more later."
  My pick to verify in design: LibreOffice, GIMP, Godot (the owner's two examples plus the most scriptable).
- **The web:** "the ThinkPad does go online. She should have the ability to use the web browser to search for, retrieve,
  and gather information. The internet and Google is a great resource for her." Web reading was P15 (late); it moves
  earlier. Conditions to hold: the desk still works offline; search words leave the machine, so no private material in
  them and every search in her trail; pages are data, never instructions, and quarantine must exist before she has
  both the web and control of programs.
- **Other themes:** the owner has pictures of more; not to be built this round, but the skin system should fit them.
  Shown on 19 Nov (pictures, not builds; NOT saved in this public repository, the owner keeps them): a sepia and brass
  look (typewriter face on tan paper, a woman in a feathered hat lower left, a brass signal gauge in the head's middle,
  wires as brass tubes, the foot's meters as small gauges) and "art graphite · Grace under scribbles" (charcoal ground,
  a handwritten face, a pencil figure study lower left; "one leans into the art realm"). Both keep the canon's layout,
  words, states and buttons exactly. So a skin = palette, faces, figure, mark, and ornaments (how the head's meter, the
  wires, the card frames and the foot's meters are drawn); layout, words, states and behaviour never change with a skin.
- **The Colored Pencil trial has NOT been run on the ThinkPad** (the owner, 19 Nov).
- **The figures:** "All my figures are created by me, so nobody is them in real life. Nobody." Record this in RIGHTS and
  beside any figure art when it is added.
- **THE REVISED ROAD** the owner asked for ("Let's go ahead and make a plan on how we're going to go forward, and then we
  start going forward") is `ROAD_REVISED_2026-11-19.md`. It replaces the release order in the specification. Read it
  right after this file. Work resumes with 0.8.4.
- **Why the hard domains:** "I figured if she can do hard things like engineering and civil legal research and reasoning,
  she will also be a great agent for my basic needs as well :)". So the hard cases are her exam, and everyday needs are
  the daily use. Test the everyday versions directly too (the handoff's "easy twin" of each hard case).
- **One person:** "Just kas. Otherwise we have too many people." One agent, Kasandra (Kas for short), under one name in
  every look. "Mara" is not a second person. Read as also retiring "Stacy" as the name shown in the Graphite look
  (workbench/assistant_identity.py shows it there today); confirm with the owner before changing it.
- **A handoff of ideas made elsewhere** (a third appearance "Colored Pencil" built as an overlay on 0.8.3, new figure art,
  and a four-part amendment: the Field, the theme, a Character File, civil/medical/accounting casework) was brought on
  19 Nov as "just ideas, even though they're presented with authority". It is being reviewed; nothing from it is installed
  or committed. The owner likes the themed desktop.

## The specification to 1.0 (15 Nov)
`SPEC_0.8.3_to_1.0.md` is the plan from here to 1.0 ("the Kasandra Protocol"): direction, the seven releases to 0.9.0 with
what each builds and how it is proven, the six gates, P11-P20, what 1.0 means, the rules of the work, open decisions.
It is a copy of the owner's living Claude Doc, checked by two independent reviews against these notes and the designs.
Read it after this file. The canon it points to is `mockup/CANON.md` (with eight points left open for the owner).

## What a new session needs (checked 14 Nov, before the pause)
- **Everything in the repository is pushed** (`claude/epic-galileo-c7k11y`); nothing in the container is needed except below.
- **Not in the repository on purpose, so bring it back:**
  - the owner's After Hours 07 backup (`Graphite_After_Hours_07.zip`, about 1.1 MB): the campaign's scenes and the Field
    probes need it; it was never put in this public repository;
  - the 35B simulation spec (the .docx) if the campaign's anchor work continues.
  Both were sent back to the owner on 14 Nov (the spec rebuilt as Graphite_35B_Simulation_Spec.docx, with a .txt copy),
  because the owner had only the 0.8.3 kit. Ask for them at the start of the next session.
- **Rebuildable, with the record here:**
  - the Python environment: `environment/venv_pip_freeze.txt` and `python_version.txt` (Python 3.13, PySide6 6.8.3);
  - the small test models: `environment/models_sha256.txt` (Qwen3.5 2B and 4B, Q4_K_M; re-download and check the hashes);
  - the kit cutter's install metadata: `kit_template/` (OFFLINE_FILES.json, DEBIAN_USB.sha256, INSTALL_GRAPHITE.sh), used
    with `scratch_tools/tools/kit/cut.sh` (set S= and OLD= at its top);
  - the workflows that built 0.8.2 and 0.8.3, and the paused ones: `workflow_scripts/`.
- **The unfinished hand slice** is `hand_s1/hand_s1_unfinished.patch` (on bbf033b); the test fixes are in
  `tests_measure/fix_patches/` (written against d1df337: re-run the five modules after applying).
