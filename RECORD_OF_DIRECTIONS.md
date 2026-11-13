# Graphite · record of directions

Read this first. It says where Graphite is going, what holds, where it stands, and what comes next. It is the whole
record: one page, kept current, with no history of what was tried and dropped. The owner keeps backups of everything
earlier; the previous record is in the 0.2a13 release.

## Where this is going

On 12 November 2026, once the source was free: "let's develop where it can go." It "is basically going to be my ultimate
desktop from which I can launch every program from a basic screen and do basic things, or launch the program into its full
window. But when I am inside of the graphite workbench, I am inside of a nice dark orange and green fantasy computer land
that is tremendously effective, efficient, smart, and knows what I'm doing because I'm doing it."

In the owner's words (master specification, `docs/briefs/Graphite_Master_Specification_v5_BOSS.pdf`):

- "The destination is a usable computer: I can work directly, delegate an edit or sustained investigation, and return
  to inspectable progress."
- "the Hello computer experience: address the machine with an intention and work at the level of the problem."
- "Completed assignments should leave the machine more capable."

And on 12 November 2026: "My wish is like Lains computer from the awesome anime." Read that as a feeling to build, not a
picture to copy: a machine you sit down to at night that is already awake, where the work hangs in layers in the dark,
the wires between things are visible, and you speak to it in one line. Everything drawn is original.

One ThinkPad on minimal Debian runs it. The model is local. Nothing leaves the computer unless the owner turns a
service on. Finished means installed and seen working on that ThinkPad, judged by real completed work.

## What holds

- **Authority.** "I pre approve all your expert opinions, recommendations, and choices." "My goal with you is to build,
  complete, and finish the project." 12 November: "Do everything auto and surprise me." Decide, say what you decided,
  keep moving. Ask only when the answer changes the result or reaches outside the computer.
- **Two people to steer by** (12 November: the source is "whatever Linus" Torvalds "would do"; "Also think what would
  Woz do ... kindness to humanity"). Linus: the source is open under the GPL version 2 only, the work is done in public, and
  what counts is whether it runs. Woz: the fewest parts that do the job; a machine one person can understand whole; the
  schematics come in the box; it is ready the moment it is switched on; it is generous, a little playful, and kind to
  the person at the keyboard (plain words, no blame, nothing taken from them, useful on a modest machine).
- **Simple, for a power user** (12 November: "let's concentrate on simple power user"). One line to speak in. Few words
  on the screen and none that explain themselves twice. One rule instead of a setting where a rule will do. No
  hand-holding. **The mouse and the keys do the same things** (13 November, the whole-build specification: "The mouse, keys
  and Stacy use the same target and operation"; "Click a tile to open the item"; "an explicit Approve button"). An earlier
  reading of this point as "keyboard first" was the builder's, not the owner's, and is withdrawn: someone should be able
  to sit down with a mouse and do the ordinary work by looking at the screen, and the keys make the same person faster.
- **Checking.** Light. Batch related edits, then one launch-and-use check. Dig deeper only for a real failure or a
  worry about the owner's data. No new test suites, no test-count campaigns.
- **Honesty.** Say plainly what is not done. Nothing counts as accepted on the ThinkPad until it is tried there.
  A picture is not a run.
- **Records.** This page, and a slim tree. Keep what teaches how the program works or why. When unsure, keep.
- **The owner stays in control.** One dispatcher for all work (the Kernel). One kill switch for every job, model and
  capture (Stop all jobs, Ctrl+Shift+F12). Session and power actions only on the owner's confirmation, never sudo.
- **Build for the smallest model.** Put the intelligence in the records and exact computation, so a better model is a
  free upgrade.
- **Use mature programs.** Open the real spreadsheet, the real editor; hand files over and take them back. Do not
  rewrite what exists. Keep every capability when the look changes.
- **Two names, one for each thing** (12 November: "to simplify things, Stacy should be the face of the assistant as
  communicated through the language of Stacy. S-T-A-C."). Graphite is the workspace. Stacy is the assistant: one
  assistant, and hers is its face. staC, said "Stacy", is how she speaks: what she reads, she shows as a staC line the
  owner can run. Her portrait is still, in its own places. Folders, settings keys and scripts keep their older names
  (Ledger, Slate, Hatch, LS, arc1) on purpose; do not rename them.

## The desk

- **The look.** Near-black ground, cream reading text. Amber is what is selected, what has the keyboard and what waits
  for the owner. Green is what is live: readings, what is current, staC, the pointer, and whatever the pointer is over
  (13 November: "I'd probably like the mouse pointer to be the systems green. We kinda need more green glowing"). The
  pointer keeps the shape the owner gave it earlier (the mark's two facets, aimed at 11 o'clock, the click at the tip)
  and takes the green as its ink. Amber glows only where it means something (13 November: "let's add some glow effects
  to the orange and anywhere else it would enhance the mood"): one amber halo on the desk, where the keys go (the
  selected sheet, the page being read, or the writing line), and a light at the mark of whatever waits for the owner,
  with Approve lit until it is pressed. Live
  things glow a little, and the pointer carries a faint light over the Field; the Clean desk keeps the green and has no
  glow. Monospaced lettering, thin rules, original ink-and-halftone art. Surfaces are still: nothing moves unless the
  owner's hand moves it. Art sits in its own places (Illustrated, ASCII or Clean) and never enters documents.
- **The frame.** The path of the current work across the top with Work, Programs and System; Files, Machine and
  Settings on the left; Talk, Activity and Context on the right; one writing strip along the bottom (Assistant,
  Terminal, Log) with CPU, GPU, RAM and TXT beside it. The work is in the middle.
- **The Field** (new, 12 November; specification sections 70 to 72; F9, Arrange → Field, or type `field`). An
  overview where the real objects of the work hang as sheets in the dark with the wires that say what feeds what:
  material, tables, calculations, findings, open questions. The selected sheet is brightest and what touches it stays
  near. Arrow keys follow the wires; Enter opens the real editor; coming back keeps the place. N shows this computer's
  network the same way (interfaces, programs, the places they reach), and Enter there opens the Log's Network stream.
  Right-click or the Menu key on a sheet opens the desk's own menu for it: open, what feeds it, what it feeds, its
  staC line, ask Graphite about it.
- **Stacy is staC, and she is more than a picture** (12 November: "She is more then wallpaper", "StaC is the secret code.
  Let's use the hell out of it!!!"). Every object in the Field carries the staC line that reads it. Her rail at the right
  of the Field shows that line for the selected sheet; S puts it in the writing strip and Shift+Enter runs it, with the
  answer in the working area. Wherever Graphite shows a thing, it should be able to say that thing in staC, and Stacy is
  where it is said. In Talk she is the assistant: asked about a sheet (its menu, or a question typed while it is
  selected) she answers with the staC line that reads it and what the records say, model or no model
  (`workbench/shell2.py`, SlateFace.answer_in_stac). A model, when there is one, adds her own words to that; it does not
  replace it.
  This is the desktop model to grow: every kind of work should be findable there, and the same action should be
  reachable from the sheet, the right-click menu, the keyboard, a typed staC line and the assistant. The code is
  `workbench/field_model.py` (no Qt), `field_qt.py` (drawing), `field_source.py` (reads through the Kernel) and
  `field_page.py` (the way in and out).
- **The desk does** (12 November: "I want a do, not a chatbot"; "Build more then I can imagine"). The program, not a
  model, knows what there is to do: for a sheet it asks the records how the thing stands and offers the steps that fit
  (`workbench/field_do.py`), each an exact line. A read runs at once. A change is put in Talk with its line and waits for
  one go. C checks the desk; one go settles what needs no decision of the owner's; then the desk checks itself, and that
  check is what "done" means. Keys in the Field: D, a digit to choose, G for the go (a digit never approves), C, and F
  on the shelf for a program's full window. Whether a step runs by itself is the Kernel's scope for it, read from the
  Kernel. Every step is an operation the program already had;
  add steps there, not a second engine. What a model does grows with the model. A 2B model on four processor threads
  puts reads into words and no more; that was measured (`docs/MODEL_TRIAL_03.md`) and it is a floor, not a ceiling. It
  was never measured what a model can do when it is given a concrete goal, the open item and a few relevant operations,
  and the owner's specification asks for exactly that: "Let the local model work out the steps." So the model's part is
  to be found by trying it on real jobs (the specification's tenth extension: two models, the same finished job), not
  fixed here. What does not move: every change waits for the owner's Approve, exact numbers come from exact computation,
  and what Stacy did can be checked by the same doubts as anyone's work.
- **Catch the trap first** (13 November: the owner's whole-build specification, 35 situations each with a "difficult
  variation", and "build what you think is the neatest ... upon the spirit of the idea"). Before Stacy makes more, she
  catches more: X doubts a sheet with exact questions (`workbench/field_doubt.py`), worst first, each row a read; a doubt
  comes with the step that removes it; the desk check doubts everything. No model takes part, and a model is not asked to
  rephrase a doubt. The specification is the map and the acceptance test (it counts on the ThinkPad, on the owner's own
  material); it is reached one trap and one situation at a time, by adding a question here and its steps in
  `field_do.py`, never by trusting a model more.
- **One thin journey through all four** (13 November: the owner's second specification and "What we want from Graphite").
  The evidence side had become a more complete product than the everyday work and the handing over. The four parts
  (click into the work; one familiar place to work in the centre, with Programs as the only way to a full program; give
  Stacy the part the owner does not know how to do; carry the result forward) are built together as journeys, not as four
  layers: take one item from the Field to the centre, through a full program and back, then let Stacy make the same trip.
  The mouse is the primary input (13 November: "now that we're using mouse as primary input for graphite"): every
  control is a visible place of a size the hand can hit, a control is as wide as it looks, and a view that cannot serve
  a control dims it and says why. The centre's bar (0.4.7: Field, Find, size, Undo, Redo, Save, Actions, made of the
  actions the keys already had) is the first slice of the specification's toolbar.
  First journey, 0.4.5: with the mouse alone, open a sheet tile, change a cell, save, come back to the same tile, trace
  the calculation and approve its recheck; and the same change asked of Stacy in words and approved with a click
  (`field.set`). Known to be missing for the next ones: the centre's common frame and small toolbar; an ordinary workbook
  as a citizen of the chain (a calculation can only be made from a sheet reviewed from a PDF); a full program through
  Programs with the saved revision coming back; Stacy working out steps for a goal.
- **A pass for the eye and the hand** (13 November: "Should we do a pass that focuses on the user experience"). After
  the powers, a pass that adds none: the real screens were looked at as a newcomer would, at the small size and at large
  reading sizes, and what got in the way was put right. An answer is read where the eyes are: a page over the work
  (`FieldView.show_reading`) for the doubt, the desk check, the brief and the keys; light pages step aside at the next
  key. Talk puts the answer before the line. ? shows every key. When a new power is added, look at it on the small
  screen before it is called done: if the answer is below the fold, it is not done.
- **Look ahead, write it up, the owner's own words** (13 November: "Build a few ideas surprise me"). Four additions in the
  same spirit, none with a model. A what-if on a sheet is followed along the wires (`workbench/field_ripple.py`,
  `field.ripple`): calculations worked again exactly, words that carry a number that would move, and each check run by
  its own program on the sheet as it would be; the Field marks what would move. More traps as exact questions
  (a subtotal counted twice, the same digits under another unit, a check on a replaced page); quantities are compared in
  base units. B writes the desk up as one page from the records (`workbench/field_brief.py`); the go keeps what was
  shown, and the page knows when the desk has moved on. The owner keeps staC reads under words of their own
  (`workbench/stac_words.py`); a word is written out before it runs. And a rule of working that proved itself: a second
  set of readers went through the code while it was being written and found real faults in 0.4.1 and 0.4.2; have a
  reader that did not write the code read it before it is called done.
- **staC reads the desk** (12 November: "Can we make staC and Stacy more powerful in creative ways"). The Field is a staC
  source: `field.read` (objects, wires, what waits), `field.trace {id}` (where a thing comes from, what rests on it),
  `field.whatif {id, set}` (a calculation worked with other values, changing nothing). `this` at the start of a line is
  the selected sheet. Stacy's trace (T) and her "what if" are those reads, shown as lines like everything she reads.
  When a new power is wanted for Stacy, make it a read staC can run first, then give it a key and words.
- **The shelf** (12 November; P in the Field). Every program and room as a sheet, in six columns set by hand that do not
  move (Work, Think, Make, Build, Move, Set up; `field_source.SHELF`). Enter opens the room, which is the basic screen;
  a native program's full window is started from its room. This is the launcher the owner asked for, first slice.
- **With a model, she reads first** (`docs/MODEL_TRIAL_03.md`). The staC read is exact and comes first; the model only puts
  the rows into words, and its words are marked as its own. A 2B model is enough for that. Improve the reads, not the
  prompt.
- **It opens on the work** (12 November, the owner left the choice here). At launch the Field is in front when the
  workspace has anything in it, with what waits selected; Esc goes to where the owner left off. An empty workspace
  opens on Home. Home's "Start: always Home" still means Home.
- **Small things that stay.** `poem` as the empty hint. Ingress and Egress. The pinned Trash. Home as a file browser.
  The game behind System (STRUTHIO ARCADE; its source is the STRUTHIO repository's `arcade/`, changed there and
  copied in).

## Where it stands

Graphite 0.4.7: 0.2a13 "After Midnight" plus the Field (0.3), then Stacy as the assistant answering in staC, the start
on the work, the shelf and the GPL (0.3.1), the desk that does (0.4), staC reading the desk, with trace and what-if (0.4.1), Stacy's doubt (0.4.2), the look ahead, the brief and the owner's words (0.4.3), a pass for reading and finding the keys (0.4.4), the mouse path with Stacy's first change on approval (0.4.5), the green pointer with green for what it is over and a glow for what is live (0.4.6), and amber light for the keyboard and for what waits, with the mouse put first: the centre's bar, the whole desk on Z, bars to drag (0.4.7). Passes 1 to 10 of the twenty-pass plan (`docs/BOSS_IMPLEMENTATION_PLAN.md`) are
built: the dark desk, the editable path, cascading menus that build staC chains, the Vulkan worker and memory
coordination, evidence preparation on the CPU, the model lifecycle, source collections, and PDF table to sheet to
report. Releases 0.2a8 to 0.2a13 then prepared the first ThinkPad install (offline kit, first-run workshop) and
settled the desk art; they also cut thin slices of later passes (the spreadsheet round trip, Open source row, Night
Shift, Method Press). `workbench/version.py` has one line per release.

Checked on 12 November 2026 in a cloud container, not on the ThinkPad: the nine release parts restore with
`INSTALL_LS.py`; `tools/check_release.py` passes; the window opens offscreen with no model; the Field draws a restored
worked case (After Hours 07) from its real records and opens its pages. The source is public in the STRUTHIO
repository on its own branch under the GNU GPL, version 2 only (`COPYING`); Stacy's artwork, the names and the game
copy are kept back (`RIGHTS.md`).

Never yet done, by every document in the tree:

- Graphite has not run on the ThinkPad (E16 Gen 2, Ryzen 7 7735HS, Radeon 680M, about 61 GiB shared memory, Debian 13
  at a text console). The offline kit is ready: `docs/THINKPAD_FIRST_INSTALL.md`.
- No model has answered on the ThinkPad, and the Vulkan path has not met the Radeon. (Two small models answered in the
  build container on 12 November: `docs/MODEL_TRIAL_03.md`.) No model file ships; the owner chooses one.
- Rust: asked about on 12 November ("I'm thinking rust soon???"). Not a rewrite. When the ThinkPad shows what is slow,
  new self-contained parts (the staC engine, indexing, evidence preparation) can be written in Rust behind the same
  dispatcher, the way the Linux kernel took Rust: new parts, one at a time.
- Twenty focused tests in five modules still fail because they assert the earlier look, layout and version.

## What comes next

1. **First boot on the ThinkPad** from the offline kit, with no model. Write down what actually happened.
2. **One real model** in the Brain room, on the processor and then on the Radeon. Record what the program reads back.
   The owner's choice for the first (12 November, voice-typed "Quinn 4.0 27B Quant 4 when it's available"): the Qwen
   family's 4.0 release at 27B, 4-bit quantised, once it exists.
3. **One whole journey with the model live:** datasheet to sheet to calculation to report (the first-run workshop),
   then a question over the prepared evidence.
4. **Connect the doing to the assignment loop** (`workbench/agent_loop.py`, which already records every step and keeps
   working while Graphite is closed): a job started from a sheet, its checks bound so that done means they pass, the
   owner's go for a waiting change in the Work block. Then the steps not offered yet: reviewing a sheet again from its
   page, deciding a held source, citing sources for a rewritten finding.
5. **Grow the Field and staC together** into the working desk: a key that starts a program in its full window from the
   shelf and brings its files back; what is in use and what was used last, so the desk knows what the owner is doing;
   every object kind (methods, files), staC lines that do
   more than read (the chain of steps that made a result, ready to run again on new material), wires that route around
   sheets, reading off the window's thread, and the way back from a full program.
6. **Then the plan's abilities, in its order:** full native programs from the desk (pass 11), a changed fact that
   travels (12), the assistant on any described job (13), getting the tools it lacks (14), web, mail and calendar on
   the owner's terms (15), specialist and creative routes (16), durable self-improvement (17), and the closing
   release (18 to 20). The passes are a map of abilities, not a schedule; measure progress by journeys that work on the
   real machine.

## Where the knowledge is

Read in this order: this page; the master specification (pages 1 to 15, then sections 70 to 76 for the desktop);
`docs/THINKPAD_FIRST_INSTALL.md`; `README.md` for install, start, backup, checks and packaging;
`docs/BOSS_IMPLEMENTATION_PLAN.md` for the passes. For how one mechanism works, read its own document in `docs/`;
documents written before 8 November describe the earlier look and names, and are right about mechanisms only.
`docs/DECISION_REGISTER.json` holds the reasons behind older choices.

The commands: test one module at a time with
`QT_QPA_PLATFORM=offscreen python3 -B -m unittest tests_integrated.test_graphite` (never discover);
`python3 tools/check_release.py` for integrity; after any source change
`python3 tools/package_graphite.py --manifest-only` rebuilds the seed and the manifest.
